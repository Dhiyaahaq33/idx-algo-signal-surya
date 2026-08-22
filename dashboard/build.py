"""Regenerate dashboard/output.html from the live "Signals" Google Sheet.

Reads the sheet via its public read-only CSV export (no credentials needed -
the sheet's "Signals" tab is shared as "anyone with the link, viewer"), splices
the data into template.html, and writes output.html ready to publish as an
Artifact. Timestamp is passed in via --generated-at (Date.now()/datetime.now()
are unreliable in some sandboxed run contexts, so the caller supplies it).
"""
import argparse
import csv
import io
import json
import urllib.request
from pathlib import Path

SHEET_ID = "1GMqmLn673TzFLC0qAUVYZCGcD3HmAu3wpIWInDEr7rY"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Signals"

HERE = Path(__file__).parent


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--generated-at", required=True, help="Timestamp string to display in the footer, e.g. '2026-08-17 16:35 WIB'")
    return p.parse_args()


def main():
    args = parse_args()

    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8")

    rows = list(csv.DictReader(io.StringIO(content)))
    print(f"fetched {len(rows)} rows from sheet")

    template = (HERE / "template.html").read_text(encoding="utf-8")
    output = template.replace("/*__DATA__*/", json.dumps(rows, ensure_ascii=False))
    output = output.replace("/*__GENERATED_AT__*/", json.dumps(args.generated_at))

    out_path = HERE / "output.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote {out_path} ({len(output)} bytes)")


if __name__ == "__main__":
    main()
