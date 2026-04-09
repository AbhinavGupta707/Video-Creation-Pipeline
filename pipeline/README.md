# Wine Ferrari Recreation Pipeline

A reusable toolkit to analyze a car video and recreate it from AI-generated still images using ffmpeg.

## What's in here

| File | Purpose |
|---|---|
| `motion_table.json` | Locked ground truth: 8 shots with timestamps, camera positions, and exact motion values for the wine ferrari video |
| `recipes.sh` | ffmpeg zoompan recipes — one function per shot. Takes a still, produces a video clip with the right motion |
| `prompts.md` | AI image prompts for all 8 shots, with tool-specific notes for Nano Banana / Midjourney / ChatGPT / Flux |
| `test_with_originals.sh` | Validates the recipes by extracting frames from the ORIGINAL video and applying the recipes (no AI credits needed) |
| `make_video.sh` | Production: takes 8 AI stills and produces the final 1080×1920 24fps video |
| `validate_motion.py` | Measures motion in a test output and compares to expected — sanity check |
| `test_output.mp4` | The recreated video using upscaled original frames (proves the recipes work) |
| `test_stills/` | First frame of each shot, upscaled to 4K for use as test stand-ins |
| `test_clips/` | Per-shot rendered clips at 1080×1920 |

## Quick start

### A. Verify the recipes work (no AI tools needed)

```
./test_with_originals.sh
open test_output.mp4
# Compare side-by-side with the original wine ferrari video
```

### B. Generate AI stills + recreate

1. Open `prompts.md`. For each of the 8 shots, copy the prompt block (shared description + shot-specific framing) into your AI tool of choice.
2. Save all 8 generated stills to a single directory, named `shot1.jpg` through `shot8.jpg`, at 2160×3840 (4K vertical 9:16).
3. Run:
   ```
   ./make_video.sh path/to/your_stills/ output.mp4
   ```
4. Output: `output.mp4` at 1080×1920 24fps, ~13.2 seconds long.

## Motion convention (for understanding the recipes)

In `recipes.sh`, each shot function uses these conventions:

| Symbol | Meaning |
|---|---|
| `tx > 0` | Camera moves RIGHT (visible window slides right in source) |
| `tx < 0` | Camera moves LEFT |
| `ty > 0` | Camera moves DOWN |
| `ty < 0` | Camera moves UP |
| `zoom_start < zoom_end` | Push-in (camera moves toward subject) |
| `zoom_start > zoom_end` | Pull-back |

All pixel values in `recipes.sh` are in **source pixel space** (2160×3840). Output pixel values would be half (1080×1920). The motion_table.json has values in OUTPUT pixel space (1080w).

## To analyze a NEW car video

This pipeline is designed for the wine ferrari but the methodology generalizes. To analyze a new video:

1. **Scene detection:**
   ```
   ffmpeg -i NEW_VIDEO.mp4 -filter:v "select='gt(scene,0.04)',showinfo" -f null - 2>&1 | grep showinfo
   ```
   Get the cut timestamps. Each cut starts a new shot.

2. **Per-shot frame extraction:** Same approach as `test_with_originals.sh` — extract first frame of each shot at the shot's start timestamp + 0.05s (to skip cut artifacts).

3. **Motion analysis:** Run optical flow methods. If you suspect ECU shots of glossy bodywork, **manually verify direction in QuickTime** using arrow-key frame stepping. This is THE most reliable method — see "Known failure modes" below.

4. **Build motion_table:** Update `motion_table.json` with the new shot list and motion values.

5. **Update recipes.sh:** Add/edit shot functions to match the new motion table.

6. **Generate prompts:** Update `prompts.md` with shot descriptions for the new car.

7. **Test, then produce:** Same workflow as above.

## Known failure modes (read this before trusting any analysis tool)

| Tool | Reliability | Failure mode |
|---|---|---|
| Optical flow (LK / Farneback / ECC) | 75% on car footage | **Specular highlights on curved glossy surfaces** confuse feature trackers — they lock onto reflections that shift in the OPPOSITE direction from the underlying geometry. Especially bad on wing macro shots, hood detail shots, bodywork close-ups. |
| Vision LLMs (GPT-4V, Gemini, Claude) | ~50% on direction | **Hallucinate confidently.** Tested both Gemini 2.5 models — they got shot 8's direction exactly opposite from ground truth. Don't trust VLMs for motion direction. They ARE useful for shot content identification. |
| ffmpeg vidstabdetect | ~85% | Better than OpenCV but still fooled by extreme close-ups of reflective surfaces. Can't easily extract data — outputs binary `.trf` for use with vidstabtransform pass 2. |
| **Human + QuickTime arrow keys** | **100%** | Open the video in QuickTime, scrub to a shot, press → to step one frame at a time, watch a fixed feature (badge, license plate) and observe direction. Takes 30 seconds per shot. **This is the gold standard.** |

**Architecture rule:** automate what's reliable (cuts, magnitudes, wide shots), and human-verify what isn't (close-ups of glossy bodywork). Don't try to make any single algorithm perfect — combine methods and use human spot-check as a feature, not a workaround.

## Troubleshooting

### "ffmpeg not found"
You need ffmpeg with libvidstab. Install via:
```
brew uninstall ffmpeg
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libvidstab
```

### Test output looks blurry / soft
Expected. The test uses the 720×1280 original frames upscaled to 2160×3840. Production output from real 4K AI stills will be sharp.

### My AI stills don't match each other (different cars across shots)
This is the consistency problem. See `prompts.md` "Tool-specific notes for consistency". Best tool right now is Nano Banana (free in Google AI Studio) — pass shot 1 as a reference image when generating shots 2-8.

### Motion looks wrong / opposite direction in my output
Check the sign convention in `recipes.sh` for that specific shot. The `zoompan_expr` helper takes (duration, zoom_start, zoom_end, x_delta_src_px, y_delta_src_px). Negative x = camera moves LEFT, negative y = camera moves UP, positive zoom_end > zoom_start = push-in.

## Credits / source

- Original video: `videos/wine ferrari.mp4` (custom widebody Ferrari render)
- Analysis: ffmpeg scene detect + OpenCV (LK, Farneback, silhouette tracking) + ghost overlays + human QuickTime verification
- Final motion ground truth verified by frame-by-frame stepping of the original video
