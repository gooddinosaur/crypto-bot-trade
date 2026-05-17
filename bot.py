"""
bot.py — Main Trading Bot Loop

รันด้วย:
  python bot.py             # live loop
  python bot.py --backtest  # backtest เท่านั้น
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import argparse
import traceback
from datetime import datetime

from config.settings import (
    SYMBOL, TIMEFRAME, LOOP_INTERVAL,
    EMA_FAST, EMA_SLOW, EMA_TREND,
    LEVERAGE, BACKTEST_DAYS, INITIAL_CAPITAL
)
from utils.helpers import (
    get_logger, get_client, fetch_ohlcv, add_indicators,
    get_balance, get_current_price
)
from strategies.ema_crossover import EMAStrategy, Signal


logger = get_logger("BOT")


class TradingBot:
    def __init__(self):
        self.client   = get_client()
        self.strategy = EMAStrategy()
        self._setup_leverage()

    def _setup_leverage(self):
        """ตั้ง leverage และ margin mode"""
        try:
            self.client.change_leverage(symbol=SYMBOL, leverage=LEVERAGE)
            self.client.change_margin_type(symbol=SYMBOL, marginType="ISOLATED")
            logger.info(f"✅ Leverage: {LEVERAGE}x | Mode: ISOLATED")
        except Exception as e:
            # อาจ error ถ้า margin type ซ้ำ — ไม่ critical
            logger.warning(f"Leverage setup: {e}")

    # ─── Main Loop ────────────────────────────────────────────────────────

    def run(self):
        logger.info("=" * 55)
        logger.info(f"  🤖  BTC Futures Bot Started")
        logger.info(f"  Pair: {SYMBOL} | TF: {TIMEFRAME} | Lev: {LEVERAGE}x")
        logger.info("=" * 55)

        while True:
            try:
                self._tick()
            except KeyboardInterrupt:
                logger.info("⛔ หยุด bot โดยผู้ใช้")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                logger.debug(traceback.format_exc())

            time.sleep(LOOP_INTERVAL)

    def _tick(self):
        """หนึ่ง iteration ของ loop"""
        # ดึงข้อมูลใหม่
        df = fetch_ohlcv(self.client, SYMBOL, TIMEFRAME, lookback_days=5)
        df = add_indicators(df, EMA_FAST, EMA_SLOW, EMA_TREND)

        price   = get_current_price(self.client, SYMBOL)
        balance = get_balance(self.client)
        signal  = self.strategy.generate_signal(df)

        last = df.iloc[-1]
        self._log_status(price, balance, last, signal)

        # ── Execute ──────────────────────────────────────────────────────
        if signal == Signal.CLOSE and self.strategy.position:
            self._execute_close(price)

        elif signal == Signal.LONG and not self.strategy.position:
            self._execute_open("LONG", price, balance)

        elif signal == Signal.SHORT and not self.strategy.position:
            self._execute_open("SHORT", price, balance)

        # อัพเดท unrealized PnL
        if self.strategy.position:
            pnl = self.strategy.update_pnl(price)
            logger.info(f"  📈 Unrealized PnL: {pnl*100:+.2f}%")

    # ─── Order Execution ──────────────────────────────────────────────────

    def _execute_open(self, side: str, price: float, balance: float):
        pos = self.strategy.open_position(side, price, balance)
        if pos.quantity <= 0:
            logger.warning("⚠️  คำนวณ position size = 0 — ข้าม")
            return

        order_side = "BUY" if side == "LONG" else "SELL"
        try:
            order = self.client.new_order(
                symbol=SYMBOL,
                side=order_side,
                type="MARKET",
                quantity=pos.quantity
            )
            logger.info(
                f"✅ OPEN {side} | Qty: {pos.quantity} BTC | "
                f"Entry: ~{price:.1f} | SL: {pos.sl_price:.1f} | TP: {pos.tp_price:.1f}"
            )

            # ตั้ง SL Order
            sl_side = "SELL" if side == "LONG" else "BUY"
            self.client.new_order(
                symbol=SYMBOL,
                side=sl_side,
                type="STOP_MARKET",
                stopPrice=round(pos.sl_price, 1),
                quantity=pos.quantity,
                reduceOnly=True,
                timeInForce="GTE_GTC"
            )

            # ตั้ง TP Order
            self.client.new_order(
                symbol=SYMBOL,
                side=sl_side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=round(pos.tp_price, 1),
                quantity=pos.quantity,
                reduceOnly=True,
                timeInForce="GTE_GTC"
            )
            logger.info(f"   🛡️  SL/TP orders ถูกตั้งแล้ว")

        except Exception as e:
            logger.error(f"❌ Open order failed: {e}")
            self.strategy.position = None   # rollback state

    def _execute_close(self, price: float):
        pos = self.strategy.position
        close_side = "SELL" if pos.side == "LONG" else "BUY"

        try:
            # ยกเลิก SL/TP เดิมก่อน
            self.client.cancel_open_orders(symbol=SYMBOL)

            self.client.new_order(
                symbol=SYMBOL,
                side=close_side,
                type="MARKET",
                quantity=pos.quantity,
                reduceOnly=True
            )
            result = self.strategy.close_position(price)
            logger.info(
                f"✅ CLOSE {result['side']} | Exit: {price:.1f} | "
                f"PnL: {result['pnl_pct']*100:+.2f}% ({result['pnl_usdt']:+.2f} USDT)"
            )
        except Exception as e:
            logger.error(f"❌ Close order failed: {e}")

    # ─── Logging ──────────────────────────────────────────────────────────

    def _log_status(self, price, balance, last, signal):
        pos_info = (
            f"{self.strategy.position.side} @ {self.strategy.position.entry_price:.1f}"
            if self.strategy.position else "None"
        )
        logger.info(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"BTC: ${price:,.1f} | "
            f"Balance: ${balance:,.2f} | "
            f"RSI: {last['rsi']:.1f} | "
            f"Signal: {signal.value} | "
            f"Position: {pos_info}"
        )


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BTC Futures Bot")
    parser.add_argument("--backtest", action="store_true",
                        help="รัน backtest เท่านั้น ไม่ส่ง order จริง")
    args = parser.parse_args()

    if args.backtest:
        from backtest.engine import BacktestEngine
        from utils.helpers import get_client, fetch_ohlcv, add_indicators

        print(f"📡 กำลังดึงข้อมูลสำหรับ backtest...")
        client = get_client()
        df     = fetch_ohlcv(client, SYMBOL, TIMEFRAME, BACKTEST_DAYS)
        df     = add_indicators(df, EMA_FAST, EMA_SLOW, EMA_TREND)
        engine = BacktestEngine(df, INITIAL_CAPITAL)
        engine.run()
    else:
        bot = TradingBot()
        bot.run()


if __name__ == "__main__":
    main()
