"""
==============================================
  BTC Futures Trading Bot — Configuration
==============================================
  ⚠️  ใช้ Testnet ก่อนเสมอ!
  แก้ TESTNET = False เมื่อพร้อม live trade
"""

# ─── API Keys ───────────────────────────────────
# ใส่ key จาก https://testnet.binancefuture.com
API_KEY    = "DkdADJdavMckV3DBiAkWEpofAwyvIcwwLBvYAcvfOyUMoYyxWZ5pyPx1tP0VsDhj"
API_SECRET = "SPfibpDWNZiRi8ZG9wezcnHhvmrf3CouJXgu1yhPkSlQWuDWR9sEIAc8z2Y18jdW"
TESTNET    = True   # ← เปลี่ยนเป็น False สำหรับ live

# ─── Trading Pair ───────────────────────────────
SYMBOL     = "BTCUSDT"
TIMEFRAME  = "5m"    # 1m 5m 15m 1h 4h 1d

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 12          # จาก 9
EMA_SLOW  = 26          # จาก 21  (MACD standard)
EMA_TREND = 100         # จาก 50

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.01   # 1% ของ portfolio ต่อ trade
MAX_POSITION_PCT = 0.10   # เปิด position สูงสุด 10% ของ balance
LEVERAGE         = 5      # leverage (1–20, แนะนำ ≤10)

# ─── Stop Loss / Take Profit ────────────────────
STOP_LOSS_PCT   = 0.012   # จาก 0.015
TAKE_PROFIT_PCT = 0.036   # จาก 0.030  (RR = 1:3)
TRAILING_STOP    = True   # ใช้ trailing stop
TRAILING_DELTA   = 0.010  # trailing ห่าง 1.0%

# ─── Filters ────────────────────────────────────
MIN_VOLUME_USDT = 1_000_000   # จาก 500_000
ATR_MULTIPLIER   = 1.5       # กรอง entry ด้วย ATR

# ─── Backtesting ────────────────────────────────
BACKTEST_DAYS    = 30
INITIAL_CAPITAL  = 10_000  # USDT

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL    = 60    # วนลูปทุก 60 วินาที
LOG_LEVEL        = "INFO"
LOG_FILE         = "logs/bot.log"
