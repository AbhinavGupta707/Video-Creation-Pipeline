"""Compute depth maps for every shot still using Depth Anything v2.

Phase 2 update: auto-discovers any number of shots matching ``shot{N}.{jpg,png}``
in the stills directory instead of hardcoding N=8. The renderer will iterate
over whatever shot IDs are present.

Output: one ``shot{N}_depth.npy`` per input still (HxW float32 in [0, 1],
1.0 = closest). Also writes a ``shot{N}_depth_preview.jpg`` visualization.

Usage:
  python compute_depth.py <stills_dir> <depth_output_dir>
"""
from __future__ import annotations

import os
import re
import sys
from glob import glob

import cv2
import numpy as np
from PIL import Image


SHOT_FILE_RE = re.compile(r"shot(\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)


def discover_shots(stills_dir: str) -> list[tuple[int, str]]:
    """Return sorted ``(shot_id, absolute_path)`` tuples for every shot still."""
    found: dict[int, str] = {}
    for path in glob(os.path.join(stills_dir, "shot*")):
        match = SHOT_FILE_RE.search(os.path.basename(path))
        if match is None:
            continue
        shot_id = int(match.group(1))
        # Prefer jpg over png if both exist for the same shot_id
        if shot_id not in found or path.lower().endswith((".jpg", ".jpeg")):
            found[shot_id] = path
    return sorted(found.items())


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: compute_depth.py <stills_dir> <depth_output_dir>")
        sys.exit(1)
    stills_dir = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    shots = discover_shots(stills_dir)
    if not shots:
        print(f"ERROR: no shot*.jpg/png files found in {stills_dir}")
        sys.exit(1)
    print(f"Found {len(shots)} shots: {[i for i, _ in shots]}")

    print("Loading Depth Anything v2 model (first run downloads ~400MB)...")
    import torch
    from transformers import pipeline
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"  Using device: {device}")
    pipe = pipeline(
        task="depth-estimation",
        model="depth-anything/Depth-Anything-V2-Large-hf",
        device=device,
    )
    print("  Model loaded.")

    for shot_id, still_path in shots:
        img = Image.open(still_path).convert("RGB")
        print(
            f"  shot{shot_id}: {img.size[0]}x{img.size[1]} → estimating depth...",
            end=" ",
            flush=True,
        )

        result = pipe(img)
        depth = np.array(result["depth"], dtype=np.float32)
        depth_min, depth_max = float(depth.min()), float(depth.max())
        if depth_max - depth_min > 1e-6:
            depth_norm = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth_norm = np.zeros_like(depth)

        np.save(os.path.join(out_dir, f"shot{shot_id}_depth.npy"), depth_norm)
        depth_vis = (depth_norm * 255).astype(np.uint8)
        depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
        cv2.imwrite(
            os.path.join(out_dir, f"shot{shot_id}_depth_preview.jpg"),
            depth_color,
        )
        print(f"min={depth_min:.2f} max={depth_max:.2f}")

    print(f"\nDone. {len(shots)} depth maps saved to {out_dir}/")

if __name__ == "__main__":
    main()
