import base64
import hmac
import io
import os
import re
import threading
from datetime import datetime, timezone
from functools import wraps

import sentry_sdk
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_socketio import SocketIO, join_room, leave_room
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sentry_sdk.integrations.flask import FlaskIntegration

from stock import (
    draw_stock_chart,
    fetch_latest_stock_price,
    fetch_stock_data,
    normalize_ticker_symbol,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("STOCK_WEB_SECRET", "dev-only-change-this")
app.config["USERNAME"] = os.environ.get("STOCK_WEB_USERNAME", "admin")
app.config["PASSWORD"] = os.environ.get("STOCK_WEB_PASSWORD", "change-me")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "本地服务")
STOCK_UPDATE_INTERVAL = max(1, int(os.environ.get("STOCK_UPDATE_INTERVAL", "60")))

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
    )

socketio = SocketIO(
    app,
    async_mode="threading",
    manage_session=False,
    message_queue=os.environ.get("SOCKETIO_MESSAGE_QUEUE") or None,
)
_subscription_lock = threading.Lock()
_subscriptions = {}
_stock_update_stops = {}
_TICKER_PATTERN = re.compile(r"[A-Z0-9^=.-]{1,32}")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def make_chart(data):
    figure = Figure(figsize=(10, 5.2), dpi=130)
    axis = figure.add_subplot(111)
    draw_stock_chart(axis, data)
    figure.autofmt_xdate()
    figure.tight_layout()

    image = io.BytesIO()
    FigureCanvasAgg(figure).print_png(image)
    return base64.b64encode(image.getvalue()).decode("ascii")


def display_value(info, key, suffix=""):
    value = info.get(key)
    if value is None:
        return "暂无数据"
    if suffix == "%":
        return f"{value * 100:.2f}%"
    return f"{value}{suffix}"


def build_overview(data):
    info = data["fundamentals"]
    revenue = info.get("totalRevenue")
    market_cap = info.get("marketCap")
    dividend_yield = info.get("dividendYield")
    return {
        "name": info.get("longName", data["ticker_symbol"]),
        "pe": display_value(info, "trailingPE"),
        "pb": display_value(info, "priceToBook"),
        "dividend": (
            f"{dividend_yield * 100:.2f}%"
            if dividend_yield is not None
            else "暂无数据"
        ),
        "market_cap": (
            f"{data['unit']}{market_cap:,.0f}"
            if market_cap is not None
            else "暂无数据"
        ),
        "revenue": (
            f"{data['unit']}{revenue:,.0f}"
            if revenue is not None
            else "暂无数据"
        ),
        "gross_margin": display_value(info, "grossMargins", "%"),
        "profit_margin": display_value(info, "profitMargins", "%"),
        "roe": display_value(info, "returnOnEquity", "%"),
        "industry": info.get("industry", "暂无数据"),
        "sector": info.get("sector", "暂无数据"),
        "country": info.get("country", "暂无数据"),
        "website": info.get("website", "暂无数据"),
        "summary": info.get("longBusinessSummary", "暂无数据"),
    }


def _stock_room(ticker):
    return f"stock:{ticker}"


def _release_stock_subscription(sid, ticker):
    with _subscription_lock:
        subscribed_tickers = _subscriptions.get(sid)
        if not subscribed_tickers or ticker not in subscribed_tickers:
            return

        subscribed_tickers.remove(ticker)
        if not subscribed_tickers:
            _subscriptions.pop(sid, None)

        if not any(ticker in tickers for tickers in _subscriptions.values()):
            stop_event = _stock_update_stops.pop(ticker, None)
            if stop_event:
                stop_event.set()


