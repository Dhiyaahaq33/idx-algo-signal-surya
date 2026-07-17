import argparse
import logging
import logging.handlers
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # biar emoji di pesan sinyal gak crash pas di-print/log ke file

from config import WATCHLIST, IPO_WATCH
from data import fetch_prices
from screeners import mean_reversal, universe, sector_basket, ipo_momentum, broker_flow, bandar_broksum
from notify import format_message, send_telegram

SCREENERS = [mean_reversal, universe, sector_basket, ipo_momentum, broker_flow, bandar_broksum]

# ponytail: Python yang nulis log sendiri (bukan numpang shell "> run.log" di Task Scheduler) - kebukti
# lebih reliable, shell redirect kemarin gagal pas task di-trigger. RotatingFileHandler biar gak numpuk
# tak terbatas selama dipakai tiap hari.
LOG_FILE = Path(__file__).parent / "signal.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("idx-algo-signal")


def parse_args():
    parser = argparse.ArgumentParser(description="Jalanin screening sinyal trading IDX.")
    parser.add_argument(
        "date", nargs="?", default=None,
        help="Tanggal analisis format YYYY-MM-DD (misal 2026-06-15). Kosongin buat data terbaru.",
    )
    return parser.parse_args()


def run(target_date=None, notify=True):
    tickers = set(WATCHLIST) | {e["ticker"] for e in IPO_WATCH}
    log.info(f"[1/3] Fetching {len(tickers)} ticker dari yfinance (sampai {target_date or 'terbaru'})...")
    prices = fetch_prices(sorted(tickers), end_date=target_date)
    log.info(f"      -> {len(prices)}/{len(tickers)} ticker berhasil ke-fetch")

    # tanggal data yang BENERAN dipakai (hari bursa terakhir yang ada datanya, bukan asumsi "hari ini")
    latest_dates = [df.index[-1] for df in prices.values() if not df.empty]
    data_as_of = max(latest_dates).strftime("%Y-%m-%d") if latest_dates else (target_date or "?")
    log.info(f"      -> data harga per {data_as_of}")

    log.info("[2/3] Menjalankan screener...")
    signals = []
    for screener in SCREENERS:
        result = screener.screen(prices, target_date=target_date)
        log.info(f"      -> {screener.__name__.split('.')[-1]}: {len(result)} sinyal")
        signals.extend(result)

    message = format_message(signals, date_label=data_as_of)
    log.info(message)
    if notify:
        log.info("[3/3] Mengirim ke Telegram...")
        send_telegram(message)
    else:
        log.info("[3/3] Skip kirim Telegram (backfill mode).")
    log.info("Selesai.")
    return signals


if __name__ == "__main__":
    args = parse_args()
    try:
        run(target_date=args.date)
    except Exception:
        log.exception("Run gagal")
        raise
