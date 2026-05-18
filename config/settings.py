"""
==============================================
  BTC Futures Trading Bot — Configuration
==============================================
"""

# ─── API Keys ───────────────────────────────────
API_KEY    = "NLYVjzCjMECjjC1NqrSvbDe5g1LuoTKGMKZLL7t7EwbtqjkHkHGplOePlqGQeyg6"
API_SECRET = "BWl4cNQPPzAmPjzY0WtaxcLASahbTJKaymTWqThveXmgwMtp67EX2cyPNjrH2FYa"
TESTNET    = False

# ─── Trading Pair ───────────────────────────────
SYMBOL        = "BTCUSDT"
TIMEFRAME     = "5m"
TIMEFRAME_HTF = "15m"

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 9
EMA_SLOW  = 21
EMA_TREND = 50

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.05   # ปรับเป็น 5% ต่อ trade (ทุนน้อย 30$ ต้องเพิ่มความเสี่ยงเพื่อให้เปิดออเดอร์ได้)
MAX_POSITION_PCT = 0.50   # 50% ของพอร์ต (ตามคอมเมนต์เดิมที่เขียนไว้)
LEVERAGE         = 10

# ─── Stop Loss / Take Profit ────────────────────
STOP_LOSS_PCT   = 0.003   # 0.3% ตัดขาดทุนไวมาก
TAKE_PROFIT_PCT = 0.006   # 0.6% รีบเก็บค่ายกับข้าว
TRAILING_STOP   = True
TRAILING_DELTA  = 0.002   # 0.2%

# ─── Filters ────────────────────────────────────
MIN_VOLUME_USDT = 500_000
ATR_MULTIPLIER  = 1.1

# ─── Backtesting ────────────────────────────────
BACKTEST_DAYS   = 30
INITIAL_CAPITAL = 10_000

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL = 60
LOG_LEVEL     = "INFO"
LOG_FILE      = "logs/bot.log"