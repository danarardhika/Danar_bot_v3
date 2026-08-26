"""
chart.py - Candlestick chart generation with 6 panels
Style: HQSahamIDX - Volume, Candlestick + BB + SMA5, RSI, Stoch5, Stoch40, MACD
"""

import io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from utils import fetch_stock_data, normalize_ticker
from signals import compute_indicators

# ── Colour palette ─────────────────────────────────────────────
C = {
    "bg":       "#ffffff",
    "panel":    "#ffffff",
    "text":     "#111111",
    "grid":     "#e0e0e0",
    "border":   "#bbbbbb",
    "up":       "#26a69a",
    "down":     "#ef5350",
    "vol_ma":   "#111111",
    "bb_fill":  "#c8d8f0",
    "bb_line":  "#3366cc",
    "bb_mid":   "#3366cc",
    "sma5":     "#009900",
    "rsi":      "#aa00aa",
    "rsi80":    "#cc0000",
    "rsi20":    "#0000cc",
    "stoch_k":  "#009900",
    "stoch_d":  "#cc0000",
    "stoch80":  "#cc0000",
    "stoch20":  "#0000cc",
    "macd":     "#0000cc",
    "macd_sig": "#cc00cc",
    "macd_pos": "#26a69a",
    "macd_neg": "#ef5350",
}

PERIOD_LIMITS = {
    "5d": 7, "1mo": 30, "3mo": 65,
    "6mo": 130, "1y": 252, "2y": 504,
}


def _style_ax(ax):
    ax.set_facecolor(C["panel"])
    ax.tick_params(axis="both", colors=C["text"], labelsize=7.5, length=3, pad=3)
    for s in ax.spines.values():
        s.set_color(C["border"])
        s.set_linewidth(0.7)
    ax.grid(axis="y", color=C["grid"], linewidth=0.5, linestyle="-", alpha=0.9)
    ax.grid(axis="x", color=C["grid"], linewidth=0.4, linestyle="-", alpha=0.6)
    ax.yaxis.set_label_position("right")
    ax.yaxis.tick_right()


def _info_bar(ax, text: str, color: str = "#111111"):
    """Floating info label di pojok kiri atas panel"""
    ax.text(
        0.005, 0.98, text,
        transform=ax.transAxes,
        fontsize=7, color=color,
        va="top", ha="left",
        bbox=dict(facecolor="#eeeeee", edgecolor=C["border"],
                  boxstyle="square,pad=0.2", linewidth=0.5, alpha=0.85),
        zorder=10,
    )


