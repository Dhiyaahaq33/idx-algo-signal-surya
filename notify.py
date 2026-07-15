import html
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _fmt_mean_reversal(s):
    return f"• <b>{s['ticker']}</b> {s['last_price']} — {s['drop_pct']}% di bawah high {s['rolling_high']}"


def _fmt_universe(s):
    movers = ", ".join(f"{t} {v:+.1f}%" for t, v in s["movers"].items())
    return f"• <b>{s['ticker']}</b> ({s['group']}) diam {s['laggard_change_pct']:+.2f}% — grup gerak: {movers}"


def _fmt_sector_basket(s):
    return f"• <b>{s['ticker']}</b> {s['ticker_pct']:+.1f}% (sektor {s['sector']}, rata-rata +{s['sector_avg_pct']}%)"


def _fmt_ipo_momentum(s):
    return f"• <b>{s['ticker']}</b> {s['last_price']} — {s['pct_of_target']:+.1f}% dari harga akumulasi {s['accum_price']}"


def _fmt_broker_flow(s):
    code = s["ticker"].removeprefix("broker:")
    name = html.escape(s["broker_name"])
    return f"• <b>{code}</b> ({name}) — {s['today_value_bn']}M vs avg {s['avg_value_bn']}M ({s['multiple']}x)"


# urutan tampil + judul + formatter per algoritma
ALGO_SECTIONS = [
    ("mean_reversal", "🔁 Mean Reversal", _fmt_mean_reversal),
    ("universe", "👥 Pairs / Universe", _fmt_universe),
    ("sector_basket", "🧺 Golden Basket", _fmt_sector_basket),
    ("ipo_momentum", "🚀 Momentum IPO", _fmt_ipo_momentum),
    ("broker_flow", "🕵️ Broker Anomali (proxy Sun Reversal)", _fmt_broker_flow),
]


def format_message(signals, date_label=None):
    header = f"📊 <b>Sinyal Trading</b> — data per {html.escape(date_label)}" if date_label else "📊 <b>Sinyal Trading</b>"

    if not signals:
        return f"{header}\n\nGak ada sinyal."

    grouped = {}
    for s in signals:
        grouped.setdefault(s["algo"], []).append(s)

    lines = [f"{header} ({len(signals)} sinyal)"]
    for algo, title, fmt in ALGO_SECTIONS:
        if algo not in grouped:
            continue
        lines.append(f"\n<b>{html.escape(title)}</b>")
        for s in grouped[algo]:
            lines.append(fmt(s))
    return "\n".join(lines)


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify] TELEGRAM_BOT_TOKEN/CHAT_ID belum diset, print ke console aja:\n" + message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    resp.raise_for_status()
