"""Puller NVAL per broker dari Stockbit.

ponytail: KENAPA TOKENNYA MANUAL. Login Stockbit di-CAPTCHA, jadi gak bisa diotomatisin. Token JWT
harus di-copy sendiri dari DevTools ke .env (STOCKBIT_TOKEN), umurnya ~24 jam jadi refresh tiap hari.
Ini bukan males: Pulse-CLI (github.com/sukirman1901/Pulse-CLI, satu-satunya tool open-source yang
beneran narik data ini) juga pakai cara yang sama persis, README-nya nyebut CAPTCHA sebagai alasannya.
bdmtool malah nyerah total ke API dan pilih export manual HOTS/IPOT.

ponytail: SCOPE. Endpoint ini per-SAHAM, sementara sheet-nya market-wide. Jangan dipakai buat nyapu
~900 saham tiap hari - itu persis pola akses yang rate-limit + CAPTCHA-nya dibikin buat nyegah, dan
bakal bikin akun kamu kena. Pakai buat watchlist (puluhan saham), bukan seluruh bursa. Kalau butuh
market-wide beneran, jalur resminya IDX Data Services (berbayar, idxdata@idx.co.id).

ponytail: BENTUK RESPONSE BELUM DIVERIFIKASI. Endpoint + param di bawah didapat dari recon (Pulse-CLI
+ probe), tapi tanpa token cuma balik 401 - jadi parser di bawah nebak strukturnya. Jalanin
`python stockbit_data.py BBRI 2026-07-03 --dump` buat lihat JSON aslinya, baru _parse_rows()
disesuaikan. Sengaja gak nebak diem-diem: mending eksplisit gagal daripada diam-diam salah angka.
"""

import argparse
import json
import subprocess
import sys

BASE = "https://exodus.stockbit.com/marketdetectors"
TIMEOUT = 30


def _get(url, token):
    """Stockbit di belakang Cloudflare - shell out ke curl, sama alasannya kayak broker_data.py
    (fingerprint TLS requests/urllib3 kena block)."""
    result = subprocess.run(
        ["curl", "-s", "-H", f"Authorization: Bearer {token}", "-H", "Accept: application/json", url],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(f"curl gagal (rc={result.returncode})")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"response bukan JSON: {result.stdout[:200]}")


def _check_auth(payload):
    """401 dari Stockbit dateng sebagai JSON, bukan exception - jadi harus dicek manual."""
    if isinstance(payload, dict) and payload.get("error_type") == "UNAUTHORIZED":
        raise RuntimeError(
            "Token ditolak (UNAUTHORIZED). Token Stockbit umurnya ~24 jam - ambil yang baru dari "
            "DevTools > Network > header Authorization, terus update STOCKBIT_TOKEN di .env."
        )


def fetch_broker_net_raw(ticker, date_str, token, market_board="MARKET_BOARD_REGULER"):
    """Raw JSON net-per-broker buat satu saham, satu hari. date_str: 'YYYY-MM-DD'.
    market_board REGULER = papan reguler doang, nyingkirin negosiasi (yang bikin TV/TF dari IDX ngaco)."""
    url = (f"{BASE}/{ticker.upper()}"
           f"?start_date={date_str}&end_date={date_str}"
           f"&transaction_type=TRANSACTION_TYPE_NET"
           f"&market_board={market_board}"
           f"&investor_type=INVESTOR_TYPE_ALL"
           f"&limit=100")
    payload = _get(url, token)
    _check_auth(payload)
    return payload


def _parse_rows(payload):
    """Ratain JSON Stockbit -> list dict {code, nval_rp, tval_rp, tfreq}.

    ponytail: bentuk aslinya belum keliatan (kena 401 pas recon), jadi ini nyari key yang masuk akal
    di beberapa lokasi umum. Kalau gak ketemu -> raise, JANGAN balikin list kosong: list kosong
    kebaca 'gak ada sinyal hari ini' dan salahnya jadi gak keliatan berhari-hari.
    """
    data = payload
    for key in ("data", "result", "results"):
        if isinstance(data, dict) and key in data:
            data = data[key]
    if isinstance(data, dict):
        for key in ("brokers", "broker_summary", "items", "list", "rows"):
            if key in data:
                data = data[key]
                break
    if not isinstance(data, list):
        raise RuntimeError(
            "Gak nemu list broker di response. Jalanin dengan --dump buat lihat strukturnya, "
            "terus sesuaikan _parse_rows(). Key paling luar: "
            f"{list(payload)[:10] if isinstance(payload, dict) else type(payload).__name__}"
        )

    def pick(row, *names):
        for n in names:
            if n in row and row[n] is not None:
                return row[n]
        return None

    rows = []
    for r in data:
        if not isinstance(r, dict):
            continue
        code = pick(r, "broker_code", "brokerCode", "code", "broker", "id")
        if not code:
            continue
        rows.append({
            "code": str(code).strip().upper(),
            "nval_rp": pick(r, "net_value", "netValue", "nval", "net"),
            "tval_rp": pick(r, "total_value", "totalValue", "tval", "value"),
            "tfreq": pick(r, "total_frequency", "totalFrequency", "tfreq", "frequency", "freq"),
        })
    if not rows:
        raise RuntimeError("List broker ketemu tapi gak ada baris kebaca - cek --dump.")
    return rows


def fetch_broker_net(ticker, date_str, token=None):
    """Net per broker buat satu saham. Token default dari config (.env)."""
    if token is None:
        from config import STOCKBIT_TOKEN
        token = STOCKBIT_TOKEN
    if not token:
        raise RuntimeError("STOCKBIT_TOKEN kosong - isi di .env dulu (lihat .env.example).")
    return _parse_rows(fetch_broker_net_raw(ticker, date_str, token))


def main():
    ap = argparse.ArgumentParser(description="Probe / tarik broker net dari Stockbit.")
    ap.add_argument("ticker")
    ap.add_argument("date", help="YYYY-MM-DD")
    ap.add_argument("--dump", action="store_true", help="print JSON mentah (buat nyocokin parser)")
    args = ap.parse_args()

    from config import STOCKBIT_TOKEN
    if not STOCKBIT_TOKEN:
        print("STOCKBIT_TOKEN kosong. Isi di .env dulu:\n"
              "  1. Buka Stockbit di browser, login.\n"
              "  2. Buka halaman broker summary / bandar detector.\n"
              "  3. DevTools (F12) > Network > klik request ke exodus.stockbit.com >\n"
              "     Headers > Authorization: Bearer <TOKEN>. Copy bagian setelah 'Bearer '.\n"
              "  4. Tulis di .env:  STOCKBIT_TOKEN=<token>\n"
              "Token umurnya ~24 jam, jadi harus di-refresh tiap hari.", file=sys.stderr)
        return 1

    payload = fetch_broker_net_raw(args.ticker, args.date, STOCKBIT_TOKEN)
    _check_auth(payload)

    if args.dump:
        print(json.dumps(payload, indent=2)[:8000])
        return 0

    for r in _parse_rows(payload):
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
