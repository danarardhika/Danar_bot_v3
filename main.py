"""
Bot Saham Telegram — Versi Ringkas (3 File)
Fitur: Info saham, Chart, Sinyal, Screener
"""
import os
import asyncio
import logging
import io
import time
import random
from datetime import datetime
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# ─── CONFIG ─────────────────────────────────────────────────────────────
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

WIB = pytz.timezone("Asia/Jakarta")

# Daftar saham IDX (hardcode + bisa diperluas via cache)
IDX_STOCKS = [
    "BBCA","BBRI","BMRI","BBNI","BRIS","BTPS","BNGA","NISP","BBTN","BDMN",
    "BJBR","BJTM","PNBN","MEGA","BNLI","AGRO","BBYB","BMAS","BNBA","BSIM",
    "MAYA","NOBU","BACA","BABP","BVIC","INPC","SDRA","BGTG","DNAR","BCIC",
    "BPTN","BSSR","ADMF","MFIN","PNLF","BCAP","BFIN","WOMF","CFIN","TIFA",
    "VRNA","LPPS","MKNT","BESS","ABMM","ADRO","PTBA","INCO","ANTM","MDKA",
    "BRMS","HRUM","BUMI","MEDC","ELSA","AKRA","TINS","ITMG","PTRO","DOID",
    "ADMR","BYAN","GEMS","MBAP","DEWA","ENRG","ESSA","FIRE","MAHA","MYOH",
    "KKGI","BIPI","RUIS","SMRU","SMMT","GTBO","ARTI","PKPK","DSSA","COAL",
    "MBSS","PSAB","IATA","INDY","GAMA","PGAS","PGEO","RAJA","WINS","HMPD",
    "RIGS","LEAD","TLKM","EXCL","ISAT","GOTO","EMTK","BUKA","MNCN","SCMA",
    "VIVA","LINK","DATA","DMMX","MLPL","MSKY","MCAS","WIFI","MTDL","KREN",
    "ATIC","INET","LAND","TELE","IBST","SUPR","TOWR","UNVR","ICBP","INDF",
    "MYOR","ULTJ","SIDO","HMSP","GGRM","ACES","MAPI","LPPF","RALS","AMRT",
    "MIDI","CSAP","MPPA","GOOD","HOKI","SKLT","DLTA","MRAT","CLEO","BOBA",
    "CEKA","FAST","PZZA","DKFT","RANC","IIKP","HERO","AISA","CAMP","KEJU",
    "ALTO","ROTI","SKBM","STTP","TBIG","MLBI","ADES","PSGO","PCAR","WMUU",
    "WIIM","ITIC","KLBF","KAEF","HEAL","MIKA","SILO","TSPC","DVLA","PYFA",
    "INAF","PEHA","PRIM","RSGK","SAME","PRDA","CARE","IRRA","OMED","MITI",
    "BSDE","SMRA","CTRA","PWON","LPKR","APLN","DILD","JRPT","KIJA","MTLA",
    "PLIN","PPRO","RDTX","SMDM","GPRA","BKSL","GWSA","LPCK","MMLP","ELTY",
    "DMAS","NIRO","MKPI","GMTD","LCGP","FMII","TARA","URBN","RISE","POLL",
    "BCIP","JSMR","WSKT","WTON","ADHI","WIKA","PTPP","META","NRCA","TOTL",
    "DGIK","CMNP","RODA","IDPR","NUSA","KPIG","BALI","ACST","MTRA","PBSA",
    "WEGE","KDSI","GIAA","CMPP","BIRD","SAFE","SMDR","TMAS","ASSA","JAYA",
    "NELI","LRNA","WEHA","INDX","TAXI","MIRA","AALI","LSIP","SIMP","TBLA",
    "BWPT","GZCO","JAWA","PALM","SGRO","SSMS","BISI","DSFI","ANJT","SMAR",
    "MGNA","UNSP","TPIA","BRPT","SMGR","INTP","ARNA","MLIA","TOTO","VOKS",
    "UNIC","EKAD","BTON","GDST","LION","LMSH","NIKL","PICO","ALKA","FASW",
    "ALDO","SPMA","KBRI","TIRT","DPNS","SRSN","AKKU","AMFG","MDKI","AGII",
    "IGTA","INAI","KRAS","ASII","UNTR","AUTO","GJTL","SMSM","GDYR","IMAS",
    "INDS","LPIN","MASA","STAR","ADMG","PRAS","BRAM","NIPS","BOLT","KBLM",
    "VKTR","KBLI","JECC","SCCO","SUCF","IKBI","SMCB","SMBR","WSBP","RICY",
    "SSTM","TFCO","TRIS","UNIT","ARGO","CNTB","PBRX","POLY","POLU","ABBA",
    "TMPO","FORU","BAYU","BUVA","INPP","JSPT","MABA","PDES","PTSP","SONA",
    "PANR","PNSE","HOME","DUTI","IGAR","INCI","KICI","LMPI","LTLS","MERK",
    "MYRX","PEGE","PGLI","SEMA","SIPD","SLIS","SMPL","SRTG","SURI","SWAT",
    "TALF","TERI","TIRA","TNCA","TOOL","TOPS","TRIM","TURI","UANG","VICI",
    "WICO","YELO","ZBRA","ABDA","AHAP","AMAG","ASBI","ASDM","ASEI","ASMI",
    "ASRM","LPGI","MREI","PNIN","TUGU",
]

