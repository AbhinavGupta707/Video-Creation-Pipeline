#!/usr/bin/env python
"""
Aggregate per_video/*.json labels into a flat shot vocabulary catalog.

Groups shots by (framing, camera_position_coarse) and emits archetypes with:
  - typical duration range (min/max/avg from observed instances)
  - source_refs (video + shot_id back-pointers)
  - dominant mood / environment / motion_tag / color_family tallies
  - example thumbnail path

Also emits distribution stats and cadence data (shot-duration histogram,
avg shots per video, etc.) for the pipeline to use later.
"""
from __future__ import annotations

import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PER_VIDEO = ROOT / "per_video"
OUT_LIBRARY = ROOT / "shot_library.json"
OUT_STATS = ROOT / "stats.json"


def coarse_camera_pos(pos: str) -> str:
    """Bucket free-form camera position into coarse groups for dedup."""
    p = (pos or "").lower()
    # height bucket
    if any(k in p for k in ("ground", "low", "bumper")):
        height = "low"
    elif any(k in p for k in ("hood", "mid", "eye")):
        height = "mid"
    elif any(k in p for k in ("high", "above", "overhead", "top")):
        height = "high"
    else:
        height = "mid"
    # direction bucket from clock position if present
    m = re.search(r"(\d{1,2})[:\s]?(\d{2})?\s*(?:o'?clock)?", p)
    direction = "unknown"
    if m:
        try:
            h = int(m.group(1))
            if 11 <= h or h <= 1:
                direction = "front"
            elif 2 <= h <= 4:
                direction = "front_right"
            elif 5 <= h <= 6:
                direction = "rear"
            elif 7 <= h <= 8:
                direction = "rear_left"
            elif h == 9:
                direction = "left"
            elif h == 10:
                direction = "front_left"
        except ValueError:
            pass
    # fallback keyword direction
    if direction == "unknown":
        if "front-left" in p or "front left" in p or "10" in p:
            direction = "front_left"
        elif "front-right" in p or "front right" in p or "2" in p:
            direction = "front_right"
        elif "rear-left" in p or "rear left" in p:
            direction = "rear_left"
        elif "rear-right" in p or "rear right" in p:
            direction = "rear_right"
        elif "rear" in p or "behind" in p:
            direction = "rear"
        elif "front" in p:
            direction = "front"
        elif "side" in p:
            direction = "side"
    return f"{direction}_{height}"


def dominant(counter: Counter) -> str:
    return counter.most_common(1)[0][0] if counter else "unknown"


