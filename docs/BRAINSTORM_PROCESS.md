# Brainstorm Process — Creative Brief & Ideation Guide

> **This is a PROCESS DOC, not code.** Brainstorming is fundamentally a conversation, not an algorithm. This file documents the structured way to ideate new car video concepts so the output can be fed into the pipeline cleanly.

---

## Why a process doc instead of a script

You can't automate creative spark. But you CAN:
1. **Structure the conversation** — ensure no critical info is missed
2. **Standardize the output format** — so downstream tools (prompt generator, render pipeline) can consume it
3. **Capture the criteria** — make decisions explicit instead of vibe-based
4. **Enable comparison** — multiple briefs can be compared side-by-side

The goal of brainstorming is to produce a **creative brief**: a one-page document that defines the video so completely that the prompt generator can produce 8 AI image prompts from it without further input.

---

## Part 1 — The Creative Brief schema

A brief has 8 sections. Fill them in with an LLM (Claude/ChatGPT) or alone.

```yaml
# === CREATIVE BRIEF ===

# 1. ONE-LINE PITCH
# What is this video in one sentence?
pitch: "A wine-red Ferrari hypercar revealed in a soft studio with cinematic walkaround"

# 2. SUBJECT (the car)
subject:
  make: "Ferrari"
  model: "custom widebody hypercar (P80/C-inspired)"
  year_or_era: "concept / one-off"
  color: "deep wine red metallic with subtle pearl flake"
  body_kit: "aggressive aero, massive carbon wing, NO STEP rocker decal"
  wheels: "black 5-spoke forged"
  livery: "Ferrari shield on fender, RACIETY California plate"
  unique_details: "exposed carbon diffuser, yellow Brembo calipers"

# 3. ENVIRONMENT
environment:
  setting: "professional photo studio"
  background: "neutral grey cyclorama, gradient darker top to lighter bottom"
  ground: "polished light grey reflective floor with contact shadow"
  time_of_day: "n/a (studio)"
  weather: "n/a (indoor)"
  surrounding_elements: "none — car is the only object"

# 4. LIGHTING
lighting:
  style: "single soft top key, no fill"
  direction: "directly above and slightly camera-front"
  quality: "large softbox, diffused"
  color_temp: "neutral white (~5500K)"
  contrast: "high (deep shadows below body, bright highlights on top edges)"

# 5. MOOD / AESTHETIC
mood:
  feeling: "premium, intentional, restrained, expensive"
  references:
    - "Ferrari official launch videos"
    - "Top Gear hero reveal sequences"
    - "Pagani photography style"
  avoid:
    - "neon / cyberpunk"
    - "outdoor / golden hour"
    - "people / hands / motion"

# 6. CAMERA LANGUAGE
camera_language:
  total_shots: 8
  duration_target: 13.2  # seconds
  pacing: "slow first half, punchy second half"
  motion_style: "subtle parallax, mostly locked-off, one strong arc on the wing macro"
  shot_type_breakdown:
    - {idx: 1, type: "establishing wide", angle: "side profile"}
    - {idx: 2, type: "wide", angle: "rear-3/4"}
    - {idx: 3, type: "ECU macro", angle: "wing badge close-up"}
    - {idx: 4, type: "wide", angle: "direct rear symmetric"}
    - {idx: 5, type: "wide", angle: "direct front symmetric"}
    - {idx: 6, type: "ECU detail", angle: "front bonnet"}
    - {idx: 7, type: "HERO wide", angle: "front-3/4"}
    - {idx: 8, type: "ECU detail", angle: "front-left wheel close"}

# 7. AUDIO (if known)
audio:
  style: "cinematic electronic / orchestral hybrid"
  bpm_target: 145  # if specific song chosen, fill this
  energy_arc: "build up first 8 sec, drop on hero shot 7 (~10.9s)"
  reference_tracks:
    - "(any URLs or track names)"

# 8. OUTPUT SPECS
output:
  resolution: "1080x1920"
  fps: 24
  aspect: "9:16 vertical"
  duration: 13.2
  delivery: "Instagram Reel"
```

