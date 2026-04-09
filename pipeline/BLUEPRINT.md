# Wine Ferrari Recreation — Final Blueprint & Spec

> **Purpose:** This is the locked specification for recreating the wine ferrari Instagram Reel
> from 8 AI-generated still images using a deterministic Python+ffmpeg pipeline.
> Every motion value, filter setting, and pipeline decision in this document was iteratively
> tuned against a frame-by-frame visual review of the original video.

---

## Part 1 — The Final Locked Motion Spec

### 1.1 Source Material

| Property | Value |
|---|---|
| Source video | `videos/wine ferrari.mp4` |
| Source resolution | 720 × 1280 (vertical 9:16) |
| Source fps | 24.32 |
| Source duration | 13.187 s |
| Total shots | 8 |
| Output target | 1080 × 1920 (vertical 9:16) |
| Output fps | 24 |
| AI still resolution | 2160 × 3840 (4K vertical 9:16) |

### 1.2 Locked Per-Shot Config (`per_shot_config.json`)

This is the **single source of truth** for every shot's motion mechanics.

| Shot | Subject | Camera Position | Duration | Frames | Motion Type | tx | ty | zoom | Scale | Parallax | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | Side profile, full car | 9:00 mid-body | 2.262 s | 54 | Push-in | 0 | 0 | 1.000 → 1.035 | **1.5×** | OFF | Pure zoom. 1.5× = effective 5.25% push, more visible than baseline 3.5% |
| **2** | Rear-3/4, full car | 7:30 wing-height | 2.261 s | 54 | Yaw right + slight pull | +15 | 0 | 1.030 → 1.000 | **1.0×** | OFF | Smooth/stable. Wide shot — parallax looks unnatural with whole car visible |
| **3** | Wing badge ECU | very close, behind wing | 2.179 s | 52 | Pan right + tilt up + push-in | +12 | -5 | 1.000 → 1.019 | **1.5×** | **4.0** | The ONLY shot with strong parallax. Large clean depth gradient sells the camera arc over the badge |
| **4** | Direct rear, full car | 6:00 low | 2.180 s | 52 | Tilt up | 0 | **-14** ⚠ | 1.000 → 1.005 | **1.0×** | OFF | ty overridden -8 → -14 for stronger upward feel. No parallax = sharp wing rails |
| **5** | Direct front, full car | 12:00 hood-height | 0.904 s | 22 | Tilt up + push-in | 0 | -3 | 1.000 → 1.006 | **1.25×** | OFF | Slightly exaggerated motion over baseline |
| **6** | Front bonnet detail (high angle) | front-right above hood | 1.152 s | 28 | Pan right + slight down + push-in | +12 | +5 | 1.000 → 1.011 | **1.0×** | OFF | Smooth — earlier hybrid was too much |
| **7** | Front-3/4 hero reveal | 10:00 hood-height | 1.069 s | 26 | Subtle pan right + push-in | +5 | 0 | 1.000 → 1.013 | **1.0×** | OFF | Locked-off feel preserved. Subtle motion only |
| **8** | Front wheel close-up | low ground-level | 1.181 s | 28 | Pan left + tilt up + push-in | -22 | -6 | 1.000 → 1.025 | **1.0×** | OFF | Already plenty of motion at baseline (22 px is biggest in video) |

**Pixel convention:** `tx > 0` = camera moves RIGHT. `ty > 0` = camera moves DOWN. Values are in OUTPUT pixels at 1080w. Positive zoom delta = push-in.

### 1.3 Edit Structure

| Beat | Shots | Cumulative time | Function |
|---|---|---|---|
| **Establish** | 1 (side) | 0.00 – 2.26 s | Set the visual language: car, paint color, lighting, scale |
| **Rear walkaround** | 2, 3, 4 | 2.26 – 8.88 s | Build aero/wing identity, brand beat, symmetry payoff |
| **Front mirror** | 5 | 8.88 – 9.79 s | Match cut with shot 4 — front symmetry rhymes with rear |
| **Front detail bookend A** | 6 | 9.79 – 10.94 s | Detail tease before the front-3/4 reveal |
| **HERO reveal** | 7 | 10.94 – 12.01 s | Climax — full front-3/4 of the car, locked off |
| **Front detail bookend B** | 8 | 12.01 – 13.19 s | Closing release beat — counter-direction (left) wheel close |

