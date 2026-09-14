# Method — SIH 2026, PS 26168

**AI-based intelligent dead reckoning for GNSS-denied ground vehicles.**
**Owner:** seat C, with each section drafted by the seat that built the thing.
**Status:** first full pass, 1 Sep 2026. §12 is deliberately empty and says why.

---

## 0. How to read the numbers in this document

Every quantity below is labelled with **where it came from**, because they are not all the same
kind of thing and a reader who cannot tell them apart cannot check any of them.

| Tag | Meaning | Where it lives |
|---|---|---|
| **[measured]** | Produced by a tool in this repository from real IO-VNBD bytes, written to a stamped artefact | `eval/figures/allan_*.csv`, `allan_summary.json` |
| **[verified]** | A property of our own code, asserted by a test that runs in CI | `tests/` — the test is named |
| **[analysis]** | Closed-form arithmetic from stated inputs; no data involved | [ERROR_BUDGET.md](ERROR_BUDGET.md) |
| **[evaluated]** | An evaluation result from `eval/run.py` under the frozen protocol | **there are none yet — see §12** |
| **[published]** | Someone else's number, cited, and never ours | §14 |

**No [evaluated] number exists at the time of writing, and none is substituted for.** D-042 is
explicit: no performance figure enters the write-up, the deck or the demo unless `eval/run.py`
produced it under the frozen protocol, stamped with commit and seed. §12 states the blocker.

---

## 1. Problem and framing

A ground vehicle loses GNSS and must keep reporting where it is. The graded metric is **position
drift under 10% of distance travelled**, and the problem statement asks for a seamless transition
into and out of the denied condition, on hardware deployable at the edge.

Three operating cases, in descending order of how confident we are about them:

1. **Road tunnels and underpasses** — tens of seconds to one or two minutes. The central case, and
   the one the 10% target is comfortably achievable in.
2. **Urban canyons** — GNSS is present but degraded, so the interesting question is rejecting bad
   fixes rather than surviving their absence. Our χ² gate is the same mechanism in both cases.
3. **Multi-level underground car parks** — long dwell, low speed, frequent turns, no road graph.
   **This is the hardest case and our least certain claim.** §13.

Sized against the reference case throughout: a 1 km tunnel at 60 km/h, 60 s, so a **100 m** total
error budget **[analysis]**.

---

## 2. Why the obvious approach fails

Integrate the accelerometer twice and you are integrating its bias twice with it. A constant
unmodelled specific force `b` from rest gives `x = ½ b t²`, so **10 mg of accelerometer bias is
176.5 m of position error in 60 s** **[analysis]** — nearly twice the entire budget, before any
noise, from a bias an order of magnitude better than a phone's datasheet.

This is not a rhetorical figure. It is measured through our own naive-strapdown baseline and pinned
by `tests/test_baselines.py::test_ten_milli_g_of_accel_bias_costs_the_176_m_the_budget_says`
**[verified]**, and it is the fourth line in every mandatory trajectory figure so that a reader can
see what the aiding buys.

It is why **hard rule H-2** in this project is that acceleration is *never* double-integrated to
obtain speed or displacement. Speed comes from a learned head and from kinematic constraints. The
one exception is that baseline, which exists precisely to measure the cost, and which is labelled
"naive strapdown" in every name, docstring and caption so it can never be mistaken for the method.

### 2.1 And the error that actually dominates is not speed

Along-track error from a speed error `ε_v` grows as `ε_v · t` — linear, and correctable by map
matching, which slides an estimate along a committed road segment. Heading error does not behave
that way. A residual gyro bias `b_g` at speed `v` gives lateral error

```
e_lat ≈ ½ · b_g · v · t²
```

**[analysis]** — quadratic, sideways, and it makes a map matcher snap confidently onto the wrong
road. At 0.1 °/s the yaw term alone eats 52 m of a 100 m budget. **The dominant error term is yaw**,
which is why yaw error is logged and plotted separately from position, always (H-6), and why the
budget's tightest requirement is on the two things that set heading: residual gyro bias after ZARU
(0.005–0.01 °/s) and the phone-to-vehicle mount yaw (≈ 1°).

---

## 3. Architecture

**One continuously-running error-state Invariant EKF on SE₂(3)**, with gyro bias, accelerometer
bias and the phone→vehicle rotation `R_sv` in the state. The IMU always propagates. GNSS is an
*optional* χ²-gated correction.

