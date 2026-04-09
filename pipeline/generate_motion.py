#!/usr/bin/env python
"""
generate_motion.py — Auto-generate motion.json from brief.json shot archetypes.

Maps each shot archetype to proven default camera motion specs derived from
the wine ferrari ground truth and Czinger 21C briefs. Writes motion.json
to the brief directory. User can tweak values after generation.

Usage:
  python pipeline/generate_motion.py briefs/wine_czinger_21c/
  python pipeline/generate_motion.py briefs/wine_czinger_21c/ --force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Archetype → default motion specs.
# Derived from wine ferrari motion_table.json (ground truth) and Czinger 21C.
# tx/ty in output pixels at 1080w. zoom_start is always 1.000.
ARCHETYPE_DEFAULTS: dict[str, dict] = {
    # --- Wide shots ---
    "wide_front_3q_right": {
        "type": "push-in (zoom)",
        "tx_px_1080": 0, "ty_px_1080": 0,
        "zoom_start": 1.000, "zoom_end": 1.035,
    },
    "wide_front_3q_left": {
        "type": "subtle pan right + push-in",
        "tx_px_1080": 5, "ty_px_1080": 0,
        "zoom_start": 1.000, "zoom_end": 1.015,
    },
    "wide_side_profile": {
        "type": "pan right + gentle push-in",
        "tx_px_1080": 10, "ty_px_1080": 0,
        "zoom_start": 1.000, "zoom_end": 1.020,
    },
    "wide_dead_front": {
        "type": "slight push-in + tiny tilt up",
        "tx_px_1080": 0, "ty_px_1080": -2,
        "zoom_start": 1.000, "zoom_end": 1.008,
    },
    "wide_dead_rear": {
        "type": "slight push-in + tilt up",
        "tx_px_1080": 0, "ty_px_1080": -3,
        "zoom_start": 1.000, "zoom_end": 1.006,
    },
    "wide_rear_3q": {
        "type": "tilt up + slight push-in",
        "tx_px_1080": 0, "ty_px_1080": -8,
        "zoom_start": 1.000, "zoom_end": 1.010,
    },
    "wide_rear_3q_left": {
        "type": "tilt up + slight push-in",
        "tx_px_1080": 0, "ty_px_1080": -8,
        "zoom_start": 1.000, "zoom_end": 1.010,
    },
    # --- Detail shots ---
    "signature_detail": {
        "type": "pan right + tilt up + push-in",
        "tx_px_1080": 12, "ty_px_1080": -5,
        "zoom_start": 1.000, "zoom_end": 1.025,
    },
    "wheel_detail": {
        "type": "dramatic push-in + pan left",
        "tx_px_1080": -15, "ty_px_1080": -3,
        "zoom_start": 1.000, "zoom_end": 1.030,
    },
    "wheel_detail_rear": {
        "type": "push-in + pan left",
        "tx_px_1080": -12, "ty_px_1080": -3,
        "zoom_start": 1.000, "zoom_end": 1.025,
    },
    "front_detail": {
        "type": "pan right + slight down + push-in",
        "tx_px_1080": 12, "ty_px_1080": 5,
        "zoom_start": 1.000, "zoom_end": 1.015,
    },
    "rear_detail": {
        "type": "pan right + tilt up + push-in",
        "tx_px_1080": 10, "ty_px_1080": -5,
        "zoom_start": 1.000, "zoom_end": 1.020,
    },
    "rear_badge_detail": {
        "type": "pan right + tilt up + push-in",
        "tx_px_1080": 8, "ty_px_1080": -4,
        "zoom_start": 1.000, "zoom_end": 1.020,
    },
    # --- Special shots ---
    "interior": {
        "type": "pure push-in",
        "tx_px_1080": 0, "ty_px_1080": 0,
        "zoom_start": 1.000, "zoom_end": 1.020,
    },
    "top_down": {
        "type": "gentle push-in",
        "tx_px_1080": 0, "ty_px_1080": 0,
        "zoom_start": 1.000, "zoom_end": 1.015,
    },
    "extreme_close_up": {
        "type": "pan + dramatic push-in",
        "tx_px_1080": 5, "ty_px_1080": -3,
        "zoom_start": 1.000, "zoom_end": 1.030,
    },
}

# Human-readable purpose per archetype
ARCHETYPE_PURPOSE: dict[str, str] = {
    "wide_front_3q_right": "Establishing shot — sets aesthetic, scale, lighting",
    "wide_front_3q_left": "Near-HERO — climactic alternate angle",
    "wide_side_profile": "Profile reveal — reads silhouette and proportions",
    "wide_dead_front": "Symmetric hero — close on the face",
    "wide_dead_rear": "Symmetric rear — diffuser and exhaust reveal",
    "wide_rear_3q": "Rear hero — wing + haunches + exhaust payoff",
    "wide_rear_3q_left": "Rear symmetry — mirrors rear 3/4 right",
    "signature_detail": "Signature detail — brand/craftsmanship hero beat",
    "wheel_detail": "Wheel hero — caliper + spoke engineering focus",
    "wheel_detail_rear": "Rear wheel — mechanical symmetry",
    "front_detail": "Front detail — headlight hero",
    "rear_detail": "Rear detail — taillight and diffuser focus",
    "rear_badge_detail": "Badge detail — brand identity close-up",
    "interior": "Interior reveal — cockpit and materials",
    "top_down": "Top-down — planform silhouette clarity",
    "extreme_close_up": "Extreme macro — texture and geometry hero",
}


def generate(brief_dir: Path, *, force: bool = False) -> Path:
    """Read brief.json shots, generate motion.json with archetype defaults."""
    brief_path = brief_dir / "brief.json"
    if not brief_path.exists():
        sys.exit(f"ERROR: brief.json not found in {brief_dir}")

    motion_path = brief_dir / "motion.json"
    if motion_path.exists() and not force:
        sys.exit(f"ERROR: motion.json already exists in {brief_dir}. "
                 f"Use --force to overwrite.")

    with open(brief_path) as f:
        brief = json.load(f)

    shots = brief.get("shots", [])
    if not shots:
        sys.exit("ERROR: brief.json has no shots")

    motion_shots: list[dict] = []
    unknown_archetypes: list[str] = []

    for shot in shots:
        archetype = shot["archetype"]
        playback = shot["playback_order"]

        if archetype not in ARCHETYPE_DEFAULTS:
            unknown_archetypes.append(archetype)
            # Fallback: gentle push-in
            defaults = {
                "type": "gentle push-in (unknown archetype)",
                "tx_px_1080": 0, "ty_px_1080": 0,
                "zoom_start": 1.000, "zoom_end": 1.015,
            }
            print(f"  WARNING: unknown archetype '{archetype}' for shot {playback}, "
                  f"using gentle push-in fallback")
        else:
            defaults = ARCHETYPE_DEFAULTS[archetype]

        purpose = ARCHETYPE_PURPOSE.get(archetype, shot.get("shot_name", ""))

        motion_shots.append({
            "id": playback,
            "subject": shot.get("shot_name", ""),
            "camera_position": shot.get("camera_clock", ""),
            "motion": dict(defaults),
            "purpose": purpose,
        })

    motion = {
        "_comment": (
            f"Auto-generated by generate_motion.py from brief.json "
            f"({len(motion_shots)} shots). Frame counts come from "
            f"audio_timings_master.json at render time. "
            f"Tweak motion values as needed."
        ),
        "output_resolution": [1080, 1920],
        "ai_still_resolution": [2160, 3840],
        "shots": motion_shots,
    }

    with open(motion_path, "w") as f:
        json.dump(motion, f, indent=2)
        f.write("\n")

    print(f"Generated {motion_path} ({len(motion_shots)} shots)")
    for s in motion_shots:
        m = s["motion"]
        tx = m["tx_px_1080"]
        ty = m["ty_px_1080"]
        z = m["zoom_end"]
        print(f"  {s['id']:>2d}  {s['subject'][:45]:<45s}  tx={tx:+.0f} ty={ty:+.0f} zoom→{z:.3f}")

    if unknown_archetypes:
        print(f"\n  WARNING: {len(unknown_archetypes)} unknown archetypes used fallback motion")
        print(f"  Known archetypes: {', '.join(sorted(ARCHETYPE_DEFAULTS.keys()))}")

    return motion_path


def main() -> int:
    p = argparse.ArgumentParser(description="Generate motion.json from brief archetypes")
    p.add_argument("brief_dir", type=Path, help="Path to brief directory")
    p.add_argument("--force", action="store_true", help="Overwrite existing motion.json")
    args = p.parse_args()
    generate(args.brief_dir, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
