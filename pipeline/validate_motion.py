"""
Validate that test_output motion matches the original.
For each test clip, run optical flow on first vs last frame and report
the actual motion detected. Compare against expected from motion_table.
"""
import cv2, glob, json
import numpy as np

EXPECTED = {
    1: {"name": "Side push-in",       "tx": 0,   "ty": 0,   "zoom": "+3.5%"},
    2: {"name": "Rear-3/4 yaw right + pull", "tx": +15, "ty": 0,   "zoom": "-3.0%"},
    3: {"name": "Wing pan right + tilt up + push", "tx": +12, "ty": -5,  "zoom": "+1.9%"},
    4: {"name": "Direct rear tilt up", "tx": 0,   "ty": -8,  "zoom": "+0.5%"},
    5: {"name": "Direct front tilt up + push", "tx": 0,   "ty": -3,  "zoom": "+0.6%"},
    6: {"name": "Bonnet pan right + tilt down + push", "tx": +12, "ty": +5,  "zoom": "+1.1%"},
    7: {"name": "Front-3/4 hero pan right + push", "tx": +5,  "ty": 0,   "zoom": "+1.3%"},
    8: {"name": "Wheel pan LEFT + tilt up + push", "tx": -22, "ty": -6,  "zoom": "+2.5%"},
}

print(f"\n{'='*100}")
print("MOTION VALIDATION — measured motion in test_output vs expected ground truth")
print(f"{'='*100}")
print(f"{'shot':<5}{'name':<45}{'expected':<25}{'measured':<25}{'verdict':<10}")
print('-'*100)

for s in range(1, 9):
    a = cv2.imread(f"first_{s}.jpg", cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(f"last_{s}.jpg",  cv2.IMREAD_GRAYSCALE)
    if a is None or b is None:
        print(f"{s}: missing frames")
        continue
    # Downsample for speed
    a = cv2.resize(a, (a.shape[1]//2, a.shape[0]//2))
    b = cv2.resize(b, (b.shape[1]//2, b.shape[0]//2))

    # Track corner features
    p0 = cv2.goodFeaturesToTrack(a, maxCorners=300, qualityLevel=0.01, minDistance=10, blockSize=7)
    if p0 is None or len(p0) < 10:
        print(f"{s}: no features")
        continue
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, winSize=(31,31), maxLevel=4)
    valid = st.flatten().astype(bool)
    if valid.sum() < 5:
        print(f"{s}: no valid tracks")
        continue
    deltas = (p1 - p0)[valid]
    med_dx = float(np.median(deltas[:,0,0])) * 2  # *2 to undo downsample
    med_dy = float(np.median(deltas[:,0,1])) * 2

    # Convert measured (which is in source pixels at 1080w / 2 = 540, then *2 = 1080)
    # No, the test clips are 1080x1920 already. We downsampled to 540x960, *2 returns to 1080.
    # The ZOOMPAN already produced 1080w output. Measured tx/ty is at 1080w scale.

    # Compute zoom from feature spread
    p0_v = p0[valid]
    p1_v = p1[valid]
    c0 = p0_v.mean(axis=0)
    c1 = p1_v.mean(axis=0)
    d0 = np.linalg.norm(p0_v - c0, axis=2).mean()
    d1 = np.linalg.norm(p1_v - c1, axis=2).mean()
    measured_zoom_pct = (d1/d0 - 1) * 100 if d0 > 0 else 0

    # CAMERA direction is opposite to feature drift
    # measured tx > 0 means features moved right, camera moved LEFT
    # But our recipe applies camera-direction tx in the OUTPUT, where positive tx = camera right
    # In the OUTPUT clip: if camera moved right, content shifts left, features dx < 0
    # So measured camera tx = -median_dx
    cam_tx = -med_dx
    cam_ty = -med_dy

    exp = EXPECTED[s]
    name = exp["name"]

    expected_str = f"tx={exp['tx']:+}px,ty={exp['ty']:+}px,z={exp['zoom']}"
    measured_str = f"tx={cam_tx:+5.1f}px,ty={cam_ty:+5.1f}px,z={measured_zoom_pct:+.1f}%"

    # Check direction match
    tx_ok = (exp['tx'] == 0 and abs(cam_tx) < 4) or (exp['tx'] != 0 and np.sign(cam_tx) == np.sign(exp['tx']))
    ty_ok = (exp['ty'] == 0 and abs(cam_ty) < 4) or (exp['ty'] != 0 and np.sign(cam_ty) == np.sign(exp['ty']))
    verdict = "✓" if (tx_ok and ty_ok) else "⚠"

    print(f"{s:<5}{name:<45}{expected_str:<25}{measured_str:<25}{verdict}")