```
State (nominal):   R ∈ SO(3),  v ∈ ℝ³,  p ∈ ℝ³,  b_g ∈ ℝ³,  b_a ∈ ℝ³,  R_sv ∈ SO(3)
Error state (18):  [ δθ | δv | δp | δb_g | δb_a | ξ_sv ]
Error convention:  right-invariant, η = X̂X⁻¹  (D-028)
Correction:        subtracted — X̂⁺ = Exp(−δ[0:9]) X̂  (D-050)
```

### 3.1 The central argument

**There is no second system and no handoff.** Inside a tunnel nothing passes the χ² gate, so nothing
is applied; on exit, a good fix is an ordinary update and a multipath fix is rejected by the same
test that rejects nothing else. There is no code path to switch, so the problem statement's
"seamless transition within milliseconds" is satisfied **by construction** rather than by handling
— there is no latency to measure and no jump to hide.

A reader will assume we built the two-system design: dead-reckoning mode, GNSS mode, and a
blending rule at the boundary. We did not, and the absence is the claim. It is asserted rather than
described: `tests/test_filter.py::test_a_rejected_gnss_fix_changes_absolutely_nothing` checks that a
rejected fix moves neither the state nor the covariance by a single bit **[verified]**, and the same
property is written into the FFI contract (`core/ffi/idr_core.h`) so it survives the October port.

### 3.2 Why *invariant*, and the single most defensible point in the design

Under the right-invariant error, the body-frame velocity Jacobian is

```
H_vb = [ 0 | R̂ᵀ | 0 | 0 | 0 | 0 ]
```

— the attitude column is **exactly zero**. A body-frame velocity constraint carries no
instantaneous heading information, and the invariant filter says so. A naive EKF has a non-zero
entry there, acquires spurious yaw observability, and then trusts a heading it has no right to
trust — producing smooth, plausible, wrong trajectories that no position plot reveals.

The derivation is in [SE23_PROPAGATION.md](SE23_PROPAGATION.md) and it was checked numerically in CI
**before the filter that uses it existed** (D-033). Doing it in that order produced three
corrections that would otherwise have shipped silently: midpoint evaluation of `A_RI` (D-029, ~1800×
lower linearisation residual), Van Loan `Q_d` rather than the `Φ G Q_c Gᵀ Φᵀ Δt` shortcut (D-031, a
measured 4.2% error at Δt = 0.1 s), and a small-angle cutoff at 1e-3 rather than 1e-6 (D-032, found
by writing the test rather than by reading the formula).

### 3.3 Process noise is measured, not guessed

`Q_c` is seeded from IO-VNBD's **own** stationary segments — the same three phones that produced
every sequence we are graded on — and not from a team handset (D-038, D-045). §11.1 has the
numbers and their limits.

---

## 4. Kinematic constraints

Three pseudo-measurements, each with an explicit **off** condition. An ungated constraint is worse
than no constraint: it injects a confident wrong measurement the filter believes.

| Constraint | Asserts | Observes | Gated off when |
|---|---|---|---|
| **NHC** | lateral and vertical vehicle-frame velocity ≈ 0 | velocity; **mount angle, with gain equal to forward speed** | speed < 1 m/s, \|yaw rate\| > 0.6 rad/s, \|lateral accel\| > 4 m/s² (D-026) |
| **ZUPT** | body-frame velocity = 0 at a detected stop | velocity, accelerometer bias | not stationary |
| **ZARU** | angular rate = 0 at a detected stop | **gyro bias, directly** | not stationary, or the innovation fails χ² (D-057) |

ZUPT and ZARU are offered **together** at every detected stop (D-004). A stop where only one is
offered is a bug, not a tuning choice.

**The non-obvious point, and it is worth making explicitly:** NHC gives no instantaneous heading
information (§3.2). Yaw reaches it only through a second-order gravity coupling, slowly, and only
while accelerating. **ZARU is a direct observation of `b_g`** — no coupling, no integration, no
waiting — which is why the cheapest thing in this system matters most for the term that dominates
the budget.

### 4.1 Gating lives with the caller, and that is a design decision

`is_stationary` needs accelerometer variance over a window; `nhc_is_valid` needs yaw rate and
lateral acceleration. **None of those is a property of the state** — they are properties of the IMU
stream, which the filter does not hold. Moving the detectors inside the filter would mean it
keeping a raw-sample buffer purely to re-derive what the caller already has, and would hide the
one rule the budget depends on (D-052).

### 4.2 The consistency failure this surfaced, and what it cost to find

A stop detector that averages over a 0.5 s window lags the stop→moving transition. At the step
where the vehicle pulls away, the window still holds four stopped samples and one moving one and
the detector still says "stopped" — so ZARU fires against a real yaw rate and injects it into the
bias estimate as though it were bias.

