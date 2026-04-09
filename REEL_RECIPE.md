# Luxury Car Reel — Master Recipe

Reverse-engineered from `videos/wine ferrari.mp4` (13.2s, 9:16, ~9 shots, CGI studio).
Pipeline: **ChatGPT (gpt-image-1) stills → Kling 2.1 / Runway Gen-4 i2v → CapCut stitch**.

---

## 0. The non-negotiable style lock

These six lines must appear (verbatim or close) in EVERY image prompt so all 8 stills look like the same car in the same studio. Paste this block into every prompt.

```
STYLE LOCK — do not deviate:
- Hyperreal CGI studio render, Octane / Unreal Engine 5 cinematic, 9:16 vertical, 720x1280.
- Seamless infinity-cove backdrop, soft gradient mid-grey (#5a5d61 top → #8a8d90 bottom), no horizon, no environment, no props.
- Lighting: single large soft top key light, subtle HDRI fill, faint contact shadow only. No rim light, no neon, no sun.
- Lens feel: 50mm full-frame equivalent, f/4, shallow but not extreme depth of field, zero lens distortion.
- Color science: muted, slightly desaturated, cool shadows, neutral whites. Filmic tone curve. No HDR halo.
- Absolute photo-grade detail on paint flake, carbon weave, brake calipers, tire sidewall. No text, no watermark, no license plate.
```

---

## 1. THE 8-SHOT MASTER SHOT LIST

