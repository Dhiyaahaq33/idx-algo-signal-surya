from datetime import date, datetime, timedelta
import json
import subprocess

# ponytail: endpoint resmi idx.co.id, dikonfirmasi jalan tanpa auth. Cuma level pasar
# (semua broker, semua saham gabung) - IDX gak buka breakdown broker per-saham secara gratis.
# Cloudflare di depan idx.co.id ngeblok fingerprint TLS-nya `requests`/urllib3 (403), tapi curl.exe
# lolos - jadi shell out ke curl daripada pasang library TLS-impersonation buat 1 endpoint doang.
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://www.idx.co.id/en/market-data/trading-summary/broker-summary"


def fetch_broker_summary(date_str):
    """date_str format YYYYMMDD. Return list kosong kalau libur/weekend."""
    url = f"https://www.idx.co.id/primary/TradingSummary/GetBrokerSummary?length=9999&start=0&date={date_str}"
    result = subprocess.run(
        ["curl", "-s", "-A", UA, "-H", f"Referer: {REFERER}", url],
        capture_output=True, text=True, timeout=20,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    return json.loads(result.stdout).get("data", [])


def fetch_recent_broker_summaries(days=10, max_calendar_lookback=25, reference_date=None):
    """Kumpulin `days` hari bursa terakhir (skip weekend/libur) sampai reference_date ('YYYY-MM-DD').
    Kalau reference_date kosong: mundur dari kemarin, karena data "hari ini" belum final selama market masih jalan."""
    if reference_date:
        d = datetime.strptime(reference_date, "%Y-%m-%d").date()
    else:
        d = date.today() - timedelta(days=1)

    results = []
    checked = 0
    while len(results) < days and checked < max_calendar_lookback:
        try:
            data = fetch_broker_summary(d.strftime("%Y%m%d"))
        except (subprocess.SubprocessError, json.JSONDecodeError):
            data = []
        if data:
            results.append((d.strftime("%Y-%m-%d"), data))
        d -= timedelta(days=1)
        checked += 1
    return results  # index 0 = hari bursa paling baru (<= reference_date)