That single sample per stop was the whole of the filter's over-confidence. Full-state NEES over the
60 s reference scenario, 100 Monte-Carlo runs, against a 95% band of [16.84, 19.19] **[verified,
`tests/test_se23_derivation.py` test 11]**:

| | NEES | Gyro-bias block (3.0 expected) |
|---|---|---|
| Before | 29.90 — **over-confident** | 13.14 |
| ZARU's `R` sourced from the Allan run instead of typed | 23.71 | 9.32 |
| Plus a genuinely independent second gyro read | — | 8.22 |
| **Plus the χ² gate on ZARU** | **14.14 — under-confident** | **3.05** |

The row that matters is the third: the correlation between the gyro sample used as process noise
and the same sample used as ZARU's measurement — the explanation we had written down (D-053) — is
worth 1.1 of the 10.1. The false firing is worth the rest. **We recorded the wrong diagnosis for a
day, and the only reason it did not survive is that the number was measured rather than reasoned
about** (D-057).

Two alternatives were measured and rejected. Testing the *maximum* of the gyro window instead of its
mean also fixes it — and breaks a belief the repo holds on evidence, because a real idling cabin
carries 20–30× the mechanical energy of a bench-quiet segment (D-045) and would stop being
ZUPT-able. Gating ZUPT as well makes ZUPT *worse* (18.93 → 44.74): its σ of 0.02 m/s collapses the
velocity block until legitimate innovations fall outside the gate and lock out permanently. The
asymmetry is physical — at the first moving sample the vehicle's *speed* is necessarily near zero,
so a false ZUPT is nearly harmless, while its *yaw rate* is whatever a driver turning the wheel
while pulling away chooses.

The filter is now **under-confident**, which is the safe direction, and the residual is entirely
NHC's `R = 0.5 m/s` — model slack for suspension travel, road camber and tyre slip that a
noise-free simulation does not contain. It is tunable into the band at 0.05 m/s and is deliberately
**not tuned**: that would be fitting a measurement-noise covariance to a scenario that omits the
physical effect the covariance exists to model (D-058).

---

## 5. Learned forward speed

A TCN over a 1–2 s window of `S-` inertial channels, in the body frame, predicting **forward speed
and its log-variance**, trained with a Gaussian NLL and fused as a pseudo-measurement whose `R` is
the head's own predicted variance.

**Why the variance head matters as much as the mean:** a confidently wrong covariance corrupts a
Kalman filter worse than a noisy mean does, and it is invisible to ordinary accuracy metrics. A head
with excellent RMSE and 60% coverage will damage the filter. Gate 2's criterion is therefore
**calibration, not accuracy** — at least 95% of speed errors inside ±2σ — and coverage is reported
before RMSE.

**Status: architecture and loss written and tested (`models/speed_head.py`); not trained.**
Blocked by H-4, which forbids adding any learned component before Gate 1 closes, and by §12's data
blocker. `InEKF.update_speed` raises `NotImplementedError` rather than returning a stub — a stub
returning `None` would let the harness produce plausible all-zero trajectories and report them as
results.

Pedestrian weights are not reused. RoNIN, IONet, RIDI, TLIO, IDOL and CTIN encode a 0.5–2 m/s gait
prior and under-predict badly at 16.7 m/s (D-017). Their *architectures* transfer; their weights do
not.

---

## 6. Learned adaptive constraint covariance

Brossard's AI-IMU mechanism: a **~6,210-parameter** CNN that outputs `R_NHC` per step — how tightly
to enforce "no sideways motion" — relaxing it in hard cornering and tightening it on straights. The
highest-leverage learned component in the system is also by far the smallest, which is a point worth
making rather than hiding.

**It adapts `R`, the measurement noise. It does not touch `Q`.** D-040 is explicit about this because
the mis-citation is easy and expensive: implementing an adaptive process noise under an AI-IMU
citation would ship an unvalidated method carried by a reference that does not support it, and that
is exactly what an adversarial question at judging finds.

**Status: not built.** First on the cut list (§5 of the plan), and blocked behind Gate 2. The
interface it plugs into exists and is tested: `update_nhc(r_nhc=...)` already accepts a per-step
2×2 covariance.

---

## 7. Mounting-angle estimation

The budget gives mount misalignment 20 m of the 100 m, which at 16.7 m/s over 60 s means the
phone→vehicle yaw must be known to **δ = 20 / (16.7 × 60) ≈ 1.15°** **[analysis]**. A phone knocked
by 5° costs 87 m over the same outage, and it is **silent** — the phone is still level, the IMU
still reads plausibly, the trajectory still looks like a drive.

