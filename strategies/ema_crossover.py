"""
strategies/ema_crossover.py — Trend-Following Strategy (1h + 4h)
ปรับใหม่: ใช้ 1h เป็น entry, 4h เป็น trend filter
เน้น quality over quantity — trade น้อยลง แต่ชัวร์กว่า
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

    def generate_signal(self, df: pd.DataFrame,
                        df_htf: pd.DataFrame = None) -> Signal:
        if len(df) < EMA_TREND + 5:
            return Signal.HOLD

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if self.position:
            if self._check_exit(last, prev) == Signal.CLOSE:
                return Signal.CLOSE

        if not self.position:
            return self._check_entry(prev, last, df, df_htf)

        return Signal.HOLD

    # ─── Entry Logic ────────────────────────────────────────────────────

    def _check_entry(self, prev: pd.Series, last: pd.Series,
                     df: pd.DataFrame,
                     df_htf: pd.DataFrame = None) -> Signal:

        fast  = f"ema_{EMA_FAST}"
        slow  = f"ema_{EMA_SLOW}"
        trend = f"ema_{EMA_TREND}"

        # ── HTF Trend Filter (4h) ──────────────────────────────────────
        # 4h ต้องบอกทิศทางชัดเจน ก่อน entry ใน 1h
        htf_bull = True
        htf_bear = True

        if df_htf is not None and len(df_htf) >= 3:
            h = df_htf.iloc[-2]   # แท่ง 4h ปิดล่าสุด

            # Bull: ราคาอยู่เหนือ EMA50 และ EMA9 > EMA21 ใน 4h
            htf_bull = (
                h["close"] > h[trend] and
                h[fast]    > h[slow]  and
                h[fast]    > h[trend]
            )
            # Bear: ราคาอยู่ต่ำกว่า EMA50 และ EMA9 < EMA21 ใน 4h
            htf_bear = (
                h["close"] < h[trend] and
                h[fast]    < h[slow]  and
                h[fast]    < h[trend]
            )

        # ── Volatility Filter ──────────────────────────────────────────
        # ATR ต้องมีขนาดพอสมควร (ตลาดต้องมี movement)
        min_atr = prev["close"] * 0.0012   # 0.12% ของราคา
        if prev["atr"] < min_atr:
            return Signal.HOLD

        # ── Volume Filter ──────────────────────────────────────────────
        if not (prev["volume"] > prev["vol_ma"] and
                prev["volume"] * prev["close"] > MIN_VOLUME_USDT):
            return Signal.HOLD

        # ── EMA Spread Filter (หลีกเลี่ยง choppy) ─────────────────────
        # EMA9 ต้องห่างจาก EMA21 พอสมควร
        spread = abs(prev[fast] - prev[slow]) / prev["close"]
        if spread < 0.0005:
            return Signal.HOLD

        # ── LONG Setup ─────────────────────────────────────────────────
        # 1. EMA9 ตัดขึ้น EMA21 (cross up)
        # 2. ราคาและ EMA9 อยู่เหนือ EMA50
        # 3. RSI ยืนเหนือ 50 (momentum เป็นบวก)
        # 4. 4h เป็น uptrend
        # 5. Candle ปิดเป็นบวก (momentum ยืนยัน)
        long_ok = (
            prev["cross_up"]             and
            prev["close"] > prev[trend]  and
            prev[fast]    > prev[trend]  and
            prev["rsi"] > 50             and
            prev["close"] > prev["open"] and   # bullish candle
            htf_bull
        )

        # ── SHORT Setup ────────────────────────────────────────────────
        short_ok = (
            prev["cross_down"]           and
            prev["close"] < prev[trend]  and
            prev[fast]    < prev[trend]  and
            prev["rsi"] < 50             and
            prev["close"] < prev["open"] and   # bearish candle
            htf_bear
        )

        if long_ok:
            return Signal.LONG
        if short_ok:
            return Signal.SHORT
        return Signal.HOLD

    # ─── Exit Logic ─────────────────────────────────────────────────────

    def _check_exit(self, last: pd.Series, prev: pd.Series) -> Signal:
        pos   = self.position
        price = last["close"]

        if pos.side == "LONG":
            # Hard TP/SL
            if price >= pos.tp_price:
                return Signal.CLOSE
            if price <= pos.sl_price:
                return Signal.CLOSE

            # Trailing Stop (เริ่มหลังกำไร 0.8%)
            if TRAILING_STOP:
                pos.highest_price = max(pos.highest_price, price)
                if price > pos.entry_price * 1.008:
                    trail = pos.highest_price * (1 - TRAILING_DELTA)
                    if price <= trail:
                        return Signal.CLOSE

            # EMA reversal (EMA cross กลับด้าน)
            if prev["cross_down"]:
                return Signal.CLOSE

        elif pos.side == "SHORT":
            if price <= pos.tp_price:
                return Signal.CLOSE
            if price >= pos.sl_price:
                return Signal.CLOSE

            if TRAILING_STOP:
                pos.lowest_price = min(pos.lowest_price, price)
                if price < pos.entry_price * 0.992:
                    trail = pos.lowest_price * (1 + TRAILING_DELTA)
                    if price >= trail:
                        return Signal.CLOSE

            if prev["cross_up"]:
                return Signal.CLOSE

        return Signal.HOLD

    # ─── Position Sizing ────────────────────────────────────────────────

    def open_position(self, side: str, entry_price: float,
                      balance: float, atr: float = 0.0) -> Position:
        """ATR-based SL/TP dengan RR 1:2"""
        if atr and atr > 0:
            sl_pct = (atr * ATR_MULTIPLIER) / entry_price
            # SL range 0.8% ~ 2.0%
            sl_pct = max(0.008, min(sl_pct, 0.020))
            tp_pct = sl_pct * 2.0   # RR 1:2
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
        pnl_pct = (
            (exit_price - pos.entry_price) / pos.entry_price
            if pos.side == "LONG" else
            (pos.entry_price - exit_price) / pos.entry_price
        )
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
        pos.pnl_pct = (
            (current_price - pos.entry_price) / pos.entry_price
            if pos.side == "LONG" else
            (pos.entry_price - current_price) / pos.entry_price
        )
        return pos.pnl_pct