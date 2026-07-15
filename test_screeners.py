import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from screeners import mean_reversal, universe, sector_basket, ipo_momentum, broker_flow


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


if __name__ == "__main__":
    test_mean_reversal_flags_drop_then_reversal()
    test_mean_reversal_ignores_no_reversal()
    test_universe_flags_laggard()
    test_sector_basket_flags_laggard_in_hot_sector()
    test_ipo_momentum_flags_when_halfway_to_target()
    test_broker_flow_flags_anomaly_above_baseline()
    test_broker_flow_ignores_below_threshold()
    print("all screener tests passed")