Three parts, all built:

1. **A PCA initialiser.** A car's specific force is dominated by braking and acceleration along its
   own forward axis, so the first principal component of the horizontal specific force *is* the
   vehicle's forward axis in the phone frame — which is exactly what the mount yaw is, with no
   navigation-frame quantity involved. It also reports its own **spread**, `√(λ₁λ₂/(n_eff(λ₁−λ₂)²))`,
   which `P₀`'s mount block then carries instead of a stated fallback (D-073). `n_eff` is the AR(1)
   effective sample count from the measured lag-1 autocorrelation, not the sample count: 10 Hz
   accelerometer samples are not independent draws.
   **PCA returns an axis, not a direction**, so the 180° ambiguity is resolved against a
   forward-acceleration reference or **reported unresolved** (D-074). A 180° mount error is not a
   large version of a small one — it is a vehicle driving backwards, and NHC's lateral and vertical
   rows are satisfied just as well by a reversed forward axis, so it will never converge out.
2. **In-filter estimation.** `R_sv` is filter state, not a one-shot alignment (D-006), observable
   through NHC **with gain equal to forward speed** — well on a motorway, barely at all in a car
   park, which states the car-park limitation as a property of the mathematics rather than as an
   apology. The perturbation convention is vehicle-frame left-multiplied (D-030) specifically so
   that `ξ_sv,z` reads **directly** as mount-yaw error in degrees and compares against the 1.15°
   requirement without a change of basis.
3. **Knock re-inflation.** A detected bump *widens* the mount block; it never corrects the rotation,
   because the gyro energy that detected a bump does not say how far the phone turned (D-076).
   Variance is added rather than reset — a reset would shrink the covariance of a filter that had
   already lost track. Measured over 60 s of cruising at 15 m/s after a 5° knock **[verified,
   `tests/test_mount.py`]**: **0.43°** of residual mount-yaw error with re-inflation against
   **8.56°** without. Not re-inflating is worse than the knock itself, because a stale rotation
   behind a confident covariance drags the rest of the state with it.

**Open, and stated here rather than found later (D-075):** the bump *detector* cannot see the knock
this section is about. A knock of angle θ delivered inside one sample presents at most `θ/Δt` of
measured rate, so at 10 Hz the configured 3.0 rad/s threshold corresponds to a **17.2°** knock,
while a 5° one presents 0.87 rad/s. The threshold has no source in this repo and was **not** lowered
to make a synthetic test pass; it needs a recording of a real phone being knocked in a cradle. Until
then the 1.15° requirement rests on the initialiser plus unaided NHC.

---

## 8. Map matching — designed, sized, not built

An online HMM over an **offline** OSM CSR graph, Viterbi over a sliding window, committing segments
older than ~5–10 s.

The adaptation worth emphasising: **the emission σ comes from the filter's own covariance**, not
from an assumed GPS noise model. Every candidate library takes GPS accuracy as one scalar —
Valhalla Meili precomputes `1/(2σ_z²)` with `σ_z` defaulting to 4.07 m, and FMM, GraphHopper and
Barefoot are the same shape. That is the right model for a raw GPS trace and the wrong one for a
filtered pose whose uncertainty we compute, so we build the matcher rather than patch someone
else's probability model (D-036). Candidate search is Mahalanobis against `P_pos`, not a scalar
radius: the 99% radius implied by our budget runs from 18 m at a 10 s outage to 359 m at 180 s, so a
single radius is wrong at both ends, and the ellipse is anisotropic and rotates with heading
(D-035).

Sized to the megabyte: ~21 MiB for the Delhi bbox, ~32 MiB for core NCR, ~16 KiB resident over a
180 s transit. The NCR extract merges Geofabrik's northern **and** central zones, because the seam
is the Yamuna and a northern-only graph ends mid-bridge at the DND Flyway (D-034). `highway=service`
is in the drivable graph at a measured +21% cost, with highway class as a 4-bit emission prior
(D-037).

**Map matching is deliberately not in the error budget.** It buys margin back; it is not a term we
plan to spend — because it does not exist in a car park. If the budget only closes with map
matching, it does not close.

---

## 9. Car-park mode — designed, not built

No road graph exists underground, so the outer correction layer is unavailable exactly where the
inner one is weakest: dwell times are long, speeds are low (so NHC's mount observability is near
zero, §7), and turns are frequent. The fallback is tight NHC plus barometer floor detection (one
level ≈ 2.5–3 m ≈ 0.3–0.36 hPa) plus ramp detection from sustained pitch.

