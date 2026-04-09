# Wine Czinger 21C — Image Prompts (1.mp3, 8 shots)

**Target:** ChatGPT Plus (GPT-Image). Manual copy-paste, one shot per chat.
**Output aspect:** 9:16 vertical. Request **2160 × 3840** or the closest 9:16 option the model offers.
**Audio:** `Audio/1.mp3` — 8 shots, steady ~1.9s cadence, no drop.
**Reference chain:** you start with a Google image of a real Czinger 21C as the *identity truth*, then each generated shot becomes a reference for the next. This is a cumulative chain — later shots get attached **more** reference images, not fewer.

---

## 0. PREP — before you start

1. Find a clean, high-res Google image of a real Czinger 21C. Ideal: front 3/4 studio shot, factory white/silver is fine (you'll repaint it in the prompt). Save as `google_ref.jpg`.
2. Create folder `briefs/wine_czinger_21c/stills/`.
3. Generate shots in the **generation order** below (not playback order). Attach every prior generated shot as a reference to the current one.

---

## 1. IDENTITY LOCK (paste verbatim at the top of every prompt)

> **SUBJECT — non-negotiable identity:** Czinger 21C hypercar. A low, wide, American 3D-printed hybrid hypercar with a distinctive **1+1 tandem cockpit** (driver centered, passenger behind — **not** side-by-side seating), a **teardrop-shaped single canopy** that tapers sharply toward the rear, exposed **raw 3D-printed structural lattice panels** (matte charcoal) around the diffuser, rear suspension, and front splitter, quad central exhausts, aggressive active rear wing, and a narrow slit-style front light signature. It is NOT a McLaren, Ferrari, Pagani, or Koenigsegg — do not substitute. If the attached reference image conflicts with this description, trust the attached reference image for shape and proportions.
>
> **PAINT & MATERIALS — lock across all 8 shots:** Deep wine / oxblood pearl paint (dark burgundy red with subtle dark-metallic flake, NOT bright red, NOT maroon-brown). Raw exposed 3D-printed lattice panels remain **unpainted matte charcoal** — do not paint over the lattice. Polished gunmetal multi-spoke forged wheels (same wheel design front and rear). Red brake calipers. Dark-tinted tandem canopy glass. Subtle Czinger badge only — no other text, no logos, no license plate.
>
> **STUDIO & LIGHTING — lock across all 8 shots:** Infinite seamless mid-grey (#6a6a6a) cyclorama studio. Large soft overhead key light slightly camera-left, cool rim light from rear-right tracing the body edges, subtle fill from camera-right. Clean reflections on paint. No environmental props, no people, no text overlays, no watermarks. Color temperature ~5200K.
>
> **TECHNICAL — lock across all 8 shots:** Photoreal, Phase One 150MP look, sharp focus on the primary subject, f/5.6 for wides and f/2.8 for details. **9:16 vertical portrait aspect ratio, 2160 × 3840 pixels.** No border, no letterbox, no frame, subject bleeds to the edges per the composition rules below.

---

## 2. GENERATION ORDER (do them in this order)

The order is chosen so each new shot can be *derived* from what's already locked, maximizing consistency.

| Gen # | Playback # | Shot | Why this position in gen order | Refs to attach |
|---|---|---|---|---|
| **G1** | 1 | Front 3/4 right (wide) | Best angle to lock car identity from a Google ref — shows face, side, wheel, proportions in one view | `google_ref.jpg` |
| **G2** | 2 | Pure side profile | Derives silhouette directly from G1; locks length + canopy shape | `google_ref.jpg`, G1 |
| **G3** | 8 | Dead-front hero symmetric | Locks the front face independently so front details later are consistent | `google_ref.jpg`, G1 |
| **G4** | 4 | Rear 3/4 right (low hero) | Uses G2 (side) + G1 (right fender) to derive rear end | `google_ref.jpg`, G1, G2 |
| **G5** | 7 | Front 3/4 left (mirror) | Uses G2 (left side now visible) + G3 (front face) to build the mirror | G1, G2, G3 |
| **G6** | 5 | Front wheel detail | Crop-equivalent of the front-right wheel from G1 | G1, G3 |
| **G7** | 3 | Rear lattice detail | Crop-equivalent of lattice visible in G4 | G4 |
| **G8** | 6 | Front splitter / badge detail | Crop-equivalent of front face from G3 | G3 |

Playback order (what the final video plays) is: **G1 → G2 → G7 → G4 → G6 → G8 → G5 → G3** (i.e., 1, 2, 3, 4, 5, 6, 7, 8 in playback terms).

---

## 3. FRAMING RULES (same logic every shot)

- **Canvas:** 2160 × 3840, 9:16.
- **Wides (G1, G2, G3, G4, G5):** the entire car fits within the frame with **~8% headroom** above the highest point of the car and **~5% floor** below the tires. Side margins ~6% on the tighter side. No part of the car clipped.
- **Wheel/detail (G6):** wheel + caliper fill **~85%** of the vertical frame. A thin sliver of wine fender visible at the top (~10% of frame height). Tire contact patch visible at the bottom.
- **Material details (G7, G8):** the focal element (lattice / badge) sits on the **upper-third horizontal line**, razor sharp, with wine paint falling out of focus in the background bokeh. No full car visible in these — pure texture shots.
- **No tilt.** Horizon perfectly level. No Dutch angles. No fisheye distortion.
- **No UI, no text, no borders, no vignette applied by the model.**

---

## 4. PROMPTS (in generation order)

For each shot: paste the **IDENTITY LOCK** block from section 1, then the shot block below, then attach the listed reference images.

---

### G1 — Front 3/4 right wide (playback shot 1)
**Attach:** `google_ref.jpg`

> Treat the attached image as the **ground truth for car shape, proportions, and body details** — but repaint it according to the identity lock (wine pearl + raw lattice) and place it in the locked studio environment.
>
> **Composition:** Wide full-car shot. Camera position: **front-right of the car at roughly 2 o'clock**, lens height at front-bumper level (~70cm from the floor), 35mm equivalent full-frame lens, subject distance ~6 meters. The car's nose points toward camera-left, the right flank recedes to the right. Entire car visible — front splitter to rear wing — with ~8% headroom above the canopy and ~5% floor below the front-right tire. Headlights on, subtle warm glow. Wine paint catches a cool rim light along the right fender peak. Small, soft floor reflection directly beneath the car only.

---

### G2 — Pure side profile (playback shot 2)
**Attach:** `google_ref.jpg`, `G1 (shot1.jpg)`

> Ground truth for car identity = attached Google reference + G1. **Same car, same paint, same wheels, same studio, same lighting as G1 — this is a continuity shot, not a new car.**
>
> **Composition:** Dead side profile. Camera perfectly perpendicular to the car's centerline (0° yaw), lens height at **mid-door height** (~90cm), 50mm equivalent, subject distance ~8 meters. **Car runs horizontally across the frame, nose pointing right.** Entire length of the car fills ~88% of the horizontal frame with ~6% margin on nose and tail. Teardrop tandem canopy silhouette clearly readable against the grey backdrop. Flat even studio lighting, minimal shadow under the car. The wheels must match G1 exactly (same spoke count, same finish).

---

### G3 — Dead-front hero symmetric (playback shot 8)
**Attach:** `google_ref.jpg`, `G1 (shot1.jpg)`

> Ground truth = attached Google reference + G1. **Same car, same paint, same studio, same lighting.** Continuity shot.
>
> **Composition:** Perfectly symmetric dead-front hero. Camera on the car's exact centerline (0° yaw, 0° tilt), lens height at **headlight level** (~85cm), 50mm equivalent, subject distance ~6 meters. Car is perfectly bilaterally symmetric in the 9:16 frame — left and right halves mirror each other pixel-wise. Entire car visible with ~8% headroom and ~5% floor. Both headlights lit, splitter lattice visible at the bottom center, canopy teardrop silhouette rising behind the front clip. Subtle floor reflection.

---

### G4 — Rear 3/4 right low hero (playback shot 4)
**Attach:** `google_ref.jpg`, `G1 (shot1.jpg)`, `G2 (shot2.jpg)`

> Ground truth = all attached images combined. Use G1 for the right-side body line, G2 for overall length and canopy shape. **Same car, same paint, same wheels, same studio, same lighting.**
>
> **Composition:** Wide rear three-quarter. Camera position: **rear-right at roughly 5 o'clock**, lens height **low** (~40cm from the floor, crouched), 35mm equivalent, subject distance ~5 meters. Entire rear end of the car dominates the frame — active rear wing raised, quad central exhausts, wide rear haunches, diffuser with visible lattice structure. ~8% headroom above the wing, ~5% floor below. Dramatic cool rim light on the wing's trailing edge. The right rear wheel visible and must match G1's wheel design exactly.

---

### G5 — Front 3/4 left wide, mirror of G1 (playback shot 7)
**Attach:** `G1 (shot1.jpg)`, `G2 (shot2.jpg)`, `G3 (shot3.jpg is G3 dead-front)`

> Ground truth = all attached images. This shot is the **mirror of G1** — same camera distance, same lens, same height, same lighting intensity, but viewed from the LEFT side of the car instead of the right. **Same car, same paint, same wheels, same studio.** Continuity shot.
>
> **Composition:** Wide full-car shot. Camera position: **front-left of the car at roughly 10 o'clock**, lens height at front-bumper level (~70cm), 35mm equivalent, subject distance ~6 meters. The car's nose points toward camera-right, the left flank recedes to the left. Entire car visible with ~8% headroom and ~5% floor. Headlights on. Left wing mirror casts a small shadow on the door. Wine paint catches cool rim light along the left fender peak. The key light is still slightly camera-left (so from the car's perspective, the light direction is mirrored relative to G1 — this is intentional and locks lighting to the studio, not the car).

---

### G6 — Front-right wheel detail (playback shot 5)
**Attach:** `G1 (shot1.jpg)`, `G3 (shot3.jpg dead-front)`

> Ground truth = G1 (wheel design, caliper color, fender paint) and G3 (front face context). **Same car, same wheel design, same caliper, same wine paint.** This is a tight crop — not a different car.
>
> **Composition:** Tight vertical detail of the **front-right wheel and brake caliper**. Camera at ground level (~15cm) beside the front-right tire, 85mm equivalent lens, subject distance ~1.5 meters, f/2.8 shallow depth of field. The wheel + polished gunmetal forged spokes + red brake caliper fill **~85% of the vertical 9:16 frame**. A thin sliver of wine fender visible at the top (~10% of frame height). Tire sidewall and contact patch visible at the bottom. Sharp focus on caliper face and front spoke faces; rear spokes fall into slight bokeh. No full car visible.

---

### G7 — Rear lattice macro detail (playback shot 3)
**Attach:** `G4 (shot4.jpg rear 3/4)`

> Ground truth = G4 (the lattice, wine paint, and rear-end geometry are all visible there). This is a tight macro crop of the rear lattice from G4. **Same car, same paint, same lattice structure.**
>
> **Composition:** Extreme macro of the **3D-printed structural lattice** near the rear diffuser and rear suspension mount. Camera low behind the car at roughly 5 o'clock, 100mm macro lens equivalent, subject distance ~0.8 meters, f/2.8 extreme shallow depth of field. Raw matte charcoal 3D-printed lattice structure in razor-sharp focus on the **upper-third horizontal line** of the frame. Wine paint of the rear fender blurred in background bokeh filling the rest of the frame. No full car visible — pure material and texture. The lattice must be clearly 3D-printed (organic, branching, optimized struts), not woven carbon fiber.

---

### G8 — Front splitter / badge macro detail (playback shot 6)
**Attach:** `G3 (shot3.jpg dead-front)`

> Ground truth = G3 (front face, splitter, badge all visible there). This is a tight macro crop of the front splitter and Czinger badge from G3. **Same car, same paint, same badge, same splitter lattice.**
>
> **Composition:** Extreme macro of the **front splitter area and Czinger badge**. Camera at bumper height (~40cm) directly in front of the car on the centerline, 100mm macro equivalent, subject distance ~0.6 meters, f/2.8 extreme shallow depth of field. The Czinger badge and the 3D-printed front splitter lattice structure in razor focus on the **upper-third horizontal line** of the frame. Wine hood paint blurred above, grey studio floor falling out of focus below. No full car — pure material close-up. The splitter lattice must match the structural style of G7 (same 3D-print aesthetic).

---

## 5. CONSISTENCY CHECKLIST (run this after each generation before moving on)

Reject and regenerate if **any** of these fail:

- [ ] Car is clearly a Czinger 21C (tandem 1+1 canopy, teardrop shape, not a McLaren/Ferrari)
- [ ] Paint is deep wine / oxblood pearl, not bright red, not maroon-brown, not pink
- [ ] Lattice panels are raw matte charcoal, NOT painted wine
- [ ] Wheel design matches G1 exactly (same spoke count, same finish)
- [ ] Brake calipers are red
- [ ] Canopy glass is dark-tinted
- [ ] Background is seamless mid-grey studio — no environment, no props, no people
- [ ] Lighting direction matches the style lock (key camera-left, rim rear-right)
- [ ] Aspect ratio is 9:16 portrait with no letterboxing or borders
- [ ] Framing matches the per-shot composition rules (headroom, floor, subject size)
- [ ] No text, no watermarks, no license plates, no UI

If a shot fails on **identity** (wrong car shape), regenerate with a stronger reference image. If it fails on **paint or lighting**, regenerate citing the specific previous shot that got it right.

---

## 6. Render

Once `shot1.jpg` … `shot8.jpg` are all in `briefs/wine_czinger_21c/stills/`:

```
./pipeline/make_video.sh briefs/wine_czinger_21c/stills/ out/wine_czinger_21c.mp4 --audio Audio/1.mp3
```

(Note: `make_video.sh` currently runs the Tier-1 planner; wiring the locked `audio_timings_master.json` frames `[46,43,45,48,44,45,46,45]` is Phase 3 — pending.)
