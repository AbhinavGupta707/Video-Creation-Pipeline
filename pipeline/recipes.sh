#!/usr/bin/env bash
# Wine Ferrari recreation — ffmpeg zoompan recipes per shot.
# Each function takes (input_still, output_clip) and produces a 1080x1920 24fps mp4
# matching the motion of the corresponding shot in the original video.
#
# Convention:
#   - Input still expected at 2160x3840 (4K vertical 9:16)
#   - Output 1080x1920 24fps
#   - Motion magnitudes are in OUTPUT pixels at 1080w; doubled for source pixel space
#
# Direction convention used in zoompan x/y expressions:
#   - Camera moves RIGHT → visible window slides RIGHT in source → x increases (positive offset)
#   - Camera moves LEFT  → x decreases (negative offset)
#   - Camera moves UP    → y decreases
#   - Camera moves DOWN  → y increases
#   - Push-in            → zoom increases over time
#   - Pull-back          → zoom decreases over time
#
# zoompan center expression: x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)'
# We add a time-varying offset to that center.
#
# IMPORTANT: zoompan animates per OUTPUT FRAME. d=N means produce N output frames.
# 'on' is the current output frame index (0..d-1).

set -euo pipefail

FFMPEG="${FFMPEG:-/opt/homebrew/bin/ffmpeg}"
OUT_W=1080
OUT_H=1920
FPS=24

# Helper: build zoompan filter expression
# args: $1=duration_frames $2=z_start $3=z_end $4=x_delta_src_px $5=y_delta_src_px
# Output offsets are in SOURCE pixels (2x output px).
zoompan_expr() {
  local D=$1 ZS=$2 ZE=$3 XD=$4 YD=$5
  local DM1=$((D - 1))
  echo "zoompan=z='${ZS}+(${ZE}-${ZS})*on/${DM1}':x='iw/2-(iw/zoom/2)+(${XD})*on/${DM1}':y='ih/2-(ih/zoom/2)+(${YD})*on/${DM1}':d=${D}:s=${OUT_W}x${OUT_H}:fps=${FPS}"
}

# ----------- per-shot recipe functions -----------

shot1() {  # Side profile, push-in 3.5%
  local IN=$1 OUT=$2
  local D=54
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.035 0 0)" -t 2.262 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot2() {  # Rear-3/4, yaw right (cam right 15px @1080w → 30 src px) + pull-back 3%
  local IN=$1 OUT=$2
  local D=54
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.030 1.000 30 0)" -t 2.261 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot3() {  # Wing macro, pan right 12 + tilt up 5 + push-in 1.9%
  local IN=$1 OUT=$2
  local D=52
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.019 24 -10)" -t 2.179 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot4() {  # Direct rear, tilt up 8 + tiny push 0.5%
  local IN=$1 OUT=$2
  local D=52
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.005 0 -16)" -t 2.180 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot5() {  # Direct front, slight tilt up 3 + push 0.6%
  local IN=$1 OUT=$2
  local D=22
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.006 0 -6)" -t 0.904 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot6() {  # Front bonnet, pan right 12 + cam down 5 + push 1.1%
  local IN=$1 OUT=$2
  local D=28
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.011 24 10)" -t 1.152 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot7() {  # Front-left 3/4 hero, subtle pan right 5 + push 1.3%
  local IN=$1 OUT=$2
  local D=26
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.013 10 0)" -t 1.069 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

shot8() {  # Front wheel, pan LEFT 22 + tilt up 6 + push 2.5%
  local IN=$1 OUT=$2
  local D=28
  $FFMPEG -y -loop 1 -i "$IN" -vf "$(zoompan_expr $D 1.000 1.025 -44 -12)" -t 1.181 -c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "$OUT"
}

# Run all shots from a directory of stills (shot1.jpg through shot8.jpg)
build_all() {
  local STILLS_DIR=$1
  local OUT_DIR=$2
  mkdir -p "$OUT_DIR"
  for i in 1 2 3 4 5 6 7 8; do
    if [[ ! -f "$STILLS_DIR/shot${i}.jpg" ]]; then
      echo "ERROR: missing $STILLS_DIR/shot${i}.jpg"; exit 1
    fi
    echo "Building shot $i..."
    shot${i} "$STILLS_DIR/shot${i}.jpg" "$OUT_DIR/clip${i}.mp4"
  done
}

# Concat 8 clips into final video
concat_clips() {
  local OUT_DIR=$1
  local FINAL=$2
  local ABS_OUT=$(cd "$OUT_DIR" && pwd)
  local LIST=$(mktemp)
  for i in 1 2 3 4 5 6 7 8; do
    echo "file '$ABS_OUT/clip${i}.mp4'" >> "$LIST"
  done
  $FFMPEG -y -f concat -safe 0 -i "$LIST" -c copy "$FINAL" -hide_banner -loglevel error
  rm -f "$LIST"
  echo "DONE: $FINAL"
}

# CLI dispatch
if [[ "${1:-}" == "build_all" ]]; then
  build_all "$2" "$3"
elif [[ "${1:-}" == "concat" ]]; then
  concat_clips "$2" "$3"
elif [[ "${1:-}" =~ ^shot[1-8]$ ]]; then
  $1 "$2" "$3"
else
  echo "Usage:"
  echo "  $0 shot{1..8} input_still.jpg output_clip.mp4"
  echo "  $0 build_all stills_dir/ output_dir/"
  echo "  $0 concat output_dir/ final.mp4"
fi
