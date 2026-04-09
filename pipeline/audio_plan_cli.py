"""CLI entry point: plan_shots <track> --tier 1|2|3|4

Usage:
  python -m pipeline.audio_plan_cli <track.mp3> --tier 1 [--out plan.json]
"""
from __future__ import annotations

import argparse
import sys

from pipeline.audio_plan import planner
from pipeline.audio_plan.schemas import FeatureJSON


def _load_backbone(tier: int):
    if tier == 1:
        from pipeline.audio_plan.backbones import librosa_backbone
        return librosa_backbone.analyze
    if tier == 2:
        from pipeline.audio_plan.backbones import allin1_backbone
        return allin1_backbone.analyze
    if tier == 3:
        from pipeline.audio_plan.backbones import allin1_stems_backbone
        return allin1_stems_backbone.analyze
    if tier == 4:
        # tier 4 = tier 3 features + CLAP rerank applied AFTER planning
        from pipeline.audio_plan.backbones import allin1_stems_backbone
        return allin1_stems_backbone.analyze
    raise ValueError(f"Unknown tier {tier}")


def main() -> int:
    p = argparse.ArgumentParser(description="Audio-driven shot planner")
    p.add_argument("track", help="Path to mp3/wav")
    p.add_argument("--tier", type=int, default=1, choices=[1, 2, 3, 4])
    p.add_argument("--out", default=None, help="Write plan JSON to file")
    p.add_argument("--features-out", default=None, help="Write feature JSON")
    p.add_argument("--n-shots", type=int, default=None,
                   help="Override target shot count")
    args = p.parse_args()

    analyze = _load_backbone(args.tier)
    feat: FeatureJSON = analyze(args.track)
    plan = planner.plan(feat, tier=args.tier, n_shots_override=args.n_shots)

    if args.tier == 4:
        from pipeline.audio_plan.rerank import clap_reranker
        plan = clap_reranker.rerank(plan, feat)

    if args.features_out:
        with open(args.features_out, "w") as f:
            f.write(feat.to_json())
    out_json = plan.to_json()
    if args.out:
        with open(args.out, "w") as f:
            f.write(out_json)
    else:
        print(out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
