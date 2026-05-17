"""
strategies/ema_crossover.py — EMA Triple Crossover Strategy
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd
import numpy as np

from config.settings import (
    EMA_FAST, EMA_SLOW, EMA_TREND,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    TRAILING_STOP, TRAILING_DELTA,
    MIN_VOLUME_USDT, RISK_PER_TRADE,
    MAX_POSITION_PCT, LEVERAGE,
    ATR_MULTIPLIER
)
from utils.helpers import calculate_position_size


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


class EMAStrategy:

    def __init__(self):
        self.position: Optional[Position] = None

    # ─── Signal Generation ──────────────────────────────────────────────

    def generate_signal(self, df: pd.DataFrame, 
                        df_htf: pd.DataFrame = None) -> Signal:
        """
        df     = fast timeframe (15m) — ใช้ entry
        df_htf = slow timeframe (1h)  — ใช้กำหนดทิศทาง
        """
        if len(df) < 3:
            return Signal.HOLD

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if self.position:
            close_signal = self._check_exit(last, prev)
            if close_signal == Signal.CLOSE:
                return Signal.CLOSE

        if not self.position:
            return self._check_entry(prev, last, df_htf)

        return Signal.HOLD

    def _check_entry(self, prev: pd.Series, last: pd.Series,
                    df_htf: pd.DataFrame = None) -> Signal:
        fast  = f"ema_{EMA_FAST}"
        slow  = f"ema_{EMA_SLOW}"
        trend = f"ema_{EMA_TREND}"

        # ── Higher Timeframe trend filter ─────────────────────────────
        htf_trend_up   = True
        htf_trend_down = True

        if df_htf is not None and len(df_htf) >= 2:
            htf = df_htf.iloc[-2]   # แท่งปิดล่าสุดของ 1h
            htf_trend_up   = (htf["close"] > htf[trend] and 
                            htf[fast] > htf[slow])
            htf_trend_down = (htf["close"] < htf[trend] and 
                            htf[fast] < htf[slow])

        # ── ATR filter ────────────────────────────────────────────────
        atr_threshold = prev["close"] * 0.0008
        if prev["atr"] < atr_threshold:
            return Signal.HOLD

        # ── Volume filter ─────────────────────────────────────────────
        vol_ok = (
            prev["volume"] > prev["vol_ma"] and
            prev["volume"] * prev["close"] > MIN_VOLUME_USDT
        )
        if not vol_ok:
            return Signal.HOLD

        # ── LONG: 15m cross + 1h trend ขึ้น ──────────────────────────
        long_ok = (
            prev["cross_up"] and
            prev["close"] > prev[trend] and
            prev[fast] > prev[trend] and
            30 < prev["rsi"] < 65 and
            htf_trend_up                    # ← 1h ต้องเป็น uptrend
        )

        # ── SHORT: 15m cross + 1h trend ลง ───────────────────────────
        short_ok = (
            prev["cross_down"] and
            prev["close"] < prev[trend] and
            prev[fast] < prev[trend] and
            35 < prev["rsi"] < 70 and
            htf_trend_down                  # ← 1h ต้องเป็น downtrend
        )

        if long_ok:
            return Signal.LONG
        if short_ok:
            return Signal.SHORT
        return Signal.HOLD

    def _check_exit(self, last: pd.Series, prev: pd.Series) -> Signal:
        pos   = self.position
        price = last["close"]

        if pos.side == "LONG":
            if price >= pos.tp_price:
                return Signal.CLOSE
            if price <= pos.sl_price:
                return Signal.CLOSE
            if TRAILING_STOP:
                pos.highest_price = max(pos.highest_price, price)
                trail_sl = pos.highest_price * (1 - TRAILING_DELTA)
                if price <= trail_sl and price > pos.entry_price:
                    return Signal.CLOSE
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

    # ─── Position Management ────────────────────────────────────────────

    def open_position(self, side: str, entry_price: float,
                      balance: float, atr: float = 0.0) -> Position:
        """
        ATR-based SL/TP: ปรับ SL/TP ตาม volatility จริง
        Fallback เป็น fixed % ถ้าไม่มี ATR
        """
        if atr and atr > 0:
            # ATR_MULTIPLIER จาก settings (default 1.5)
            sl_dist = atr * ATR_MULTIPLIER          # SL = 1.5x ATR
            tp_dist = atr * ATR_MULTIPLIER * 2.0    # TP = 3.0x ATR (RR 1:2)
            sl_pct  = sl_dist / entry_price
            tp_pct  = tp_dist / entry_price

            # Cap ไม่ให้ SL กว้างเกินไป (max 2% และ min 0.3%)
            sl_pct = max(0.003, min(sl_pct, 0.02))
            tp_pct = sl_pct * 2.0   # รักษา RR 1:2 เสมอ
        else:
            sl_pct = STOP_LOSS_PCT
            tp_pct = TAKE_PROFIT_PCT

        if side == "LONG":
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
        else:
            sl_price = entry_price * (1 + sl_pct)
            tp_price = entry_price * (1 - tp_pct)

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