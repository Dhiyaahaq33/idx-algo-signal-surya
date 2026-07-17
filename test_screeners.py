import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from screeners import mean_reversal, universe, sector_basket, ipo_momentum, broker_flow, bandar_broksum
import broksum_data


def _df(closes):
    return pd.DataFrame({"Close": closes})


def test_mean_reversal_flags_drop_then_reversal():
    # turun dari 100 ke 80 (20% drop), lalu 2 hari naik -> harus kena
    closes = [100] * 20 + [80, 82, 85]
    prices = {"XXXX": _df(closes)}
    signals = mean_reversal.screen(prices)
    assert len(signals) == 1
    assert signals[0]["ticker"] == "XXXX"


def test_mean_reversal_ignores_no_reversal():
    # turun terus tanpa reversal -> gak boleh kena
    closes = [100] * 20 + [80, 78, 75]
    prices = {"XXXX": _df(closes)}
    assert mean_reversal.screen(prices) == []


def test_universe_flags_laggard():
    universe.OWNERSHIP_GROUPS = {"testgroup": ["A", "B", "C"]}
    prices = {
        "A": _df([100, 106]),   # +6% mover
        "B": _df([100, 107]),   # +7% mover
        "C": _df([100, 100.2]),  # diam, laggard
    }
    signals = universe.screen(prices)
    assert len(signals) == 1
    assert signals[0]["ticker"] == "C"


def test_sector_basket_flags_laggard_in_hot_sector():
    sector_basket.SECTOR_MAP = {"A": "sawit", "B": "sawit", "C": "kesehatan"}
    sector_basket.SECTOR_LOOKBACK_DAYS = 1
    prices = {
        "A": _df([100, 120]),   # +20%
        "B": _df([100, 105]),   # +5%, laggard vs sector avg 12.5%
        "C": _df([100, 100]),   # sektor lain, gak kepilih
    }
    signals = sector_basket.screen(prices)
    assert len(signals) == 1
    assert signals[0]["ticker"] == "B"


def test_ipo_momentum_flags_when_halfway_to_target():
    ipo_momentum.IPO_WATCH = [{"ticker": "Z", "accum_price": 1000}]
    prices = {"Z": _df([1500])}  # +50% dari accum price
    signals = ipo_momentum.screen(prices)
    assert len(signals) == 1
    assert signals[0]["pct_of_target"] == 50.0


def test_broker_flow_flags_anomaly_above_baseline():
    baseline = [("2026-01-0%d" % i, [{"IDFirm": "AA", "FirmName": "Test Sekuritas", "Value": 1_000_000_000}])
                for i in range(2, 6)]  # baseline avg = 1B
    latest = ("2026-01-06", [{"IDFirm": "AA", "FirmName": "Test Sekuritas", "Value": 3_000_000_000}])  # 3x
    broker_flow.fetch_recent_broker_summaries = lambda days=10, reference_date=None: [latest] + baseline

    signals = broker_flow.screen()
    assert len(signals) == 1
    assert signals[0]["multiple"] == 3.0


def test_broker_flow_ignores_below_threshold():
    baseline = [("2026-01-0%d" % i, [{"IDFirm": "AA", "FirmName": "Test Sekuritas", "Value": 1_000_000_000}])
                for i in range(2, 6)]
    latest = ("2026-01-06", [{"IDFirm": "AA", "FirmName": "Test Sekuritas", "Value": 1_200_000_000}])  # 1.2x, di bawah 2x
    broker_flow.fetch_recent_broker_summaries = lambda days=10, reference_date=None: [latest] + baseline

    assert broker_flow.screen() == []