**Cadence:** First half slow (~2.2 s/shot), second half punchy (~1.05 s/shot). The film accelerates as it walks around to the front.

### 1.4 Filter Stack

**ON by default (clean studio look):**
- Sub-pixel `cv2.warpAffine` warp with **Lanczos4** interpolation
- **Smoothstep easing** (cinematic ease-in/out on every camera move)
- **Inverse-depth perspective parallax** (only on shots with `depth_intensity > 1.0`)
- **Subtle bloom** on bright pixels (specular highlights bleed)
- **Slight unsharp mask** to recover micro-detail lost in lanczos warp

**OFF by default (opt-in via flags):**
- ❌ Color grade (teal-orange split tone) — `--grade`
- ❌ Vignette (corner darkening) — `--vignette`
- ❌ Film grain (random luma noise) — `--grain`
- ❌ All cinematic filters at once — `--cinematic`

---

## Part 2 — The Mechanics Philosophy (What We Learned)

These principles are **the core insights** distilled from iterative shot-by-shot tuning. They generalize to any car video.

### Principle 1 — Parallax helps when there's REAL depth variation, hurts otherwise

**Use parallax when:**
- The shot has a clear foreground/midground/background separation in the depth map
- Closer objects have noticeable depth gradient (e.g., wing endplate sticking out from car body)
- The motion is large enough that differential displacement is visible (>10 px at 1080w)

**Don't use parallax when:**
- The shot is a wide view of the whole car against a clean cyc (e.g., shots 2, 7) — parallax reads as "weird warping" instead of "3D"
- Everything visible is at roughly the same depth (e.g., shot 8 wheel close-up)
- The depth map has sharp cliffs that produce visible distortion artifacts (e.g., shot 4 wing edge)

**Of our 8 shots, only ONE uses parallax (shot 3, the wing macro).** The other 7 look better with depth_intensity = 1.0 (off). This was deeply counterintuitive going in — I expected parallax to be a global win.

### Principle 2 — Pure-zoom shots benefit from MORE motion magnitude

Shots with minimal translation (shots 1, 5) feel "static" at baseline because the eye doesn't register subtle zoom. Bumping them to **1.5× scale** (shot 1) or **1.25× scale** (shot 5) makes the motion legible without becoming dramatic.

### Principle 3 — Wide shots want STABLE, close-ups want DRAMATIC

Wide shots (full car visible) feel right when they're locked off or barely moving — the eye wants to study the car. Close-ups (ECU details) feel right when they have stronger motion and (sometimes) parallax — the eye wants the camera to be exploring.

This matches real cinematography: wide establishing shots are usually static, ECU detail shots usually have a slow dolly or handheld micro-motion.

### Principle 4 — The hero shot must feel locked off

Shot 7 (front-3/4 hero) has the SUBTLEST motion of all close-up-ish shots (5 px pan, 1.3% push). Adding parallax or scale to it kills the "this is the hero" feel. The viewer should be looking AT the car, not noticing the camera.

### Principle 5 — Depth-cliff artifacts are the #1 failure mode of inverse-depth parallax

When `depth_intensity > 2.0` and the depth map has sharp depth boundaries (like a wing edge against the cyc background), the warp creates visible "stretch" or "blur" along that boundary. The fix is **lower the depth intensity for that shot** — typically to 1.5 or 1.0 (off).

### Principle 6 — Per-shot tuning is non-negotiable

A single global setting (one motion_scale, one depth_intensity) cannot make every shot look right. Real car commercial editors tune every shot individually. Our pipeline supports this via `per_shot_config.json`.

### Principle 7 — Clean defaults > stylized defaults

The original wine ferrari is a clean CGI render with neutral grading and no grain. Adding cinematic filters (grain, teal-orange grade, vignette) moves AWAY from the source aesthetic, not toward it. Default to clean; offer stylization as opt-in.