def generate_chart(df: pd.DataFrame, ticker: str, period: str = "3mo") -> io.BytesIO:
    """Generate 6-panel candlestick chart"""
    
    # Hitung indikator
    df = compute_indicators(df)
    df = df.dropna(subset=["Close"])
    
    limit = PERIOD_LIMITS.get(period, 65)
    df = df.tail(limit)
    n = len(df)
    x = list(range(n))
    
    # ── Figure + GridSpec ──
    fig = plt.figure(figsize=(13, 13), facecolor=C["bg"])
    gs = gridspec.GridSpec(
        6, 1,
        height_ratios=[0.85, 3.8, 1.25, 1.25, 1.25, 1.35],
        hspace=0.0,
        figure=fig,
    )
    ax_vol = fig.add_subplot(gs[0])
    ax_candle = fig.add_subplot(gs[1], sharex=ax_vol)
    ax_rsi = fig.add_subplot(gs[2], sharex=ax_vol)
    ax_st5 = fig.add_subplot(gs[3], sharex=ax_vol)
    ax_st40 = fig.add_subplot(gs[4], sharex=ax_vol)
    ax_macd = fig.add_subplot(gs[5], sharex=ax_vol)
    
    all_axes = [ax_vol, ax_candle, ax_rsi, ax_st5, ax_st40, ax_macd]
    for ax in all_axes:
        _style_ax(ax)
    
    fig.subplots_adjust(left=0.02, right=0.90, top=0.96, bottom=0.04)
    
    # ── PANEL 0: Volume ──
    vol_colors = [
        C["up"] if df["Close"].iloc[i] >= df["Open"].iloc[i] else C["down"]
        for i in range(n)
    ]
    ax_vol.bar(x, df["Volume"].values, color=vol_colors, width=0.7, alpha=0.85)
    if "Vol_SMA20" in df.columns:
        ax_vol.plot(x, df["Vol_SMA20"].values, color=C["vol_ma"], lw=0.9)
    
    ax_vol.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _:
            f"{v/1e9:.2f}B" if v >= 1e9 else
            f"{v/1e6:.2f}M" if v >= 1e6 else
            f"{v/1e3:.0f}K")
    )
    ax_vol.yaxis.set_major_locator(mticker.MaxNLocator(nbins=3, prune="both"))
    
    ma_vol = df["Vol_SMA20"].iloc[-1] if "Vol_SMA20" in df.columns else 0
    last_vol = df["Volume"].iloc[-1]
    _vol_fmt = lambda v: (f"{v/1e9:.3f}B" if v >= 1e9 else
                          f"{v/1e6:.3f}M" if v >= 1e6 else f"{v:,.0f}")
    _info_bar(ax_vol, f"■ MAVol(20): {_vol_fmt(ma_vol)}   Vol: {_vol_fmt(last_vol)}")
    
    last_close = df["Close"].iloc[-1]
    last_date = df.index[-1].strftime("%Y-%m-%d")
    ax_vol.set_title(
        f"*{ticker}   {last_date}  (data delayed 10 min) — Daily chart",
        color=C["text"], fontsize=9.5, fontweight="bold",
        loc="left", pad=4,
    )
    
    # ── PANEL 1: Candlestick ──
    if "BB_upper" in df.columns:
        ax_candle.fill_between(
            x, df["BB_upper"].values, df["BB_lower"].values,
            color=C["bb_fill"], alpha=0.40, zorder=1,
        )
        ax_candle.plot(x, df["BB_upper"].values, color=C["bb_line"], lw=0.85, zorder=2)
        ax_candle.plot(x, df["BB_middle"].values, color=C["bb_mid"], lw=0.85,
                       ls="--", zorder=2)
        ax_candle.plot(x, df["BB_lower"].values, color=C["bb_line"], lw=0.85, zorder=2)
    
    if "SMA5" in df.columns:
        ax_candle.plot(x, df["SMA5"].values, color=C["sma5"], lw=1.15, zorder=3)
    
    # Gambar candlestick
    for i, (_, row) in enumerate(df.iterrows()):
        o, h, l, c_ = row["Open"], row["High"], row["Low"], row["Close"]
        col = C["up"] if c_ >= o else C["down"]
        ax_candle.plot([i, i], [l, h], color=col, lw=0.9, zorder=4)
        body_h = max(abs(c_ - o), (h - l) * 0.005)
        ax_candle.bar(i, body_h, bottom=min(o, c_), color=col,
                      width=0.68, edgecolor="none", zorder=4)
    
    ax_candle.yaxis.set_major_locator(mticker.MaxNLocator(nbins=6, prune="both"))
    ax_candle.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{v:,.0f}"))
    
    last = df.iloc[-1]
    o_, h_, l_, c_ = last["Open"], last["High"], last["Low"], last["Close"]
    sma5_v = last.get("SMA5", float("nan"))
    bb_u = last.get("BB_upper", float("nan"))
    bb_l_v = last.get("BB_lower", float("nan"))
    bb_m = last.get("BB_middle", float("nan"))
    sma_str = f"SMA(5): {sma5_v:,.0f}" if not np.isnan(sma5_v) else ""
    bb_str = (f"Bollinger(20,2): {bb_l_v:,.1f}–{bb_u:,.1f}  mid:{bb_m:,.1f}"
              if not np.isnan(bb_u) else "")
    _info_bar(ax_candle,
              f"Op:{o_:,.0f}  Hi:{h_:,.0f}  Lo:{l_:,.0f}  Cl:{c_:,.0f}"
              f"     {sma_str}     {bb_str}")
    
    # ── PANEL 2: RSI ──
    if "RSI" in df.columns:
        rsi_v = df["RSI"].values
        ax_rsi.plot(x, rsi_v, color=C["rsi"], lw=1.1)
        ax_rsi.axhline(80, color=C["rsi80"], lw=0.75, alpha=0.85)
        ax_rsi.axhline(20, color=C["rsi20"], lw=0.75, alpha=0.85)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_yticks([20, 50, 80])
        last_rsi = rsi_v[-1]
        _info_bar(ax_rsi, f"■ RSI (14): {last_rsi:.2f}", color=C["rsi"])
    
    # ── PANEL 3 & 4: Stochastic ──
    def _draw_stoch(ax, k_col, d_col, title: str):
        if k_col not in df.columns:
            return
        k_v = df[k_col].values
        d_v = df[d_col].values
        ax.plot(x, k_v, color=C["stoch_k"], lw=1.1)
        ax.plot(x, d_v, color=C["stoch_d"], lw=0.9, ls="--")
        ax.axhline(80, color=C["stoch80"], lw=0.75, alpha=0.85)
        ax.axhline(20, color=C["stoch20"], lw=0.75, alpha=0.85)
        ax.set_ylim(-2, 105)
        ax.set_yticks([20, 50, 80])
        last_k, last_d = k_v[-1], d_v[-1]
        _info_bar(ax,
                  f"■ {title}  %K: {last_k:.2f}   %D: {last_d:.2f}",
                  color=C["stoch_k"])
    
    _draw_stoch(ax_st5, "STOCH5_K", "STOCH5_D", "Slow Stoch(5,3,3)")
    _draw_stoch(ax_st40, "STOCH40_K", "STOCH40_D", "Slow Stoch(40,3,3)")
    
    # ── PANEL 5: MACD ──
    if "MACD" in df.columns:
        macd_v = df["MACD"].values
        sig_v = df["MACD_signal"].values
        hist_v = df["MACD_hist"].values
        hcol = [C["macd_pos"] if v >= 0 else C["macd_neg"] for v in hist_v]
        ax_macd.bar(x, hist_v, color=hcol, width=0.7, alpha=0.85)
        ax_macd.plot(x, macd_v, color=C["macd"], lw=1.1)
        ax_macd.plot(x, sig_v, color=C["macd_sig"], lw=0.9, ls="--")
        ax_macd.axhline(0, color=C["border"], lw=0.6)
        ax_macd.yaxis.set_major_locator(mticker.MaxNLocator(nbins=4, prune="both"))
        last_macd = macd_v[-1]
        last_sig = sig_v[-1]
        last_div = hist_v[-1]
        _info_bar(ax_macd,
                  f"■ MACD(12,26): {last_macd:.3f}   "
                  f"■ EXP(9): {last_sig:.3f}   "
                  f"■ Divergence: {last_div:.1f}",
                  color=C["macd"])
    
    # ── X-axis ──
    for ax in [ax_vol, ax_candle, ax_rsi, ax_st5, ax_st40]:
        plt.setp(ax.get_xticklabels(), visible=False)
        ax.tick_params(axis="x", length=0)
    
    step = max(1, n // 10)
    tick_pos = list(range(0, n, step))
    tick_labels = [df.index[i].strftime("%b %d") for i in tick_pos]
    ax_macd.set_xticks(tick_pos)
    ax_macd.set_xticklabels(tick_labels, fontsize=8, color=C["text"])
    ax_macd.set_xlim(-0.8, n - 0.2)
    
    # ── Save ──
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130,
                facecolor=C["bg"], edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf
