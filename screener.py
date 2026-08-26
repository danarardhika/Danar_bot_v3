"""
screener.py - Multi-thread screener untuk 300+ saham IDX
"""

import time
import random
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np

from utils import fetch_stock_data, normalize_ticker
from signals import compute_indicators, generate_signals
from stock_list import get_idx_stocks

IDX_STOCKS = get_idx_stocks()

FILTER_MODES = {
    "macd": "MACD Golden Cross",
    "volume": "Volume ≥ 2x Hari Sebelumnya",
    "rsi20": "RSI ≤ 20 (Oversold)",
    "rsi50": "RSI Crossing 50 (Bullish)",
    "rsi80": "RSI ≥ 80 (Overbought)",
    "stoch5": "Stoch(5,3,3) Golden Cross",
    "stoch40": "Stoch(40,3,3) Golden Cross",
    "beli": "Sinyal BELI / BELI KUAT",
    "jual": "Sinyal JUAL / JUAL KUAT",
    "beli_kuat": "Sinyal BELI KUAT",
    "jual_kuat": "Sinyal JUAL KUAT",
    "semua": "Semua Saham",
}

VALID_FILTERS = set(FILTER_MODES.keys())


def _check_macd(row, prev):
    m, ms = row.get("macd"), row.get("macd_sig")
    pm, pms = prev.get("macd"), prev.get("macd_sig")
    if any(v is None or np.isnan(v) for v in [m, ms, pm, pms]):
        return False
    return pm <= pms and m > ms


def _check_volume(row, prev):
    vol = row.get("volume", 0)
    pvol = prev.get("volume", 0)
    return pvol > 0 and vol >= 2 * pvol


def _check_rsi20(row, _):
    rsi = row.get("rsi")
    return rsi is not None and not np.isnan(rsi) and rsi <= 20


def _check_rsi50(row, prev):
    rsi = row.get("rsi")
    prsi = prev.get("rsi")
    if any(v is None or np.isnan(v) for v in [rsi, prsi]):
        return False
    return prsi < 50 <= rsi


def _check_rsi80(row, _):
    rsi = row.get("rsi")
    return rsi is not None and not np.isnan(rsi) and rsi >= 80


def _check_stoch5(row, prev):
    k, d = row.get("k5"), row.get("d5")
    pk, pd_ = prev.get("k5"), prev.get("d5")
    if any(v is None or np.isnan(v) for v in [k, d, pk, pd_]):
        return False
    return pk <= pd_ and k > d


def _check_stoch40(row, prev):
    k, d = row.get("k40"), row.get("d40")
    pk, pd_ = prev.get("k40"), prev.get("d40")
    if any(v is None or np.isnan(v) for v in [k, d, pk, pd_]):
        return False
    return pk <= pd_ and k > d


def _check_beli(row, _):
    return "BELI" in row.get("signal", "")


def _check_jual(row, _):
    return "JUAL" in row.get("signal", "")


def _check_beli_kuat(row, _):
    return row.get("signal") == "BELI KUAT"


def _check_jual_kuat(row, _):
    return row.get("signal") == "JUAL KUAT"


FILTER_FN = {
    "macd": _check_macd,
    "volume": _check_volume,
    "rsi20": _check_rsi20,
    "rsi50": _check_rsi50,
    "rsi80": _check_rsi80,
    "stoch5": _check_stoch5,
    "stoch40": _check_stoch40,
    "beli": _check_beli,
    "jual": _check_jual,
    "beli_kuat": _check_beli_kuat,
    "jual_kuat": _check_jual_kuat,
    "semua": lambda r, p: True,
}


