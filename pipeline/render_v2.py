"""
render_v2.py — Enhanced sub-pixel renderer with depth-based parallax and cinematic filters.

Improvements over render_smooth.py:
1. DEPTH-BASED PARALLAX (the big one)
   Uses Depth Anything v2 maps to give closer parts of the image MORE motion than
   distant parts. Real cameras do this naturally — it's what makes them feel 3D.
   Implementation: cv2.remap with depth-displaced source coordinates.

2. CINEMATIC POST-PROCESSING per frame:
   - Easing curves (smoothstep) for natural motion ramps
   - Bloom / glow on bright specular highlights
   - Subtle color grade (lift shadows, warm/cool split)
   - Vignette
   - Slight unsharp mask to recover micro-detail
   - Film grain (the #1 fake-tell killer for AI imagery)

3. MOTION SCALE parameter
   --scale 1.0 → match wine ferrari original (default)
   --scale 1.5 → 50% more dramatic
   --scale 2.0 → twice as dramatic

Usage:
  python render_v2.py all <stills_dir> <depth_dir> <clips_dir> <final.mp4> [--scale 1.5]
  python render_v2.py shot <n> <still> <depth.npy> <out_dir> [--scale 1.5]
"""
import sys, os, subprocess, argparse, json
import cv2
import numpy as np

OUT_W = 1080
OUT_H = 1920
FPS = 24
FFMPEG = "/opt/homebrew/bin/ffmpeg"

# Default path to the ground-truth motion table (wine ferrari).
DEFAULT_MOTION_TABLE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "motion_table.json"
)


def _load_motion_table(path: str) -> dict[int, dict]:
    """Load per-shot motion specs from a motion_table.json file.

    Returns a dict keyed by integer shot_id. Each value has keys
    ``dur, frames, z0, z1, tx, ty`` matching the legacy renderer schema.

    The motion table is the single source of truth for N (shot count).
    Phase 2 removed the hardcoded 8-shot SHOTS dict that used to live here.
    """
    with open(path) as f:
        data = json.load(f)
    shots_list = data.get("shots", [])
    result: dict[int, dict] = {}
    for entry in shots_list:
        shot_id = int(entry["id"])
        motion = entry.get("motion", {})
        duration = float(entry.get("duration", 0.0))
        frame_count = int(entry.get("frame_count", round(duration * FPS)))
        result[shot_id] = {
            "dur": duration,
            "frames": frame_count,
            "z0": float(motion.get("zoom_start", 1.0)),
            "z1": float(motion.get("zoom_end", 1.0)),
            "tx": float(motion.get("tx_px_1080", 0.0)),
            "ty": float(motion.get("ty_px_1080", 0.0)),
        }
    return result


# Loaded lazily by render_all / render_shot so test-only imports don't hit disk.
SHOTS: dict[int, dict] = {}

# ============================================================
# Easing
# ============================================================

def ease_in_out(t):
    """Smoothstep — t^2 * (3 - 2t). Natural ease in and out."""
    return t * t * (3.0 - 2.0 * t)

# ============================================================
# Depth-based parallax warping
# ============================================================

