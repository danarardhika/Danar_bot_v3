"""
stock_list.py - Daftar lengkap saham IDX (300+ saham) dengan cache
"""

import json
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

_CACHE_FILE = os.path.join(os.path.dirname(__file__), "idx_stocks_cache.json")
_CACHE_TTL = 24 * 3600  # 1 hari

# ── 300+ SAHAM IDX HARDCODE ──
HARDCODED_IDX = [
    # Perbankan
    "BBCA", "BBRI", "BMRI", "BBNI", "BRIS", "BTPS", "BNGA", "NISP",
    "BBTN", "BDMN", "BJBR", "BJTM", "PNBN", "MEGA", "BNLI", "AGRO",
    "BBYB", "BMAS", "BNBA", "BSIM", "MAYA", "NOBU", "BACA", "BABP",
    "BVIC", "INPC", "SDRA", "BGTG", "DNAR", "BCIC", "BPTN", "BSSR",
    # Keuangan non-bank
    "ADMF", "MFIN", "PNLF", "BCAP", "BFIN", "WOMF", "CFIN", "TIFA",
    "VRNA", "LPPS", "MKNT", "BESS", "ABMM",
    # Energi & Tambang
    "ADRO", "PTBA", "INCO", "ANTM", "MDKA", "BRMS", "HRUM", "BUMI",
    "MEDC", "ELSA", "AKRA", "TINS", "ITMG", "PTRO", "DOID", "ADMR",
    "BYAN", "GEMS", "MBAP", "DEWA", "ENRG", "ESSA", "FIRE", "MAHA",
    "MYOH", "KKGI", "BIPI", "RUIS", "SMRU", "SMMT", "GTBO", "ARTI",
    "PKPK", "DSSA", "COAL", "MBSS", "PSAB", "IATA", "INDY", "GAMA",
    # Minyak & Gas
    "PGAS", "PGEO", "RAJA", "WINS", "HMPD", "RIGS", "LEAD",
    # Telekomunikasi & Teknologi
    "TLKM", "EXCL", "ISAT", "GOTO", "EMTK", "BUKA", "MNCN", "SCMA",
    "VIVA", "LINK", "DATA", "DMMX", "MLPL", "MSKY", "MCAS", "WIFI",
    "MTDL", "KREN", "ATIC", "INET", "LAND", "TELE", "IBST", "SUPR", "TOWR",
    # Konsumen
    "UNVR", "ICBP", "INDF", "MYOR", "ULTJ", "SIDO", "HMSP", "GGRM",
    "ACES", "MAPI", "LPPF", "RALS", "AMRT", "MIDI", "CSAP", "MPPA",
    "GOOD", "HOKI", "SKLT", "DLTA", "MRAT", "CLEO", "BOBA", "CEKA",
    "FAST", "PZZA", "DKFT", "RANC", "IIKP", "HERO", "AISA", "CAMP",
    "KEJU", "ALTO", "ROTI", "SKBM", "STTP", "TBIG", "MLBI", "ADES",
    "PSGO", "PCAR", "WMUU", "WIIM", "ITIC",
    # Kesehatan
    "KLBF", "KAEF", "HEAL", "MIKA", "SILO", "TSPC", "DVLA", "PYFA",
    "INAF", "PEHA", "PRIM", "RSGK", "SAME", "PRDA", "CARE", "IRRA", "OMED",
    # Properti
    "BSDE", "SMRA", "CTRA", "PWON", "LPKR", "APLN", "DILD", "JRPT",
    "KIJA", "MTLA", "PLIN", "PPRO", "RDTX", "SMDM", "GPRA", "BKSL",
    "GWSA", "LPCK", "MMLP", "ELTY", "DMAS", "NIRO", "MKPI", "GMTD",
    "LCGP", "FMII", "TARA", "URBN", "RISE", "POLL", "BCIP",
    # Infrastruktur & Konstruksi
    "JSMR", "WSKT", "WTON", "ADHI", "WIKA", "PTPP", "META", "NRCA",
    "TOTL", "DGIK", "CMNP", "RODA", "IDPR", "NUSA", "KPIG", "BALI",
    "ACST", "MTRA", "PBSA", "WEGE", "KDSI",
    # Transportasi
    "GIAA", "CMPP", "BIRD", "SAFE", "SMDR", "TMAS", "ASSA", "JAYA",
    "NELI", "LRNA", "WEHA", "INDX", "TAXI", "MIRA",
    # Perkebunan
    "AALI", "LSIP", "SIMP", "TBLA", "BWPT", "GZCO", "JAWA", "PALM",
    "SGRO", "SSMS", "BISI", "DSFI", "ANJT", "SMAR", "MGNA", "UNSP",
    # Industri Dasar
    "TPIA", "BRPT", "SMGR", "INTP", "ARNA", "MLIA", "TOTO", "VOKS",
    "UNIC", "EKAD", "BTON", "GDST", "LION", "LMSH", "NIKL", "PICO",
    "ALKA", "FASW", "ALDO", "SPMA", "KBRI", "TIRT", "DPNS", "SRSN",
    "AKKU", "AMFG", "MDKI", "AGII", "IGTA", "INAI", "KRAS",
    # Manufaktur & Otomotif
    "ASII", "UNTR", "AUTO", "GJTL", "SMSM", "GDYR", "IMAS", "INDS",
    "LPIN", "MASA", "STAR", "ADMG", "PRAS", "BRAM", "NIPS", "BOLT",
    "KBLM", "VKTR", "KBLI", "JECC", "SCCO", "SUCF", "IKBI",
    # Lainnya
    "SMCB", "SMBR", "WSBP", "RICY", "SSTM", "TFCO", "TRIS", "UNIT",
    "ARGO", "CNTB", "PBRX", "POLY", "POLU", "ABBA", "TMPO", "FORU",
    "BAYU", "BUVA", "INPP", "JSPT", "MABA", "PDES", "PTSP", "SONA",
    "PANR", "PNSE", "HOME", "DUTI", "IGAR", "INCI", "KICI", "LMPI",
    "LTLS", "MERK", "MYRX", "PEGE", "PGLI", "SEMA", "SIPD", "SLIS",
    "SMPL", "SRTG", "SURI", "SWAT", "TALF", "TERI", "TIRA", "TNCA",
    "TOOL", "TOPS", "TRIM", "TURI", "UANG", "VICI", "WICO", "YELO",
    "ZBRA", "ABDA", "AHAP", "AMAG", "ASBI", "ASDM", "ASEI", "ASMI",
    "ASRM", "LPGI", "MREI", "PNIN", "TUGU",
]

# Deduplikasi
_seen = set()
_deduped = []
for s in HARDCODED_IDX:
    if s not in _seen:
        _seen.add(s)
        _deduped.append(s)
HARDCODED_IDX = _deduped


def _load_cache():
    try:
        with open(_CACHE_FILE, "r") as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) < _CACHE_TTL:
            return data["stocks"]
    except Exception:
        pass
    return None


def _save_cache(stocks):
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "stocks": stocks}, f)
    except Exception:
        pass


def get_idx_stocks(use_cache=True):
    """Get list of IDX stocks (300+)"""
    if use_cache:
        cached = _load_cache()
        if cached:
            return cached
    return HARDCODED_IDX
