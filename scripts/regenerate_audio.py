#!/usr/bin/env python3
"""
Regenerate the pronunciation audio in this repo with your own Azure Speech account.

Reads words.csv (columns: id, hanzi, pinyin, audio) and writes one MP3 per row to
the path in the `audio` column. Files that already exist are skipped, so an
interrupted run resumes where it stopped.

Single characters are synthesized using the row's pinyin, so characters with
several readings (行, 长, 了) sound right. Words are sent as plain text, which
Azure reads correctly in context.

Setup:
  pip install -r requirements.txt
  export AZURE_SPEECH_KEY=...        # Azure portal > Speech resource > Keys
  export AZURE_SPEECH_REGION=eastus  # your resource's region

Usage:
  python scripts/regenerate_audio.py --dry-run          # count characters, no calls
  python scripts/regenerate_audio.py --limit 20         # trial run
  python scripts/regenerate_audio.py                    # everything missing
  python scripts/regenerate_audio.py --force            # overwrite existing files
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape

try:
    import requests
except ImportError:
    sys.exit("pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
VOICE = "zh-CN-XiaoxiaoNeural"
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"

TONE_MARKS = {
    "ā": ("a", 1), "á": ("a", 2), "ǎ": ("a", 3), "à": ("a", 4),
    "ē": ("e", 1), "é": ("e", 2), "ě": ("e", 3), "è": ("e", 4),
    "ī": ("i", 1), "í": ("i", 2), "ǐ": ("i", 3), "ì": ("i", 4),
    "ō": ("o", 1), "ó": ("o", 2), "ǒ": ("o", 3), "ò": ("o", 4),
    "ū": ("u", 1), "ú": ("u", 2), "ǔ": ("u", 3), "ù": ("u", 4),
    "ǖ": ("v", 1), "ǘ": ("v", 2), "ǚ": ("v", 3), "ǜ": ("v", 4),
}


def sapi_from_pinyin(pinyin):
    """'chén' -> 'chen 2'. Picks the first reading that carries a tone mark."""
    for reading in re.split(r"[,/;]", pinyin or ""):
        reading = unicodedata.normalize("NFC", reading.strip().lower())
        if not re.fullmatch(r"[a-zü" + "".join(TONE_MARKS) + r"]+", reading):
            continue
        tone, out = None, []
        for ch in reading:
            if ch in TONE_MARKS:
                base, tone = TONE_MARKS[ch]
                out.append(base)
            else:
                out.append("v" if ch == "ü" else ch)
        if tone:
            return f"{''.join(out)} {tone}"
    return None


def build_ssml(hanzi, pinyin, is_single_char):
    ph = sapi_from_pinyin(pinyin) if is_single_char else None
    body = (f'<phoneme alphabet="sapi" ph="{ph}">{escape(hanzi)}</phoneme>'
            if ph else escape(hanzi))
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
            f'<voice name="{VOICE}">{body}</voice></speak>')


def synthesize(session, region, key, ssml):
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
        "User-Agent": "mandarin-hsk3-audio-regen",
    }
    for attempt in range(5):
        r = session.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=30)
        if r.status_code == 200 and r.content:
            return r.content
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"Azure TTS {r.status_code}: {r.text[:200]}")
    raise RuntimeError("Azure TTS kept failing (rate limit?)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "words.csv"), help="path to words.csv")
    ap.add_argument("--limit", type=int, help="only the first N rows (for a trial)")
    ap.add_argument("--dry-run", action="store_true", help="count characters, call nothing")
    ap.add_argument("--force", action="store_true", help="overwrite files that already exist")
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]
    todo = [r for r in rows if args.force or not (ROOT / r["audio"]).exists()]
    chars = sum(len(r["hanzi"]) for r in todo)
    print(f"{len(rows):,} rows, {len(todo):,} to synthesize ({chars:,} characters)")
    if args.dry_run or not todo:
        return

    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        sys.exit("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")

    session = requests.Session()
    done = failed = 0
    for i, row in enumerate(todo, 1):
        out = ROOT / row["audio"]
        try:
            ssml = build_ssml(row["hanzi"], row["pinyin"], len(row["hanzi"]) == 1)
            try:
                audio = synthesize(session, region, key, ssml)
            except RuntimeError:
                # Azure rejected the pinyin hint (e.g. lüè): read the plain character instead.
                audio = synthesize(session, region, key, build_ssml(row["hanzi"], None, False))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(audio)
            done += 1
            time.sleep(0.05)
        except Exception as e:  # keep going; rerun resumes
            failed += 1
            print(f"  failed: {row['hanzi']} ({row['id']}): {e}")
        if i % 200 == 0:
            print(f"  {i:,}/{len(todo):,}")
    print(f"{done:,} done, {failed:,} failed. Rerun the same command to retry failures.")


if __name__ == "__main__":
    main()
