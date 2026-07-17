"""Loader broker summary harian buat algo bandarmology (broksum).

ponytail: NVAL (net value = buy - sell per broker) GAK ADA di endpoint publik IDX. Udah dicek tuntas
(Jul 2026): di /primary/TradingSummary/ cuma ada GetBrokerSummary, GetStockSummary, GetIndexSummary
- 14 tebakan nama lain (GetBrokerSummaryDetail, GetBrokerNet, dst) semuanya 404. GetBrokerSummary cuma
ngasih Volume/Value/Frequency tanpa pecahan buy/sell, dan 16 variasi param papan (board/boardCode/
market/papan/...) diabaikan diam-diam (byte response identik). Dibuktikan silang lewat GetStockSummary:
broker Value / 2 = 10.544T vs stock (RG + NonRegular) = 10.535T, jadi Value = (Regular+Nego) x 2 =
BVal+SVal. Satu persamaan, dua variabel -> NVAL gak bisa diturunkan. IDX buka dimensi buy/sell per
SAHAM (ForeignBuy/ForeignSell) tapi gak pernah per BROKER; itu produk berbayar mereka.

Jadi: NVAL wajib dari export terminal (IPOT/Stockbit/RTI/HOTS) -> CSV. TVAL+TFREQ bisa auto-fetch dari
IDX buat cross-check/isi bolong, tapi baca peringatan negosiasi di fetch_idx_tval_tfreq().
"""

import csv
import re
from pathlib import Path

from broker_data import fetch_broker_summary

# Suffix satuan di header CSV, biar bisa nelen header gaya sheet ("NVAL B", "TFREQ K") apa adanya.
_UNIT_SCALE = {"B": 1e9, "M": 1e6, "K": 1e3, "JT": 1e6, "RB": 1e3}

# Alias header -> field internal. Dicocokin ke token pertama header (case-insensitive).
_FIELD_ALIASES = {
    "code": {"code", "kode", "broker", "brokercode", "idfirm", "firm"},
    "nval": {"nval", "net", "netval", "nbsa", "netvalue"},
    "tval": {"tval", "value", "totalvalue", "tvalue"},
    "tfreq": {"tfreq", "freq", "frequency", "frekuensi"},
}


def _parse_header(header):
    """Map index kolom -> (field, scale). Satuan diambil dari suffix header: 'NVAL B' -> x1e9."""
    mapping = {}
    for i, raw in enumerate(header):
        tokens = re.split(r"[\s_/().]+", (raw or "").strip())
        tokens = [t for t in tokens if t]
        if not tokens:
            continue
        key = tokens[0].lower()
        field = next((f for f, aliases in _FIELD_ALIASES.items() if key in aliases), None)
        if field is None:
            continue
        scale = 1.0
        if field != "code" and len(tokens) > 1:
            scale = _UNIT_SCALE.get(tokens[1].upper(), 1.0)
        mapping[i] = (field, scale)
    return mapping


def _parse_number(text):
    """Nelen '1.234,56' (ID), '1,234.56' (US), '(123)' negatif, '12%'. Return None kalau bukan angka."""
    s = (text or "").strip().replace("%", "").replace("Rp", "").replace(" ", "")
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]
    if "," in s and "." in s:
        # yang paling kanan = pemisah desimal
        s = s.replace(".", "").replace(",", ".") if s.rindex(",") > s.rindex(".") else s.replace(",", "")
    elif "," in s:
        # koma tunggal: desimal kalau <=2 digit di belakang (1,5), selain itu pemisah ribuan (1,234)
        s = s.replace(",", ".") if len(s.split(",")[-1]) <= 2 else s.replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def load_broksum_csv(path):
    """Baca CSV broker summary -> list dict {code, nval_rp, tval_rp, tfreq} dalam satuan MENTAH
    (rupiah + jumlah transaksi). Header wajib punya kolom code/broker, nval, tval, tfreq (alias &
    suffix satuan ditoleransi). Baris tanpa kode atau tanpa angka lengkap di-skip diam-diam."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []

    # Header = baris pertama yang kenal minimal kolom code + salah satu metrik (sheet suka ada baris kosong di atas).
    mapping = None
    start = 0
    for idx, row in enumerate(rows):
        candidate = _parse_header(row)
        fields = {f for f, _ in candidate.values()}
        if "code" in fields and fields & {"nval", "tval", "tfreq"}:
            mapping, start = candidate, idx + 1
            break
    if mapping is None:
        raise ValueError(f"{path.name}: gak nemu header dengan kolom CODE + NVAL/TVAL/TFREQ")

    records = []
    for row in rows[start:]:
        record = {}
        for i, (field, scale) in mapping.items():
            if i >= len(row):
                continue
            if field == "code":
                record["code"] = (row[i] or "").strip().upper()
            else:
                number = _parse_number(row[i])
                if number is not None:
                    record[field] = number * scale
        code = record.get("code", "")
        # kode broker IDX selalu 2 huruf; ini juga yang nyaring baris nomor urut/total/kosong
        if not re.fullmatch(r"[A-Z]{2}", code):
            continue
        if not {"nval", "tval", "tfreq"} <= record.keys():
            continue
        records.append({
            "code": code,
            "nval_rp": record["nval"],
            "tval_rp": record["tval"],
            "tfreq": record["tfreq"],
            "source": "csv",
        })
    return records


def load_for_date(target_date=None):
    """Ambil broksum buat 'YYYY-MM-DD' dari BROKSUM_DIR (file '<YYYY-MM-DD>.csv'). Kalau target_date
    kosong: pakai CSV paling baru yang ada. Gak ada file = list kosong (bukan error) - biar run harian
    tetap jalan di hari kamu belum sempat export."""
    from config import BROKSUM_DIR

    directory = Path(BROKSUM_DIR)
    if not directory.is_dir():
        return []

    if target_date:
        path = directory / f"{target_date}.csv"
        if not path.is_file():
            return []
    else:
        # nama file = tanggal ISO, jadi urutan nama == urutan tanggal
        candidates = sorted(p for p in directory.glob("*.csv") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
        if not candidates:
            return []
        path = candidates[-1]

    return [{**r, "date": path.stem} for r in load_broksum_csv(path)]


def fetch_idx_tval_tfreq(date_str):
    """TVAL+TFREQ per broker dari IDX (satuan mentah). date_str: 'YYYYMMDD'. NVAL selalu None.

    ponytail: PERINGATAN - Value di sini termasuk papan NEGOSIASI dan gak bisa difilter. Buat broker
    yang banyak crossing angkanya ngaco parah: RB 3 Jul 2026 = 417.92B/710trx (=588 juta per transaksi,
    kelihatan kayak bandar raksasa) padahal di broksum papan reguler cuma 4.71B/1000trx (=6.89 juta).
    Mayoritas broker selisihnya ~1% (AK +0.9%, BB +0.04%, SS 0%), tapi KZ/IF meleset +34%. Jadi TV/TF
    dari sumber ini cuma buat kasar-kasaran; yang dipakai buat sinyal beneran tetap CSV papan reguler.
    """
    return [{
        "code": row["IDFirm"],
        "firm_name": row.get("FirmName", ""),
        "nval_rp": None,
        "tval_rp": row["Value"],
        "tfreq": row["Frequency"],
        "source": "idx",
    } for row in fetch_broker_summary(date_str)]
