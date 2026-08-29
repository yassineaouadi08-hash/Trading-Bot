from flask import Flask, request
import threading
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Stable Crypto Bot is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def get_crypto_data(coin_id, name):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=5"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "prices" not in data:
            return f"لا توجد بيانات متاحة لـ {name}"
            
        prices = [x[1] for x in data["prices"]]
        df = pd.DataFrame(prices, columns=['close'])
        df['open'] = df['close'].shift(1).fillna(df['close'])
        
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
        current_price = float(df['close'].iloc[-1])
        rsi = float(last_row['rsi']) if not pd.isna(last_row['rsi']) else 50.0
        macd = float(last_row['MACD']) if not pd.isna(last_row['MACD']) else 0.0
        signal = float(last_row['Signal']) if not pd.isna(last_row['Signal']) else 0.0

        # تحديد Long أو Short بوضوح تام
        sentiment = "محايد ⚖️"
        advice = "السوق عرضي، انتظر إشارة قوية."
        if rsi < 48 and macd > signal:
            sentiment = "إيجابي (Long مُمتاز) 🟢"
            advice = "فرصة دخول شراء (Long) قوية حسب المؤشرات!"
        elif rsi > 52 and macd < signal:
            sentiment = "سلبي (Short مُمتاز) 🔴"
            advice = "فرصة دخول بيع (Short) قوية حسب المؤشرات!"

        report = (f"📊 **تحليل عملة {name}**\n\n"
                  f"💰 السعر الحالي: `{current_price:,.2f}$`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD Line: `{macd:.4f}` | Signal: `{signal:.4f}`\n\n"
                  f"🎯 **القرار الفني:** {sentiment}\n"
                  f"💡 **النصيحة:** {advice}")
        return report
    except Exception as e:
        return f"خطأ في تحليل {name}: {str(e)}"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start":
            reply = ("مرحباً بك يا ياسين! 🤖 البوت يشتغل بانتظام.\n\n"
                     "الأوامر المتاحة:\n"
                     "🔹 `/btc` - تحليل Bitcoin\n"
                     "🔹 `/sol` - تحليل Solana\n"
                     "🔹 `/hype` - تحليل Hyperliquid (HYPE)\n"
                     "🔹 `/status` - تقرير شامل (Long / Short)")
            send_telegram_message(reply, chat_id)
            
        elif text == "/btc":
            send_telegram_message(get_crypto_data('bitcoin', 'Bitcoin (BTC)'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_crypto_data('solana', 'Solana (SOL)'), chat_id)
        elif text == "/hype":
            send_telegram_message(get_crypto_data('hyperliquid', 'Hyperliquid (HYPE)'), chat_id)
        elif text == "/status":
            btc_rep = get_crypto_data('bitcoin', 'Bitcoin (BTC)')
            sol_rep = get_crypto_data('solana', 'Solana (SOL)')
            hype_rep = get_crypto_data('hyperliquid', 'Hyperliquid (HYPE)')
            send_telegram_message(f"🔥 **تقرير السوق الشامل (Long / Short)**:\n\n{btc_rep}\n\n------------------\n\n{sol_rep}\n\n------------------\n\n{hype_rep}", chat_id)
        else:
            send_telegram_message("عذراً، استعمل الأوامر التالية:\n/btc, /sol, /hype, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
