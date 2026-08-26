"""
Bot Saham Danar v2.5 - Dengan Candlestick Chart 6 Panel & Screener 300+ Saham
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from functools import partial

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv

from utils import (
    normalize_ticker, fetch_stock_data, fetch_stock_info,
    format_large_number, now_wib, format_price, PERIOD_MAP, PERIOD_LABEL
)
from signals import compute_indicators, generate_signals
from chart import generate_chart
from screener import run_screener, format_screener_results, FILTER_MODES, VALID_FILTERS, IDX_STOCKS
from stock_list import get_idx_stocks

load_dotenv()

# ── Logging ──
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ── Config ──
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    print("❌ ERROR: TELEGRAM_TOKEN tidak ditemukan!")
    sys.exit(1)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", 8080))

# ── Help Text ──
HELP_TEXT = (
    "📈 *Danar Bot Saham v2.5*\n\n"
    "📊 *Perintah Dasar:*\n"
    "/start - Menu utama\n"
    "/help - Bantuan ini\n\n"
    "📈 *Harga & Chart:*\n"
    "/h BBCA - Info harga saham\n"
    "/c BBCA - Chart candlestick 6 panel ⭐\n"
    "/chart BBCA - Chart candlestick\n\n"
    "🎯 *Analisis:*\n"
    "/sn BBCA - Sinyal beli/jual\n"
    "/signal BBCA - Sinyal beli/jual\n\n"
    "🔍 *Screener:*\n"
    "/s macd - Screening dengan filter\n"
    "/screener macd - Screener lengkap\n\n"
    "📌 *Filter Screener:*\n"
    "`macd` `volume` `rsi20` `rsi50` `rsi80`\n"
    "`stoch5` `stoch40` `beli` `jual`\n"
    "`beli_kuat` `jual_kuat` `semua`\n"
    "_Contoh:_ `/s macd volume beli`\n\n"
    "⚠️ Data Yahoo Finance delay ±15 menit\n"
    "⚠️ Bukan saran investasi"
)

# ── Handlers ──

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nama = user.first_name if user else "Investor"
    await update.message.reply_text(
        f"Halo *{nama}*! 👋\n\n"
        "Selamat datang di *Danar Bot Saham v2.5* 📈\n"
        "Bot dengan candlestick chart 6 panel & screener 300+ saham.\n\n"
        "Ketik /help untuk daftar perintah.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def cmd_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Gunakan: `/h BBCA` atau `/h BBRI`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    raw = context.args[0]
    ticker = normalize_ticker(raw)
    msg = await update.message.reply_text(f"⏳ Mengambil data `{ticker}`...", parse_mode=ParseMode.MARKDOWN)
    
    try:
        df = fetch_stock_data(ticker, period="5d")
        info = fetch_stock_info(ticker)
        
        if df.empty:
            await msg.edit_text(f"❌ Data `{ticker}` tidak ditemukan.", parse_mode=ParseMode.MARKDOWN)
            return
        
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        change = ((last["Close"] - prev["Close"]) / prev["Close"]) * 100 if prev["Close"] else 0
        
        name = info.get("longName") or info.get("shortName") or ticker
        text = (
            f"📊 *{name}* (`{ticker}`)\n"
            f"⏱ {now_wib()}\n\n"
            f"💰 Harga: `{format_price(last['Close'])}`\n"
            f"📈 Perubahan: `{change:+.2f}%`\n"
            f"📊 Volume: `{format_large_number(last['Volume'])}`\n"
            f"📉 High/Low: `{format_price(last['High'])}` / `{format_price(last['Low'])}`\n\n"
            f"💡 /chart `{raw.upper()}` - Lihat chart candlestick"
        )
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"cmd_harga error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)


async def cmd_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Gunakan: `/c BBCA` atau `/c BBCA 3m`\n"
            "Periode: `1w` `1m` `3m` `6m` `1y` `2y`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    raw = context.args[0]
    ticker = normalize_ticker(raw)
    period_input = context.args[1].lower() if len(context.args) > 1 else "6m"
    period = PERIOD_MAP.get(period_input, "3mo")
    period_label = PERIOD_LABEL.get(period, period)
    
    msg = await update.message.reply_text(
        f"📊 Membuat chart `{ticker}` ({period_label})...\n⏳ Mohon tunggu 10-15 detik",
        parse_mode=ParseMode.MARKDOWN,
    )
    
    try:
        df = fetch_stock_data(ticker, period=period)
        if df.empty or len(df) < 10:
            await msg.edit_text(
                f"⚠️ Data tidak cukup untuk `{ticker}` ({len(df)} hari).\n"
                f"Minimal 10 hari data diperlukan.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        
        df_ind = compute_indicators(df)
        result = generate_signals(df_ind)
        buf = generate_chart(df, ticker, period)
        
        # Caption
        last = df.iloc[-1]
        change = ((last["Close"] - df.iloc[-2]["Close"]) / df.iloc[-2]["Close"]) * 100 if len(df) > 1 else 0
        caption = (
            f"📈 *{raw.upper()}* — {period_label}\n"
            f"💰 {format_price(last['Close'])} ({change:+.2f}%)\n"
            f"🎯 {result['emoji']} *{result['signal']}* | Skor: `{result['score']}`\n"
            f"⏱ {now_wib()}\n"
            f"⚠️ _Bukan saran investasi_"
        )
        
        await update.message.reply_photo(
            photo=buf,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
        await msg.delete()
        
    except Exception as e:
        logger.error(f"cmd_chart error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:150]}", parse_mode=ParseMode.MARKDOWN)


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Gunakan: `/sn BBCA`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    raw = context.args[0]
    ticker = normalize_ticker(raw)
    msg = await update.message.reply_text(f"🔍 Menganalisis `{ticker}`...", parse_mode=ParseMode.MARKDOWN)
    
    try:
        df = fetch_stock_data(ticker, period="6mo")
        if df.empty or len(df) < 30:
            await msg.edit_text(f"❌ Data tidak cukup untuk `{ticker}`", parse_mode=ParseMode.MARKDOWN)
            return
        
        df_ind = compute_indicators(df)
        result = generate_signals(df_ind)
        
        last = df_ind.iloc[-1]
        price = last.get("Close", 0)
        
        details = "\n".join(f"• {d}" for d in result["details"])
        text = (
            f"{result['emoji']} *SINYAL: {result['signal']}* — `{raw.upper()}`\n"
            f"⏱ {now_wib()}\n"
            f"💰 Harga: `{format_price(price)}`\n"
            f"⚖️ Skor: `{result['score']}`\n\n"
            f"📋 *Analisis:*\n{details}\n\n"
            f"📈 /c `{raw.upper()}` - Lihat chart"
        )
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"cmd_signal error: {e}")
        await msg.edit_text(f"❌ Error: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)


async def cmd_screener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_args = [a.lower() for a in (context.args or [])]
    
    if not raw_args:
        await update.message.reply_text(
            "🔍 *Screener Saham IDX*\n\n"
            "Filter tersedia:\n"
            "`macd` `volume` `rsi20` `rsi50` `rsi80`\n"
            "`stoch5` `stoch40` `beli` `jual`\n"
            "`beli_kuat` `jual_kuat` `semua`\n\n"
            "Contoh: `/s macd volume beli`\n"
            "Gunakan `/s screener` untuk semua saham",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    invalid = [f for f in raw_args if f not in VALID_FILTERS]
    if invalid:
        await update.message.reply_text(
            f"⚠️ Filter tidak dikenal: `{', '.join(invalid)}`\n\n"
            "Filter valid: `macd` `volume` `rsi20` `rsi50` `rsi80` `stoch5` `stoch40` `beli` `jual` `beli_kuat` `jual_kuat` `semua`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    
    filters = list(dict.fromkeys(raw_args))
    filter_label = " + ".join(FILTER_MODES.get(f, f) for f in filters)
    
    msg = await update.message.reply_text(
        f"🔍 *Screener IDX* berjalan...\n"
        f"📋 Filter: *{filter_label}*\n"
        f"⏳ Memindai {len(IDX_STOCKS)} saham — mohon tunggu...",
        parse_mode=ParseMode.MARKDOWN,
    )
    
    try:
        loop = asyncio.get_event_loop()
        progress_state = {"last": 0}
        
        def on_progress(done, total, valid, no_data, errors):
            if done - progress_state["last"] < 5 and done != total:
                return
            progress_state["last"] = done
            pct = (done / total * 100) if total else 100
            text = (
                f"🔍 *Screener IDX* berjalan...\n"
                f"📋 Filter: *{filter_label}*\n"
                f"📡 Progres: `{done}/{total}` ({pct:.0f}%)\n"
                f"✅ Valid: `{valid}` | ⚪ No data: `{no_data}` | ❌ Gagal: `{errors}`"
            )
            asyncio.run_coroutine_threadsafe(
                msg.edit_text(text, parse_mode=ParseMode.MARKDOWN),
                loop,
            )
        
        results, total_scanned, total_valid, total_no_data, total_errors = await loop.run_in_executor(
            None,
            partial(run_screener, filters, None, 5, on_progress),
        )
        
        messages = format_screener_results(results, filters, total_scanned, total_valid, total_no_data, total_errors)
        await msg.edit_text(messages[0], parse_mode=ParseMode.MARKDOWN)
        for extra in messages[1:]:
            await update.message.reply_text(extra, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"cmd_screener error: {e}")
        await msg.edit_text(f"❌ Screener gagal: {str(e)[:150]}", parse_mode=ParseMode.MARKDOWN)


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Perintah tidak dikenal.\n\n"
        "Gunakan /help untuk melihat daftar perintah.\n\n"
        "💡 Contoh: `/c BBCA` untuk chart candlestick"
    )


# ── Command Menu ──
BOT_COMMANDS = [
    BotCommand("start", "Menu utama"),
    BotCommand("help", "Bantuan / daftar perintah"),
    BotCommand("h", "Info harga saham"),
    BotCommand("c", "Chart candlestick 6 panel"),
    BotCommand("chart", "Chart candlestick"),
    BotCommand("sn", "Sinyal beli/jual"),
    BotCommand("signal", "Sinyal beli/jual"),
    BotCommand("s", "Screener IDX"),
    BotCommand("screener", "Screener IDX"),
]


# ── Main ──
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("bantuan", cmd_help))
    
    # Harga
    app.add_handler(CommandHandler("h", cmd_harga))
    app.add_handler(CommandHandler("saham", cmd_harga))
    
    # Chart
    app.add_handler(CommandHandler("c", cmd_chart))
    app.add_handler(CommandHandler("chart", cmd_chart))
    
    # Signal
    app.add_handler(CommandHandler("sn", cmd_signal))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("sinyal", cmd_signal))
    
    # Screener
    app.add_handler(CommandHandler("s", cmd_screener))
    app.add_handler(CommandHandler("screener", cmd_screener))
    
    # Unknown
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown))
    
    # Set command menu
    app.bot.set_my_commands(BOT_COMMANDS)
    
    print("=" * 60)
    print("🤖 BOT SAHAM DANAR v2.5 - CANDLESTICK 6 PANEL")
    print("=" * 60)
    print(f"📌 Token: ✓")
    print(f"📌 Watchlist: {len(IDX_STOCKS)} saham")
    print(f"📌 Chart: 6 panel (Volume, Candlestick, RSI, Stoch5, Stoch40, MACD)")
    print(f"📌 Screener: Multi-thread 300+ saham")
    print(f"📌 Environment: {ENVIRONMENT}")
    print("=" * 60)
    print("📊 Bot siap menerima perintah!")
    print("💡 Contoh: /c BBCA, /s macd, /sn BBRI")
    print("=" * 60)
    
    if ENVIRONMENT == "production":
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path=TELEGRAM_TOKEN)
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
