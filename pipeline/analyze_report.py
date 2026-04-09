"""Post-analysis reporting: contact sheet + HTML dashboard for a single video.

Inputs: a directory that `analyze_video.py` wrote to (contains motion_table.json,
stills/, depths/).

Outputs:
  <dir>/contact_sheet.jpg         6-up JPG of the extracted stills
  <dir>/depth_sheet.jpg           6-up JPG of depth previews
  <dir>/report.html               Per-shot dashboard with confidence, motion, previews

Used by the batch runner to produce a browsable per-video summary.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np


THUMB_W = 360
THUMB_H = 640
MARGIN = 12
BG_COLOR = (24, 24, 24)


def _make_grid(image_paths: list[Path], thumb_w: int = THUMB_W,
               thumb_h: int = THUMB_H, cols: int = 3) -> np.ndarray:
    """Assemble images into a grid with padding + labels."""
    n = len(image_paths)
    if n == 0:
        return np.full((thumb_h, thumb_w, 3), BG_COLOR, dtype=np.uint8)
    rows = (n + cols - 1) // cols
    W = cols * thumb_w + (cols + 1) * MARGIN
    H = rows * thumb_h + (rows + 1) * MARGIN
    canvas = np.full((H, W, 3), BG_COLOR, dtype=np.uint8)
    for i, p in enumerate(image_paths):
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        # Letterbox thumbnail
        scale = min(thumb_w / w, thumb_h / h)
        tw, th = int(w * scale), int(h * scale)
        small = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
        thumb = np.full((thumb_h, thumb_w, 3), BG_COLOR, dtype=np.uint8)
        ox = (thumb_w - tw) // 2
        oy = (thumb_h - th) // 2
        thumb[oy:oy + th, ox:ox + tw] = small
        # Label
        cv2.putText(thumb, f"shot{i + 1}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        # Place into canvas
        r, c = divmod(i, cols)
        y = MARGIN + r * (thumb_h + MARGIN)
        x = MARGIN + c * (thumb_w + MARGIN)
        canvas[y:y + thumb_h, x:x + thumb_w] = thumb
    return canvas


def make_contact_sheets(work_dir: Path) -> None:
    stills = sorted(work_dir.glob("stills/shot*.jpg"))
    if stills:
        sheet = _make_grid(stills)
        cv2.imwrite(str(work_dir / "contact_sheet.jpg"), sheet,
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
    depths = sorted(work_dir.glob("depths/shot*_depth_preview.jpg"))
    if depths:
        sheet = _make_grid(depths)
        cv2.imwrite(str(work_dir / "depth_sheet.jpg"), sheet,
                    [cv2.IMWRITE_JPEG_QUALITY, 90])


def _conf_class(conf: float) -> tuple[str, str]:
    if conf >= 0.7:
        return "ok", "green"
    if conf >= 0.4:
        return "warn", "orange"
    return "bad", "red"


def write_html_report(work_dir: Path) -> None:
    """Build a self-contained per-video HTML dashboard."""
    mt_path = work_dir / "motion_table.json"
    if not mt_path.exists():
        return
    data = json.loads(mt_path.read_text())
    shots = data.get("shots", [])
    src = data.get("source_video", "?")
    bpm_line = f"{data.get('source_resolution', '?')} @ {data.get('source_fps', '?')}fps, {data.get('source_duration', '?')}s"

    rows: list[str] = []
    for s in shots:
        i = int(s["id"])
        m = s.get("motion", {})
        conf = float(s.get("_flow_confidence", 0.0))
        cls, color = _conf_class(conf)
        rows.append(f"""
        <tr class="{cls}">
          <td class="idx">{i}</td>
          <td class="thumb"><img src="stills/shot{i}.jpg"></td>
          <td class="depth"><img src="depths/shot{i}_depth_preview.jpg"></td>
          <td class="time">{s['start']:.2f} – {s['end']:.2f}<br><small>{s['duration']:.2f}s / {s['frame_count']}f</small></td>
          <td class="motion">
            <div>tx {m.get('tx_px_1080', 0):+.1f}</div>
            <div>ty {m.get('ty_px_1080', 0):+.1f}</div>
            <div>z {m.get('zoom_start', 1):.3f} → {m.get('zoom_end', 1):.3f}</div>
            <small>{m.get('type', '?')}</small>
          </td>
          <td class="conf"><span style="color:{color}">●</span> {conf:.2f}</td>
        </tr>""")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{Path(src).name} — analyze report</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; padding: 24px; background: #111; color: #eee;
          font-family: -apple-system, system-ui, sans-serif; font-size: 14px; }}
  h1 {{ font-size: 18px; margin: 0 0 4px 0; }}
  .meta {{ color: #888; margin-bottom: 24px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 10px; text-align: left; vertical-align: top;
            border-bottom: 1px solid #222; }}
  th {{ color: #888; font-weight: 500; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.05em; }}
  tr.bad td.conf {{ background: rgba(255, 80, 80, 0.12); }}
  tr.warn td.conf {{ background: rgba(255, 180, 60, 0.12); }}
  tr.ok td.conf {{ background: rgba(80, 200, 120, 0.12); }}
  img {{ width: 120px; height: auto; display: block;
         border-radius: 4px; background: #000; }}
  .motion {{ font-family: ui-monospace, monospace; font-size: 12px; line-height: 1.6; }}
  .motion small {{ color: #888; font-size: 10px; }}
  .idx {{ font-weight: 600; color: #888; }}
  .conf {{ font-weight: 600; }}
  .sheet {{ margin: 16px 0; }}
  .sheet img {{ width: 100%; max-width: 1080px; border-radius: 8px; }}
  h2 {{ font-size: 14px; margin-top: 32px; color: #aaa; font-weight: 500; }}
</style>
</head>
<body>
  <h1>{Path(src).name}</h1>
  <div class="meta">{bpm_line} · {len(shots)} shots</div>

  <table>
    <tr>
      <th>#</th><th>still</th><th>depth</th><th>time</th><th>motion</th><th>conf</th>
    </tr>
    {''.join(rows)}
  </table>

  <h2>Contact sheet</h2>
  <div class="sheet"><img src="contact_sheet.jpg"></div>

  <h2>Depth sheet</h2>
  <div class="sheet"><img src="depth_sheet.jpg"></div>
</body>
</html>
"""
    (work_dir / "report.html").write_text(html)


def build(work_dir: str) -> None:
    p = Path(work_dir)
    if not (p / "motion_table.json").exists():
        print(f"ERROR: {work_dir} has no motion_table.json — run analyze_video.py first")
        return
    make_contact_sheets(p)
    write_html_report(p)
    print(f"  -> {p}/report.html")
    print(f"  -> {p}/contact_sheet.jpg")
    print(f"  -> {p}/depth_sheet.jpg")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze_report.py <work_dir>")
        sys.exit(1)
    build(sys.argv[1])