# Angka asli dari sheet broksum 3 Juli 2026 (CODE, NVAL B, TVAL B, TFREQ K, TV/TF, MODAL 1 ORG, NV/(TV/TF)).
# Ini oracle-nya: kalau compute_metrics() geser dari sini berarti rumusnya salah.
# Catatan RB: sheet nampilin TFREQ K = "1" (dibulatkan 0 desimal), nilai aslinya 0.684 - ketauan dari
# TV/TF sheet-nya sendiri (4.71/6.885964912 = 0.684). Dikuatin data IDX: freq RB 710 all-board vs 684
# reguler; selisih 26 transaksi itu bawa ~413 miliar alias block trade negosiasi.
SHEET_2026_07_03 = [
    ("KZ", 293.31, 364.48, 18.55, 19.64851752, 0.01964851752, 14.92784378),
    ("AK", 146.37, 1920.0, 177.83, 10.79682843, 0.01079682843, 13.55675891),
    ("IF", 140.93, 221.7, 12.57, 17.6372315, 0.0176372315, 7.990483085),
    ("AZ", 68.45, 348.73, 31.78, 10.97325362, 0.01097325362, 6.237894646),
    ("BB", 52.65, 221.16, 26.41, 8.374100719, 0.008374100719, 6.287242268),
    ("PD", 51.76, 665.56, 116.91, 5.692926183, 0.005692926183, 9.091985095),
    ("TP", 36.96, 179.96, 14.01, 12.84511064, 0.01284511064, 2.877359413),
    ("OD", 35.91, 277.57, 47.33, 5.864567927, 0.005864567927, 6.123213244),
    ("BK", 34.07, 576.54, 40.66, 14.17953763, 0.01417953763, 2.402758178),
    ("LG", 31.06, 234.52, 26.16, 8.964831804, 0.008964831804, 3.464649497),
    ("SS", 21.44, 73.24, 3.18, 23.03144654, 0.02303144654, 0.9309011469),
    ("GR", 21.08, 200.16, 21.14, 9.468306528, 0.009468306528, 2.2263749),
    ("AI", 19.74, 87.35, 7.39, 11.82002706, 0.01182002706, 1.670046938),
    ("AG", 12.51, 92.32, 10.91, 8.461961503, 0.008461961503, 1.478380633),
    ("FS", 9.66, 32.19, 3.0, 10.73, 0.01073, 0.9002795899),
    ("DU", 3.78, 8.89, 1.31, 6.786259542, 0.006786259542, 0.557007874),
    ("TS", 2.24, 7.55, 1.44, 5.243055556, 0.005243055556, 0.4272317881),
    ("IN", 2.12, 37.82, 4.37, 8.654462243, 0.008654462243, 0.2449603384),
    ("AR", 1.51, 9.56, 2.31, 4.138528139, 0.004138528139, 0.3648640167),
    ("RB", 1.42, 4.71, 0.684, 6.885964912, 0.006885964912, 0.2062165605),
]


def _sheet_records():
    return [{"code": c, "nval_rp": nval * 1e9, "tval_rp": tval * 1e9, "tfreq": tfreq * 1e3}
            for c, nval, tval, tfreq, _, _, _ in SHEET_2026_07_03]


def test_bandar_metrics_match_sheet_exactly():
    rows = {r["code"]: r for r in bandar_broksum.compute_metrics(_sheet_records())}
    assert len(rows) == 20
    for code, _, _, _, tv_tf, modal, nv_ratio in SHEET_2026_07_03:
        r = rows[code]
        assert abs(r["tv_tf"] - tv_tf) < 1e-6, f"{code} TV/TF {r['tv_tf']} != {tv_tf}"
        assert abs(r["modal_1org"] - modal) < 1e-9, f"{code} MODAL 1 ORG {r['modal_1org']} != {modal}"
        assert abs(r["nv_per_tvtf"] - nv_ratio) < 1e-6, f"{code} NV/(TV/TF) {r['nv_per_tvtf']} != {nv_ratio}"


def test_bandar_metrics_sorted_by_nval_desc():
    rows = bandar_broksum.compute_metrics(_sheet_records())
    assert [r["code"] for r in rows[:3]] == ["KZ", "AK", "IF"]  # urutan sheet
    assert rows[-1]["code"] == "RB"


def test_bandar_flags_concentrated_broker():
    # Threshold default (TV/TF >= 10, NV/(TV/TF) <= 2, TVAL >= 10M) di sheet 3 Jul cuma nyaring 3 broker.
    signals = bandar_broksum.screen(records=_sheet_records(), target_date="2026-07-03")
    codes = [s["ticker"].removeprefix("broker:") for s in signals]
    assert codes == ["FS", "SS", "AI"]  # diurut nv_per_tvtf naik: 0.90, 0.93, 1.67
    # KZ NVAL-nya #1 tapi NV/(TV/TF) 14.93 = rame -> bukan bandar
    assert "KZ" not in codes
    # PD frekuensinya paling gede & TV/TF cuma 5.69 = ritel -> bukan bandar
    assert "PD" not in codes


def test_bandar_ignores_net_seller():
    # NVAL negatif -> NV/(TV/TF) negatif -> jangan sampai lolos cek "<= BANDAR_MAX_NV_RATIO".
    # Metodenya soal konsentrasi net BUY; net sell butuh aturan sendiri.
    records = [{"code": "XX", "nval_rp": -50e9, "tval_rp": 73.24e9, "tfreq": 3180}]
    rows = bandar_broksum.compute_metrics(records)
    assert rows[0]["nv_per_tvtf"] < 0
    assert bandar_broksum.screen(records=records) == []


