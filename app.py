import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Trading Bot is running!"

@app.route("/health")
def health():
    return "OK"

port = int(os.environ.get("PORT", 10000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
    
from flask import Flask, request
import pandas as pd
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Advanced Trading Bot is running 24/7!"

TELEGRAM_TOKEN = "8943043289:AAE-Uh6rb_FAn-xE5eJl9jXcZEBQe9JtzvA"
CHAT_ID = "6937661753"

def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

def analyze_market(symbol="BTCUSDT"):
    try:
        # جلب بيانات الشרות من Binance Public API (بدون مفاتيح معقدة)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not isinstance(data, list) or len(data) < 50:
            return f"❌ لا توجد بيانات كافية للعملة {symbol}"
            
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        current_price = df['close'].iloc[-1]
        
        # مؤشر RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        rsi = float(df['rsi'].iloc[-1])
        
        # مؤشر MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        macd = float(df['MACD'].iloc[-1])
        signal_line = float(df['Signal'].iloc[-1])
        
        # نظام النقاط (Scoring System)
        score = 50  # البداية محايد
        
        # تحليل RSI
        if rsi < 40:
            score += 20
        elif rsi > 60:
            score -= 20
            
        # تحليل MACD
        if macd > signal_line:
            score += 15
        else:
            score -= 15
            
        # تحديد القرار النهائي والنسبة
        if score >= 70:
            signal_type = "🚀 Strong LONG (شراء قوي)"
            confidence = score
        elif score >= 55:
            signal_type = "🟢 LONG (شراء)"
            confidence = score
        elif score <= 30:
            signal_type = "💥 Strong SHORT (بيع قوي)"
            confidence = 100 - score
        elif score <= 45:
            signal_type = "🔴 SHORT (بيع)"
            confidence = 100 - score
        else:
            signal_type = "⚖️ WAIT / SIDEWAYS (انتظار)"
            confidence = 50

        report = (f"📊 **تحليل فني متقدم: {symbol}** (15m)\n\n"
                  f"💰 السعر الحالي: `{current_price:,.2f}$`\n"
                  f"📈 RSI: `{rsi:.2f}`\n"
                  f"📉 MACD: `{macd:.4f}`\n\n"
                  f"🎯 **القرار:** {signal_type}\n"
                  f"⭐ **نسبة الثقة (Score):** `{confidence}%`")
        return report
    except Exception as e:
        return f"خطأ في جلب أو تحليل بيانات {symbol}: {str(e)}"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram():
    update = request.get_json()
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
        parts = text.split()
        cmd = parts[0].lower() if parts else ""
        
        if cmd == "/start":
            send_telegram_message("مرحباً يا ياسين! بوت التحليل الذكي بنظام النقاط جاهز.\n\nاستعمل:\n🔹 `/analyze BTCUSDT`\n🔹 `/analyze ETHUSDT`\n🔹 `/analyze SOLUSDT`", chat_id)
        elif cmd == "/analyze":
            symbol = parts[1].upper() if len(parts) > 1 else "BTCUSDT"
            send_telegram_message(f"⏳ جاري تحليل {symbol} عبر Binance...", chat_id)
            result = analyze_market(symbol)
            send_telegram_message(result, chat_id)
        else:
            send_telegram_message("الاستعمال الصحيح:\n`/analyze BTCUSDT` أو `/analyze SOLUSDT`", chat_id)
            
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
