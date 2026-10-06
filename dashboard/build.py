"""Regenerate dashboard/output.html from dashboard/data.json.

data.json is committed to the repo by export_data.py (run in GitHub Actions,
which has real internet access) - this script itself does NO network calls,
so it works even in a locked-down sandbox (e.g. the scheduled cloud routine
that rebuilds the published dashboard, whose egress proxy can't reach Google).
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--generated-at", required=True, help="Timestamp string to display in the footer, e.g. '2026-08-17 16:35 WIB'")
    return p.parse_args()


def main():
    args = parse_args()

    data_path = HERE / "data.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))
    print(f"read {len(rows)} rows from {data_path}")

    template = (HERE / "template.html").read_text(encoding="utf-8")
    output = template.replace("/*__DATA__*/", json.dumps(rows, ensure_ascii=False))
    output = output.replace("/*__GENERATED_AT__*/", json.dumps(args.generated_at))

    out_path = HERE / "output.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"wrote {out_path} ({len(output)} bytes)")


if __name__ == "__main__":
    main()
