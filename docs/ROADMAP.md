# Roadmap — From Wine Ferrari to Full Production System

> **Current state:** Wine ferrari recreation pipeline is locked. The renderer (sub-pixel + depth parallax + per-shot config) is reusable. What's missing is the orchestration around it: analysis automation, brainstorming, prompt generation, audio sync.

---

## Phases at a glance

```
PHASE 1  Audio sync (next session — TOP PRIORITY) ← critical for output quality
PHASE 2  Generalize render_v2.py for variable shot counts
PHASE 3  Test pipeline on a real-world (non-studio) video
PHASE 4  Build analyze.sh — one-command video analyzer
PHASE 5  Build prompt generator from creative briefs
PHASE 6  Brainstorm process refinement
PHASE 7  Preset library (emerges naturally)
```

Total estimated effort: **~12-16 hours** of focused work split across 3-4 sessions.

---

## PHASE 1 — Audio Sync (NEXT SESSION, ~3.5 hours)

**Why first:** Without beat sync, the output video looks amateur regardless of how good the visuals are. This is the single biggest quality lever remaining.

**Read first:** `AUDIO_SYNC_RESEARCH.md` in this directory — full deep-dive already done.

**Deliverables:**
- `pipeline/audio_sync.py` — librosa-based beat detection + shot-to-beat alignment
- Updated `pipeline/render_v2.py` — accepts variable frame counts from audio_sync
- Updated `pipeline/make_video.sh` — `--audio`, `--bpm-override`, `--drop-at`, `--drop-shot`, `--granularity` flags
- Audio overlay step in make_video.sh (final ffmpeg mux)
- 5 validation tests (see AUDIO_SYNC_RESEARCH.md Part 9)

**Dependencies:** none, can start immediately

**Blocks:** Phase 2 (variable shot counts is needed for audio sync to adjust durations)

**Success criteria:**
- `./pipeline/make_video.sh stills/ output.mp4 --audio song.mp3` produces a video where cuts visibly land on beats
- The hero shot (or designated drop shot) starts on the music's drop
- Beat detection works on at least 3 different songs without manual override
- Total video length stays within ±200ms of target

---

## PHASE 2 — Generalize render_v2.py for variable shot counts (~2 hours)

**Why:** Currently `SHOTS` dict is hard-coded with 8 wine ferrari shots. New videos may have 5-12 shots. Need to load the shot list dynamically.

**Tasks:**
1. Move `SHOTS` dict from `render_v2.py` to `motion_table.json`
2. `render_v2.py` loads shots from `motion_table.json` at startup
3. `make_video.sh` loops over the actual shot count instead of hardcoded `1..8`
4. `per_shot_config.json` accepts arbitrary shot count
5. `compute_depth.py` handles variable count

**Dependencies:** none, can be done in parallel with Phase 1

**Blocks:** Phase 3, 4

**Success criteria:**
- Can render a 5-shot or 12-shot video using the same pipeline
- All wine ferrari outputs still produce identical results (regression test)

---

## PHASE 3 — Real-world (non-studio) video test (~1-2 hours)

**Why:** The clean filter stack and depth parallax are tuned for clean studio CGI. Real outdoor/street footage has different characteristics. Need to know what breaks before generalizing further.

**Tasks:**
1. User selects ONE real-world car video (street, mountain, track, anywhere outdoor)
2. Run the existing pipeline on it (`make_video.sh`) using extracted frames as stand-ins
3. Document what works and what fails:
   - Does optical flow handle real motion?
   - Does Depth Anything v2 produce useful depth on outdoor scenes?
   - Do the clean filters look right on real footage, or does it need grain/grade?
   - Are there shot types we don't handle (fast pans, motion blur, lens flares)?
4. Decide: one preset for all, or "studio preset" + "real-world preset"?

