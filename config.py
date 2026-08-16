import os
from dotenv import load_dotenv

load_dotenv()

# Watchlist saham yang dipantau tiap run: contoh dari modul trading + seluruh konstituen LQ45 (paling likuid, per Mei 2026)
# + anggota grup konglomerasi di bawah yang belum masuk LQ45. Tambahin/kurangin manual sesuai saham yang kamu pantau.
# ponytail: LQ45 rebalance tiap ~4 bulan, refresh list ini periodik dari idx.co.id biar gak basi
_EXAMPLES = ["DEFI", "BOBA", "PSKT", "PTMR", "JGLE", "UANG", "RAJA", "RATU", "BNBR", "VKTR"]
_LQ45 = [
    "AADI", "ADMR", "ADRO", "AKRA", "AMMN", "AMRT", "ANTM", "ASII", "BBCA", "BBNI",
    "BBRI", "BBTN", "BMRI", "BRPT", "BUMI", "CPIN", "CUAN", "DEWA", "EMTK", "ESSA",
    "EXCL", "GOTO", "HRTA", "ICBP", "INCO", "INDF", "INKP", "ISAT", "ITMG", "JPFA",
    "KLBF", "MAPI", "MBMA", "MDKA", "MEDC", "PGAS", "PGEO", "PTBA", "SCMA", "TLKM",
    "TOWR", "UNTR", "UNVR", "WIFI",
]
_GROUP_EXTRAS = [
    "TPIA", "PTRO",                          # Barito (BRPT, CUAN udah di LQ45)
    "DNET", "FAPA", "PANI",                  # Salim (INDF, ICBP, AMMN udah di LQ45)
    "BSDE", "BSIM", "TKIM", "DSSA", "GEMS", "DMAS", "SMMA",  # Sinar Mas (INKP udah di LQ45)
    "LPKR", "SILO", "LPPF", "MLPL",          # Lippo
    "BHIT", "BMTR", "MNCN", "MSIN", "IPTV",  # MNC (grouping kurang pasti, cek ulang sebelum dipakai serius)
    "AALI", "AUTO",                          # Astra (ASII, UNTR udah di LQ45)
]
WATCHLIST = list(dict.fromkeys(_EXAMPLES + _LQ45 + _GROUP_EXTRAS))  # dedupe, jaga urutan

# ponytail: kurasi manual, gak ada API resmi buat "saham satu grup pemilik" -> verifikasi ke prospektus/berita
# sebelum dipakai serius, terutama grup MNC yang saya kurang yakin lengkapnya. Update sendiri kalau ada grup baru.
OWNERSHIP_GROUPS = {
    "hapsoro": ["UANG", "RAJA", "RATU", "PSKT"],
    "bakrie": ["BNBR", "VKTR", "DEWA", "JGLE"],
    "barito": ["BRPT", "TPIA", "CUAN", "PTRO"],
    "salim": ["INDF", "ICBP", "AMMN", "DNET", "FAPA", "PANI"],
    "sinarmas": ["BSDE", "BSIM", "INKP", "TKIM", "DSSA", "GEMS", "DMAS", "SMMA"],
    "djarum": ["BBCA"],
    "lippo": ["LPKR", "SILO", "LPPF", "MLPL"],
    "mnc": ["BHIT", "BMTR", "MNCN", "MSIN", "IPTV"],
    "astra": ["ASII", "UNTR", "AALI", "AUTO"],
}

# ponytail: sektor IDX-IC, verified via web search Jul 2026 - bukan API resmi realtime, cek idx.co.id kalau ragu.
# UANG/RAJA/RATU sengaja gak dimasukin: gak ketemu data sektor yang bisa diverifikasi, mending kosong daripada nebak.
SECTOR_MAP = {
    # financials
    "BBCA": "financials", "BBNI": "financials", "BBRI": "financials", "BBTN": "financials",
    "BMRI": "financials", "BSIM": "financials", "SMMA": "financials", "MLPL": "financials",
    "DEFI": "financials",
    # energy
    "ADMR": "energy", "ADRO": "energy", "AADI": "energy", "PTBA": "energy", "ITMG": "energy",
    "BUMI": "energy", "MEDC": "energy", "PGAS": "energy", "PGEO": "energy", "AKRA": "energy",
    "ESSA": "energy", "CUAN": "energy", "DSSA": "energy", "GEMS": "energy", "DEWA": "energy",
    # basic materials
    "ANTM": "basic-materials", "INCO": "basic-materials", "MDKA": "basic-materials",
    "MBMA": "basic-materials", "AMMN": "basic-materials", "INKP": "basic-materials",
    "TKIM": "basic-materials", "BRPT": "basic-materials", "TPIA": "basic-materials",
    "HRTA": "basic-materials", "PTMR": "basic-materials",
    # industrials
    "ASII": "industrials", "UNTR": "industrials", "AUTO": "industrials", "PTRO": "industrials",
    "BNBR": "industrials", "VKTR": "industrials",
    # consumer non-cyclicals
    "ICBP": "consumer-non-cyclicals", "INDF": "consumer-non-cyclicals", "UNVR": "consumer-non-cyclicals",
    "CPIN": "consumer-non-cyclicals", "JPFA": "consumer-non-cyclicals", "AALI": "consumer-non-cyclicals",
    "FAPA": "consumer-non-cyclicals",
    # consumer cyclicals
    "MAPI": "consumer-cyclicals", "LPPF": "consumer-cyclicals", "DNET": "consumer-cyclicals",
    "BOBA": "consumer-cyclicals", "PSKT": "consumer-cyclicals", "AMRT": "consumer-cyclicals",
    # healthcare
    "KLBF": "healthcare", "SILO": "healthcare",
    # properties
    "BSDE": "properties", "DMAS": "properties", "LPKR": "properties", "PANI": "properties",
    "JGLE": "properties",
    # technology (termasuk media, klasifikasi IDX-IC-nya suka campur)
    "GOTO": "technology", "EMTK": "technology", "SCMA": "technology", "MNCN": "technology",
    "BMTR": "technology", "BHIT": "technology", "MSIN": "technology", "IPTV": "technology",
    "WIFI": "technology",
    # infrastructure
    "TLKM": "infrastructure", "ISAT": "infrastructure", "EXCL": "infrastructure", "TOWR": "infrastructure",
}

# ponytail: IPO momentum butuh data broker-summary buat deteksi akumulasi otomatis (belum ada sumber gratis/legal
# yang jelas, sama kayak masalah bdmtool) -> untuk sekarang accum_price diisi manual pas kamu lihat sendiri di broker summary
IPO_WATCH = [
    # {"ticker": "CDIA", "accum_price": 1000},
]

BROKER_FLOW_LOOKBACK_DAYS = 10        # berapa hari bursa buat hitung rata-rata baseline tiap broker
BROKER_FLOW_ANOMALY_MULTIPLE = 2.0    # flag kalau value hari ini >= 2x rata-rata broker itu sendiri
BROKER_FLOW_MIN_BASELINE_VALUE = 1_000_000_000  # skip broker kecil (baseline < 1M supaya gak noise)

MEAN_REVERSAL_LOOKBACK_DAYS = 20
MEAN_REVERSAL_DROP_THRESHOLD = 0.15   # flag kalau harga >15% di bawah rolling high
UNIVERSE_MOVE_THRESHOLD = 0.05        # anggota grup lain naik/turun >5%
UNIVERSE_LAGGARD_THRESHOLD = 0.01     # tapi ticker ini masih diam <1%
SECTOR_LOOKBACK_DAYS = 5

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "")
FONNTE_TARGET = os.environ.get("FONNTE_TARGET", "")
