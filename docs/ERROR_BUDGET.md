# Error Budget

**Owner:** seat S. **Revised at:** Gate 1 (against measured Allan variance), Gate 2, Gate 3.
**Status:** provisional allocation — the numbers below are targets derived from first principles,
not measurements. Sprint 1 replaces the sensor assumptions with our own Allan-variance run.

The grade metric is **position drift < 10% of distance travelled**. This document says where that
10% is allowed to go, so that when a term overruns we know which one and who owns it.

---

## 1. Reference scenario

Everything below is sized against one concrete case, chosen because it is the problem statement's
central story and roughly the worst realistic tunnel:

| Quantity | Value |
|---|---|
| Speed *v* | 16.7 m/s (60 km/h) |
| Outage duration *t* | 60 s |
| Distance travelled *L* | ≈ 1,000 m |
| **Total error budget** | **100 m** (10% of L) |

A 100 m budget sounds generous. It is not, once you see how fast the yaw term climbs.

---

## 2. Why the obvious approach fails

Accelerometer bias `b_a` double-integrates:

```
e_pos ≈ ½ · b_a · t²
```

At a typical phone bias of 10 mg ≈ 0.0981 m/s², over 60 s:

```
½ × 0.0981 × 60² = ½ × 0.0981 × 3600 ≈ 176 m
```

**176 m of error in 60 s, from bias alone, before any noise.** That is 176% of the budget from a
single unmodelled term. This is the whole reason the architecture regresses forward speed with a
network and constrains it with NHC/ZUPT, instead of integrating acceleration twice.

**Rule:** acceleration is never double-integrated to obtain speed. Anywhere. See
[DECISION_LOG.md](DECISION_LOG.md) D-003.

---

## 3. The dominant term: heading

A constant gyro bias `b_g` integrates linearly into heading error, which converts into **lateral**
position error quadratically:

```
Δψ(t) = b_g · t
e_lat ≈ v · ∫₀ᵗ Δψ dτ = ½ · b_g · v · t²
```

Lateral error is the dangerous kind. Along-track error is bounded by the speed head and corrected
by map matching. Lateral error is unbounded, and once it exceeds roughly half a road width the map
matcher stops rescuing us and starts confidently snapping onto the wrong road — turning a metric
problem into a categorically wrong answer.

### 3.1 What the whole budget buys

Spending the *entire* 100 m on gyro bias:

```
½ · b_g · 16.7 · 3600 < 100
b_g < 100 / 30,060 ≈ 3.33 × 10⁻³ rad/s ≈ 0.19 °/s ≈ 690 °/hr
```

*(The condensed brief prints 683 °/hr; the difference is rounding. Either way the conclusion holds.)*

690 °/hr looks trivially easy — phone gyros are 10–100 °/hr of bias *instability*. **This number is
misleading and should not be quoted as evidence the problem is easy.** It assumes bias is constant,
perfectly known in direction, and the only error term. In reality we face residual bias after
estimation, bias random walk, angular random walk, scale-factor error during turns, and R_sv
misalignment — and they add.

### 3.2 What residual bias actually costs

The number that matters is the bias **left over** after ZARU and GNSS-available estimation:

| Residual gyro bias | in °/hr | Lateral error at 60 s | Share of budget |
|---|---|---|---|
| 0.005 °/s | 18 | 2.6 m | 3% |
| 0.010 °/s | 36 | 5.2 m | 5% |
| 0.050 °/s | 180 | 26 m | 26% |
| 0.100 °/s | 360 | 52 m | 52% |
| 0.190 °/s | 684 | 100 m | **100%** |

The operating point we need is the **0.005–0.01 °/s** row. That is achievable, but only with
aggressive bias estimation while GNSS is available, a **bias snapshot at tunnel entry**, and **ZARU
at every detected stop**.

### 3.3 Angular random walk is not the problem at these timescales

Heading uncertainty from ARW grows as `σ_ψ(t) = ARW · √t`, and its contribution to lateral error is
`≈ v · (2/3) · ARW · t^1.5`. At 60 s and 16.7 m/s:

| ARW | Lateral error at 60 s |
|---|---|
| 1 °/√hr | ≈ 1.5 m |
| 5 °/√hr | ≈ 7.5 m |

**Conclusion: residual bias dominates ARW by roughly an order of magnitude over a 60 s outage.**
Spend the effort on bias observability (ZARU, snapshot, map heading feedback), not on noise filtering.
Re-check this conclusion at Gate 1 against our own Allan-variance numbers — it flips for outages of
several minutes.

---

## 4. Speed error

Forward-speed error `ε_v` integrates linearly into along-track error:

```
e_along ≈ ε_v · t
```

For 30 m over 60 s, the speed head must hold `ε_v ≈ 0.5 m/s` (1.8 km/h) RMS. That is a realistic
target for a learned head on car data, and it is the number seat M is training against.

Along-track error is also the error map matching corrects best — it slides the estimate along a
committed road segment. Treat 0.5 m/s as the requirement, not the aspiration.