def test_bandar_ignores_rows_without_nval():
    # sumber IDX gak punya NVAL -> gak boleh bikin sinyal (apalagi crash)
    records = [{"code": "RB", "nval_rp": None, "tval_rp": 417.92e9, "tfreq": 710}]
    assert bandar_broksum.screen(records=records) == []


def test_bandar_skips_zero_frequency():
    records = [{"code": "ZZ", "nval_rp": 1e9, "tval_rp": 1e9, "tfreq": 0}]
    assert bandar_broksum.compute_metrics(records) == []


def test_broksum_csv_reads_sheet_style_header_and_units():
    path = os.path.join(os.path.dirname(__file__), "broksum", "2026-07-03.csv")
    records = broksum_data.load_broksum_csv(path)
    assert len(records) == 20
    kz = next(r for r in records if r["code"] == "KZ")
    assert kz["nval_rp"] == 293.31e9   # suffix "B" -> miliar
    assert kz["tfreq"] == 18550        # suffix "K" -> ribuan
    # dan hasil metriknya tetap sama kayak sheet
    rows = {r["code"]: r for r in bandar_broksum.compute_metrics(records)}
    assert abs(rows["KZ"]["tv_tf"] - 19.64851752) < 1e-6


def test_broksum_csv_parses_id_number_format_and_negatives():
    import tempfile, pathlib
    csv_text = "CODE,NVAL B,TVAL B,TFREQ K\nXX,\"-1.234,5\",\"2.000,0\",\"1,5\"\n"
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.csv"
        p.write_text(csv_text, encoding="utf-8")
        r = broksum_data.load_broksum_csv(p)[0]
    assert r["nval_rp"] == -1234.5e9   # net SELL, harus kebaca negatif
    assert r["tfreq"] == 1500


def test_stockbit_parser_feeds_metrics_with_sheet_numbers():
    # bentuk JSON-nya masih tebakan (recon kena 401), tapi kontraknya jelas: apa pun yang keluar
    # _parse_rows() harus bisa langsung masuk compute_metrics() dan ngasih angka yang sama kayak sheet.
    import stockbit_data
    payload = {"data": {"brokers": [
        {"broker_code": "kz", "net_value": 293.31e9, "total_value": 364.48e9, "total_frequency": 18550},
        {"brokerCode": "SS", "netValue": 21.44e9, "totalValue": 73.24e9, "totalFrequency": 3180},
    ]}}
    rows = stockbit_data._parse_rows(payload)
    assert rows[0]["code"] == "KZ"  # dinormalin ke huruf besar

    metrics = {r["code"]: r for r in bandar_broksum.compute_metrics(rows)}
    assert abs(metrics["KZ"]["tv_tf"] - 19.64851752) < 1e-6
    assert abs(metrics["SS"]["nv_per_tvtf"] - 0.9309011469) < 1e-6


def test_stockbit_parser_raises_on_unknown_shape():
    # KRUSIAL: bentuk gak dikenal harus MELEDAK, bukan balik list kosong - list kosong kebaca
    # "gak ada sinyal hari ini" dan salahnya gak keliatan berhari-hari.
    import stockbit_data
    try:
        stockbit_data._parse_rows({"weird": {"nested": 1}})
    except RuntimeError:
        pass
    else:
        assert False, "harusnya raise, bukan diam-diam balik kosong"


def test_stockbit_rejects_expired_token():
    import stockbit_data
    try:
        stockbit_data._check_auth({"error_type": "UNAUTHORIZED", "message": "Unauthorized"})
    except RuntimeError as e:
        assert "24 jam" in str(e)  # pesannya harus nunjukin cara benerin
    else:
        assert False, "token ditolak harusnya raise"


if __name__ == "__main__":
    test_mean_reversal_flags_drop_then_reversal()
    test_mean_reversal_ignores_no_reversal()
    test_universe_flags_laggard()
    test_sector_basket_flags_laggard_in_hot_sector()
    test_ipo_momentum_flags_when_halfway_to_target()
    test_broker_flow_flags_anomaly_above_baseline()
    test_broker_flow_ignores_below_threshold()
    test_bandar_metrics_match_sheet_exactly()
    test_bandar_metrics_sorted_by_nval_desc()
    test_bandar_flags_concentrated_broker()
    test_bandar_ignores_net_seller()
    test_bandar_ignores_rows_without_nval()
    test_bandar_skips_zero_frequency()
    test_broksum_csv_reads_sheet_style_header_and_units()
    test_broksum_csv_parses_id_number_format_and_negatives()
    test_stockbit_parser_feeds_metrics_with_sheet_numbers()
    test_stockbit_parser_raises_on_unknown_shape()
    test_stockbit_rejects_expired_token()
    print("all screener tests passed")
