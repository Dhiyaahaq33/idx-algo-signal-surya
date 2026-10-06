import datetime
import logging
import os

log = logging.getLogger("idx-algo-signal")

HEADER = ["Tanggal", "Algoritma", "Ticker", "Keterangan"]

# epoch tanggal Google Sheets (serial 0 = 30 Des 1899) - dipakai supaya kolom Tanggal tersimpan
# sebagai angka tanggal ASLI (bisa di-sort kronologis, bisa diformat dd/mm), bukan teks yang
# auto-parse-nya Sheets gak reliable buat string ISO "YYYY-MM-DD" tergantung locale spreadsheet.
_SHEETS_EPOCH = datetime.date(1899, 12, 30)


def _to_sheets_date_serial(date_label):
    d = datetime.datetime.strptime(date_label, "%Y-%m-%d").date()
    return (d - _SHEETS_EPOCH).days

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
    except Exception:
        worksheet = spreadsheet.add_worksheet(title="Signals", rows=1000, cols=len(HEADER))

    # header/format juga perlu di-setup ulang kalau sheet-nya ada tapi kosong (mis. abis di-clear manual)
    if worksheet.row_values(1) != HEADER:
        worksheet.clear()
        worksheet.append_row(HEADER)
        worksheet.format("A1:D1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85},
        })
        # kolom A disimpan sebagai serial tanggal asli (biar bisa di-sort bener), cuma DITAMPILKAN dd/mm
        worksheet.format("A2:A1000", {"numberFormat": {"type": "DATE", "pattern": "dd/mm"}})
        worksheet.freeze(rows=1)
        worksheet.columns_auto_resize(0, len(HEADER) - 1)

    return worksheet


_MONTH_START_COLOR = {"red": 1.0, "green": 0.95, "blue": 0.8}  # kuning tipis, nandain awal bulan
_DAY_BAND_COLORS = [
    {"red": 1.0, "green": 1.0, "blue": 1.0},      # putih
    {"red": 0.93, "green": 0.95, "blue": 0.98},   # abu-biru tipis
]


def _style_rows_by_day(worksheet, last_row):
    """Selang-seling warna tiap ganti tanggal (zebra per hari, bukan per baris), dan tetap nandain
    awal bulan dengan warna kuning tipis (nimpa warna zebra-nya) biar tetap paling nonjol. Jalan
    tiap push, berdasarkan urutan sheet yang udah di-sort kronologis - full reset & re-derive biar
    idempotent walau ada backfill yang nyisip di tengah bikin urutan/grouping berubah."""
    if last_row <= 2:
        return

    serials = worksheet.get(f"A2:A{last_row}", value_render_option="UNFORMATTED_VALUE")
    dates = [_SHEETS_EPOCH + datetime.timedelta(days=int(row[0])) for row in serials if row]

    # kelompokin baris-baris yang tanggalnya sama jadi satu run (start_row, end_row, date)
    runs = []
    for i, d in enumerate(dates):
        sheet_row = i + 2
        if runs and runs[-1]["date"] == d:
            runs[-1]["end"] = sheet_row
        else:
            runs.append({"date": d, "start": sheet_row, "end": sheet_row})

    formats = []
    band = 0
    prev_month = None
    for run in runs:
        is_month_start = prev_month != (run["date"].year, run["date"].month)
        color = _MONTH_START_COLOR if is_month_start else _DAY_BAND_COLORS[band % 2]
        formats.append({
            "range": f"A{run['start']}:D{run['end']}",
            "format": {"backgroundColor": color},
        })
        prev_month = (run["date"].year, run["date"].month)
        band += 1

    worksheet.batch_format(formats)


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

    date_serial = _to_sheets_date_serial(date_label)
    rows = []
    for s in signals:
        algo_label = ALGO_LABELS.get(s.get("algo"), s.get("algo", ""))
        rows.append([date_serial, algo_label, _display_ticker(s), _describe(s)])

    worksheet.append_rows(rows, value_input_option="RAW")

    last_row = len(worksheet.get_all_values())
    if last_row > 2:
        worksheet.sort((1, "asc"), range=f"A2:D{last_row}")

    _style_rows_by_day(worksheet, last_row)
    worksheet.columns_auto_resize(0, len(HEADER) - 1)
    log.info(f"      -> Push ke Google Sheets: {len(rows)} baris ditambahkan, sheet di-sort ulang & diwarnai per hari")
