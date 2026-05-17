# 🤖 BTC Futures Trading Bot

EMA Triple Crossover strategy สำหรับ Binance USD-M Futures

---

## 📁 โครงสร้างไฟล์

```
btc_bot/
├── bot.py                    ← จุดเริ่มต้นหลัก
├── requirements.txt
├── config/
│   └── settings.py           ← ⚙️  ตั้งค่าทั้งหมดที่นี่
├── strategies/
│   └── ema_crossover.py      ← กลยุทธ์ EMA Crossover
├── utils/
│   └── helpers.py            ← Indicators, Position sizing, Client
├── backtest/
│   ├── engine.py             ← Backtest engine
│   ├── trades_result.csv     ← (สร้างหลัง backtest)
│   └── equity_curve.csv      ← (สร้างหลัง backtest)
└── logs/
    └── bot.log               ← Log ทั้งหมด
```

---

## 🚀 วิธีติดตั้งและรัน

### 1. ติดตั้ง dependencies
```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า API Key
แก้ไข `config/settings.py`:
```python
API_KEY    = "YOUR_TESTNET_API_KEY"
API_SECRET = "YOUR_TESTNET_API_SECRET"
TESTNET    = True   # ← ใช้ testnet ก่อนเสมอ!
```
สร้าง Testnet key ได้ที่: https://testnet.binancefuture.com

### 3. รัน Backtest ก่อน
```bash
python bot.py --backtest
```

### 4. รัน Bot (Testnet)
```bash
python bot.py
```

---

## 📊 กลยุทธ์ EMA Triple Crossover

| เงื่อนไข | LONG | SHORT |
|---------|------|-------|
| EMA Signal | EMA9 ตัดขึ้น EMA21 | EMA9 ตัดลง EMA21 |
| Trend Filter | Price > EMA50 | Price < EMA50 |
| RSI Filter | RSI < 70 | RSI > 30 |
| Volume Filter | Volume > MA20 และ > 500K USDT | เดียวกัน |

**Exit conditions:**
- Take Profit: +3.0% (Risk:Reward = 1:2)
- Stop Loss: -1.5%
- Trailing Stop: 1.0% จาก highest/lowest
- EMA reversal cross

---

## ⚙️ ค่าที่ควรปรับ (settings.py)

| Parameter | Default | คำแนะนำ |
|-----------|---------|---------|
| `LEVERAGE` | 5 | อย่าเกิน 10x |
| `RISK_PER_TRADE` | 1% | 0.5–2% |
| `TIMEFRAME` | 15m | 1h สำหรับ swing |
| `EMA_FAST/SLOW` | 9/21 | ทดสอบก่อนเปลี่ยน |
| `STOP_LOSS_PCT` | 1.5% | ตามความเสี่ยงส่วนตัว |

---

## ⚠️ คำเตือน

- **ทดสอบบน Testnet เสมอก่อน live**
- Crypto futures มีความเสี่ยงสูงมาก โดยเฉพาะเมื่อใช้ leverage
- Past performance ไม่ได้รับประกันผลในอนาคต
- อย่า risk เงินที่รับไม่ได้ถ้าหาย

---

## 🔧 การ Optimize

หลัง backtest ให้ดูที่:
1. **Win rate > 45%** และ **Profit factor > 1.5** ถือว่าใช้ได้
2. **Max Drawdown < 20%** สำหรับความเสี่ยงปานกลาง
3. ลอง timeframe ต่างๆ: 15m (scalping), 1h (intraday), 4h (swing)
4. ปรับ EMA periods ด้วย `EMA_FAST`, `EMA_SLOW`, `EMA_TREND`
