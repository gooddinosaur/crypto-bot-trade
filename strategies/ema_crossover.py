"""
strategies/ema_crossover.py — EMA Triple Crossover Strategy (Balanced)
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
        if len(df) < 5:
            return Signal.HOLD

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if self.position:
            close_signal = self._check_exit(last, prev)
            if close_signal == Signal.CLOSE:
                return Signal.CLOSE

        if not self.position:
            return self._check_entry(prev, last, df, df_htf)

        return Signal.HOLD

    def _check_entry(self, prev: pd.Series, last: pd.Series,
                     df: pd.DataFrame,
                     df_htf: pd.DataFrame = None) -> Signal:
        fast  = f"ema_{EMA_FAST}"
        slow  = f"ema_{EMA_SLOW}"
        trend = f"ema_{EMA_TREND}"

        # ── 1. Higher Timeframe trend filter (1h) ─────────────────────
        htf_trend_up   = True
        htf_trend_down = True

        if df_htf is not None and len(df_htf) >= 2:
            htf = df_htf.iloc[-2]
            htf_trend_up   = (htf[fast] > htf[slow] and
                              htf["close"] > htf[trend])
            htf_trend_down = (htf[fast] < htf[slow] and
                              htf["close"] < htf[trend])

        # ── 2. ATR filter ─────────────────────────────────────────────
        atr_threshold = prev["close"] * 0.0008
        if prev["atr"] < atr_threshold:
            return Signal.HOLD

        # ── 3. Volume filter ──────────────────────────────────────────
        vol_ok = (
            prev["volume"] > prev["vol_ma"] and
            prev["volume"] * prev["close"] > MIN_VOLUME_USDT
        )
        if not vol_ok:
            return Signal.HOLD

        # ── 4. EMA gap — หลีกเลี่ยง sideways ─────────────────────────
        ema_gap = abs(prev[fast] - prev[slow]) / prev["close"]
        if ema_gap < 0.0003:
            return Signal.HOLD

        # ── 5. LONG conditions ────────────────────────────────────────
        long_ok = (
            prev["cross_up"] and
            prev["close"] > prev[trend] and
            prev[fast] > prev[trend] and
            30 < prev["rsi"] < 68 and
            htf_trend_up
        )

        # ── 6. SHORT conditions ───────────────────────────────────────
        short_ok = (
            prev["cross_down"] and
            prev["close"] < prev[trend] and
            prev[fast] < prev[trend] and
            32 < prev["rsi"] < 70 and
            htf_trend_down
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
                if price <= trail_sl and price > pos.entry_price * 1.005:
                    return Signal.CLOSE
            if prev["cross_down"]:
                return Signal.CLOSE
            if last["rsi"] > 80:
                return Signal.CLOSE

        elif pos.side == "SHORT":
            if price <= pos.tp_price:
                return Signal.CLOSE
            if price >= pos.sl_price:
                return Signal.CLOSE
            if TRAILING_STOP:
                pos.lowest_price = min(pos.lowest_price, price)
                trail_sl = pos.lowest_price * (1 + TRAILING_DELTA)
                if price >= trail_sl and price < pos.entry_price * 0.995:
                    return Signal.CLOSE
            if prev["cross_up"]:
                return Signal.CLOSE
            if last["rsi"] < 20:
                return Signal.CLOSE

        return Signal.HOLD

    # ─── Position Management ────────────────────────────────────────────

    def open_position(self, side: str, entry_price: float,
                      balance: float, atr: float = 0.0) -> Position:
        if atr and atr > 0:
            sl_dist = atr * ATR_MULTIPLIER
            tp_dist = atr * ATR_MULTIPLIER * 2.0
            sl_pct  = sl_dist / entry_price
            sl_pct  = max(0.005, min(sl_pct, 0.018))
            tp_pct  = sl_pct * 2.0
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