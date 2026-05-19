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

        # ── HTF Trend Filter (15m) ──────────────────────────────────────
        # ให้กรองแค่ว่า EMA9 ตัด EMA21 หรือเปล่าพอ จะได้ไม่ตึงเกินไป
        htf_bull = True
        htf_bear = True

        if df_htf is not None and len(df_htf) >= 3:
            h = df_htf.iloc[-2]   # แท่งก่อนหน้าปิดล่าสุด

            # ใช้ Trend filter จริงๆ (EMA 21 และ 50) เพื่อลด noise
            htf_bull = (h[fast] > h[slow]) and (h["close"] > h[trend])
            htf_bear = (h[fast] < h[slow]) and (h["close"] < h[trend])

        # ── Volume & ATR Filter (ปิดชั่วคราวเพื่อให้เทรดถี่) ────────────
        # (เราเอาเงื่อนไข filter ที่ตึงเกินไปออกทั้งหมด เพื่อจำลอง day trade เต็มรูปแบบ)

        # ── LONG Setup ─────────────────────────────────────────────────
        # 1) Entry จาก Crossover
        long_cross = (
            prev["cross_up"]             and
            prev["close"] > prev[trend]  and
            prev[fast]    > prev[trend]  and
            prev["rsi"] > 50             and
            htf_bull
        )

        # 2) Entry จาก Pullback (ราคาอยู่อัพเทรน ซึมลงมาแตะ EMA ช้า แล้วเด้งกลับ)
        long_pullback = (
            not prev["cross_up"] and  # ไม่ใช่จังหวะตัดกันพอดี
            (prev[fast] > prev[slow] > prev[trend]) and # เป็นขาขึ้นชัดเจน
            (prev["low"] <= prev[slow]) and # ราคาลงมาแตะหรือหลุดเส้น EMA21
            (prev["close"] > prev[fast]) and # สร้างแท่งเทียนกลับตัวทะลุ EMA9 กลับขึ้นไป!
            (prev["close"] > prev["open"]) and # แท่งเทียนเป็นสีเขียว
            (prev["rsi"] > 50) and # มีแรงซื้อ
            htf_bull
        )

        long_ok = long_cross or long_pullback

        # ── SHORT Setup ────────────────────────────────────────────────
        # 1) Entry จาก Crossover
        short_cross = (
            prev["cross_down"]           and
            prev["close"] < prev[trend]  and
            prev[fast]    < prev[trend]  and
            prev["rsi"] < 50             and
            htf_bear
        )

        # 2) Entry จาก Pullback (ราคาอยู่ดาวน์เทรน เด้งขึ้นมาแตะ EMA ช้า แล้วโดนตบลง)
        short_pullback = (
            not prev["cross_down"] and
            (prev[fast] < prev[slow] < prev[trend]) and
            (prev["high"] >= prev[slow]) and
            (prev["close"] < prev[fast]) and # แท่งเทียนกลับตัวทะลุ EMA9 ลงไป
            (prev["close"] < prev["open"]) and
            (prev["rsi"] < 50) and
            htf_bear
        )

        short_ok = short_cross or short_pullback

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
        
        # 1. คำนวณ PnL แบบดิบๆ (ยังไม่หัก Fee)
        gross_pnl_pct = (
            (exit_price - pos.entry_price) / pos.entry_price
            if pos.side == "LONG" else
            (pos.entry_price - exit_price) / pos.entry_price
        )
        gross_pnl_usdt = gross_pnl_pct * pos.entry_price * pos.quantity

        # 2. คำนวณค่าธรรมเนียม (สมมติเหมาจ่ายทั้งเข้า-ออก รวมแล้วประมาณ 0.08% หรือ 0.0008)
        # - ถ้าคุณใช้ Limit สองฝั่ง ค่า Fee ประมาณ 0.04% (0.0004)
        # - ถ้าคุณใช้ Market สองฝั่ง ค่า Fee ประมาณ 0.10% (0.0010)
        # ลองตั้งค่ากลางๆ ไว้ที่ 0.04% ก่อน
        FEE_RATE = 0.0004
        total_fee = (pos.entry_price * pos.quantity * FEE_RATE) + (exit_price * pos.quantity * FEE_RATE)
        
        # 3. หักลบค่าธรรมเนียมออกจากกำไร/ขาดทุน
        net_pnl_usdt = gross_pnl_usdt - total_fee
        
        # ปรับกลับเป็นเปอเซ็นต์ PnL สุทธิ เพื่อให้ Report แสดงได้ถูกต้อง
        net_pnl_pct = net_pnl_usdt / (pos.entry_price * pos.quantity)

        result = {
            "side":     pos.side,
            "entry":    pos.entry_price,
            "exit":     exit_price,
            "quantity": pos.quantity,
            "pnl_pct":  net_pnl_pct,      # ใช้ net (หัก fee แล้ว)
            "pnl_usdt": net_pnl_usdt,     # ใช้ net (หัก fee แล้ว)
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