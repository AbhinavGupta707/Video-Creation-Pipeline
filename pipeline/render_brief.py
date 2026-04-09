#!/usr/bin/env python
"""
render_brief.py — Single-command car showcase reel renderer.

Reads a brief directory containing brief.json, motion.json, and stills,
looks up locked frame counts from audio_timings_master.json, computes or
reuses cached depth maps, renders with render_v2.py, and muxes audio.

Usage:
  python pipeline/render_brief.py briefs/wine_czinger_21c/ \\
      --audio "audio 1.mp3" -o /tmp/czinger.mp4

  python pipeline/render_brief.py briefs/wine_czinger_21c/ \\
      --audio "1.mp3" -o /tmp/czinger_1mp3.mp4 --scale 1.5 --cinematic

  python pipeline/render_brief.py briefs/wine_czinger_21c/ \\
      --audio "audio 1.mp3" -o /dev/null --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = Path(__file__).resolve().parent
AUDIO_TIMINGS_PATH = PROJECT_DIR / "Audio" / "audio_timings_master.json"
PYTHON = str(PROJECT_DIR / ".venv" / "bin" / "python")
FFMPEG = os.environ.get("FFMPEG", "/opt/homebrew/bin/ffmpeg")
FPS = 24


def load_brief(brief_dir: Path) -> dict:
    """Load and validate brief.json."""
    path = brief_dir / "brief.json"
    if not path.exists():
        sys.exit(f"ERROR: brief.json not found in {brief_dir}")
    with open(path) as f:
        brief = json.load(f)
    if "shots" not in brief:
        sys.exit("ERROR: brief.json missing 'shots' array")
    return brief


def load_motion(brief_dir: Path) -> dict:
    """Load motion.json from the brief directory."""
    path = brief_dir / "motion.json"
    if not path.exists():
        sys.exit(f"ERROR: motion.json not found in {brief_dir}")
    with open(path) as f:
        motion = json.load(f)
    if "shots" not in motion:
        sys.exit("ERROR: motion.json missing 'shots' array")
    return motion


def load_locked_timings(track_name: str) -> dict:
    """Load frame_counts and metadata for a track from audio_timings_master.json."""
    if not AUDIO_TIMINGS_PATH.exists():
        sys.exit(f"ERROR: audio_timings_master.json not found at {AUDIO_TIMINGS_PATH}")
    with open(AUDIO_TIMINGS_PATH) as f:
        master = json.load(f)
    tracks = master.get("tracks", {})
    if track_name not in tracks:
        available = ", ".join(sorted(tracks.keys()))
        sys.exit(f"ERROR: track '{track_name}' not in audio_timings_master.json. "
                 f"Available: {available}")
    return tracks[track_name]


def merge_motion_table(motion: dict, timings: dict) -> dict:
    """Merge motion specs with locked frame counts into a render_v2-compatible table.

    Validates that shot counts match.
    """
    motion_shots = motion["shots"]
    frame_counts = timings["frame_counts"]

    if len(motion_shots) != len(frame_counts):
        sys.exit(f"ERROR: motion.json has {len(motion_shots)} shots but "
                 f"audio track expects {len(frame_counts)} shots")

    merged = {
        "_comment": "Auto-merged by render_brief.py — DO NOT EDIT",
        "source_audio": timings.get("path", ""),
        "output_resolution": motion.get("output_resolution", [1080, 1920]),
        "output_fps": FPS,
        "ai_still_resolution": motion.get("ai_still_resolution", [2160, 3840]),
        "shots": [],
    }

    for shot, fc in zip(motion_shots, frame_counts):
        merged["shots"].append({
            "id": shot["id"],
            "duration": round(fc / FPS, 3),
            "frame_count": fc,
            "subject": shot.get("subject", ""),
            "camera_position": shot.get("camera_position", ""),
            "motion": dict(shot["motion"]),
            "purpose": shot.get("purpose", ""),
        })

    return merged


def resolve_stills_dir(brief_dir: Path, brief: dict) -> Path:
    """Find the stills directory, checking brief config then common names."""
    candidates = []
    if "stills_dir" in brief:
        candidates.append(brief_dir / brief["stills_dir"])
    candidates.extend([
        brief_dir / "Final Images",
        brief_dir / "stills",
    ])
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("shot*")):
            return candidate
    checked = [str(c) for c in candidates]
    sys.exit(f"ERROR: no stills directory found. Checked: {checked}")


def ensure_depths(
    brief_dir: Path, prepped_dir: Path, depths_dir: Path
) -> None:
    """Compute depth maps, using brief_dir/depths/ as a persistent cache."""
    cache_dir = brief_dir / "depths"
    cache_dir.mkdir(exist_ok=True)

    cmd = [
        PYTHON, str(PIPELINE_DIR / "compute_depth.py"),
        str(prepped_dir), str(depths_dir),
        "--cache-dir", str(cache_dir),
    ]
    subprocess.run(cmd, check=True)


def prep_stills(stills_dir: Path, prepped_dir: Path, shot_ids: list[int]) -> None:
    """Resize stills to 2160x3840 (4K 9:16) for the renderer."""
    prepped_dir.mkdir(parents=True, exist_ok=True)
    for shot_id in shot_ids:
        src = None
        for ext in ("jpg", "png"):
            candidate = stills_dir / f"shot{shot_id}.{ext}"
            if candidate.exists():
                src = candidate
                break
        if src is None:
            sys.exit(f"ERROR: missing shot{shot_id}.jpg or .png in {stills_dir}")

        dst = prepped_dir / f"shot{shot_id}.jpg"
        subprocess.run([
            FFMPEG, "-y", "-i", str(src),
            "-vf", "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840",
            "-q:v", "2", str(dst),
            "-hide_banner", "-loglevel", "error",
        ], check=True)
        print(f"  shot{shot_id} prepped")


def render(
    brief_dir: Path,
    audio_track: str,
    output: Path,
    *,
    scale: float = 1.0,
    depth_intensity: float = 2.5,
    crf: int = 22,
    config: str | None = None,
    no_parallax: bool = False,
    grade: bool = False,
    vignette: bool = False,
    grain: bool = False,
    cinematic: bool = False,
    dry_run: bool = False,
    open_after: bool = False,
) -> None:
    """Main orchestration: brief + audio track → final video."""
    # 1. Load sources
    print(f"Brief: {brief_dir}")
    brief = load_brief(brief_dir)
    motion = load_motion(brief_dir)
    timings = load_locked_timings(audio_track)
    print(f"Audio: {audio_track} ({timings['duration_sec']:.1f}s, "
          f"{timings['shot_count']} shots)")

    # 2. Merge motion + timing
    merged = merge_motion_table(motion, timings)
    shot_ids = [s["id"] for s in merged["shots"]]
    frame_counts = timings["frame_counts"]
    total_frames = sum(frame_counts)
    print(f"Shots: {len(shot_ids)} | Frames: {frame_counts} "
          f"(total {total_frames}, {total_frames / FPS:.2f}s)")

    if dry_run:
        print("\n--- Merged motion table (dry run) ---")
        print(json.dumps(merged, indent=2))
        return

    # 3. Set up working directory
    work = Path(tempfile.mkdtemp(prefix="render_brief_"))
    try:
        prepped_dir = work / "stills"
        depths_dir = work / "depths"
        clips_dir = work / "clips"
        prepped_dir.mkdir()
        depths_dir.mkdir()
        clips_dir.mkdir()

        # 4. Resolve and prep stills
        stills_dir = resolve_stills_dir(brief_dir, brief)
        print(f"\nStep 1: prepping stills from {stills_dir.name}/...")
        prep_stills(stills_dir, prepped_dir, shot_ids)

        # 5. Compute/cache depth maps
        print("\nStep 2: computing depth maps (cache-aware)...")
        ensure_depths(brief_dir, prepped_dir, depths_dir)

        # 6. Write merged motion table
        merged_path = work / "motion_table.json"
        with open(merged_path, "w") as f:
            json.dump(merged, f, indent=2)

        # 7. Render
        silent_path = work / "silent.mp4"
        print(f"\nStep 3: rendering {len(shot_ids)} parallax clips...")
        print(f"  scale={scale}x | depth_intensity={depth_intensity} | crf={crf}")

        render_cmd = [
            PYTHON, str(PIPELINE_DIR / "render_v2.py"),
            "all", str(prepped_dir), str(depths_dir), str(clips_dir),
            str(silent_path),
            "--motion-table", str(merged_path),
            "--scale", str(scale),
            "--depth-intensity", str(depth_intensity),
            "--crf", str(crf),
        ]
        if config:
            render_cmd.extend(["--config", config])
        if no_parallax:
            render_cmd.append("--no-parallax")
        if grade or cinematic:
            render_cmd.append("--grade")
        if vignette or cinematic:
            render_cmd.append("--vignette")
        if grain or cinematic:
            render_cmd.append("--grain")

        subprocess.run(render_cmd, check=True)

        # 8. Mux audio
        audio_path = PROJECT_DIR / timings["path"]
        if not audio_path.exists():
            sys.exit(f"ERROR: audio file not found: {audio_path}")

        print(f"\nStep 4: muxing audio ({audio_path.name})...")
        subprocess.run([
            FFMPEG, "-y",
            "-i", str(silent_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(output),
            "-hide_banner", "-loglevel", "error",
        ], check=True)

        # 9. Quality report
        car_name = brief.get("car", {}).get("full_name", brief_dir.name)
        size = output.stat().st_size
        drop_shot = timings.get("drop_shot")

        print("\n" + "=" * 60)
        print(f"DONE -- {car_name} x {audio_track}")
        print("=" * 60)
        print(f"  Duration: {total_frames / FPS:.2f}s | "
              f"{total_frames} frames | "
              f"{size / 1048576:.1f} MB | crf {crf}")
        print()
        print("  Shot breakdown:")
        print(f"  {'#':>2s}  {'Archetype':<28s}  {'Frames':>6s}  "
              f"{'Duration':>8s}  {'Motion':<s}")

        for shot_meta, merged_shot in zip(
            brief.get("shots", []), merged["shots"]
        ):
            sid = merged_shot["id"]
            archetype = shot_meta.get("archetype", "?")
            fc = merged_shot["frame_count"]
            dur = fc / FPS
            m = merged_shot["motion"]
            tx = m.get("tx_px_1080", 0)
            ty = m.get("ty_px_1080", 0)
            z0 = m.get("zoom_start", 1.0)
            z1 = m.get("zoom_end", 1.0)

            # Build compact motion string
            parts = []
            if tx != 0:
                parts.append(f"tx{tx:+.0f}")
            if ty != 0:
                parts.append(f"ty{ty:+.0f}")
            parts.append(f"zoom {z0:.3f}->{z1:.3f}")
            motion_str = " ".join(parts)

            drop_marker = "  <- DROP" if drop_shot and sid == drop_shot else ""
            print(f"  {sid:>2d}  {archetype:<28s}  {fc:>6d}  "
                  f"{dur:>7.2f}s  {motion_str}{drop_marker}")

        print(f"\n  Output: {output}")

        if open_after:
            subprocess.run(["open", str(output)], check=False)

    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Render a car showcase reel from a brief directory"
    )
    p.add_argument("brief_dir", type=Path, help="Path to brief directory")
    p.add_argument("--audio", required=True,
                   help="Audio track name (key in audio_timings_master.json)")
    p.add_argument("--output", "-o", type=Path, required=True,
                   help="Output video path")
    p.add_argument("--scale", type=float, default=1.0,
                   help="Motion magnitude multiplier (default 1.0)")
    p.add_argument("--depth-intensity", type=float, default=2.5,
                   help="Perspective parallax strength (default 2.5)")
    p.add_argument("--crf", type=int, default=22,
                   help="Quality: 18=master, 20=high, 22=delivery, 24=social")
    p.add_argument("--config", type=str, default=None,
                   help="Per-shot config JSON path")
    p.add_argument("--no-parallax", action="store_true")
    p.add_argument("--grade", action="store_true")
    p.add_argument("--vignette", action="store_true")
    p.add_argument("--grain", action="store_true")
    p.add_argument("--cinematic", action="store_true",
                   help="Enable grade + vignette + grain")
    p.add_argument("--dry-run", action="store_true",
                   help="Print merged motion table and exit without rendering")
    p.add_argument("--open", action="store_true",
                   help="Open the output video in QuickTime after render")
    args = p.parse_args()

    render(
        brief_dir=args.brief_dir,
        audio_track=args.audio,
        output=args.output,
        scale=args.scale,
        depth_intensity=args.depth_intensity,
        crf=args.crf,
        config=args.config,
        no_parallax=args.no_parallax,
        grade=args.grade,
        vignette=args.vignette,
        grain=args.grain,
        cinematic=args.cinematic,
        dry_run=args.dry_run,
        open_after=args.open,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
