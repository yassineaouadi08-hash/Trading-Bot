import os
import requests
import pandas as pd
import numpy as np
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# إعدادات الـ Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# توكن التيليجرام الخاص بك (عوضه بالتوكن الصحيح)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# 1. إعداد خادم Flask البسيط لترضية منصة Render وتخلي البوت ديما يخدم
app = Flask(__name__)

@app.route('/')
def home():
    return "Trading Bot is running!"

@app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# 2. وظائف جلب وتحليل البيانات (Binance & Bybit)
def fetch_binance_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
        return None
    except Exception as e:
        logging.error(f"Binance Error: {e}")
        return None

def fetch_bybit_data(symbol, interval):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit=100"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('retCode') == 0 and len(data['result']['list']) > 0:
            list_data = data['result']['list']
            list_data.reverse()
            df = pd.DataFrame(list_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
        return None
    except Exception as e:
        logging.error(f"Bybit Error: {e}")
        return None

def calculate_indicators(df):
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def analyze_market(df):
    score = 50 
    reasons = []
    last_row = df.iloc[-1]
    
    if last_row['close'] > last_row['EMA20'] and last_row['EMA20'] > last_row['EMA50']:
        score += 25
        reasons.append("✅ Strong Bullish Trend (Price > EMA20 > EMA50)")
    elif last_row['close'] > last_row['EMA50']:
        score += 15
        reasons.append("✅ Price above EMA 50")
    else:
        score -= 20
        reasons.append("❌ Bearish Trend (Price below key EMAs)")

    rsi = last_row['RSI']
    if 45 <= rsi <= 65:
        score += 10
        reasons.append(f"ℹ️ RSI in healthy zone ({rsi:.1f})")
    elif rsi < 35:
        score += 15
        reasons.append(f"🟢 RSI Oversold / Buying opportunity ({rsi:.1f})")
    elif rsi > 65:
        score -= 10
        reasons.append(f"🔴 RSI getting overbought ({rsi:.1f})")

    if score >= 75:
        signal = "🚀 Strong LONG (فرصة قوية صعود)"
    elif 60 <= score < 75:
        signal = "📈 LONG (دخول صفقة شراء)"
    elif 45 <= score < 60:
        signal = "⏳ WAIT (السوق محايد، انتظر تأكيد)"
    elif 30 <= score < 44:
        signal = "📉 SHORT (دخول صفقة بيع)"
    else:
        signal = "🩸 Strong SHORT (فرصة قوية نزول)"

    return signal, score, reasons

# 3. أوامر التيليجرام
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ مثال للاستخدام:\n`/analyze BTCUSDT 15`\n`/analyze SOLUSDT 1h`", parse_mode="Markdown")
        return
    
    symbol = args[0].upper()
    interval = args[1]
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    df = fetch_binance_data(symbol, interval)
    if df is None:
        df = fetch_bybit_data(symbol, interval)

    if df is None:
        await update.message.reply_text(f"❌ لم يتم العثور على بيانات للعملة {symbol}.")
        return

    df = calculate_indicators(df)
    signal, score, reasons = analyze_market(df)
    current_price = df.iloc[-1]['close']

    response_msg = (
        f"📊 **تقرير تحليل السوق**\n"
        f"🪙 **العملة:** `{symbol}` | **الفريم:** `{interval}`\n\n"
        f"🎯 **الإشارة:** **{signal}**\n"
        f"⭐ **الـ Score:** `{score} / 100`\n"
        f"💵 **السعر الحالي:** `{current_price}`\n\n"
        f"📋 **الأسباب الفنية:**\n" + "\n".join(reasons)
    )
    
    await update.message.reply_text(response_msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 أهلاً بك يا ياسين في بوت التحليل الذكي!\n\n"
        "للتحليل، استعمل الأمر:\n"
        "🔹 `/analyze BTCUSDT 15`\n"
        "🔹 `/analyze SOLUSDT 1h`\n"
        "🔹 `/analyze HYPEUSDT 4h`\n"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

def main():
    # تشغيل سيرفر Flask في خلفية منفصلة (Thread)
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # تشغيل بوت تليجرام
    app_telegram = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("analyze", analyze_command))
    
    print("Telegram Bot & Flask Server are running...")
    app_telegram.run_polling()

if __name__ == "__main__":
    main()
