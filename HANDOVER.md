# 🎬 Session Handover — Read This First

> **For next session: this is the ENTRY POINT.** Read this top-to-bottom in 5 minutes, then jump to the relevant deep-dive doc. Everything below is structured for fast context recovery.

---

## 30-second project summary

Building a **deterministic pipeline** that takes **8 AI-generated still images** of a car and produces a **1080×1920 24fps Instagram Reel** that mimics the camera moves of a reference video. Wine ferrari recreation is complete and validated. Next phase: **audio sync to musical beats** (critical), then generalizing to any car video.

The pipeline lives in `pipeline/`. Documentation lives in `instagram/` root.

---

## Status: where we are

### ✅ Done
- **Renderer:** Sub-pixel `cv2.warpAffine` + inverse-depth perspective parallax + clean filters (bloom + sharpen). Locked, working.
- **Wine ferrari motion analysis:** All 8 shots verified by frame-stepping in QuickTime. Ground truth locked in `pipeline/motion_table.json`.
- **Per-shot tuning:** 8-shot config tuned and locked in `pipeline/per_shot_config.json`. Only 1 of 8 shots uses parallax (shot 3 wing macro). The rest are clean sub-pixel warps.
- **Output validated:** `pipeline/test_output_tuned.mp4` matches user intent across all 8 shots after iterative review.
- **Documentation:** `pipeline/BLUEPRINT.md` is the comprehensive 9-part spec.

### ⚠️ Locked but limited
- The renderer **assumes 8 shots hard-coded**. Variable shot counts not supported yet.
- Filter stack tuned for **clean studio CGI**. Real-world videos untested.
- **No audio support** yet. Output is silent.

### ✅ Also done
- **Phase 1 audio sync** — Tier 1 (librosa) planner shipped, wired into `make_video.sh --audio`. T2/T3/T4 R&D parked (see `AUDIO_RESULTS.md`).
- **Phase 2 variable shot counts** — renderer, depth pipeline, and shell script all read N from `motion_table.json`. Smoke-tested at N=8 (byte-identical to locked output) and N=5 (synthetic). Audio T1 planner wired end-to-end — any N works.

### ❌ Not started
- Real-world video test (Phase 3)
- One-command video analyzer (Phase 4)
- Prompt generator from creative briefs (Phase 5)
- Brainstorm validation (Phase 6)
- Preset library (Phase 7)

---

## File map (read in this order if you have 15 min)

| File | Read time | Purpose |
|---|---|---|
| **`HANDOVER.md`** ← you are here | 5 min | Entry point, status, file map |
| **`AUDIO_SYNC_RESEARCH.md`** | 15 min | **READ THIS BEFORE STARTING PHASE 1.** Deep research on beat detection, BPM strategy, drop alignment, librosa, implementation plan |
| **`ROADMAP.md`** | 10 min | All 7 phases, dependencies, success criteria |
| **`BRAINSTORM_PROCESS.md`** | 10 min | Creative brief schema, LLM conversation flow, examples |
| **`pipeline/BLUEPRINT.md`** | 20 min | Full pipeline spec — read if you need to understand the renderer math, decision trees, or wine ferrari motion details |
| **`pipeline/README.md`** | 5 min | User-facing pipeline docs (how to run, options) |
| **`pipeline/per_shot_config.json`** | 2 min | The locked wine ferrari config |
| **`pipeline/motion_table.json`** | 5 min | Wine ferrari ground truth motion values |
| `REEL_RECIPE.md` (pre-existing) | optional | A pre-existing artifact from an earlier session — describes a "ChatGPT + Kling/Runway i2v + CapCut" workflow. Not part of the current pipeline; kept for reference. The current pipeline supersedes it. |

**Minimum viable context for jumping into Phase 1 (audio sync):** read this file + AUDIO_SYNC_RESEARCH.md. ~20 min.

---

## Quick-start commands

### Run the existing pipeline (sanity check)
```bash
cd /Users/abhinavgupta/Desktop/instagram
./pipeline/make_video.sh pipeline/test_stills/ /tmp/sanity.mp4
open /tmp/sanity.mp4
# Should produce ~13s, ~1MB video matching pipeline/test_output_tuned.mp4
```

### View the locked output
```bash
cd /Users/abhinavgupta/Desktop/instagram
open pipeline/test_output_tuned.mp4
```

