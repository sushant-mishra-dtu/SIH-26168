# idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles

Smart India Hackathon 2026 · Problem Statement **26168** · AI-based intelligent dead reckoning.

> **Grade metric:** position drift under **10% of distance travelled**
> **Screening submission:** **Tue 8 Sep 2026** (past — see [docs/SUBMISSION_AUDIT.md](docs/SUBMISSION_AUDIT.md))
> **Status:** 14 Sep 2026. CI green, 728 Python tests plus JUnit on both Android roots.
> **The demo app is installable.** `releases/app-osm-debug.apk` is the `osm` flavour of the
> operator UI (`android-ui/`), built from `main`; download link and install steps in
> [releases/README.md](releases/README.md). The committed APK is **v0.1.0**; the source is at
> **v0.1.3** and the file has not been refreshed yet — what changed is
> [CHANGELOG.md](CHANGELOG.md). It carries the navigation screen, the autonomous
> tunnel state machine (D-126), turn guidance and the covariance ellipse (D-125). A `mapbox`
> flavour exists behind two tokens that are not checked in (D-121, D-122) and is not published.
> **Gate 1 is measured and does not close.** The sweep runs end to end on IO-VNBD (D-110); at 60 s
> the pooled ratio against the GNSS-available baseline is **11.8×** on 205 windows (D-115) against
> the required 3–5×, with the remaining gap split between the recordings (yaw-axis vibration
> aliased at 10 Hz) and the filter. D-115 names the next fix. Under H-4 no learned component goes
> in until it closes, so P-08/P-09/P-10 have not been started.
> **The hardware baseline is measured** on the team Samsung Galaxy A55 5G: 125 Hz achieved, 8.1 ms
> Δt jitter, and an Allan run on our own phone recorded next to IO-VNBD's, not in place of it
> (D-116, D-119, D-120).
> **Branching:** everything lands on `main` from here. The last seat branch, `a/mapbox-scaffold`,
> was merged in PR #20 and deleted on 14 Sep.
> **Plan of record:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) *(27 Aug — supersedes
> the sprint calendars in AGENTS.md and SPRINT_BOARD.md)*; the Android list is
> [android/HANDOVER.md](android/HANDOVER.md) §9.

---

## The thesis in one paragraph

One continuously-running error-state **Invariant EKF on SE₂(3)**. The IMU always propagates; GNSS is
an *optional* χ²-gated correction. There is no second system and no handoff, so the problem
statement's "seamless transition within milliseconds" is satisfied **by construction** rather than
by clever code. Three inputs keep the filter honest: a **learned forward-speed head** (never
double-integrated accel), **kinematic constraints** (NHC + ZUPT + ZARU), and **HMM map matching**
over an offline OSM graph whose emission σ is driven by the filter's own covariance.

**The dominant error term is yaw, not speed.** Lateral error grows as ≈ ½·b_g·v·t² — unbounded,
sideways, and it makes map matching snap confidently onto the wrong road.

---

## Architecture

```mermaid
flowchart LR
    subgraph sensors["Sensors"]
        direction TB
        IMU["IMU<br/>accel + gyro<br/>10 Hz phone / 200 Hz FOG"]
        BARO["Barometer"]
        GNSS["GNSS<br/>GPS + GLONASS<br/>Galileo + BeiDou"]
    end

    subgraph learned["Learned components"]
        direction TB
        SPEED["Speed + variance head<br/>TCN, 1-2 s window"]
        RNHC["Adaptive R_NHC<br/>AI-IMU CNN, ~6k params"]
    end

    subgraph constraints["Kinematic constraints"]
        direction TB
        NHC["NHC<br/>no sideways, no vertical"]
        ZUPT["ZUPT + ZARU<br/>at every detected stop"]
    end

    FILTER{{"Invariant EKF on SE₂ 3<br/>R, v, p, bias_g, bias_a, R_sv<br/>always propagating"}}
    GATE["χ² innovation gate"]
    MAP["HMM map matching<br/>offline OSM CSR graph<br/>emission σ from filter covariance"]
    OUT["10 Hz pose + uncertainty ellipse"]

    IMU --> FILTER
    IMU --> SPEED
    IMU --> RNHC
    IMU --> ZUPT
    SPEED -->|"pseudo-measurement<br/>with predicted R"| FILTER
    RNHC -->|"per-step R"| NHC
    NHC --> FILTER
    ZUPT --> FILTER
    GNSS --> GATE
    GATE -->|"accepted"| FILTER
    GATE -.->|"rejected: tunnel or multipath<br/>no update, no mode switch"| FILTER
    BARO -->|"floor detection, car parks only"| FILTER
    FILTER --> MAP
    MAP -->|"heading feedback"| FILTER
    MAP --> OUT

    style FILTER fill:#1f6feb,color:#fff,stroke:#0d419d,stroke-width:2px
    style GATE fill:#9e6a03,color:#fff
    style OUT fill:#238636,color:#fff
```

