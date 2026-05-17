"""
strategies/ema_crossover.py — EMA Triple Crossover Strategy

กลยุทธ์:
  LONG  → EMA fast ตัดขึ้น EMA slow + price > EMA trend + RSI < 70 + Volume สูง
  SHORT → EMA fast ตัดลง EMA slow + price < EMA trend + RSI > 30 + Volume สูง

Exit:
  - Take Profit (fixed %)
  - Stop Loss   (fixed %)
  - Trailing Stop (ถ้าเปิดใช้)
  - EMA cross กลับด้าน
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import pandas as pd

from config.settings import (
    EMA_FAST, EMA_SLOW, EMA_TREND,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    TRAILING_STOP, TRAILING_DELTA,
    MIN_VOLUME_USDT, RISK_PER_TRADE,
    MAX_POSITION_PCT, LEVERAGE
)
from utils.helpers import add_indicators, calculate_position_size


class Signal(Enum):
    LONG  = "LONG"
    SHORT = "SHORT"
    HOLD  = "HOLD"
    CLOSE = "CLOSE"


@dataclass
class Position:
    side:          str            # "LONG" | "SHORT"
    entry_price:   float
    quantity:      float
    sl_price:      float
    tp_price:      float
    highest_price: float = 0.0   # สำหรับ trailing stop (LONG)
    lowest_price:  float = 0.0   # สำหรับ trailing stop (SHORT)
    pnl_pct:       float = 0.0

    def __post_init__(self):
        self.highest_price = self.entry_price
        self.lowest_price  = self.entry_price


class EMAStrategy:
    """
    Triple EMA Crossover + RSI filter + Volume filter
    """

    def __init__(self):
        self.position: Optional[Position] = None

    # ─── Signal Generation ──────────────────────────────────────────────────

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """
        วิเคราะห์ DataFrame ล่าสุด และส่งคืน Signal
        df ต้องผ่าน add_indicators() มาแล้ว
        """
        if len(df) < 3:
            return Signal.HOLD

        last  = df.iloc[-1]   # แท่งปัจจุบัน (ยังไม่ปิด)
        prev  = df.iloc[-2]   # แท่งก่อนหน้า (ปิดแล้ว ← ใช้สร้าง signal)

        # ── ถ้ามี position อยู่ → เช็ค exit ก่อน ──────────────────────────
        if self.position:
            close_signal = self._check_exit(last, prev)
            if close_signal == Signal.CLOSE:
                return Signal.CLOSE

        # ── ยังไม่มี position → หา entry ──────────────────────────────────
        if not self.position:
            return self._check_entry(prev, last)

        return Signal.HOLD

    def _check_entry(self, prev: pd.Series, last: pd.Series) -> Signal:
        fast  = f"ema_{EMA_FAST}"
        slow  = f"ema_{EMA_SLOW}"
        trend = f"ema_{EMA_TREND}"

        # Volume filter: ต้องสูงกว่า MA และเกิน minimum
        vol_ok = (
            prev["volume"] > prev["vol_ma"] and
            prev["volume"] * prev["close"] > MIN_VOLUME_USDT
        )
        if not vol_ok:
            return Signal.HOLD

        # LONG conditions
        long_ok = (
            prev["cross_up"] and
            prev["close"] > prev[trend] and
            30 < prev["rsi"] < 65     # จาก < 70 → เข้าเฉพาะก่อน overbought
        )

        # SHORT conditions
        short_ok = (
            prev["cross_down"] and
            prev["close"] < prev[trend] and
            35 < prev["rsi"] < 70    # จาก > 30 → เข้าเฉพาะก่อน oversold
        )

        if long_ok:
            return Signal.LONG
        if short_ok:
            return Signal.SHORT
        return Signal.HOLD

    def _check_exit(self, last: pd.Series, prev: pd.Series) -> Signal:
        """ตรวจสอบเงื่อนไข exit"""
        pos   = self.position
        price = last["close"]

        if pos.side == "LONG":
            # Take Profit
            if price >= pos.tp_price:
                return Signal.CLOSE
            # Stop Loss
            if price <= pos.sl_price:
                return Signal.CLOSE
            # Trailing Stop
            if TRAILING_STOP:
                pos.highest_price = max(pos.highest_price, price)
                trail_sl = pos.highest_price * (1 - TRAILING_DELTA)
                if price <= trail_sl and price > pos.entry_price:
                    return Signal.CLOSE
            # EMA reversal
            if prev["cross_down"]:
                return Signal.CLOSE

        elif pos.side == "SHORT":
            if price <= pos.tp_price:
                return Signal.CLOSE
            if price >= pos.sl_price:
                return Signal.CLOSE
            if TRAILING_STOP:
                pos.lowest_price = min(pos.lowest_price, price)
                trail_sl = pos.lowest_price * (1 + TRAILING_DELTA)
                if price >= trail_sl and price < pos.entry_price:
                    return Signal.CLOSE
            if prev["cross_up"]:
                return Signal.CLOSE

        return Signal.HOLD

    # ─── Position Management ────────────────────────────────────────────────

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
            "side":        pos.side,
            "entry":       pos.entry_price,
            "exit":        exit_price,
            "quantity":    pos.quantity,
            "pnl_pct":     pnl_pct,
            "pnl_usdt":    pnl_pct * pos.entry_price * pos.quantity * LEVERAGE,
        }
        self.position = None
        return result

    def update_pnl(self, current_price: float) -> float:
        """คำนวณ unrealized PnL (%)"""
        if not self.position:
            return 0.0
        pos = self.position
        if pos.side == "LONG":
            pos.pnl_pct = (current_price - pos.entry_price) / pos.entry_price
        else:
            pos.pnl_pct = (pos.entry_price - current_price) / pos.entry_price
        return pos.pnl_pct