def render_frame_parallax(src, depth, n, N, z0, z1, tx_out, ty_out,
                           out_w=OUT_W, out_h=OUT_H,
                           depth_intensity=2.5, easing=True,
                           motion_scale=1.0):
    """
    Render output frame n by warping the source still with PERSPECTIVE-CORRECT
    inverse-depth parallax (the math used by real cameras).

    Real cameras follow: pixel_shift = focal × dx_world / z
    So a pixel at depth z=1 shifts twice as much as a pixel at z=2.
    This is what produces the "camera moving past stuff" feel — close objects
    sweep dramatically while far objects barely move.

    Args:
        src: source still image (H, W, 3) uint8
        depth: depth map (H, W) float32 in [0, 1]; 1=closest, 0=farthest
        n, N: current frame index, total frames
        z0, z1: zoom start/end
        tx_out, ty_out: motion in output pixels at out_w
        depth_intensity: how dramatically near pixels move vs far pixels.
                         1.0 = no parallax (uniform shift)
                         2.0 = closest pixel shifts 2× the farthest
                         2.5 = closest 2.5× — visible 3D feel (default)
                         4.0 = strong 3D, possible artifacts at depth edges
                         6.0 = dramatic, near pixels almost detach
        easing: smoothstep curve on motion
        motion_scale: multiplier for tx/ty/zoom (1.0=baseline)
    """
    src_h, src_w = src.shape[:2]
    if N <= 1:
        t = 0.0
    else:
        t = n / (N - 1)
        if easing:
            t = ease_in_out(t)

    # Apply motion scale to magnitudes
    tx_scaled = tx_out * motion_scale
    ty_scaled = ty_out * motion_scale
    z0s = 1.0 + (z0 - 1.0) * motion_scale
    z1s = 1.0 + (z1 - 1.0) * motion_scale
    z = z0s + (z1s - z0s) * t

    # Convert output-pixel motion to source-pixel motion
    src_per_out = src_w / (out_w * z)
    tx_src = tx_scaled * t * src_per_out
    ty_src = ty_scaled * t * src_per_out

    # Visible source region size
    visible_w = src_w / z
    visible_h = src_h / z

    # Center of visible region — the BASE camera position (assumes pixels at infinity)
    cx = src_w / 2 + tx_src
    cy = src_h / 2 + ty_src

    # Build base inverse map (output → source)
    yy, xx = np.meshgrid(np.arange(out_h, dtype=np.float32),
                          np.arange(out_w, dtype=np.float32),
                          indexing='ij')
    map_x = (cx - visible_w / 2) + xx * (visible_w / out_w)
    map_y = (cy - visible_h / 2) + yy * (visible_h / out_h)

    # Sample depth at base sample positions
    cx_idx = np.clip(map_x.astype(np.int32), 0, src_w - 1)
    cy_idx = np.clip(map_y.astype(np.int32), 0, src_h - 1)
    d_at_pixel = depth[cy_idx, cx_idx]  # 0..1, 1=closest

    # PERSPECTIVE-CORRECT inverse-depth parallax
    # Map depth d ∈ [0,1] to a virtual z coordinate:
    #   d=0 (far)   → z=1.0 (baseline distance)
    #   d=1 (close) → z=1/depth_intensity (closer to camera)
    # Then perspective_mult = baseline_z / pixel_z = 1 / pixel_z (since baseline=1)
    # This means closest pixels get multiplied by depth_intensity, farthest get 1.0
    z_norm = 1.0 - d_at_pixel * (1.0 - 1.0 / depth_intensity)
    perspective_mult = 1.0 / z_norm  # in [1.0, depth_intensity]

    # Apply: extra shift on top of base = (mult - 1) * base
    # So far pixels get base shift only, close pixels get base × mult
    extra_factor = perspective_mult - 1.0
    map_x_p = map_x + tx_src * extra_factor
    map_y_p = map_y + ty_src * extra_factor

    out = cv2.remap(src, map_x_p, map_y_p,
                     interpolation=cv2.INTER_LANCZOS4,
                     borderMode=cv2.BORDER_REPLICATE)
    return out

# ============================================================
# Cinematic post-processing filters
# ============================================================

def filter_bloom(img, threshold=180, strength=0.35, blur_radius=25):
    """Add bloom/glow on bright pixels (specular highlights on car paint)."""
    img_f = img.astype(np.float32)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # Soft threshold: anything over `threshold` contributes to bloom
    soft_mask = np.clip((gray - threshold) / (255 - threshold), 0, 1)
    bright = img_f * soft_mask[..., None]
    blurred = cv2.GaussianBlur(bright, (0, 0), blur_radius)
    out = img_f + blurred * strength
    return np.clip(out, 0, 255).astype(np.uint8)

def filter_color_grade(img):
    """Subtle teal-orange split: warm in highlights, cool in shadows. Lifted blacks. Mild contrast."""
    img_f = img.astype(np.float32) / 255.0
    # Slight gamma lift for shadows
    img_f = np.power(img_f, 0.95)
    # Compute luminance for splitting
    lum = 0.2126 * img_f[..., 2] + 0.7152 * img_f[..., 1] + 0.0722 * img_f[..., 0]
    # Warm in highlights (push red+green up where lum is high)
    highlight_mask = np.clip((lum - 0.5) * 2, 0, 1)
    img_f[..., 2] += highlight_mask * 0.04  # red
    img_f[..., 1] += highlight_mask * 0.02  # green
    # Cool in shadows (push blue up where lum is low)
    shadow_mask = np.clip((0.5 - lum) * 2, 0, 1)
    img_f[..., 0] += shadow_mask * 0.04  # blue
    # Mild contrast S-curve
    img_f = (img_f - 0.5) * 1.05 + 0.5
    return np.clip(img_f * 255, 0, 255).astype(np.uint8)