---

## Part 2 — The brainstorming conversation flow

When using an LLM (Claude/ChatGPT) to develop a brief, follow this 6-step conversation:

### Step 1: Open broad
> **You:** "I want to create a 13-second car video. Help me brainstorm. Start by asking me 5 questions to understand the FEELING I want to create. Don't suggest cars yet."

The LLM should ask things like:
- What emotion should the viewer feel?
- Daytime or nighttime?
- Is it a "hero showcase" or a "lifestyle moment"?
- Aggressive or refined?
- Studio-clean or environmental?

### Step 2: Narrow to specifics
> **You:** "[answers to step 1]. Now suggest 3 directions I could go, each with a different car + environment combo that fits the feeling."

The LLM proposes 3 distinct creative directions. Pick one (or hybrid).

### Step 3: Lock the subject and setting
> **You:** "I want direction 2: [car description] in [environment]. Help me get specific. Describe the exact car (color, body kit, wheels, livery details) and the exact environment (lighting, time of day, ground, surrounding elements)."

The LLM produces a detailed subject+environment description.

### Step 4: Define the camera language
> **You:** "Now design the 8-shot sequence. Use the wine ferrari structure as a reference: establish, walkaround, ECU detail, hero reveal, closing detail. For each shot, give: position relative to car, lens feel, framing (wide/MS/CU/ECU), motion type (push-in / pan / tilt / static)."

The LLM produces a shot list. **Critical:** insist on shot-by-shot specificity.

### Step 5: Mood and references
> **You:** "What 3 reference videos or photographers should we look at for visual style? What should we AVOID?"

The LLM gives reference points and anti-patterns.

### Step 6: Compile to brief
> **You:** "Compile everything we discussed into the YAML brief format from BRAINSTORM_PROCESS.md."

The LLM outputs the final structured brief.

---

## Part 3 — Validation checklist

Before passing the brief to the prompt generator, verify:

- [ ] **One-line pitch** is sharp and specific (not "a cool car video")
- [ ] **Car details** include color, body kit, wheels, badging, plate
- [ ] **Environment** is fully described (not just "a street")
- [ ] **Lighting** specifies direction, quality, and color temp
- [ ] **Mood** has at least 2 reference videos and 2 things to avoid
- [ ] **Camera language** has shot count, duration, and per-shot type/angle
- [ ] **Audio** has BPM target if known (otherwise mark as "TBD")
- [ ] **Output specs** are concrete numbers, not "high quality"

If any section is vague, **go back to that step and ask the LLM more questions.**

---

## Part 4 — How the brief drives the pipeline

```
Creative Brief (YAML)
        │
        ▼
┌─────────────────────────┐
│ Prompt Generator         │
│ (Phase 6 of roadmap)     │
│  reads: brief + shot list│
│  outputs: prompts.md     │
└─────────────────────────┘
        │
        ▼
   AI image tool
   (8 stills)
        │
        ▼
┌─────────────────────────┐
│ make_video.sh            │
│  + per_shot_config       │
│  + (optional) audio file │
└─────────────────────────┘
        │
        ▼
   final video.mp4
```

The brief is the **single source of truth** for the project. Save it as `briefs/<project_name>_brief.yaml` so future renders can reference it.

---

## Part 5 — Example: a fictional new brief

Here's what a brief for a NEW video might look like:

