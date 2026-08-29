from flask import Flask, request
import threading
import ccxt
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Kraken Trading Bot is running 24/7!"

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
        # استخدام منصة Kraken لتجنب الحظر الجغرافي
        exchange = ccxt.kraken()
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # مؤشر RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # مؤشر MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        last_row = df.iloc[-2]
        current_price = float(last_row['close'])
        rsi = float(last_row['rsi']) if not pd.isna(last_row['rsi']) else 50.0
        macd = float(last_row['MACD']) if not pd.isna(last_row['MACD']) else 0.0
        signal = float(last_row['Signal']) if not pd.isna(last_row['Signal']) else 0.0

        sentiment = "محايد ⚖️"
        advice = "الوضع عرضي، انتظر تأكيد إشارة واضحة."
        if rsi < 45 and macd > signal:
            sentiment = "إيجابي (Long مُمتاز) 🟢"
            advice = "الإشارات تدعم صعود السوق ودخول (Long)!"
        elif rsi > 55 and macd < signal:
            sentiment = "سلبي (Short مُمتاز) 🔴"
            advice = "الإشارات تدعم هبوط السوق ودخول (Short)!"

        report = (f"📊 **تحليل عملة {symbol}**\n\n"
                  f"💰 السعر الحالي: `{current_price:,.2f}$`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD: `{macd:.4f}` | Signal: `{signal:.4f}`\n\n"
                  f"🎯 **القرار الفني:** {sentiment}\n"
                  f"💡 **النصيحة:** {advice}")
        return report
    except Exception as e:
        return f"خطأ في تحليل {symbol}: {str(e)}"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start":
            reply = ("مرحباً بك يا ياسين في بوت التداول المطور عبر Kraken!\n\n"
                     "الأوامر المتاحة:\n"
                     "🔹 `/btc` - تحليل Bitcoin\n"
                     "🔹 `/sol` - تحليل Solana\n"
                     "🔹 `/status` - تقرير شامل للسوق (Long أو Short)")
            send_telegram_message(reply, chat_id)
            
        elif text == "/btc":
            send_telegram_message(get_market_analysis('BTC/USD'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_market_analysis('SOL/USD'), chat_id)
        elif text == "/status":
            btc_rep = get_market_analysis('BTC/USD')
            sol_rep = get_market_analysis('SOL/USD')
            send_telegram_message(f"🔥 **تقرير السوق الشامل (Long / Short)**:\n\n{btc_rep}\n\n------------------\n\n{sol_rep}", chat_id)
        else:
            send_telegram_message("عذراً، استعمل الأوامر التالية:\n/btc, /sol, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
