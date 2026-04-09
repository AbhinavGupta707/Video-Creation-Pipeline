#!/usr/bin/env python
"""
Scene-detect + thumbnail extraction only (no VLM).

For each video in sample_25.json:
  1. PySceneDetect ContentDetector -> shot boundaries
  2. Extract mid-frame of each shot -> thumbs/<video>/shotNN.jpg
  3. Write per_video/<video>.json with shots stub (label = null)

The VLM labeling step is done separately by subagents reading the thumbs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
VIDEOS_DIR = REPO / "videos"
PER_VIDEO_DIR = ROOT / "per_video"
THUMBS_DIR = ROOT / "thumbs"
SAMPLE_FILE = ROOT / "sample_25.json"

MAX_THUMB_W = 640
MIN_SHOT_SEC = 0.35


def detect_shots(video_path: Path, threshold: float = 20.0) -> list[tuple[float, float]]:
    video = open_video(str(video_path))
    mgr = SceneManager()
    mgr.add_detector(ContentDetector(threshold=threshold))
    mgr.detect_scenes(video)
    scenes = mgr.get_scene_list()
    if not scenes:
        cap = cv2.VideoCapture(str(video_path))
        n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.release()
        return [(0.0, n / fps if fps else 0.0)]
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
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t_mid * fps)))
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


def process_video(video_path: Path) -> dict:
    name_stem = video_path.stem
    shots = detect_shots(video_path)
    shot_objs = []
    for i, (s, e) in enumerate(shots, 1):
        dur = e - s
        t_mid = (s + e) / 2
        thumb = THUMBS_DIR / name_stem / f"shot{i:02d}.jpg"
        if not extract_mid_frame(video_path, t_mid, thumb):
            continue
        shot_objs.append({
            "id": i,
            "start": round(s, 3),
            "end": round(e, 3),
            "duration": round(dur, 3),
            "thumb": str(thumb.relative_to(REPO)),
            "label": None,  # filled by subagent labeling pass
        })
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
    ap.add_argument("--only", help="Only this filename substring")
    args = ap.parse_args()

    sample = json.loads(SAMPLE_FILE.read_text())["videos"]
    if args.only:
        sample = [v for v in sample if args.only in v]

    PER_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for i, name in enumerate(sample, 1):
        vp = VIDEOS_DIR / name
        if not vp.exists():
            print(f"[{i}/{len(sample)}] MISSING {name}")
            continue
        result = process_video(vp)
        out_json = PER_VIDEO_DIR / f"{vp.stem}.json"
        out_json.write_text(json.dumps(result, indent=2))
        print(f"[{i:2d}/{len(sample)}] {name}  -> {result['shot_count']} shots, {result['total_duration']}s")


if __name__ == "__main__":
    main()
