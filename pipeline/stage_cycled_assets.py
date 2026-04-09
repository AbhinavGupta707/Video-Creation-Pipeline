#!/usr/bin/env python
"""
Build a staged asset directory with N shots by cycling the wine ferrari 8-shot base.
Produces: <staging>/stills/, <staging>/depths/, <staging>/motion_table.json

Usage:
  python stage_cycled_assets.py <n_shots> <staging_dir>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
BASE_STILLS = PIPELINE / "test_stills"
BASE_DEPTHS = PIPELINE / "depth_maps"
BASE_MOTION = PIPELINE / "motion_table.json"


def main(n: int, staging: Path) -> None:
    stills_out = staging / "stills"
    depths_out = staging / "depths"
    stills_out.mkdir(parents=True, exist_ok=True)
    depths_out.mkdir(parents=True, exist_ok=True)

    base_motion = json.loads(BASE_MOTION.read_text())
    base_shots = base_motion["shots"]
    base_n = len(base_shots)

    cycled_shots: list[dict] = []
    for new_id in range(1, n + 1):
        src_idx = ((new_id - 1) % base_n) + 1
        src_still = BASE_STILLS / f"shot{src_idx}.jpg"
        dst_still = stills_out / f"shot{new_id}.jpg"
        shutil.copy(src_still, dst_still)

        src_depth = BASE_DEPTHS / f"shot{src_idx}_depth.npy"
        dst_depth = depths_out / f"shot{new_id}_depth.npy"
        shutil.copy(src_depth, dst_depth)

        shot_obj = dict(base_shots[src_idx - 1])
        shot_obj["id"] = new_id
        cycled_shots.append(shot_obj)

    cycled_motion = dict(base_motion)
    cycled_motion["shots"] = cycled_shots
    (staging / "motion_table.json").write_text(json.dumps(cycled_motion, indent=2))
    print(f"Staged {n} shots in {staging}")


if __name__ == "__main__":
    main(int(sys.argv[1]), Path(sys.argv[2]))
