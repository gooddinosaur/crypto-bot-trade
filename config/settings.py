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
TIMEFRAME     = "15m"
TIMEFRAME_HTF = "1h" 

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 9
EMA_SLOW  = 21
EMA_TREND = 50      

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.01  
MAX_POSITION_PCT = 0.10  
LEVERAGE         = 5    

# ─── Stop Loss / Take Profit ────────────────────
STOP_LOSS_PCT   = 0.012
TAKE_PROFIT_PCT = 0.024   # RR 1:2
TRAILING_STOP   = True
TRAILING_DELTA  = 0.010

# ─── Filters ────────────────────────────────────
MIN_VOLUME_USDT = 500_000
ATR_MULTIPLIER = 1.2

# ─── Backtesting ────────────────────────────────
BACKTEST_DAYS    = 365
INITIAL_CAPITAL  = 10_000  # USDT

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL    = 60    # วนลูปทุก 60 วินาที
LOG_LEVEL        = "INFO"
LOG_FILE         = "logs/bot.log"
