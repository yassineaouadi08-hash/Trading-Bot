from flask import Flask, request
import threading
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto Trading Bot with HYPE is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def get_coingecko_analysis(coin_id, symbol_name):
    try:
        # جلب البيانات التاريخية للأسعار مباشرة من CoinGecko (بدون حظر جغرافي)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=5"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "prices" not in data:
            return f"لا توجد بيانات متاحة لـ {symbol_name}"
            
        prices = [x[1] for x in data["prices"]]
        df = pd.DataFrame(prices, columns=['close'])
        df['open'] = df['close'].shift(1).fillna(df['close'])
        
        # حساب RSI مبسط
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # حساب MACD مبسط
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

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
        current_price = float(df['close'].iloc[-1])
        rsi = float(last_row['rsi']) if not pd.isna(last_row['rsi']) else 50.0
        macd = float(last_row['MACD']) if not pd.isna(last_row['MACD']) else 0.0
        signal = float(last_row['Signal']) if not pd.isna(last_row['Signal']) else 0.0
        is_bullish = bool(last_row['bullish_engulfing'])
        is_bearish = bool(last_row['bearish_engulfing'])

        # تحديد التوصية (Long أو Short)
        sentiment = "محايد ⚖️"
        advice = "الوضع عرضي، انتظر تأكيد الإشارة."
        if rsi < 45 and macd > signal:
            sentiment = "إيجابي (Long مُمتاز) 🟢"
            advice = "المؤشرات توحي بفرصة صعود ودخول (Long)!"
        elif rsi > 55 and macd < signal:
            sentiment = "سلبي (Short مُمتاز) 🔴"
            advice = "المؤشرات توحي بفرصة هبوط ودخول (Short)!"

        report = (f"📊 **تحليل عملة {symbol_name}**\n\n"
                  f"💰 السعر الحالي: `{current_price:,.4f}$`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD Line: `{macd:.4f}` | Signal: `{signal:.4f}`\n\n"
                  f"🎯 **القرار الفني:** {sentiment}\n"
                  f"💡 **النصيحة:** {advice}")
        return report
    except Exception as e:
        return f"خطأ في تحليل {symbol_name}: {str(e)}"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start":
            reply = ("مرحباً بك يا ياسين في بوت التداول المطور!\n\n"
                     "الأوامر المتاحة:\n"
                     "🔹 `/btc` - تحليل Bitcoin\n"
                     "🔹 `/sol` - تحليل Solana\n"
                     "🔹 `/hype` - تحليل عملة Hype الفوري\n"
                     "🔹 `/status` - تقرير شامل لجميع العملات (Long أو Short)")
            send_telegram_message(reply, chat_id)
            
        elif text == "/btc":
            send_telegram_message(get_coingecko_analysis('bitcoin', 'Bitcoin (BTC)'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_coingecko_analysis('solana', 'Solana (SOL)'), chat_id)
        elif text == "/hype":
            send_telegram_message(get_coingecko_analysis('hyperliquid', 'Hyperliquid (HYPE)'), chat_id)
        elif text == "/status":
            btc_rep = get_coingecko_analysis('bitcoin', 'Bitcoin (BTC)')
            sol_rep = get_coingecko_analysis('solana', 'Solana (SOL)')
            hype_rep = get_coingecko_analysis('hyperliquid', 'Hyperliquid (HYPE)')
            send_telegram_message(f"🔥 **تقرير السوق الشامل (Long / Short)**:\n\n{btc_rep}\n\n------------------\n\n{sol_rep}\n\n------------------\n\n{hype_rep}", chat_id)
        else:
            send_telegram_message("عذراً، استعمل الأوامر التالية:\n/btc, /sol, /hype, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
