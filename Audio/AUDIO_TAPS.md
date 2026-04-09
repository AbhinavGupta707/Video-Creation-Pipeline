# Audio test set — ground-truth tapped cuts

These are user-tapped shot durations recorded with iPhone Stopwatch lap timer.
Each list = per-shot duration in seconds. Number of shots = list length + 1
(the last shot runs from final tap to track end).

## Files

| File | Source | Tap status | Use |
|---|---|---|---|
| `audio 1.mp3` | Original test track | Tapped (7 cuts → 8 shots) | Train/validate |
| `1.mp3` | New car-edit track #1 | Tapped (7 cuts → 8 shots) | Train/validate |
| `2.mp3` | New car-edit track #2 | Tapped (9 cuts → 10 shots) | Train/validate |
| `3.mp3` | New car-edit track #3 | Tapped (10 cuts → 11 shots) | Train/validate |
| `4.mp3` | New car-edit track #4 | **Blind — not tapped** | Held-out test set |

## Tapped shot durations (seconds)

### `audio 1.mp3`
```
2.47, 2.18, 2.12, 2.35, 1.03, 1.15, 1.13
```
Cumulative cut points: 2.47, 4.65, 6.77, 9.12, 10.15, 11.30, 12.43
Shots: 8 (last shot = 12.43s → end)

### `1.mp3`
```
1.90, 1.96, 1.85, 1.88, 1.84, 1.86, 1.92
```
Cumulative cut points: 1.90, 3.86, 5.71, 7.59, 9.43, 11.29, 13.21
Shots: 8 (last shot = 13.21s → end)
Pattern: very even spacing — likely a steady-tempo track with no big dynamic shift.

### `2.mp3`
```
1.98, 1.83, 1.60, 1.75, 1.71, 1.77, 1.63, 1.80, 1.68
```
Cumulative cut points: 1.98, 3.81, 5.41, 7.16, 8.87, 10.64, 12.27, 14.07, 15.75
Shots: 10 (last shot = 15.75s → end)
Pattern: tight 1.6–2.0s shots — moderate-energy track, regular cadence.

### `3.mp3`
```
2.60, 2.58, 1.31, 2.10, 2.23, 1.04, 1.03, 2.05, 1.21, 1.03
```
Cumulative cut points: 2.60, 5.18, 6.49, 8.59, 10.82, 11.86, 12.89, 14.94, 16.15, 17.18
Shots: 11 (last shot = 17.18s → end)
Pattern: mixed — alternates 2-second phrases with 1-second hits. Likely
breakdown→drop sections. Highest variance of the four.

### `4.mp3`
**Blind set.** No taps recorded. Used to validate the planner generalizes
beyond what was used for tuning.

## Diversity check

| Track | Shot count | Min dur | Max dur | Mean | StDev | Variance signature |
|---|---|---|---|---|---|---|
| audio 1 | 8 | 1.03 | 2.47 | 1.63 | 0.62 | Slow→fast (intro→drop) |
| 1 | 8 | 1.85 | 1.96 | 1.89 | 0.04 | Very steady (low variance) |
| 2 | 10 | 1.60 | 1.98 | 1.75 | 0.12 | Tight steady-mid |
| 3 | 11 | 1.03 | 2.60 | 1.72 | 0.65 | High variance (mixed sections) |

This is good test diversity:
- audio 1 = dynamic arc with clear drop
- 1 = monotone steady (regularity test — does the planner avoid over-cutting?)
- 2 = mid-density even (medium baseline)
- 3 = high variance with breakdown/drop alternation
- 4 = unknown (held out)

## Tap notation

The user taps **at the moment a cut should occur** — the duration value is
"how long the shot BEFORE this tap lasted". So:

- Tap 1 = duration of shot 1
- Tap 2 = duration of shot 2
- ...
- Final shot duration = `track_duration − sum(taps)`

Tolerance for matching: ±100ms is "perfect", ±200ms is "good", >300ms is "wrong".