PERIOD_MAP = {"1w":"5d","1m":"1mo","3m":"3mo","6m":"6mo","1y":"1y","2y":"2y"}
PERIOD_LABEL = {"5d":"1 Minggu","1mo":"1 Bulan","3mo":"3 Bulan","6mo":"6 Bulan","1y":"1 Tahun","2y":"2 Tahun"}

# ─── UTILITIES ──────────────────────────────────────────────────────────
def normalize_ticker(t: str) -> str:
    t = t.upper().strip()
    return t + ".JK" if "." not in t and len(t) <= 6 else t

def fetch_data(ticker: str, period: str = "3mo") -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
    if df.empty:
        raise ValueError(f"Data tidak ditemukan untuk {ticker}")
    return df

def now_wib() -> str:
    return datetime.now(WIB).strftime("%d/%m/%Y %H:%M WIB")

# ─── INDICATORS ──────────────────────────────────────────────────────────
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    
    # RSI 14
    delta = c.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # MACD (12,26,9)
    exp1 = c.ewm(span=12, adjust=False).mean()
    exp2 = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    
    # Bollinger Bands (20,2)
    ma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df["BB_upper"] = ma20 + 2 * std20
    df["BB_middle"] = ma20
    df["BB_lower"] = ma20 - 2 * std20
    
    # SMA5
    df["SMA5"] = c.rolling(5).mean()
    
    # Slow Stochastic
    for kp, ks, ds in [(5,3,3), (40,3,3)]:
        ll = l.rolling(kp).min()
        hh = h.rolling(kp).max()
        raw_k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
        slow_k = raw_k.rolling(ks).mean()
        d = slow_k.rolling(ds).mean()
        df[f"STOCH{kp}_K"] = slow_k
        df[f"STOCH{kp}_D"] = d
    
    # Volume SMA20
    df["Vol_SMA20"] = v.astype(float).rolling(20).mean()
    return df

