import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8")

from broker_data import fetch_recent_broker_summaries
from main import run


def parse_args():
    p = argparse.ArgumentParser(description="Jalanin screening buat N hari bursa terakhir sekaligus, tiap hari kecatat terpisah di signal.log.")
    p.add_argument("days", type=int, help="Berapa hari bursa ke belakang (misal 10)")
    p.add_argument("--end-date", default=None, help="Tanggal akhir YYYY-MM-DD, default hari ini")
    p.add_argument("--notify", action="store_true", help="Kirim juga ke Telegram tiap hari (default: cuma log lokal, gak spam Telegram)")
    return p.parse_args()


def main():
    args = parse_args()
    # ponytail: reuse deteksi hari bursa dari broker_data (skip weekend/libur otomatis) daripada nulis ulang kalender IDX
    trading_days = sorted(d for d, _ in fetch_recent_broker_summaries(days=args.days, reference_date=args.end_date))
    if not trading_days:
        print("Gak ketemu hari bursa buat range ini.")
        return

    print(f"Backfill {len(trading_days)} hari bursa: {trading_days[0]} s/d {trading_days[-1]}")
    for i, d in enumerate(trading_days, 1):
        print(f"\n[{i}/{len(trading_days)}] --- {d} ---")
        run(target_date=d, notify=args.notify)


if __name__ == "__main__":
    main()
