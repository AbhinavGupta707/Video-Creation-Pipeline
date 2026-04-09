#!/usr/bin/env python3
"""Generate image-gen prompts for a car showcase reel from a brief JSON.

Encodes learnings from the wine Czinger 21C pipeline sessions:
    - Multi-reference chain (identity refs + locked prior shots)
    - Generation order optimised for derivability (wides before details)
    - Framing rules that leave room for post-production camera motion
    - Continuity vocabulary: "same car, same studio as locked reference X"
    - Negative vocabulary: no vignette, no tilt-shift, no AI render feel
    - Photoreal anchors: Phase One 150MP, deep focus f/8, press photography
    - Correct side-profile geometry: viewing LEFT flank ⇒ nose points LEFT

Usage:
    python pipeline/generate_prompts.py <brief.json> <output_dir>

Outputs:
    <output_dir>/00_style_lock.md   — shared style lock block
    <output_dir>/01_index.md        — generation order + playback order tables
    <output_dir>/G{n}_playback{p}_{archetype}.md — per-shot prompts in gen order

The brief JSON schema is documented in briefs/wine_czinger_21c/brief.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---- learned constants ----

OUTPUT_W, OUTPUT_H = 2160, 3840

# Wide-shot framing — leaves ~35% of the frame empty for post-production motion.
WIDE_HEADROOM_PCT = 20
WIDE_FLOOR_PCT = 18
WIDE_SIDE_PCT = 13
WIDE_CAR_H_PCT = 50
WIDE_CAR_W_PCT = 60

DETAIL_SUBJECT_PCT = 60
DETAIL_DOF_F_STOP = 5.6  # moderate — NOT f/2.8 extreme shallow, so context remains readable
WIDE_DOF_F_STOP = 8.0
DEFAULT_COLOR_TEMP_K = 5200

# Generation-order rank per archetype. Lower = generate earlier.
# Logic: establish identity from the angle a Google ref shows best (front-3/4),
# then the angle that shares the most visual information with it (side),
# then the independent face (dead-front), then shots that derive cleanly from
# already-locked shots. Details go last because they crop from locked wides.
GEN_RANK: dict[str, int] = {
    # Wides first — establish identity, then increasingly dependent shots
    "wide_front_3q_right": 1,
    "wide_side_profile":   2,
    "wide_dead_front":     3,
    "wide_rear_3q":        4,
    "wide_rear_3q_left":   4,   # same rank as rear_3q — another wide
    "wide_front_3q_left":  5,
    "wide_dead_rear":      5,
    # Details — generated after wides they depend on
    "wheel_detail":        6,
    "wheel_detail_rear":   6,
    "rear_detail":         7,
    "signature_detail":    7,
    "rear_badge_detail":   7,
    "front_detail":        8,
    # Special — generated last (often depend on multiple locked shots)
    "extreme_close_up":    9,
    "interior":            9,
    "top_down":            9,
}


# ---- data classes (immutable) ----

@dataclass(frozen=True)
class SignatureDetail:
    """The car's most visually striking detail element for the tight close-up shot.

    For cars with an iconic rear badge (Ferrari prancing horse, Porsche script),
    this is typically the rear badge. For cars without one, pick the most
    photogenic and unique element (exhaust cluster, engine bay, canopy, etc.).
    """
    element: str
    location: str
    why: str
    visual_description: str
    camera_approach: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SignatureDetail":
        return cls(
            element=d["element"],
            location=d["location"],
            why=d["why"],
            visual_description=d["visual_description"],
            camera_approach=d["camera_approach"],
        )


@dataclass(frozen=True)
class Car:
    full_name: str
    short_name: str
    body_description: str
    not_cars: tuple[str, ...]
    signature_detail: SignatureDetail | None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Car":
        sig = d.get("signature_detail")
        return cls(
            full_name=d["full_name"],
            short_name=d["short_name"],
            body_description=d["body_description"],
            not_cars=tuple(d["not_cars"]),
            signature_detail=SignatureDetail.from_dict(sig) if sig else None,
        )


@dataclass(frozen=True)
class Paint:
    name: str
    description: str
    lattice_treatment: str
    wheels: str
    calipers: str
    canopy: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Paint":
        return cls(
            name=d["name"],
            description=d["description"],
            lattice_treatment=d.get("lattice_treatment", ""),
            wheels=d["wheels"],
            calipers=d["calipers"],
            canopy=d["canopy"],
        )


@dataclass(frozen=True)
class Studio:
    description: str
    color_temp_k: int = DEFAULT_COLOR_TEMP_K

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Studio":
        return cls(
            description=d["description"],
            color_temp_k=d.get("color_temp_k", DEFAULT_COLOR_TEMP_K),
        )


@dataclass(frozen=True)
class Shot:
    playback_order: int
    archetype: str
    shot_name: str
    camera_clock: str
    lens_height_cm: int
    lens_mm: int
    subject_distance_m: float
    composition_notes: str = ""
    is_detail: bool = False
    flank_visible: str = ""  # "" | "left" | "right"
    derived_from_playback: tuple[int, ...] = ()
    car_h_pct: int = WIDE_CAR_H_PCT
    car_w_pct: int = WIDE_CAR_W_PCT

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Shot":
        return cls(
            playback_order=int(d["playback_order"]),
            archetype=d["archetype"],
            shot_name=d["shot_name"],
            camera_clock=d["camera_clock"],
            lens_height_cm=int(d["lens_height_cm"]),
            lens_mm=int(d["lens_mm"]),
            subject_distance_m=float(d["subject_distance_m"]),
            composition_notes=d.get("composition_notes", ""),
            is_detail=bool(d.get("is_detail", False)),
            flank_visible=d.get("flank_visible", ""),
            derived_from_playback=tuple(d.get("derived_from_playback", [])),
            car_h_pct=int(d.get("car_h_pct", WIDE_CAR_H_PCT)),
            car_w_pct=int(d.get("car_w_pct", WIDE_CAR_W_PCT)),
        )


@dataclass(frozen=True)
class Brief:
    car: Car
    paint: Paint
    studio: Studio
    audio_track: str
    shots: tuple[Shot, ...]
    identity_references: tuple[tuple[str, str], ...]  # (label, path) pairs
    stills_dir: Path

    @classmethod
    def from_dict(cls, d: dict[str, Any], stills_dir: Path) -> "Brief":
        return cls(
            car=Car.from_dict(d["car"]),
            paint=Paint.from_dict(d["paint"]),
            studio=Studio.from_dict(d["studio"]),
            audio_track=d["audio_track"],
            shots=tuple(Shot.from_dict(s) for s in d["shots"]),
            identity_references=tuple(
                (label, path) for label, path in d["identity_references"].items()
            ),
            stills_dir=stills_dir,
        )


# ---- template builders (pure functions) ----

def build_style_lock(brief: Brief, *, is_detail: bool = False) -> str:
    """Build the identity + paint + studio + photo + output lock block.

    For detail shots, the photo-quality section uses moderate DOF f/5.6 with
    orientation anchors required; for wide shots it uses deep-focus f/8.
    """
    n = len(brief.shots)
    not_cars = ", ".join(brief.car.not_cars)
    lattice = f" {brief.paint.lattice_treatment}" if brief.paint.lattice_treatment else ""
    if is_detail:
        photo_block = (
            f"**Photographic quality:** Photoreal medium-format studio photograph, "
            f"Phase One 150MP look, **moderate depth of field f/{DETAIL_DOF_F_STOP} "
            f"— NOT extreme shallow DOF, NOT f/2.8, NOT tilt-shift, NOT miniature.** "
            f"The primary focal subject is in razor-sharp focus; the surrounding "
            f"orientation-anchor landmarks (named in the composition notes) are in "
            f"gentle slightly-soft focus but must still be clearly readable — "
            f"the viewer must be able to identify which part of the car they are "
            f"looking at within 0.5 seconds. Real automotive product detail "
            f"photography like a Porsche, Pagani, or Ferrari press kit shot — "
            f"NOT AI-rendered, NOT abstract texture."
        )
    else:
        photo_block = (
            f"**Photographic quality:** Photoreal medium-format studio photograph, "
            f"Phase One 150MP look, **deep focus f/{WIDE_DOF_F_STOP} sharp "
            f"throughout the entire car from nose to tail** — NOT shallow DOF, "
            f"NOT tilt-shift, NOT miniature effect. Real automotive press "
            f"photography feel — NOT AI-rendered smoothness, NOT Midjourney "
            f"over-stylization. Tactile sharp detail on paint reflections, "
            f"lattice texture, and wheel spokes."
        )
    return (
        f"**Subject identity — {brief.car.full_name}.** {brief.car.body_description}\n"
        f"It is NOT a {not_cars}. Use the attached reference images as ground truth "
        f"for body shape, proportions, and identity.\n\n"
        f"**Paint and materials (locked across all {n} shots):** "
        f"{brief.paint.description}.{lattice} {brief.paint.wheels}. "
        f"{brief.paint.calipers}. {brief.paint.canopy} — interior reads as a pure "
        f"black void with no driver, no helmet, no figure, no visible interior "
        f"detail. Subtle {brief.car.short_name} badge only, no other text, no logos, "
        f"no license plate, no people anywhere in the frame.\n\n"
        f"**Studio environment (locked across all {n} shots):** "
        f"{brief.studio.description}. **No dark corner vignette. No moody dramatic "
        f"contrast. No theatrical lighting. No fan of multiple hot floor reflections.** "
        f"Single soft floor reflection directly beneath the car only, fading gently. "
        f"Color temperature ~{brief.studio.color_temp_k}K.\n\n"
        f"{photo_block}\n\n"
        f"**Output spec:** 9:16 vertical portrait, {OUTPUT_W} × {OUTPUT_H} pixels. "
        f"No borders, no letterbox, no watermark, no text, no UI overlay. "
        f"Horizon perfectly level, no Dutch angle, no fisheye distortion."
    )


def build_continuity_block(shot: Shot, brief: Brief) -> str:
    if not shot.derived_from_playback:
        return ""
    ref_list = ", ".join(
        f"locked shot{p}.jpg (playback shot {p})" for p in shot.derived_from_playback
    )
    return (
        f"**Continuity lock:** EXACT same {brief.car.full_name} as {ref_list} "
        f"(all attached). Same {brief.paint.name} paint, same wheels, same brake "
        f"calipers, same lattice, same dark empty canopy, same studio, same lighting, "
        f"same photographic quality as those locked references. Only the camera "
        f"angle changes between this shot and the locked references."
    )


def build_camera_block(shot: Shot) -> str:
    parts = [
        f"**Camera:** Position {shot.camera_clock} relative to the car. "
        f"Lens height {shot.lens_height_cm}cm from the floor. "
        f"{shot.lens_mm}mm full-frame equivalent lens, subject distance "
        f"~{shot.subject_distance_m}m."
    ]
    if shot.flank_visible in ("left", "right"):
        other = "right" if shot.flank_visible == "left" else "left"
        flank = shot.flank_visible
        parts.append(
            f"Camera perpendicular to the car centerline (90° dead side-on, zero yaw). "
            f"The viewer sees the complete {flank.upper()} flank of the car. "
            f"**The car runs horizontally across the frame with its nose pointing "
            f"toward the {flank.upper()} side of the frame and its tail pointing "
            f"toward the {other.upper()} side of the frame.**"
        )
    if shot.composition_notes:
        parts.append(f"**Composition notes:** {shot.composition_notes}")
    return "\n\n".join(parts)


def build_framing_block(shot: Shot) -> str:
    if shot.is_detail:
        return (
            f"**Framing (tight detail, NOT extreme macro, NOT abstract texture):** "
            f"The focal subject fills ~{DETAIL_SUBJECT_PCT}% of the frame of the 9:16 "
            f"portrait. Leave generous grey breathing room around the subject for "
            f"post-production motion room and so orientation-anchor landmarks named "
            f"in the composition notes above are all visible in the frame. "
            f"**Do NOT zoom all the way in — the viewer must be able to identify "
            f"which part of the car they are looking at within 0.5 seconds.**"
        )
    return (
        f"**Framing (critical — small subject in large empty studio):** "
        f"Car occupies ~{shot.car_h_pct}% of frame height and ~{shot.car_w_pct}% of "
        f"frame width of the 9:16 portrait. ~{WIDE_HEADROOM_PCT}% empty grey space "
        f"above the highest point of the car. ~{WIDE_FLOOR_PCT}% empty grey floor "
        f"below the tires. ~{WIDE_SIDE_PCT}% empty grey space on each side of the "
        f"widest point of the car. This breathing room is required for "
        f"post-production camera motion in the final reel."
    )


def build_references_for_shot(
    shot: Shot, brief: Brief
) -> list[tuple[str, str]]:
    """Return ordered list of (label, path) references to attach to this shot."""
    refs: list[tuple[str, str]] = []
    # Detail shots with locked-shot dependencies skip identity refs — the locked
    # shots already contain all the paint/material/studio info the detail needs.
    include_identity = not (shot.is_detail and shot.derived_from_playback)
    if include_identity:
        refs.extend(brief.identity_references)
    for p in shot.derived_from_playback:
        label = f"locked shot{p}.jpg (playback shot {p})"
        path = str(brief.stills_dir / f"shot{p}.jpg")
        refs.append((label, path))
    return refs


def build_signature_detail_block(brief: Brief) -> str:
    """Build an extra block for signature_detail archetype shots.

    Injects the car-specific signature element description so the image gen
    model knows exactly what to focus on as the hero element.
    """
    sig = brief.car.signature_detail
    if sig is None:
        return ""
    return (
        f"**Signature detail — hero element for this shot:** "
        f"{sig.element}, located at {sig.location}.\n\n"
        f"**Why this element:** {sig.why}\n\n"
        f"**Visual description of the hero element:** {sig.visual_description}\n\n"
        f"**Camera approach:** {sig.camera_approach}"
    )


def compute_generation_order(shots: tuple[Shot, ...]) -> list[Shot]:
    """Sort shots by derivability rank (wides first, details last)."""
    return sorted(
        shots, key=lambda s: (GEN_RANK.get(s.archetype, 99), s.playback_order)
    )


def _blockquote(text: str) -> str:
    return "\n".join(f"> {line}" if line.strip() else ">" for line in text.split("\n"))


def render_shot_prompt(shot: Shot, brief: Brief) -> str:
    """Render a full-density prompt for one shot.

    Detail shots get a different style lock (moderate DOF f/5.6) than wide
    shots (deep focus f/8) so the viewer can identify the subject.
    """
    refs = build_references_for_shot(shot, brief)
    ref_lines = "\n".join(f"- `{label}` → `{path}`" for label, path in refs)
    per_shot_lock = build_style_lock(brief, is_detail=shot.is_detail)
    # For signature_detail archetype, inject the car-specific hero element block
    sig_block = ""
    if shot.archetype in ("signature_detail", "rear_badge_detail"):
        sig_block = build_signature_detail_block(brief)
    blocks = [
        build_continuity_block(shot, brief),
        per_shot_lock,
        sig_block,
        build_camera_block(shot),
        build_framing_block(shot),
        "**Generate.**",
    ]
    prompt_body = "\n\n".join(b for b in blocks if b)
    return (
        f"# Shot {shot.playback_order} of {len(brief.shots)} — {shot.shot_name}\n\n"
        f"**Archetype:** `{shot.archetype}`\n\n"
        f"## References to attach\n\n{ref_lines}\n\n"
        f"## Prompt (paste verbatim into ChatGPT / Nano Banana / Ideogram)\n\n"
        f"{_blockquote(prompt_body)}\n"
    )


def build_index(brief: Brief, gen_order: list[Shot]) -> str:
    lines = [
        f"# {brief.car.full_name} — Prompt Index",
        "",
        f"**Audio track:** `{brief.audio_track}`",
        f"**Shot count:** {len(brief.shots)}",
        f"**Stills directory:** `{brief.stills_dir}`",
        "",
        "## Usage",
        "",
        "1. Generate shots in the **generation order** below, not playback order.",
        "2. For each shot, attach the references listed in its prompt file, "
        "then paste the prompt body into your image-gen tool.",
        "3. Save each approved result as `shot{playback_order}.jpg` in the stills "
        "directory so subsequent shots can reference it for continuity.",
        "4. Run the consistency checklist after each generation — reject if car "
        "identity, paint, wheels, or studio drifts.",
        "",
        "## Generation order (do them in this order)",
        "",
        "| Gen | Playback | Archetype | Shot name | Refs |",
        "|---|---|---|---|---|",
    ]
    for i, s in enumerate(gen_order, start=1):
        deps = ", ".join(f"shot{p}" for p in s.derived_from_playback) or "identity only"
        lines.append(
            f"| G{i} | {s.playback_order} | `{s.archetype}` | {s.shot_name} | {deps} |"
        )
    lines += [
        "",
        "## Playback order (final video sequence)",
        "",
        "| Playback | Archetype | Shot name |",
        "|---|---|---|",
    ]
    for s in sorted(brief.shots, key=lambda x: x.playback_order):
        lines.append(f"| {s.playback_order} | `{s.archetype}` | {s.shot_name} |")
    lines += [
        "",
        "## Consistency checklist (run after every generation)",
        "",
        f"- [ ] Car is clearly a {brief.car.full_name}, not a {brief.car.not_cars[0]}",
        f"- [ ] Paint matches {brief.paint.name} exactly",
        "- [ ] Lattice panels remain unpainted matte charcoal",
        "- [ ] Wheel design matches prior locked shots exactly",
        "- [ ] Brake calipers are red",
        "- [ ] Canopy glass tinted, no driver or helmet visible",
        "- [ ] Background is seamless mid-grey cyclorama, no vignette",
        "- [ ] Floor has one soft reflection only, no scattered hot spots",
        "- [ ] 9:16 portrait with no letterbox or borders",
        "- [ ] Framing margins match the rule (~20% top, ~18% bottom, ~13% sides)",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate image-gen prompts from a brief JSON."
    )
    ap.add_argument("brief", type=Path, help="path to brief.json")
    ap.add_argument("output_dir", type=Path, help="where to write prompt files")
    args = ap.parse_args(argv)

    if not args.brief.exists():
        print(f"error: brief file not found: {args.brief}", file=sys.stderr)
        return 1

    brief_data = json.loads(args.brief.read_text())
    stills_dir = (args.brief.parent / "stills").resolve()
    brief = Brief.from_dict(brief_data, stills_dir=stills_dir)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    gen_order = compute_generation_order(brief.shots)

    # Reference style locks — wides and details differ on DOF + orientation
    (args.output_dir / "00_style_lock_wide.md").write_text(
        build_style_lock(brief, is_detail=False) + "\n"
    )
    (args.output_dir / "00_style_lock_detail.md").write_text(
        build_style_lock(brief, is_detail=True) + "\n"
    )
    (args.output_dir / "01_index.md").write_text(build_index(brief, gen_order))

    for i, shot in enumerate(gen_order, start=1):
        fname = (
            f"G{i}_playback{shot.playback_order:02d}_{shot.archetype}.md"
        )
        fp = args.output_dir / fname
        fp.write_text(render_shot_prompt(shot, brief))
        print(f"wrote {fp}")

    print(f"\n{len(gen_order)} prompts written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