### Principle 8 — Sub-pixel rendering is non-negotiable for slow motion

ffmpeg `zoompan` rounds crop coordinates to integer source pixels per frame. For motions of <1 pixel/frame (typical for our subtle shots), this creates visible judder. The fix is **`cv2.warpAffine` with floating-point affine matrices** — true sub-pixel positioning.

### Principle 9 — Vision LLMs hallucinate motion direction

Tested both Gemini 2.5 models on this video. Both confidently reported wrong directions on multiple shots. The reliable order is: **human eye + QuickTime arrow keys (100%) > optical flow + multi-method consensus (~75%, fails on glossy bodies) > Vision LLMs (~50%, hallucinate)**.

### Principle 10 — Specular reflections fool optical flow

Glossy curved car bodies create specular highlights that shift in the opposite direction of the underlying geometry as the camera moves. Generic feature trackers (LK, Farneback, ECC) lock onto these highlights and report wrong direction. **Always verify ECU shots with human frame-stepping.**

---

## Part 3 — Pipeline Architecture

### 3.1 File Layout

```
pipeline/
├── BLUEPRINT.md                ← THIS FILE — locked spec
├── README.md                   ← user-facing docs
├── motion_table.json           ← raw ground truth from original video
├── per_shot_config.json        ← tuned per-shot overrides ⭐
├── prompts.md                  ← AI image prompts (8 shots)
│
├── compute_depth.py            ← Depth Anything v2 Large wrapper
├── render_v2.py                ← THE renderer ⭐
├── make_video.sh               ← production CLI ⭐
│
├── recipes.sh                  ← legacy ffmpeg zoompan (for --legacy comparison)
├── render_smooth.py            ← v1 sub-pixel renderer (kept for comparison)
├── validate_motion.py          ← motion validation
├── measure_smoothness.py       ← smoothness measurement
│
├── depth_maps/                 ← per-still depth .npy + previews
├── test_stills/                ← upscaled originals (test stand-ins)
├── test_clips_tuned/           ← per-shot rendered clips
├── test_output.mp4             ← legacy zoompan baseline (for comparison)
├── test_output_smooth.mp4      ← sub-pixel baseline (for comparison)
└── test_output_tuned.mp4       ← FINAL tuned output ⭐
```

### 3.2 Component Responsibilities

| Component | Purpose | Inputs | Outputs |
|---|---|---|---|
| **`compute_depth.py`** | Estimate per-pixel depth | 8 stills @ 4K | 8 depth maps (.npy) + previews |
| **`render_v2.py`** | Sub-pixel render with parallax + filters | stills, depth maps, per-shot config | 8 mp4 clips + final concat |
| **`per_shot_config.json`** | Locked motion config | (config file) | Loaded by render_v2 |
| **`make_video.sh`** | One-command production wrapper | stills directory | Final mp4 |

### 3.3 Data Flow

```
                    ┌─────────────────┐
                    │  AI image tool  │  (Nano Banana, Midjourney, Flux, etc.)
                    │  + prompts.md   │
                    └────────┬────────┘
                             │ 8 stills @ 2160×3840
                             ▼
                    ┌─────────────────┐
                    │ make_video.sh   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ compute_depth│ │  render_v2   │ │   ffmpeg     │
    │  (DA v2 L)   │→│ (cv2 warp +  │→│ x264 encode  │
    │              │ │  per-shot    │ │  + concat    │
    │              │ │  config)     │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  output.mp4     │  (1080×1920, 24fps, ~13.2s, ~1MB)
                    └─────────────────┘
```

### 3.4 Renderer Math (`render_v2.py`)

For each shot, for each output frame n in [0, N-1]:

