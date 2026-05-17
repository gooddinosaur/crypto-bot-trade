"""
==============================================
  BTC Futures Trading Bot — Configuration
==============================================
"""

# ─── API Keys ───────────────────────────────────
API_KEY    = "DkdADJdavMckV3DBiAkWEpofAwyvIcwwLBvYAcvfOyUMoYyxWZ5pyPx1tP0VsDhj"
API_SECRET = "SPfibpDWNZiRi8ZG9wezcnHhvmrf3CouJXgu1yhPkSlQWuDWR9sEIAc8z2Y18jdW"
TESTNET    = True

# ─── Trading Pair ───────────────────────────────
SYMBOL        = "BTCUSDT"
TIMEFRAME     = "5m"
TIMEFRAME_HTF = "15m"

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 9
EMA_SLOW  = 21
EMA_TREND = 50

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.01   # 1% per trade
MAX_POSITION_PCT = 0.50   # 50% ของพอร์ต (เพราะ Stop loss สั้นมาก ใช้ Margin เยอะขึ้นเพื่อกำไร)
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
BACKTEST_DAYS   = 90
INITIAL_CAPITAL = 10_000

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL = 60
LOG_LEVEL     = "INFO"
LOG_FILE      = "logs/bot.log"