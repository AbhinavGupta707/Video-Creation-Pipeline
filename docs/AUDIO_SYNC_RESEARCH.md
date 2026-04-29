# Audio Sync — Deep Research & Implementation Plan

> **Status:** Research complete, ready to implement in next session.
> **Context:** Car commercial Instagram Reels live and die on cut timing. If shot transitions don't land on beats/drops, the video feels amateur. This document contains everything needed to implement professional beat-driven editing.

---

## Part 1 — Why this is THE most important polish step

### The perception fact
Human brains automatically expect visual transitions to align with strong audio events (beats, drops, snares). When they don't, the result feels "off" even if the viewer can't articulate why. **A perfectly-rendered video with mistimed cuts feels worse than a roughly-rendered video with perfect cuts.**

### What car commercials actually do
Watch any high-budget car commercial and notice:
- Shots cut on the downbeat (beat 1 of every bar)
- The "hero reveal" lands on a drop
- The final shot resolves on the last bar
- Match cuts (rear→front symmetry) often happen on a snare hit, not a kick

### What goes wrong without sync
- Cuts feel "early" or "late" by 50-200ms — viewer registers it subconsciously
- Hero reveal happens DURING a build-up, not on the drop → emotional payoff is missed
- Final shot ends mid-bar → song feels unresolved → video feels unfinished

---

## Part 2 — The fundamental tension

Our wine ferrari pipeline has **fixed shot durations** derived from analyzing the original video:

```
Shot 1: 2.262s
Shot 2: 2.261s
Shot 3: 2.179s
Shot 4: 2.180s
Shot 5: 0.904s
Shot 6: 1.152s
Shot 7: 1.069s
Shot 8: 1.181s
Total:  13.187s
```

For beat sync, these durations need to align to musical beats. **They don't naturally — most music will land cuts mid-beat.**

There are three ways to resolve this:

### Approach A: Adjust shots to fit beats
Stretch or shrink each shot's duration to the nearest beat boundary. Loses fidelity to original timing but gains musical coherence.

### Approach B: Pick music whose BPM matches existing durations
Find music whose beat structure naturally aligns with our 8 shot durations. Constrains music choice but preserves original timing.

### Approach C: Hybrid
Pick music that's CLOSE to natural alignment, then make small adjustments to a few shot durations to nail the alignment.

**My recommendation: Approach C (hybrid)** because it preserves most of the original timing intent while achieving musical sync. Pure approach A creates choppy timing changes; pure approach B over-constrains music selection.

---

## Part 3 — The math of beats and bars

### Definitions
- **BPM** (beats per minute) — tempo of the song. Common car commercial range: 100-150 BPM
- **Beat** — one rhythmic pulse. At 120 BPM, beat = 60/120 = 0.5 seconds
- **Bar** (or measure) — 4 beats in standard time. At 120 BPM, bar = 2.0 seconds
- **Phrase** — 4 or 8 bars typically. At 120 BPM, 8-bar phrase = 16.0 seconds
- **Downbeat** — beat 1 of a bar (the strongest)
- **Drop** — the moment where the bass enters or the energy explodes. Usually on a downbeat at the start of a phrase.

### Wine ferrari analysis
Total duration: 13.187s
Average shot: 1.65s

Let's check what BPMs naturally align:

| BPM | Beat duration | Bar duration | Avg shot in beats | Avg shot in bars |
|---|---|---|---|---|
| 120 | 0.500s | 2.000s | 3.30 | 0.825 |
| 130 | 0.462s | 1.846s | 3.57 | 0.894 |
| 140 | 0.429s | 1.714s | 3.85 | 0.962 |
| **145** | **0.414s** | **1.655s** | **3.99** | **0.998** ⭐ |
| 150 | 0.400s | 1.600s | 4.13 | 1.031 |

**At 145 BPM, the average shot is almost exactly 1 bar.** This is the natural sync point for wine ferrari structure.

### Per-shot bar alignment at 145 BPM (bar = 1.655s)

| Shot | Original | Bars | Quantized to bars | Quantized duration | Drift |
|---|---|---|---|---|---|
| 1 | 2.262s | 1.367 | 1.5 bars | 2.483s | +0.221s |
| 2 | 2.261s | 1.366 | 1.5 bars | 2.483s | +0.222s |
| 3 | 2.179s | 1.317 | 1.0 bars | 1.655s | -0.524s |
| 4 | 2.180s | 1.317 | 1.5 bars | 2.483s | +0.303s |
| 5 | 0.904s | 0.546 | 0.5 bars | 0.828s | -0.076s |
| 6 | 1.152s | 0.696 | 0.5 bars | 0.828s | -0.324s |
| 7 | 1.069s | 0.646 | 0.5 bars | 0.828s | -0.241s |
| 8 | 1.181s | 0.714 | 1.0 bars | 1.655s | +0.474s |
| **Total** | **13.187s** | **7.969** | **8.0 bars** | **13.241s** | **+0.054s** |

