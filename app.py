from flask import Flask, request
import threading
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Direct Signal Bot is running 24/7!"

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
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=2"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "prices" not in data:
            return f"لا توجد بيانات متاحة لـ {name}"
            
        prices = [x[1] for x in data["prices"]]
        df = pd.DataFrame(prices, columns=['close'])
        
        # مؤشر RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        current_price = float(df['close'].iloc[-1])
        rsi = float(df['rsi'].iloc[-2]) if not pd.isna(df['rsi'].iloc[-2]) else 50.0

        # قرار صارم ومباشر بدون محايد
        if rsi < 50:
            sentiment = "إيجابي (فرصة Long) 🟢"
            advice = "السعر في منطقة شراء، توجه نحو Long 🚀"
        else:
            sentiment = "سلبي (فرصة Short) 🔴"
            advice = "السعر في منطقة بيع، توجه نحو Short 📉"

        report = (f"📊 **تحليل عملة {name}**\n\n"
                  f"💰 السعر الحالي: `{current_price:,.2f}$`\n"
                  f"📈 RSI: `{rsi:.2f}`\n\n"
                  f"🎯 **القرار:** {sentiment}\n"
                  f"💡 **الاتجاه:** {advice}")
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
            send_telegram_message("مرحباً بك يا ياسين! البوت جاهز لإعطاء إشارات Long و Short مباشرة.", chat_id)
        elif text == "/btc":
            send_telegram_message(get_crypto_data('bitcoin', 'Bitcoin (BTC)'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_crypto_data('solana', 'Solana (SOL)'), chat_id)
        elif text == "/hype":
            send_telegram_message(get_crypto_data('hyperliquid', 'Hyperliquid (HYPE)'), chat_id)
        elif text == "/status":
            btc = get_crypto_data('bitcoin', 'Bitcoin (BTC)')
            sol = get_crypto_data('solana', 'Solana (SOL)')
            hype = get_crypto_data('hyperliquid', 'Hyperliquid (HYPE)')
            send_telegram_message(f"🔥 **قرارات السوق المباشرة (Long / Short)**:\n\n{btc}\n\n---\n\n{sol}\n\n---\n\n{hype}", chat_id)
        else:
            send_telegram_message("استعمل الأوامر: /btc, /sol, /hype, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