**Drift may exceed 10% on a long stay.** §13.

---

## 10. Deployment

**One library, two frontends.** [`core/ffi/idr_core.h`](../core/ffi/idr_core.h) is the surface both
the Android build (via JNI) and the 200 Hz FOG edge engine bind to. It is a C header rather than a
C++ or Rust one because JNI binds C directly and Rust reaches it through `extern "C"` — a native
interface in either would force the other through a shim, and a shim is where units and ownership
rules get quietly re-interpreted (D-077). Units, frames, buffer ownership and threading are stated
on every entry point, and a CI test keeps the header an accurate description of the reference
filter rather than a document that drifts.

**It is a definition, not an implementation**, and that is a decision rather than an omission
(D-022, D-043). The screening filter is the Python reference; the port is October's.

Measured throughput of that reference **[verified]**: 2,905 `propagate`/s and **2,327 realistic
10 Hz steps/s — 233× real time**. The hotspot is the 36×36 Van Loan matrix exponential at 0.172 ms,
**50.1% of `propagate`** and the largest single `tottime` in a profile of 600 steps. Two honest
consequences: nothing in the harness needs optimising (the full sweep is about five minutes), and at
200 Hz the FOG build's 5 ms step budget would absorb even the *Python* at 8.6% — **so the port is
needed for the deployment target, not for throughput.** The `expm` stays: D-031 chose it over the
cheap closed form on a measured 4.2% error, and the port must validate any replacement against it
rather than substituting one.

The learned components are swappable modules, not baked in — TFLite/ExecuTorch on phone,
ONNX/TensorRT on edge, FP16 export only. INT8 needs an explicit covariance-head degradation test
(D-012) and is out of scope.

---

## 11. Evaluation protocol

**Read this before any number.** A reader who wonders whether we used wheel speed will not believe
anything after the point at which they started wondering.

### 11.1 Inputs, and the channel restriction

**`S-` smartphone channels only.** PS 26168 disallows wheel odometry, and IO-VNBD ships the
wheel-speed columns in the same download, in adjacent columns, on paired sequence names — so
accidental leakage is a one-typo mistake that would invalidate every number in the submission.

The guard is an **allowlist**, not a denylist: a denylist protects you from the columns you thought
of. It has **its own CI job**, separate from the test suite so it reads as a distinct gate, and that
job additionally asserts the guard *rejects* a `V-` column — a guard never observed to fire is not
known to work.

One exception, and it is not an input: [EVALUATION.md](EVALUATION.md) §1.2 permits the paired `V-`
GPS as **ground truth** on paired sequences. It is read through `eval/loaders/truth.py`, whose
allowlist is latitude, longitude and time of day and nothing else — no velocity, no heading — whose
columns are selected from the header before the body is read, and whose return type is deliberately
not a `Sequence`, so it has no `features()` and cannot reach a model.

Measured sensor characterisation, from IO-VNBD's own stationary segments **[measured,
`eval/figures/allan_*.csv`, commit `4e0c9ac`, seed 26168]**:

| Parameter | Measured | Worst axis |
|---|---|---|
| Angular random walk | **0.75 °/√hr** (`gyro_arw = 2.18e-4` rad/s/√Hz) | `gyro_roll`, S-T2 |
| Velocity random walk | **0.24 m/s/√hr** | `accel_x`, S-T2 |
| Gyro bias instability | **22 °/hr** at τ ≈ 32 s | `gyro_roll`, S-T2 |
| Accel bias instability | **0.25 mg** at τ ≈ 48 s | `accel_x`, S-T2 |

D-045 read 1.41 °/√hr, 0.45 m/s/√hr, 42 °/hr and 0.34 mg from the same two stops; every figure
was about 2× pessimistic because the segment finder kept the second of settle and pull-away at
each end of a stop, and ARW is read at τ = 0.2–2 s (D-120).

Four limits, stated because they change how far these can be pushed. There is **no >20 min
stationary segment** in the `S-` stream — [DATASETS.md](DATASETS.md) claimed one and the claim did
not survive being checked; the longest is 484 s, so τ_max is ~48 s and bias instability is an
**upper bound** with the curve still descending. The two bias driving noises are **derived** from a
Gauss–Markov model, not measured, and are labelled as derived everywhere. **The white-band gate
decides which axes count**: three of six gyro fits are flatter than −½ over τ = 0.2–2 s and are
refused — at this floor the 10 Hz gyro's short-τ behaviour on those axes is not a random walk —
and one accelerometer fit is, because a parked car genuinely accelerates at low frequency. And
these are **bench-quiet** numbers — a car idling with an occupant
returns an apparent ARW ~6× larger, which measures the cabin, not the gyroscope.

