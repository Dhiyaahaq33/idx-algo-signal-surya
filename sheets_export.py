import logging
import os

log = logging.getLogger("idx-algo-signal")

HEADER = ["Tanggal", "Algoritma", "Ticker", "Keterangan"]

ALGO_LABELS = {
    "mean_reversal": "🔁 Mean Reversal",
    "universe": "👥 Pairs / Universe",
    "sector_basket": "🧺 Golden Basket",
    "ipo_momentum": "🚀 Momentum IPO",
    "broker_flow": "🕵️ Broker Anomali (proxy Sun Reversal)",
}


def _describe(s):
    """Kalimat keterangan human-readable per algoritma, senada sama format pesan Telegram (notify.py)."""
    algo = s.get("algo")

    if algo == "mean_reversal":
        return f"Harga {s['last_price']} — turun {s['drop_pct']}% dari rolling high {s['rolling_high']}, mulai reversal"

    if algo == "universe":
        movers = ", ".join(f"{t} {v:+.1f}%" for t, v in s.get("movers", {}).items())
        return f"Grup {s['group']} diam ({s['laggard_change_pct']:+.2f}%) sementara anggota lain gerak: {movers}"

    if algo == "sector_basket":
        return f"{s['ticker_pct']:+.1f}% — ketinggalan dari sektor {s['sector']} (rata-rata sektor +{s['sector_avg_pct']}%)"

    if algo == "ipo_momentum":
        return f"Harga {s['last_price']} — {s['pct_of_target']:+.1f}% dari harga akumulasi {s['accum_price']}"

    if algo == "broker_flow":
        name = s.get("broker_name", "")
        return f"{name} — transaksi hari ini {s['today_value_bn']}M vs rata-rata {s['avg_value_bn']}M ({s['multiple']}x)"

    return ""


def _display_ticker(s):
    return s.get("ticker", "").removeprefix("broker:")


def _get_client():
    """Bikin gspread client dari service account. Return None kalau config gak lengkap (fitur di-skip diam-diam)."""
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not creds_json or not sheet_id:
        return None, None

    import json
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client, sheet_id


def _get_or_init_worksheet(spreadsheet):
    try:
        worksheet = spreadsheet.worksheet("Signals")
        return worksheet
    except Exception:
        pass

    worksheet = spreadsheet.add_worksheet(title="Signals", rows=1000, cols=len(HEADER))
    worksheet.append_row(HEADER)
    worksheet.format("A1:D1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
    })
    worksheet.freeze(rows=1)
    worksheet.columns_auto_resize(0, len(HEADER) - 1)
    return worksheet


def push_signals(signals, date_label):
    """Append tiap sinyal sebagai baris baru ke Google Sheet (tab 'Signals'), dalam bentuk keterangan
    yang enak dibaca (bukan JSON mentah) - biar bisa dipahami langsung tanpa parsing tambahan.

    Butuh env var GOOGLE_SHEETS_CREDENTIALS_JSON (isi JSON service account) dan
    GOOGLE_SHEET_ID (ID spreadsheet, dari URL). Kalau salah satu kosong, fungsi ini
    no-op supaya jalan lokal tanpa Sheets tetap gak error.
    """
    client, sheet_id = _get_client()
    if client is None:
        log.info("      -> Skip push ke Google Sheets (GOOGLE_SHEETS_CREDENTIALS_JSON/GOOGLE_SHEET_ID belum diset)")
        return

    spreadsheet = client.open_by_key(sheet_id)
    worksheet = _get_or_init_worksheet(spreadsheet)

    if not signals:
        log.info("      -> Push ke Google Sheets: 0 sinyal, tidak ada baris ditambahkan")
        return

    rows = []
    for s in signals:
        algo_label = ALGO_LABELS.get(s.get("algo"), s.get("algo", ""))
        rows.append([date_label, algo_label, _display_ticker(s), _describe(s)])

    worksheet.append_rows(rows, value_input_option="RAW")
    worksheet.columns_auto_resize(0, len(HEADER) - 1)
    log.info(f"      -> Push ke Google Sheets: {len(rows)} baris ditambahkan")
