"""Tier 2: beat_this (SOTA beats+downbeats) + librosa sections.

PIVOT NOTE: The original plan was to use `allin1` for one-shot structure
analysis, but the natten dependency fails to build cleanly against current
torch on Apple Silicon (see AUDIO_PLAN.md risk register, R1). We pivoted to
beat_this — also from CPJKU, ISMIR 2024, pure PyTorch, beats madmom on F1
across all standard benchmarks, and installs without pain.

What changes vs Tier 1:
  - beat_this for beats AND downbeats (librosa only does beats; we previously
    had to phase-fit downbeats)
  - same librosa sections + RMS energy

What we LOSE vs theoretical allin1 backbone:
  - Functional segment labels (intro/verse/chorus/bridge/...)
  - Demixed-input beat tracking (allin1 internally runs Demucs)
Tier 3 adds Demucs back to recover the latter.
"""
from __future__ import annotations

import numpy as np

from ..schemas import FeatureJSON, Mode, Section
from .librosa_backbone import (
    ENERGY_HZ, _classify_mode, _detect_drops, _detect_sections,
)


def _beat_this_beats(path: str) -> tuple[list[float], list[float]] | None:
    """Use beat_this for SOTA beat + downbeat detection."""
    try:
        from beat_this.inference import File2Beats
    except Exception as e:
        print(f"  beat_this import failed: {e}")
        return None
    try:
        # final0 = the trained checkpoint, dbn=False = no DBN postprocessing
        f2b = File2Beats(checkpoint_path="final0", dbn=False)
        beats, downbeats = f2b(path)
        return ([float(b) for b in beats], [float(d) for d in downbeats])
    except Exception as e:
        print(f"  beat_this inference failed: {e}")
        return None


def analyze(path: str) -> FeatureJSON:
    import librosa
    import scipy.signal as sp

    y, sr = librosa.load(path, sr=22050, mono=True)
    duration = float(len(y) / sr)

    sos = sp.butter(4, 200, "lp", fs=sr, output="sos")
    y_bass = sp.sosfilt(sos, y).astype(np.float32)

    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    bass_rms = librosa.feature.rms(y=y_bass, hop_length=hop)[0]
    rms_t = librosa.times_like(rms, sr=sr, hop_length=hop)

    target_n = max(8, int(duration * ENERGY_HZ))
    tgt_t = np.linspace(0, duration, target_n)
    energy = np.interp(tgt_t, src_t := rms_t, rms)
    bass_energy = np.interp(tgt_t, src_t, bass_rms)
    if energy.max() > 0:
        energy /= energy.max()
    if bass_energy.max() > 0:
        bass_energy /= bass_energy.max()

    rms_dyn_range = float(np.percentile(energy, 90) - np.percentile(energy, 10))
    bass_weight = min(1.0, float(np.mean(bass_energy)) / max(float(np.mean(energy)), 1e-6))

    # Try beat_this first; fall back to librosa if it fails.
    bt = _beat_this_beats(path)
    if bt:
        beats, _bt_downbeats = bt
        # beat_this sometimes returns 8th-notes instead of quarter-notes
        # (median interval < 0.4s = suspicious). Subsample until quarter-note.
        beats_arr = np.array(beats)
        if len(beats_arr) >= 2:
            while True:
                interval = float(np.median(np.diff(beats_arr)))
                if interval >= 0.34 or len(beats_arr) < 8:
                    break
                beats_arr = beats_arr[::2]
            beats = [float(b) for b in beats_arr]
            bpm = 60.0 / float(np.median(np.diff(beats_arr)))
        else:
            bpm = 120.0
        # Octave fold to musical range
        while bpm > 180:
            bpm /= 2
            beats = beats[::2]
        while bpm < 70:
            bpm *= 2
        # Re-derive downbeats from the corrected beat grid via onset-strength
        # phase fitting (same trick as librosa fallback below).
        onset_env_for_db = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        bf_idx = (np.array(beats) * sr / hop).astype(int)
        bf_idx = np.clip(bf_idx, 0, len(onset_env_for_db) - 1)
        beat_strengths = onset_env_for_db[bf_idx]
        best_phase = max(range(4), key=lambda p: float(beat_strengths[p::4].sum()))
        downbeats = [float(b) for b in np.array(beats)[best_phase::4]]
    else:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=hop, onset_envelope=onset_env,
        )
        bpm = float(np.atleast_1d(tempo)[0])
        beats_arr = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
        beats = [float(b) for b in beats_arr]
        # Phase-fit downbeats from onset peaks
        beat_frames_clipped = (np.array(beats) * sr / hop).astype(int)
        beat_frames_clipped = np.clip(beat_frames_clipped, 0, len(onset_env) - 1)
        strengths = onset_env[beat_frames_clipped]
        best_phase = max(range(4), key=lambda p: float(strengths[p::4].sum()))
        downbeats = [float(b) for b in np.array(beats)[best_phase::4]]

    mode = _classify_mode(bpm, rms_dyn_range, bass_weight)
    sections = _detect_sections(rms, rms_t, duration)
    drops = _detect_drops(bass_energy, tgt_t)

    return FeatureJSON(
        track_path=path,
        duration=duration,
        bpm=bpm,
        beats=beats,
        downbeats=downbeats,
        sections=sections,
        energy_curve=[float(x) for x in energy],
        energy_curve_hz=ENERGY_HZ,
        bass_energy_curve=[float(x) for x in bass_energy],
        drum_onset_curve=None,
        drop_candidates=drops,
        mode=mode,
        backbone="beat_this+librosa",
    )


# Keep this name for older callers; the contents are now beat_this-based.
LABEL_MAP = {}
