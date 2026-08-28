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

