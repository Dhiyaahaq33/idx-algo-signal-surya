"""Dump the full "Signals" sheet to dashboard/data.json, committed to the repo.

Runs in GitHub Actions (which has real internet + GOOGLE_SHEETS_CREDENTIALS_JSON)
right after main.py pushes the day's signals. The scheduled cloud routine that
rebuilds the web dashboard has a locked-down egress proxy that cannot reach
docs.google.com/sheets.googleapis.com directly - so instead of fetching the
sheet live, it just reads this file out of its own git checkout.
"""
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(HERE))

from sheets_export import _get_client


def main():
    client, sheet_id = _get_client()
    if client is None:
        print("GOOGLE_SHEETS_CREDENTIALS_JSON/GOOGLE_SHEET_ID belum diset, skip export")
        return

    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet("Signals")
    values = worksheet.get_all_values()
    if not values:
        print("Sheet kosong, skip export")
        return

    header, rows = values[0], values[1:]
    data = [dict(zip(header, row)) for row in rows]

    out_path = os.path.join(HERE, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"exported {len(data)} rows to {out_path}")


if __name__ == "__main__":
    main()