Interesting result: at 145 BPM, the total naturally lands on 8 bars (~13.24s) with the original total at 13.19s (only 54ms off). This suggests **the wine ferrari was likely cut to 145 BPM music to begin with.**

But individual shots have significant drift (up to 524ms on shot 3). Pure quantization to bar boundaries would change timings noticeably.

### A better strategy: half-bar quantization

Half bars (2 beats) at 145 BPM = 0.828s. Finer granularity:

| Shot | Original | Half-bars | Quantized | Drift |
|---|---|---|---|---|
| 1 | 2.262s | 2.73 | 3 (1.5 bar) | -0.221s |
| 2 | 2.261s | 2.73 | 3 (1.5 bar) | -0.222s |
| 3 | 2.179s | 2.63 | 3 (1.5 bar) | -0.304s |
| 4 | 2.180s | 2.63 | 3 (1.5 bar) | -0.303s |
| 5 | 0.904s | 1.09 | 1 (0.5 bar) | +0.076s |
| 6 | 1.152s | 1.39 | 1 (0.5 bar) | +0.324s |
| 7 | 1.069s | 1.29 | 1 (0.5 bar) | +0.241s |
| 8 | 1.181s | 1.43 | 2 (1 bar) | -0.474s |
| **Total** | **13.187s** | | **17 half-bars = 8.5 bars** | -1.083s |

Total of 8.5 bars = 14.07s. ~880ms longer than original. Each shot rounded to nearest half-bar.

**Drift acceptable?** Mostly yes — under ~300ms is invisible to the viewer. Shots 6 (+324ms) and 8 (-474ms) push the threshold but might still feel right because they're close-ups where the brain has less timing reference.

### The final approach: smart beat alignment

**Pseudocode for the actual implementation:**

```python
def align_shots_to_beats(shot_durations, bpm, granularity='half_bar'):
    """
    Returns adjusted shot durations that align to musical beats.

    granularity:
      'beat'      - finest, each shot is whole beats
      'half_bar'  - 2-beat groups (default — best for car commercials)
      'bar'       - 4-beat groups (very rigid)
    """
    beat_duration = 60.0 / bpm
    grain = {
        'beat': beat_duration,
        'half_bar': beat_duration * 2,
        'bar': beat_duration * 4,
    }[granularity]

    aligned = []
    cumulative_drift = 0
    for d in shot_durations:
        # Adjust target by accumulated drift to prevent drift accumulation
        target = d - cumulative_drift
        n_grains = max(1, round(target / grain))
        new_d = n_grains * grain
        cumulative_drift += (new_d - d)
        aligned.append(new_d)
    return aligned
```

The cumulative drift correction is important — without it, errors compound and the total length drifts off.

---

## Part 4 — Detecting beats and drops in the music

### Tool: librosa (Python audio analysis)

```bash
.venv/bin/pip install librosa
```

~50MB install. Includes numpy/scipy/scikit-learn deps.

### Beat tracking

```python
import librosa

y, sr = librosa.load("song.mp3", sr=22050)
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beat_frames, sr=sr)

print(f"Tempo: {tempo} BPM")
print(f"Beats: {beat_times}")  # array of timestamps in seconds
```

Returns: estimated BPM (single number) + array of beat timestamps. Works on most music.

**Accuracy notes:**
- Works great on music with strong percussive content (rock, EDM, hip-hop)
- Struggles on jazz, classical, ambient, or anything with rubato
- Can sometimes report HALF or DOUBLE the true tempo (octave error)

### Onset detection (alternative to beats)

```python
onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
```

Returns ALL percussive events, not just beats. Useful for identifying snares, claps, transients that you might want to cut on.

### Detecting drops specifically

This is harder. A "drop" is a structural feature, not a single beat. Two approaches:

**Approach 1: Energy spike detection**
```python
import numpy as np
# RMS energy over time
rms = librosa.feature.rms(y=y)[0]
rms_times = librosa.times_like(rms, sr=sr)

# A drop is a sudden large increase in RMS following a quieter section
# Find peaks where rms[i] > 1.5 × rms[i-N]
```