**Dependencies:** Phase 2 (need variable shot counts since real videos won't be 8 shots)

**Blocks:** Phase 4 (analyzer needs to know what to look for)

**Success criteria:**
- Honest assessment of failure modes documented
- Decision made on preset architecture
- At least ONE real-world video successfully analyzed end-to-end

---

## PHASE 4 — analyze.sh — one-command video analyzer (~2 hours)

**Why:** Currently you'd need to manually run scene detection, frame extraction, optical flow, overlay generation, and write motion_table.json by hand. This phase glues all of that into a single script.

**Tasks:**
1. `pipeline/analyze.sh <video.mp4> <output_dir>` — orchestrates the full analysis
2. Outputs into `<output_dir>/`:
   - `motion_table.json` (detected shots + draft motion values)
   - `per_shot_config.json` (sensible defaults — all smooth, no parallax to start)
   - `depth_maps/` (per-shot depth maps)
   - `overlays/` (ghost overlays for human verification)
   - `contact_sheet.jpg` (visual summary of all shots)
   - `verification_checklist.md` (which shots need human attention, with QuickTime timestamps)
3. Multi-method optical flow with confidence scoring — flag shots where methods disagree
4. Print clear next-steps to the user: "open video.mp4 in QuickTime, verify shots [3, 5, 7] using arrow keys"

**Dependencies:** Phase 2 (variable shot counts), Phase 3 (real-world handling)

**Blocks:** the goal of "analyze multiple saved videos"

**Success criteria:**
- One command analyzes any car video in <2 minutes
- Outputs are consumable by render_v2.py without manual editing
- Human verification list is clear and actionable

---

## PHASE 5 — Prompt generator from creative briefs (~1.5 hours)

**Why:** Currently `prompts.md` is hand-written for wine ferrari. New videos need new prompts that match their aesthetic. The brief from BRAINSTORM_PROCESS.md should drive prompt generation automatically.

**Tasks:**
1. `pipeline/generate_prompts.py <brief.yaml> <motion_table.json> <output.md>`
2. Reads creative brief (subject, environment, lighting, mood)
3. Reads shot list (camera positions, framings)
4. Outputs `prompts.md` with:
   - Universal description block (filled from brief)
   - Per-shot framing block (filled from shot list + brief mood)
   - Tool-specific consistency notes (Nano Banana, Midjourney, Flux)
5. Template-based — easy to add new prompt formats for new tools

**Dependencies:** Phase 4 (need motion_table.json from analyzer)

**Blocks:** end-to-end "brief → final video" workflow

**Success criteria:**
- Given a brief and a shot list, produces ready-to-paste AI prompts
- Generated prompts maintain car/environment consistency across all shots
- Output works with at least 2 AI image tools

---

## PHASE 6 — Brainstorm process refinement (~30 min)

**Why:** Validate the BRAINSTORM_PROCESS.md guide actually works in practice. Iterate based on real use.

**Tasks:**
1. Use BRAINSTORM_PROCESS.md to develop a NEW creative brief from scratch
2. Pass that brief through the prompt generator (Phase 5)
3. Generate stills, render the video
4. Compare against intent — does the rendered video match the brief?
5. Update BRAINSTORM_PROCESS.md with lessons learned

**Dependencies:** Phase 5

**Blocks:** nothing (this is iterative)

**Success criteria:**
- Successfully brainstormed and produced ONE new video end-to-end
- Process documentation updated with real findings

---

## PHASE 7 — Preset library (emerges naturally, ~ongoing)

**Why:** As you analyze more videos, common patterns emerge ("hero reveal preset," "wing macro arc preset"). Codifying these saves tuning time on future projects.

**Tasks:**
1. After analyzing 3-5 videos, identify recurring shot types
2. Build `pipeline/presets/` directory with named presets:
   - `presets/hero_reveal.json` — wide front-3/4, smooth, no parallax
   - `presets/wing_macro_arc.json` — ECU, 1.5× scale, depth_intensity 4.0
   - `presets/wheel_sweep.json` — low ECU, baseline motion, no parallax
   - etc.
3. `per_shot_config.json` can REFERENCE presets by name: `{"preset": "hero_reveal"}`
4. Add CLI: `make_video.sh --list-presets`

**Dependencies:** Phase 4 (need to have analyzed multiple videos first)

**Blocks:** nothing — pure UX improvement

**Success criteria:**
- Common shots can be configured by preset name instead of manual tuning
- Library has at least 8-10 presets covering most car shot types

---

## What's NOT on the roadmap (and why)

### ❌ Native AI video integration (Veo / Runway / Kling)
**Why not:** This is a fundamentally different approach (replace stills+pipeline with AI video). It's worth EXPERIMENTING with but not building into the deterministic pipeline. The pipeline's value is reproducibility; AI video's value is quality. They're complementary, not substitutable. Test Veo manually for individual shots when the pipeline output isn't enough.

### ❌ 3D mesh generation (InstantMesh / Hunyuan3D)
**Why not:** Massive complexity jump. Would require Blender integration or a custom 3D renderer. Worth exploring eventually but premature now.

### ❌ Real-time preview / GUI
**Why not:** Out of scope for a CLI pipeline. iteration is fast enough via re-render.

### ❌ Cloud rendering / scaling
**Why not:** Local Mac M-series renders fast enough for one video. Scaling is a problem for later.

### ❌ Stock music library / royalty-free integration
**Why not:** User can supply their own audio. Don't need a music database.

---

## Critical path

The fastest path to "full production system" is:

```
PHASE 1 (audio) ──┐
                  ├─→ PHASE 4 (analyze) ─→ PHASE 5 (prompts) ─→ PHASE 6 (validate brief)
PHASE 2 (varN) ───┘                                                       │
                                                                          │
PHASE 3 (real-world test) ────────────────────────────────────────────────┤
                                                                          ▼
                                                            FULL END-TO-END WORKING
```

**Phases 1 and 2 can run in parallel.** They have no dependency on each other (audio sync needs the variable frame counts from Phase 2, but you can build audio_sync.py first and integrate it after Phase 2 lands).

**Phase 3 (real-world test) is independent** — could be done anytime after Phase 2 lands.

---

## Decision points along the way

These are choices to make as you go:

| Phase | Decision | Default |
|---|---|---|
| 1 | Beat granularity | half_bar (2 beats) |
| 1 | Drift handling | per-shot accuracy over total accuracy |
| 1 | Drop shot default | designated by config, default = "longest of last 4 shots" |
| 2 | Where to put SHOTS dict | motion_table.json (single source of truth) |
| 3 | Preset architecture | one preset, tune via per-shot config |
| 3 | Real-world filter stack | start with same defaults, add only if needed |
| 4 | Confidence threshold for verification flags | LK + Farneback disagree on direction → flag |
| 5 | Prompt format | markdown with frontmatter for tool-specific notes |
| 6 | Brief format | YAML (already locked in BRAINSTORM_PROCESS.md) |
| 7 | Preset reference syntax | `{"preset": "name"}` in per_shot_config.json |

---

## Estimated timelines

| Phase | Optimistic | Realistic | Pessimistic |
|---|---|---|---|
| 1 (audio) | 2 hr | 3.5 hr | 6 hr |
| 2 (var count) | 1.5 hr | 2 hr | 3 hr |
| 3 (real-world test) | 1 hr | 1.5 hr | 4 hr |
| 4 (analyze.sh) | 1.5 hr | 2 hr | 3 hr |
| 5 (prompt gen) | 1 hr | 1.5 hr | 2 hr |
| 6 (validate) | 0.5 hr | 1 hr | 2 hr |
| 7 (presets) | 0.5 hr | ongoing | ongoing |
| **Total** | **8 hr** | **12 hr** | **20 hr** |

Realistic: ~3-4 focused sessions to reach full production system.

---

## What "done" looks like

When the roadmap is complete, the workflow will be:

```bash
# 1. Brainstorm with Claude → output: brief.yaml (15 min conversation)

# 2. Optionally analyze a reference video for shot inspiration
./pipeline/analyze.sh reference_video.mp4 ./refs/

# 3. Generate prompts from the brief
./pipeline/generate_prompts.py brief.yaml refs/motion_table.json prompts.md

# 4. Generate AI stills (manual, in your image tool of choice)

# 5. Make the final video with audio sync
./pipeline/make_video.sh ai_stills/ output.mp4 \
    --config refs/per_shot_config.json \
    --audio song.mp3

# Output: 1080x1920 24fps Reel-ready mp4 with cuts on the beat
```

Total time per new video, once everything is built: **~30-60 minutes** (mostly waiting for AI image generation).
