"""Tier 1: pure librosa backbone. Cheap baseline, fastest, no neural models.

Outputs FeatureJSON. Limited section labeling (RMS-quantile fallback) and
no proper downbeat tracking — librosa gives beats only, so we infer
downbeats by phase-fitting bars to the beat grid.
"""
from __future__ import annotations

import numpy as np

from ..schemas import FeatureJSON, Mode, Section, SectionLabel

ENERGY_HZ = 50.0  # samples per second of the energy curve


def _classify_mode(bpm: float, rms_dyn_range: float, bass_weight: float) -> Mode:
    """R7.1 — phonk vs cinematic vs hybrid.

    Phonk requires both high BPM and high dynamic range (drops + breakdowns).
    Steady mid-tempo tracks with no big dynamic shift are hybrid, not phonk,
    even if BPM is >125.
    """
    if bpm >= 130 and bass_weight > 0.60 and rms_dyn_range > 0.35:
        return "phonk"
    if bpm <= 100 and rms_dyn_range < 0.45:
        return "cinematic"
    return "hybrid"


def _infer_downbeats(beats: np.ndarray, onset_strength: np.ndarray,
                     sr: int, hop: int) -> np.ndarray:
    """Pick the phase (0-3 mod 4) with the highest summed onset strength.

    librosa doesn't track downbeats, so we approximate: bars are 4 beats,
    the downbeat is the beat with the most percussive impact on average.
    """
    if len(beats) < 4:
        return beats[:1]
    beat_frames = (beats * sr / hop).astype(int)
    beat_frames = np.clip(beat_frames, 0, len(onset_strength) - 1)
    strengths = onset_strength[beat_frames]
    best_phase = 0
    best_sum = -1.0
    for phase in range(4):
        s = strengths[phase::4].sum()
        if s > best_sum:
            best_sum = s
            best_phase = phase
    return beats[best_phase::4]


def _detect_sections(rms: np.ndarray, rms_t: np.ndarray,
                     duration: float) -> list[Section]:
    """Cheap section detection: split track at large RMS-derivative changes.

    Returns 3-6 segments labelled by relative energy: low->intro/break,
    mid->verse, high->drop.
    """
    if len(rms) < 4:
        return [Section(0.0, duration, "unknown", 0.5)]

    # Smooth + derivative. Window = ~2 seconds of rms samples, capped to N/4.
    dt = float(rms_t[1] - rms_t[0]) if len(rms_t) > 1 else 1.0 / ENERGY_HZ
    win = max(8, min(len(rms) // 4, int(2.0 / max(dt, 1e-3))))
    smooth = np.convolve(rms, np.ones(win) / win, mode="same")
    deriv = np.abs(np.diff(smooth))
    if deriv.max() == 0:
        return [Section(0.0, duration, "unknown", 0.5)]
    # Pick the top 4 derivative peaks separated by >1.5s
    min_gap_idx = max(1, int(1.5 / max(rms_t[1] - rms_t[0], 1e-3)))
    peaks: list[int] = []
    for i in np.argsort(-deriv):
        if all(abs(i - p) > min_gap_idx for p in peaks):
            peaks.append(int(i))
        if len(peaks) >= 4:
            break
    boundaries = sorted([0] + peaks + [len(rms) - 1])

    # Classify each segment by mean RMS quantile
    quantiles = np.quantile(smooth, [0.33, 0.66])
    sections: list[Section] = []
    for a, b in zip(boundaries[:-1], boundaries[1:]):
        mean_e = float(smooth[a:b].mean()) if b > a else 0.0
        if mean_e < quantiles[0]:
            label: SectionLabel = "break"
        elif mean_e < quantiles[1]:
            label = "verse"
        else:
            label = "drop"
        t0 = float(rms_t[a])
        t1 = float(rms_t[min(b, len(rms_t) - 1)])
        sections.append(Section(start=t0, end=t1, label=label, confidence=0.6))
    # Force first section to start at 0 and last to end at duration
    if sections:
        first = sections[0]
        sections[0] = Section(0.0, first.end, first.label, first.confidence)
        last = sections[-1]
        sections[-1] = Section(last.start, duration, last.label, last.confidence)
    return sections


def _detect_drops(bass_rms: np.ndarray, t: np.ndarray) -> list[float]:
    """Find moments where bass energy spikes >=1.5x the prior 1.5s window."""
    if len(bass_rms) < 8:
        return []
    drops: list[float] = []
    win_idx = max(4, int(1.5 * ENERGY_HZ))
    for i in range(win_idx, len(bass_rms) - 1):
        prev_mean = float(np.mean(bass_rms[i - win_idx:i]))
        if prev_mean > 1e-6 and bass_rms[i] > 1.5 * prev_mean:
            if not drops or t[i] - drops[-1] > 1.0:
                drops.append(float(t[i]))
    return drops


def analyze(path: str) -> FeatureJSON:
    import librosa
    import scipy.signal as sp

    y, sr = librosa.load(path, sr=22050, mono=True)
    duration = float(len(y) / sr)

    # Bass-band filter (<200Hz) for kick/sub energy
    sos = sp.butter(4, 200, "lp", fs=sr, output="sos")
    y_bass = sp.sosfilt(sos, y).astype(np.float32)

    hop = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beat_frames = librosa.beat.beat_track(
        y=y, sr=sr, hop_length=hop, onset_envelope=onset_env,
    )
    bpm = float(np.atleast_1d(tempo)[0])
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
    downbeats = _infer_downbeats(beats, onset_env, sr, hop)

    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    bass_rms = librosa.feature.rms(y=y_bass, hop_length=hop)[0]
    rms_t = librosa.times_like(rms, sr=sr, hop_length=hop)

    # Resample energy curves to ENERGY_HZ
    target_n = max(8, int(duration * ENERGY_HZ))
    src_t = rms_t
    tgt_t = np.linspace(0, duration, target_n)
    energy = np.interp(tgt_t, src_t, rms)
    bass_energy = np.interp(tgt_t, src_t, bass_rms)
    # Normalize to 0..1
    if energy.max() > 0:
        energy = energy / energy.max()
    if bass_energy.max() > 0:
        bass_energy = bass_energy / bass_energy.max()

    rms_dyn_range = float(np.percentile(energy, 90) - np.percentile(energy, 10))
    bass_weight = float(np.mean(bass_energy)) / max(float(np.mean(energy)), 1e-6)
    bass_weight = min(1.0, bass_weight)
    mode = _classify_mode(bpm, rms_dyn_range, bass_weight)

    sections = _detect_sections(rms, rms_t, duration)
    drops = _detect_drops(bass_energy, tgt_t)

    return FeatureJSON(
        track_path=path,
        duration=duration,
        bpm=bpm,
        beats=[float(b) for b in beats],
        downbeats=[float(d) for d in downbeats],
        sections=sections,
        energy_curve=[float(x) for x in energy],
        energy_curve_hz=ENERGY_HZ,
        bass_energy_curve=[float(x) for x in bass_energy],
        drum_onset_curve=None,
        drop_candidates=drops,
        mode=mode,
        backbone="librosa",
    )