### Check the pipeline files
```bash
cd /Users/abhinavgupta/Desktop/instagram
ls -la pipeline/
cat pipeline/per_shot_config.json
cat pipeline/motion_table.json
```

### Activate the Python venv (if needed for development)
```bash
cd /Users/abhinavgupta/Desktop/instagram
source .venv/bin/activate
python -c "import cv2, numpy, torch; print('OK')"
```

### Verify ffmpeg with vidstab
```bash
ffmpeg -filters | grep vidstab
# should show vidstabdetect and vidstabtransform
```

---

## 🎯 Next session priority: Phase 1 — Audio sync

**Read this before doing anything:** `AUDIO_SYNC_RESEARCH.md` in this directory.

It contains:
- Why beat sync is critical (Part 1)
- The BPM math for wine ferrari (Part 3) — wine ferrari naturally aligns to ~145 BPM
- Beat/drop detection with librosa (Part 4)
- Full sync architecture diagram (Part 5)
- File-by-file implementation plan (Part 6)
- 7 open questions to resolve (Part 7)
- Step-by-step implementation order (Part 8) — ~3.5 hours total
- 5 validation tests (Part 9)
- Anti-patterns (Part 10)

**The TL;DR is in Part 8 of that doc.** Just read it and start implementing.

**Phase 1 deliverables:**
1. `pipeline/audio_sync.py` (NEW) — librosa beat detection + shot-to-beat alignment
2. `pipeline/render_v2.py` (UPDATE) — accept variable frame counts from audio_sync
3. `pipeline/make_video.sh` (UPDATE) — `--audio`, `--bpm-override`, `--drop-at`, `--drop-shot`, `--granularity` flags
4. Audio overlay step in `make_video.sh`

**Success criteria:** `./pipeline/make_video.sh stills/ output.mp4 --audio song.mp3` produces a video where cuts visibly land on beats and the hero shot lands on the drop.

---

## Critical context to NOT lose

### Hard-won insights (don't relearn these the hard way)

1. **Vision LLMs hallucinate motion direction.** Tested both Gemini 2.5 models — got shot 8 exactly opposite. Use optical flow + human verification, not VLMs, for motion analysis.

2. **Optical flow fails on glossy car bodies** because specular highlights shift in the opposite direction of geometry. This is THE failure mode for ECU shots. **ALWAYS verify ECU shots with QuickTime arrow-key frame stepping.**

3. **Of 8 wine ferrari shots, only ONE uses parallax** (shot 3 wing macro). Parallax is a niche tool, not a global win. Wide shots with full car visible look WRONG with parallax. ECU shots with uniform depth look WRONG with parallax. Only ECU shots with strong depth gradient benefit.

4. **`zoompan` has integer-pixel stepping** that creates visible judder for slow motion. Use `cv2.warpAffine` with float matrices instead. This was the main reason v1 felt shaky.

5. **Default to clean filters, not stylized.** Adding grain/grade/vignette by default makes everything look "AI-stylized." The wine ferrari is clean CGI — matching it means clean defaults. Stylization is opt-in via flags.

6. **Per-shot tuning is non-negotiable.** No global setting (one motion_scale, one depth_intensity) wins on every shot. Real cinematographers tune every shot. The pipeline supports this via `per_shot_config.json`.

7. **Sub-pixel rendering matters even when motion is small.** Slow camera moves (~0.4-1.5 px/frame) round to 0/1 with integer rounding, creating judder. Always use float math.

8. **Depth-cliff distortion is the #1 failure mode of inverse-depth parallax** at high intensity. Wing edges, splitter edges, anywhere there's a sharp depth boundary will smear/stretch. Fix: lower depth_intensity for affected shots or disable parallax entirely.

9. **Film grain DESTROYS H.264 compression.** Random noise is incompressible by design. Adding grain bumped wine ferrari output from 0.8 MB to 62 MB. Skip grain unless you specifically want film aesthetic.

10. **Quicktime caches files by name.** When you re-render an output with the same filename, you have to QUIT and reopen QuickTime to see the new version. Wasted ~15 min on this.

### Things that DIDN'T work (don't re-try)