```yaml
pitch: "A matte black Lamborghini Huracán prowling a rain-slick Tokyo street at midnight, neon reflections on the paint"

subject:
  make: "Lamborghini"
  model: "Huracán Performante"
  year_or_era: "2024"
  color: "matte black with subtle anthracite accents"
  body_kit: "Performante factory aero — rear wing, forged carbon side blades"
  wheels: "Forged carbon dished 5-spoke, anthracite finish"
  livery: "minimal — Lambo shield only, no decals"
  unique_details: "neon green brake calipers, satin black exhaust tips"

environment:
  setting: "narrow Tokyo street at night, after rain"
  background: "warm neon shop signs (kanji + katakana), reflections in puddles"
  ground: "wet asphalt with neon reflections"
  time_of_day: "midnight, post-rain"
  weather: "just stopped raining, wet ground, dry air"
  surrounding_elements: "vending machine glow camera-left, distant headlights, no people"

lighting:
  style: "neon practicals + rim from headlight"
  direction: "mixed — neon sources from sides, key from car's own headlights"
  quality: "hard, colored, mixed temperature"
  color_temp: "warm neons (3000K) + cool moonlight ambient (7000K)"
  contrast: "very high, deep shadows, vivid highlights"

mood:
  feeling: "predatory, mysterious, cinematic, restrained menace"
  references:
    - "Drive (2011) car shots"
    - "Blade Runner 2049 vehicle photography"
    - "Need for Speed Heat night sequences"
  avoid:
    - "daylight"
    - "people"
    - "static brochure shots"
    - "obvious CGI feel"

camera_language:
  total_shots: 8
  duration_target: 13.0
  pacing: "moody slow, punchy back half, drop on shot 6 wheel close-up"
  motion_style: "subtle parallax, all locked-off, one slow side dolly past the car"
  shot_type_breakdown:
    - {idx: 1, type: "establishing wide", angle: "low front-3/4 with neon background bokeh"}
    - {idx: 2, type: "wide", angle: "side profile against neon shop"}
    - {idx: 3, type: "ECU detail", angle: "matte paint texture with neon spec highlight"}
    - {idx: 4, type: "wide", angle: "rear-3/4 with vending machine glow"}
    - {idx: 5, type: "ECU macro", angle: "Lamborghini badge with neon reflection"}
    - {idx: 6, type: "ECU dramatic", angle: "front wheel low, ground-level, brake caliper visible"}
    - {idx: 7, type: "HERO wide", angle: "front fascia head-on, headlights on, neon halo"}
    - {idx: 8, type: "wide outro", angle: "tail lights driving away (slight motion ok)"}

audio:
  style: "synthwave / dark electronic"
  bpm_target: 100
  energy_arc: "tense build, drop on shot 6 wheel"
  reference_tracks:
    - "Carpenter Brut - Turbo Killer"
    - "Mitch Murder - Interceptor"

output:
  resolution: "1080x1920"
  fps: 24
  aspect: "9:16 vertical"
  duration: 13.0
  delivery: "Instagram Reel"
```

This brief is **complete enough** that the prompt generator could produce 8 detailed AI image prompts without asking any further questions.

---

## Part 6 — Anti-patterns to avoid

1. **Vibes-only brief** — "make it cool" tells the prompt generator nothing
2. **No reference videos** — without references, the LLM falls back to generic "car commercial" tropes
3. **Mixed environments** — don't try to do "studio + street + mountain" in one video; pick one
4. **Inconsistent mood** — "playful but menacing but luxurious" is impossible to render coherently
5. **Too many shots** — 6-10 is the sweet spot for a 10-15s reel; 12+ feels rushed
6. **Generic car** — "a sports car" produces a mishmash; specify make/model/color
7. **Hand-wavy lighting** — "good lighting" → AI invents random lighting; specify direction + quality
8. **No audio plan** — leaving audio for later means the cuts won't match. Define BPM early.

---

## Part 7 — When to come back and refine

After rendering the first version of the video, you may need to revise the brief if:
- The car looks inconsistent across shots → tighten subject details
- The environment morphs between shots → tighten environment details
- The motion feels wrong → adjust per_shot_config (not the brief)
- The mood doesn't match → revisit references in the brief

**The brief is a living doc.** Save updated versions as v2, v3, etc.

---

## TL;DR

1. **Have a structured conversation** with Claude/ChatGPT using the 6-step flow above
2. **Output a complete YAML brief** with all 8 sections filled in
3. **Validate** against the checklist
4. **Save** as `briefs/<project>_brief.yaml`
5. **Pass to prompt generator** (Phase 6 of roadmap) to produce AI image prompts
6. **Iterate** if the rendered output doesn't match intent
