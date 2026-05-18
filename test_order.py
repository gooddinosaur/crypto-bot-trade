import sys
sys.path.insert(0, '.')

from utils.helpers import get_client, get_current_price
from config.settings import SYMBOL, LEVERAGE

client = get_client()

def test_order(label, use_algo=False, **kwargs):
    try:
        if use_algo:
            order = client.sign_request("POST", "/fapi/v1/algoOrder", kwargs)
            order_id = order.get("algoId", "?")
        else:
            order = client.new_order(**kwargs)
            order_id = order.get("orderId", "?")
        print(f"  ✅ {label} — OK (orderId: {order_id})")
        return order_id
    except Exception as e:
        print(f"  ❌ {label} — FAILED: {e}")
        return None

def cancel(order_id, use_algo=False):
    if order_id:
        try:
            if use_algo:
                client.sign_request("DELETE", "/fapi/v1/algoOrder", {"symbol": SYMBOL, "algoId": order_id})
            else:
                client.cancel_order(symbol=SYMBOL, orderId=order_id)
            print(f"     🗑  ยกเลิก order {order_id} แล้ว")
        except Exception as e:
            print(f"     ⚠️  ยกเลิกไม่ได้: {e}")

print(f"\n{'='*55}")
print(f"  🧪  Order Type Test — {SYMBOL}")
print(f"{'='*55}")

price = get_current_price(client, SYMBOL)
print(f"\n  Current Price: ")

sl_price = round(price * 0.97, 1)   # -3%
tp_price = round(price * 1.06, 1)   # +6%
qty = 0.001 

print(f"  Test Qty: {qty} BTC | SL:  | TP: ")
print(f"  (ราคาห่างพอที่ SL/TP จะไม่ trigger ระหว่าง test)\n")

print("[ Test 1 ] MARKET BUY")
market_id = test_order(
    "MARKET BUY",
    symbol=SYMBOL, side="BUY", type="MARKET", quantity=qty
)

if market_id:
    import time
    time.sleep(1)

    print("\n[ Test 2 ] STOP_MARKET (Stop Loss)")
    sl_id = test_order(
        "STOP_MARKET",
        use_algo=True,
        symbol=SYMBOL, side="SELL", algoType="CONDITIONAL", type="STOP_MARKET",
        triggerPrice=sl_price, closePosition="true", workingType="MARK_PRICE"
    )

    print("\n[ Test 3 ] TAKE_PROFIT_MARKET (Take Profit)")
    tp_id = test_order(
        "TAKE_PROFIT_MARKET",
        use_algo=True,
        symbol=SYMBOL, side="SELL", algoType="CONDITIONAL", type="TAKE_PROFIT_MARKET",
        triggerPrice=tp_price, closePosition="true", workingType="MARK_PRICE"
    )

    print("\n[ Cleanup ]")
    cancel(sl_id, use_algo=True)
    cancel(tp_id, use_algo=True)

    time.sleep(0.5)
    close_id = test_order(
        "MARKET SELL (close position)",
        symbol=SYMBOL, side="SELL", type="MARKET",
        quantity=qty, reduceOnly="true"
    )

print(f"\n{'='*55}")
print("  ✔  Test เสร็จแล้ว — ดูผลข้างบน")
print(f"{'='*55}\n")
