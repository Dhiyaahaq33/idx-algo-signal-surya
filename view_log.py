import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

LOG_FILE = Path(__file__).parent / "signal.log"
RUN_START = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[1/3\] Fetching")
TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ ")
DATA_DATE = re.compile(r"data harga per (\S+)")
SIGNAL_COUNT = re.compile(r"\((\d+) sinyal\)")
SECTION_HEADER = re.compile(r"^<b>(.+?)</b>$")
BULLET_TICKER = re.compile(r"^• <b>([^<]+)</b>")
STRIP_HTML = re.compile(r"</?b>")


def _load_all_lines():
    # RotatingFileHandler: .3 paling lama -> .1 -> signal.log paling baru
    files = [LOG_FILE.with_suffix(LOG_FILE.suffix + f".{i}") for i in (3, 2, 1)] + [LOG_FILE]
    lines = []
    for f in files:
        if f.exists():
            lines += f.read_text(encoding="utf-8").splitlines()
    return lines


def parse_runs():
    runs, current = [], []
    for line in _load_all_lines():
        if RUN_START.match(line):
            if current:
                runs.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        runs.append(current)
    return list(reversed(runs))  # terbaru duluan


def summarize(block):
    text = "\n".join(block)
    started_at = RUN_START.match(block[0]).group(1)
    m_date = DATA_DATE.search(text)
    data_date = m_date.group(1) if m_date else "?"
    m_count = SIGNAL_COUNT.search(text)
    signal_count = m_count.group(1) if m_count else ("0" if "Gak ada sinyal" in text else "?")
    status = "OK" if "Selesai." in text else "GAGAL/TERPOTONG"
    return started_at, data_date, signal_count, status


def extract_signals(block):
    """Return list of (judul_algo, ticker) yang muncul di 1 run."""
    results, current_section = [], None
    for line in block:
        msg = TIMESTAMP_PREFIX.sub("", line).strip()
        header = SECTION_HEADER.match(msg)
        if header:
            current_section = header.group(1)
            continue
        bullet = BULLET_TICKER.match(msg)
        if bullet and current_section:
            results.append((current_section, bullet.group(1)))
    return results


def cmd_list():
    runs = parse_runs()
    if not runs:
        print("Belum ada log. Jalanin `python main.py` dulu minimal sekali.")
        return

    print(f"Riwayat run ({len(runs)} total):\n")
    for i, block in enumerate(runs, 1):
        started_at, data_date, signal_count, status = summarize(block)
        print(f"[{i}] dijalankan {started_at} -> data per {data_date} -> {signal_count} sinyal -> {status}")

    choice = sys.argv[2] if len(sys.argv) > 2 else input("\nPilih nomor atau tanggal (YYYY-MM-DD), Enter buat keluar: ").strip()
    if not choice:
        return

    if re.match(r"^\d{4}-\d{2}-\d{2}$", choice):
        matches = [b for b in runs if summarize(b)[1] == choice]
        if not matches:
            print(f"Gak ketemu run buat data tanggal {choice}.")
            return
        block = matches[0]
    else:
        idx = int(choice) - 1
        if not (0 <= idx < len(runs)):
            print("Nomor gak valid.")
            return
        block = runs[idx]

    print("\n" + "=" * 60)
    print(STRIP_HTML.sub("", "\n".join(block)))


def compute_streaks():
    """Return (trading_days sorted, list of (streak, (algo, ticker), dates) sorted desc, streak>=2 aja).
    dates = list tanggal persis (hari bursa berurutan) tempat sinyal itu muncul, terbaru duluan."""
    runs = parse_runs()
    by_date = {}
    for block in runs:
        _, data_date, _, _ = summarize(block)
        if data_date == "?":
            continue
        by_date.setdefault(data_date, set()).update(extract_signals(block))

    trading_days = sorted(by_date.keys())  # hari bursa asli (dari data_date tiap run), bukan tanggal kalender
    if len(trading_days) < 2:
        return trading_days, []

    all_keys = set().union(*by_date.values())
    streaks = []
    for key in all_keys:
        dates = []
        for d in reversed(trading_days):
            if key in by_date[d]:
                dates.append(d)
            else:
                break
        if len(dates) >= 2:
            streaks.append((len(dates), key, dates))
    streaks.sort(reverse=True)
    return trading_days, streaks


def build_streak_report():
    trading_days, streaks = compute_streaks()
    if len(trading_days) < 2:
        return "Belum cukup history (minimal 2 hari bursa tercatat) buat analisa beruntun. Jalanin main.py/backfill.py beberapa hari dulu."

    lines = [f"Hari bursa tercatat: {trading_days[0]} s/d {trading_days[-1]} ({len(trading_days)} hari)\n"]
    if not streaks:
        lines.append("Gak ada sinyal yang muncul berturut-turut >=2 hari bursa terakhir.")
        return "\n".join(lines)

    lines.append("Sinyal yang BERTURUT-TURUT muncul di hari bursa terakhir:\n")
    for streak, (algo, ticker), dates in streaks:
        tanggal = ", ".join(reversed(dates))  # tampilin dari yang paling lama ke terbaru
        lines.append(f"  {streak}x berturut-turut -- [{algo}] {ticker} -- tanggal: {tanggal}")
    return "\n".join(lines)


def build_watch_recommendation(top_n=10):
    trading_days, streaks = compute_streaks()
    if len(trading_days) < 2:
        return "📌 Belum cukup history buat rekomendasi (minimal 2 hari bursa tercatat)."
    if not streaks:
        return f"📌 Belum ada yang konsisten muncul >=2 hari bursa terakhir (per {trading_days[-1]}). Coba lagi beberapa hari lagi."

    lines = [f"📌 <b>Rekomendasi Pantau</b> (konsisten di {len(trading_days)} hari bursa terakhir, {trading_days[0]} s/d {trading_days[-1]})\n"]
    for streak, (algo, ticker), dates in streaks[:top_n]:
        tanggal = ", ".join(reversed(dates))
        lines.append(f"• <b>{ticker}</b> — {streak}x berturut-turut di {algo} ({tanggal})")
    lines.append("\n<i>Bukan rekomendasi beli — cuma yang paling konsisten muncul di screening, tetep cross-check manual.</i>")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "streak":
        print(build_streak_report())
    elif len(sys.argv) > 1 and sys.argv[1] == "watch":
        print(STRIP_HTML.sub("", build_watch_recommendation()).replace("<i>", "").replace("</i>", ""))
    else:
        cmd_list()
