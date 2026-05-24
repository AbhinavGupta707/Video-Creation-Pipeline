# Car Reel Pipeline

Turns AI-generated car stills into cinematic Instagram Reels — with depth-aware parallax, beat-synced cuts, and per-shot camera tuning.

## What it does

Takes AI-generated still images of a car and outputs a 1080x1920 24fps vertical video where every shot mimics the camera motion of a reference video. The pipeline:

1. Analyzes a reference video with optical flow to extract per-shot camera motion (direction, speed, zoom)
2. Computes monocular depth maps (Depth Anything v2) for each still
3. Renders each shot with sub-pixel `cv2.warpAffine` motion + inverse-depth parallax (closer parts move more)
4. Detects musical beats with librosa and aligns cuts to the beat grid
5. Muxes clips + audio with ffmpeg into a final Reel-ready MP4

The result: cuts that land on the beat, camera moves that feel 3D, and output that's indistinguishable from a conventionally shot and edited car reel.

## Demo

The locked reference output — 8 shots of a widebody Ferrari recreation, tuned frame-by-frame:

```
pipeline/test_output_tuned.mp4   (0.8 MB, 13.2s, 1080x1920 24fps)
```

Generated from `pipeline/test_stills/` (upscaled originals used as stand-ins for real AI stills).

## Tech stack

| Layer | Tools |
|---|---|
| Computer vision | OpenCV (Lucas-Kanade + Farneback optical flow, warpAffine) |
| Depth estimation | Depth Anything v2 via HuggingFace Transformers |
| Audio sync | librosa (beat tracking, BPM detection, drop alignment) |
| Video encoding | ffmpeg (libx264, libvidstab) |
| Runtime | Python 3.9+, PyTorch (MPS on Apple Silicon) |

## Quick start

**Requirements:** Python 3.9+, ffmpeg with libx264

```bash
git clone https://github.com/Dominator0311/Car-Content-Generation
cd Car-Content-Generation

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install ffmpeg (macOS)
brew install ffmpeg

# Render the demo output (uses included test stills)
./pipeline/make_video.sh pipeline/test_stills/ /tmp/demo.mp4
open /tmp/demo.mp4
```

## Usage

### A. Render from your own AI stills

Generate 8 stills in your AI tool of choice (Midjourney, Flux, ChatGPT, Nano Banana). Name them `shot1.jpg` through `shot8.jpg`, 2160x3840 (4K vertical 9:16).

```bash
./pipeline/make_video.sh path/to/stills/ output.mp4
```

### B. Render with audio sync

```bash
./pipeline/make_video.sh path/to/stills/ output.mp4 \
    --audio song.mp3 \
    --bpm-override 145 \
    --drop-at 10.94 \
    --drop-shot 7
```

Cuts will land on the beat. The designated "drop shot" starts at the music's drop.

### C. Analyze a new reference video

To recreate a different car video, extract its camera motion first:

```bash
# Scene detection
ffmpeg -i reference.mp4 -filter:v "select='gt(scene,0.04)',showinfo" -f null - 2>&1 | grep showinfo

# Then compute depth maps for your stills
python pipeline/compute_depth.py pipeline/test_stills/ pipeline/depth_maps/

# Generate motion table from brief
python pipeline/generate_motion.py briefs/your_brief/brief.json pipeline/motion_table.json
```

See `pipeline/README.md` for the full analysis workflow.

## Project structure

```
pipeline/
  render_v2.py              — core renderer: sub-pixel motion + depth parallax + filters
  compute_depth.py          — Depth Anything v2 wrapper, outputs .npy depth maps
  generate_prompts.py       — generates AI image prompts from a creative brief
  generate_motion.py        — builds motion_table.json from a brief
  render_brief.py           — end-to-end render from a brief config
  make_video.sh             — production CLI: orchestrates the full pipeline
  analyze_video.py          — optical flow analysis on a reference video
  analyze_and_render.sh     — combined analyze + render workflow
  batch_analyze.py          — batch analysis across multiple reference videos
  motion_table.json         — per-shot camera motion ground truth (wine ferrari)
  per_shot_config.json      — per-shot tuning (scale, parallax intensity, filters)
  test_stills/              — demo stills (upscaled originals, stand-ins for AI stills)

docs/
  BLUEPRINT.md              — full technical spec: renderer math, decision trees, failure modes
  ROADMAP.md                — 7-phase plan from wine ferrari to full production system
  AUDIO_SYNC_RESEARCH.md    — deep-dive: beat detection, BPM strategy, drop alignment
  BRAINSTORM_PROCESS.md     — creative brief schema and LLM conversation flow

briefs/
  wine_czinger_21c/         — example brief: Czinger 21C, with prompts, refs, motion config

audio/
  audio_timings_master.json — beat timestamps for included reference tracks
  *.mp3                     — reference audio tracks

reference_analysis/
  build_library.py          — builds a shot library from reference video collection
  extract_shots.py          — scene detection and frame extraction
  analyze_shallow.py        — lightweight motion analysis pass
  shot_library.json         — indexed shot library from reference videos

scripts/
  download_instagram_reels.py          — download reference reels by URL
  download_instagram_reels_mac_videos.py — macOS Photos-aware variant

reels.csv                              — 79 Instagram reel URLs used as references (title, url)
```

To fetch the reference reel set:

```bash
python scripts/download_instagram_reels.py --csv reels.csv --output-dir videos/
```

## Key technical decisions

**Why `cv2.warpAffine` instead of `ffmpeg zoompan`**
`zoompan` uses integer pixel stepping — slow camera moves (~0.4–1.5 px/frame) round to 0 or 1, creating visible judder. `warpAffine` with float matrices gives true sub-pixel motion.

**Why inverse-depth parallax**
Linear parallax (strength × depth) is bounded by a ~1.6× depth ratio in typical car shots — too subtle to feel 3D. Inverse-depth (closer = much more displacement) creates the parallax pop you see in real lens footage.

**Why human verification over optical flow alone**
Optical flow fails on glossy bodywork — specular highlights shift in the opposite direction from the underlying geometry, so feature trackers lock onto reflections. QuickTime arrow-key frame stepping is 100% reliable and takes 30 seconds per shot.

**Why librosa over a drop-detection API**
Beat tracking needs per-frame control so cuts can land on exact beat positions. librosa gives onset strength envelopes and BPM with enough granularity to hit half-bar precision. Drop detection uses spectral novelty with manual override for edge cases.

## Roadmap

- [x] Phase 1 — Audio sync (librosa beat detection, shot-to-beat alignment)
- [x] Phase 2 — Variable shot counts (pipeline reads N from motion_table.json)
- [ ] Phase 3 — Real-world (non-studio) video test
- [ ] Phase 4 — `analyze.sh` — one-command video analyzer
- [ ] Phase 5 — Prompt generator from creative briefs
- [ ] Phase 6 — Brainstorm process validation
- [ ] Phase 7 — Preset library

See `ROADMAP.md` for full scope and estimates.

## License

MIT — see [LICENSE](LICENSE)
