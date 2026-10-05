#!/usr/bin/env python3
"""
Maintainer-only helper: export words.csv from the source database.
Not needed to use or regenerate the audio.

  pip install supabase
  export SUPABASE_URL=...
  export SUPABASE_SERVICE_ROLE_KEY=...
  python scripts/export_words.py
"""
import csv
import os
import sys
from pathlib import Path

from supabase import create_client

url = os.environ.get("SUPABASE_URL", "").strip()
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
if not url or not key:
    sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

sb = create_client(url, key)
rows, offset = [], 0
while True:
    page = (sb.table("characters").select("id,hanzi,pinyin").order("id")
            .range(offset, offset + 999).execute().data or [])
    rows += page
    if len(page) < 1000:
        break
    offset += 1000

out = Path(__file__).resolve().parent.parent / "words.csv"
with open(out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "hanzi", "pinyin", "audio"])
    for r in rows:
        w.writerow([r["id"], r["hanzi"], r["pinyin"] or "", f"audio/{r['id']}.mp3"])
print(f"Wrote {len(rows):,} rows to {out}")
