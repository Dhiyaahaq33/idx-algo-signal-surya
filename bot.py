import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from main import run as run_screening
from view_log import parse_runs, summarize, build_streak_report, build_watch_recommendation

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
# ponytail: offset disimpen ke file biar restart bot gak ngulang balesin command lama yang belum di-ack
OFFSET_FILE = Path(__file__).parent / ".bot_offset"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HELP_TEXT = (
    "Command yang tersedia:\n"
    "/run — screening data terbaru\n"
    "/run YYYY-MM-DD — screening buat tanggal tertentu\n"
    "/streak — sinyal yang beruntun beberapa hari bursa\n"
    "/status — kapan terakhir bot ini jalan\n"
    "/watch — rekomendasi apa yang perlu dipantau"
)


def reply(text):
    requests.post(f"{API}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)


def cmd_run(args):
    date = args[0] if args else None
    if date and not DATE_RE.match(date):
        reply("Format tanggal salah. Contoh: /run 2026-06-15")
        return
    reply(f"⏳ Jalanin screening buat {date or 'data terbaru'}...")
    run_screening(target_date=date, notify=True)  # run_screening sendiri yang ngirim hasilnya


def cmd_status():
    runs = parse_runs()
    if not runs:
        reply("Belum pernah jalan sama sekali.")
        return
    started_at, data_date, signal_count, status = summarize(runs[0])
    reply(f"Terakhir jalan: {started_at}\nData per: {data_date}\nSinyal: {signal_count}\nStatus: {status}")


def handle_command(text):
    parts = text.strip().split()
    if not parts:
        return
    cmd, args = parts[0].lower(), parts[1:]

    if cmd == "/run":
        cmd_run(args)
    elif cmd == "/streak":
        reply(build_streak_report())
    elif cmd == "/watch":
        reply(build_watch_recommendation())
    elif cmd == "/status":
        cmd_status()
    elif cmd in ("/start", "/help"):
        reply(HELP_TEXT)
    else:
        reply(f"Command gak dikenal: {cmd}\n\n{HELP_TEXT}")


def poll_loop():
    print("Bot polling aktif. Ctrl+C buat berhenti.")
    reply(f"🤖 Bot aktif.\n\n{HELP_TEXT}")
    offset = int(OFFSET_FILE.read_text()) if OFFSET_FILE.exists() else None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{API}/getUpdates", params=params, timeout=40)
            resp.raise_for_status()
            updates = resp.json().get("result", [])
        except requests.RequestException as e:
            print(f"[poll error] {e}")
            time.sleep(5)
            continue

        for u in updates:
            offset = u["update_id"] + 1
            OFFSET_FILE.write_text(str(offset))
            msg = u.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = msg.get("text", "")
            if not text:
                continue
            if chat_id != str(TELEGRAM_CHAT_ID):
                continue  # ponytail: cuma balesin chat_id yang di .env, siapapun lain diabaikan
            print(f"[command] {text}")
            try:
                handle_command(text)
            except Exception as e:
                reply(f"Error jalanin command: {e}")


if __name__ == "__main__":
    poll_loop()
