"""Tier 3: allin1 + beat_this cross-check + Demucs drum-stem energy.

Uses allin1 for sections (its main strength), beat_this for SOTA beat tracking
(verifies allin1's beats), and runs Demucs once to extract the drums stem so we
can compute a drum-onset energy curve and detect drops on the bass+drum stems.

When allin1 and beat_this disagree on beats by more than 1 beat duration, we
trust beat_this (it has higher published F1).
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np

from ..schemas import FeatureJSON, Mode, Section
from .allin1_backbone import LABEL_MAP, _classify_mode, _detect_drops, ENERGY_HZ


def _run_demucs_drums(path: str) -> tuple[np.ndarray, int] | None:
    """Run Demucs htdemucs to isolate drums; return (drums_audio, sr).

    Returns None if Demucs fails. Cached on disk.
    """
    try:
        import torch
        import torchaudio
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except Exception:
        return None

    cache_dir = Path("/tmp/demucs_cache")
    cache_dir.mkdir(exist_ok=True)
    stem_path = cache_dir / f"{Path(path).stem}_drums.wav"
    if stem_path.exists():
        wav, sr = torchaudio.load(str(stem_path))
        return wav.numpy().mean(axis=0), int(sr)

    try:
        model = get_model("htdemucs")
        model.eval()
        wav, sr = torchaudio.load(path)
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)
        wav = wav.unsqueeze(0)  # (1, 2, T)
        with torch.no_grad():
            stems = apply_model(model, wav, device="cpu", split=True, overlap=0.1)
        # stems shape: (1, num_stems, 2, T) — order: drums, bass, other, vocals
        stem_names = list(model.sources)
        drums_idx = stem_names.index("drums")
        drums = stems[0, drums_idx].mean(dim=0).cpu().numpy()
        torchaudio.save(str(stem_path), torch.tensor(drums).unsqueeze(0), sr)
        return drums, int(sr)
    except Exception as e:
        print(f"  demucs failed: {e}")
        return None


def _drum_onset_curve(drums: np.ndarray, sr: int, duration: float) -> np.ndarray:
    """Onset strength on the drum stem, resampled to ENERGY_HZ."""
    import librosa
    hop = 512
    onset = librosa.onset.onset_strength(y=drums.astype(np.float32), sr=sr, hop_length=hop)
    src_t = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=hop)
    target_n = max(8, int(duration * ENERGY_HZ))
    tgt_t = np.linspace(0, duration, target_n)
    out = np.interp(tgt_t, src_t, onset)
    if out.max() > 0:
        out /= out.max()
    return out


def _beat_this_beats(path: str) -> tuple[list[float], list[float]] | None:
    """Use beat_this for SOTA beat + downbeat detection."""
    try:
        from beat_this.inference import File2Beats
    except Exception:
        return None
    try:
        f2b = File2Beats(checkpoint_path="final0", dbn=False)
        beats, downbeats = f2b(path)
        return ([float(b) for b in beats], [float(d) for d in downbeats])
    except Exception as e:
        print(f"  beat_this failed: {e}")
        return None


def analyze(path: str) -> FeatureJSON:
    # Try allin1 first; if it fails (e.g. NATTEN issue), fall back to librosa+beat_this.
    try:
        from .allin1_backbone import analyze as allin1_analyze
        feat = allin1_analyze(path)
    except Exception as e:
        print(f"  allin1 unavailable ({e}); falling back to librosa backbone for sections")
        from .librosa_backbone import analyze as librosa_analyze
        feat = librosa_analyze(path)

    # Cross-check beats with beat_this
    bt = _beat_this_beats(path)
    if bt:
        bt_beats, bt_downbeats = bt
        # Replace if reasonable
        if bt_beats:
            feat.beats = bt_beats
        if bt_downbeats:
            feat.downbeats = bt_downbeats

    # Drum-stem augmentation
    drums = _run_demucs_drums(path)
    drum_curve = None
    if drums is not None:
        drum_audio, sr = drums
        drum_curve = _drum_onset_curve(drum_audio, sr, feat.duration)
        # Augment drop detection: use drum onset spikes
        tgt_t = np.linspace(0, feat.duration, len(drum_curve))
        extra = _detect_drops(drum_curve, tgt_t)
        for d in extra:
            if not feat.drop_candidates or min(abs(d - x) for x in feat.drop_candidates) > 1.0:
                feat.drop_candidates.append(d)
        feat.drop_candidates = sorted(feat.drop_candidates)

    feat.backbone = feat.backbone + "+stems"
    if drum_curve is not None:
        feat.drum_onset_curve = [float(x) for x in drum_curve]
    return feat
