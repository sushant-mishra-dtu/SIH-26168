# Evaluation Protocol

**Status:** DRAFT → to be FROZEN at Gate 0 (**Fri 28 Aug 2026**).
**Owner:** seat D. **Ratified by:** all six seats.
**Submission:** Tue 8 Sep 2026 (see DECISION_LOG D-021 — the schedule compressed on 26 Aug).

Once frozen, this document is the contract. Every number, table and plot in the submission is
produced by the harness described here. Changing anything below after freeze requires an entry in
[DECISION_LOG.md](DECISION_LOG.md) naming what changed, why, and which results were invalidated.

The point of freezing before any model trains is simple: a protocol that can move is a protocol that
will be moved, one small justified step at a time, until the numbers flatter us and mean nothing.

---

## 1. Input channels

### 1.1 Allowlist — IO-VNBD `S-` (smartphone) stream only

10 Hz, GPS at 1 Hz. Permitted columns:

| Group | Columns | Unit |
|---|---|---|
| Accelerometer | accel X / Y / Z | m/s² |
| Gravity | gravity X / Y / Z | m/s² |
| Gyroscope | gyro yaw / pitch / roll | rad/s |
| Magnetometer | magnetic X / Y / Z | µT |
| Orientation | orientation yaw / pitch / roll | deg |
| Time | time-since-start, date | ms |
| GNSS *(reference & gated update only)* | lat, lon, altitude, speed, accuracy, orientation, sats-in-range | deg / m / km·h⁻¹ / m |

### 1.2 Denylist — the `V-` (ECU/CAN) stream

**Wheel speed FL/FR/RL/RR is disallowed by PS 26168.** So is anything derived from it. The whole
`V-` stream is out of the feature path. `V-` GPS may be used **only** as ground truth on paired
sequences, and only where explicitly labelled as such in the plot caption.

### 1.3 Enforcement

- The dataloader carries an explicit column allowlist. Anything not on it raises.
- A CI test asserts that no tensor reaching a model or filter input was built from a column whose
  name matches `wheel|steer|rpm|engine|brake|clutch|gear|pedal|handbrake` or begins with `V-`.
- **The leakage audit runs twice:** once in Sprint 1, once again in the week before submission.
  A test that only ever ran when it was written is not a test.

---

## 2. Frames and ground truth

| Item | Convention |
|---|---|
| Navigation frame | **NED** (North-East-Down) |
| Tracking | 2-D horizontal, **yaw-only** rotation R^n_b (pitch/roll zeroed for the position metric) |
| Body frame | Vehicle frame. Phone→vehicle rotation is **R_sv**. |
| Ground-truth displacement | **Vincenty's inverse geodesic formula** between GNSS fixes |
| GNSS reference accuracy | ≈ ±3 m (VBOX) |
| Sample rate | 10 Hz IMU, 1 Hz GNSS |

Never assume a nominal Δt. Use the recorded timestamps, and interpolate GNSS onto IMU epochs
rather than the reverse.

---

## 3. Outage injection

- Outage lengths: **10 / 30 / 60 / 120 / 180 s**.
- Sequences are **non-overlapping**, drawn from **held-out scenarios only**.
- Prediction cadence during an outage: **1 s**.
- 10 s outages are used for the challenging-scenario set; 30–180 s for the long-outage set.
- During an outage the filter receives **no GNSS update at all** — not a degraded one. The χ² gate is
  exercised separately on the re-acquisition transient (§6).

### Held-out scenario sets

| Set | Sequences |
|---|---|
| **Long outage** (30/60/120/180 s) | V-St6, V-St7, V-S3a, Vtb3, Vfb01c, Vfb02a, Vta1a, Vfb02b, Vfb02g |
| **Roundabout** (10 s) | Vta11, Vfb02d |
| **Hard brake** (10 s) | Vw16b, Vw17, Vta9 |
| **Accel change** (10 s) | Vfb02e, Vta12 |
| **Sharp corner / SLR** (10 s) | Vw6, Vw7, Vw8 |
| **Wet road** (10 s) | Vtb8, Vtb11, Vtb13 |
| **Motorway (easy control)** (10 s) | Vw12 |

Training sets (≈1,590 min / 1,165 km): V-S1, V-S2, V-S3c, V-S4, V-St1, V-M, V-Y2, plus Vta/Vtb/Vw/Vfa/Vfb
subsets not listed above. **No sequence appears in both.** The split is fixed in code, not in a notebook.

**Mandatory position plots for the submission:** V-St6, V-St7, V-S3a (long outage) and at least one
roundabout scenario.

> ⚠️ **This table is the protocol as drafted from the paper, and it is not yet loadable.** The paper
> is written against the `V-` vehicle stream; we consume `S-` only. Eleven of the stems above —
> `St1`, `St6`, `St7`, `Y2`, `Vtb13`, `Vfb01c`, `Vfb02a`, `Vfb02b`, `Vfb02d`, `Vfb02e`, `Vfb02g` —
> have **no `S-` smartphone file** in either IO-VNBD folder. `eval/splits.py` is the authority and
> currently holds the loadable subset: long outage `S3a, Vtb3, Vta1a`; mandatory plots `S3a, Vta11`;
> train `S1, S2, S3c, S4, M`. **Seat D re-picks replacements and rewrites this table before the
> Gate 0 freeze** — see [DECISION_LOG.md](DECISION_LOG.md) D-044.

---

## 4. Metrics

Report all four. Never report one alone.

### 4.1 CTE — Cumulative True Error

