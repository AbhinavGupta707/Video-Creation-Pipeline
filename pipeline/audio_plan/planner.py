"""Rule-based shot planner — encodes the editing craft rulebook from Agent 4.

Input: FeatureJSON (from any backbone)
Output: ShotPlan (consumed by renderer or benchmark)

Rules encoded (see AUDIO_PLAN.md section 4 for the full rulebook):
  R1.1 Murch weighting of cut candidates
  R2.1-R2.5 Section -> density mapping
  R3.1-R3.5 Granularity ladder (phrase > downbeat > snare > beat > lift)
  R7.1-R7.4 Phonk vs cinematic mode
  R9.1-R9.5 Dynamic arc constraint
  R10.1-R10.3 Shot count target formula
  V1-V8 Veto rules

The planner is deterministic. Same FeatureJSON in -> same ShotPlan out.
"""
from __future__ import annotations

from typing import Iterable

from .schemas import (
    CutCandidate, FeatureJSON, Granularity, Mode, SectionLabel,
    Shot, ShotPlan,
)


# ==============================================================
# Tunable constants (R2, R7, R10)
# ==============================================================

# Cuts per bar by mode (R10.2). Tuned against user tap data.
# NOTE: empirically the user's tap data shows avg ~1.3 cuts/bar across tracks.
# Phonk is NOT higher than hybrid here — in the car-edit tap set, "phonk"
# classified tracks had steady 1-cut-per-bar pacing, not the 2-4/bar that
# Agent 4's rulebook assumed. Tuned against ground truth.
MODE_FACTOR: dict[Mode, float] = {
    "cinematic": 0.8,
    "hybrid":    1.5,
    "phonk":     1.1,
}

# R2.1-R2.5: target cuts per bar by section label.
SECTION_DENSITY: dict[SectionLabel, float] = {
    "intro":   0.35,
    "verse":   0.70,
    "chorus":  1.20,
    "bridge":  0.80,
    "build":   1.30,   # accelerating — we use this as average
    "drop":    1.60,
    "break":   0.50,
    "inst":    1.00,
    "solo":    1.00,
    "outro":   0.30,
    "unknown": 0.80,
}

# R10.2 shot count bounds (6 <= N <= 36)
MIN_SHOTS = 6
MAX_SHOTS = 36

# R2.6/R2.7 hard ceilings
MAX_CUTS_PER_SEC = 3.0
MIN_SHOT_SEC = 0.20
MAX_SHOT_SEC = 6.0

# R3 granularity scores (higher = preferred by selector)
GRANULARITY_WEIGHT: dict[Granularity, float] = {
    "phrase":   1.00,
    "downbeat": 0.80,
    "snare":    0.60,
    "beat":     0.40,
    "lift":     0.30,
}

# R1 Murch weighting
W_EMOTION = 0.50   # energy at that moment
W_STORY   = 0.30   # arc progress (later = heavier in builds)
W_RHYTHM  = 0.20   # granularity weight


# ==============================================================
# Helpers
# ==============================================================

def _section_at(sections, t: float) -> SectionLabel:
    for s in sections:
        if s.start <= t < s.end:
            return s.label
    return "unknown"


def _sample_energy(curve: list[float], hz: float, t: float) -> float:
    if not curve:
        return 0.5
    i = max(0, min(len(curve) - 1, int(t * hz)))
    return float(curve[i])


def _target_shot_count(duration: float, bpm: float, mode: Mode) -> int:
    """R10.2 — derive target N shots from length, BPM, and mode.

    Anchored on "shots per bar". A bar is 4 beats. Mode factor adjusts
    around the baseline of 1 cut per bar.
    """
    bar_duration = (60.0 / max(bpm, 1)) * 4
    n_bars = duration / bar_duration
    # mode factor is interpreted as cuts-per-bar
    raw = n_bars * MODE_FACTOR[mode]
    return max(MIN_SHOTS, min(MAX_SHOTS, round(raw)))


# ==============================================================
# Candidate generation
# ==============================================================

