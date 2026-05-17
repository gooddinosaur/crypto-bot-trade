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
TIMEFRAME     = "15m"
TIMEFRAME_HTF = "1h"

# ─── EMA Strategy Parameters ────────────────────
EMA_FAST  = 9
EMA_SLOW  = 21
EMA_TREND = 50

# ─── Risk Management ────────────────────────────
RISK_PER_TRADE   = 0.01   # 1% per trade
MAX_POSITION_PCT = 0.20   # เพิ่มขนาดไม้เพื่อให้ถึงเป้ากำไร
LEVERAGE         = 10     # Day trade มักใช้ Leverage ช่วยทดแทนรอบที่แคบลง

# ─── Stop Loss / Take Profit ────────────────────
STOP_LOSS_PCT   = 0.005   # 0.5% (Stop Loss สั้นลง)
TAKE_PROFIT_PCT = 0.012   # 1.2% (Take profit สั้นลง เก็บกำไรไวขึ้น)
TRAILING_STOP   = True
TRAILING_DELTA  = 0.004   # 0.4%

# ─── Filters ────────────────────────────────────
MIN_VOLUME_USDT = 500_000
ATR_MULTIPLIER  = 1.1

# ─── Backtesting ────────────────────────────────
BACKTEST_DAYS   = 365
INITIAL_CAPITAL = 10_000

# ─── Bot Settings ───────────────────────────────
LOOP_INTERVAL = 60
LOG_LEVEL     = "INFO"
LOG_FILE      = "logs/bot.log"