---

## 5. Mounting misalignment (R_sv)

A yaw misalignment `δ` between the phone and vehicle frames steers the whole velocity vector off
course, producing lateral error:

```
e_lat ≈ v · t · δ        (small δ)
```

For 20 m over 60 s at 16.7 m/s:

```
δ = 20 / (16.7 × 60) ≈ 0.020 rad ≈ 1.15°
```

**The phone-to-vehicle yaw must be known to about 1 degree.** This is a hard requirement and it is
why R_sv goes into the filter state and is estimated recursively under NHC, rather than being fixed
once by PCA at startup (D-006). It is also why the mount-disturbance detector matters: a phone
knocked by 5° silently costs 87 m over the same outage.

---

## 6. Provisional allocation

| Term | Budget | Owner | Attacked by |
|---|---|---|---|
| Lateral — residual gyro bias | 40 m | S | ZARU at every stop, bias snapshot at tunnel entry, map-matching heading feedback, magnetometer as weak prior only |
| Along-track — speed estimate | 30 m | M | Learned speed+variance head, NHC, ZUPT |
| Lateral — R_sv misalignment | 20 m | S | R_sv in filter state, observable through turns under NHC; bump detector re-inflates covariance |
| Gyro scale factor during turns | 10 m | S | Scale-factor state, Allan-variance-seeded Q, map heading feedback |
| **Total** | **100 m** | | |

These add in quadrature in the happy case and linearly in the bad one; size against the linear case.

Map matching is deliberately **not** in the allocation. It is an outer correction layer that should
buy margin back, not a term we plan to spend. If the budget only closes with map matching, it does
not close in a car park.

---

## 7. Instrumentation requirements

The budget is worthless if we cannot see which term is overrunning. Every evaluation run logs:

- **Yaw error time series**, separately and always ([EVALUATION.md](EVALUATION.md) §4.4).
- Estimated gyro bias vs. time, with a marker at each ZUPT/ZARU application.
- Estimated R_sv and its covariance, with mount-disturbance events marked.
- Along-track and cross-track error **decomposed**, not just the norm — a 40 m error means very
  different things depending on which direction it points.
- Covariance trace, to confirm the filter's own uncertainty tracks reality.

---

## 8. The honest limits

**Tunnels and underpasses (tens of seconds to ~1–2 min): the 10% target is achievable** with learned
speed + NHC + ZUPT/ZARU + a continuously running filter + map matching. Without map matching, expect
to miss 10% occasionally on curved tunnels and roundabouts, where heading error and road curvature
compound.

**Multi-level underground car parks: this is the genuinely hard case and the least certain claim we
make.** There is no road graph, so map matching is unavailable; dwell times are long, speeds low, and
turns frequent. The fallback is tight NHC + barometer floor detection (one level ≈ 2.5–3 m ≈
0.3–0.36 hPa) + ramp detection from sustained pitch. **Drift may exceed 10% on a long stay.**

State this in the submission before a judge finds it. An honest limitation costs a fraction of what
an overclaim costs when it is tested live.

---

## 9. Sensor noise — measured, and the grades for context

### 9.1 Measured on IO-VNBD

These are **our numbers**, from IO-VNBD's own stationary segments — the same three phones (Huawei
P20 Pro / Moto G7 Power / BlackBerry Priv) that produced every sequence we are graded on. They are
not a datasheet, not a published range, and not our own team phone (D-038, D-045).

Produced by [`eval/allan.py`](../eval/allan.py); regenerate with

```bash
python -m eval.allan --paths-from data/manifest/allan_segments_input.txt --out-dir eval/figures
```

which writes `eval/figures/allan_{segments,curve,coefficients}.csv` and `allan_summary.json`, each
carrying the commit SHA and seed that produced it.

| Parameter | Measured | Worst axis | In SI, as `FilterConfig` takes it |
|---|---|---|---|
| Angular random walk | **1.41 °/√hr** (range 0.60–1.41 across axes) | `gyro_pitch`, S-T2 | `gyro_arw = 4.11e-4` rad/s/√Hz |
| Velocity random walk | **0.45 m/s/√hr** | `accel_z`, S-T7 | `accel_vrw = 7.46e-3` m/s²/√Hz |
| Gyro bias instability | **42 °/hr** at τ ≈ 45 s | `gyro_yaw`, S-T7 | 2.04e-4 rad/s |
| Accel bias instability | **0.34 mg** at τ ≈ 20 s | `accel_x`, S-T7 | 3.32e-3 m/s² |
| Gyro bias driving noise | *derived, not measured* | — | `gyro_bias_rw = 5.48e-5` rad/s²/√Hz |
| Accel bias driving noise | *derived, not measured* | — | `accel_bias_rw = 1.04e-3` m/s³/√Hz |
| Mount driving noise `σ_sv` | **not measured, and not guessed** | — | `mount_rw = 0.0` rad/s/√Hz (D-048) |

