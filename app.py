from flask import Flask
import threading
import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Multi-Coin Trading Bot is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def analyze_market():
    symbols = ['BTC/USDT', 'SOL/USDT', 'HYPE/USDT']
    
    while True:
        for symbol in symbols:
            try:
                exchange = ccxt.bybit()
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                df['rsi'] = ta.rsi(df['close'], length=14)
                macd = ta.macd(df['close'])
                df = pd.concat([df, macd], axis=1)

                df['prev_open'] = df['open'].shift(1)
                df['prev_close'] = df['close'].shift(1)
                
                df['bullish_engulfing'] = (df['prev_close'] < df['prev_open']) & \
                                          (df['close'] > df['open']) & \
                                          (df['open'] <= df['prev_close']) & \
                                          (df['close'] >= df['prev_open'])
                                          
                df['bearish_engulfing'] = (df['prev_close'] > df['prev_open']) & \
                                          (df['close'] < df['open']) & \
                                          (df['open'] >= df['prev_close']) & \
                                          (df['close'] <= df['prev_open'])

                last_row = df.iloc[-2]
                rsi = last_row['rsi']
                macd_line = last_row['MACD_12_26_9']
                signal_line = last_row['MACDs_12_26_9']
                current_price = last_row['close']
                
                is_bullish = last_row['bullish_engulfing']
                is_bearish = last_row['bearish_engulfing']

                if rsi < 40 and macd_line > signal_line and is_bullish:
                    stop_loss = last_row['low'] * 0.998
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * 2)
                    
                    msg = (f"🟢 **صفقة Long (شراء) على {symbol}** 🟢\n\n"
                           f"💰 السعر الحالي: {current_price:.4f}\n"
                           f"📊 RSI: {rsi:.2f}\n"
                           f"🕯 البرايس أكشن: شمعة ابتلاعية شرائية ✅\n"
                           f"📈 التقاطع: MACD إيجابي ✅\n\n"
                           f"🛑 Stop Loss: {stop_loss:.4f}\n"
                           f"🎯 Take Profit: {take_profit:.4f}")
                    send_telegram_message(msg)
                    
                elif rsi > 60 and macd_line < signal_line and is_bearish:
                    stop_loss = last_row['high'] * 1.002
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * 2) 
                    
                    msg = (f"🔴 **صفقة Short (بيع) على {symbol}** 🔴\n\n"
                           f"💰 السعر الحالي: {current_price:.4f}\n"
                           f"📊 RSI: {rsi:.2f}\n"
                           f"🕯 البرايس أكشن: شمعة ابتلاعية بيعية ✅\n"
                           f"📉 التقاطع: MACD سلبي ✅\n\n"
                           f"🛑 Stop Loss: {stop_loss:.4f}\n"
                           f"🎯 Take Profit: {take_profit:.4f}")
                    send_telegram_message(msg)

            except Exception as e:
                print(f"Error analyzing {symbol}:", e)
                
            time.sleep(5) # فاصل زمني قصير بين العملة والثانية لتفادي ضغط الطلبات
            
        time.sleep(900) # ينتظر 15 دقيقة قبل إعادة الفحص للعملات الكل

threading.Thread(target=analyze_market, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