The **signed** sum of per-second position errors over an outage. Signed, so systematic over- or
under-prediction shows up instead of cancelling into an RMS.

### 4.2 CRSE — Cumulative Root Square Error

The name admits two readings, and they differ by √n:

| Convention | Formula | Behaviour |
|---|---|---|
| **`SUM_SQUARES`** *(current default)* | √(Σ eᵢ²) | "Cumulative" — grows with outage length |
| `RMS` | √(mean eᵢ²) | Length-independent |

**Default is `SUM_SQUARES`, on a consistency argument.** Against WhONet's published 180 s physics
baseline (CTE 2.90 m, CRSE 13.67 m, ~180 one-second epochs): under `SUM_SQUARES` a typical
per-epoch error is 13.67/√180 ≈ 1.0 m, which sits sensibly beside a signed sum of 2.90 m after
cancellation. Under `RMS`, every epoch would average 13.67 m of error while the signed sum stayed
at 2.90 m — requiring implausible cancellation.

Implemented as `CrseConvention` in [`eval/metrics/core.py`](../eval/metrics/core.py), so switching
is a one-line change rather than a rewrite.

> **These are Onyekpe's definitions — Cumulative True Error and Cumulative Root Square Error.
> They are NOT cross-track error and NOT ATE.** The task brief mislabels them, and so does most
> secondary writing about this dataset. State the definition explicitly in the write-up.
>
> **Open item for Sprint 0 (blocks freeze):** the reasoning above is a consistency argument, not a
> verified reading. Seat D must pin the exact equations against the WhONet paper's own equation
> numbers and record them here verbatim before Gate 0. If they differ, the paper wins — flip the
> enum and re-run the sweep.

### 4.3 Drift as % of distance travelled — **this is what PS 26168 grades**

```
drift_% = ‖ p̂(T) − p(T) ‖₂ / L × 100
```

where `p̂(T)` is the estimated position at the end of the outage, `p(T)` the Vincenty ground truth,
and `L` the ground-truth path length travelled during the outage. Report **median and 95th
percentile** across sequences, not just the mean — the mean hides the tail, and the tail is what a
judge finds.

### 4.4 Yaw error — logged separately, always

`ψ̂(t) − ψ(t)`, wrapped to (−π, π], reported as RMS and max over each outage. This is the dominant
error term ([ERROR_BUDGET.md](ERROR_BUDGET.md)); a run that reports position error without yaw error
is not a complete result.

---

## 5. Baselines

| Baseline | What it is | Why it exists |
|---|---|---|
| **Raw strapdown INS** | Double-integrated accel, integrated gyro, no constraints | The floor. Shows the problem is real. |
| **Onyekpe "Learning to Localise" INS** | 1 s window, MAE, Adamax 7e-4, batch 128, dropout 0.05, ~72-unit RNN | **The honest phone-grade number to beat.** Reproduced in Sprint 1. |
| **Physics-only InEKF** | InEKF + NHC + ZUPT/ZARU, no learning, Q from Allan variance | Gate 1. Must land within 3–5× of the GNSS-available baseline over 60 s. |
| **GNSS-available** | Filter with GNSS updates applied throughout | The ceiling for this sensor set. |

**Reference-only, never quoted as ours:** AI-IMU 1.10% (KITTI, automotive-grade IMU) and
WhONet ~0.15% (wheel speed, disallowed here). Both appear in the write-up as context with the
sensor-grade caveat attached, or not at all.

---

## 6. Re-acquisition behaviour

Measured, not assumed:

- Position discontinuity at the first accepted GNSS fix after an outage (metres). Target: no visible jump.
- χ² gate behaviour on tunnel-exit multipath — how many fixes were rejected, and were they right to be.
- Covariance trace through the outage: must grow monotonically during, collapse on re-acquisition.

---

## 7. Reporting rules

1. **Every figure and table is stamped with the git commit SHA and RNG seed that produced it.**
   A result whose provenance is unknown is deleted, not debugged.
2. **One command regenerates every figure in the submission.** If it takes manual steps, it will
   drift from the numbers in the text.
3. Fixed seeds; report the seed. Where variance matters, report across ≥3 seeds.
4. Report **both** WhONet outage-sequence counts (809/399/197/129 from its intro,
   688/342/168/111 from its tables) and note the inconsistency ourselves. The paper also prints an
   identical 120 s CTE of 1.78 m for both methods, which is likely a typo. Cite the tables.
   Finding this before a judge does is worth more than the half-mark it costs.
5. Every plot caption names its data stream (`S-` or `V-`) explicitly. The phone stream is 10 Hz —
   we cannot demonstrate a 200 Hz pipeline on it and must not imply we did.

---

## 8. Gate criteria

| Gate | Date | Criterion |
|---|---|---|
| **0** | Fri 28 Aug | Harness reproduces to the digit across two machines. Metric equations pinned. Split fixed in code. |
| **1** | Tue 1 Sep | Physics-only InEKF within **3–5×** of the GNSS-available baseline over 60 s outages. **Hard stop** — no network before this clears. |
| **2** | Fri 4 Sep | Speed head calibrated: **≥95% of speed errors inside ±2σ** of the predicted variance. |
| **3** | Mon 7 Sep | Full sweep, all plots, write-up, deck, video. **Submit Tue 8 Sep by midday.** |

If Gate 1 fails, diagnose in this order: **timestamps → NHC gating conditions → process noise →
ZUPT thresholds.** Do not add model capacity to a broken spine.