| Approach | Why it failed |
|---|---|
| Linear parallax (current strength * depth) | Bounded ratio (1.6× max), too subtle to feel 3D. **Use inverse-depth instead.** |
| Color grade by default | Looked filtered, away from clean CGI source. Make opt-in. |
| Vignette by default | Same — wrong for clean studio. Make opt-in. |
| Film grain by default | Massive file size + wrong aesthetic for CGI source. Make opt-in. |
| `ffmpeg vidstabdetect` for analysis | Outputs binary `.trf` file, hard to extract per-shot motion. We installed it but ended up not using it. |
| `ffmpeg zoompan` for sub-pixel motion | Integer pixel stepping causes judder. Use cv2 instead. |
| Vision LLMs (Gemini) for motion direction | Hallucinated direction on multiple shots. Don't trust them. |
| Median pixel difference (Pillow) for motion magnitude | Too coarse, only detects large motion. Use optical flow. |

---

## Open questions / unresolved decisions

These are NOT blockers but should be addressed when relevant:

1. **Variable shot count pipeline support** — currently 8-shot hardcoded. Phase 2 fixes this.
2. **Real-world video filter stack** — untested whether clean filters work on outdoor footage. Phase 3 tests this.
3. **Music BPM detection accuracy** — librosa sometimes reports octave errors (60 vs 120). Need user override flag.
4. **Drop detection** — should be auto-detected via spectral novelty, but manual override should be supported. Phase 1 covers this.
5. **Real AI stills pending** — user hasn't generated wine ferrari AI stills yet. Pipeline tested only with extracted+upscaled originals as stand-ins. Real 4K AI stills will look sharper.

---

## What you'll need to build next session (Phase 1)

### New files
- `pipeline/audio_sync.py` — beat detection, shot-to-beat alignment

### Modified files
- `pipeline/render_v2.py` — accept variable frame counts (currently hardcoded in SHOTS dict)
- `pipeline/make_video.sh` — add audio sync flags
- `pipeline/per_shot_config.json` — optionally accept `frame_count` overrides

### New dependencies
- `librosa` (~50 MB pip install with deps)

### New CLI surface
```bash
./pipeline/make_video.sh stills/ output.mp4 \
    --audio song.mp3 \
    --bpm-override 145 \
    --drop-at 10.94 \
    --drop-shot 7 \
    --granularity half_bar
```

### Tests to run
See `AUDIO_SYNC_RESEARCH.md` Part 9 for the 5-test validation suite.

---

## Hardware/environment context

- **Machine:** Mac (Apple Silicon, M-series with MPS acceleration)
- **Project root:** `/Users/abhinavgupta/Desktop/instagram`
- **Python:** `/Users/abhinavgupta/Desktop/instagram/.venv/bin/python` (Python 3.9, OpenCV 4.13, NumPy 2.0, PyTorch 2.8 with MPS, Transformers 4.57)
- **ffmpeg:** `/opt/homebrew/bin/ffmpeg` (8.1, with libvidstab, libx264, libx265, etc. — built from `homebrew-ffmpeg/ffmpeg` tap)
- **Disk:** Plenty
- **Source video:** `videos/wine ferrari.mp4` (720×1280, 13.19s, 24.32fps, 514 KB)

---

## File tree (current state)