```
1. t = ease_in_out(n / (N-1))   # smoothstep easing

2. z(t) = z0 + (z1 - z0) * t * motion_scale     # interpolated zoom
   tx_src = tx_out * t * motion_scale * (src_w / (out_w * z))
   ty_src = ty_out * t * motion_scale * (src_w / (out_w * z))

3. Build base inverse map (output → source):
     visible_w = src_w / z;  visible_h = src_h / z
     cx = src_w/2 + tx_src;  cy = src_h/2 + ty_src
     map_x[i,j] = (cx - visible_w/2) + j * (visible_w / out_w)
     map_y[i,j] = (cy - visible_h/2) + i * (visible_h / out_h)

4. PERSPECTIVE PARALLAX (only if depth_intensity > 1):
     d = depth[map_y, map_x]                    # sample depth at base position
     z_norm = 1 - d * (1 - 1/depth_intensity)   # virtual z, in [1/intensity, 1]
     extra_factor = (1/z_norm) - 1              # in [0, intensity-1]
     map_x += tx_src * extra_factor             # closer pixels shift MORE
     map_y += ty_src * extra_factor

5. cv2.remap(src, map_x, map_y, INTER_LANCZOS4, BORDER_REPLICATE)

6. Post-process:
     unsharp_mask  (recovers detail lost in lanczos)
     bloom         (highlight bleed)
     # grade, vignette, grain are OFF by default
```

The **inverse-depth math** in step 4 is the key insight: real cameras shift pixels by `focal × dx / z`, so closer objects (smaller z) shift more. Our normalized formulation gives `depth_intensity` as a single tunable parameter where 1.0 = no parallax and higher values give stronger 3D feel.

---

## Part 4 — Creation Workflow

### 4.1 Recreating the wine ferrari (current task)

```bash
# Once you have 8 AI stills as shot1.jpg .. shot8.jpg in some directory:
cd /Users/abhinavgupta/Desktop/instagram
./pipeline/make_video.sh path/to/your_stills/ output.mp4
```

That's it. The script will:
1. Resize/crop each still to 2160×3840
2. Compute depth maps with Depth Anything v2 Large (~3 sec/still)
3. Render 8 sub-pixel clips with the locked per-shot config
4. Concat into final 1080×1920 24fps mp4 (~13.2s, ~1 MB)

Total runtime on Apple M-series: ~60 seconds for 8 shots.

### 4.2 Generating AI stills

Open `prompts.md`. For each of 8 shots:
1. Copy the **shared car description block** (defines paint, body kit, environment, lighting)
2. Append the **shot-specific framing** (camera angle, lens, composition)
3. Paste into your AI tool of choice

**Critical:** to maintain consistency across 8 stills, use a tool that supports image-conditioned generation (Nano Banana / Flux Kontext / Midjourney `--cref`). Otherwise you'll get 8 different cars.

### 4.3 Adapting to a NEW car video

The pipeline is reusable. To analyze and recreate a different car video:

#### Step 1: Scene detection
```bash
ffmpeg -i NEW_VIDEO.mp4 -filter:v "select='gt(scene,0.04)',showinfo" -f null - 2>&1 | grep showinfo
```
Get the cut timestamps.

#### Step 2: Per-shot frame extraction
Extract first frame of each shot at the cut timestamp + 0.05s.

#### Step 3: Motion analysis (multi-method)
Run optical flow methods. Treat their output as a STARTING POINT, not ground truth.

#### Step 4: HUMAN VERIFICATION (mandatory)
Open the video in QuickTime, scrub to each shot, frame-step with arrow keys. For each shot:
- Watch a fixed feature (badge, license plate, edge)
- Note which way it drifts in the frame
- Camera direction = OPPOSITE of feature drift

This step takes ~30 sec per shot but is **the only 100% reliable source of motion direction**.

#### Step 5: Update `motion_table.json` with verified values
Per-shot: timestamps, subject description, camera position, motion (tx, ty, zoom).

#### Step 6: Render baseline
```bash
./pipeline/make_video.sh new_stills/ baseline.mp4 --no-config
```

#### Step 7: Tune per-shot
Watch baseline. For each shot:
- Does it feel right? → keep defaults
- Wide shot looks weird with parallax? → set `depth_intensity: 1.0`
- Pure-zoom shot too subtle? → set `motion_scale: 1.5`
- ECU shot with depth gradient? → try `depth_intensity: 4.0`
- Direction needs adjustment? → override `tx`, `ty`, `z0`, `z1` per shot