def _fetch_one(ticker_code):
    ticker = normalize_ticker(ticker_code)
    for attempt in range(3):
        try:
            if attempt > 0:
                sleep_s = (2 ** attempt) + random.uniform(0.5, 2.0)
                time.sleep(sleep_s)
            
            df = fetch_stock_data(ticker, period="6mo")
            if df.empty or len(df) < 30:
                return None, "no_data"
            
            df_ind = compute_indicators(df)
            result = generate_signals(df_ind)
            
            cur = df_ind.iloc[-1]
            prev = df_ind.iloc[-2]
            
            def _g(row, key):
                v = row.get(key)
                return None if v is None or np.isnan(v) else v
            
            close = _g(cur, "Close")
            pclose = _g(prev, "Close")
            change = ((close - pclose) / pclose * 100) if close and pclose else 0
            
            row = {
                "close": close or 0,
                "volume": float(cur.get("Volume", 0)),
                "rsi": _g(cur, "RSI"),
                "macd": _g(cur, "MACD"),
                "macd_sig": _g(cur, "MACD_signal"),
                "k5": _g(cur, "STOCH5_K"),
                "d5": _g(cur, "STOCH5_D"),
                "k40": _g(cur, "STOCH40_K"),
                "d40": _g(cur, "STOCH40_D"),
                "signal": result["signal"],
                "emoji": result["emoji"],
                "score": result["score"],
            }
            prev = {
                "volume": float(prev.get("Volume", 0)),
                "rsi": _g(prev, "RSI"),
                "macd": _g(prev, "MACD"),
                "macd_sig": _g(prev, "MACD_signal"),
                "k5": _g(prev, "STOCH5_K"),
                "d5": _g(prev, "STOCH5_D"),
                "k40": _g(prev, "STOCH40_K"),
                "d40": _g(prev, "STOCH40_D"),
            }
            
            out = {"code": ticker_code, "ticker": ticker, "change_pct": change, "row": row, "prev": prev}
            del df, df_ind
            gc.collect()
            return out, "ok"
            
        except Exception:
            if attempt == 2:
                return None, "error"
            continue
    return None, "error"


def run_screener(filters, custom_list=None, max_workers=5, progress_callback=None):
    stocks = list(custom_list) if custom_list else list(IDX_STOCKS)
    all_results = []
    completed = 0
    total_no_data = 0
    total_errors = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, code): code for code in stocks}
        for future in as_completed(futures):
            try:
                data, status = future.result()
            except Exception:
                data, status = None, "error"
            
            if data is not None:
                all_results.append(data)
            elif status == "no_data":
                total_no_data += 1
            else:
                total_errors += 1
            
            completed += 1
            if progress_callback:
                try:
                    progress_callback(completed, len(stocks), len(all_results), total_no_data, total_errors)
                except Exception:
                    pass
    
    fns = [FILTER_FN[f] for f in filters if f in FILTER_FN]
    filtered = []
    for data in all_results:
        row = data["row"]
        prev = data["prev"]
        if all(fn(row, prev) for fn in fns):
            filtered.append(data)
    
    filtered.sort(key=lambda d: (-d["row"]["score"], -d["change_pct"]))
    return filtered, len(stocks), len(all_results), total_no_data, total_errors


def _fmt_vol(v):
    if v >= 1e9: return f"{v/1e9:.2f}B"
    if v >= 1e6: return f"{v/1e6:.2f}M"
    if v >= 1e3: return f"{v/1e3:.0f}K"
    return f"{v:.0f}"


def format_screener_results(results, filters, total_scanned, total_valid, total_no_data=0, total_errors=0):
    filter_labels = " + ".join(FILTER_MODES.get(f, f) for f in filters)
    
    header = (
        f"🔍 *SCREENER SAHAM IDX*\n"
        f"📋 Filter: *{filter_labels}*\n"
        f"📊 Scan: {total_scanned} saham  |  Valid: {total_valid}  |  Hasil: {len(results)}\n"
        f"ℹ️ No data: {total_no_data}  |  Gagal: {total_errors}\n"
        f"{'─' * 34}\n"
    )
    
    if not results:
        return [header + "\n_Tidak ada saham yang memenuhi kriteria._"]
    
    col_head = "`Kode    Harga      Ubah   RSI   St5  St40   Vol      Sinyal`\n`" + "─" * 62 + "`\n"
    rows = []
    
    for d in results:
        r = d["row"]
        p = d["prev"]
        chg = d["change_pct"]
        arrow = "▲" if chg >= 0 else "▼"
        
        rsi_s = f"{r['rsi']:.1f}" if r["rsi"] is not None else "─"
        k5_s = f"{r['k5']:.1f}" if r["k5"] is not None else "─"
        k40_s = f"{r['k40']:.1f}" if r["k40"] is not None else "─"
        vol_s = _fmt_vol(r["volume"])
        
        rows.append(
            f"`{d['code']:<6}` "
            f"`{r['close']:>8,.0f}` "
            f"`{arrow}{abs(chg):>5.1f}%` "
            f"`{rsi_s:>5}` "
            f"`{k5_s:>5}` "
            f"`{k40_s:>5}` "
            f"`{vol_s:>7}` "
            f"{r['emoji']} *{r['signal']}*"
        )
    
    messages = []
    current = header + col_head
    for row_str in rows:
        candidate = current + row_str + "\n"
        if len(candidate) > 4000:
            messages.append(current)
            current = col_head + row_str + "\n"
        else:
            current = candidate
    if current.strip():
        messages.append(current)
    return messages
