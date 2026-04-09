#!/usr/bin/env bash
# One-command wrapper: take a reference video, analyze + depth + render a B_default variant.
#
# Usage:
#   ./pipeline/analyze_and_render.sh <video> [out_dir]
#
# The result is written to <out_dir>/renders/B_default.mp4, with a full
# per-shot HTML dashboard at <out_dir>/report.html.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  sed -n '2,/^set -euo/p' "$0" | sed 's/^# \?//'
  exit 1
fi

VIDEO=$1
VIDEO_STEM=$(basename "$VIDEO" | sed 's/\.[^.]*$//')
SLUG=$(echo "$VIDEO_STEM" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')
OUT_DIR=${2:-"pipeline/$SLUG"}

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$PROJECT_DIR/.venv/bin/python"

echo "[1/5] Analyzing $VIDEO..."
"$PY" "$PROJECT_DIR/pipeline/analyze_video.py" "$VIDEO" "$OUT_DIR"

echo ""
echo "[2/5] Computing depth maps..."
"$PY" "$PROJECT_DIR/pipeline/compute_depth.py" "$OUT_DIR/stills" "$OUT_DIR/depths" 2>&1 | tail -10

echo ""
echo "[3/5] Generating starter per_shot_config.json..."
"$PY" "$PROJECT_DIR/pipeline/generate_per_shot_config.py" "$OUT_DIR"

echo ""
echo "[4/5] Building HTML report + contact sheets..."
"$PY" "$PROJECT_DIR/pipeline/analyze_report.py" "$OUT_DIR"

echo ""
echo "[5/5] Rendering B_default.mp4 (parallax 2.5, clean filters)..."
mkdir -p "$OUT_DIR/renders" "$OUT_DIR/stills_prepped" "$OUT_DIR/_render_work"
FFMPEG="${FFMPEG:-/opt/homebrew/bin/ffmpeg}"
for STILL in "$OUT_DIR"/stills/shot*.jpg; do
  NAME=$(basename "$STILL")
  $FFMPEG -y -i "$STILL" \
    -vf "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840" \
    -q:v 2 "$OUT_DIR/stills_prepped/$NAME" -hide_banner -loglevel error
done
"$PY" "$PROJECT_DIR/pipeline/render_v2.py" all \
  "$OUT_DIR/stills_prepped" "$OUT_DIR/depths" "$OUT_DIR/_render_work" \
  "$OUT_DIR/renders/B_default.mp4" \
  --motion-table "$OUT_DIR/motion_table.json" \
  --config "$OUT_DIR/per_shot_config.json" \
  --depth-intensity 2.5 --crf 22 2>&1 | tail -5

echo ""
echo "============================================================"
echo "DONE"
echo "============================================================"
echo "  Report:  $OUT_DIR/report.html"
echo "  Render:  $OUT_DIR/renders/B_default.mp4"
echo "  Config:  $OUT_DIR/per_shot_config.json"
