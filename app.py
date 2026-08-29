from flask import Flask, request
import threading
import ccxt
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Interactive Trading Bot is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def get_market_analysis(symbol):
    try:
        # استبدال Bybit بـ Binance لتجنب الحظر الجغرافي على سيرفرات Render
        exchange = ccxt.binance()
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD_12_26_9'] = exp1 - exp2
        df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()

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
        current_price = last_row['close']
        rsi = last_row['rsi']
        macd = last_row['MACD_12_26_9']
        signal = last_row['MACDs_12_26_9']
        is_bullish = last_row['bullish_engulfing']
        is_bearish = last_row['bearish_engulfing']

        sentiment = "محايد ⚖️"
        advice = "الوضع غير واضح، انتظر حتى تتوفر شروط قوية."
        if rsi < 40 and macd > signal and is_bullish:
            sentiment = "إيجابي قوي (Long مُمتاز) 🟢"
            advice = "الشروط توحي بفرصة شراْء (Long) ناجحة!"
        elif rsi > 60 and macd < signal and is_bearish:
            sentiment = "سلبي قوي (Short مُمتاز) 🔴"
            advice = "الشروط توحي بفرصة بيع (Short) ناجحة!"

        report = (f"📊 **تحليل عملة {symbol}**\n\n"
                  f"💰 السعر الحالي: `{current_price:.4f}`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD Line: `{macd:.4f}` | Signal: `{signal:.4f}`\n"
                  f"🕯 شمعة ابتلاعية شرائية: `{'نعم ✅' if is_bullish else 'لا ❌'}`\n"
                  f"🕯 شمعة ابتلاعية بيعية: `{'نعم ✅' if is_bearish else 'لا ❌'}`\n\n"
                  f"🎯 **التقييم:** {sentiment}\n"
                  f"💡 **الرأي الفني:** {advice}")
        return report
    except Exception as e:
        return f"خطأ في جلب بيانات {symbol}: {str(e)}"

def background_monitor():
    symbols = ['BTC/USDT', 'SOL/USDT', 'BNB/USDT']
    while True:
        for symbol in symbols:
            try:
                exchange = ccxt.binance()
                bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
                df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))

                exp1 = df['close'].ewm(span=12, adjust=False).mean()
                exp2 = df['close'].ewm(span=26, adjust=False).mean()
                df['MACD_12_26_9'] = exp1 - exp2
                df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()

                df['prev_open'] = df['open'].shift(1)
                df['prev_close'] = df['close'].shift(1)
                df['bullish_engulfing'] = (df['prev_close'] < df['prev_open']) & (df['close'] > df['open']) & (df['open'] <= df['prev_close']) & (df['close'] >= df['prev_open'])
                df['bearish_engulfing'] = (df['prev_close'] > df['prev_open']) & (df['close'] < df['open']) & (df['open'] >= df['prev_close']) & (df['close'] <= df['prev_open'])

                last_row = df.iloc[-2]
                rsi = last_row['rsi']
                macd_line = last_row['MACD_12_26_9']
                signal_line = last_row['MACDs_12_26_9']
                current_price = last_row['close']
                
                if rsi < 40 and macd_line > signal_line and last_row['bullish_engulfing']:
                    stop_loss = last_row['low'] * 0.998
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * 2)
                    msg = f"🟢 **صفقة Long أوتوماتيكية على {symbol}**\n\n💰 السعر: `{current_price:.4f}`\n📊 RSI: `{rsi:.2f}`\n🛑 Stop Loss: `{stop_loss:.4f}`\n🎯 Take Profit: `{take_profit:.4f}`"
                    send_telegram_message(msg)
                    
                elif rsi > 60 and macd_line < signal_line and last_row['bearish_engulfing']:
                    stop_loss = last_row['high'] * 1.002
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * 2) 
                    msg = f"🔴 **صفقة Short أوتوماتيكية على {symbol}**\n\n💰 السعر: `{current_price:.4f}`\n📊 RSI: `{rsi:.2f}`\n🛑 Stop Loss: `{stop_loss:.4f}`\n🎯 Take Profit: `{take_profit:.4f}`"
                    send_telegram_message(msg)
            except Exception as e:
                pass
            time.sleep(5)
        time.sleep(900)

threading.Thread(target=background_monitor, daemon=True).start()

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start":
            reply = ("مرحباً بك يا ياسين! 🤖 أنا بوت التداول الذكي الخاص بك.\n\n"
                     "الأوامر المتاحة:\n"
                     "🔹 `/btc` - تحليل شامل للـ Bitcoin\n"
                     "🔹 `/sol` - تحليل شامل للـ Solana\n"
                     "🔹 `/bnb` - تحليل شامل للـ BNB\n"
                     "🔹 `/status` - حالة السوق العامة وما إذا كان Long أو Short أفضل")
            send_telegram_message(reply, chat_id)
            
        elif text == "/btc":
            send_telegram_message(get_market_analysis('BTC/USDT'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_market_analysis('SOL/USDT'), chat_id)
        elif text == "/bnb":
            send_telegram_message(get_market_analysis('BNB/USDT'), chat_id)
        elif text == "/status":
            btc_rep = get_market_analysis('BTC/USDT')
            sol_rep = get_market_analysis('SOL/USDT')
            bnb_rep = get_market_analysis('BNB/USDT')
            send_telegram_message(f"تقرير شامل لسوق العملات:\n\n{btc_rep}\n\n------------------\n\n{sol_rep}\n\n------------------\n\n{bnb_rep}", chat_id)
        else:
            send_telegram_message("عذراً، لم أفهم طلبك. استعمل الأوامر الآتية:\n/btc, /sol, /bnb, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
