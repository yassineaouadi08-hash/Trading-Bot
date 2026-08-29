import os
import ccxt
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

exchange = ccxt.bybit()

DEFAULT_PAIRS = ['BTC/USDT', 'SOL/USDT', 'PEPE/USDT', 'DOGE/USDT']

def fetch_and_analyze(symbol: str, timeframe: str = '15m'):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات الفنية بـ pandas البسيطة (بدون pandas_ta لتفادي مشاكل السرفر)
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        df['TR'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        bullish_engulfing = (prev['close'] < prev['open']) and (last['close'] > last['open']) and (last['close'] > prev['open'])
        bearish_engulfing = (prev['close'] > prev['open']) and (last['close'] < last['open']) and (last['close'] < prev['open'])
        pinbar_bull = (last['high'] - last['low']) > 3 * abs(last['close'] - last['open']) and (last['close'] - last['low']) > 0.6 * (last['high'] - last['low'])

        score = 0
        reasons = []

        if last['close'] > last['EMA_50'] > last['EMA_200']:
            score += 20
            reasons.append("✅ Trend صاعد فوق EMA 50/200 (+20)")
        elif last['close'] < last['EMA_50'] < last['EMA_200']:
            score -= 20
            reasons.append("🛑 Trend هابط تحت EMA 50/200 (-20)")

        if bullish_engulfing or pinbar_bull:
            score += 15
            reasons.append("✅ شمعة انعكاسية صاعدة Bullish Pattern (+15)")
        elif bearish_engulfing:
            score -= 15
            reasons.append("🛑 شمعة بيعية قوية Bearish Engulfing (-15)")

        rsi_val = last['RSI']
        if pd.notna(rsi_val):
            if 40 <= rsi_val <= 60:
                score += 10
                reasons.append(f"✅ RSI متوازن ({rsi_val:.1f}) (+10)")
            elif rsi_val > 70:
                score -= 10
                reasons.append(f"🛑 تشبع شرائي RSI Overbought ({rsi_val:.1f}) (-10)")

        if last['MACD'] > last['MACD_signal']:
            score += 10
            reasons.append("✅ تقاطع إيجابي MACD Bullish Cross (+10)")

        close_price = last['close']
        atr_val = last['ATR'] if pd.notna(last['ATR']) else (close_price * 0.01)
        
        if score >= 35:
            signal = "🟢 Strong LONG"
            sl = close_price - (1.5 * atr_val)
            tp = close_price + (3.0 * atr_val)
        elif score <= -30:
            signal = "🔴 Strong SHORT"
            sl = close_price + (1.5 * atr_val)
            tp = close_price - (3.0 * atr_val)
        else:
            signal = "⚪ WAIT / NO CLEAR ENTRY"
            sl, tp = 0, 0

        rr = round(abs(tp - close_price) / abs(close_price - sl), 2) if sl > 0 else 0

        report = f"📊 **تحليل العملة: {symbol} ({timeframe})**\n\n"
        report += f"🎯 **القرار:** {signal}\n"
        report += f"📈 **السعر الحالي:** {close_price:.4f}\n"
        if sl > 0:
            report += f"🛑 **Stop Loss (SL):** {sl:.4f}\n"
            report += f"🎯 **Take Profit (TP):** {tp:.4f}\n"
            report += f"⚖️ **Risk/Reward:** 1:{rr}\n\n"
        
        report += "🔍 **تفاصيل التحليل:**\n" + "\n".join(reasons)
        return report

    except Exception as e:
        return f"حدث خطأ أثناء تحليل {symbol}: {str(e)}"

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("جاري تحليل BTC, SOL والعملات الـ Hype...")
    for pair in DEFAULT_PAIRS:
        result = fetch_and_analyze(pair, timeframe='15m')
        await update.message.reply_text(result, parse_mode='Markdown')

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        symbol = context.args[0].upper() + "/USDT"
        tf = context.args[1] if len(context.args) > 1 else '15m'
        result = fetch_and_analyze(symbol, timeframe=tf)
        await update.message.reply_text(result, parse_mode='Markdown')
    else:
        await update.message.reply_text("الرجاء تحديد العملة، مثال:\n`/analyze SOL 15m`", parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("analyze", analyze))
    print("Bot started...")
    app.run_polling()
