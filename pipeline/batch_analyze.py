"""Batch-analyze every video in a directory.

For each .mp4 found, runs analyze_video + compute_depth + analyze_report +
generate_per_shot_config, producing a self-contained working directory per
video. Builds a top-level index.html linking to every per-video report.

Usage:
  python batch_analyze.py <videos_dir> <out_dir> [--skip-depth] [--limit N]

  --skip-depth   Skip Depth Anything v2 (faster, but no parallax possible)
  --limit N      Only process the first N videos (for smoke testing)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from pathlib import Path

from pipeline import analyze_report, analyze_video, generate_per_shot_config


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return SLUG_RE.sub("_", name.lower()).strip("_")


def compute_depth_for(work_dir: Path) -> bool:
    """Call compute_depth.py as a subprocess to keep model-loading isolated."""
    import subprocess
    stills = work_dir / "stills"
    depths = work_dir / "depths"
    if not stills.exists():
        return False
    depths.mkdir(exist_ok=True)
    # Skip if already done
    expected = len(list(stills.glob("shot*.jpg")))
    existing = len(list(depths.glob("shot*_depth.npy")))
    if existing >= expected and expected > 0:
        print(f"    depth cached ({existing} maps)")
        return True
    proj_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [str(proj_dir / ".venv" / "bin" / "python"),
         str(proj_dir / "pipeline" / "compute_depth.py"),
         str(stills), str(depths)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"    depth FAILED: {result.stderr[-200:]}")
        return False
    return True


def process_video(video_path: Path, out_dir: Path, skip_depth: bool) -> dict:
    """Analyze + depth + report + per-shot config for one video."""
    slug = slugify(video_path.stem)
    work = out_dir / slug
    started = time.time()
    result = {
        "video": video_path.name,
        "slug": slug,
        "path": str(video_path),
        "work_dir": str(work),
        "success": False,
        "n_shots": 0,
        "duration_s": 0,
        "confidence": {"ok": 0, "warn": 0, "bad": 0},
        "error": None,
        "elapsed_s": 0.0,
    }
    try:
        print(f"\n[{video_path.name}]")
        # 1. Analyze (scene detection + motion + stills + motion_table)
        table = analyze_video.analyze(str(video_path), str(work))
        result["n_shots"] = len(table.get("shots", []))
        result["duration_s"] = float(table.get("source_duration", 0))
        # 2. Depth
        if not skip_depth:
            compute_depth_for(work)
        # 3. Per-shot config scaffolding
        generate_per_shot_config.generate(str(work))
        # 4. Contact sheet + HTML report
        analyze_report.build(str(work))
        # 5. Tally confidence
        for s in table.get("shots", []):
            c = float(s.get("_flow_confidence", 0))
            if c >= 0.7:
                result["confidence"]["ok"] += 1
            elif c >= 0.4:
                result["confidence"]["warn"] += 1
            else:
                result["confidence"]["bad"] += 1
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
        traceback.print_exc()
    result["elapsed_s"] = round(time.time() - started, 1)
    return result


def write_index(out_dir: Path, results: list[dict]) -> None:
    rows: list[str] = []
    for r in sorted(results, key=lambda x: x["video"]):
        ok = r["confidence"]["ok"]
        warn = r["confidence"]["warn"]
        bad = r["confidence"]["bad"]
        status = "✓" if r["success"] and bad == 0 else ("⚠" if r["success"] else "✗")
        color = "#5c9" if (r["success"] and bad == 0) else ("#e90" if r["success"] else "#e55")
        thumb_path = f'{r["slug"]}/contact_sheet.jpg'
        report_link = f'{r["slug"]}/report.html'
        rows.append(f"""
        <tr>
          <td class="status" style="color:{color}">{status}</td>
          <td class="name"><a href="{report_link}">{r['video']}</a></td>
          <td class="shots">{r['n_shots']}</td>
          <td class="dur">{r['duration_s']:.1f}s</td>
          <td class="conf">
            <span style="color:#5c9">{ok}</span> /
            <span style="color:#e90">{warn}</span> /
            <span style="color:#e55">{bad}</span>
          </td>
          <td class="elapsed">{r['elapsed_s']:.1f}s</td>
        </tr>""")

    ok_count = sum(1 for r in results if r["success"])
    total = len(results)

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Batch analyze report</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; padding: 24px; background: #111; color: #eee;
          font-family: -apple-system, system-ui, sans-serif; font-size: 14px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px 0; }}
  .meta {{ color: #888; margin-bottom: 24px; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 960px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #222; }}
  th {{ color: #888; font-weight: 500; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.05em; }}
  td.status {{ font-size: 18px; width: 24px; text-align: center; }}
  td.name a {{ color: #8cf; text-decoration: none; }}
  td.name a:hover {{ text-decoration: underline; }}
  td.shots, td.dur, td.elapsed {{ color: #aaa; font-variant-numeric: tabular-nums; }}
  td.conf {{ font-family: ui-monospace, monospace; font-size: 12px; }}
</style>
</head>
<body>
  <h1>Batch analyze — {ok_count}/{total} videos processed</h1>
  <div class="meta">Confidence columns: ok / warn / bad shots per video</div>
  <table>
    <tr>
      <th></th><th>Video</th><th>Shots</th><th>Duration</th>
      <th>Confidence</th><th>Time</th>
    </tr>
    {''.join(rows)}
  </table>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html)
    print(f"\nIndex -> {out_dir}/index.html")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("videos_dir")
    p.add_argument("out_dir")
    p.add_argument("--skip-depth", action="store_true",
                   help="Skip Depth Anything v2 (faster but no parallax)")
    p.add_argument("--limit", type=int, default=0,
                   help="Only process first N videos (smoke test)")
    p.add_argument("--pattern", default="*.mp4",
                   help="Glob pattern for videos (default: *.mp4)")
    args = p.parse_args()

    videos_dir = Path(args.videos_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(videos_dir.glob(args.pattern))
    if args.limit:
        videos = videos[: args.limit]
    print(f"Batch processing {len(videos)} videos -> {out_dir}")

    results: list[dict] = []
    for v in videos:
        results.append(process_video(v, out_dir, args.skip_depth))
        write_index(out_dir, results)  # rewrite after each so partial progress is visible

    (out_dir / "results.json").write_text(json.dumps(results, indent=2))

    # Final summary
    ok = sum(1 for r in results if r["success"])
    total_shots = sum(r["n_shots"] for r in results)
    total_bad = sum(r["confidence"]["bad"] for r in results)
    print(f"\nDONE: {ok}/{len(results)} videos, {total_shots} total shots, "
          f"{total_bad} low-confidence shots needing review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