def filter_vignette(img, strength=0.25):
    """Subtle darkening at corners — deepens the frame."""
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2.0, H / 2.0
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - np.power(dist / max_dist, 2.0) * strength
    return np.clip(img.astype(np.float32) * vignette[..., None], 0, 255).astype(np.uint8)

def filter_unsharp(img, strength=0.4, radius=1.2):
    """Slight sharpen to recover micro-detail lost in lanczos warp."""
    blurred = cv2.GaussianBlur(img, (0, 0), radius)
    sharp = img.astype(np.float32) + (img.astype(np.float32) - blurred.astype(np.float32)) * strength
    return np.clip(sharp, 0, 255).astype(np.uint8)

def filter_grain(img, strength=0.018):
    """Add subtle film grain. Single most impactful AI-tell killer."""
    noise = np.random.randn(*img.shape[:2], 1).astype(np.float32) * 255 * strength
    out = img.astype(np.float32) + noise  # broadcast across channels for monochromatic grain
    return np.clip(out, 0, 255).astype(np.uint8)

def post_process(img, enable_sharpen=True, enable_bloom=True,
                 enable_grade=False, enable_vignette=False, enable_grain=False):
    """Apply the post-processing chain.

    DEFAULT (clean): sharpen + bloom only — restores micro-detail and lets
    specular highlights bleed naturally without adding stylization.

    OPT-IN stylized filters: grade, vignette, grain — enable these for a
    'cinematic film stock' look. Off by default to match clean studio CGI.
    """
    if enable_sharpen:
        img = filter_unsharp(img)
    if enable_bloom:
        img = filter_bloom(img)
    if enable_grade:
        img = filter_color_grade(img)
    if enable_vignette:
        img = filter_vignette(img)
    if enable_grain:
        img = filter_grain(img)
    return img

# ============================================================
# Per-shot rendering
# ============================================================

def render_shot(shot_num, still_path, depth_path, out_dir,
                 motion_scale=1.0, easing=True, parallax=True,
                 depth_intensity=2.5, crf=20,
                 enable_grade=False, enable_vignette=False, enable_grain=False):
    if shot_num not in SHOTS:
        raise ValueError(f"Unknown shot {shot_num}")
    s = SHOTS[shot_num]
    src = cv2.imread(still_path)
    if src is None:
        raise FileNotFoundError(still_path)

    if parallax:
        depth = np.load(depth_path).astype(np.float32)
        if depth.shape[:2] != src.shape[:2]:
            depth = cv2.resize(depth, (src.shape[1], src.shape[0]), interpolation=cv2.INTER_LINEAR)
    else:
        depth = np.zeros(src.shape[:2], dtype=np.float32)

    os.makedirs(out_dir, exist_ok=True)

    di = depth_intensity if parallax else 1.0
    print(f"  Shot {shot_num}: {s['frames']} frames, "
          f"z {s['z0']:.3f}→{s['z1']:.3f}, tx={s['tx']:+}, ty={s['ty']:+} "
          f"[scale={motion_scale}x, depth_intensity={di}]")

    for n in range(s['frames']):
        frame = render_frame_parallax(
            src, depth, n, s['frames'],
            s['z0'], s['z1'],
            s['tx'], s['ty'],
            depth_intensity=di,
            easing=easing,
            motion_scale=motion_scale,
        )
        frame = post_process(frame,
                             enable_grade=enable_grade,
                             enable_vignette=enable_vignette,
                             enable_grain=enable_grain)
        cv2.imwrite(os.path.join(out_dir, f"f{n:04d}.png"),
                    frame, [cv2.IMWRITE_PNG_COMPRESSION, 1])

