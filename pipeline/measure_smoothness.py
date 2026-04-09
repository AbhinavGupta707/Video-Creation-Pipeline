"""
Measure motion smoothness across consecutive frames in a clip.
Lower stddev of frame-to-frame differences = smoother motion.
Compares zoompan version vs subpixel version side by side.
"""
import cv2, glob, sys
import numpy as np

def per_frame_motion_variance(clip_path):
    """For each consecutive frame pair, compute median optical flow magnitude.
    Smooth motion should have steady deltas; jittery motion has high variance."""
    cap = cv2.VideoCapture(clip_path)
    deltas = []
    prev = None
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (g.shape[1]//4, g.shape[0]//4))
        if prev is not None:
            # Use Farneback flow median magnitude
            flow = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            mag = np.sqrt(flow[...,0]**2 + flow[...,1]**2)
            deltas.append(float(np.median(mag)))
        prev = g
    cap.release()
    if not deltas: return None
    arr = np.array(deltas)
    return {
        "mean": float(arr.mean()),
        "std":  float(arr.std()),
        "min":  float(arr.min()),
        "max":  float(arr.max()),
        "ratio_max_min": float(arr.max() / max(arr.min(), 0.01)),
    }

print(f"\n{'='*100}")
print("MOTION SMOOTHNESS COMPARISON — zoompan (test_clips/) vs subpixel (test_clips_smooth/)")
print(f"{'='*100}")
print("Lower std and lower max/min ratio = smoother motion")
print()
print(f"{'shot':<6}{'zoompan std':<16}{'subpixel std':<16}{'zoompan max/min':<20}{'subpixel max/min':<20}{'verdict'}")
print('-'*100)

for s in range(1, 9):
    a = per_frame_motion_variance(f"test_clips/clip{s}.mp4")
    b = per_frame_motion_variance(f"test_clips_smooth/clip{s}.mp4")
    if a is None or b is None: continue
    smoother = "subpixel ✓" if b['std'] < a['std'] else "zoompan ✓"
    print(f"{s:<6}{a['std']:<16.4f}{b['std']:<16.4f}{a['ratio_max_min']:<20.2f}{b['ratio_max_min']:<20.2f}{smoother}")
