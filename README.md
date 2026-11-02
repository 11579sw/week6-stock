# Stock Trend Viewer

A stock lookup and trend analysis tool built with Python, Tkinter, Matplotlib, and yfinance.

The application provides a graphical interface for entering a ticker symbol and viewing:

- Historical closing price trends
- The latest closing price
- The highest and lowest prices during the selected period
- Company valuation metrics
- Company performance data
- Company information
- Historical price data exported as CSV

## Features

### Stock Price Data

Enter a ticker symbol and the number of calendar days to query. The application retrieves historical data from Yahoo Finance and displays the closing price trend. Because the period uses calendar days, the number of returned rows depends on the exchange trading calendar.

### Company Overview

The right-side panel displays company information and fundamental data, including:

- Price-to-earnings ratio (PE)
- Price-to-book ratio (PB)
- Dividend yield
- Market capitalization
- Total revenue
- Gross margin
- Profit margin
- Return on equity (ROE)
- Revenue growth
- Earnings growth
- Company name
- Industry and sector
- Country or region
- Company website
- Business summary

Some stocks may not provide complete fundamental data. Missing values are displayed as `N/A`.

### CSV Export

After a successful query, click the **Export CSV** button and choose a location to save the historical price data.

The exported data typically includes:

- Date
- Open price
- High price
- Low price
- Close price
- Adjusted close price
- Trading volume

## Requirements

- Python 3.10 or newer
- Internet access for retrieving data from Yahoo Finance
- Tkinter for displaying the GUI window

If Tkinter is not installed on Linux, install it with:

```bash
sudo apt install python3-tk
```

## Installation

Navigate to the project directory:

```bash
cd "/home/ming99/shiming/weekly_work/week 3"
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

To leave the virtual environment:

```bash
deactivate
```

## Start the GUI

Run the application with the Python interpreter from the virtual environment:

```bash
.venv/bin/python stock.py
```

Alternatively, activate the environment first and then run:

```bash
source .venv/bin/activate
python stock.py
```

After the window opens, enter a ticker symbol and the number of days, then click **Query**.

## Start the Web Version

The web version provides a login page and a browser-based stock query dashboard. Start it from the project directory:

```bash
.venv/bin/python web.py
```

Open `http://127.0.0.1:5000` in a browser and sign in with the default local account:

```text
Username: admin
Password: change-me
```

Set these environment variables before starting the server to use a different account and secret key:

```bash
export STOCK_WEB_USERNAME="your-name"
export STOCK_WEB_PASSWORD="your-password"
export STOCK_WEB_SECRET="a-long-random-secret"
.venv/bin/python web.py
```

The default server listens on the local computer only. To make it reachable from another device on the same network, set `STOCK_WEB_HOST=0.0.0.0` and use the computer's local IP address. Do not use the default password or Flask development server for a public deployment.

## Run the Docker Deployment

The Docker Compose deployment runs two Flask-SocketIO instances behind an Nginx
round-robin proxy, with shared PostgreSQL and Redis services. Redis carries
Socket.IO broadcasts between instances. Only Nginx is published to the host, on
port 80. PostgreSQL data is persisted in the `postgres_data` volume.

Set non-default credentials before starting the stack (or put them in a `.env`
file beside `docker-compose.yml`):

```bash
export STOCK_WEB_USERNAME="your-name"
export STOCK_WEB_PASSWORD="your-password"
export STOCK_WEB_SECRET="a-long-random-secret"
export POSTGRES_USER="stock_viewer"
export POSTGRES_PASSWORD="a-long-random-database-password"
export POSTGRES_DB="stock_viewer"
# Optional: enable Sentry error and performance reporting.
export SENTRY_DSN="https://your-sentry-dsn"
# Optional: sample a fraction of transactions, from 0 to 1 (default: 0).
export SENTRY_TRACES_SAMPLE_RATE="0.1"
docker compose up --build
```

