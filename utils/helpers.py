"""
utils/helpers.py — Logger, Binance client, Technical Indicators
"""
import logging
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from binance.um_futures import UMFutures
from config.settings import (
    API_KEY, API_SECRET, TESTNET, LOG_LEVEL, LOG_FILE
)


# ─── Logger ─────────────────────────────────────────────────────────────────

def get_logger(name: str = "BTCBot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL, logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File
    fh = logging.FileHandler(LOG_FILE)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ─── Binance Client ──────────────────────────────────────────────────────────

def get_client() -> UMFutures:
    """สร้าง Binance USD-M Futures client (testnet/live)"""
    base_url = (
        "https://testnet.binancefuture.com"
        if TESTNET else
        "https://fapi.binance.com"
    )
    return UMFutures(key=API_KEY, secret=API_SECRET, base_url=base_url)


# ─── Data Fetching ───────────────────────────────────────────────────────────

def fetch_ohlcv(client: UMFutures, symbol: str, interval: str,
                lookback_days: int = 5) -> pd.DataFrame:
    """
    ดึง OHLCV จาก Binance Futures
    Returns DataFrame columns: [open, high, low, close, volume]
    """
    limit = min(1500, lookback_days * 24 * 60 // _interval_minutes(interval))
    raw = client.klines(symbol=symbol, interval=interval, limit=limit)

    df = pd.DataFrame(raw, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df[["open", "high", "low", "close", "volume"]]


def _interval_minutes(interval: str) -> int:
    mapping = {"1m": 1, "3m": 3, "5m": 5, "15m": 15,
               "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
    return mapping.get(interval, 15)


# ─── Technical Indicators ────────────────────────────────────────────────────

def add_indicators(df: pd.DataFrame,
                   fast: int, slow: int, trend: int) -> pd.DataFrame:
    """
    เพิ่ม EMA, ATR, RSI, Volume MA ลงใน DataFrame
    """
    df = df.copy()

    # EMA
    df[f"ema_{fast}"]  = df["close"].ewm(span=fast,  adjust=False).mean()
    df[f"ema_{slow}"]  = df["close"].ewm(span=slow,  adjust=False).mean()
    df[f"ema_{trend}"] = df["close"].ewm(span=trend, adjust=False).mean()

    # ATR (Average True Range) — วัด volatility
    high_low   = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close  = (df["low"]  - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"]  = true_range.ewm(span=14, adjust=False).mean()

    # RSI (Relative Strength Index) — 14 period
    delta  = df["close"].diff()
    gain   = delta.clip(lower=0).ewm(span=14, adjust=False).mean()
    loss   = (-delta.clip(upper=0)).ewm(span=14, adjust=False).mean()
    rs     = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Volume MA
    df["vol_ma"] = df["volume"].rolling(20).mean()

    # Signals
    df["cross_up"]   = (
        (df[f"ema_{fast}"] > df[f"ema_{slow}"]) &
        (df[f"ema_{fast}"].shift() <= df[f"ema_{slow}"].shift())
    )
    df["cross_down"] = (
        (df[f"ema_{fast}"] < df[f"ema_{slow}"]) &
        (df[f"ema_{fast}"].shift() >= df[f"ema_{slow}"].shift())
    )

    return df.dropna()


# ─── Position Sizing ─────────────────────────────────────────────────────────

def calculate_position_size(balance: float, entry: float, sl_price: float,
                             risk_pct: float, max_pct: float,
                             leverage: int) -> float:
    """
    คำนวณจำนวน contract ที่จะเปิด
    - ใช้ fixed-fractional risk (risk X% ของ balance ต่อ trade)
    - จำกัด position ไม่เกิน max_pct ของ balance
    """
    risk_amount  = balance * risk_pct
    sl_distance  = abs(entry - sl_price) / entry   # % distance ถึง SL

    if sl_distance == 0:
        return 0.0

    # position value = risk / sl_distance (notional)
    position_value = risk_amount / sl_distance

    # จำกัดด้วย max position
    max_value      = balance * max_pct * leverage
    position_value = min(position_value, max_value)

    # แปลงเป็น BTC quantity
    qty = position_value / entry
    return round(qty, 3)


# ─── Price Helpers ───────────────────────────────────────────────────────────

def get_balance(client: UMFutures, asset: str = "USDT") -> float:
    """ดึง available balance จาก Futures wallet"""
    balances = client.balance()
    for b in balances:
        if b["asset"] == asset:
            return float(b["availableBalance"])
    return 0.0


def get_current_price(client: UMFutures, symbol: str) -> float:
    ticker = client.ticker_price(symbol=symbol)
    return float(ticker["price"])