Update `per_shot_config.json` (or create a new one) and re-render until satisfied.

#### Step 8: Lock and ship
Once tuned, that config IS your final spec for that video. Save it alongside the source video.

### 4.4 The decision tree for tuning a new shot

```
Watch the rendered shot.
│
├─ Is the motion direction wrong?
│  └─ Check tx/ty signs in motion_table.json. Override in per_shot_config if needed.
│
├─ Does it feel like zoom when it should be camera-moving?
│  └─ Increase motion_scale (try 1.5 first, then 2.0)
│
├─ Is the motion too subtle to register?
│  └─ Increase motion_scale OR override tx/ty for that shot
│
├─ Is the motion too dramatic?
│  └─ Decrease motion_scale
│
├─ Wide shot with whole car visible — does the car wobble unnaturally vs background?
│  └─ Set depth_intensity: 1.0 (parallax off)
│
├─ ECU close-up — does the camera feel like it's just zooming, not exploring?
│  └─ Set depth_intensity: 2.5 or 4.0 (try both)
│
├─ Visible distortion at depth boundaries (wing edge, splitter)?
│  └─ Lower depth_intensity (try 1.5 or 1.0)
│
└─ Hero shot — does it feel like the camera is showing off instead of being locked?
   └─ Set motion_scale: 1.0 and depth_intensity: 1.0 (smooth, no parallax)
```

---

## Part 5 — Known Limitations & Honest Ceilings

### What our 2.5D approach CAN do
- ✅ Sub-pixel accurate camera motion from a single still
- ✅ True 3D parallax via depth-based warping
- ✅ Per-shot tuning for cinematic intent
- ✅ Reusable for any car video with the same workflow
- ✅ Deterministic and fast (~60 sec for 8 shots)

### What it CANNOT do (the ceiling)
- ❌ **Reflections sliding across the paint** as the camera moves — they're frozen in the still
- ❌ **Occlusion changes** — parts of the car hidden behind other parts won't reveal as the camera moves
- ❌ **True 3D rotation** of the car body
- ❌ **Lighting changes** during the move
- ❌ **Physical motion** in the scene (water, smoke, exhaust)

For these, the next steps are:
1. **InstantMesh / Hunyuan3D** — single image → 3D mesh, then render with a real 3D camera in Blender or Open3D. ~1 hour setup, dramatic quality leap.
2. **Native AI video** (Veo 3, Runway Gen-4, Kling 2) — generate each shot directly as 2-3 sec AI video, then concat. ~$5 total cost. Best quality but less control.
3. **Real 3D in Blender** — model the car, animate cameras, render. Highest ceiling, biggest effort.

### Where the pipeline excels vs alternatives
| Approach | Quality | Reproducibility | Cost | Iteration speed |
|---|---|---|---|---|
| **This pipeline** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Free | ⭐⭐⭐⭐⭐ |
| InstantMesh + 3D render | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Free | ⭐⭐⭐ |
| Native AI video (Veo) | ⭐⭐⭐⭐⭐ | ⭐⭐ | $$ | ⭐⭐⭐ |
| Real 3D Blender | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Free | ⭐ |

Our pipeline wins on **iteration speed and reproducibility** — the two things that matter most when you're tuning a 13-second video and want it to look exactly right. AI video wins on visual quality but you can't tune individual shots, and consistency between shots is unpredictable.

---

## Part 6 — Test Outputs (Reference Comparison)

| File | Renderer | Filters | Parallax | Per-shot tuning | Use case |
|---|---|---|---|---|---|
| `test_output.mp4` | ffmpeg zoompan | none | none | none | Legacy baseline — visible pixel-stepping |
| `test_output_smooth.mp4` | sub-pixel cv2 | none | none | none | Sub-pixel baseline — smooth, no 3D |
| **`test_output_tuned.mp4`** | sub-pixel cv2 | clean (bloom+sharpen) | per-shot | **YES** ⭐ | **Final locked output** |