def _stream_stock_prices(ticker, stop_event):
    while not stop_event.is_set():
        try:
            price = fetch_latest_stock_price(ticker)
            socketio.emit(
                "stock_price",
                {
                    **price,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                to=_stock_room(ticker),
            )
        except RuntimeError as error:
            app.logger.warning("Unable to update %s price: %s", ticker, error)
            sentry_sdk.capture_exception(error)
            socketio.emit(
                "stock_price_error",
                {"ticker": ticker, "message": "暂时无法获取最新行情，请稍后重试。"},
                to=_stock_room(ticker),
            )

        if stop_event.wait(STOCK_UPDATE_INTERVAL):
            break


@socketio.on("connect")
def handle_socket_connect(auth=None):
    if not session.get("logged_in"):
        return False


@socketio.on("subscribe_stock")
def handle_stock_subscription(payload):
    payload = payload if isinstance(payload, dict) else {}
    ticker = normalize_ticker_symbol(str(payload.get("ticker", "")))
    if not _TICKER_PATTERN.fullmatch(ticker):
        return {"ok": False, "error": "股票代码无效。"}

    sid = request.sid
    join_room(_stock_room(ticker))
    should_start_worker = False
    with _subscription_lock:
        subscribed_tickers = _subscriptions.setdefault(sid, set())
        if ticker not in subscribed_tickers:
            subscribed_tickers.add(ticker)
            stop_event = _stock_update_stops.get(ticker)
            if stop_event is None or stop_event.is_set():
                stop_event = threading.Event()
                _stock_update_stops[ticker] = stop_event
                should_start_worker = True

    if should_start_worker:
        socketio.start_background_task(_stream_stock_prices, ticker, stop_event)
    return {"ok": True, "ticker": ticker}


@socketio.on("unsubscribe_stock")
def handle_stock_unsubscription(payload):
    payload = payload if isinstance(payload, dict) else {}
    ticker = normalize_ticker_symbol(str(payload.get("ticker", "")))
    if not _TICKER_PATTERN.fullmatch(ticker):
        return {"ok": False, "error": "股票代码无效。"}

    leave_room(_stock_room(ticker))
    _release_stock_subscription(request.sid, ticker)
    return {"ok": True, "ticker": ticker}


@socketio.on("disconnect")
def handle_socket_disconnect(reason=None):
    sid = request.sid
    with _subscription_lock:
        subscribed_tickers = list(_subscriptions.get(sid, ()))
    for ticker in subscribed_tickers:
        _release_stock_subscription(sid, ticker)


@app.get("/api/hello")
def hello():
    return jsonify(service=SERVICE_NAME, message=f"Hello from {SERVICE_NAME}")


@app.get("/healthz")
def healthz():
    return jsonify(status="ok", service=SERVICE_NAME)


@app.get("/db-test")
def db_test():
    try:
        import psycopg
    except ImportError:
        app.logger.exception("PostgreSQL driver is unavailable")
        return jsonify(error="PostgreSQL driver is unavailable"), 503

    try:
        with psycopg.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
            dbname=os.environ.get("DB_NAME", "stock_viewer"),
            user=os.environ.get("DB_USER", "stock_viewer"),
            password=os.environ.get("DB_PASSWORD", ""),
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS service_db_test (
                        id INTEGER PRIMARY KEY,
                        service TEXT NOT NULL,
                        checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO service_db_test (id, service)
                    VALUES (1, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET service = EXCLUDED.service, checked_at = NOW()
                    """,
                    (SERVICE_NAME,),
                )
                cursor.execute(
                    "SELECT service, checked_at FROM service_db_test WHERE id = 1"
                )
                row = cursor.fetchone()
    except psycopg.Error:
        app.logger.exception("PostgreSQL connectivity check failed")
        return jsonify(error="PostgreSQL connectivity check failed"), 503

    return jsonify(
        status="ok",
        service=SERVICE_NAME,
        database_service=row[0],
        checked_at=row[1].isoformat(),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid_username = hmac.compare_digest(username, app.config["USERNAME"])
        valid_password = hmac.compare_digest(password, app.config["PASSWORD"])
        if valid_username and valid_password:
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("用户名或密码错误。", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def dashboard():
    result = None
    error = None
    ticker = request.form.get("ticker", "0700.HK")
    days_text = request.form.get("days", "365")

    if request.method == "POST":
        try:
            days = int(days_text)
            result = fetch_stock_data(ticker, days)
            result["chart"] = make_chart(result)
            result["overview"] = build_overview(result)
        except (RuntimeError, ValueError) as exc:
            error = str(exc)

    return render_template(
        "dashboard.html",
        result=result,
        error=error,
        ticker=ticker,
        days=days_text,
    )


@app.get("/download")
@login_required
def download():
    ticker = request.args.get("ticker", "")
    days_text = request.args.get("days", "365")
    try:
        data = fetch_stock_data(ticker, int(days_text))
    except (RuntimeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))

    csv_data = data["historical_data"].copy()
    csv_data.index.name = "Date"
    output = io.BytesIO(csv_data.to_csv(encoding="utf-8-sig").encode("utf-8-sig"))
    filename = f"{data['ticker_symbol']}_historical.csv"
    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("STOCK_WEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("STOCK_WEB_PORT", "5000")),
        debug=False,
    )
