"""
Sub-pixel smooth renderer for the wine ferrari recreation pipeline.
Replaces ffmpeg zoompan (which has integer-pixel stepping artifacts)
with cv2.warpAffine using floating-point affine matrices and lanczos
interpolation. Produces mathematically exact sub-pixel motion.

Usage:
  python render_smooth.py <shot_number> <input_still> <output_dir_for_frames>
  python render_smooth.py all <stills_dir> <output_clips_dir>

Each shot renders a PNG sequence into a per-shot subdirectory, then
encodes it to mp4 using ffmpeg (which is lossless from PNGs).
"""
import sys, os, subprocess, json
import cv2
import numpy as np

OUT_W = 1080
OUT_H = 1920
FPS = 24
FFMPEG = "/opt/homebrew/bin/ffmpeg"

# All motion specs in OUTPUT pixel space (1080w). render_frame converts to source space internally.
# Format: (duration_seconds, frame_count, z_start, z_end, tx_out_px, ty_out_px)
# tx > 0 = camera right (visible window slides right), ty > 0 = camera down, z increase = push-in
SHOTS = {
    1: {"dur": 2.262, "frames": 54, "z0": 1.000, "z1": 1.035, "tx": 0,   "ty": 0},
    2: {"dur": 2.261, "frames": 54, "z0": 1.030, "z1": 1.000, "tx": 15,  "ty": 0},
    3: {"dur": 2.179, "frames": 52, "z0": 1.000, "z1": 1.019, "tx": 12,  "ty": -5},
    4: {"dur": 2.180, "frames": 52, "z0": 1.000, "z1": 1.005, "tx": 0,   "ty": -8},
    5: {"dur": 0.904, "frames": 22, "z0": 1.000, "z1": 1.006, "tx": 0,   "ty": -3},
    6: {"dur": 1.152, "frames": 28, "z0": 1.000, "z1": 1.011, "tx": 12,  "ty": 5},
    7: {"dur": 1.069, "frames": 26, "z0": 1.000, "z1": 1.013, "tx": 5,   "ty": 0},
    8: {"dur": 1.181, "frames": 28, "z0": 1.000, "z1": 1.025, "tx": -22, "ty": -6},
}

def ease_in_out(t):
    """Smoothstep easing — gives a more natural feel than linear ramps for camera moves."""
    return t * t * (3 - 2 * t)

def render_frame(src, n, N, z0, z1, tx_out, ty_out, easing=True, out_w=OUT_W, out_h=OUT_H):
    """
    Render output frame n (0..N-1) by warping the source still.
    Returns (out_h, out_w, 3) uint8 image.

    Math:
    - Compute t = n/(N-1), apply easing
    - Interpolate zoom z(t), translation (tx, ty)
    - The output is a window of size (out_w/zoom_relative, out_h/zoom_relative) from the source,
      centered on (src_w/2 + tx_src, src_h/2 + ty_src), scaled to (out_w, out_h)
    - We use cv2.warpAffine with the inverse mapping
    """
    src_h, src_w = src.shape[:2]
    if N <= 1:
        t = 0.0
    else:
        t = n / (N - 1)
        if easing:
            t = ease_in_out(t)

    # Interpolated values
    z = z0 + (z1 - z0) * t
    # Convert output-pixel translation to source-pixel translation
    # The "base scale" maps src to output: scale_base = out_w / src_w
    # At zoom z, the visible region of the source has width src_w/z
    # That visible region maps to out_w pixels of output
    # So 1 source px = (out_w / (src_w/z)) = (out_w * z / src_w) output px
    # Inverse: 1 output px = src_w / (out_w * z) source px
    src_per_out = src_w / (out_w * z)
    tx_src = tx_out * t * src_per_out
    ty_src = ty_out * t * src_per_out

    # Center of the visible source region
    cx = src_w / 2 + tx_src
    cy = src_h / 2 + ty_src

    # Visible source region size
    visible_w = src_w / z
    visible_h = src_h / z

    # Top-left of visible region in source coordinates
    x0 = cx - visible_w / 2
    y0 = cy - visible_h / 2

    # Build affine matrix that maps source -> output
    # Mapping: out_x = (src_x - x0) * out_w / visible_w
    #          out_y = (src_y - y0) * out_h / visible_h
    sx = out_w / visible_w
    sy = out_h / visible_h
    M = np.array([
        [sx, 0,  -x0 * sx],
        [0,  sy, -y0 * sy],
    ], dtype=np.float64)

    # warpAffine with high-quality interpolation
    out = cv2.warpAffine(src, M, (out_w, out_h),
                          flags=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REPLICATE)
    return out