### 11.2 The protocol

Synthetic GNSS outages of **10 / 30 / 60 / 120 / 180 s**, non-overlapping (asserted, not assumed),
tiled deterministically over held-out sequences after a 30 s warm-up, at a 1 s prediction cadence.
During an outage the filter receives **no GNSS update at all** — not a degraded one. Feeding a
noisier fix is a different and easier experiment.

The train/test split is frozen in code with disjointness asserted. Every artefact carries the commit
SHA and RNG seed **inside the file**, never in a filename — a filename is renamed, copied and pasted
into a slide, and the provenance is lost at the first of those.

### 11.3 Metrics

**CTE** and **CRSE** are Onyekpe's *Cumulative True Error* and *Cumulative Root Square Error*. They
are **not** cross-track error and **not** ATE; the task brief mislabels them and so does most
secondary writing about this dataset.

CRSE is `Σ|eᵢ|` — the sum of absolute per-second errors. This was settled against the papers rather
than reasoned about (D-054): R-WhONet **Eq. (16)** takes the root **per term, inside the sum**, with
Eq. (17) giving `CTE = Σ eᵢ` as its signed counterpart. Both papers' *prose* says "cumulative root
mean squared", which the equation contradicts; the equation wins, and it is confirmed
arithmetically against the papers' own published tables — only this reading leaves the per-epoch
error rate flat across four outage lengths. An earlier decision had chosen a different convention on
a consistency argument that, checked, never discriminated between the readings.

**Drift %** — final position error over ground-truth path length — is what PS 26168 grades. No paper
in this line reports it, so it is ours to define unambiguously. It is reported as **median and 95th
percentile**, never a mean: the tail is what a judge asks about.

**Yaw error is reported alongside position error on every figure, without exception** (H-6). Truth
is a lat/lon track with no heading channel, so both sides of that comparison are course made good
over each epoch, computed by one shared function (D-063). That is a real caveat and it belongs in
the caption: the filter's *attitude* is not what its yaw error is measured against.

### 11.4 Two defects in the protocol as drafted, found by checking

**The held-out set was unloadable.** The `V-` prefix denotes the *stream*, not the sequence, so the
split named files the leakage guard correctly rejected — and the failure read as a wheel-speed bug.
Worse, **eleven of the named stems ship on the `V-` stream only**, with no `S-` counterpart in
either folder, so PS 26168 puts them out of reach entirely. Long-outage dropped from 9 sequences to
3 and the mandatory plot set from 4 to 2 (D-044). **The long-outage result rests on three
sequences and must be reported as such.**

**The `S-` GPS is not 1 Hz.** The protocol was drafted as "1 Hz GNSS" from a paper written against
the vehicle stream. Measured across all 72 `S-` stems, the median inter-fix interval is **9.0 s**,
with a 109 s worst gap on a held-out one, and only three stems update at 1 Hz. CTE and CRSE are sums
over 1 s epochs and drift-% needs a position at the outage boundary, so neither is computable from
that. Ground truth therefore comes from the paired `V-` VBOX track, which is a genuine 10 Hz
instrument; the `S-` fixes keep their other role as the gated filter update, which is the
measurement a phone actually has.

---

## 12. Results

**There are none, and none is substituted for.**

`eval/run.py` is wired end to end: it loads the held-out sequences, runs the filter across each
outage window with GNSS masked, scores the physics-only filter against the naive-strapdown and
GNSS-available baselines through one metrics path, and writes stamped `summary.json`,
`windows.csv` and per-sequence trajectory records. Running it in the environment this document was
written in exits with **"dataset not found"**: every IO-VNBD CSV in the upstream repository is a
Git-LFS object and the LFS lane is credential-gated here, so a clone yields 134-byte pointer stubs
(D-059).

What **is** established is that the wiring is correct — which is the failure class that produces a
plausible number rather than an error. `tests/test_harness_wiring.py` drives the whole path on a
synthetic drive whose answers are known independently: loader arrays and the D-047 axis mapping,
**both clocks** (the fixture puts the `S-` and `V-` clocks 09:30:00 apart on purpose), the GNSS
mask, epoch slicing, the truth lookup, all three methods, the metrics composition and the stamped
artefacts — including reaching §2's 176.5 m accelerometer-bias figure through the full pipeline
rather than through hand-built arrays.

