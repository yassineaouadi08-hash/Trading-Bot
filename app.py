import os
import ccxt
import pandas as pd
import pandas_ta as ta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("8971401995: AAErEwwoauKH_noctI2Xm
WE1noVNDu7ELx4")
exchange = ccxt.bybit() # أو ccxt.binance()

# قائمة العملات المحددة والـ Hype
DEFAULT_PAIRS = ['BTC/USDT', 'SOL/USDT', 'PEPE/USDT', 'DOGE/USDT']

def fetch_and_analyze(symbol: str, timeframe: str = '15m'):
    try:
        # 1. جلب بيانات الشموع (OHLCV)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. حساب المؤشرات الفنية
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['EMA_200'] = ta.ema(df['close'], length=200)
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_signal'] = macd['MACDs_12_26_9']
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 3. تحليل الشموع اليابانية (Candlestick Patterns)
        bullish_engulfing = (prev['close'] < prev['open']) and (last['close'] > last['open']) and (last['close'] > prev['open'])
        bearish_engulfing = (prev['close'] > prev['open']) and (last['close'] < last['open']) and (last['close'] < prev['open'])
        pinbar_bull = (last['high'] - last['low']) > 3 * abs(last['close'] - last['open']) and (last['close'] - last['low']) > 0.6 * (last['high'] - last['low'])

        # 4. تطبيق نظام التقييم (Scoring System)
        score = 0
        reasons = []

        # Trend Score (20 pts)
        if last['close'] > last['EMA_50'] > last['EMA_200']:
            score += 20
            reasons.append("✅ Trend صاعد فوق EMA 50/200 (+20)")
        elif last['close'] < last['EMA_50'] < last['EMA_200']:
            score -= 20
            reasons.append("🛑 Trend هابط تحت EMA 50/200 (-20)")

        # Candlestick Score (15 pts)
        if bullish_engulfing or pinbar_bull:
            score += 15
            reasons.append("✅ شمعة انعكاسية صاعدة Bullish Pattern (+15)")
        elif bearish_engulfing:
            score -= 15
            reasons.append("🛑 شمعة بيعية قوية Bearish Engulfing (-15)")

        # RSI Score (10 pts)
        if 40 <= last['RSI'] <= 60:
            score += 10
            reasons.append(f"✅ RSI متوازن ({last['RSI']:.1f}) (+10)")
        elif last['RSI'] > 70:
            score -= 10
            reasons.append(f"🛑 تشبع شرائي RSI Overbought ({last['RSI']:.1f}) (-10)")

        # MACD Score (10 pts)
        if last['MACD'] > last['MACD_signal']:
            score += 10
            reasons.append("✅ تقاطع إيجابي MACD Bullish Cross (+10)")

        # 5. تحديد القرار وإدارة المخاطر (SL / TP)
        close_price = last['close']
        atr_val = last['ATR']
        
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

        # صياغة التقرير النهائي
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

# أوامر التليجرام
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
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("analyze", analyze))
    print("Bot started...")
    app.run_polling()
