#!/usr/bin/env python
"""
Shallow shot-vocabulary analyzer.

For each video:
  1. Detect cuts with PySceneDetect (ContentDetector).
  2. Extract middle frame of each shot as a thumbnail.
  3. Send thumbnail to Claude Sonnet 4.6 vision -> structured JSON label
     (framing, camera_position, subject, motion_tag [low confidence],
      lighting, mood, environment).
  4. Write per_video/<name>.json with the full shot list + cadence.

NOTE on motion_tag: VLMs hallucinate motion *direction* (documented in
HANDOVER.md). We still collect a coarse tag for the library catalog, but
it is explicitly marked low-confidence and not used as ground truth.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

import anthropic
import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
VIDEOS_DIR = REPO / "videos"
PER_VIDEO_DIR = ROOT / "per_video"
THUMBS_DIR = ROOT / "thumbs"
SAMPLE_FILE = ROOT / "sample_25.json"

MODEL = "claude-sonnet-4-5"  # vision-capable, structured output
MAX_THUMB_W = 512  # keep image payload small
MIN_SHOT_SEC = 0.35  # filter micro-cuts


SYSTEM_PROMPT = """You are a cinematographer labeling a single still frame from a car reveal / showcase video. Return STRICT JSON with these keys:

{
  "subject": "one short phrase — what the camera is looking at (e.g. 'front-left 3/4 full car', 'rear wing endplate ECU', 'front-left wheel close-up')",
  "framing": "one of: wide_full_car | medium_3q | medium_side | tight_detail | extreme_close_up | low_hero | top_down | wheel_detail | badge_detail | interior",
  "camera_position": "clock position + height (e.g. '10:30 hood-height', '6:00 bumper-low', '9:00 mid-body', 'top-down overhead', 'ground-level front-left')",
  "motion_tag_guess": "best guess at camera motion type, LOW CONFIDENCE (e.g. 'push_in', 'pan_right', 'pull_back', 'tilt_up', 'static_arc', 'orbit_right', 'unknown')",
  "environment": "one of: studio_grey | studio_black | studio_white | outdoor_street | outdoor_track | outdoor_nature | garage | showroom | themed_set | unknown",
  "lighting": "one short phrase (e.g. 'single top key soft', 'hard side light', 'ambient outdoor overcast', 'rim backlight dark bg')",
  "mood": "one short phrase (e.g. 'premium restrained', 'aggressive aero hero', 'playful candy pop', 'menacing dark')",
  "color_family": "one of: wine | candy_vivid | carbon_black | dark_moody | light_pastel | white | themed | outdoor_natural",
  "notable_details": "brief — any livery, badge, decal, unique element, or 'none'"
}

Rules:
- Respond with ONLY the JSON object. No prose before or after.
- If uncertain on any field, use 'unknown' rather than guessing.
- motion_tag_guess is inherently unreliable from a single frame; mark 'unknown' liberally.
"""


def detect_shots(video_path: Path, threshold: float = 27.0) -> list[tuple[float, float]]:
    video = open_video(str(video_path))
    mgr = SceneManager()
    mgr.add_detector(ContentDetector(threshold=threshold))
    mgr.detect_scenes(video)
    scenes = mgr.get_scene_list()
    if not scenes:
        # single shot fallback
        duration = video.duration.get_seconds() if hasattr(video.duration, "get_seconds") else float(video.duration)
        return [(0.0, duration)]
    out = []
    for start, end in scenes:
        s, e = start.get_seconds(), end.get_seconds()
        if e - s >= MIN_SHOT_SEC:
            out.append((s, e))
    return out or [(scenes[0][0].get_seconds(), scenes[-1][1].get_seconds())]


def extract_mid_frame(video_path: Path, t_mid: float, out_path: Path) -> bool:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_idx = int(round(t_mid * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return False
    h, w = frame.shape[:2]
    if w > MAX_THUMB_W:
        scale = MAX_THUMB_W / w
        frame = cv2.resize(frame, (MAX_THUMB_W, int(h * scale)), interpolation=cv2.INTER_AREA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return True


def label_frame(client: anthropic.Anthropic, thumb_path: Path) -> dict:
    img_b64 = base64.standard_b64encode(thumb_path.read_bytes()).decode()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                {"type": "text", "text": "Label this frame."},
            ],
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    # Strip code fences if the model wrapped it
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": text}


def analyze_video(video_path: Path, client: anthropic.Anthropic, verbose: bool = True) -> dict:
    name = video_path.stem
    shots = detect_shots(video_path)
    shot_objs = []
    for i, (s, e) in enumerate(shots, 1):
        dur = e - s
        t_mid = (s + e) / 2
        thumb = THUMBS_DIR / name / f"shot{i:02d}.jpg"
        if not extract_mid_frame(video_path, t_mid, thumb):
            if verbose:
                print(f"  shot {i}: frame extract FAILED")
            continue
        label = label_frame(client, thumb)
        shot_objs.append({
            "id": i,
            "start": round(s, 3),
            "end": round(e, 3),
            "duration": round(dur, 3),
            "thumb": str(thumb.relative_to(REPO)),
            "label": label,
        })
        if verbose:
            subj = label.get("subject", "?")[:50] if isinstance(label, dict) else "?"
            print(f"  shot {i:2d} [{s:5.2f}-{e:5.2f} {dur:4.2f}s]  {subj}")
    total = shots[-1][1] - shots[0][0] if shots else 0.0
    durations = [o["duration"] for o in shot_objs]
    return {
        "video": video_path.name,
        "total_duration": round(total, 3),
        "shot_count": len(shot_objs),
        "avg_shot_duration": round(sum(durations) / len(durations), 3) if durations else 0.0,
        "min_shot_duration": round(min(durations), 3) if durations else 0.0,
        "max_shot_duration": round(max(durations), 3) if durations else 0.0,
        "shots": shot_objs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Only analyze this video filename (for testing)")
    ap.add_argument("--limit", type=int, help="Stop after N videos")
    ap.add_argument("--skip-existing", action="store_true", help="Skip videos with existing per_video json")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")

    sample = json.loads(SAMPLE_FILE.read_text())["videos"]
    if args.only:
        sample = [v for v in sample if args.only in v]
    if args.limit:
        sample = sample[: args.limit]

    client = anthropic.Anthropic()
    PER_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    for i, name in enumerate(sample, 1):
        out_json = PER_VIDEO_DIR / f"{Path(name).stem}.json"
        if args.skip_existing and out_json.exists():
            print(f"[{i}/{len(sample)}] SKIP {name}")
            continue
        vp = VIDEOS_DIR / name
        if not vp.exists():
            print(f"[{i}/{len(sample)}] MISSING {name}")
            continue
        print(f"[{i}/{len(sample)}] {name}")
        try:
            result = analyze_video(vp, client)
            out_json.write_text(json.dumps(result, indent=2))
            print(f"   wrote {out_json.relative_to(REPO)}  ({result['shot_count']} shots, {result['total_duration']}s)")
        except Exception as exc:
            print(f"   ERROR: {exc}")


if __name__ == "__main__":
    main()
