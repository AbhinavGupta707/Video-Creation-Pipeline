#!/usr/bin/env bash
# Test the recipes on the ORIGINAL wine ferrari video.
# Extracts the first frame of each shot, upscales 720x1280 → 2160x3840,
# applies the recipe, concats them, and produces test_output.mp4.
#
# This validates that the motion recipes match the original WITHOUT
# spending AI credits. The upscaled stills will be soft (since source is
# only 720w), but the MOTION direction/magnitude/pacing should match
# the original video closely.

set -euo pipefail

PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$PIPELINE_DIR")"
FFMPEG="${FFMPEG:-/opt/homebrew/bin/ffmpeg}"
SOURCE="$PROJECT_DIR/videos/wine ferrari.mp4"
STILLS_DIR="$PIPELINE_DIR/test_stills"
OUT_DIR="$PIPELINE_DIR/test_clips"
FINAL="$PIPELINE_DIR/test_output.mp4"

# Shot start times (just after cut to skip compression artifacts)
SHOT_TIMES=(0.10 2.36 4.62 6.80 8.98 9.88 11.04 12.10)

mkdir -p "$STILLS_DIR" "$OUT_DIR"

echo "Step 1: extracting first frame of each shot, upscaling to 4K..."
for i in 1 2 3 4 5 6 7 8; do
  IDX=$((i-1))
  T=${SHOT_TIMES[$IDX]}
  $FFMPEG -y -ss "$T" -i "$SOURCE" -frames:v 1 -vf "scale=2160:3840:flags=lanczos" -pix_fmt yuvj420p -q:v 2 "$STILLS_DIR/shot${i}.jpg" -hide_banner -loglevel error
  echo "  shot${i}.jpg extracted at t=${T}s"
done

echo ""
echo "Step 2: building 8 zoompan clips using recipes..."
"$PIPELINE_DIR/recipes.sh" build_all "$STILLS_DIR" "$OUT_DIR" 2>&1 | grep -v "^$" | tail -20

echo ""
echo "Step 3: concatenating clips into final test video..."
"$PIPELINE_DIR/recipes.sh" concat "$OUT_DIR" "$FINAL"

echo ""
echo "============================================================"
echo "TEST COMPLETE"
echo "============================================================"
echo "Original: $SOURCE"
echo "Test:     $FINAL"
echo ""
echo "Open both side by side in QuickTime to compare motion."
echo "The test will be SOFTER (upscaled from 720p) but the motion"
echo "direction and pacing should match the original closely."
