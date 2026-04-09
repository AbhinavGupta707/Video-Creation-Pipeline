# Audio-driven shot planning — Final Plan

> Synthesis of 4 parallel research agents (libraries, prior art, audio LLMs, editing craft).
> Replaces the earlier Tier 1–4 sketch with the architecture the research actually supports.

---

## 1. Convergent findings

Four independent research passes all converge on the same conclusions:

1. **`allin1` is the backbone.** Single model returns BPM + beats + downbeats + section boundaries + functional labels (intro/verse/chorus/bridge/break/inst/solo/outro) in one inference pass. SOTA on Harmonix (still un-beaten as of 2026). Internally demixes via Demucs, which is *the* reason it beats librosa/madmom on EDM and phonk.
2. **`beat_this` replaces madmom.** ISMIR 2024, pure PyTorch, MPS-friendly, no Cython hell, beats madmom on F1 across every standard benchmark. We never install madmom.
3. **No end-to-end "audio → cut plan" model exists.** Every audio LLM (Qwen2-Audio, Gemini, GPT-4o) hallucinates timestamps. They are **only** useful as re-rankers over heuristic candidates.
4. **CLAP can replace the LLM tier entirely.** Zero-shot text↔audio scoring lets us rate audio windows against prompts like *"heavy bass drop"* / *"snare roll buildup"* deterministically and fast. Better than calling an LLM.
5. **Stem separation before beat tracking helps.** Quantitatively measured: ~+5% F1 on full mix, much more on drum-sparse genres. allin1 already does this internally; we add `drumsep` (kick/snare/hat split) for explicit drop detection.
6. **Cut placement rules are codifiable.** Agent 4 produced a complete rulebook (R1.1–R10.3 + V1–V8) covering Murch's Rule of Six, beat/bar/phrase granularity, mode classification (phonk vs cinematic), section→density mapping, veto rules. This is the core of the planner.

---

## 2. The pivot

**Old plan:** 4 escalating tiers (librosa → demucs → madmom → LLM critic), each tier a strict superset.

**New plan:** 4 ablation tiers that share a common rule-based planner. We swap the **audio analysis backbone**, hold the planner constant, measure how much each backbone matters. Then in Tier 4 we add a re-ranker layer.

This is a cleaner experimental design — it isolates which component drives accuracy.

| Tier | Backbone | Drop detection | Re-ranker | Expected F1 vs taps |
|---|---|---|---|---|
| **T1 — Librosa baseline** | `librosa.beat.beat_track` + onset_strength + RMS | RMS spike on full mix | none | ~0.60 |
| **T2 — allin1 structure** | `allin1` (BPM + beats + downbeats + sections) | RMS on Demucs `bass` stem (free from allin1) | none | ~0.80 |
| **T3 — Stem-aware drops** | `allin1` + `beat_this` cross-check | `drumsep` kick stem energy delta on bar boundaries | none | ~0.87 |
| **T4 — Re-ranked** | T3 stack | T3 detector | **CLAP zero-shot** + optional Anthropic SDK critic | ~0.92 |

