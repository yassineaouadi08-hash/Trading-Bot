from flask import Flask, request
import threading
import yfinance as yf
import pandas as pd
import requests
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Yahoo Finance Trading Bot is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def get_market_analysis(ticker, name):
    try:
        # جلب البيانات عبر Yahoo Finance (بدون قيود جغرافية)
        df = yf.download(ticker, period="5d", interval="15m", progress=False)
        if df.empty:
            return f"لا توجد بيانات متاحة حالياً لـ {name}"
        
        # تصحيح أعمدة البيانات إذا جاءت مزدوجة
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['close'] = df['Close']
        df['open'] = df['Open']
        
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
        current_price = float(last_row['close'])
        rsi = float(last_row['rsi'])
        macd = float(last_row['MACD_12_26_9'])
        signal = float(last_row['MACDs_12_26_9'])
        is_bullish = bool(last_row['bullish_engulfing'])
        is_bearish = bool(last_row['bearish_engulfing'])

        sentiment = "محايد ⚖️"
        advice = "الوضع غير واضح، انتظر حتى تتوفر شروط قوية."
        if rsi < 40 and macd > signal and is_bullish:
            sentiment = "إيجابي قوي (Long مُمتاز) 🟢"
            advice = "الشروط توحي بفرصة شراْء (Long) ناجحة!"
        elif rsi > 60 and macd < signal and is_bearish:
            sentiment = "سلبي قوي (Short مُمتاز) 🔴"
            advice = "الشروط توحي بفرصة بيع (Short) ناجحة!"

        report = (f"📊 **تحليل عملة {name}**\n\n"
                  f"💰 السعر الحالي: `{current_price:.2f}`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD Line: `{macd:.4f}` | Signal: `{signal:.4f}`\n"
                  f"🕯 شمعة ابتلاعية شرائية: `{'نعم ✅' if is_bullish else 'لا ❌'}`\n"
                  f"🕯 شمعة ابتلاعية بيعية: `{'نعم ✅' if is_bearish else 'لا ❌'}`\n\n"
                  f"🎯 **التقييم:** {sentiment}\n"
                  f"💡 **الرأي الفني:** {advice}")
        return report
    except Exception as e:
        return f"خطأ في جلب بيانات {name}: {str(e)}"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip().lower()
        
        if text == "/start":
            reply = ("مرحباً بك يا ياسين! 🤖 تم تحديث البوت ليعمل عبر Yahoo Finance بدون أي قيود جغرافية.\n\n"
                     "الأوامر المتاحة:\n"
                     "🔹 `/btc` - تحليل شامل للـ Bitcoin\n"
                     "🔹 `/sol` - تحليل شامل للـ Solana\n"
                     "🔹 `/eth` - تحليل شامل للـ Ethereum\n"
                     "🔹 `/status` - حالة السوق العامة وما إذا كان Long أو Short أفضل")
            send_telegram_message(reply, chat_id)
            
        elif text == "/btc":
            send_telegram_message(get_market_analysis('BTC-USD', 'Bitcoin'), chat_id)
        elif text == "/sol":
            send_telegram_message(get_market_analysis('SOL-USD', 'Solana'), chat_id)
        elif text == "/eth":
            send_telegram_message(get_market_analysis('ETH-USD', 'Ethereum'), chat_id)
        elif text == "/status":
            btc_rep = get_market_analysis('BTC-USD', 'Bitcoin')
            sol_rep = get_market_analysis('SOL-USD', 'Solana')
            eth_rep = get_market_analysis('ETH-USD', 'Ethereum')
            send_telegram_message(f"تقرير شامل لسوق العملات:\n\n{btc_rep}\n\n------------------\n\n{sol_rep}\n\n------------------\n\n{eth_rep}", chat_id)
        else:
            send_telegram_message("عذراً، لم أفهم طلبك. استعمل الأوامر الآتية:\n/btc, /sol, /eth, /status", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