That clock pairing was itself a defect this exercise found: the scorer derived the truth time from
the sample index, which is right for a synthetic track whose origin is zero and wrong for every real
one (D-066). It is item one in Gate 1's fixed diagnosis order — **timestamps** — and it would have
graded each window against a stretch of road hours away.

**Gate 1 is therefore open.** Under H-4 no learned component is added until physics-only lands
within 3–5× of the GNSS-available baseline over 60 s outages, so the speed head (§5) and the
adaptive `R_NHC` (§6) have not been started. Closing it needs a machine that can fetch the dataset;
it does not need any further code.

When it runs, this section will carry: drift % as median and p95 at every outage length; the
four-trajectory figures for `S3a` and `Vta11` with the growing uncertainty ellipse; yaw error
alongside position error on every one of them; re-acquisition behaviour measured per
[EVALUATION.md](EVALUATION.md) §6 rather than assumed; and the sequence count each number rests on.
**Under-reporting that count is a far worse failure than a small count.**

One number the harness will produce is worth flagging in advance because it reads oddly: with GNSS
*available* throughout, a phone-only system is still several percent out over 60 s, purely because
the receiver speaks every 9 s. That is the honest Gate 1 denominator, it is a property of the update
rate rather than of the receiver's accuracy, and it is phase-sensitive with respect to where the
window falls (D-062).

---

## 13. Honest limits — never cut

**Multi-level underground car parks are the least certain claim in this submission.** No road graph
exists, so map matching is unavailable; dwell times are long, speeds are low — and NHC's mount
observability has gain equal to forward speed, so the mount angle is barely estimated at exactly the
moment it is being knocked about — and turns are frequent. **Drift may exceed 10% on a long stay.**

**Tunnels and underpasses: the 10% target is achievable**, comfortably so with map matching. Without
it, expect to miss 10% occasionally on curved tunnels and roundabouts, where heading error and road
curvature compound.

**The phone stream is 10 Hz.** Everything demonstrated on IO-VNBD is at 10 Hz. The 200 Hz FOG
configuration is an architecture claim backed by a measured throughput headroom (§10), **not a
demonstrated pipeline**, and no figure or caption implies otherwise.

**What we designed and did not build for screening**, each deferred rather than dropped:

| | State |
|---|---|
| Online HMM map matcher | Designed, sized to the megabyte (§8). Not implemented. |
| Android foreground logger, demo app, JNI | Not started. The FFI surface it binds to is defined (§10). |
| Car-park mode — barometer floor, ramp detection | Designed (§9). Not implemented. |
| comma2k19 pretraining | Not started. |
| Delhi/NCR collection and domain-shift ablation | Not started. |
| C++/Rust port of the core | Deferred to October by decision; interface defined. |
| Speed + variance head, adaptive `R_NHC` | Architecture written and tested; **not trained** — blocked by Gate 1 (H-4). |
| The Onyekpe baseline reproduction | Nine of its eighteen hyperparameters are ours, not the papers' (§14). Not trained. |

**One open item that is a gap rather than a deferral**, stated here because a limitation we state
costs a fraction of what one a judge finds costs:

1. **The mount-disturbance detector cannot see a 5° knock at 10 Hz** (§7, D-075). The reference InEKF
   threshold (`mount_disturbance_gyro_thresh = 3.0` rad/s) corresponds to a 17.2° knock under 10 Hz sampling.
   In the on-device operator UI (`CourseTracker`), a knock that *tilts* the handset is seen by the
   rotation-matrix gravity-vector tilt rate (`acos(dot)/dt > 0.44` rad/s, `TILT_DISTURBANCE_RAD_PER_SEC`):
   a 5° tilt inside one 100 ms sample is 0.87 rad/s. A knock that only yaws the phone about the vertical
   does not move that vector and is caught only by the 3.5 rad/s raw-rate rule, so the blind spot is
   narrowed on the device, not closed. The offline filter detector remains un-tuned around to avoid
   fitting without cradle hardware recordings.

**Closed items previously listed as open:**
- **The IO-VNBD accelerometer sign convention (R-8 / D-059) is CLOSED by D-085**: measured on real
  stationary segments `S-T2[31422:36490]` (norm 9.7561 m/s²) and `S-T7[47809:52285]` (norm 9.8781 m/s²).
  Confirmed specific force with gravity included, `GRAVITY` channel points UP, and `R_sv @ accel` has
  `z ≈ -9.8` matching `-GRAVITY_NED` in `core/reference/inekf.py:191`. SE₂(3) test 2 is confirmed.
- **Gate 0 being open is CLOSED**: the split was re-picked against measured truth pairing (D-092) and
  [EVALUATION.md](EVALUATION.md) was frozen on 03 Sep 2026 (D-103).