def generate_signal(df: pd.DataFrame) -> dict:
    if len(df) < 52:
        return {"signal":"TIDAK CUKUP DATA","emoji":"⚠️","score":0,"details":[]}
    
    row, prev = df.iloc[-1], df.iloc[-2]
    score, details = 0, []
    
    # RSI
    rsi = row.get("RSI")
    if pd.notna(rsi):
        if rsi < 30: score += 2; details.append(f"RSI {rsi:.1f} — Oversold 🟢")
        elif rsi < 40: score += 1; details.append(f"RSI {rsi:.1f} — Mendekati oversold 🟩")
        elif rsi > 70: score -= 2; details.append(f"RSI {rsi:.1f} — Overbought 🔴")
        elif rsi > 60: score -= 1; details.append(f"RSI {rsi:.1f} — Mendekati overbought 🟥")
        else: details.append(f"RSI {rsi:.1f} — Netral 🟡")
    
    # MACD
    macd, sig, pm, ps = row.get("MACD"), row.get("MACD_signal"), prev.get("MACD"), prev.get("MACD_signal")
    if all(pd.notna(x) for x in [macd, sig, pm, ps]):
        if pm <= ps and macd > sig: score += 2; details.append("MACD — Bullish crossover 🟢")
        elif pm >= ps and macd < sig: score -= 2; details.append("MACD — Bearish crossover 🔴")
        elif macd > sig: score += 1; details.append("MACD — Bullish 🟩")
        else: score -= 1; details.append("MACD — Bearish 🟥")
    
    # Bollinger
    close, upper, lower, mid = row.get("Close"), row.get("BB_upper"), row.get("BB_lower"), row.get("BB_middle")
    if all(pd.notna(x) for x in [close, upper, lower]):
        if close < lower: score += 2; details.append("Harga di bawah BB Lower 🟢")
        elif close > upper: score -= 2; details.append("Harga di atas BB Upper 🔴")
        elif close < mid: details.append("Harga di bawah BB Middle")
        else: details.append("Harga di atas BB Middle")
    
    # Stochastics
    for kp in [5, 40]:
        k, d, pk, pd = row.get(f"STOCH{kp}_K"), row.get(f"STOCH{kp}_D"), prev.get(f"STOCH{kp}_K"), prev.get(f"STOCH{kp}_D")
        if all(pd.notna(x) for x in [k, d, pk, pd]):
            if pk <= pd and k > d and k < 30: score += 2; details.append(f"Stoch({kp}) GC di oversold 🟢")
            elif pk >= pd and k < d and k > 70: score -= 2; details.append(f"Stoch({kp}) DC di overbought 🔴")
            elif k < 20: score += 1; details.append(f"Stoch({kp}) %K {k:.1f} — Oversold 🟩")
            elif k > 80: score -= 1; details.append(f"Stoch({kp}) %K {k:.1f} — Overbought 🟥")
            else: details.append(f"Stoch({kp}) %K {k:.1f} — Netral")
    
    if score >= 5: signal, emoji = "BELI KUAT", "🟢"
    elif score >= 2: signal, emoji = "BELI", "🟩"
    elif score <= -5: signal, emoji = "JUAL KUAT", "🔴"
    elif score <= -2: signal, emoji = "JUAL", "🟥"
    else: signal, emoji = "TAHAN", "🟡"
    
    return {"signal": signal, "emoji": emoji, "score": score, "details": details}

