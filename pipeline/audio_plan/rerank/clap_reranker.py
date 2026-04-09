"""Tier 4: CLAP zero-shot re-ranker.

For each existing cut in the plan, score the 1.5s audio window centred on it
against text prompts that describe what makes a good cut. Use the score to
nudge cut times toward the highest-scored nearby beat (within ±2 beats).

This is a SOFT refinement — we never add or remove cuts, only shift them to
the local maximum.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np

from ..schemas import FeatureJSON, Shot, ShotPlan


PROMPTS = [
    "a heavy bass drop",
    "a punchy snare hit",
    "a kick drum impact",
    "an energetic transition between sections",
    "a build-up resolving into a chorus",
]


_model_cache: dict[str, object] = {}


def _load_clap():
    if "model" in _model_cache:
        return _model_cache["model"]
    import laion_clap
    # HTSAT-tiny matches the default downloadable checkpoint (630k-best)
    model = laion_clap.CLAP_Module(enable_fusion=False, amodel="HTSAT-tiny")
    model.load_ckpt()
    _model_cache["model"] = model
    return model


def _score_window(model, audio: np.ndarray, sr: int) -> float:
    """Mean similarity between audio window and the cut-quality prompts."""
    import torch
    with torch.no_grad():
        audio_emb = model.get_audio_embedding_from_data(x=audio[None, :], use_tensor=False)
        text_emb = model.get_text_embedding(PROMPTS, use_tensor=False)
        # cosine sim
        a = audio_emb / (np.linalg.norm(audio_emb, axis=-1, keepdims=True) + 1e-6)
        t = text_emb / (np.linalg.norm(text_emb, axis=-1, keepdims=True) + 1e-6)
        sims = (a @ t.T).flatten()  # shape (5,)
        return float(np.mean(sims))


def rerank(plan: ShotPlan, feat: FeatureJSON,
           window_sec: float = 1.5) -> ShotPlan:
    """Shift each interior cut to the highest-scored beat within ±2 beats."""
    if len(plan.shots) <= 2:
        return plan

    try:
        import librosa
        model = _load_clap()
    except Exception as e:
        print(f"  CLAP unavailable ({e}); returning plan unchanged")
        plan.notes.append(f"clap_skipped:{e}")
        return plan

    y, sr = librosa.load(feat.track_path, sr=48000, mono=True)  # CLAP wants 48k
    beat_dur = 60.0 / max(feat.bpm, 1)
    cut_times = [s.start for s in plan.shots[1:]]  # exclude first
    new_cuts: list[float] = []

    beats = np.asarray(feat.beats, dtype=float)

    for ct in cut_times:
        # Candidate beats within ±2 beats of current cut
        if len(beats) == 0:
            new_cuts.append(ct)
            continue
        nearby = beats[np.abs(beats - ct) <= 2 * beat_dur]
        if len(nearby) == 0:
            new_cuts.append(ct)
            continue
        # Score each candidate
        best_t = ct
        best_score = -1.0
        for cand in nearby:
            i0 = max(0, int((cand - window_sec / 2) * sr))
            i1 = min(len(y), int((cand + window_sec / 2) * sr))
            if i1 - i0 < int(0.5 * sr):
                continue
            window = y[i0:i1].astype(np.float32)
            try:
                s = _score_window(model, window, sr)
            except Exception:
                continue
            if s > best_score:
                best_score = s
                best_t = float(cand)
        new_cuts.append(best_t)

    # Re-sort + dedupe
    new_cuts = sorted(set(round(t, 4) for t in new_cuts))
    boundaries = [0.0] + new_cuts + [feat.duration]
    new_shots: list[Shot] = []
    for i in range(len(boundaries) - 1):
        old = plan.shots[min(i, len(plan.shots) - 1)]
        new_shots.append(Shot(
            index=i,
            start=boundaries[i],
            end=boundaries[i + 1],
            section_label=old.section_label,
            energy=old.energy,
            granularity=old.granularity,
        ))
    plan.shots = new_shots
    plan.n_shots = len(new_shots)
    plan.notes.append(f"clap_reranked windows={window_sec}s")
    return plan
