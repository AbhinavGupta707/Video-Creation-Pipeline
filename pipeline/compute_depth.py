"""Compute depth maps for every shot still using Depth Anything v2.

Auto-discovers any number of shots matching ``shot{N}.{jpg,png}``
in the stills directory. The renderer will iterate over whatever
shot IDs are present.

Output: one ``shot{N}_depth.npy`` per input still (HxW float32 in [0, 1],
1.0 = closest). Also writes a ``shot{N}_depth_preview.jpg`` visualization.

Supports ``--cache-dir`` for persistent depth map caching across renders.
If a cached depth exists and is newer than the still, it is reused.

Usage:
  python compute_depth.py <stills_dir> <depth_output_dir> [--cache-dir <dir>]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
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
        if shot_id not in found or path.lower().endswith((".jpg", ".jpeg")):
            found[shot_id] = path
    return sorted(found.items())


def _is_cached(still_path: str, cache_dir: str, shot_id: int) -> bool:
    """Return True if cached depth exists and is newer than the still."""
    cached = os.path.join(cache_dir, f"shot{shot_id}_depth.npy")
    if not os.path.exists(cached):
        return False
    return os.path.getmtime(cached) >= os.path.getmtime(still_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute depth maps with Depth Anything v2")
    parser.add_argument("stills_dir", help="Directory containing shot*.jpg/png stills")
    parser.add_argument("out_dir", help="Output directory for depth maps")
    parser.add_argument("--cache-dir", default=None,
                        help="Persistent cache directory. Reuses cached depths if "
                             "newer than the still, saving recomputation time.")
    args = parser.parse_args()

    stills_dir = args.stills_dir
    out_dir = args.out_dir
    cache_dir = args.cache_dir
    os.makedirs(out_dir, exist_ok=True)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    shots = discover_shots(stills_dir)
    if not shots:
        print(f"ERROR: no shot*.jpg/png files found in {stills_dir}")
        sys.exit(1)
    print(f"Found {len(shots)} shots: {[i for i, _ in shots]}")

    # Partition into cached vs needs-compute
    to_compute: list[tuple[int, str]] = []
    cached_count = 0
    for shot_id, still_path in shots:
        if cache_dir and _is_cached(still_path, cache_dir, shot_id):
            # Copy from cache to output
            for suffix in ("_depth.npy", "_depth_preview.jpg"):
                src = os.path.join(cache_dir, f"shot{shot_id}{suffix}")
                dst = os.path.join(out_dir, f"shot{shot_id}{suffix}")
                if os.path.exists(src):
                    shutil.copy2(src, dst)
            print(f"  shot{shot_id}: cached (skipped)")
            cached_count += 1
        else:
            to_compute.append((shot_id, still_path))

    if cached_count > 0:
        print(f"  {cached_count} shots loaded from cache, {len(to_compute)} to compute")

    if not to_compute:
        print(f"\nDone. All {len(shots)} depth maps served from cache → {out_dir}/")
        return

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

    for shot_id, still_path in to_compute:
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

        npy_name = f"shot{shot_id}_depth.npy"
        preview_name = f"shot{shot_id}_depth_preview.jpg"

        np.save(os.path.join(out_dir, npy_name), depth_norm)
        depth_vis = (depth_norm * 255).astype(np.uint8)
        depth_color = cv2.applyColorMap(depth_vis, cv2.COLORMAP_INFERNO)
        cv2.imwrite(os.path.join(out_dir, preview_name), depth_color)

        # Persist to cache
        if cache_dir:
            shutil.copy2(os.path.join(out_dir, npy_name),
                         os.path.join(cache_dir, npy_name))
            shutil.copy2(os.path.join(out_dir, preview_name),
                         os.path.join(cache_dir, preview_name))

        print(f"min={depth_min:.2f} max={depth_max:.2f}")

    print(f"\nDone. {len(shots)} depth maps saved to {out_dir}/")


if __name__ == "__main__":
    main()