**Where our numbers are worse than published ones, the reason is the sensor grade and the permitted
inputs, and we say so rather than letting the comparison stand.** §14.

---

## 14. Citation hygiene

Checked line by line. Each of these is a number someone will otherwise assume we are claiming.

| Claim | Whose, and on what | Our position |
|---|---|---|
| **AI-IMU, 1.10%** | KITTI, an **automotive-grade** IMU | Never quoted as ours. Their *mechanism* — a small CNN adapting `R_NHC` — is what we take, and we say so (§6). |
| **WhONet, ~0.15%** | Requires **wheel speed**, which PS 26168 disallows | A ceiling, never a target and never ours. |
| **Onyekpe INS models** (IDNN / vRNN / LSTM / GRU) | `S-` channels on IO-VNBD | **This is our honest reference point.** §14.1. |
| Pedestrian ATE (RoNIN, TLIO, RIDI, IONet, IDOL, CTIN) | Handheld/pocket, 0.5–2 m/s | Ranks architectures. Does **not** predict car performance and is not comparable to drift %. |
| 2025–26 preprints (FTIN, IONext, GNIO, MosaicIMU, SNN+InEKF) | Little independent replication | Treated as provisional if cited at all. |
| "QGRU from the IO-VNBD paper" | **Does not exist** | IO-VNBD (Data in Brief 35:106885) is a *dataset* paper; quaternion GRUs are not its contribution. Do not cite it that way. |

**A defect in our source table, flagged by us rather than by a judge.** WhONet's outage-sequence
counts are internally inconsistent — 809/399/197/129 in the introduction against 688/342/168/111 in
the tables — and it reports an *identical* CTE for both methods at 120 s. We cite the tables and
note the discrepancy. Finding it first is a different conversation from having it found.

### 14.1 The reproduction is half ours

The Onyekpe baseline's hyperparameters split nine stated, nine omitted. The papers state the window
(1 s, 10 samples), the architecture (vanilla RNN, one hidden layer, 72 units), dropout 0.05, batch
128, learning rate 7e-4, Adamax, MAE, 0–1 feature scaling and the framework. They omit epochs, early
stopping, the train/validation split, weight initialisation, gradient clipping, the LR schedule,
shuffling and window stride, the magnitude of the GNSS input noise they say is injected, and **the
set the scaler is fitted on**. `python -m models.train_baseline_rnn --audit` prints the table.

The papers also disagree with each other: **the INS paper does not surface its loss or its
optimiser**, and both rows come from WhONet. That is recorded per row rather than smoothed into "the
papers".

The scaler fitting set is called out separately because it is the one silence that can *invalidate*
the result rather than shift it, and it is invisible to every guard we have: fitting on train+test
leaks the held-out dynamic range into training, and **no disallowed column is involved**, so the
allowlist and the CI leakage job both stay green (D-071).

**A reproduction that lands 20% off with a stated reason is a result. One that lands exactly on the
published number with no explanation is usually a leak.** We will report the gap rather than close
it by search.

---

## 15. References

- Onyekpe, Palade, Kanarachos et al. — *Learning to Localise Automated Vehicles in Challenging
  Environments* (INS baseline; IDNN / vRNN / LSTM / GRU).
- Onyekpe et al. — *WhONet: Wheel Odometry Neural Network*, arXiv:2104.02581 §3.2 (CTE/CRSE
  definitions, Eq. 16–17).
- Onyekpe et al. — *R-WhONet*, arXiv:2209.05877, Eq. (16)–(17) (the CRSE convention this repo pins
  against, D-054).
- Onyekpe et al. — *IO-VNBD: Inertial and Odometry Vehicle Navigation Benchmark Dataset*, Data in
  Brief 35:106885. **A dataset paper.**
- Brossard, Barrau, Bonnabel — *AI-IMU Dead-Reckoning* (adaptive measurement covariance for NHC).
- Barrau & Bonnabel — *The Invariant Extended Kalman Filter as a Stable Observer*.
- Hartley, Ghaffari, Eustice, Grizzle — *Contact-aided Invariant EKF for Legged Robot State
  Estimation* (SE₂(3) formulation).
- Van Loan — *Computing Integrals Involving the Matrix Exponential* (discrete `Q_d`).
- IEEE Std 952 — Allan-variance procedure and the flicker-floor relation `σ_min = 0.664 B`.
- Vincenty — *Direct and Inverse Solutions of Geodesics on the Ellipsoid*.
- Geofabrik OSM extracts — northern-zone and central-zone India (D-034).
