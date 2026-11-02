import argparse
import datetime
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import yfinance as yf

# 货币符号映射表
CURRENCY_SYMBOLS = {
    "USD": "$",
    "CNY": "¥",
    "HKD": "HK$",
    "EUR": "€",
    "GBP": "£",
}


def normalize_ticker_symbol(ticker_symbol):
    ticker_symbol = ticker_symbol.strip().upper()
    if ticker_symbol.startswith("HKG:"):
        ticker_symbol = f"{ticker_symbol[4:].strip()}.HK"
    return ticker_symbol


def fetch_stock_data(ticker_symbol, period_days=365, currency_code=None):
    ticker_symbol = normalize_ticker_symbol(ticker_symbol)
    if not ticker_symbol:
        raise ValueError("Ticker symbol cannot be empty.")
    if period_days <= 0:
        raise ValueError("period_days must be greater than 0.")

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=period_days)

    try:
        ticker = yf.Ticker(ticker_symbol)
        stock_data = ticker.history(
            start=start_date,
            end=end_date,
            auto_adjust=False,
        )
    except Exception as error:
        raise RuntimeError(f"Failed to fetch data: {error}") from error

    if stock_data.empty:
        raise RuntimeError(f"No data found for {ticker_symbol}.")

    if currency_code is None:
        try:
            info = ticker.info
            currency_code = info.get("currency", "USD")
        except Exception:
            info = {}
            currency_code = "USD"
    else:
        try:
            info = ticker.info
        except Exception:
            info = {}
    if not isinstance(currency_code, str) or not currency_code.strip():
        currency_code = "USD"
    currency_code = currency_code.strip().upper()
    unit = CURRENCY_SYMBOLS.get(currency_code, currency_code)

    close_prices = stock_data["Close"].dropna()
    if close_prices.empty:
        raise RuntimeError("No valid closing price data found.")

    latest_price = close_prices.iloc[-1]
    max_price = close_prices.max()
    min_price = close_prices.min()
    latest_date = close_prices.index[-1].strftime("%Y-%m-%d")

    return {
        "ticker_symbol": ticker_symbol,
        "period_days": period_days,
        "currency_code": currency_code,
        "unit": unit,
        "close_prices": close_prices,
        "historical_data": stock_data,
        "fundamentals": info,
        "latest_price": latest_price,
        "max_price": max_price,
        "min_price": min_price,
        "latest_date": latest_date,
    }


def fetch_latest_stock_price(ticker_symbol):
    ticker_symbol = normalize_ticker_symbol(ticker_symbol)
    if not ticker_symbol:
        raise ValueError("Ticker symbol cannot be empty.")

    try:
        stock_data = yf.Ticker(ticker_symbol).history(
            period="1d",
            interval="1m",
            auto_adjust=False,
        )
    except Exception as error:
        raise RuntimeError(f"Failed to fetch latest price: {error}") from error

    if stock_data.empty or "Close" not in stock_data:
        raise RuntimeError(f"No latest price found for {ticker_symbol}.")

    close_prices = stock_data["Close"].dropna()
    if close_prices.empty:
        raise RuntimeError(f"No latest price found for {ticker_symbol}.")

    return {
        "ticker_symbol": ticker_symbol,
        "price": float(close_prices.iloc[-1]),
        "market_time": close_prices.index[-1].isoformat(),
    }


def draw_stock_chart(axis, data):
    axis.clear()
    close_prices = data["close_prices"]
    latest_price = data["latest_price"]
    unit = data["unit"]
    currency_code = data["currency_code"]

    axis.plot(
        data["close_prices"].index,
        data["close_prices"],
        label="Closing price",
        color="#1f77b4",
        linewidth=2,
    )

    axis.axhline(
        y=latest_price,
        color="r",
        linestyle="--",
        alpha=0.5,
        label=f"Latest Close: {unit}{latest_price:.2f}",
    )

    axis.set_title(
        f"{data['ticker_symbol']} {data['period_days']}-Day Price Trend "
        f"({data['latest_date']})",
        fontsize=20,
        fontweight="bold",
    )
    axis.set_xlabel("Date", fontsize=15)
    axis.set_ylabel(f"Price ({unit} {currency_code})", fontsize=15)
    axis.tick_params(axis="both", labelsize=13)
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend(loc="upper left", fontsize=13)

    

def plot_stock_trend(
    ticker_symbol, period_days=365, currency_code=None, output_path=None
):
    print(
        f"Fetching data for {ticker_symbol.strip().upper()} for "
        f"the last {period_days} days..."
    )
    data = fetch_stock_data(ticker_symbol, period_days, currency_code)
    print(
        f"Latest close: {data['unit']}{data['latest_price']:.2f} | "
        f"Period high: {data['unit']}{data['max_price']:.2f} | "
        f"Period low: {data['unit']}{data['min_price']:.2f}"
    )

    figure, axis = plt.subplots(figsize=(12, 6))
    draw_stock_chart(axis, data)
    figure.autofmt_xdate()
    figure.tight_layout()

    try:
        if output_path:
            figure.savefig(output_path, dpi=150)
            print(f"Chart saved to {output_path}")
        else:
            plt.show()
    finally:
        plt.close()