The dashed edge is the whole argument: in a tunnel nothing passes the gate, so nothing is applied.
There is no code path to switch, therefore no transition latency and no position jump.

---

## Where the 10% goes

Sized against the reference case — 1 km tunnel, 60 s at 60 km/h, so a **100 m** total budget.

```mermaid
pie showData
    title Error budget, 100 m over a 60 s outage at 16.7 m/s
    "Yaw — residual gyro bias" : 40
    "Along-track — speed estimate" : 30
    "Lateral — mount angle R_sv" : 20
    "Gyro scale factor in turns" : 10
```

Two requirements fall out of that arithmetic, and both are tighter than they look:

| Term | Requirement | Why it bites |
|---|---|---|
| Residual gyro bias | **0.005–0.01 °/s** after ZARU | At 0.1 °/s the yaw term alone eats 52 m — half the budget |
| Phone→vehicle yaw (R_sv) | **≈ 1°** | A 5° knock costs 87 m over the same outage, silently |

Map matching is deliberately **not** in the allocation. It buys margin back; it is not a term we
plan to spend — because it does not exist in a car park. Full derivation:
[docs/ERROR_BUDGET.md](docs/ERROR_BUDGET.md).

---

## Schedule — 13 days

```mermaid
gantt
    title Screening submission, Tue 8 Sep 2026
    dateFormat YYYY-MM-DD
    axisFormat %d %b

    section Sprint 0 · harness
    Loader, metrics, outages, CI     :active, s0, 2026-08-26, 3d
    Gate 0 · reproduces on 2 machines :milestone, crit, g0, 2026-08-28, 0d

    section Sprint 1 · spine
    Onyekpe baseline reproduction    :s1a, 2026-08-29, 4d
    InEKF, no learning, Allan Q      :s1b, 2026-08-29, 4d
    Gate 1 · physics-only within 3-5x :milestone, crit, g1, 2026-09-01, 0d

    section Sprint 2 · learning
    Speed + variance head            :s2, 2026-09-02, 3d
    Gate 2 · 95% inside 2 sigma      :milestone, crit, g2, 2026-09-04, 0d

    section Sprint 3 · submit
    Adaptive R_NHC, eval sweep       :s3a, 2026-09-05, 3d
    Write-up, deck, video            :s3b, 2026-09-05, 3d
    SUBMIT                           :milestone, crit, sub, 2026-09-08, 0d
```

**Gate 1 is a hard stop.** No network goes on top of a filter that has not cleared physics-only.
If it fails, diagnose in order: timestamps → NHC gating → process noise → ZUPT thresholds.

At 13 days the cut list bit early. What was **in scope** for screening: harness, leakage audit,
physics-only InEKF, eval sweep, write-up. What was **deferred past screening**: the speed head
(blocked on Gate 1), online HMM map matching, car-park mode, comma2k19 pretraining, and the
C++/Rust port. The Android logger and demo app were on that deferred list too and have since
landed (D-116, D-121..D-126). See [docs/SPRINT_BOARD.md](docs/SPRINT_BOARD.md) for the calendar as
it was written.

---

## Quick start

```bash
python -m venv .venv && ./.venv/Scripts/pip install -e ".[dev]"
```

Run the tests — none of them need the dataset:

```bash
pytest -q
```

Validate the evaluation protocol without any data:

```bash
python -m eval.run --dry-run
```

Once IO-VNBD is in `data/` (see [docs/DATASETS.md](docs/DATASETS.md)):

```bash
python -m eval.run --data data/IO-VNBD --seed 0
```

Measure what the GNSS actually does, and whether the paired `V-` track can serve as ground truth.
The `S-` smartphone GPS updates roughly every **9 s**, not the 1 Hz the protocol was drafted
against, so this is a Gate 0 blocker rather than a diagnostic:

```bash
python -m eval.cadence --data-root data
```

### Try the demo app on a phone

No Android toolchain needed — the pre-built `osm` flavour is committed at
[releases/app-osm-debug.apk](releases/app-osm-debug.apk); open
[releases/README.md](releases/README.md) on the phone for the direct link and install steps. Every
push to `main` also uploads a fresh build as the `app-osm-debug` artifact of the
[Android workflow](.github/workflows/android.yml). To build it yourself:

```bash
cd android-ui && ./gradlew :app:assembleOsmDebug :app:testOsmDebugUnitTest
```

Nothing the app shows is a submission number — [android-ui/README.md](android-ui/README.md)
explains what it is and is not.

---

## What is built and what is not

| Layer | State | Owner |
|---|---|---|
| Vincenty geodesy, NED, angle wrapping | **working**, tested against the canonical reference | S |
| CTE, CRSE, drift %, yaw error | **working**, each against a hand-computed case. CRSE pinned to R-WhONet Eq. (16), `Σ\|eᵢ\|` (D-054) | D |
| Wheel-speed leakage guard | **working**, and verified to reject | D |
| Outage injection + non-overlap proof | **working** | D |
| Frozen train/test split | **working** | D |
| Provenance stamping, seeding | **working** | D |
| Constraint gating, χ² gate, stop detection | **working** | S |
| InEKF `propagate()` on SE₂(3) | **working**, against the derivation | S |
| InEKF update family — ZUPT, ZARU, NHC, GNSS | **working but not yet consistent** — over-confident, ZARU is the cause (D-053). P-04 owns it | S |
| Ground truth from the paired `V-` VBOX GPS | **built, not yet verified against real bytes** — run `python -m eval.cadence` | D |
| Speed pseudo-measurement | `NotImplementedError` — Sprint 2 | S+M |
| Speed head, Onyekpe baseline | architecture defined, untrained | M |
| Baselines — naive strapdown, GNSS-available | **working**, against closed-form cases | P |
| Harness wired end to end (`eval/run.py`) | **working** on IO-VNBD; **Gate 1 measured, not closed** — 11.8× pooled at 60 s against 3–5× required (D-110, D-115) | D |
| `R_sv` — PCA initialiser, in-filter estimate, knock re-inflation | **working**; the bump *detector* cannot see a 5° knock at 10 Hz (D-075) | S |
| `core/ffi/idr_core.h` | **defined**, not implemented (D-043). Hotspot measured: the 36×36 expm, 50% of `propagate` | S |
| Replay renderer | **working**, empty state until a run produces artefacts | A |
| OSM graph, HMM matcher | designed and sized (D-034..D-037, D-041); no code — see [maps/README.md](maps/README.md) | P |
| Android foreground logger (`android/`) | **working, on the phone** — installed on the team A55, 125 Hz measured (D-116); CSV schema pinned to the harness loader; replay view renders a real `eval/run.py` record | A |
| Android operator UI (`android-ui/`) | **working, APK published** — OSM map, navigation screen, tunnel FSM (D-126), covariance ellipse (D-125); `mapbox` flavour scaffolded behind tokens (D-121); estimator is the on-device placeholder, not the InEKF (D-118) | A |

The `NotImplementedError` placeholders are deliberate: a stub returning `None` would let the
harness produce plausible all-zero trajectories and report them as results.

---

## Repo map

```
idr-26168/
├── idr/               shared: geodesy, provenance stamping, seeding
├── core/              filter core                                       [seat S]
│   ├── reference/       Python InEKF — screening prototype
│   ├── filter/          C++/Rust SE₂(3) state, propagation, updates
│   ├── constraints/     pseudo-measurements + gating conditions
│   └── ffi/             JNI surface; same lib feeds the edge build
├── models/            PyTorch — speed+variance head, adaptive R_NHC     [seat M]
├── eval/              the harness — owns every number in the submission [seat D]
│   ├── loaders/         IO-VNBD S- features; V- GPS is truth only, behind its own allowlist
│   ├── outages/         10/30/60/120/180 s injection
│   ├── metrics/         CTE, CRSE, drift %, yaw error
│   ├── cadence.py       measured GNSS cadence; V-/S- truth alignment
│   ├── baselines.py     naive strapdown + GNSS-available, the Gate 1 denominators
│   ├── replay/          one self-contained HTML page over the harness's own output
│   └── figures/         every plot regenerated by one command
├── maps/              OSM → CSR graph, HMM matcher                      [seat P]
├── android/           foreground logger + replay view (one Gradle root) [seat A]
├── android-ui/        operator UI — second Gradle root, osm + mapbox flavours [seat A]
├── releases/          the pre-built osm APK and how to install it
├── data/              gitignored; manifest with checksums is committed
├── docs/              method, error budget, decision log, protocol
└── tests/             the leakage audit is its own CI gate
```

---

## Documentation