This catches loud moments but doesn't always correspond to musical drops.

**Approach 2: Spectral novelty / segmentation**
```python
# Self-similarity matrix → segment boundaries
mfcc = librosa.feature.mfcc(y=y, sr=sr)
boundaries = librosa.segment.agglomerative(mfcc, k=8)
boundary_times = librosa.frames_to_time(boundaries, sr=sr)
```

Returns timestamps where the song structure changes (intro→verse, verse→chorus, build→drop). Better for finding drops semantically.

**Approach 3: Manual annotation**
For a 13-second clip, you can just LISTEN and mark the drop timestamp manually. Takes 30 seconds, 100% accurate.

**My recommendation: combine automatic detection with manual override.** Auto-detect by default, allow user to override the drop timestamp via CLI flag.

### Drop placement strategy

Once we know the drop timestamp, we want to ensure a SHOT TRANSITION lands on it. Options:

1. **Hero shot starts on drop** — the hero reveal (shot 7 in wine ferrari) coincides with the drop. Maximum emotional payoff.
2. **Final shot starts on drop** — the final detail bookend (shot 8) explodes on the drop. Good for "closing release" feel.
3. **First shot starts on drop** — drop at t=0, video opens on the impact. Less common but impactful.

For wine ferrari: hero reveal (shot 7) at 10.94s. If we align shot 7 START to a drop at exactly 10.94s, we'd need a song with a drop at that time. UNLIKELY to find one. So we'd need to either:
- Find music with a drop somewhere ELSE and rearrange shots so the hero lands on it
- Adjust shot durations so shot 7 starts AT the drop time of a chosen song
- Or accept that the drop is a random beat, not necessarily "the drop"

**The cleanest solution: adjust the START times of one or two key shots so they land on drops.** All other shots quantize normally to beats.

---

## Part 5 — The full sync architecture

```
┌─────────────────────────────────────────────────────────┐
│  USER PROVIDES:                                          │
│   - 8 stills (shot1.jpg .. shot8.jpg)                    │
│   - motion_table.json (shot durations from analysis)     │
│   - per_shot_config.json (motion tuning)                 │
│   - music_track.mp3                                      │
│   - (optional) drop_time_override = 10.5 (seconds)       │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: ANALYZE MUSIC                                   │
│   librosa.beat.beat_track → BPM + beat_times             │
│   librosa.feature.rms → drop candidates                  │
│   (or use user-provided drop_time)                       │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: DETERMINE SYNC STRATEGY                         │
│   - bar_duration = 4 × (60 / BPM)                        │
│   - check natural alignment of shot durations            │
│   - select granularity (beat / half-bar / bar)           │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: ADJUST SHOT DURATIONS                           │
│   - quantize each shot to nearest grain                  │
│   - apply cumulative drift correction                    │
│   - if drop_time provided: shift adjacent shots so the   │
│     designated "drop shot" starts at drop_time           │
│   - output: adjusted_shot_durations                      │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: RECOMPUTE FRAME COUNTS                          │
│   - new_frame_count = round(adjusted_duration × fps)     │
│   - update SHOTS dict before rendering                   │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: RENDER (existing pipeline)                      │
│   render_v2.py uses adjusted frame counts                │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: AUDIO OVERLAY                                   │
│   ffmpeg -i video.mp4 -i music.mp3                       │
│     -map 0:v -map 1:a                                    │
│     -c:v copy -c:a aac                                   │
│     -shortest output.mp4                                 │
└─────────────────────────────────────────────────────────┘
```

---

## Part 6 — Implementation files needed

### `pipeline/audio_sync.py` (NEW)

Functions:
- `analyze_track(path)` → `{bpm, beat_times, drop_candidates, duration}`
- `align_shots_to_beats(durations, bpm, granularity='half_bar', drop_anchor=None)` → `adjusted_durations`
- `compute_frame_counts(durations, fps)` → list of int frame counts

### `pipeline/render_v2.py` (UPDATE)

- Accept `frame_counts` override (currently hardcoded in `SHOTS` dict)
- Currently `SHOTS[i]['frames']` is fixed; needs to come from per-shot config or audio_sync output

### `pipeline/make_video.sh` (UPDATE)

New options:
- `--audio <file.mp3>` → enable audio sync
- `--bpm-override N` → manual BPM if librosa fails
- `--drop-at <seconds>` → manual drop timestamp
- `--drop-shot <N>` → which shot should land on the drop (default 7 = hero)
- `--granularity beat|half_bar|bar` → quantization grain (default half_bar)

---