# ─── CHART GENERATOR ──────────────────────────────────────────────────────
def generate_chart(df: pd.DataFrame, ticker: str, period: str = "3mo") -> io.BytesIO:
    df = compute_indicators(df).dropna(subset=["Close"])
    n = len(df)
    x = list(range(n))
    colors = {"up":"#26a69a","down":"#ef5350","bg":"#ffffff","grid":"#e0e0e0","text":"#111111"}
    
    fig = plt.figure(figsize=(13, 13), facecolor=colors["bg"])
    gs = gridspec.GridSpec(6, 1, height_ratios=[0.85, 3.8, 1.25, 1.25, 1.25, 1.35], hspace=0)
    ax_vol, ax_candle, ax_rsi, ax_st5, ax_st40, ax_macd = [fig.add_subplot(gs[i], sharex=ax_vol) if i > 0 else fig.add_subplot(gs[0]) for i in range(6)]
    
    for ax in [ax_vol, ax_candle, ax_rsi, ax_st5, ax_st40, ax_macd]:
        ax.set_facecolor(colors["bg"])
        ax.tick_params(colors=colors["text"], labelsize=7.5)
        ax.grid(axis="y", color=colors["grid"], linewidth=0.5)
    
    # Volume
    vol_colors = [colors["up"] if df["Close"].iloc[i] >= df["Open"].iloc[i] else colors["down"] for i in range(n)]
    ax_vol.bar(x, df["Volume"].values, color=vol_colors, width=0.7, alpha=0.85)
    if "Vol_SMA20" in df.columns:
        ax_vol.plot(x, df["Vol_SMA20"].values, color="#111111", lw=0.9)
    ax_vol.set_title(f"*){ticker}   {df.index[-1].strftime('%Y-%m-%d')} — Daily chart", fontsize=9.5, fontweight="bold", loc="left")
    
    # Candlestick
    if "BB_upper" in df.columns:
        ax_candle.fill_between(x, df["BB_upper"], df["BB_lower"], color="#c8d8f0", alpha=0.4)
        ax_candle.plot(x, df["BB_upper"], color="#3366cc", lw=0.85)
        ax_candle.plot(x, df["BB_middle"], color="#3366cc", lw=0.85, ls="--")
        ax_candle.plot(x, df["BB_lower"], color="#3366cc", lw=0.85)
    if "SMA5" in df.columns:
        ax_candle.plot(x, df["SMA5"], color="#009900", lw=1.15)
    for i, (_, r) in enumerate(df.iterrows()):
        col = colors["up"] if r["Close"] >= r["Open"] else colors["down"]
        ax_candle.plot([i,i], [r["Low"], r["High"]], color=col, lw=0.9)
        ax_candle.bar(i, max(abs(r["Close"]-r["Open"]), (r["High"]-r["Low"])*0.005), bottom=min(r["Open"], r["Close"]), color=col, width=0.68)
    
    # RSI
    if "RSI" in df.columns:
        ax_rsi.plot(x, df["RSI"].values, color="#aa00aa", lw=1.1)
        ax_rsi.axhline(80, color="#cc0000", lw=0.75, alpha=0.85)
        ax_rsi.axhline(20, color="#0000cc", lw=0.75, alpha=0.85)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_yticks([20, 50, 80])
    
    # Stochastics
    for ax, kp in [(ax_st5, 5), (ax_st40, 40)]:
        if f"STOCH{kp}_K" in df.columns:
            k = df[f"STOCH{kp}_K"].values
            d = df[f"STOCH{kp}_D"].values
            ax.plot(x, k, color="#009900", lw=1.1)
            ax.plot(x, d, color="#cc0000", lw=0.9, ls="--")
            ax.axhline(80, color="#cc0000", lw=0.75, alpha=0.85)
            ax.axhline(20, color="#0000cc", lw=0.75, alpha=0.85)
            ax.set_ylim(-2, 105)
            ax.set_yticks([20, 50, 80])
    
    # MACD
    if "MACD" in df.columns:
        hist = df["MACD_hist"].values
        hcol = ["#26a69a" if v >= 0 else "#ef5350" for v in hist]
        ax_macd.bar(x, hist, color=hcol, width=0.7, alpha=0.85)
        ax_macd.plot(x, df["MACD"].values, color="#0000cc", lw=1.1)
        ax_macd.plot(x, df["MACD_signal"].values, color="#cc00cc", lw=0.9, ls="--")
        ax_macd.axhline(0, color="#bbbbbb", lw=0.6)
    
    # X-axis
    for ax in [ax_vol, ax_candle, ax_rsi, ax_st5, ax_st40]:
        plt.setp(ax.get_xticklabels(), visible=False)
    step, tick_pos = max(1, n//10), list(range(0, n, max(1, n//10)))
    ax_macd.set_xticks(tick_pos)
    ax_macd.set_xticklabels([df.index[i].strftime("%b %d") for i in tick_pos], fontsize=8)
    ax_macd.set_xlim(-0.8, n-0.2)
    
    fig.subplots_adjust(left=0.02, right=0.90, top=0.96, bottom=0.04)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, facecolor=colors["bg"])
    plt.close(fig)
    buf.seek(0)
    return buf

