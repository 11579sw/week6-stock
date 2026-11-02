FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STOCK_WEB_HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libtk8.6 libtcl8.6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt stock.py web.py ./
COPY web ./web
COPY templates ./templates
COPY static ./static

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gthread", "--workers", "1", "--threads", "100", "--access-logfile", "-", "web:app"]