| # | Shot | Camera position | Framing | Camera motion (1.2–1.5s) | Notes |
|---|------|-----------------|---------|---------------------------|-------|
| 1 | **Pure side profile** | Dead 90° to driver side, lens at mid-door height | Full car centered, ~10% headroom, ~15% floor | **Very slow push-in** (5% zoom over 1.4s) | Hero establishing shot. Wing & front splitter must fit. |
| 2 | **Rear 3/4 (left)** | Diagonally behind left rear wheel, ~30° off centerline, lens at taillight height | Whole rear + half of side, wing prominent | **Slow horizontal arc right** (camera orbits ~3° right around the car) | Reveal of the wing and diffuser. |
| 3 | **Rear-deck logo macro** | Directly behind, lens 20cm from spoiler base, looking down at rear deck through underside of wing | Tight on Ferrari badge / rear deck, wing fills top 1/3, diffuser bottom 1/3 | **Slow drift left→right + tiny tilt down** (2% vertical, 5% horizontal) | The cinematic "money" shot. Maximum bokeh. |
| 4 | **Dead-rear elevation** | Centered behind car, lens at bumper height | Full rear symmetrical, wing fills upper third | **Tiny crane up** (camera rises 3cm over 1.4s) | Symmetry shot. Aero on full display. |
| 5 | **Dead-front elevation** | Centered in front of car, lens at headlight height | Full front symmetrical, splitter to roof | **Tiny crane up** (mirror of shot 4) | Symmetry rhyme with shot 4. |
| 6 | **Front-right hood macro** | Diagonally in front of right front wheel, lens 30cm from hood, looking across hood toward windshield | Tight on hood crease, badge, base of windshield, side mirror peeking | **Slow drift left→right** along the hood line | Texture/material shot. |
| 7 | **Front 3/4 (left)** | Diagonally in front of left front wheel, ~30° off centerline, lens at headlight height | Whole front + half of side, headlights catching light | **Slow horizontal arc left→right** (mirror of shot 2's energy) | Mirrors shot 2 for symmetry across the reel. |
| 8 | **Front-left wheel macro** | Crouched, lens 25cm from front-left wheel hub, slightly forward of the wheel | Wheel + brake caliper fills frame, bit of fender + splitter | **Slow drift right→left** (reverse direction = reel "exhales") | Closing shot. Reverses motion direction to feel like a button. |

**Total runtime:** 8 × 1.4s = **11.2s** (perfect for 12s reel slot with a 0.8s music outro).
**All cuts hard on the beat.** No transitions, no fades.

---

## 2. REUSABLE IMAGE PROMPT TEMPLATE (works for any car)

Use this in **one continuous ChatGPT conversation**. Generate Shot 1 first. Then for shots 2–8, **attach the previous image** and start the prompt with `Same exact car, same studio, same lighting as the attached image. Now show me:`. This is the consistency hack.

```
SUBJECT: [CAR_DESCRIPTION — silhouette-led, NOT model name. e.g. "low-slung mid-engine widebody hypercar with massive rear wing, exposed carbon diffuser, deep front splitter, twin-element dive planes, magnesium centerlock wheels"]
FINISH: [PAINT — e.g. "deep oxblood wine metallic clearcoat, near-black in shadow, red hotspots only on highlight rolls, satin not gloss"]
DETAILS: matte black aero, gloss carbon weave on splitter/diffuser/wing endplates, dark anthracite forged wheels, machined gold brake calipers (or [SPEC]).

SHOT [N]: [SHOT NAME from table above]
CAMERA: [position from table — e.g. "lens at headlight height, 30° off centerline, diagonally in front of left front wheel, 50mm equivalent, f/4"]
FRAMING: [framing from table]
COMPOSITION: car occupies [X]% of frame, [Y]% headroom, centered horizontally.

[STYLE LOCK BLOCK — paste verbatim from section 0]
```

---

## 3. THE 8 FILLED-IN PROMPTS — Wine Ferrari (your reference car)

**Subject block (constant across all 8 — paste at top of every prompt):**

```
SUBJECT: low-slung mid-engine widebody Ferrari-style hypercar concept, custom one-off bodywork, massive swan-neck rear wing with carbon endplates, exposed carbon rear diffuser with central fin, deep front splitter, twin dive planes, prancing horse badge on hood and rear deck, aggressive haunches, single-piece bubble canopy greenhouse with thin black A-pillars.
FINISH: deep oxblood wine-red metallic clearcoat, near-black in shadow with red hotspots on highlight rolls, satin clearcoat not high-gloss.
DETAILS: matte black aero elements, gloss carbon weave on splitter / diffuser / wing endplates / rocker panels, dark anthracite five-spoke forged centerlock wheels, gloss black brake calipers, Michelin slick-look tyres with subtle sidewall lettering.
```

### Shot 1 — Pure side profile
> SHOT 1: Full pure 90° side profile of the car, driver side facing camera.
> CAMERA: dead-on perpendicular to the car, lens at mid-door height, ~6 metres back, 50mm equivalent, f/5.6.
> FRAMING: entire car visible nose-to-tail, ~10% headroom, ~15% floor space below the tyres, car perfectly centered horizontally and vertically.
> COMPOSITION: silhouette reads cleanly, both wheels visible, wing and front splitter both inside frame.
> + STYLE LOCK

### Shot 2 — Rear 3/4 left
> *(attach Shot 1)* Same exact car, same studio, same lighting as the attached image. Now show me:
> SHOT 2: Rear three-quarter view from the left side.
> CAMERA: standing diagonally behind the left rear wheel, ~30° off the car's centerline, lens at taillight height, ~3 metres back, 50mm equivalent, f/4.
> FRAMING: entire rear of the car plus the rear half of the driver-side flank visible. Rear wing dominant in upper third, diffuser in lower third, left rear wheel and haunch filling left side of frame.
> COMPOSITION: car occupies ~75% of frame, slight negative space top-right.
> + STYLE LOCK

### Shot 3 — Rear-deck logo macro
> *(attach Shot 2)* Same exact car, same studio, same lighting. Now show me:
> SHOT 3: Extreme cinematic macro of the rear deck and prancing horse badge, shot from directly behind looking slightly down.
> CAMERA: lens 20cm from the rear deck, centered behind the car, slightly above deck height looking down through the underside of the rear wing, 85mm equivalent macro, f/2.8, very shallow depth of field — Ferrari badge razor-sharp, wing endplate softly out of focus in foreground bokeh.
> FRAMING: rear wing fills upper third (slightly defocused), Ferrari badge dead-center on rear deck (sharp), carbon honeycomb diffuser fills lower third (slightly defocused).
> COMPOSITION: vertical layered composition, wing → badge → diffuser, no sky, no floor visible.
> + STYLE LOCK

### Shot 4 — Dead-rear elevation
> *(attach Shot 3)* Same exact car, same studio, same lighting. Now show me:
> SHOT 4: Symmetrical dead-rear elevation of the entire car.
> CAMERA: centered directly behind the car, lens at rear bumper height, ~4 metres back, 50mm equivalent, f/5.6.
> FRAMING: entire rear of the car, perfectly symmetrical, rear wing filling upper third, twin exhausts and diffuser in middle, contact shadow at base.
> COMPOSITION: car centered, ~70% of frame width, equal negative space left and right, ~15% headroom above wing.
> + STYLE LOCK

### Shot 5 — Dead-front elevation
> *(attach Shot 4)* Same exact car, same studio, same lighting. Now show me:
> SHOT 5: Symmetrical dead-front elevation of the entire car.
> CAMERA: centered directly in front of the car, lens at headlight height, ~4 metres back, 50mm equivalent, f/5.6.
> FRAMING: entire front of the car, perfectly symmetrical, front splitter and dive planes in lower third, headlights and bonnet vents in middle, windscreen and roof in upper third.
> COMPOSITION: car centered, ~70% of frame width, equal negative space left and right, ~15% headroom above roof. Mirrors Shot 4 exactly in framing energy.
> + STYLE LOCK

### Shot 6 — Front-right hood macro
> *(attach Shot 5)* Same exact car, same studio, same lighting. Now show me:
> SHOT 6: Tight cinematic macro of the right side of the front hood / bonnet, looking across the hood line toward the base of the windshield.
> CAMERA: standing diagonally in front of the right front wheel, lens 30cm above the hood, looking diagonally back across the hood crease toward the windshield base and right side mirror, 50mm equivalent, f/2.8, shallow depth of field.
> FRAMING: hood crease and prancing horse hood badge sharp in middle, base of windshield and right wing mirror softly defocused in upper-right, fender curve in lower-left.
> COMPOSITION: diagonal composition flowing top-right to bottom-left.
> + STYLE LOCK

### Shot 7 — Front 3/4 left
> *(attach Shot 6)* Same exact car, same studio, same lighting. Now show me:
> SHOT 7: Front three-quarter view from the left side.
> CAMERA: standing diagonally in front of the left front wheel, ~30° off the car's centerline, lens at headlight height, ~3 metres back, 50mm equivalent, f/4.
> FRAMING: entire front of the car plus the front half of the driver-side flank visible. Front splitter and left headlight prominent, hood crease leading the eye toward the windshield, left front wheel and haunch filling left side of frame.
> COMPOSITION: car occupies ~75% of frame, slight negative space top-right. Mirrors Shot 2's framing on the opposite end of the car.
> + STYLE LOCK

### Shot 8 — Front-left wheel macro
> *(attach Shot 7)* Same exact car, same studio, same lighting. Now show me:
> SHOT 8: Tight cinematic macro of the front-left wheel and brake assembly.
> CAMERA: crouched low, lens 25cm from the front-left wheel hub, slightly forward of the wheel looking back along the rocker, 85mm equivalent, f/2.8.
> FRAMING: front-left wheel and brake caliper fill ~70% of frame, slice of front splitter visible on left edge, slice of front fender arch visible on right edge, tyre sidewall in foreground softly defocused.
> COMPOSITION: wheel centered, brake caliper and rotor sharp, spoke detail razor-clean, subtle reflection of studio light on wheel face.
> + STYLE LOCK

---

## 4. IMAGE-TO-VIDEO ANIMATION PROMPTS

Feed each still image into the recommended model with this text prompt. **All clips: 5 seconds, you'll trim to ~1.4s in CapCut.** Set Kling to "low motion" / Runway to "motion strength 2/10".

| # | Model | Prompt |
|---|-------|--------|
| 1 | **Kling 2.1 std** | "Camera holds locked off, then performs an extremely slow, smooth dolly-in toward the car. Total push: 5%. The car is completely static. No part of the car moves, no wheels turn, no reflections shift. Cinematic, locked tripod feel, 24fps motion blur." |
| 2 | **Kling 2.1 std** | "Camera performs a very slow, smooth horizontal arc to the right around the static car, ~3 degrees of orbit. Subtle parallax between the rear wing and the body. Car is completely static. No moving parts. Cinematic, smooth gimbal feel." |
| 3 | **Runway Gen-4 Turbo** | "Extreme micro-movement only. Camera drifts very slowly from left to right, ~5% horizontal travel, with a barely perceptible tilt downward of ~2%. Macro depth of field shifts almost imperceptibly. Car is completely static. Cinematic macro, locked-off feel." |
| 4 | **Kling 2.1 std** | "Camera performs a very slow, smooth vertical crane upward, ~3% travel. The framing rises so the rear wing moves slightly down in frame. Car is completely static. No wheels, no reflections shifting. Locked, symmetrical, cinematic." |
| 5 | **Kling 2.1 std** | "Camera performs a very slow, smooth vertical crane upward, ~3% travel, mirroring the previous shot. Car is completely static. Locked, symmetrical, cinematic." |
| 6 | **Runway Gen-4 Turbo** | "Camera drifts very slowly from left to right along the hood line, ~5% horizontal travel. Macro shallow depth of field stays consistent. Car is completely static. Cinematic macro, locked-off feel." |
| 7 | **Kling 2.1 std** | "Camera performs a very slow, smooth horizontal arc from left to right around the static car, ~3 degrees of orbit. Subtle parallax between the front splitter and the body. Car is completely static. Cinematic, smooth gimbal feel." |
| 8 | **Runway Gen-4 Turbo** | "Camera drifts very slowly from right to left across the wheel face, ~5% horizontal travel. Brake caliper and rotor stay sharp. Wheel is completely static, no rotation whatsoever. Cinematic macro, locked-off feel." |

**Critical motion negatives** (paste into Kling's negative prompt field): `wheels rotating, car moving, car driving, engine vibration, wind, reflections shifting violently, fast camera, whip pan, zoom blur, lens flare, motion blur on car`.

---

## 5. STITCH RECIPE (CapCut, 5 minutes)

1. New project, **9:16, 30fps, 1080×1920**.
2. Drag all 8 video clips onto the timeline in order 1→8.
3. Trim each clip to **1.40 seconds** (use the speed tool to slow Kling's 5s clip to ~28% if you want extra slow-mo, or just hard-trim to the best 1.4s window).
4. **Hard cuts only** between clips. No fades, no dissolves, no transitions.
5. Audio: pick a trending IG/TT audio with a clear beat at ~85 BPM. Snap each cut to a downbeat.
6. **Color grade** (CapCut → Adjust):
   - Contrast +8, Saturation -6, Highlights -10, Shadows +5, Temperature -4 (cooler), Tint +2.
   - Add LUT: "Teal & Orange Subtle" at 30% strength, OR "Cinematic Filmic" at 40%.
7. Add a 0.5s fade-out at the very end. Done.

---

## 6. TROUBLESHOOTING — what to do when consistency breaks

| Symptom | Cause | Fix |
|---|---|---|
| Car looks slightly different in shot 5 vs shot 1 | GPT lost context across the chat | Start a new chat, attach **shot 1 AND** the most recent good shot, regenerate |
| Wing shape changes between shots | Subject block too vague | Add explicit detail: "swan-neck rear wing with two vertical endplates, single horizontal element, mounted on twin pylons" |
| Color drifts to maroon or pink | Lighting confusing the model | Add to STYLE LOCK: "color #4a0e1a deep oxblood, do not lighten, do not pink-shift" |
| Kling animates the car driving away | Motion prompt too loose | Use the negative prompt block above, drop motion strength to minimum |
| Cuts feel jerky | Clips not on the beat | Re-snap to the audio waveform peaks in CapCut |
| Floor reflection inconsistent | Studio backdrop drifting | Add to STYLE LOCK: "no floor reflection, only soft contact shadow under tyres" |

---

## 7. QUICK CHECKLIST BEFORE YOU GENERATE

- [ ] Decided your car (silhouette description, NOT model name)
- [ ] Decided your color (with hex code if possible)
- [ ] Opened ONE ChatGPT chat — will not start fresh chats mid-sequence
- [ ] Style lock block copied to clipboard
- [ ] Have 8 image slots ready in a folder, named `01_side.png`, `02_rear34.png`, etc.
- [ ] Kling + Runway credits topped up (~$10 budget)
- [ ] CapCut project pre-set to 9:16 30fps