def main():
    per_video_files = sorted(glob.glob(str(PER_VIDEO / "*.json")))
    all_shots = []
    cadence_rows = []
    for f in per_video_files:
        d = json.load(open(f))
        cadence_rows.append({
            "video": d["video"],
            "shot_count": d["shot_count"],
            "total_duration": d["total_duration"],
            "avg_shot_duration": d["avg_shot_duration"],
            "min_shot_duration": d["min_shot_duration"],
            "max_shot_duration": d["max_shot_duration"],
        })
        for s in d["shots"]:
            if not s.get("label"):
                continue
            all_shots.append({
                "video": d["video"],
                "shot_id": s["id"],
                "duration": s["duration"],
                "thumb": s["thumb"],
                "label": s["label"],
            })

    # Group into archetypes
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for s in all_shots:
        framing = s["label"].get("framing", "unknown")
        cam_coarse = coarse_camera_pos(s["label"].get("camera_position", ""))
        groups[(framing, cam_coarse)].append(s)

    archetypes = []
    for (framing, cam_coarse), shots in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        durations = [s["duration"] for s in shots]
        motion_tags = Counter(s["label"].get("motion_tag_guess", "unknown") for s in shots)
        environments = Counter(s["label"].get("environment", "unknown") for s in shots)
        moods = Counter(s["label"].get("mood", "unknown") for s in shots)
        colors = Counter(s["label"].get("color_family", "unknown") for s in shots)
        lightings = Counter(s["label"].get("lighting", "unknown") for s in shots)
        subjects = Counter(s["label"].get("subject", "unknown") for s in shots)
        archetypes.append({
            "id": f"{framing}__{cam_coarse}",
            "framing": framing,
            "camera_position_coarse": cam_coarse,
            "instance_count": len(shots),
            "duration_min": round(min(durations), 3),
            "duration_max": round(max(durations), 3),
            "duration_avg": round(sum(durations) / len(durations), 3),
            "motion_tag_distribution": dict(motion_tags.most_common()),
            "environment_distribution": dict(environments.most_common(5)),
            "mood_distribution": dict(moods.most_common(5)),
            "color_family_distribution": dict(colors.most_common(5)),
            "lighting_examples": [l for l, _ in lightings.most_common(3)],
            "subject_examples": [s for s, _ in subjects.most_common(3)],
            "example_thumbs": [s["thumb"] for s in shots[:3]],
            "source_refs": [{"video": s["video"], "shot_id": s["shot_id"]} for s in shots],
        })

    # Overall stats
    framing_counts = Counter(s["label"].get("framing", "unknown") for s in all_shots)
    env_counts = Counter(s["label"].get("environment", "unknown") for s in all_shots)
    color_counts = Counter(s["label"].get("color_family", "unknown") for s in all_shots)
    motion_counts = Counter(s["label"].get("motion_tag_guess", "unknown") for s in all_shots)
    all_durations = [s["duration"] for s in all_shots]
    stats = {
        "total_videos": len(cadence_rows),
        "total_shots": len(all_shots),
        "total_archetypes": len(archetypes),
        "avg_shots_per_video": round(sum(r["shot_count"] for r in cadence_rows) / len(cadence_rows), 2),
        "avg_video_duration": round(sum(r["total_duration"] for r in cadence_rows) / len(cadence_rows), 2),
        "shot_duration_histogram": {
            "min": round(min(all_durations), 3),
            "max": round(max(all_durations), 3),
            "mean": round(sum(all_durations) / len(all_durations), 3),
            "p25": round(sorted(all_durations)[len(all_durations) // 4], 3),
            "p50": round(sorted(all_durations)[len(all_durations) // 2], 3),
            "p75": round(sorted(all_durations)[3 * len(all_durations) // 4], 3),
        },
        "framing_distribution": dict(framing_counts.most_common()),
        "environment_distribution": dict(env_counts.most_common()),
        "color_family_distribution": dict(color_counts.most_common()),
        "motion_tag_distribution": dict(motion_counts.most_common()),
        "per_video_cadence": cadence_rows,
    }

    library = {
        "_comment": "Shot vocabulary built from 25 reference videos (Phase A). Archetypes grouped by (framing, camera_position_coarse). Use source_refs to trace back to example frames.",
        "archetypes": archetypes,
    }

    OUT_LIBRARY.write_text(json.dumps(library, indent=2))
    OUT_STATS.write_text(json.dumps(stats, indent=2))
    print(f"Wrote {OUT_LIBRARY.relative_to(REPO)}  ({len(archetypes)} archetypes)")
    print(f"Wrote {OUT_STATS.relative_to(REPO)}")
    print()
    print("=== STATS ===")
    print(f"Videos: {stats['total_videos']}   Shots: {stats['total_shots']}   Archetypes: {stats['total_archetypes']}")
    print(f"Avg shots/video: {stats['avg_shots_per_video']}  Avg video duration: {stats['avg_video_duration']}s")
    print(f"Shot duration (s): min={stats['shot_duration_histogram']['min']} "
          f"p25={stats['shot_duration_histogram']['p25']} "
          f"p50={stats['shot_duration_histogram']['p50']} "
          f"p75={stats['shot_duration_histogram']['p75']} "
          f"max={stats['shot_duration_histogram']['max']}")
    print()
    print("Framing distribution:")
    for k, v in stats["framing_distribution"].items():
        print(f"  {k:24s} {v:3d}")
    print()
    print("Environment distribution:")
    for k, v in stats["environment_distribution"].items():
        print(f"  {k:24s} {v:3d}")
    print()
    print("Top 15 archetypes by instance count:")
    for a in archetypes[:15]:
        print(f"  {a['instance_count']:2d}  {a['id']:50s} avg={a['duration_avg']:4.2f}s")


if __name__ == "__main__":
    main()
