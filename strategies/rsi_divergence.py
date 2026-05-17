"""
strategies/rsi_divergence.py — RSI Divergence Strategy

กลยุทธ์:
  LONG  → RSI oversold (< 35) + RSI กลับขึ้น + price > EMA200 (trend filter)
  SHORT → RSI overbought (> 65) + RSI กลับลง + price < EMA200

Exit:
  - Take Profit (fixed %)
  - Stop Loss   (fixed %)
  - Trailing Stop
  - RSI กลับด้าน
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
import numpy as np

from config.settings import (
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    TRAILING_STOP, TRAILING_DELTA,
    MIN_VOLUME_USDT, RISK_PER_TRADE,
    MAX_POSITION_PCT, LEVERAGE
)
from utils.helpers import calculate_position_size

# ─── RSI Thresholds ──────────────────────────────
RSI_OVERSOLD    = 35   # ซื้อเมื่อ RSI ต่ำกว่านี้แล้วกลับขึ้น
RSI_OVERBOUGHT  = 65   # ขายเมื่อ RSI สูงกว่านี้แล้วกลับลง
RSI_EXIT_LONG   = 60   # ปิด LONG เมื่อ RSI ขึ้นมาถึง
RSI_EXIT_SHORT  = 40   # ปิด SHORT เมื่อ RSI ลงมาถึง
EMA_TREND       = 200  # trend filter


class Signal(Enum):
    LONG  = "LONG"
    SHORT = "SHORT"
    HOLD  = "HOLD"
    CLOSE = "CLOSE"


@dataclass
class Position:
    side:          str
    entry_price:   float
    quantity:      float
    sl_price:      float
    tp_price:      float
    highest_price: float = 0.0
    lowest_price:  float = 0.0
    pnl_pct:       float = 0.0

    def __post_init__(self):
        self.highest_price = self.entry_price
        self.lowest_price  = self.entry_price


class RSIDivergenceStrategy:
    def __init__(self):
        self.position: Optional[Position] = None

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        if len(df) < 5:
            return Signal.HOLD

        # ใช้แท่งที่ปิดแล้ว
        p1 = df.iloc[-2]   # แท่งล่าสุดที่ปิดแล้ว
        p2 = df.iloc[-3]   # แท่งก่อนหน้า

        if self.position:
            if self._check_exit(p1, p2) == Signal.CLOSE:
                return Signal.CLOSE

        if not self.position:
            return self._check_entry(p1, p2)

        return Signal.HOLD

    def _check_entry(self, p1: pd.Series, p2: pd.Series) -> Signal:
        # Volume filter
        vol_ok = (
            p1["volume"] > p1["vol_ma"] and
            p1["volume"] * p1["close"] > MIN_VOLUME_USDT
        )
        if not vol_ok:
            return Signal.HOLD

        ema200 = p1.get(f"ema_{EMA_TREND}", p1["close"])

        # LONG: RSI เพิ่งออกจาก oversold (ต่ำแล้วกลับขึ้น)
        rsi_bounce_up = (
            p2["rsi"] < RSI_OVERSOLD and      # แท่งก่อนอยู่ใน oversold
            p1["rsi"] > p2["rsi"] and          # RSI กลับขึ้น
            p1["rsi"] < RSI_OVERSOLD + 10      # ยังไม่วิ่งไปไกล
        )
        long_ok = rsi_bounce_up and p1["close"] > ema200 * 0.995

        # SHORT: RSI เพิ่งออกจาก overbought (สูงแล้วกลับลง)
        rsi_drop_down = (
            p2["rsi"] > RSI_OVERBOUGHT and
            p1["rsi"] < p2["rsi"] and
            p1["rsi"] > RSI_OVERBOUGHT - 10
        )
        short_ok = rsi_drop_down and p1["close"] < ema200 * 1.005

        if long_ok:
            return Signal.LONG
        if short_ok:
            return Signal.SHORT
        return Signal.HOLD

    def _check_exit(self, p1: pd.Series, p2: pd.Series) -> Signal:
        pos   = self.position
        price = p1["close"]

        if pos.side == "LONG":
            if price >= pos.tp_price:
                return Signal.CLOSE
            if price <= pos.sl_price:
                return Signal.CLOSE
            if TRAILING_STOP:
                pos.highest_price = max(pos.highest_price, price)
                if price <= pos.highest_price * (1 - TRAILING_DELTA):
                    if price > pos.entry_price:
                        return Signal.CLOSE
            # RSI exit — RSI ขึ้นมาถึงเป้าแล้ว
            if p1["rsi"] > RSI_EXIT_LONG:
                return Signal.CLOSE

        elif pos.side == "SHORT":
            if price <= pos.tp_price:
                return Signal.CLOSE
            if price >= pos.sl_price:
                return Signal.CLOSE
            if TRAILING_STOP:
                pos.lowest_price = min(pos.lowest_price, price)
                if price >= pos.lowest_price * (1 + TRAILING_DELTA):
                    if price < pos.entry_price:
                        return Signal.CLOSE
            if p1["rsi"] < RSI_EXIT_SHORT:
                return Signal.CLOSE

        return Signal.HOLD

    def open_position(self, side: str, entry_price: float,
                      balance: float) -> Position:
        if side == "LONG":
            sl_price = entry_price * (1 - STOP_LOSS_PCT)
            tp_price = entry_price * (1 + TAKE_PROFIT_PCT)
        else:
            sl_price = entry_price * (1 + STOP_LOSS_PCT)
            tp_price = entry_price * (1 - TAKE_PROFIT_PCT)

        qty = calculate_position_size(
            balance, entry_price, sl_price,
            RISK_PER_TRADE, MAX_POSITION_PCT, LEVERAGE
        )

        self.position = Position(
            side=side, entry_price=entry_price,
            quantity=qty, sl_price=sl_price, tp_price=tp_price
        )
        return self.position

    def close_position(self, exit_price: float) -> dict:
        if not self.position:
            return {}

        pos = self.position
        if pos.side == "LONG":
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price

        result = {
            "side":     pos.side,
            "entry":    pos.entry_price,
            "exit":     exit_price,
            "quantity": pos.quantity,
            "pnl_pct":  pnl_pct,
            "pnl_usdt": pnl_pct * pos.entry_price * pos.quantity * LEVERAGE,
        }
        self.position = None
        return result

    def update_pnl(self, current_price: float) -> float:
        if not self.position:
            return 0.0
        pos = self.position
        if pos.side == "LONG":
            pos.pnl_pct = (current_price - pos.entry_price) / pos.entry_price
        else:
            pos.pnl_pct = (pos.entry_price - current_price) / pos.entry_price
        return pos.pnl_pct