## Part 7 — Open questions to resolve in next session

1. **Should drift correction prioritize total duration or per-shot accuracy?**
   Per-shot accuracy means total drifts. Total accuracy means per-shot can drift more. **My default: per-shot (humans notice rhythm, not total length).**

2. **Should the renderer support "drop emphasis" (extra zoom kick on the drop shot)?**
   Real editors often add a quick zoom-in or whip-pan ON the drop. Could be a per-shot config field: `"drop_emphasis": true`. **Defer until basic sync works.**

3. **What if librosa reports the wrong BPM (octave error)?**
   - 60 BPM detected when actual is 120 BPM → halve durations
   - 240 BPM detected when actual is 120 BPM → double durations
   - Solution: require user to confirm BPM in CLI output, allow `--bpm-override`

4. **For new videos, do we adjust SHOTS to fit MUSIC, or pick MUSIC to fit SHOTS?**
   Both directions are valid. Rule of thumb:
   - If you have a creative shot list and music is open → adjust music BPM to natural alignment of shots
   - If you have a specific song you must use → adjust shots to fit beats
   - **Most flexible: build the tool to support both directions**

5. **Should the system automatically pick which shot lands on the drop?**
   Heuristic: drop = the most visually impactful shot. For wine ferrari that's shot 7 (hero). For a different video it might be different. **Default to "the longest of the last 4 shots" as the drop shot, allow override.**

6. **Multi-drop songs (intro drop + main drop)?**
   Some songs have multiple drops. Pick the strongest and align the hero to it. Other drops just play through without forced sync. **First implementation: handle single-drop case only.**

7. **What about the END of the video — should it land on a bar boundary?**
   YES. The total video should end on a downbeat, not mid-bar. Add a constraint to the alignment algorithm: total duration must be a whole number of bars.

---

## Part 8 — Recommended implementation order for next session

| Step | Time | Deliverable |
|---|---|---|
| 1 | 5 min | `pip install librosa` |
| 2 | 30 min | `audio_sync.py` with `analyze_track()` and `align_shots_to_beats()` |
| 3 | 15 min | Test on 3-5 music tracks, verify BPM detection works |
| 4 | 30 min | Update `render_v2.py` to accept per-shot frame_count overrides |
| 5 | 15 min | Update `make_video.sh` with `--audio`, `--bpm-override`, `--drop-at`, `--drop-shot` flags |
| 6 | 30 min | Audio overlay step in make_video.sh (ffmpeg final mux) |
| 7 | 30 min | Test on wine ferrari with 2-3 different songs, verify sync feels right |
| 8 | 1 hour | Iterate: tune drift handling, granularity defaults, edge cases |

**Total: ~3.5 hours.** Realistic for one focused session.

---

## Part 9 — A concrete first test plan

Once built, validate with these specific tests:

1. **No music** — render wine ferrari with no audio. Should match current `test_output_tuned.mp4` exactly.
2. **Music at 145 BPM** — should naturally align with minimal drift. Verify cuts feel "on the beat."
3. **Music at 90 BPM** — slow song. Each shot should be ~2 bars. Verify the algorithm scales.
4. **Music with manual drop at t=10.94** — should ensure shot 7 starts exactly there. Verify other shots adjusted to compensate.
5. **Wrong BPM detection** — manually feed `--bpm-override 60` when track is 120. Should produce visibly wrong sync. Verify the override works.

---

## Part 10 — Things NOT to do (lessons from car commercial editing)

- **Don't sync EVERY cut to a beat.** Some shots benefit from "floating" between beats for breathing room. The HERO should be on a beat; transitional cuts can drift slightly.
- **Don't pick music with constantly changing tempo.** Rubato kills beat detection.
- **Don't use songs longer than the video.** Shorter clips don't need full songs. Use a 15-30s instrumental section, not a 3-min track.
- **Don't fade audio at arbitrary points.** Always fade on a beat boundary.
- **Don't ignore the song's INTRO.** A song that starts with 2 seconds of build-up before the first beat needs `--audio-offset 2.0` or you'll waste the intro on a static frame.

---

## TL;DR for next session

1. Read this doc top to bottom (~10 min)
2. Install librosa
3. Build `audio_sync.py` per the architecture in Part 5
4. Update `render_v2.py` and `make_video.sh` per the file list in Part 6
5. Test on wine ferrari with the 5 tests in Part 9
6. Tune defaults, ship

**You're aiming for the experience: `./pipeline/make_video.sh stills/ output.mp4 --audio song.mp3` and the cuts magically land on the beat.**
