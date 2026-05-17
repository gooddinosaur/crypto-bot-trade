import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("backtest/equity_curve.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

plt.plot(df["timestamp"], df["equity"])
plt.title("Equity Curve")
plt.xlabel("Date")
plt.ylabel("USDT")
plt.grid(True)
plt.show()