def encode_clip(frames_dir, output_mp4, crf=20):
    """Encode PNG sequence with x264 tuned for grain.
    crf 18 = master/archival (~130MB for 13s 1080p with grain)
    crf 20 = high quality (~80MB)
    crf 22 = good quality (~40MB) — recommended for delivery
    crf 24 = web/social (~20MB) — Instagram/TikTok optimized
    """
    cmd = [
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "f%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "slow",
        "-tune", "grain",
        "-crf", str(crf),
        "-movflags", "+faststart",
        output_mp4,
        "-hide_banner", "-loglevel", "error"
    ]
    subprocess.run(cmd, check=True)

def concat_clips(clips_dir, final_out, shot_ids=None):
    """Concatenate per-shot clip mp4s into the final video.

    If ``shot_ids`` is None, iterate over the currently loaded SHOTS dict.
    """
    if shot_ids is None:
        shot_ids = sorted(SHOTS.keys())
    list_path = "/tmp/concat_list.txt"
    with open(list_path, "w") as f:
        for i in shot_ids:
            abs_path = os.path.abspath(os.path.join(clips_dir, f"clip{i}.mp4"))
            f.write(f"file '{abs_path}'\n")
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
           "-i", list_path, "-c", "copy", final_out,
           "-hide_banner", "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    print(f"DONE: {final_out}")

def load_per_shot_config(path):
    """Load per-shot config JSON. Returns dict mapping shot_id (int) -> {motion_scale, depth_intensity, ty?, tx?, zoom_start?, zoom_end?}."""
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        cfg = json.load(f)
    result = {}
    for k, v in cfg.get("shots", {}).items():
        try:
            result[int(k)] = v
        except ValueError:
            pass
    return result

