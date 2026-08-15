import json
import logging
import os

log = logging.getLogger("idx-algo-signal")

HEADER = ["date", "algo", "ticker", "details"]


def _get_client():
    """Bikin gspread client dari service account. Return None kalau config gak lengkap (fitur di-skip diam-diam)."""
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not creds_json or not sheet_id:
        return None, None

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client, sheet_id


def push_signals(signals, date_label):
    """Append tiap sinyal sebagai baris baru ke Google Sheet (tab 'Signals').

    Butuh env var GOOGLE_SHEETS_CREDENTIALS_JSON (isi JSON service account) dan
    GOOGLE_SHEET_ID (ID spreadsheet, dari URL). Kalau salah satu kosong, fungsi ini
    no-op supaya jalan lokal tanpa Sheets tetap gak error.
    """
    client, sheet_id = _get_client()
    if client is None:
        log.info("      -> Skip push ke Google Sheets (GOOGLE_SHEETS_CREDENTIALS_JSON/GOOGLE_SHEET_ID belum diset)")
        return

    spreadsheet = client.open_by_key(sheet_id)
    try:
        worksheet = spreadsheet.worksheet("Signals")
    except Exception:
        worksheet = spreadsheet.add_worksheet(title="Signals", rows=1000, cols=len(HEADER))
        worksheet.append_row(HEADER)

    if not signals:
        log.info("      -> Push ke Google Sheets: 0 sinyal, tidak ada baris ditambahkan")
        return

    rows = []
    for s in signals:
        rest = {k: v for k, v in s.items() if k not in ("ticker", "algo")}
        rows.append([date_label, s.get("algo", ""), s.get("ticker", ""), json.dumps(rest, ensure_ascii=False)])

    worksheet.append_rows(rows, value_input_option="RAW")
    log.info(f"      -> Push ke Google Sheets: {len(rows)} baris ditambahkan")