Open `http://localhost/` to use the existing stock dashboard. After a successful
stock query, its latest price is pushed to the browser over a WebSocket; the
browser does not poll the web API. The page loads the Socket.IO browser client
from its CDN. The server fetches Yahoo Finance 1-minute intraday data every 60
seconds by default. The upstream data's availability and latency depend on
Yahoo Finance; set `STOCK_UPDATE_INTERVAL` to change the server-side refresh
interval.

Set `SENTRY_DSN` to enable Sentry error tracking (and optionally set
`SENTRY_TRACES_SAMPLE_RATE` for transaction performance traces). Sentry is
disabled when no DSN is configured. Identify the instance serving a request
with `http://localhost/api/hello`. `/healthz` is a lightweight health endpoint,
and `/db-test` writes and reads a test row in PostgreSQL. Nginx uses passive
upstream failure checks, while Docker health checks gate startup until the
database, Redis, and both app instances are ready.

Stop the services with `Ctrl+C`, or run `docker compose down`. The database
volume remains after stopping; `docker compose down -v` also deletes its stored
data.

## Ticker Symbol Formats

Common examples:

| Market | Example |
| --- | --- |
| United States | `AAPL` |
| Hong Kong | `0700.HK` |
| Hong Kong | `HKG: 1810` |
| Shanghai | `600519.SS` |
| Shenzhen | `000001.SZ` |

Hong Kong stocks can also be entered with a market prefix:

```text
HKG: 1810
```

The application automatically converts it to:

```text
1810.HK
```

## Command-Line Mode

The default mode is the GUI. Add `--cli` to use command-line mode:

```bash
.venv/bin/python stock.py --cli AAPL --days 30
```

Command-line arguments:

| Argument | Description | Example |
| --- | --- | --- |
| `ticker` | Ticker symbol | `AAPL` |
| `--cli` | Use command-line mode | `--cli` |
| `--days` | Number of calendar days to query | `--days 30` |
| `--currency` | Manually specify a currency code | `--currency USD` |
| `--output` | Save the trend chart to an image file | `--output aapl.png` |

For example, query Tencent and save the chart:

```bash
.venv/bin/python stock.py --cli 0700.HK --days 365 --output tencent.png
```

Specify a currency:

```bash
.venv/bin/python stock.py --cli AAPL --days 90 --currency USD --output aapl.png
```

## Running in VS Code

1. Open the Command Palette with `Ctrl+Shift+P`.
2. Select `Python: Select Interpreter`.
3. Select the project interpreter:

```text
/home/ming99/shiming/weekly_work/week 3/.venv/bin/python
```

4. Open `stock.py`.
5. Click the Run button, or execute this command in the terminal:

```bash
.venv/bin/python stock.py
```

## Troubleshooting

### 1. yfinance or matplotlib cannot be found

Make sure that VS Code is using the project virtual environment, then run:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

You can also check the dependencies with:

```bash
.venv/bin/python -m pip check
```

### 2. The query fails or returns no data

Possible causes include:

- Incorrect ticker symbol format
- Network connection failure
- Temporary request limits from Yahoo Finance
- The stock has been delisted
- No data is available for the selected market

You can test the application with common symbols first:

```text
AAPL
0700.HK
1810.HK
```

### 3. The GUI font or window size looks incorrect

The application includes high-DPI support and allows the window to be resized. Start it with the virtual environment interpreter:

```bash
.venv/bin/python stock.py
```

### 4. The GUI does not start on Linux

Make sure that Tkinter is installed:

```bash
sudo apt install python3-tk
```

## Run Tests

Run the offline unit tests from the project directory:

```bash
.venv/bin/python -m unittest -v test_stock.py
```

## Project Files

```text
week 3/
├── stock.py
├── web.py
├── test_stock.py
├── test_web.py
├── templates/
├── static/
├── web/
│   ├── Dockerfile
│   └── app.py
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── requirements.txt
├── README.md
└── .venv/
```

`.venv/` is the local virtual environment directory and usually should not be committed to a Git repository.

## Notes

- Stock data is provided by Yahoo Finance for learning and informational purposes only.
- Data may be delayed and does not necessarily represent real-time prices.
- Company fundamental data may be incomplete or delayed.
- This application does not provide investment advice.
# week-5
# week6-stock