```
/Users/abhinavgupta/Desktop/instagram/
├── HANDOVER.md                    ⭐ ENTRY POINT (this file)
├── AUDIO_SYNC_RESEARCH.md         ⭐ READ FOR PHASE 1
├── BRAINSTORM_PROCESS.md          (process doc, no code)
├── ROADMAP.md                     (7 phases laid out)
├── .claude_context                (breadcrumb pointing here)
│
├── videos/
│   └── wine ferrari.mp4           (13.19s reference video)
│
├── wine_ferrari_frames/
│   └── *.jpg                      (78 evenly-extracted frames at 6fps)
│
├── shots_analysis/                (intermediate analysis files — kept for reference)
│   ├── *.py                       (various analysis scripts)
│   ├── shot{1-8}_p{5,25,50,75,95}.jpg  (40 sample frames)
│   ├── dense_s{1-8}_f{...}.jpg    (94 dense sample frames)
│   ├── overlay_shot{1-8}.jpg      (ghost overlays for verification)
│   ├── contact_sheet.jpg
│   └── transforms.trf             (vidstab output, unused)
│
├── pipeline/                      ⭐ THE PIPELINE
│   ├── BLUEPRINT.md               (9-part spec — full reference)
│   ├── README.md                  (user-facing docs)
│   │
│   ├── motion_table.json          (locked ground truth)
│   ├── per_shot_config.json       (locked tuning) ⭐
│   ├── prompts.md                 (AI image prompts for wine ferrari)
│   │
│   ├── compute_depth.py           (Depth Anything v2 wrapper)
│   ├── render_v2.py               (THE RENDERER) ⭐
│   ├── make_video.sh              (production CLI) ⭐
│   │
│   ├── recipes.sh                 (legacy ffmpeg zoompan, kept for --legacy)
│   ├── render_smooth.py           (v1 sub-pixel renderer, kept for comparison)
│   ├── validate_motion.py         (motion validation)
│   ├── measure_smoothness.py      (smoothness measurement)
│   │
│   ├── depth_maps/                (per-shot depth .npy + previews)
│   │   ├── shot{1-8}_depth.npy
│   │   └── shot{1-8}_depth_preview.jpg
│   │
│   ├── test_stills/               (extracted+upscaled originals as stand-ins)
│   │   └── shot{1-8}.jpg
│   │
│   ├── test_clips_tuned/          (per-shot rendered clips)
│   │   └── clip{1-8}.mp4
│   │
│   ├── test_output.mp4            (legacy zoompan, 1.2 MB, baseline reference)
│   ├── test_output_smooth.mp4     (sub-pixel only, 1.4 MB, no parallax baseline)
│   └── test_output_tuned.mp4      ⭐ FINAL LOCKED OUTPUT (0.8 MB)
│
└── .venv/                         (Python venv with cv2, torch, transformers, etc.)
```

---

## How to verify everything still works (smoke test)

If you're picking this up after a long break and want to make sure nothing rotted:

```bash
cd /Users/abhinavgupta/Desktop/instagram

# 1. Verify Python env
.venv/bin/python -c "import cv2, numpy, torch, transformers; print('Python OK')"

# 2. Verify ffmpeg
ffmpeg -filters | grep -E "vidstab|libx264" | head -5

# 3. Re-render the locked tuned output
./pipeline/make_video.sh pipeline/test_stills/ /tmp/smoke_test.mp4

# 4. Compare against the saved version (file sizes should match within 1KB)
ls -la /tmp/smoke_test.mp4 pipeline/test_output_tuned.mp4

# 5. Visual comparison
open /tmp/smoke_test.mp4 pipeline/test_output_tuned.mp4
```

If all 5 steps pass, the pipeline is healthy and you can start Phase 1.

---

## When in doubt

- **Stuck on audio sync architecture?** → re-read `AUDIO_SYNC_RESEARCH.md` Part 5 (full diagram)
- **Stuck on rendering math?** → re-read `pipeline/BLUEPRINT.md` Part 3.4 (renderer math)
- **Stuck on which shot needs what tuning?** → re-read `pipeline/BLUEPRINT.md` Part 4.4 (decision tree)
- **Stuck on creative brief format?** → re-read `BRAINSTORM_PROCESS.md` Part 1 (schema) and Part 5 (example)
- **Stuck on roadmap priorities?** → re-read `ROADMAP.md` "Critical path" section
- **Optical flow giving wrong direction?** → It probably is. Use QuickTime arrow keys instead.

---

## Final notes for next session

1. **Don't re-tune wine ferrari motion.** It's locked. Don't touch `per_shot_config.json` unless adding new fields (like `frame_count` overrides for audio sync).

2. **Phase 1 (audio sync) and Phase 2 (variable shot count) can run in parallel.** Audio sync needs Phase 2 to be useful, but you can build the audio_sync.py module first and integrate after.

3. **Real AI stills haven't been generated yet.** When user does this, the test outputs will look noticeably sharper (currently using upscaled 720p originals). The pipeline is unchanged.

4. **The user's vision is bigger than wine ferrari.** They want to analyze multiple saved videos, brainstorm new ones, generate new prompts, and produce videos with audio sync. Wine ferrari is the FIRST one. The roadmap is the path.

5. **Don't over-engineer the brainstorm process.** It's a conversation, not code. The doc is enough. Resist the urge to write a chatbot for it.

6. **Audio sync is the highest-leverage thing.** Without it, even perfect visuals feel amateur. With it, even rough visuals feel professional. Prioritize accordingly.

---

**Now go read `AUDIO_SYNC_RESEARCH.md` and start Phase 1.**