The last row is the one to read twice. [SE23_PROPAGATION.md](SE23_PROPAGATION.md) §5.3 names `σ_sv`
in `Q_c`, but nothing in this repo measures it — the Allan run characterises the IMU, not the way a
phone sits in a cradle. It is therefore **zero**, which states the model P-02 actually implements
(a rigid mount) rather than dressing a guess as a measurement. The consequence is concrete: the
`ξ_sv` block of `P` cannot grow under propagation, so until P-11 estimates `R_sv` in-filter and
wires `detect_mount_disturbance` to re-inflate it, the ~1° requirement in §5 rests on the PCA
initialiser alone. That is a limitation to state in the write-up, not a term the filter models.

All four measured values land inside the phone-MEMS column of §9.3. The ARW replaces a `3.0e-3`
placeholder that was 10.3 °/√hr — 7× pessimistic and outside our own stated range (plan item R-2).

**Method.** Overlapping Allan deviation per axis at 10 Hz (the `S-` stream's rate, confirmed from
the timestamps: median Δt = 100.0 ms). ARW/VRW is the white-noise coefficient at τ = 1 s, taken as
the log-mean of σ(τ)√τ over τ ∈ [0.2, 2] s and **accepted only if the fitted log-log slope is
within 0.15 of −½**. Bias instability is the flat minimum, `B = σ_min / 0.664` (IEEE Std 952).
The scalar seeding `FilterConfig` is the worst axis over both segments: an undersized Q makes the
filter reject good measurements at the χ² gate, and that failure reads as a sensor problem rather
than a tuning one (D-031).

### 9.2 What these numbers do not cover — read before quoting them

Four limits, each of which changes how far the numbers can be pushed:

1. **There is no >20 min stationary segment in the `S-` stream.** [DATASETS.md](DATASETS.md) §1.4
   said there was; that claim did not survive being checked against the files. Sweeping all 168
   distinct `S-` files, the longest continuous, uniformly-sampled, genuinely-still stretch is
   **507 s (8.4 min)**, in `S-T2`. Consequence: τ_max is ~51 s at the usual T/10 confidence limit.
2. **Bias instability is an upper bound, not a floor.** At τ_max most axes are still descending —
   the curve has not been observed to turn back up, so what is reported is σ at the longest τ the
   record supports. The true floor is at some larger τ and is *smaller*. Conservative for Q,
   wrong to quote as "the sensor's bias instability" without this sentence.
3. **`gyro_bias_rw` / `accel_bias_rw` are derived, not measured.** The +½ rate-random-walk slope
   needs a record an order of magnitude longer. They come from modelling each bias as first-order
   Gauss–Markov with the measured `B` and the measured Allan-minimum τ: `q = B √(2/τ_c)`.
4. **VRW rests on a single axis.** Five of six accelerometer fits failed the −½ slope check: a
   parked car genuinely accelerates at low frequency (thermal settle, wind, suspension), and that
   is signal, not sensor noise. Only `accel_z` on S-T7 gave a clean white band. Stated as one axis
   rather than dressed up as three.

**These are bench-quiet numbers.** Both usable segments sit an order of magnitude inside the ZUPT
thresholds. Segments that pass the ZUPT detector but *not* that quietness margin — a car idling
with an occupant, `S-A6` — return an apparent ARW ~6× larger. That number is real and it measures
the cabin, not the gyroscope. In-cabin vibration therefore belongs in Q as an explicit inflation
term at Gate 1, sized against a driving segment, not folded silently into the ARW here.

### 9.3 Sensor grades, for context

| Parameter | Phone MEMS | Tactical MEMS | FOG (edge-engine target) |
|---|---|---|---|
| Gyro bias instability | ~10–100 °/hr | ~0.3–3 °/hr | <0.01–0.1 °/hr |
| Angular random walk | ~0.5–5 °/√hr | ~0.1–0.3 °/√hr | <0.05 °/√hr |
| Accel bias instability | ~0.1–1 mg | ~10–50 µg | ~1–10 µg |
| Scale-factor error | ~1–5 % | ~100–1000 ppm | ~10–100 ppm |

Phone IMUs are 1–3 orders of magnitude worse than tactical grade and usually do not publish these
numbers at all — which is why we measure our own.

**Allan variance procedure:** compute the overlapping Allan deviation σ(τ) per axis over a
stationary, temperature-stable record. The **−½ slope** region gives ARW/VRW (read σ at τ = 1 s);
the **flat minimum** gives bias instability as **σ_min ÷ 0.664** — this is a division, and an
earlier revision of this section wrote "×0.664", which understates B by 2.3× (D-046); the **+½
slope** gives rate random walk. Seed the InEKF process noise Q from these instead of guessing.

A separate several-hour, multi-temperature run on our own handset — logged at max rate via
`HIGH_SAMPLING_RATE_SENSORS` — remains worth doing for the demo and edge story, and would bound
thermal drift and resolve limits 2 and 3 above. It is explicitly **not** on the Gate 1 critical
path (D-038): it characterises a device that produced none of the graded data.
