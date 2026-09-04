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

**Re-picked 2026-09-02 against measured truth pairing — [DECISION_LOG.md](DECISION_LOG.md) D-092,
executing the TODO D-044 opened.** `eval/splits.py` is the authority and this table follows it.
Every stem below was run through `align_to_sequence` and through the harness's own uniform-grid
check: `python -m eval.cadence --all-paired --data-root data`.

| Set | Sequences | 60 s windows |
|---|---|---|
| **Long outage** (30/60/120/180 s) | S3a, S3c, Vta1a, Vta1b, Vta16, Vw2, Vw4 | 459 |
| **Roundabout** (10 s) | Vta11 | — |
| **Hard brake** (10 s) | Vw16b | — |
| **Accel change** (10 s) | Vta12 | — |
| **Sharp corner / SLR** (10 s) | Vw6 | — |
| **Wet road** (10 s) | *(none — see below)* | — |
| **Motorway (easy control)** (10 s) | Vw12 | — |

**Training set — pinned to an explicit list of stems.** M, S1, S2, S4, Vw14a, Vw14b, Vw14c, Vta2,
Vta4, Vta10, Vta14, Vta15, Vta19, Vw3, Vw5, Vw9, Vw10, Vw11, Vw13. This replaces the previous
"plus Vta/Vtb/Vw/Vfa/Vfb subsets not listed above", which was an open-ended clause living only in
this document: `assert_split_disjoint` compares two tuples, so a held-out stem drawn from that
unnamed remainder would have overlapped training with no check able to see it. **No sequence
appears in both**, and no *parent recording* straddles the split either — `Vw14a/b/c` are kept
together in train, `Vta1a/Vta1b` and `S3a/S3c` together in test, and `Vw16a` is left unassigned
because its sibling `Vw16b` is held out. That second rule is `assert_no_family_straddles_the_split`,
and it caught a real leak the moment it was written. The split is fixed in code, not in a notebook.

**Mandatory position plots for the submission:** S3a and Vw4 (long outage).

> ⚠️ **What this set cannot report, stated here rather than discovered later.**
>
> - **Wet road is empty.** `Vtb8` and `Vtb11` are refused by truth pairing at 33.7 m and 35.1 m
>   median residual against a 10 m limit, and no other stem in the dataset is documented as wet.
>   The scenario cannot be reported at all. The group is kept in `eval/splits.py` as an empty
>   tuple rather than deleted, so the omission is visible in the code as well as here.
> - **The roundabout plot cannot be produced.** This document requires "at least one roundabout
>   scenario" plot; the only roundabout stem is `Vta11`, which is 51.0 s long and cannot host the
>   60 s window `eval.run.REPLAY_LENGTH_S` plots. Open — it needs a scenario-length replay window
>   or a longer recording, and both are protocol decisions.
> - **Nothing was promoted into a scenario group.** Scenario labels are claims about what the
>   vehicle was doing, and the only source is this table as drafted from the paper. The 53
>   previously unallocated stems are undocumented, so thinned groups stay thin; promotion happened
>   only into the long-outage set, where membership is a measurable property.
> - **Eleven stems have no `S-` file at all** — `St1`, `St6`, `St7`, `Y2`, `Vtb13`, `Vfb01c`,
>   `Vfb02a`, `Vfb02b`, `Vfb02d`, `Vfb02e`, `Vfb02g` — and remain out of reach under §1.2 (D-044).
> - **Refused by truth pairing:** `Vtb3` (8.5 m but at a −2.70 s lag against a 0.5 s limit),
>   `Vtb8`, `Vtb11`, `Vw7` and `Vw8` (zero fixes matched, ~−165 s, undiagnosed), `S3b`.
>   **Too short for any outage:** `Vw17` (32.9 s), `Vta9` (15.6 s).
> - **Driver diversity is thin.** 62 of the 72 paired stems are Driver E. `S3a`/`S3c` are the only
>   Driver A sequences in the held-out set, and they are there only because D-091 recovered them.

---

## 4. Metrics

Report all four. Never report one alone.

### 4.1 CTE — Cumulative True Error

The **signed** sum of per-second position errors over an outage. Signed, so systematic over- or
under-prediction shows up instead of cancelling into an RMS.

### 4.2 CRSE — Cumulative Root Square Error

**The sum of absolute per-second errors, `Σ|eᵢ|`.** Settled against the paper's own equations —
[DECISION_LOG.md](DECISION_LOG.md) D-054, superseding D-023.

R-WhONet (arXiv 2209.05877) **Eq. (16)**, verbatim:

```
CRSE = Σ_{t=1}^{N_t} √(e_pred²)
```

and **Eq. (17)**:

```
CTE = Σ_{t=1}^{N_t} e_pred
```

> "Where `N_t` is GNSS outage length, `e_pred` refers to the prediction error, and `t` represents
> the sampling period which we define as 1 second in this research."

The root is taken **per term, inside the sum**. CRSE is therefore the sum of absolute per-second
errors and not a root of any sum, and CTE is its signed counterpart — the two differ only by the
absolute value, which is exactly why they are reported as a pair. The original WhONet paper
(arXiv 2104.02581 §3.2) carries the same metrics at the same equation numbers.

Both papers' *prose* calls it "cumulative root mean squared", which the equation contradicts.
**The equation wins**, and the prose is why three documents in this repo described it as an RMS.

| Convention | Formula | Status |
|---|---|---|
| **`SUM_ABS`** *(default)* | Σ\|eᵢ\| | **Eq. (16). The paper's metric.** |
| `SUM_SQUARES` | √(Σ eᵢ²) | Retained; D-023's reading, kept so earlier working is reproducible |
| `RMS` | √(mean eᵢ²) | Retained; the reading the prose suggests |

**Confirmed arithmetically against WhONet's own tables** (§3 of [DATASETS.md](DATASETS.md), four
outage lengths × two methods). A CRSE that sums over `N_t` one-second epochs has a per-epoch error
rate of `CRSE / N_t`, which should be roughly flat across outage lengths. Only Eq. (16) makes it so:

| Divide published CRSE by | Physics spread | WhONet spread |
|---|---|---|
| `N_t` — the `SUM_ABS` reading | **1.4 %** | **2.3 %** |
| `√N_t` — the `SUM_SQUARES` reading | 2.4× | 2.4× |
| nothing — the `RMS` reading | 5.9× | 5.9× |

D-023 chose `SUM_SQUARES` from the 180 s row alone and labelled itself *"reasoned, not verified"*.
That argument never discriminated: `SUM_ABS` satisfies it too (13.67/180 ≈ 0.076 m per epoch beside
a signed sum of 2.90 m). It takes all four rows to separate the readings.

Implemented as `CrseConvention` in [`eval/metrics/core.py`](../eval/metrics/core.py). Every member
is branched on explicitly and an unknown one raises — there is no `else` fallthrough, because the
function previously ended in a bare `return √(mean(…))` and a new member added without a branch
would have silently computed RMS under the new name.

> **These are Onyekpe's definitions — Cumulative True Error and Cumulative Root Square Error.
> They are NOT cross-track error and NOT ATE.** The task brief mislabels them, and so does most
> secondary writing about this dataset. State the definition explicitly in the write-up.
>
> **R-4 is closed.** The equations above are quoted from the paper, not inferred, and the
> convention they fix is verified against the paper's published tables. Nothing was invalidated by
> the change: no CRSE had been computed on real data when it was made.

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
