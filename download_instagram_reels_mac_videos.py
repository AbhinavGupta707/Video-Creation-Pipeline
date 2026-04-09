#!/usr/bin/env python3
"""
Batch-download Instagram reels from a CSV using yt-dlp on macOS.

Default CSV path:
  ~/Desktop/instagram/updated.csv

Default output folder:
  ~/Downloads/instagram

Expected CSV columns:
- reel title
- url

Examples:
  python3 download_instagram_reels_mac.py

  python3 download_instagram_reels_mac.py \
      --browser safari

  python3 download_instagram_reels_mac.py \
      --output-dir ~/Desktop/instagram/downloads

  python3 download_instagram_reels_mac.py \
      --cookies-file ~/Desktop/instagram/cookies.txt
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_CSV_PATH = Path.home() / "Desktop" / "instagram" / "updated.csv"
DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "instagram" / "videos"
REPORT_FILENAME = "download_report.csv"
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'


def normalize_colname(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


TITLE_CANDIDATES = [
    "reel title",
    "reel_title",
    "title",
    "name",
]

URL_CANDIDATES = [
    "url",
    "reel url",
    "reel_url",
    "link",
]


def pick_column(fieldnames: Iterable[str], candidates: List[str]) -> Optional[str]:
    normalized_map = {normalize_colname(name): name for name in fieldnames}
    for candidate in candidates:
        if candidate in normalized_map:
            return normalized_map[candidate]
    return None



def sanitize_filename(value: str, max_length: int = 140) -> str:
    value = value.strip()
    value = re.sub(INVALID_FILENAME_CHARS, "", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    if not value:
        value = "untitled_reel"
    if len(value) > max_length:
        value = value[:max_length].rstrip(" .")
    return value



def make_unique_basenames(titles: List[str]) -> List[str]:
    counts = Counter(titles)
    seen: Counter[str] = Counter()
    unique_names: List[str] = []

    for title in titles:
        seen[title] += 1
        if counts[title] == 1:
            unique_names.append(title)
        else:
            unique_names.append(f"{title} ({seen[title]})")
    return unique_names



def load_rows(csv_path: Path) -> Tuple[List[Dict[str, str]], str, str]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")

        title_col = pick_column(reader.fieldnames, TITLE_CANDIDATES)
        url_col = pick_column(reader.fieldnames, URL_CANDIDATES)

        if not title_col:
            raise ValueError(
                f"Could not find a title column. Expected one of: {', '.join(TITLE_CANDIDATES)}"
            )
        if not url_col:
            raise ValueError(
                f"Could not find a URL column. Expected one of: {', '.join(URL_CANDIDATES)}"
            )

        rows = list(reader)
        return rows, title_col, url_col



def find_existing_download(output_dir: Path, base_name: str) -> Optional[Path]:
    matches = sorted(output_dir.glob(f"{base_name}.*"))
    for match in matches:
        if match.is_file() and match.name != REPORT_FILENAME:
            return match
    return None



def build_command(
    yt_dlp_path: str,
    output_dir: Path,
    base_name: str,
    url: str,
    browser: Optional[str],
    cookies_file: Optional[Path],
    ffmpeg_location: Optional[str],
) -> List[str]:
    cmd = [
        yt_dlp_path,
        "--no-overwrites",
        "--no-part",
        "--paths",
        str(output_dir),
        "--output",
        f"{base_name}.%(ext)s",
    ]

    if ffmpeg_location:
        cmd.extend(["--ffmpeg-location", ffmpeg_location])

    if browser:
        cmd.extend(["--cookies-from-browser", browser])

    if cookies_file:
        cmd.extend(["--cookies", str(cookies_file)])

    cmd.append(url)
    return cmd



def write_report(report_path: Path, rows: List[Dict[str, str]]) -> None:
    fieldnames = [
        "row_number",
        "status",
        "reel_title",
        "url",
        "filename_base",
        "saved_file",
        "message",
    ]
    with report_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)



def main() -> int:
    parser = argparse.ArgumentParser(description="Download Instagram reels from a CSV using yt-dlp on macOS")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=str(DEFAULT_CSV_PATH),
        help="Path to the cleaned CSV file",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder where videos should be saved (default: ~/Desktop/instagram/videos)",
    )
    parser.add_argument(
        "--yt-dlp-path",
        default="yt-dlp",
        help="Path to the yt-dlp executable if it is not already on PATH",
    )
    parser.add_argument(
        "--browser",
        choices=["brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi", "whale"],
        help="Read cookies directly from a logged-in browser if Instagram blocks public access",
    )
    parser.add_argument(
        "--cookies-file",
        help="Path to a Netscape/Mozilla cookies.txt file",
    )
    parser.add_argument(
        "--ffmpeg-location",
        help="Optional path to ffmpeg or the directory containing it",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.5,
        help="Pause between downloads to reduce rate-limiting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually running yt-dlp",
    )

    args = parser.parse_args()

    csv_path = Path(os.path.expandvars(os.path.expanduser(args.csv_path))).resolve()
    output_dir = Path(os.path.expandvars(os.path.expanduser(args.output_dir))).resolve()
    cookies_file = (
        Path(os.path.expandvars(os.path.expanduser(args.cookies_file))).resolve()
        if args.cookies_file
        else None
    )

    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        print("Expected default macOS path: ~/Desktop/instagram/updated.csv", file=sys.stderr)
        return 1

    if not args.dry_run and shutil.which(args.yt_dlp_path) is None and not Path(args.yt_dlp_path).exists():
        print(
            "ERROR: yt-dlp was not found. On Mac, install it with: brew install yt-dlp",
            file=sys.stderr,
        )
        return 1

    if cookies_file and not cookies_file.exists():
        print(f"ERROR: cookies file not found: {cookies_file}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        rows, title_col, url_col = load_rows(csv_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    clean_titles: List[str] = []
    prepared_rows: List[Tuple[int, str, str]] = []
    for idx, row in enumerate(rows, start=1):
        raw_title = (row.get(title_col) or "").strip()
        raw_url = (row.get(url_col) or "").strip()

        title = sanitize_filename(raw_title or f"reel_{idx:03d}")
        clean_titles.append(title)
        prepared_rows.append((idx, title, raw_url))

    unique_bases = make_unique_basenames(clean_titles)

    report_rows: List[Dict[str, str]] = []
    total = len(prepared_rows)

    for position, ((row_number, title, url), base_name) in enumerate(zip(prepared_rows, unique_bases), start=1):
        if not url:
            report_rows.append(
                {
                    "row_number": str(row_number),
                    "status": "skipped",
                    "reel_title": title,
                    "url": "",
                    "filename_base": base_name,
                    "saved_file": "",
                    "message": "Missing URL",
                }
            )
            print(f"[{position}/{total}] SKIP  row {row_number}: missing URL")
            continue

        existing_file = find_existing_download(output_dir, base_name)
        if existing_file:
            report_rows.append(
                {
                    "row_number": str(row_number),
                    "status": "already_exists",
                    "reel_title": title,
                    "url": url,
                    "filename_base": base_name,
                    "saved_file": str(existing_file),
                    "message": "File already exists",
                }
            )
            print(f"[{position}/{total}] EXISTS {existing_file.name}")
            continue

        cmd = build_command(
            yt_dlp_path=args.yt_dlp_path,
            output_dir=output_dir,
            base_name=base_name,
            url=url,
            browser=args.browser,
            cookies_file=cookies_file,
            ffmpeg_location=args.ffmpeg_location,
        )

        if args.dry_run:
            print(f"[{position}/{total}] DRYRUN {' '.join(cmd)}")
            report_rows.append(
                {
                    "row_number": str(row_number),
                    "status": "dry_run",
                    "reel_title": title,
                    "url": url,
                    "filename_base": base_name,
                    "saved_file": "",
                    "message": "Command prepared but not executed",
                }
            )
            continue

        print(f"[{position}/{total}] DOWNLOADING {base_name}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        downloaded_file = find_existing_download(output_dir, base_name)
        if result.returncode == 0 and downloaded_file:
            report_rows.append(
                {
                    "row_number": str(row_number),
                    "status": "downloaded",
                    "reel_title": title,
                    "url": url,
                    "filename_base": base_name,
                    "saved_file": str(downloaded_file),
                    "message": "OK",
                }
            )
            print(f"[{position}/{total}] DONE  {downloaded_file.name}")
        else:
            error_message = (result.stderr or result.stdout or "Unknown yt-dlp error").strip()
            error_message = error_message.replace("\n", " | ")[:500]
            report_rows.append(
                {
                    "row_number": str(row_number),
                    "status": "failed",
                    "reel_title": title,
                    "url": url,
                    "filename_base": base_name,
                    "saved_file": str(downloaded_file) if downloaded_file else "",
                    "message": error_message,
                }
            )
            print(f"[{position}/{total}] FAIL  {base_name}")
            print(f"           {error_message}")

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    report_path = output_dir / REPORT_FILENAME
    write_report(report_path, report_rows)

    downloaded = sum(1 for r in report_rows if r["status"] == "downloaded")
    skipped = sum(1 for r in report_rows if r["status"] in {"skipped", "already_exists"})
    failed = sum(1 for r in report_rows if r["status"] == "failed")

    print("\nFinished")
    print(f"Downloaded: {downloaded}")
    print(f"Skipped/already existed: {skipped}")
    print(f"Failed: {failed}")
    print(f"Report: {report_path}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
