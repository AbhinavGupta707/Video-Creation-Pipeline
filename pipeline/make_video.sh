#!/usr/bin/env bash
# Production: take a directory of 8 AI-generated stills and produce a final 1080x1920 24fps video.
#
# Uses render_v2.py — sub-pixel renderer with PERSPECTIVE-CORRECT inverse-depth
# parallax (true 3D feel from a 2D still) and clean default filters.
# Auto-computes depth maps with Depth Anything v2 Large if not present.
#
# Usage:
#   ./make_video.sh <stills_dir> <output.mp4> [options]
#
# OPTIONS
#   --scale N             Motion magnitude multiplier (default 1.0)
#                            1.0 = matches wine ferrari original
#                            1.5 = 50% more dramatic
#                            2.0 = double cinematic
#   --depth-intensity N   Perspective parallax strength (default 2.5)
#                            1.0 = flat (no parallax)
#                            2.0 = subtle 3D
#                            2.5 = visible 3D (default)
#                            4.0 = strong 3D
#                            6.0 = dramatic
#   --crf N               Quality (default 22)
#                            18 = master/archive (~130MB with grain, ~5MB without)
#                            20 = high
#                            22 = delivery (default)
#                            24 = social/small
#   --grade               Add cinematic teal-orange color grade (off by default)
#   --vignette            Add corner vignette (off by default)
#   --grain               Add film grain (off by default — adds 50-100MB to file)
#   --cinematic           Enable all stylized filters (grade + vignette + grain)
#   --no-parallax         Disable depth parallax (uniform shift, faster)
#   --legacy              Use old ffmpeg zoompan recipes
#
# DEFAULTS produce a CLEAN STUDIO LOOK matching the wine ferrari original:
#   - Inverse-depth parallax at intensity 2.5
#   - Sub-pixel sub-frame motion with smoothstep easing
#   - Bloom on highlights + slight unsharp mask
#   - NO grain, NO color grade, NO vignette
#
# EXAMPLES
#   ./make_video.sh ai_stills/ output.mp4
#   ./make_video.sh ai_stills/ dramatic.mp4 --scale 1.5 --depth-intensity 4
#   ./make_video.sh ai_stills/ cinematic.mp4 --cinematic
#   ./make_video.sh ai_stills/ social.mp4 --crf 24

set -euo pipefail

if [[ $# -lt 2 ]]; then
  sed -n '2,/^set -euo/p' "$0" | sed 's/^# \?//'
  exit 1
fi

STILLS_IN=$1
OUTPUT=$2
shift 2

SCALE=1.0
CRF=22
DEPTH_INTENSITY=2.5
PIPELINE_DIR_BOOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$PIPELINE_DIR_BOOT/per_shot_config.json"
MOTION_TABLE="$PIPELINE_DIR_BOOT/motion_table.json"
EXTRA_FLAGS=""
USE_LEGACY=false
AUDIO=""
BPM_OVERRIDE=""
DROP_AT=""
DROP_SHOT="7"
GRANULARITY="half_bar"

while [[ $# -gt 0 ]]; do
  case $1 in
    --scale)            SCALE=$2; shift 2 ;;
    --depth-intensity)  DEPTH_INTENSITY=$2; shift 2 ;;
    --crf)              CRF=$2; shift 2 ;;
    --config)           CONFIG=$2; shift 2 ;;
    --no-config)        CONFIG=""; shift ;;
    --motion-table)     MOTION_TABLE=$2; shift 2 ;;
    --no-parallax)      EXTRA_FLAGS="$EXTRA_FLAGS --no-parallax"; shift ;;
    --grade)            EXTRA_FLAGS="$EXTRA_FLAGS --grade"; shift ;;
    --vignette)         EXTRA_FLAGS="$EXTRA_FLAGS --vignette"; shift ;;
    --grain)            EXTRA_FLAGS="$EXTRA_FLAGS --grain"; shift ;;
    --cinematic)        EXTRA_FLAGS="$EXTRA_FLAGS --cinematic"; shift ;;
    --legacy)           USE_LEGACY=true; shift ;;
    --audio)            AUDIO=$2; shift 2 ;;
    --bpm-override)     BPM_OVERRIDE=$2; shift 2 ;;
    --drop-at)          DROP_AT=$2; shift 2 ;;
    --drop-shot)        DROP_SHOT=$2; shift 2 ;;
    --granularity)      GRANULARITY=$2; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -n "$CONFIG" && -f "$CONFIG" ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --config $CONFIG"
fi

PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$PIPELINE_DIR")"
PYTHON="$PROJECT_DIR/.venv/bin/python"
FFMPEG="${FFMPEG:-/opt/homebrew/bin/ffmpeg}"

WORK=$(mktemp -d)
trap "rm -rf $WORK" EXIT

PREPPED="$WORK/stills"
DEPTHS="$WORK/depths"
CLIPS="$WORK/clips"
mkdir -p "$PREPPED" "$DEPTHS" "$CLIPS"

