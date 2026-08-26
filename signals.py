"""
signals.py - Technical analysis indicators using TA library
"""

import pandas as pd
import numpy as np
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to DataFrame"""
    if df.empty or len(df) < 20:
        return df
    
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    
    # RSI (14)
    df["RSI"] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    
    # MACD (12, 26, 9)
    macd = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"] = macd.macd_diff()
    
    # Bollinger Bands (20, 2)
    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_middle"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()
    
    # SMA 5
    df["SMA5"] = close.rolling(window=5).mean()
    
    # SMA 20 untuk Volume
    df["Vol_SMA20"] = volume.rolling(window=20).mean()
    
    # Slow Stochastic (5, 3, 3)
    df["STOCH5_K"], df["STOCH5_D"] = _slow_stochastic(high, low, close, 5, 3, 3)
    
    # Slow Stochastic (40, 3, 3)
    df["STOCH40_K"], df["STOCH40_D"] = _slow_stochastic(high, low, close, 40, 3, 3)
    
    return df


def _slow_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                     k_period: int, k_smooth: int, d_smooth: int):
    """Slow stochastic oscillator"""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    denom = highest_high - lowest_low
    raw_k = 100 * (close - lowest_low) / denom.replace(0, np.nan)
    slow_k = raw_k.rolling(k_smooth).mean()
    d = slow_k.rolling(d_smooth).mean()
    return slow_k, d


def generate_signals(df: pd.DataFrame) -> dict:
    """Generate buy/sell/hold signals from indicators"""
    if df.empty or len(df) < 30:
        return {"signal": "DATA TIDAK CUKUP", "emoji": "⚠️", "score": 0, "details": []}
    
    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    
    score = 0
    details = []
    
    # --- RSI ---
    rsi = row.get("RSI")
    if pd.notna(rsi):
        if rsi < 30:
            score += 2
            details.append(f"RSI {rsi:.1f} — Oversold 🟢")
        elif rsi < 40:
            score += 1
            details.append(f"RSI {rsi:.1f} — Mendekati oversold 🟩")
        elif rsi > 70:
            score -= 2
            details.append(f"RSI {rsi:.1f} — Overbought 🔴")
        elif rsi > 60:
            score -= 1
            details.append(f"RSI {rsi:.1f} — Mendekati overbought 🟥")
        else:
            details.append(f"RSI {rsi:.1f} — Netral 🟡")
    
    # --- MACD ---
    macd = row.get("MACD")
    sig = row.get("MACD_signal")
    p_macd = prev.get("MACD")
    p_sig = prev.get("MACD_signal")
    
    if all(pd.notna(x) for x in [macd, sig, p_macd, p_sig]):
        if p_macd <= p_sig and macd > sig:
            score += 2
            details.append("MACD — Golden Cross 🟢")
        elif p_macd >= p_sig and macd < sig:
            score -= 2
            details.append("MACD — Death Cross 🔴")
        elif macd > sig:
            score += 1
            details.append("MACD — Bullish 🟩")
        else:
            score -= 1
            details.append("MACD — Bearish 🟥")
    
    # --- Bollinger Bands ---
    close = row.get("Close")
    bb_u = row.get("BB_upper")
    bb_l = row.get("BB_lower")
    bb_m = row.get("BB_middle")
    
    if all(pd.notna(x) for x in [close, bb_u, bb_l, bb_m]):
        if close < bb_l:
            score += 2
            details.append("Harga di bawah BB Lower 🟢")
        elif close > bb_u:
            score -= 2
            details.append("Harga di atas BB Upper 🔴")
        elif close < bb_m:
            details.append("Harga di bawah BB Middle 🟡")
        else:
            details.append("Harga di atas BB Middle 🟡")
    
    # --- Stochastic (5,3,3) ---
    k5 = row.get("STOCH5_K")
    d5 = row.get("STOCH5_D")
    pk5 = prev.get("STOCH5_K")
    pd5 = prev.get("STOCH5_D")
    
    if all(pd.notna(x) for x in [k5, d5, pk5, pd5]):
        if pk5 <= pd5 and k5 > d5 and k5 < 30:
            score += 2
            details.append(f"Stoch(5) Golden Cross di oversold 🟢")
        elif pk5 >= pd5 and k5 < d5 and k5 > 70:
            score -= 2
            details.append(f"Stoch(5) Death Cross di overbought 🔴")
        elif k5 < 20:
            score += 1
            details.append(f"Stoch(5) %K {k5:.1f} — Oversold 🟩")
        elif k5 > 80:
            score -= 1
            details.append(f"Stoch(5) %K {k5:.1f} — Overbought 🟥")
        else:
            details.append(f"Stoch(5) %K {k5:.1f} — Netral 🟡")
    
    # --- Stochastic (40,3,3) ---
    k40 = row.get("STOCH40_K")
    d40 = row.get("STOCH40_D")
    pk40 = prev.get("STOCH40_K")
    pd40 = prev.get("STOCH40_D")
    
    if all(pd.notna(x) for x in [k40, d40, pk40, pd40]):
        if pk40 <= pd40 and k40 > d40 and k40 < 30:
            score += 2
            details.append(f"Stoch(40) Golden Cross di oversold 🟢")
        elif pk40 >= pd40 and k40 < d40 and k40 > 70:
            score -= 2
            details.append(f"Stoch(40) Death Cross di overbought 🔴")
        elif k40 < 20:
            score += 1
            details.append(f"Stoch(40) %K {k40:.1f} — Oversold 🟩")
        elif k40 > 80:
            score -= 1
            details.append(f"Stoch(40) %K {k40:.1f} — Overbought 🟥")
        else:
            details.append(f"Stoch(40) %K {k40:.1f} — Netral 🟡")
    
    # --- Final Signal ---
    if score >= 5:
        signal, emoji = "BELI KUAT", "🟢"
    elif score >= 2:
        signal, emoji = "BELI", "🟩"
    elif score <= -5:
        signal, emoji = "JUAL KUAT", "🔴"
    elif score <= -2:
        signal, emoji = "JUAL", "🟥"
    else:
        signal, emoji = "TAHAN / NETRAL", "🟡"
    
    return {"signal": signal, "emoji": emoji, "score": score, "details": details}
