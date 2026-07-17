"""Bandarmology lewat broker summary: cari broker yang transaksinya dikuasai segelintir pemain.

Dua metrik inti, dua-duanya dihitung dalam satuan sheet (TVAL/NVAL miliar, TFREQ ribu):

  TV/TF        = TVAL_B / TFREQ_K   -> juta rupiah per transaksi ("modal rata-rata per orang" di
                                       broker itu). Makin GEDE = makin bandar: nguasain nilai segitu
                                       gede cuma dengan sekian frekuensi.
  MODAL 1 ORG  = TV/TF / 1000        -> sama persis, cuma diskala biar enak dibaca.
  NV/(TV/TF)   = NVAL_B / (TV/TF)    -> proksi JUMLAH ORANG yang net-buy di broker itu. Makin KECIL
                                       (mendekati 1 atau 0) = makin bandar: net value segitu gede
                                       ditanggung sedikit pelaku.

Bandar candidate = TV/TF tinggi DAN NV/(TV/TF) rendah. Di sheet 3 Jul 2026, SS kena dua-duanya
(TV/TF 23.03 = tertinggi, NV/(TV/TF) 0.93 = mepet 1) - dan emang SS yang paling banyak dipantau.

ponytail: perhatiin satuan NV/(TV/TF). Karena NVAL dalam miliar dan TFREQ dalam ribu, hasilnya dalam
RIBUAN transaksi - jadi SS = 0.93 artinya ~930 transaksi net-buy, bukan 1 orang harfiah. Rankingnya
tetap valid (makin kecil makin terkonsentrasi), cuma jangan dibaca "1 = satu orang".
"""

from config import (
    BANDAR_MIN_TV_TF, BANDAR_MAX_NV_RATIO, BANDAR_MIN_TVAL_BN, BROKSUM_TOP_N,
)


def compute_metrics(records):
    """records: list dict {code, nval_rp, tval_rp, tfreq}. Return list baru + kolom turunan,
    diurut NVAL desc (persis kayak sheet). Baris dengan tfreq/tval 0 di-skip (gak bisa dibagi)."""
    out = []
    for r in records:
        tval_rp, tfreq = r.get("tval_rp"), r.get("tfreq")
        if not tval_rp or not tfreq:
            continue

        tval_bn = tval_rp / 1e9
        tfreq_k = tfreq / 1e3
        tv_tf = tval_bn / tfreq_k              # juta rupiah per transaksi

        nval_rp = r.get("nval_rp")
        nval_bn = None if nval_rp is None else nval_rp / 1e9
        nv_ratio = None if nval_bn is None or tv_tf == 0 else nval_bn / tv_tf

        out.append({
            **r,
            "nval_bn": nval_bn,
            "tval_bn": tval_bn,
            "tfreq_k": tfreq_k,
            "tv_tf": tv_tf,
            "modal_1org": tv_tf / 1000,
            "nv_per_tvtf": nv_ratio,
        })

    # NVAL None (sumber IDX) ditaruh paling bawah, bukan bikin sort meledak
    out.sort(key=lambda r: (r["nval_bn"] is not None, r["nval_bn"] or 0), reverse=True)
    return out


def is_bandar(row):
    """Kena kalau modal per transaksi gede TAPI ditanggung sedikit pelaku. Butuh NVAL -> baris
    tanpa NVAL (sumber IDX) otomatis gak pernah kena.

    ponytail: syarat nv_per_tvtf > 0 itu WAJIB, bukan basa-basi. Broker net SELL punya NVAL negatif ->
    NV/(TV/TF) ikut negatif -> lolos gitu aja dari cek "<= BANDAR_MAX_NV_RATIO" dan ke-flag bandar,
    padahal metodenya soal konsentrasi net BUY (sheet-nya emang cuma top-20 net buyer). Deteksi
    distribusi/net sell butuh aturan sendiri, belum dibikin.
    """
    if row["nv_per_tvtf"] is None:
        return False
    if row["tval_bn"] < BANDAR_MIN_TVAL_BN:
        return False
    if row["nv_per_tvtf"] <= 0:
        return False
    return row["tv_tf"] >= BANDAR_MIN_TV_TF and row["nv_per_tvtf"] <= BANDAR_MAX_NV_RATIO


def screen(prices=None, target_date=None, records=None):
    """Butuh broksum papan reguler (ada NVAL) dari CSV export terminal - lihat broksum_data.py soal
    kenapa gak bisa auto-fetch. Gak ada CSV buat tanggal itu = gak ada sinyal (bukan error)."""
    if records is None:
        from broksum_data import load_for_date
        records = load_for_date(target_date)
    if not records:
        return []

    rows = compute_metrics(records)
    ranked = rows[:BROKSUM_TOP_N]

    signals = []
    for rank, row in enumerate(ranked, start=1):
        if not is_bandar(row):
            continue
        signals.append({
            "ticker": f"broker:{row['code']}",
            "algo": "bandar_broksum",
            "date": row.get("date", target_date),
            "rank_nval": rank,
            "nval_bn": round(row["nval_bn"], 2),
            "tval_bn": round(row["tval_bn"], 2),
            "tfreq_k": round(row["tfreq_k"], 2),
            "tv_tf": round(row["tv_tf"], 2),
            "modal_1org": round(row["modal_1org"], 6),
            "nv_per_tvtf": round(row["nv_per_tvtf"], 2),
        })

    # yang paling terkonsentrasi (NV/(TV/TF) terkecil) duluan = kandidat bandar terkuat
    signals.sort(key=lambda s: s["nv_per_tvtf"])
    return signals
