#!/usr/bin/env python
"""
new_brief.py — Scaffold a new car showcase brief directory.

Interactive CLI that creates the directory structure and starter files
for a new car brief. Generates brief.json with the standard shot sequence,
then auto-generates motion.json via generate_motion.py.

Usage:
  python pipeline/new_brief.py briefs/blue_porsche_gt3/
  python pipeline/new_brief.py briefs/blue_porsche_gt3/ --shots 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import generate_motion from sibling module
PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR.parent))
from pipeline.generate_motion import generate as generate_motion

# Standard shot sequences — proven playback orders.
SHOT_SEQUENCE_8 = [
    {"playback_order": 1, "archetype": "wide_front_3q_right",
     "shot_name": "front 3/4 right wide establishing",
     "camera_clock": "2 o'clock", "lens_height_cm": 70, "lens_mm": 35,
     "subject_distance_m": 6.0, "is_detail": False,
     "derived_from_playback": []},
    {"playback_order": 2, "archetype": "wide_side_profile",
     "shot_name": "pure side profile showing the LEFT flank",
     "camera_clock": "9 o'clock", "lens_height_cm": 90, "lens_mm": 50,
     "subject_distance_m": 8.0, "is_detail": False,
     "derived_from_playback": [1]},
    {"playback_order": 3, "archetype": "signature_detail",
     "shot_name": "signature detail close-up",
     "camera_clock": "TBD — depends on signature element location",
     "lens_height_cm": 30, "lens_mm": 85, "subject_distance_m": 1.5,
     "is_detail": True, "derived_from_playback": [4]},
    {"playback_order": 4, "archetype": "wide_rear_3q",
     "shot_name": "rear 3/4 right low hero",
     "camera_clock": "5 o'clock", "lens_height_cm": 40, "lens_mm": 35,
     "subject_distance_m": 5.0, "is_detail": False,
     "derived_from_playback": [1, 2, 8]},
    {"playback_order": 5, "archetype": "wheel_detail",
     "shot_name": "front-right wheel and brake caliper detail",
     "camera_clock": "2-3 o'clock ground level",
     "lens_height_cm": 15, "lens_mm": 85, "subject_distance_m": 1.5,
     "is_detail": True, "derived_from_playback": [1, 8]},
    {"playback_order": 6, "archetype": "front_detail",
     "shot_name": "angled front headlight and nose detail",
     "camera_clock": "1-2 o'clock low",
     "lens_height_cm": 40, "lens_mm": 85, "subject_distance_m": 1.8,
     "is_detail": True, "derived_from_playback": [1]},
    {"playback_order": 7, "archetype": "wide_front_3q_left",
     "shot_name": "front 3/4 LEFT wide (mirror of shot 1)",
     "camera_clock": "10 o'clock", "lens_height_cm": 70, "lens_mm": 35,
     "subject_distance_m": 6.0, "is_detail": False,
     "derived_from_playback": [1, 2, 8]},
    {"playback_order": 8, "archetype": "wide_dead_front",
     "shot_name": "dead-front hero symmetric",
     "camera_clock": "12 o'clock", "lens_height_cm": 85, "lens_mm": 50,
     "subject_distance_m": 6.0, "is_detail": False,
     "derived_from_playback": [1]},
]

SHOT_SEQUENCE_10 = SHOT_SEQUENCE_8[:4] + [
    {"playback_order": 5, "archetype": "wide_rear_3q_left",
     "shot_name": "rear 3/4 left hero (mirrors shot 4)",
     "camera_clock": "7 o'clock", "lens_height_cm": 40, "lens_mm": 35,
     "subject_distance_m": 5.0, "is_detail": False,
     "derived_from_playback": [4, 8]},
    {"playback_order": 6, "archetype": "wheel_detail",
     "shot_name": "front-right wheel and brake caliper detail",
     "camera_clock": "2-3 o'clock ground level",
     "lens_height_cm": 15, "lens_mm": 85, "subject_distance_m": 1.5,
     "is_detail": True, "derived_from_playback": [1, 8]},
    {"playback_order": 7, "archetype": "front_detail",
     "shot_name": "angled front headlight and nose detail",
     "camera_clock": "1-2 o'clock low",
     "lens_height_cm": 40, "lens_mm": 85, "subject_distance_m": 1.8,
     "is_detail": True, "derived_from_playback": [1]},
    {"playback_order": 8, "archetype": "rear_detail",
     "shot_name": "rear taillight and diffuser detail",
     "camera_clock": "5-6 o'clock low",
     "lens_height_cm": 30, "lens_mm": 85, "subject_distance_m": 1.5,
     "is_detail": True, "derived_from_playback": [4]},
    {"playback_order": 9, "archetype": "wide_front_3q_left",
     "shot_name": "front 3/4 LEFT wide (mirror of shot 1)",
     "camera_clock": "10 o'clock", "lens_height_cm": 70, "lens_mm": 35,
     "subject_distance_m": 6.0, "is_detail": False,
     "derived_from_playback": [1, 2, 8]},
    {"playback_order": 10, "archetype": "wide_dead_front",
     "shot_name": "dead-front hero symmetric",
     "camera_clock": "12 o'clock", "lens_height_cm": 85, "lens_mm": 50,
     "subject_distance_m": 6.0, "is_detail": False,
     "derived_from_playback": [1]},
]


def prompt_input(label: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val if val else default


def scaffold(brief_dir: Path, *, shot_count: int = 8) -> None:
    """Create brief directory with starter files."""
    if brief_dir.exists() and (brief_dir / "brief.json").exists():
        sys.exit(f"ERROR: {brief_dir / 'brief.json'} already exists")

    brief_dir.mkdir(parents=True, exist_ok=True)
    (brief_dir / "Final Images").mkdir(exist_ok=True)

    print(f"\nNew brief: {brief_dir.name}")
    print(f"Shot count: {shot_count}")
    print("=" * 50)
    print("\nCar details:")

    full_name = prompt_input("Full name (e.g. Porsche 911 GT3 RS)")
    short_name = prompt_input("Short name (e.g. Porsche)", full_name.split()[0])
    body_desc = prompt_input("Body description (one paragraph)")
    not_cars_raw = prompt_input("Visually similar cars to exclude (comma-separated)",
                                "McLaren, Ferrari")
    not_cars = [c.strip() for c in not_cars_raw.split(",") if c.strip()]

    print("\nSignature detail (the car's most photogenic unique element):")
    sig_element = prompt_input("Element (e.g. quad exhaust cluster)")
    sig_location = prompt_input("Location on car (e.g. rear center)")

    print("\nPaint & materials:")
    paint_name = prompt_input("Paint name (e.g. deep wine oxblood pearl)")
    paint_desc = prompt_input("Paint description (include what it is NOT)")
    wheels = prompt_input("Wheel description", "Polished multi-spoke forged wheels")
    calipers = prompt_input("Caliper color", "Red brake calipers")

    print("\nAudio:")
    audio_track = prompt_input("Audio track filename (key in audio_timings_master.json)",
                                "1.mp3")

    # Build shot sequence
    shots = SHOT_SEQUENCE_10 if shot_count == 10 else SHOT_SEQUENCE_8
    # Add composition_notes placeholder
    shots_with_notes = []
    for shot in shots:
        s = dict(shot)
        s["composition_notes"] = "TODO — fill in detailed framing instructions"
        shots_with_notes.append(s)

    brief = {
        "car": {
            "full_name": full_name,
            "short_name": short_name,
            "body_description": body_desc,
            "not_cars": not_cars,
            "signature_detail": {
                "element": sig_element,
                "location": sig_location,
                "why": "TODO — explain why this is the most photogenic detail",
                "visual_description": "TODO — describe what the camera sees",
                "camera_approach": "TODO — describe ideal camera position",
            },
        },
        "paint": {
            "name": paint_name,
            "description": paint_desc,
            "wheels": wheels,
            "calipers": calipers,
            "canopy": "Tinted canopy glass",
        },
        "studio": {
            "description": "Infinite seamless mid-grey (#6a6a6a) cyclorama, evenly lit edge to edge with bright clean even studio lighting",
            "color_temp_k": 5200,
        },
        "audio_track": audio_track,
        "stills_dir": "Final Images",
        "identity_references": {},
        "shots": shots_with_notes,
    }

    brief_path = brief_dir / "brief.json"
    with open(brief_path, "w") as f:
        json.dump(brief, f, indent=2)
        f.write("\n")
    print(f"\n  Created {brief_path}")

    # Auto-generate motion.json
    motion_path = generate_motion(brief_dir, force=True)
    print(f"  Created {motion_path}")

    # Print next steps
    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print(f"  1. Add 2-3 reference photos to {brief_dir}/")
    print(f"  2. Fill in composition_notes and signature_detail in brief.json")
    print(f"  3. Run: python pipeline/generate_prompts.py {brief_dir}/")
    print(f"  4. Generate images using the prompts, save as shot1-{shot_count}.png")
    print(f"     in {brief_dir / 'Final Images/'}")
    print(f"  5. Render: python pipeline/render_brief.py {brief_dir}/ "
          f"--audio \"{audio_track}\" -o output.mp4")


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold a new car showcase brief")
    p.add_argument("brief_dir", type=Path, help="Path for new brief directory")
    p.add_argument("--shots", type=int, default=8, choices=[8, 10],
                   help="Number of shots (8 or 10)")
    args = p.parse_args()
    scaffold(args.brief_dir, shot_count=args.shots)
    return 0


if __name__ == "__main__":
    sys.exit(main())
