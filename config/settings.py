"""
==============================================
  BTC Futures Trading Bot — Configuration
==============================================
  :warning:  ใช้ Testnet ก่อนเสมอ!
  แก้ TESTNET = False เมื่อพร้อม live trade
"""

# ─── API Keys ───────────────────────────────────
# ใส่ key จาก https://testnet.binancefuture.com
API_KEY    = "DkdADJdavMckV3DBiAkWEpofAwyvIcwwLBvYAcvfOyUMoYyxWZ5pyPx1tP0VsDhj"
API_SECRET = "SPfibpDWNZiRi8ZG9wezcnHhvmrf3CouJXgu1yhPkSlQWuDWR9sEIAc8z2Y18jdW"
TESTNET    = True   # ← เปลี่ยนเป็น False สำหรับ live

# ─── Trading Pair ───────────────────────────────
SYMBOL     = "BTCUSDT"
TIMEFRAME  = "15m"    # 1m 5m 15m 1h 4h 1d

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 8
EMA_SLOW  = 13           # EMA Fibonacci — reactive กว่า
EMA_TREND = 34

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.01        # ลดจาก 2% → 1%
MAX_POSITION_PCT = 0.10
LEVERAGE         = 3      # leverage (1–20, แนะนำ ≤10)

# ─── Stop Loss / Take Profit ────────────────────
STOP_LOSS_PCT    = 0.012
TAKE_PROFIT_PCT  = 0.030
TRAILING_STOP    = True
TRAILING_DELTA   = 0.005

# ─── Filters ────────────────────────────────────
MIN_VOLUME_USDT  = 1_000_000  # จาก 500_000
ATR_MULTIPLIER   = 1.5       # กรอง entry ด้วย ATR

# ─── Backtesting ────────────────────────────────
BACKTEST_DAYS    = 30    # ย้อนหลัง 30 วัน
INITIAL_CAPITAL  = 10_000  # USDT

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL    = 60    # วนลูปทุก 60 วินาที
LOG_LEVEL        = "INFO"
LOG_FILE         = "logs/bot.log"