def render_shot(shot_num, input_still_path, output_dir, easing=True):
    if shot_num not in SHOTS:
        raise ValueError(f"Unknown shot {shot_num}")
    s = SHOTS[shot_num]
    src = cv2.imread(input_still_path)
    if src is None:
        raise FileNotFoundError(input_still_path)
    os.makedirs(output_dir, exist_ok=True)

    print(f"  Rendering shot {shot_num}: {s['frames']} frames, "
          f"z {s['z0']:.3f}→{s['z1']:.3f}, "
          f"tx={s['tx']:+}, ty={s['ty']:+}")

    for n in range(s['frames']):
        frame = render_frame(src, n, s['frames'],
                             s['z0'], s['z1'],
                             s['tx'], s['ty'],
                             easing=easing)
        cv2.imwrite(os.path.join(output_dir, f"f{n:04d}.png"), frame,
                    [cv2.IMWRITE_PNG_COMPRESSION, 1])

def encode_clip(frames_dir, output_mp4):
    """Encode PNG sequence to mp4 with high quality."""
    cmd = [
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "f%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "slow",
        "-crf", "16",
        "-movflags", "+faststart",
        output_mp4,
        "-hide_banner", "-loglevel", "error"
    ]
    subprocess.run(cmd, check=True)

def render_all(stills_dir, output_clips_dir, easing=False):
    os.makedirs(output_clips_dir, exist_ok=True)
    work_dir = os.path.join(output_clips_dir, "_frames")
    for i in range(1, 9):
        still = os.path.join(stills_dir, f"shot{i}.jpg")
        if not os.path.exists(still):
            still = os.path.join(stills_dir, f"shot{i}.png")
        if not os.path.exists(still):
            print(f"ERROR: missing {stills_dir}/shot{i}.jpg or .png")
            return False
        frames_dir = os.path.join(work_dir, f"shot{i}")
        render_shot(i, still, frames_dir, easing=easing)
        clip_path = os.path.join(output_clips_dir, f"clip{i}.mp4")
        encode_clip(frames_dir, clip_path)
        print(f"  → {clip_path}")
    return True

def concat_clips(clips_dir, final_out):
    list_path = "/tmp/concat_list.txt"
    with open(list_path, "w") as f:
        for i in range(1, 9):
            abs_path = os.path.abspath(os.path.join(clips_dir, f"clip{i}.mp4"))
            f.write(f"file '{abs_path}'\n")
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0",
           "-i", list_path, "-c", "copy", final_out,
           "-hide_banner", "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    print(f"DONE: {final_out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "all":
        if len(sys.argv) < 4:
            print("Usage: render_smooth.py all <stills_dir> <output_clips_dir> [final.mp4]")
            sys.exit(1)
        stills, clips_out = sys.argv[2], sys.argv[3]
        ok = render_all(stills, clips_out)
        if ok and len(sys.argv) >= 5:
            concat_clips(clips_out, sys.argv[4])
    elif cmd == "concat":
        concat_clips(sys.argv[2], sys.argv[3])
    elif cmd.isdigit():
        shot_num = int(cmd)
        in_still, out_dir = sys.argv[2], sys.argv[3]
        render_shot(shot_num, in_still, out_dir)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