# ─── SCREENER ─────────────────────────────────────────────────────────────
FILTER_FN = {
    "macd": lambda r,p: p.get("macd",0) <= p.get("macd_sig",0) and r.get("macd",0) > r.get("macd_sig",0),
    "volume": lambda r,p: r.get("volume",0) >= 2 * p.get("volume",0) if p.get("volume",0) > 0 else False,
    "rsi20": lambda r,p: r.get("rsi",100) <= 20 if r.get("rsi") else False,
    "rsi50": lambda r,p: (p.get("rsi",0) < 50 <= r.get("rsi",0)) if all(x is not None for x in [r.get("rsi"), p.get("rsi")]) else False,
    "rsi80": lambda r,p: r.get("rsi",0) >= 80 if r.get("rsi") else False,
    "stoch5": lambda r,p: p.get("k5",0) <= p.get("d5",0) and r.get("k5",0) > r.get("d5",0),
    "stoch40": lambda r,p: p.get("k40",0) <= p.get("d40",0) and r.get("k40",0) > r.get("d40",0),
    "beli": lambda r,p: "BELI" in r.get("signal",""),
    "jual": lambda r,p: "JUAL" in r.get("signal",""),
    "beli_kuat": lambda r,p: r.get("signal") == "BELI KUAT",
    "jual_kuat": lambda r,p: r.get("signal") == "JUAL KUAT",
    "semua": lambda r,p: True,
}
VALID_FILTERS = set(FILTER_FN.keys())

def scan_one(code: str) -> tuple[Optional[dict], str]:
    ticker = normalize_ticker(code)
    for attempt in range(3):
        try:
            if attempt > 0: time.sleep((2**attempt) + random.uniform(0.5, 2.0))
            df = fetch_data(ticker, period="6mo")
            if len(df) < 52: return None, "no_data"
            
            df_ind = compute_indicators(df)
            sig = generate_signal(df_ind)
            cur, prev = df_ind.iloc[-1], df_ind.iloc[-2]
            
            def g(r,k): return None if r.get(k) is None or pd.isna(r.get(k)) else float(r.get(k))
            
            row = {
                "close": g(cur,"Close") or 0,
                "volume": float(cur.get("Volume",0)),
                "rsi": g(cur,"RSI"),
                "macd": g(cur,"MACD"),
                "macd_sig": g(cur,"MACD_signal"),
                "k5": g(cur,"STOCH5_K"),
                "d5": g(cur,"STOCH5_D"),
                "k40": g(cur,"STOCH40_K"),
                "d40": g(cur,"STOCH40_D"),
                "signal": sig["signal"],
                "emoji": sig["emoji"],
                "score": sig["score"],
            }
            prv = {
                "volume": float(prev.get("Volume",0)),
                "rsi": g(prev,"RSI"),
                "macd": g(prev,"MACD"),
                "macd_sig": g(prev,"MACD_signal"),
                "k5": g(prev,"STOCH5_K"),
                "d5": g(prev,"STOCH5_D"),
                "k40": g(prev,"STOCH40_K"),
                "d40": g(prev,"STOCH40_D"),
            }
            return {"code": code, "ticker": ticker, "row": row, "prev": prv}, "ok"
        except: continue
    return None, "error"

def run_screener(filters: list[str], progress_callback=None) -> tuple[list, int, int, int, int]:
    stocks = IDX_STOCKS
    results, completed, no_data, errors = [], 0, 0, 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_one, code): code for code in stocks}
        for future in as_completed(futures):
            data, status = future.result() or (None, "error")
            if data: results.append(data)
            elif status == "no_data": no_data += 1
            else: errors += 1
            completed += 1
            if progress_callback:
                try: progress_callback(completed, len(stocks), len(results), no_data, errors)
                except: pass
    
    fns = [FILTER_FN[f] for f in filters if f in FILTER_FN]
    filtered = [d for d in results if all(fn(d["row"], d["prev"]) for fn in fns)]
    filtered.sort(key=lambda d: (-d["row"]["score"], -(d.get("change_pct",0))))
    return filtered, len(stocks), len(results), no_data, errors

# ─── TELEGRAM HANDLERS ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Selamat datang di Danar Bot Saham! Ketik /bantuan")

