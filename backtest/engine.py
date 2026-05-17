"""
backtest/engine.py — Backtesting Engine

รัน: python -m backtest.engine
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from binance.um_futures import UMFutures

from config.settings import (
    SYMBOL, TIMEFRAME, BACKTEST_DAYS, INITIAL_CAPITAL,
    EMA_FAST, EMA_SLOW, EMA_TREND, LEVERAGE
)
from utils.helpers import get_client, fetch_ohlcv, add_indicators, get_logger
from strategies.ema_crossover import EMAStrategy, Signal


logger = get_logger("Backtest")


class BacktestEngine:
    def __init__(self, df: pd.DataFrame, initial_capital: float = INITIAL_CAPITAL):
        self.df      = df.copy()
        self.capital = initial_capital
        self.equity  = initial_capital
        self.trades  = []
        self.equity_curve = []
        self.strategy = EMAStrategy()

    def run(self) -> dict:
        logger.info(f"▶ เริ่ม Backtest | {len(self.df)} candles | Capital: ${self.capital:,.0f}")

        for i in range(EMA_SLOW + 5, len(self.df)):
            window = self.df.iloc[:i+1]
            last   = window.iloc[-1]
            price  = last["close"]

            signal = self.strategy.generate_signal(window)

            # ── Exit ──────────────────────────────────────────────────────
            if signal == Signal.CLOSE and self.strategy.position:
                result = self.strategy.close_position(price)
                self.equity += result["pnl_usdt"]
                result["equity"] = self.equity
                result["timestamp"] = window.index[-1]
                self.trades.append(result)
                logger.debug(
                    f"  CLOSE {result['side']} @ {price:.1f} | "
                    f"PnL: {result['pnl_pct']*100:.2f}% | "
                    f"Equity: ${self.equity:,.2f}"
                )

            # ── Entry ─────────────────────────────────────────────────────
            elif signal in (Signal.LONG, Signal.SHORT) and not self.strategy.position:
                pos = self.strategy.open_position(signal.value, price, self.equity)
                logger.debug(
                    f"  OPEN {signal.value} @ {price:.1f} | "
                    f"Qty: {pos.quantity} | SL: {pos.sl_price:.1f} | TP: {pos.tp_price:.1f}"
                )

            self.equity_curve.append({
                "timestamp": window.index[-1],
                "equity":    self.equity,
                "price":     price,
                "position":  self.strategy.position.side if self.strategy.position else None
            })

        return self._summary()

    def _summary(self) -> dict:
        if not self.trades:
            return {"error": "ไม่มี trades ใน backtest period"}

        df_trades = pd.DataFrame(self.trades)
        wins      = df_trades[df_trades["pnl_usdt"] > 0]
        losses    = df_trades[df_trades["pnl_usdt"] <= 0]

        total_return   = (self.equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
        win_rate       = len(wins) / len(df_trades) * 100
        avg_win        = wins["pnl_pct"].mean() * 100 if len(wins) else 0
        avg_loss       = losses["pnl_pct"].mean() * 100 if len(losses) else 0
        profit_factor  = (wins["pnl_usdt"].sum() / abs(losses["pnl_usdt"].sum())
                          if len(losses) and losses["pnl_usdt"].sum() != 0 else float("inf"))

        # Max Drawdown
        equity_vals = [e["equity"] for e in self.equity_curve]
        peak        = INITIAL_CAPITAL
        max_dd      = 0.0
        for eq in equity_vals:
            peak  = max(peak, eq)
            dd    = (peak - eq) / peak
            max_dd = max(max_dd, dd)

        # Sharpe Ratio (simplified, annualized)
        returns   = df_trades["pnl_pct"].values
        sharpe    = (returns.mean() / returns.std() * np.sqrt(252)
                     if returns.std() > 0 else 0)

        summary = {
            "period_days":       BACKTEST_DAYS,
            "total_trades":      len(df_trades),
            "winning_trades":    len(wins),
            "losing_trades":     len(losses),
            "win_rate_pct":      round(win_rate, 2),
            "initial_capital":   INITIAL_CAPITAL,
            "final_equity":      round(self.equity, 2),
            "total_return_pct":  round(total_return, 2),
            "avg_win_pct":       round(avg_win, 3),
            "avg_loss_pct":      round(avg_loss, 3),
            "profit_factor":     round(profit_factor, 2),
            "max_drawdown_pct":  round(max_dd * 100, 2),
            "sharpe_ratio":      round(sharpe, 2),
        }

        # ─── Print Report ─────────────────────────────────────────────────
        print("\n" + "═" * 52)
        print(f"  📊  BACKTEST REPORT — {SYMBOL} {TIMEFRAME}")
        print("═" * 52)
        print(f"  Period         : {BACKTEST_DAYS} days")
        print(f"  Total trades   : {summary['total_trades']}")
        print(f"  Win rate       : {summary['win_rate_pct']:.1f}%")
        print(f"  Profit factor  : {summary['profit_factor']:.2f}")
        print(f"  Sharpe ratio   : {summary['sharpe_ratio']:.2f}")
        print(f"  Max drawdown   : {summary['max_drawdown_pct']:.1f}%")
        print(f"  Avg win / loss : +{summary['avg_win_pct']:.2f}% / {summary['avg_loss_pct']:.2f}%")
        print("─" * 52)
        print(f"  Initial        : ${summary['initial_capital']:>10,.2f}")
        print(f"  Final equity   : ${summary['final_equity']:>10,.2f}")
        print(f"  Total return   : {summary['total_return_pct']:>+.2f}%")
        print("═" * 52 + "\n")

        # บันทึก trades ลงไฟล์
        df_trades.to_csv("backtest/trades_result.csv", index=False)
        pd.DataFrame(self.equity_curve).to_csv("backtest/equity_curve.csv", index=False)
        print("  💾 บันทึกผลไว้ที่ backtest/trades_result.csv\n")

        return summary


if __name__ == "__main__":
    print(f"📡 กำลังดึงข้อมูล {SYMBOL} {TIMEFRAME} ย้อนหลัง {BACKTEST_DAYS} วัน...")
    client = get_client()
    df     = fetch_ohlcv(client, SYMBOL, TIMEFRAME, BACKTEST_DAYS)
    df     = add_indicators(df, EMA_FAST, EMA_SLOW, EMA_TREND)

    print(f"   ได้ {len(df)} candles ({df.index[0].date()} → {df.index[-1].date()})")

    engine = BacktestEngine(df)
    engine.run()