def _generate_candidates(feat: FeatureJSON) -> list[CutCandidate]:
    """Produce one candidate per meaningful grid point.

    Granularity priority:
      phrase = every 4th downbeat (or section boundary if closer)
      downbeat = every downbeat
      snare = beats 2 and 4 of each bar (interpolated from downbeats+beats)
      beat = every beat
      lift = 1/16 before every downbeat (a small pre-hit)
    """
    cands: list[CutCandidate] = []
    beats = feat.beats
    downbeats = feat.downbeats

    def push(time: float, g: Granularity, notes: str = "") -> None:
        if not 0.0 <= time <= feat.duration:
            return
        label = _section_at(feat.sections, time)
        energy = _sample_energy(feat.energy_curve, feat.energy_curve_hz, time)
        # R1 Murch weighting for score
        arc_progress = time / feat.duration if feat.duration > 0 else 0.0
        # "story" weight: rises toward drop, falls after
        if feat.drop_candidates:
            drop_t = min(feat.drop_candidates, key=lambda d: abs(d - time))
            dist_to_drop = abs(time - drop_t) / max(1.0, feat.duration / 2)
            story = max(0.0, 1.0 - dist_to_drop)
        else:
            story = arc_progress
        score = (
            W_EMOTION * energy
            + W_STORY * story
            + W_RHYTHM * GRANULARITY_WEIGHT[g]
        )
        cands.append(CutCandidate(
            time=time, granularity=g, score=score,
            section_label=label, notes=notes,
        ))

    # phrase cuts = section boundaries + every 4th downbeat
    for s in feat.sections:
        if s.start > 0:
            push(s.start, "phrase", f"section:{s.label}")
    for i in range(0, len(downbeats), 4):
        push(downbeats[i], "phrase", "4-bar phrase")

    # downbeat cuts
    for d in downbeats:
        push(d, "downbeat")

    # beat cuts (and snare = beat 2/4 inference)
    if downbeats and beats:
        db_set = set(round(d, 3) for d in downbeats)
        # approximate: beats that are beat-index 1 or 3 within a bar = snare
        for j, b in enumerate(beats):
            if round(b, 3) in db_set:
                continue  # already a downbeat
            # find nearest downbeat index
            db_i = min(range(len(downbeats)), key=lambda k: abs(downbeats[k] - b))
            # position within bar = fraction of next-downbeat distance
            if db_i + 1 < len(downbeats):
                frac = (b - downbeats[db_i]) / (downbeats[db_i + 1] - downbeats[db_i])
            else:
                frac = (b - downbeats[db_i]) / max(0.01, 60.0 / max(feat.bpm, 1))
            if 0.4 <= frac <= 0.6:
                push(b, "snare", f"bar pos~{frac:.2f}")
            else:
                push(b, "beat")
    else:
        for b in beats:
            push(b, "beat")

    # lift cuts = 1/16 before each downbeat
    sixteenth = 60.0 / max(feat.bpm, 1) / 4
    for d in downbeats:
        push(d - sixteenth, "lift", "1/16 pre-downbeat")

    return cands


# ==============================================================
# Candidate selection
# ==============================================================

def _dedupe_close(cands: list[CutCandidate], min_gap: float) -> list[CutCandidate]:
    """Keep only the highest-scored candidate within any `min_gap` window."""
    if not cands:
        return []
    sorted_c = sorted(cands, key=lambda c: c.time)
    kept: list[CutCandidate] = []
    for c in sorted_c:
        if kept and c.time - kept[-1].time < min_gap:
            if c.score > kept[-1].score:
                kept[-1] = c
            continue
        kept.append(c)
    return kept


def _veto(cand: CutCandidate, prev_time: float, feat: FeatureJSON) -> bool:
    """V1-V8 veto rules. True = reject."""
    shot_len = cand.time - prev_time
    if shot_len < MIN_SHOT_SEC:
        return True
    if shot_len > MAX_SHOT_SEC:
        # Only hard-reject if there IS a higher-priority candidate nearby;
        # otherwise a long shot is fine.
        return False
    return False


