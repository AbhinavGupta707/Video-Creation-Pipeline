"""Phase 3 / Phase 4-lite: analyze any reference video → motion_table.json + stills.

Pipeline:
  1. Scene detection (PySceneDetect, content detector) → list of (start, end) shots
  2. Per-shot optical flow (Farneback dense flow averaged across sampled frames)
  3. Derive tx_px_1080, ty_px_1080, zoom_start, zoom_end for each shot
  4. Extract the middle frame per shot, upscale to 2160x3840, write as shot{N}.jpg
  5. Emit motion_table.json in the schema render_v2.py expects

Usage:
  .venv/bin/python pipeline/analyze_video.py <video> <out_dir>

The resulting out_dir is ready to feed into make_video.sh:
  ./pipeline/make_video.sh <out_dir>/stills/ final.mp4 \
        --motion-table <out_dir>/motion_table.json --no-config
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np


OUTPUT_W = 1080
OUTPUT_H = 1920
STILL_W = 2160
STILL_H = 3840
SAMPLES_PER_SHOT = 8  # frames to sample per shot for flow estimation
SCENE_THRESHOLD = 27.0  # PySceneDetect content-detector default


def detect_shots(video_path: str) -> list[tuple[float, float]]:
    """Run PySceneDetect ContentDetector; return list of (start_s, end_s)."""
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector

    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=SCENE_THRESHOLD))
    sm.detect_scenes(video)
    scenes = sm.get_scene_list()
    if not scenes:
        # Single-scene fallback: treat entire video as one shot
        return [(0.0, float(video.duration.get_seconds()))]
    return [(float(s[0].get_seconds()), float(s[1].get_seconds())) for s in scenes]


def _sample_frame_indices(start_frame: int, end_frame: int, n: int) -> list[int]:
    if end_frame - start_frame <= n:
        return list(range(start_frame, end_frame))
    return list(np.linspace(start_frame, end_frame - 1, n, dtype=int))


def analyze_shot_motion(cap: cv2.VideoCapture, src_w: int, src_h: int,
                        start_s: float, end_s: float, fps: float,
                        shot_idx: int) -> dict:
    """Estimate tx/ty/zoom for one shot using Farneback dense optical flow.

    Aggregates mean flow vectors across SAMPLES_PER_SHOT frame pairs, then
    converts source-pixel flow into OUTPUT-pixel-space (1080w) values that
    render_v2.py expects.

    The zoom delta is derived from the radial-flow component (mean outward
    flow magnitude from frame center).
    """
    start_frame = int(start_s * fps)
    end_frame = int(end_s * fps)
    indices = _sample_frame_indices(start_frame, end_frame, SAMPLES_PER_SHOT)
    if len(indices) < 2:
        return _empty_motion(start_s, end_s, shot_idx)

    # Read sampled frames
    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, f = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        # Downscale for speed (flow is robust to this)
        small = cv2.resize(g, (src_w // 2, src_h // 2))
        frames.append(small)
    if len(frames) < 2:
        return _empty_motion(start_s, end_s, shot_idx)

    scale_to_1080 = OUTPUT_W / (src_w / 2)
    tx_vals: list[float] = []
    ty_vals: list[float] = []
    radial_vals: list[float] = []

    for a, b in zip(frames[:-1], frames[1:]):
        flow = cv2.calcOpticalFlowFarneback(
            a, b, None,
            pyr_scale=0.5, levels=3, winsize=25, iterations=3,
            poly_n=5, poly_sigma=1.2, flags=0,
        )
        h, w = flow.shape[:2]
        fx = flow[..., 0]
        fy = flow[..., 1]
        # Central-70% crop to dodge edge artifacts
        mh, mw = int(h * 0.15), int(w * 0.15)
        fx_c = fx[mh:h - mh, mw:w - mw]
        fy_c = fy[mh:h - mh, mw:w - mw]
        tx_vals.append(float(np.mean(fx_c)))
        ty_vals.append(float(np.mean(fy_c)))
        # Radial flow: dot product of (flow, radial_dir) → positive = outward (zoom-in)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rx = xx - w / 2
        ry = yy - h / 2
        rnorm = np.sqrt(rx * rx + ry * ry) + 1e-6
        rx /= rnorm
        ry /= rnorm
        radial = fx * rx + fy * ry
        radial_c = radial[mh:h - mh, mw:w - mw]
        radial_vals.append(float(np.mean(radial_c)))

    # Aggregate: total motion across the shot ~= mean * (n_pairs)
    n_pairs = max(1, len(frames) - 1)
    total_tx_src = float(np.sum(tx_vals))
    total_ty_src = float(np.sum(ty_vals))
    total_radial_src = float(np.sum(radial_vals))

    # Convert to 1080-space totals (what render_v2 expects per full shot)
    total_tx_1080 = total_tx_src * scale_to_1080
    total_ty_1080 = total_ty_src * scale_to_1080
    # Radial → zoom delta. A positive radial of r pixels at the edge
    # corresponds roughly to a fractional scale change of r / half_dim.
    half_dim_small = min(src_w, src_h) / 4  # since we halved
    zoom_delta = total_radial_src / max(half_dim_small, 1.0)

    zoom_start = 1.0
    zoom_end = 1.0 + float(zoom_delta)

    confidence = _confidence(tx_vals, ty_vals)

    # Hard clamp: translations > 40 px in 1080-space are unrealistic for short
    # shots and almost always indicate flow failure (specular, scene change).
    # Under low confidence (<0.3) shrink even further.
    MAX_TX = 40.0
    MAX_TY = 25.0
    if confidence < 0.3:
        MAX_TX = 15.0
        MAX_TY = 10.0
    total_tx_1080 = max(-MAX_TX, min(MAX_TX, total_tx_1080))
    total_ty_1080 = max(-MAX_TY, min(MAX_TY, total_ty_1080))
    # Zoom clamped to ±6% — matches wine ferrari baseline range
    zoom_end = max(0.97, min(1.06, zoom_end))

    duration = end_s - start_s
    frame_count = max(1, int(round(duration * 24)))  # output fps

    return {
        "id": shot_idx,
        "start": round(start_s, 3),
        "end": round(end_s, 3),
        "duration": round(duration, 3),
        "frame_count": frame_count,
        "subject": f"Auto-detected shot {shot_idx}",
        "camera_position": "unknown",
        "motion": {
            "type": _describe_motion(total_tx_1080, total_ty_1080, zoom_end - 1.0),
            "tx_px_1080": round(total_tx_1080, 1),
            "ty_px_1080": round(total_ty_1080, 1),
            "zoom_start": round(zoom_start, 4),
            "zoom_end": round(zoom_end, 4),
        },
        "_flow_confidence": round(confidence, 3),
        "purpose": "auto",
    }


def _empty_motion(start_s: float, end_s: float, shot_idx: int) -> dict:
    duration = end_s - start_s
    return {
        "id": shot_idx,
        "start": round(start_s, 3),
        "end": round(end_s, 3),
        "duration": round(duration, 3),
        "frame_count": max(1, int(round(duration * 24))),
        "subject": f"Shot {shot_idx} (no flow)",
        "camera_position": "unknown",
        "motion": {
            "type": "static",
            "tx_px_1080": 0,
            "ty_px_1080": 0,
            "zoom_start": 1.0,
            "zoom_end": 1.0,
        },
        "_flow_confidence": 0.0,
        "purpose": "auto",
    }


def _describe_motion(tx: float, ty: float, zoom_delta: float) -> str:
    parts: list[str] = []
    if abs(tx) > 5:
        parts.append("pan right" if tx > 0 else "pan left")
    if abs(ty) > 5:
        parts.append("tilt down" if ty > 0 else "tilt up")
    if abs(zoom_delta) > 0.005:
        parts.append("push-in" if zoom_delta > 0 else "pull-back")
    return " + ".join(parts) if parts else "mostly static"


def _confidence(tx_vals: list[float], ty_vals: list[float]) -> float:
    """Low variance in per-pair flow => higher confidence."""
    if not tx_vals:
        return 0.0
    arr = np.array(tx_vals + ty_vals)
    if arr.size < 2:
        return 1.0
    # Confidence = 1 / (1 + std) scaled to 0..1
    return float(1.0 / (1.0 + np.std(arr)))


def extract_still(cap: cv2.VideoCapture, start_s: float, end_s: float, fps: float,
                  out_path: str) -> None:
    """Pull the middle frame of the shot and upscale to 2160x3840."""
    mid_frame = int(((start_s + end_s) / 2) * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"failed to read middle frame at {mid_frame}")
    h, w = frame.shape[:2]
    # Scale to match 2160x3840 portrait, center crop if needed
    target_aspect = STILL_W / STILL_H
    src_aspect = w / h
    if src_aspect > target_aspect:
        # too wide — crop width
        new_w = int(h * target_aspect)
        off = (w - new_w) // 2
        frame = frame[:, off:off + new_w]
    else:
        new_h = int(w / target_aspect)
        off = (h - new_h) // 2
        frame = frame[off:off + new_h, :]
    frame = cv2.resize(frame, (STILL_W, STILL_H), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])


def build_motion_table(video_path: str, shots: list[dict],
                        src_w: int, src_h: int, src_fps: float,
                        src_duration: float) -> dict:
    return {
        "_comment": f"Auto-generated from {os.path.basename(video_path)} by analyze_video.py",
        "source_video": video_path,
        "source_resolution": [src_w, src_h],
        "source_fps": round(src_fps, 2),
        "source_duration": round(src_duration, 3),
        "output_resolution": [OUTPUT_W, OUTPUT_H],
        "output_fps": 24,
        "ai_still_resolution": [STILL_W, STILL_H],
        "shots": shots,
    }


def analyze(video_path: str, out_dir: str) -> dict:
    out_path = Path(out_dir)
    stills_dir = out_path / "stills"
    stills_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Detecting shots in {video_path}...")
    shot_spans = detect_shots(video_path)
    print(f"    found {len(shot_spans)} shots")
    for i, (a, b) in enumerate(shot_spans, start=1):
        print(f"      shot{i}: {a:6.2f}s - {b:6.2f}s  ({b - a:.2f}s)")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_duration = n_frames / max(src_fps, 1e-3)
    print(f"    source: {src_w}x{src_h} @ {src_fps:.2f}fps, {src_duration:.2f}s")

    print(f"[2/4] Analyzing per-shot motion via Farneback flow...")
    shots: list[dict] = []
    for i, (a, b) in enumerate(shot_spans, start=1):
        info = analyze_shot_motion(cap, src_w, src_h, a, b, src_fps, i)
        print(f"    shot{i}: tx={info['motion']['tx_px_1080']:+.1f} "
              f"ty={info['motion']['ty_px_1080']:+.1f} "
              f"z {info['motion']['zoom_start']:.3f}->{info['motion']['zoom_end']:.3f} "
              f"conf={info['_flow_confidence']:.2f} "
              f"({info['motion']['type']})")
        shots.append(info)

    print(f"[3/4] Extracting stills to {stills_dir}...")
    for i, (a, b) in enumerate(shot_spans, start=1):
        still_path = stills_dir / f"shot{i}.jpg"
        extract_still(cap, a, b, src_fps, str(still_path))
        print(f"    -> {still_path}")

    cap.release()

    print(f"[4/4] Writing motion_table.json...")
    table = build_motion_table(video_path, shots, src_w, src_h, src_fps, src_duration)
    table_path = out_path / "motion_table.json"
    table_path.write_text(json.dumps(table, indent=2))
    print(f"    -> {table_path}")
    return table


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    video_path = sys.argv[1]
    out_dir = sys.argv[2]
    analyze(video_path, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
