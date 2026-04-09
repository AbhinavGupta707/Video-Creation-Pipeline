"""Auto-generate a starter per_shot_config.json from an analyzed motion_table.

Rules:
  conf >= 0.7           motion_scale 1.0, depth_intensity 2.5 (default)
  0.4 <= conf < 0.7     motion_scale 1.0, depth_intensity 2.0 (less aggressive parallax)
  conf < 0.4            motion_scale 0.8, depth_intensity 1.0 (play it safe, no parallax)

Shots flagged with a note so a human reviewer knows which need QuickTime
verification before locking for publication.

Usage:
  python generate_per_shot_config.py <work_dir>
  -> writes <work_dir>/per_shot_config.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def generate(work_dir: str) -> dict:
    p = Path(work_dir)
    mt_path = p / "motion_table.json"
    if not mt_path.exists():
        raise FileNotFoundError(f"{mt_path} not found")
    data = json.loads(mt_path.read_text())
    shots = data.get("shots", [])

    config = {
        "_comment": f"Auto-generated starter config for {Path(data.get('source_video', '?')).name}. "
                    "Shots with confidence < 0.7 are flagged — verify with QuickTime arrow-key "
                    "frame stepping before locking.",
        "default_motion_scale": 1.0,
        "default_depth_intensity": 2.5,
        "shots": {},
    }

    for s in shots:
        i = int(s["id"])
        conf = float(s.get("_flow_confidence", 0.0))
        motion_type = s.get("motion", {}).get("type", "?")
        if conf >= 0.7:
            config["shots"][str(i)] = {
                "motion_scale": 1.0,
                "depth_intensity": 2.5,
                "_note": f"auto: high confidence ({conf:.2f}), {motion_type}",
            }
        elif conf >= 0.4:
            config["shots"][str(i)] = {
                "motion_scale": 1.0,
                "depth_intensity": 2.0,
                "_note": f"auto: medium confidence ({conf:.2f}), parallax softened. {motion_type}. VERIFY.",
            }
        else:
            config["shots"][str(i)] = {
                "motion_scale": 0.8,
                "depth_intensity": 1.0,
                "_note": f"auto: LOW confidence ({conf:.2f}), parallax disabled, motion dampened. {motion_type}. MANUAL TUNING REQUIRED.",
            }

    out = p / "per_shot_config.json"
    out.write_text(json.dumps(config, indent=2))
    print(f"  -> {out}")
    # Summary
    n_ok = sum(1 for s in shots if s.get("_flow_confidence", 0) >= 0.7)
    n_warn = sum(1 for s in shots if 0.4 <= s.get("_flow_confidence", 0) < 0.7)
    n_bad = sum(1 for s in shots if s.get("_flow_confidence", 0) < 0.4)
    print(f"  confidence: {n_ok} ok / {n_warn} warn / {n_bad} bad")
    return config


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_per_shot_config.py <work_dir>")
        sys.exit(1)
    generate(sys.argv[1])