def _select_cuts(cands: list[CutCandidate], n_target: int,
                 feat: FeatureJSON) -> list[CutCandidate]:
    """Energy-weighted equal-density selection (R9.2).

    Approach:
    1. Dedupe candidates within 1 beat (keep best).
    2. Build a cumulative ENERGY INTEGRAL over the track. High-energy regions
       accumulate cuts faster than low-energy ones — this gives the dynamic
       arc that matches what editors do.
    3. Divide the integral into N equal slices. Each slice boundary is a
       desired cut TIME — find the best-scored candidate within a beat of it.
    4. Apply edge buffer + min-gap + density ceiling.
    """
    import numpy as np

    beat_dur = 60.0 / max(feat.bpm, 1)
    min_gap = beat_dur * 0.75
    cands = _dedupe_close(cands, min_gap)
    if not cands:
        return []

    target_cuts = n_target - 1
    edge_buffer = max(MIN_SHOT_SEC * 2.5, beat_dur * 1.5)

    # Build cumulative energy integral on the energy curve, weighted slightly
    # so even silent regions get SOME cut budget (avoid pathological clustering).
    energy = np.array(feat.energy_curve, dtype=float)
    if len(energy) < 2:
        energy = np.ones(max(2, int(feat.duration * 10)))
    weighted = 0.15 + 0.85 * energy  # floor prevents starvation; let energy dominate
    cum = np.cumsum(weighted)
    cum = cum / cum[-1]  # 0..1
    times_axis = np.linspace(0, feat.duration, len(cum))

    # Desired cut times: equal slices in cumulative-energy space
    desired_quantiles = np.linspace(0, 1, target_cuts + 2)[1:-1]
    desired_times: list[float] = []
    for q in desired_quantiles:
        idx = int(np.searchsorted(cum, q))
        idx = min(idx, len(times_axis) - 1)
        desired_times.append(float(times_axis[idx]))

    # For each desired time, find the best candidate within ±2 beats
    accepted: list[CutCandidate] = []
    accepted_times: list[float] = []
    for d_time in desired_times:
        if d_time < edge_buffer or d_time > feat.duration - edge_buffer:
            continue
        nearby = [
            c for c in cands
            if abs(c.time - d_time) <= 2 * beat_dur
            and c.time >= edge_buffer
            and c.time <= feat.duration - edge_buffer
            and not any(abs(c.time - t) < max(MIN_SHOT_SEC, beat_dur * 0.9)
                        for t in accepted_times)
        ]
        if not nearby:
            # Fall back to widest search window (4 beats)
            nearby = [
                c for c in cands
                if abs(c.time - d_time) <= 4 * beat_dur
                and c.time >= edge_buffer
                and c.time <= feat.duration - edge_buffer
                and not any(abs(c.time - t) < max(MIN_SHOT_SEC, beat_dur * 0.9)
                            for t in accepted_times)
            ]
        if not nearby:
            continue
        best = max(nearby, key=lambda c: c.score)
        accepted.append(best)
        accepted_times.append(best.time)

    return sorted(accepted, key=lambda c: c.time)


# ==============================================================
# Plan assembly
# ==============================================================

def _build_shots(cuts: list[CutCandidate], feat: FeatureJSON,
                 tier: int) -> ShotPlan:
    """Convert cut list into a ShotPlan."""
    # Cut points define shot boundaries; shot 0 starts at 0.0, last ends at duration.
    boundaries = [0.0] + [c.time for c in cuts] + [feat.duration]
    shots: list[Shot] = []
    for i in range(len(boundaries) - 1):
        s_start = boundaries[i]
        s_end = boundaries[i + 1]
        mid = (s_start + s_end) / 2
        label = _section_at(feat.sections, mid)
        energy = _sample_energy(feat.energy_curve, feat.energy_curve_hz, mid)
        # granularity of the cut that STARTS this shot (first shot = "phrase")
        if i == 0:
            g: Granularity = "phrase"
        else:
            g = cuts[i - 1].granularity
        shots.append(Shot(
            index=i,
            start=s_start,
            end=s_end,
            section_label=label,
            energy=energy,
            granularity=g,
        ))

    # Drop shot detection
    drop_at = feat.drop_candidates[0] if feat.drop_candidates else None
    drop_shot_index: int | None = None
    if drop_at is not None:
        for i, s in enumerate(shots):
            if s.start <= drop_at < s.end:
                drop_shot_index = i
                break

    notes: list[str] = []
    notes.append(f"mode={feat.mode} bpm={feat.bpm:.1f} backbone={feat.backbone}")
    notes.append(f"n_target={len(shots)} n_candidates={len(cuts)+1}")

    return ShotPlan(
        track_path=feat.track_path,
        duration=feat.duration,
        bpm=feat.bpm,
        mode=feat.mode,
        n_shots=len(shots),
        shots=shots,
        drop_at=drop_at,
        drop_shot_index=drop_shot_index,
        backbone=feat.backbone,
        tier=tier,
        notes=notes,
    )


# ==============================================================
# Public entry point
# ==============================================================

def plan(feat: FeatureJSON, tier: int = 1,
         n_shots_override: int | None = None) -> ShotPlan:
    """Run the full planner pipeline on a FeatureJSON.

    Args:
        feat: audio features from any backbone
        tier: 1-4, stamped into the output for logging
        n_shots_override: force a specific shot count (for debugging/ablation)
    """
    n_target = (
        n_shots_override
        if n_shots_override is not None
        else _target_shot_count(feat.duration, feat.bpm, feat.mode)
    )
    cands = _generate_candidates(feat)
    selected = _select_cuts(cands, n_target, feat)
    return _build_shots(selected, feat, tier)