async def bantuan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = """📈 *Danar Bot Saham*
/h <kode> — Info harga
/c <kode> [periode] — Chart (1w/1m/3m/6m/1y/2y)
/sn <kode> — Sinyal teknikal
/s [filter...] — Screener IDX
Filter: macd volume rsi20 rsi50 rsi80 stoch5 stoch40 beli jual beli_kuat jual_kuat semua
⚠️ Bukan saran investasi"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def saham(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ /saham BBCA")
        return
    ticker = normalize_ticker(ctx.args[0])
    msg = await update.message.reply_text(f"⏳ {ticker}...")
    try:
        df = fetch_data(ticker, period="5d")
        info = yf.Ticker(ticker).info
        last = df["Close"].iloc[-1]
        prev = df["Close"].iloc[-2]
        change = last - prev
        pct = change/prev*100
        text = f"📊 *{info.get('longName',ticker)}* (`{ticker}`)\n💰 `{last:,.0f}` ({'🔺' if change>=0 else '🔻'}{change:+,.0f} {pct:+.2f}%)\n⏱ {now_wib()}"
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ Gagal: {e}")

async def chart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ /chart BBCA 3m")
        return
    ticker = normalize_ticker(ctx.args[0])
    period = PERIOD_MAP.get(ctx.args[1].lower() if len(ctx.args)>1 else "6m", "3mo")
    msg = await update.message.reply_text(f"📊 Membuat chart {ticker}...")
    try:
        df = fetch_data(ticker, period=period)
        if len(df) < 20:
            await msg.edit_text("Data tidak cukup")
            return
        buf = generate_chart(df, ticker, period)
        await update.message.reply_photo(buf, caption=f"📊 {ticker} — {PERIOD_LABEL.get(period,period)}")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

async def sinyal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ /sinyal BBCA")
        return
    ticker = normalize_ticker(ctx.args[0])
    msg = await update.message.reply_text(f"🔍 {ticker}...")
    try:
        df = fetch_data(ticker, period="6mo")
        sig = generate_signal(compute_indicators(df))
        text = f"{sig['emoji']} *{sig['signal']}* — `{ticker}`\n" + "\n".join(f"• {d}" for d in sig["details"][:8])
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

async def screener(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    filters = [a.lower() for a in (ctx.args or [])]
    if not filters:
        await update.message.reply_text("🔍 Filter: macd volume rsi20 rsi50 rsi80 stoch5 stoch40 beli jual beli_kuat jual_kuat semua")
        return
    invalid = [f for f in filters if f not in VALID_FILTERS]
    if invalid:
        await update.message.reply_text(f"⚠️ Filter tidak dikenal: {', '.join(invalid)}")
        return
    filters = list(dict.fromkeys(filters))
    msg = await update.message.reply_text(f"🔍 Scan {len(IDX_STOCKS)} saham...")
    try:
        results, total, valid, no_data, errors = await asyncio.get_event_loop().run_in_executor(
            None, partial(run_screener, filters)
        )
        label = " + ".join(filters)
        text = f"🔍 *Screener* — {label}\n📊 {valid} valid → {len(results)} hasil\n"
        if results:
            for d in results[:10]:
                r = d["row"]
                text += f"`{d['code']:<6}` `{r['close']:>8,.0f}` {r['emoji']} *{r['signal']}*\n"
        else:
            text += "\n_Tidak ada hasil_"
        await msg.edit_text(text[:4000], parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("h","Info harga"), BotCommand("c","Chart"),
        BotCommand("sn","Sinyal"), BotCommand("s","Screener"),
        BotCommand("b","Bantuan"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bantuan", bantuan))
    app.add_handler(CommandHandler("help", bantuan))
    app.add_handler(CommandHandler("b", bantuan))
    app.add_handler(CommandHandler("saham", saham))
    app.add_handler(CommandHandler("h", saham))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("c", chart))
    app.add_handler(CommandHandler("sinyal", sinyal))
    app.add_handler(CommandHandler("sn", sinyal))
    app.add_handler(CommandHandler("screener", screener))
    app.add_handler(CommandHandler("s", screener))
    app.add_handler(MessageHandler(filters.COMMAND, lambda u,c: u.message.reply_text("❓ Tidak dikenal. /bantuan")))
    app.run_polling()

if __name__ == "__main__":
    main()
