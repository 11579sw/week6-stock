import unittest
from unittest.mock import Mock, patch

import pandas as pd

import stock


class StockDataTests(unittest.TestCase):
    def test_normalize_hong_kong_symbol(self):
        self.assertEqual(stock.normalize_ticker_symbol(" hkg: 1810 "), "1810.HK")
        self.assertEqual(stock.normalize_ticker_symbol("aapl"), "AAPL")

    def test_fetch_rejects_invalid_period(self):
        with self.assertRaises(ValueError):
            stock.fetch_stock_data("AAPL", 0)

    @patch("stock.yf.Ticker")
    def test_fetch_returns_price_summary(self, ticker_factory):
        history = pd.DataFrame(
            {"Close": [10.0, 12.5, 11.0]},
            index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05"]),
        )
        ticker = Mock()
        ticker.history.return_value = history
        ticker.info = {"currency": "USD", "longName": "Example Corp"}
        ticker_factory.return_value = ticker

        result = stock.fetch_stock_data("aapl", period_days=30)

        self.assertEqual(result["ticker_symbol"], "AAPL")
        self.assertEqual(result["latest_price"], 11.0)
        self.assertEqual(result["max_price"], 12.5)
        self.assertEqual(result["min_price"], 10.0)
        ticker.history.assert_called_once()
        self.assertFalse(ticker.history.call_args.kwargs["auto_adjust"])

    @patch("stock.yf.Ticker")
    def test_fetch_latest_stock_price_returns_last_intraday_close(self, ticker_factory):
        history = pd.DataFrame(
            {"Close": [10.0, 12.5]},
            index=pd.to_datetime(["2026-01-05 10:00", "2026-01-05 10:01"]),
        )
        ticker = Mock()
        ticker.history.return_value = history
        ticker_factory.return_value = ticker

        result = stock.fetch_latest_stock_price("aapl")

        self.assertEqual(result["ticker_symbol"], "AAPL")
        self.assertEqual(result["price"], 12.5)
        self.assertEqual(result["market_time"], "2026-01-05T10:01:00")
        ticker.history.assert_called_once_with(
            period="1d",
            interval="1m",
            auto_adjust=False,
        )


if __name__ == "__main__":
    unittest.main()
