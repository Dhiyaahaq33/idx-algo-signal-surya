from broker_data import fetch_recent_broker_summaries
from config import BROKER_FLOW_LOOKBACK_DAYS, BROKER_FLOW_ANOMALY_MULTIPLE, BROKER_FLOW_MIN_BASELINE_VALUE


def screen(prices=None, target_date=None):
    """Deteksi broker yang value transaksinya hari ini jauh di atas rata-rata dia sendiri.

    ponytail: ini APPROXIMATION dari algoritma "Sun Reversal" di modul trading, bukan replika persis.
    Data resmi IDX cuma level pasar (broker X total transaksi berapa hari ini), BUKAN breakdown per
    saham (broker X beli saham Y berapa) - itu yang gak ada API gratisnya. Jadi sinyal ini cuma bilang
    "broker ini lagi aktif banget", BUKAN "broker ini beli saham tertentu". Cross-check manual ke
    HOTS/IPOT kalau mau tau saham apa yang dia gerakin.
    """
    history = fetch_recent_broker_summaries(days=BROKER_FLOW_LOOKBACK_DAYS, reference_date=target_date)
    if len(history) < 2:
        return []

    latest_date, latest_data = history[0]
    baseline_days = history[1:]

    baseline_totals = {}
    for _, day_data in baseline_days:
        for row in day_data:
            code = row["IDFirm"]
            baseline_totals.setdefault(code, []).append(row["Value"])

    signals = []
    for row in latest_data:
        code = row["IDFirm"]
        today_value = row["Value"]
        past_values = baseline_totals.get(code, [])
        if not past_values:
            continue

        avg_value = sum(past_values) / len(past_values)
        if avg_value < BROKER_FLOW_MIN_BASELINE_VALUE:
            continue

        multiple = today_value / avg_value
        if multiple >= BROKER_FLOW_ANOMALY_MULTIPLE:
            signals.append({
                "ticker": f"broker:{code}",
                "algo": "broker_flow",
                "broker_name": row["FirmName"],
                "date": latest_date,
                "today_value_bn": round(today_value / 1e9, 1),
                "avg_value_bn": round(avg_value / 1e9, 1),
                "multiple": round(multiple, 1),
            })

    signals.sort(key=lambda s: s["multiple"], reverse=True)
    return signals