def create_gui(default_ticker="0700.HK", default_days=365):
    root = tk.Tk()
    root.title("Stock Trend Viewer")
    root.geometry("1440x900")
    root.minsize(1100, 700)
    root.resizable(True, True)

    # Use the monitor's physical DPI as a baseline for Tk's point-to-pixel scale.
    screen_dpi = root.winfo_fpixels("1i")
    dpi_scale = max(1.25, min(screen_dpi / 72, 2.0))
    root.tk.call("tk", "scaling", dpi_scale)

    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=13)
    small_font = tkfont.nametofont("TkTextFont")
    small_font.configure(size=12)
    heading_font = tkfont.nametofont("TkDefaultFont").copy()
    heading_font.configure(size=14, weight="bold")
    root.option_add("*Font", default_font)
    style = ttk.Style(root)
    style.configure("TLabel", font=default_font)
    style.configure("TButton", font=default_font, padding=(16, 8))
    style.configure("TEntry", font=default_font)
    style.configure("TLabelframe.Label", font=heading_font)

    current_data = {"value": None}

    controls = ttk.Frame(root, padding=16)
    controls.pack(fill=tk.X)
    controls.columnconfigure(1, weight=1)
    controls.columnconfigure(3, weight=1)

    ttk.Label(controls, text="股票代码").grid(
        row=0, column=0, padx=(0, 8), sticky=tk.W
    )
    ticker_entry = ttk.Entry(controls, width=20)
    ticker_entry.insert(0, default_ticker)
    ticker_entry.grid(row=0, column=1, padx=(0, 16), sticky=tk.EW)

    ttk.Label(controls, text="天数").grid(
        row=0, column=2, padx=(0, 8), sticky=tk.W
    )
    days_entry = ttk.Entry(controls, width=10)
    days_entry.insert(0, str(default_days))
    days_entry.grid(row=0, column=3, padx=(0, 16), sticky=tk.EW)

    search_button = ttk.Button(controls, text="查询")
    search_button.grid(row=0, column=4)

    export_button = ttk.Button(controls, text="导出 CSV", state=tk.DISABLED)
    export_button.grid(row=0, column=5, padx=(8, 0))

    status_label = ttk.Label(
        root, text="请输入股票代码后点击查询", padding=(16, 0), font=default_font
    )
    status_label.pack(anchor=tk.W)

    content = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(10, 16))

    chart_frame = ttk.Frame(content)
    overview_frame = ttk.LabelFrame(content, text="公司概览", padding=12)
    overview_frame.configure(width=430)
    chart_frame.configure(width=620)
    content.add(chart_frame, weight=5)
    content.add(overview_frame, weight=2)

    summary_label = ttk.Label(
        chart_frame,
        text="",
        padding=(0, 0, 0, 10),
        justify=tk.LEFT,
        font=default_font,
    )
    summary_label.pack(anchor=tk.W)

    figure = Figure(figsize=(10, 6), dpi=140)
    axis = figure.add_subplot(111)
    canvas = FigureCanvasTkAgg(figure, master=chart_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    overview_scrollbar = ttk.Scrollbar(overview_frame, orient=tk.VERTICAL)
    overview_text = tk.Text(
        overview_frame,
        width=30,
        height=20,
        font=small_font,
        wrap=tk.WORD,
        state=tk.DISABLED,
        relief=tk.FLAT,
        yscrollcommand=overview_scrollbar.set,
    )
    overview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    overview_scrollbar.config(command=overview_text.yview)
    overview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def set_overview(data):
        info = data["fundamentals"]
        dividend_yield = info.get("dividendYield")
        if dividend_yield is not None:
            dividend_text = f"{dividend_yield * 100:.2f}%"
        else:
            dividend_text = "暂无数据"

        market_cap = info.get("marketCap")
        if market_cap is not None:
            market_cap_text = f"{data['unit']}{market_cap:,.0f}"
        else:
            market_cap_text = "暂无数据"

        def value_text(key, suffix=""):
            value = info.get(key)
            if value is None:
                return "暂无数据"
            if suffix == "%":
                return f"{value * 100:.2f}%"
            return f"{value}{suffix}"

        revenue = info.get("totalRevenue")
        revenue_text = (
            f"{data['unit']}{revenue:,.0f}"
            if revenue is not None
            else "暂无数据"
        )

        overview = (
            f"公司名称\n{info.get('longName', data['ticker_symbol'])}\n\n"
            f"估值指标\n"
            f"市盈率 (PE): {value_text('trailingPE')}\n"
            f"市净率 (PB): {value_text('priceToBook')}\n"
            f"股息率: {dividend_text}\n"
            f"市值: {market_cap_text}\n\n"
            f"业绩数据\n"
            f"总收入: {revenue_text}\n"
            f"毛利率: {value_text('grossMargins', '%')}\n"
            f"净利率: {value_text('profitMargins', '%')}\n"
            f"净资产收益率 (ROE): {value_text('returnOnEquity', '%')}\n"
            f"收入增长: {value_text('revenueGrowth', '%')}\n"
            f"盈利增长: {value_text('earningsGrowth', '%')}\n\n"
            f"公司信息\n"
            f"行业: {info.get('industry', '暂无数据')}\n"
            f"板块: {info.get('sector', '暂无数据')}\n"
            f"国家/地区: {info.get('country', '暂无数据')}\n"
            f"网址: {info.get('website', '暂无数据')}\n\n"
            f"公司简介\n{info.get('longBusinessSummary', '暂无数据')}"
        )
        overview_text.config(state=tk.NORMAL)
        overview_text.delete("1.0", tk.END)
        overview_text.insert("1.0", overview)
        overview_text.config(state=tk.DISABLED)

    def show_error(error_message):
        search_button.config(state=tk.NORMAL)
        status_label.config(text="查询失败")
        messagebox.showerror("查询失败", error_message, parent=root)

    def show_result(data):
        current_data["value"] = data
        draw_stock_chart(axis, data)
        figure.autofmt_xdate()
        figure.tight_layout()
        canvas.draw()
        unit = data["unit"]
        summary_label.config(
            text=(
                f"{data['ticker_symbol']} | 最近收盘: {unit}{data['latest_price']:.2f} | "
                f"最高: {unit}{data['max_price']:.2f} | "
                f"最低: {unit}{data['min_price']:.2f} | "
                f"日期: {data['latest_date']}"
            )
        )
        set_overview(data)
        status_label.config(text="查询完成")
        search_button.config(state=tk.NORMAL)
        export_button.config(state=tk.NORMAL)

    def export_csv():
        data = current_data["value"]
        if data is None:
            return

        output_path = filedialog.asksaveasfilename(
            parent=root,
            title="导出历史价格数据",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"{data['ticker_symbol']}_historical.csv",
        )
        if not output_path:
            return

        try:
            historical_data = data["historical_data"].copy()
            historical_data.index.name = "Date"
            historical_data.to_csv(output_path, encoding="utf-8-sig")
        except Exception as error:
            messagebox.showerror("导出失败", str(error), parent=root)
        else:
            status_label.config(text=f"CSV 已导出: {output_path}")
            messagebox.showinfo("导出成功", "历史价格数据已导出。", parent=root)

    def search_stock():
        ticker_symbol = normalize_ticker_symbol(ticker_entry.get())
        try:
            period_days = int(days_entry.get())
        except ValueError:
            messagebox.showerror("输入错误", "天数必须是整数。", parent=root)
            return

        if period_days <= 0:
            messagebox.showerror("输入错误", "天数必须大于 0。", parent=root)
            return

        search_button.config(state=tk.DISABLED)
        export_button.config(state=tk.DISABLED)
        status_label.config(text="正在获取数据，请稍候...")

        def load_data():
            try:
                data = fetch_stock_data(ticker_symbol, period_days)
            except Exception as error:
                error_message = str(error)
                root.after(0, lambda message=error_message: show_error(message))
            else:
                root.after(0, lambda: show_result(data))

        threading.Thread(target=load_data, daemon=True).start()

    search_button.config(command=search_stock)
    export_button.config(command=export_csv)
    ticker_entry.bind("<Return>", lambda event: search_stock())
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot a stock price trend.")
    parser.add_argument("ticker", nargs="?", default="0700.HK")
    parser.add_argument(
        "--cli", action="store_true", help="Use command-line mode instead of the GUI."
    )
    parser.add_argument(
        "--days", type=int, default=365, help="Number of calendar days to fetch."
    )
    parser.add_argument(
        "--currency", default=None, help="Currency code, for example HKD or USD."
    )
    parser.add_argument(
        "--output", default=None, help="Save the chart to an image file."
    )
    arguments = parser.parse_args()

    if arguments.cli or arguments.output:
        try:
            plot_stock_trend(
                arguments.ticker,
                period_days=arguments.days,
                currency_code=arguments.currency,
                output_path=arguments.output,
            )
        except (OSError, RuntimeError, ValueError) as error:
            parser.error(str(error))
    else:
        create_gui(arguments.ticker, arguments.days)