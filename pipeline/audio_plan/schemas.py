"""Shared dataclasses passed between backbone -> planner -> reranker -> output.

All tiers consume FeatureJSON and emit ShotPlan. Backbones differ in HOW they
populate FeatureJSON; the planner is shared.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal
import json


Mode = Literal["phonk", "hybrid", "cinematic"]
Granularity = Literal["beat", "snare", "downbeat", "phrase", "lift"]
SectionLabel = Literal[
    "intro", "verse", "chorus", "bridge", "build", "drop", "break",
    "inst", "solo", "outro", "unknown"
]


@dataclass(frozen=True)
class Section:
    """A labelled time region of the track."""
    start: float
    end: float
    label: SectionLabel
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class CutCandidate:
    """One possible cut point with provenance + score."""
    time: float
    granularity: Granularity
    score: float                # 0..1, higher = more likely a real cut
    section_label: SectionLabel
    notes: str = ""


@dataclass
class FeatureJSON:
    """Stage-2 output. Everything the planner needs about the audio."""
    track_path: str
    duration: float
    bpm: float
    beats: list[float]
    downbeats: list[float]
    sections: list[Section]
    energy_curve: list[float]           # 0..1, sampled at energy_curve_hz
    energy_curve_hz: float
    bass_energy_curve: list[float]      # 0..1, same hz
    drum_onset_curve: list[float] | None  # optional, None for tier 1
    drop_candidates: list[float]        # timestamps of probable drops
    mode: Mode
    backbone: str                       # "librosa" | "allin1" | "allin1+stems"

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2, default=str)


@dataclass(frozen=True)
class Shot:
    """One shot in the final plan."""
    index: int
    start: float
    end: float
    section_label: SectionLabel
    energy: float
    granularity: Granularity            # what kind of cut started this shot

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class ShotPlan:
    """Stage-5 output. The deliverable."""
    track_path: str
    duration: float
    bpm: float
    mode: Mode
    n_shots: int
    shots: list[Shot]
    drop_at: float | None
    drop_shot_index: int | None         # 0-based shot containing the drop
    backbone: str
    tier: int
    notes: list[str] = field(default_factory=list)

    @property
    def cut_points(self) -> list[float]:
        return [s.start for s in self.shots[1:]]  # cuts BETWEEN shots

    @property
    def shot_durations(self) -> list[float]:
        return [s.duration for s in self.shots]

    def frame_counts(self, fps: int) -> list[int]:
        return [max(1, round(s.duration * fps)) for s in self.shots]

    def to_json(self) -> str:
        return json.dumps({
            "track_path": self.track_path,
            "duration": round(self.duration, 3),
            "bpm": round(self.bpm, 2),
            "mode": self.mode,
            "n_shots": self.n_shots,
            "tier": self.tier,
            "backbone": self.backbone,
            "drop_at": round(self.drop_at, 3) if self.drop_at else None,
            "drop_shot_index": self.drop_shot_index,
            "shots": [
                {
                    "i": s.index,
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "duration": round(s.duration, 3),
                    "section": s.section_label,
                    "energy": round(s.energy, 3),
                    "granularity": s.granularity,
                }
                for s in self.shots
            ],
            "cut_points": [round(t, 3) for t in self.cut_points],
            "shot_durations": [round(d, 3) for d in self.shot_durations],
            "notes": self.notes,
        }, indent=2)