The same `planner.py` (encoding Agent 4's rulebook) consumes whichever backbone JSON. Easy to swap.

---

## 3. Architecture

```
                    ┌─────────────────────────┐
                    │   audio/N.mp3           │
                    └───────────┬─────────────┘
                                ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 1 — AUDIO ANALYSIS BACKBONE           │
        │   (one of: librosa | allin1 | allin1+stems)  │
        │   outputs: beats, downbeats, sections,       │
        │            energy curves per stem            │
        └───────────┬──────────────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 2 — FEATURE JSON                      │
        │   bpm, beats[], downbeats[], sections[],     │
        │   energy_curve[], drop_candidates[],         │
        │   onset_strength[], mode (phonk|cinematic)   │
        └───────────┬──────────────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 3 — RULE-BASED PLANNER                │
        │   Encodes Agent 4 rulebook:                  │
        │    R1: Murch weighting                       │
        │    R2: section→density mapping               │
        │    R3: beat/bar/phrase granularity           │
        │    R7: phonk vs cinematic mode                │
        │    R9: dynamic arc (hook→build→peak→tail)    │
        │    R10: shot count formula                   │
        │    V1-V8: veto rules                         │
        │   outputs: candidate cut points + N_target   │
        └───────────┬──────────────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 4 — RE-RANKER (Tier 4 only)           │
        │   CLAP scores each candidate against         │
        │   prompts: "drop hit", "buildup peak",       │
        │   "section transition". Optional Anthropic   │
        │   SDK critic over the JSON plan.             │
        └───────────┬──────────────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 5 — SHOT PLAN JSON                    │
        │   { n_shots, cut_points, shot_durations,     │
        │     shot_kinds, drop_at, mode,               │
        │     frame_counts (for renderer) }            │
        └───────────┬──────────────────────────────────┘
                    ▼
        ┌──────────────────────────────────────────────┐
        │  STAGE 6 — BENCHMARK                         │
        │   Compare every tier vs user taps using      │
        │   F1, mean cut distance, count error,        │
        │   density correlation, end alignment.        │
        │   Generate click-track audio for ear-test.   │
        └──────────────────────────────────────────────┘
```

---

## 4. The rulebook (encoded from Agent 4)

The planner is deterministic and small (~400 LOC). Core rules it encodes:

### Mode classification (R7.1)
```
if bpm >= 125 and bass_distortion > threshold: mode = "phonk"
elif bpm <= 100 and rms_dynamic_range < threshold: mode = "cinematic"
else: mode = "hybrid"
```

### Shot count target (R10.2)
```
mode_factor = {"cinematic": 0.25, "hybrid": 0.5, "phonk": 0.9}[mode]
n_target = clamp(length_s * bpm/60 * mode_factor, 6, 36)
```

### Section→density mapping (R2.1–R2.5)
```
density_per_bar = {
    "intro":  0.25–0.5,
    "verse":  0.5–1.0,
    "build":  accelerating 0.5→2.0,
    "drop":   1.0–2.0 (phonk: up to 4 for ≤4 bars),
    "break":  0.5,
    "outro":  long held final shot
}
```

### Granularity ladder (R3)
```
phrase_cut > downbeat_cut > snare_cut > beat_cut > 1/16_lift
```
Phrase cuts dominate intros/outros. Bar cuts dominate verses. Beat/snare cuts dominate drops.

### Veto rules (V1–V8)
- V1: cut > 2 frames off grid
- V4: shot < 0.2s or > 6s
- V5: 5+ consecutive same-granularity cuts
- V7: cut on top of a riser (kills tension before drop)
- ... etc

### Hard ceilings
- Max 3 cuts/sec (R2.6)
- Min shot length 6 frames (R2.7)
- Final shot ends on last downbeat + 0.5–1s tail (R9.4)

---

## 5. File layout

```
pipeline/
  audio_plan/
    __init__.py
    backbones/
      librosa_backbone.py     # Tier 1
      allin1_backbone.py      # Tier 2 + 3
      stem_aug.py             # drumsep wrapper for Tier 3
    planner.py                # Stage 3 — rulebook (shared by all tiers)
    rerank/
      clap_reranker.py        # Tier 4 CLAP scoring
      llm_critic.py           # Tier 4 optional Anthropic SDK
    schemas.py                # FeatureJSON, ShotPlan dataclasses
  benchmark/
    metrics.py                # F1, mean dist, density corr, etc.
    run_all.py                # all tiers × all tracks → comparison.csv
    click_track.py            # generate audible cut markers for ear test
  audio_plan_cli.py           # entry point: plan_shots <track> --tier N
Audio/
  AUDIO_TAPS.md               # ground truth (already written)
  audio 1.mp3 ...             # 5 tracks
docs/
  AUDIO_PLAN.md               # this file
```

The existing `pipeline/audio_sync.py` becomes obsolete and gets archived.

---

## 6. Risk register

| Risk | Mitigation |
|---|---|
| **`allin1` install fails on Apple Silicon** (NATTEN compile) | Try official wheels first, fall back to `all-in-one-mlx` fork, last resort: stay on Tier 1+`beat_this` only |
| **`allin1` pulls madmom transitively + numpy<2 conflict** | Use a sidecar venv `.venv-audio` with pinned `numpy<2`. Main `.venv` (renderer) stays on numpy 2.0. |
| **Section labels unreliable on phonk/cinematic** (Harmonix is pop-trained) | Cross-check with raw novelty curve, fall back to RMS-based section detection if labels look wrong |
| **CLAP scores noisy** | Use as a soft re-ranker (delta of ±2 cuts), not a hard filter |
| **Only 4 tapped tracks → low statistical power** | Report per-track metrics, not just means; visualize cut alignment per track; user listens to click tracks for subjective check |
| **`claude` CLI not installed → no LLM critic** | Use Anthropic Python SDK directly with `ANTHROPIC_API_KEY` env var, OR drop the LLM critic entirely (CLAP alone may be sufficient) |
| **Tier 4 LLM API requires key user doesn't have** | If no key, Tier 4 runs CLAP-only and we report it as "Tier 4a CLAP-only" + skip LLM variant |

---

## 7. Open decisions you need to make

### D1 — Sidecar venv OK?
`allin1` requires `numpy<2`. Your main `.venv` has `numpy==2.0`. Cleanest fix: create `.venv-audio` with Python 3.11 + numpy<2 + allin1 + beat_this + drumsep + CLAP. Renderer stays in `.venv`. Two venvs, two purposes.

**Need your OK to install:**
- `brew install python@3.11` (if not already present)
- New venv at `.venv-audio`

### D2 — LLM critic source
Three options for Tier 4 LLM:
- **(a) CLAP only (no LLM)** — fully local, free, deterministic, good enough per research
- **(b) Anthropic SDK + API key** — best quality but needs `ANTHROPIC_API_KEY`. Do you have one?
- **(c) Local Qwen2-Audio-7B** — ~16GB download, runs on MPS, slow

My recommendation: **(a) CLAP only.** Research says LLMs hallucinate timestamps and add little value over CLAP for this specific task. Keeps everything local. We can add (b) later if results disappoint.

### D3 — Test track 4 — generate auto-plan and you eyeball/listen?
The held-out track has no taps. After all tiers run, I'll generate a click-track mp3 (audio + tick on each planned cut) for each tier on track 4. You listen, pick the winner. This is the held-out subjective evaluation. OK?

### D4 — Drop / archive existing `audio_sync.py`?
The earlier half-bar-quantizer is now obsolete. I'll move it to `pipeline/_archive/audio_sync_v1.py` with a note. OK?

### D5 — Render comparison videos?
After picking the winning tier per track, do you want me to actually render a video for each (using existing wine ferrari stills) so you can watch the result? Or just judge from click-track audio?

---

## 8. Build order

| Step | Effort | Output |
|---|---|---|
| **0** Resolve D1–D5 | 5 min (your call) | green light to install |
| **1** Set up `.venv-audio` + install allin1, beat_this, drumsep, CLAP | 30 min | working sidecar venv |
| **2** Build `schemas.py` (FeatureJSON, ShotPlan dataclasses) | 15 min | type-safe data flow |
| **3** Build `planner.py` (the rulebook) | 2 h | shared planner all tiers use |
| **4** Build `librosa_backbone.py` (Tier 1) | 30 min | T1 working end-to-end |
| **5** Build `allin1_backbone.py` (Tier 2) | 1 h | T2 working |
| **6** Build `stem_aug.py` + Tier 3 wiring | 1 h | T3 working |
| **7** Build `clap_reranker.py` (Tier 4) | 1 h | T4 working |
| **8** Build `metrics.py` + `benchmark/run_all.py` | 1 h | comparison table |
| **9** Build `click_track.py` | 30 min | audible ear-test mp3s |
| **10** Run benchmark on all 4 tracks × 4 tiers | 30 min | results CSV + plots |
| **11** Generate held-out click tracks for track 4 | 10 min | subjective test |
| **12** Write `RESULTS.md` with winner + recommendations | 30 min | decision document |

**Total: ~9 hours focused work.** I'll commit each step atomically so you can review progress.

---

## 9. Success criteria

The plan succeeds if:

1. At least one tier achieves **mean F1 ≥ 0.85** across the 4 tapped tracks (the threshold where cuts feel "right" to humans)
2. Mean cut distance is **< 150ms** for the winning tier
3. Count error `|N_pred − N_user| ≤ 1` on at least 3 of 4 tracks
4. The held-out track 4 click-track sounds right to your ear
5. The winning tier installs cleanly enough to be reproducible

If we hit all 5, we ship the winning tier as the production planner and integrate it into `make_video.sh` (replacing the current `audio_sync.py`). Phase 1 is properly done.

If we miss → we know exactly which tier failed and where, and we can iterate.

---

## 10. References

All cited in the agent reports — full list in `/private/tmp/.../tasks/*.output`. Highlights:

- [allin1 paper](https://arxiv.org/abs/2307.16425) / [GitHub](https://github.com/mir-aidj/all-in-one)
- [beat_this paper](https://arxiv.org/abs/2407.21658) / [GitHub](https://github.com/CPJKU/beat_this)
- [AutoMV (closest prior art)](https://arxiv.org/html/2512.12196v1)
- [Foote 2002 (canonical novelty)](https://dl.acm.org/doi/10.1145/1027527.1027641)
- [LAION CLAP](https://github.com/LAION-AI/CLAP)
- [drumsep](https://github.com/inagoy/drumsep)
- Walter Murch — *In the Blink of an Eye*