| # | Document | Why |
|---|---|---|
| 1 | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | **The plan of record.** Audit of what is built, the reconciliation of the two prior plans, the 12-day calendar, gates. Start here. |
| 2 | [AGENTS.md](AGENTS.md) | Seats, risks, cut list, citation hygiene. Its sprint table is stale — see above. |
| 3 | [docs/GLOSSARY.md](docs/GLOSSARY.md) | InEKF, NHC, ZUPT, CTE/CRSE — read once, save everyone time. |
| 4 | [docs/EVALUATION.md](docs/EVALUATION.md) | **The protocol.** Every number in the submission comes from here. Still **DRAFT** — it freezes when Gate 0 closes, not before. |
| 5 | [docs/ERROR_BUDGET.md](docs/ERROR_BUDGET.md) | Where the 10% goes, term by term, with the arithmetic shown. |
| 6 | [docs/SE23_PROPAGATION.md](docs/SE23_PROPAGATION.md) | The derivation the filter is written from, checked in CI before the filter existed. |
| 7 | [docs/DATASETS.md](docs/DATASETS.md) | IO-VNBD schema, splits, the three traps. |
| 8 | [CONTRIBUTING.md](CONTRIBUTING.md) | Branches, CI gates, reproducibility rules. |
| — | [docs/SPRINT_BOARD.md](docs/SPRINT_BOARD.md) | Superseded by the plan of record. Kept for the record. |
| — | [docs/DECISION_LOG.md](docs/DECISION_LOG.md) | Append-only. Every non-obvious choice and its reason. |
| — | [docs/METHOD.md](docs/METHOD.md) | **The write-up.** First full pass, 1 Sep. §0 tags every number with its provenance; §12 (Results) is deliberately empty and says why. |
| — | [docs/SUBMISSION_AUDIT.md](docs/SUBMISSION_AUDIT.md) | The pre-submission checklist, with evidence per line and the gaps named as gaps. |
| — | [android/HANDOVER.md](android/HANDOVER.md) | **The Android list.** §9 is the remaining seat-A work in order; §1 is what is verifiable on the phone today. |
| — | [docs/UI_UX_NAVIGATION_PLAN.md](docs/UI_UX_NAVIGATION_PLAN.md) | The navigation UI plan; §7 is the Mapbox SDK review and the rules R1–R7 the `mapbox` flavour is held to. |
| — | [docs/TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md](docs/TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md) | The tunnel state machine and the on-screen stages; implemented as `TunnelFsm.kt` (D-126). |
| — | [releases/README.md](releases/README.md) | The published APK, which commit built it, and how to install it. |

---

## Six seats

| Tag | Role | Scope |
|---|---|---|
| **S** | Filter core & edge engine (Sushant) | InEKF, NHC/ZUPT/ZARU, mounting angle, JNI; becomes the 200 Hz FOG edge build |
| **M** | Learning | Speed+variance head, AI-IMU adaptive R_NHC CNN, FP16 export |
| **D** | Data & evaluation | IO-VNBD loader, outage harness, metrics, leakage audit, all plots |
| **P** | Maps & geodata | OSM → CSR graph, online HMM matcher, car-park fallback |
| **A** | Android | Foreground logger, uncalibrated sensors, timestamp alignment, demo UI |
| **C** | Field data & submission | Delhi/NCR collection, domain-shift ablation, write-up, deck, video |

---

## Non-negotiables

Cheap to break by accident, expensive to discover late.

1. **`S-` smartphone channels are the only inputs.** Wheel speed (`V-`) is disallowed by PS 26168.
   A CI test fails on any `V-` column reaching a feature tensor — and is itself verified to reject.
   One exception, and it is not an input: [EVALUATION.md](docs/EVALUATION.md) §1.2 permits the
   paired `V-` GPS as **ground truth** on paired sequences. It is read through
   `eval/loaders/truth.py`, whose allowlist is latitude, longitude and time of day and nothing
   else — no velocity, no heading — and whose return type has no feature path.
2. **Never double-integrate acceleration for speed.** 10 mg of bias ≈ 176 m of error in 60 s.
3. **The harness is frozen before any model trains.** Changing it needs a DECISION_LOG entry.
4. **Gate 1 is a hard stop.** No network on top of a filter that has not cleared physics-only.
5. **Every plot and table is stamped with the commit and seed that produced it.**
6. **Yaw error is logged separately, always** — it decides whether we hit 10%.
7. **Cite honestly.** AI-IMU's 1.10% is an automotive-grade IMU; WhONet's 0.15% needs wheel speed.
   Neither is a phone-only result. Our reference point is the Onyekpe INS numbers.

**Never cut:** the evaluation harness, the leakage audit, the yaw instrument, the honest-limits
section of the write-up.