def render_all(stills_dir, depth_dir, clips_dir, final_out=None,
               motion_scale=1.0, easing=True, parallax=True,
               depth_intensity=2.5, crf=20,
               enable_grade=False, enable_vignette=False, enable_grain=False,
               per_shot_config=None):
    os.makedirs(clips_dir, exist_ok=True)
    work = os.path.join(clips_dir, "_frames")
    shot_ids = sorted(SHOTS.keys())
    if not shot_ids:
        print("  ERROR: SHOTS is empty — call _load_motion_table() first")
        return False
    for i in shot_ids:
        still = None
        for ext in ("jpg", "png"):
            p = os.path.join(stills_dir, f"shot{i}.{ext}")
            if os.path.exists(p):
                still = p; break
        if not still:
            print(f"  ERROR: missing shot{i} in {stills_dir}")
            return False
        depth_p = os.path.join(depth_dir, f"shot{i}_depth.npy")
        if not os.path.exists(depth_p) and parallax:
            print(f"  WARNING: missing depth for shot{i}, falling back to no-parallax")
            this_parallax = False
        else:
            this_parallax = parallax

        # Resolve per-shot overrides
        cfg = per_shot_config.get(i, {}) if per_shot_config else {}
        shot_scale = cfg.get("motion_scale", motion_scale)
        shot_di = cfg.get("depth_intensity", depth_intensity)
        # Apply optional motion overrides (ty, tx, zoom) by mutating SHOTS temporarily
        original = SHOTS[i].copy()
        for key in ("tx", "ty", "z0", "z1", "zoom_start", "zoom_end"):
            if key in cfg:
                target_key = {"zoom_start": "z0", "zoom_end": "z1"}.get(key, key)
                SHOTS[i][target_key] = cfg[key]

        frames_dir = os.path.join(work, f"shot{i}")
        render_shot(i, still, depth_p, frames_dir,
                    motion_scale=shot_scale, easing=easing,
                    parallax=this_parallax, depth_intensity=shot_di,
                    enable_grade=enable_grade,
                    enable_vignette=enable_vignette,
                    enable_grain=enable_grain)
        SHOTS[i] = original  # restore
        clip_path = os.path.join(clips_dir, f"clip{i}.mp4")
        encode_clip(frames_dir, clip_path, crf=crf)
        print(f"    → {clip_path}")
    if final_out:
        concat_clips(clips_dir, final_out, shot_ids=shot_ids)
    return True

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Enhanced wine ferrari renderer")
    p.add_argument("cmd", choices=["all", "shot", "concat"])
    p.add_argument("args", nargs="+")
    p.add_argument("--scale", type=float, default=1.0,
                   help="Motion magnitude scale (1.0=baseline, 1.5=dramatic, 2.0=double)")
    p.add_argument("--no-parallax", action="store_true", help="Disable depth parallax (uniform shift)")
    p.add_argument("--no-easing", action="store_true", help="Linear motion (no smoothstep ease)")
    p.add_argument("--depth-intensity", type=float, default=2.5,
                   help="Perspective parallax intensity. 1=flat, 2=subtle 3D, 2.5=default, 4=strong, 6=dramatic")
    p.add_argument("--crf", type=int, default=20,
                   help="Quality: 18=master/big, 20=high, 22=delivery, 24=social/small")
    # Stylized filters (off by default — clean studio look)
    p.add_argument("--grade", action="store_true", help="Enable color grade (teal-orange split)")
    p.add_argument("--vignette", action="store_true", help="Enable corner vignette")
    p.add_argument("--grain", action="store_true", help="Enable film grain")
    p.add_argument("--cinematic", action="store_true",
                   help="Enable all stylized filters (grade + vignette + grain)")
    p.add_argument("--config", type=str, default=None,
                   help="Path to per-shot config JSON (overrides --scale and --depth-intensity per shot)")
    p.add_argument("--frames", type=str, default=None,
                   help="Comma-separated frame counts (one per shot) overriding SHOTS[i]['frames']. "
                        "Used by audio sync to retarget shot durations to musical beats.")
    p.add_argument("--motion-table", type=str, default=DEFAULT_MOTION_TABLE,
                   help="Path to motion_table.json — single source of truth for N shots "
                        "and their per-shot motion specs. Defaults to the wine ferrari table.")
    args = p.parse_args()

    # Load motion table before anything else: it defines N.
    loaded_shots = _load_motion_table(args.motion_table)
    if not loaded_shots:
        print(f"ERROR: no shots loaded from {args.motion_table}", file=sys.stderr)
        sys.exit(2)
    SHOTS.clear()
    SHOTS.update(loaded_shots)
    print(f"Loaded motion table: {args.motion_table} — {len(SHOTS)} shots "
          f"({sorted(SHOTS.keys())})")

    if args.frames:
        overrides = [int(x) for x in args.frames.split(",") if x.strip()]
        if len(overrides) != len(SHOTS):
            print(f"ERROR: --frames must have {len(SHOTS)} values, got {len(overrides)}",
                  file=sys.stderr)
            sys.exit(2)
        for shot_id, fc in zip(sorted(SHOTS.keys()), overrides):
            SHOTS[shot_id]["frames"] = max(1, fc)
            SHOTS[shot_id]["dur"] = SHOTS[shot_id]["frames"] / FPS
        print(f"Frame count override applied: {overrides} (total {sum(overrides)} frames, "
              f"{sum(overrides)/FPS:.2f}s)")

    enable_grade = args.grade or args.cinematic
    enable_vignette = args.vignette or args.cinematic
    enable_grain = args.grain or args.cinematic
    per_shot_cfg = load_per_shot_config(args.config) if args.config else None
    if per_shot_cfg:
        print(f"Loaded per-shot config from {args.config} ({len(per_shot_cfg)} shots)")

    if args.cmd == "all":
        if len(args.args) < 3:
            print("Usage: render_v2.py all <stills_dir> <depth_dir> <clips_dir> [final.mp4]")
            sys.exit(1)
        stills = args.args[0]
        depths = args.args[1]
        clips  = args.args[2]
        final  = args.args[3] if len(args.args) > 3 else None
        render_all(stills, depths, clips, final,
                   motion_scale=args.scale,
                   easing=not args.no_easing,
                   parallax=not args.no_parallax,
                   depth_intensity=args.depth_intensity,
                   crf=args.crf,
                   enable_grade=enable_grade,
                   enable_vignette=enable_vignette,
                   enable_grain=enable_grain,
                   per_shot_config=per_shot_cfg)
    elif args.cmd == "concat":
        concat_clips(args.args[0], args.args[1])
    elif args.cmd == "shot":
        n = int(args.args[0])
        still = args.args[1]
        depth = args.args[2]
        out = args.args[3]
        render_shot(n, still, depth, out,
                    motion_scale=args.scale,
                    easing=not args.no_easing,
                    parallax=not args.no_parallax,
                    depth_intensity=args.depth_intensity,
                    crf=args.crf,
                    enable_grade=enable_grade,
                    enable_vignette=enable_vignette,
                    enable_grain=enable_grain)
