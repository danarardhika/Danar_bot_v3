"""
utils.py - Utility functions: fetch stock data, format messages, normalize ticker
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

WIB = pytz.timezone("Asia/Jakarta")

PERIOD_MAP = {
    "1w": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
    "2y": "2y",
}

PERIOD_LABEL = {
    "5d": "1 Minggu",
    "1mo": "1 Bulan",
    "3mo": "3 Bulan",
    "6mo": "6 Bulan",
    "1y": "1 Tahun",
    "2y": "2 Tahun",
}


def normalize_ticker(ticker: str) -> str:
    """Normalize IDX ticker: BBCA -> BBCA.JK"""
    ticker = ticker.upper().strip()
    if "." not in ticker and len(ticker) <= 6:
        return ticker + ".JK"
    return ticker


def fetch_stock_data(ticker: str, period: str = "3mo") -> pd.DataFrame:
    """
    Download OHLCV data dari Yahoo Finance.
    Period: 5d, 1mo, 3mo, 6mo, 1y, 2y
    """
    try:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval="1d", auto_adjust=True)
        if df.empty:
            logger.warning(f"Data kosong untuk {ticker}")
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    """Get stock info dari Yahoo Finance"""
    try:
        tk = yf.Ticker(ticker)
        return tk.info or {}
    except Exception:
        return {}


def format_large_number(n) -> str:
    if n is None:
        return "N/A"
    try:
        n = float(n)
        if n >= 1e12:
            return f"{n/1e12:.2f}T"
        if n >= 1e9:
            return f"{n/1e9:.2f}B"
        if n >= 1e6:
            return f"{n/1e6:.2f}M"
        return f"{n:,.0f}"
    except Exception:
        return "N/A"


def now_wib() -> str:
    return datetime.now(WIB).strftime("%d/%m/%Y %H:%M WIB")


def format_price(price: float) -> str:
    return f"Rp{price:,.0f}".replace(',', '.')