# Discover shot IDs from the motion table (single source of truth for N).
# Space-separated to stay compatible with macOS bash 3.2 (no readarray).
SHOT_IDS=$("$PYTHON" -c "
import json
with open('$MOTION_TABLE') as f:
    data = json.load(f)
print(' '.join(str(int(s['id'])) for s in data.get('shots', [])))
")
if [[ -z "$SHOT_IDS" ]]; then
  echo "ERROR: no shots in $MOTION_TABLE"
  exit 1
fi
SHOT_COUNT=$(echo "$SHOT_IDS" | wc -w | tr -d ' ')
echo "Shot plan: $MOTION_TABLE -> $SHOT_COUNT shots ($SHOT_IDS)"

echo "Step 1: prepping stills (resize to 2160x3840 if needed)..."
for i in $SHOT_IDS; do
  SRC="$STILLS_IN/shot${i}.jpg"
  [[ -f "$SRC" ]] || SRC="$STILLS_IN/shot${i}.png"
  if [[ ! -f "$SRC" ]]; then
    echo "ERROR: missing $STILLS_IN/shot${i}.jpg or .png"
    exit 1
  fi
  $FFMPEG -y -i "$SRC" -vf "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840" -q:v 2 "$PREPPED/shot${i}.jpg" -hide_banner -loglevel error
  echo "  shot${i} prepped"
done

FRAMES_FLAG=""
AUDIO_VENV_PY="$PROJECT_DIR/.venv-audio/bin/python"
if [[ -n "$AUDIO" ]]; then
  echo ""
  echo "Step 1.5: running audio_plan Tier 1 planner..."
  if [[ ! -x "$AUDIO_VENV_PY" ]]; then
    echo "ERROR: audio venv missing at $AUDIO_VENV_PY"
    echo "  Create it per AUDIO_PLAN.md before using --audio."
    exit 1
  fi
  PLAN_JSON="$WORK/audio_plan.json"
  (cd "$PROJECT_DIR" && "$AUDIO_VENV_PY" -m pipeline.audio_plan_cli "$AUDIO" \
      --tier 1 --n-shots "$SHOT_COUNT" --out "$PLAN_JSON") >&2
  FRAMES_CSV=$("$PYTHON" -c "
import json
p = json.load(open('$PLAN_JSON'))
fps = 24
print(','.join(str(max(1, round(d * fps))) for d in p['shot_durations']))
")
  echo "  plan: $PLAN_JSON"
  echo "  → frame counts: $FRAMES_CSV"
  FRAMES_FLAG="--frames $FRAMES_CSV"
fi

# Render to a temporary path so we can mux audio afterwards.
RENDER_OUT="$OUTPUT"
if [[ -n "$AUDIO" ]]; then
  RENDER_OUT="$WORK/silent.mp4"
fi

if [[ "$USE_LEGACY" == "true" ]]; then
  echo ""
  echo "Step 2: building 8 zoompan clips (LEGACY ffmpeg zoompan)..."
  "$PIPELINE_DIR/recipes.sh" build_all "$PREPPED" "$CLIPS"
  echo ""
  echo "Step 3: concatenating final video..."
  "$PIPELINE_DIR/recipes.sh" concat "$CLIPS" "$RENDER_OUT"
else
  echo ""
  echo "Step 2: computing depth maps with Depth Anything v2 Large..."
  "$PYTHON" "$PIPELINE_DIR/compute_depth.py" "$PREPPED" "$DEPTHS" 2>&1 | grep -v "^$" | tail -15

  echo ""
  echo "Step 3: rendering 8 perspective-parallax clips..."
  echo "  motion scale: ${SCALE}x | depth intensity: ${DEPTH_INTENSITY} | crf: ${CRF}"
  "$PYTHON" "$PIPELINE_DIR/render_v2.py" all "$PREPPED" "$DEPTHS" "$CLIPS" "$RENDER_OUT" \
    --scale "$SCALE" --depth-intensity "$DEPTH_INTENSITY" --crf "$CRF" \
    --motion-table "$MOTION_TABLE" $EXTRA_FLAGS $FRAMES_FLAG
fi

if [[ -n "$AUDIO" ]]; then
  echo ""
  echo "Step 4: muxing audio ($AUDIO)..."
  $FFMPEG -y -i "$RENDER_OUT" -i "$AUDIO" \
    -map 0:v:0 -map 1:a:0 \
    -c:v copy -c:a aac -b:a 192k \
    -shortest -movflags +faststart \
    "$OUTPUT" -hide_banner -loglevel error
fi

echo ""
echo "============================================================"
echo "DONE"
echo "============================================================"
$FFMPEG -i "$OUTPUT" -hide_banner 2>&1 | grep -E "Duration|Stream #0:0" | sed 's/^/  /'
SIZE=$(ls -la "$OUTPUT" | awk '{print $5}')
SIZE_MB=$(echo "scale=1; $SIZE/1048576" | bc)
echo "  File size: ${SIZE_MB} MB"
echo ""
echo "Output: $OUTPUT"