To compare:
```bash
cd /Users/abhinavgupta/Desktop/instagram
open pipeline/test_output_smooth.mp4 pipeline/test_output_tuned.mp4
```

---

## Part 7 — CLI Reference

### `make_video.sh`

```bash
./pipeline/make_video.sh <stills_dir> <output.mp4> [options]
```

**Defaults:** uses `pipeline/per_shot_config.json` if present, CRF 22, clean filters.

| Option | Default | Purpose |
|---|---|---|
| `--config <path>` | `per_shot_config.json` | Per-shot config file |
| `--no-config` | — | Disable per-shot config (use globals) |
| `--scale N` | 1.0 | Global motion magnitude (overridden by config) |
| `--depth-intensity N` | 2.5 | Global depth intensity (overridden by config) |
| `--crf N` | 22 | Quality (18=master, 22=delivery, 24=social) |
| `--grade` | off | Add color grade |
| `--vignette` | off | Add vignette |
| `--grain` | off | Add film grain (large file size) |
| `--cinematic` | off | Enable all stylized filters |
| `--no-parallax` | — | Disable depth parallax globally |
| `--legacy` | off | Use ffmpeg zoompan (for comparison) |

### `render_v2.py` (called by make_video.sh)

```bash
python pipeline/render_v2.py all <stills> <depths> <clips_dir> <final.mp4> [options]
```

Same options as make_video.sh, plus `--no-easing` to disable smoothstep.

### `compute_depth.py`

```bash
python pipeline/compute_depth.py <stills_dir> <output_dir>
```

Computes depth maps with Depth Anything v2 Large. ~3 sec per still on Apple M-series with MPS acceleration.

---

## Part 8 — Ground Truth Verification History

This blueprint was iteratively refined over many rounds:

| Iteration | Method | Outcome |
|---|---|---|
| **v0** | ffmpeg scene detection + LK optical flow | 6/8 directions correct, shots 3+4 wrong |
| **v0.5** | + Farneback dense flow + silhouette tracking | Same 6/8, confirmed failure mode is glossy ECUs |
| **v0.7** | + ghost overlays for visual verification | Confirmed LK was right on 3+4, user originally remembered backwards |
| **v0.8** | + Gemini vision analysis (2 models) | Worse than optical flow — VLMs hallucinated direction |
| **v1.0** | + Human QuickTime frame-stepping | 8/8 ground truth locked |
| **v1.5** | + ffmpeg zoompan recipes | Worked but had pixel-stepping judder |
| **v1.8** | + sub-pixel cv2.warpAffine | Smooth but flat 2D |
| **v2.0** | + Depth Anything v2 + linear parallax + cinematic filters | Too filtered, parallax too subtle |
| **v2.5** | + inverse-depth perspective parallax + clean defaults | Better, but global settings didn't fit all shots |
| **v3.0 (THIS)** | + per-shot config + tuned values | **Locked** ⭐ |

---

## Part 9 — Reusable Insights for the Bigger Picture

This whole exercise produced principles that apply to **any** video reconstruction project:

1. **Trust the human eye over any automation.** Vision LLMs are unreliable for spatial tasks. Optical flow is unreliable on reflective surfaces. The eye + frame stepping is 100%.

2. **Multi-method consensus + human spot-check is the production-grade architecture.** Run several algorithms, flag where they disagree, human-verify the disagreements.

3. **Per-shot tuning is non-negotiable for quality.** No global setting wins on every shot.

4. **Sub-pixel rendering matters even when you don't think it does.** Slow motion at integer-pixel resolution looks shaky. Always use floating-point warps.

5. **Default to clean. Stylization is opt-in.** Adding filters by default makes everything look "AI-stylized." Let the user choose to add them.

6. **Depth-based parallax has a sweet spot.** Too low = no 3D feel. Too high = depth-cliff distortion. Per-shot intensity is the answer.

7. **Document the iteration journey.** The "wrong" approaches we tried (and why they failed) are as valuable as the final working version, because they prevent future repetition.

---

**End of blueprint. This document is the locked spec. Future changes should be tracked as new versions of `per_shot_config.json` and noted in the iteration history.**
