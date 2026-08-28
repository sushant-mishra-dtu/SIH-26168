# Datasets

**Owner:** seat D. Acquisition steps and the checksum manifest live in [../data/README.md](../data/README.md).

---

## 1. IO-VNBD — the mandated screening dataset

Onyekpe, Palade, Kanarachos, Szkolnik. *Data in Brief* **35**:106885 (2021).
DOI [10.1016/j.dib.2021.106885](https://doi.org/10.1016/j.dib.2021.106885) · arXiv 2005.01701 ·
repo `github.com/onyekpeu/IO-VNBD`.

Roughly 5,700 km / 98 h across the UK, France and Nigeria, from a Ford Fiesta. 8 drivers (A–H),
aggressive and defensive styles, 32 scenario types: roundabouts, hard braking, wet/dirt/mud roads,
drifts, potholes, valleys, motorway.

### 1.1 Two parallel streams

| Stream | Rate | Contents | Use |
|---|---|---|---|
| **`V-`** (car ECU) | 10 Hz, ~1.4M × 29 cols | Racelogic VBOX HD2 CAN + VBOX GPS: wheel speeds FL/FR/RL/RR, steering angle, yaw rate, brake pressure, engine rpm, gear, clutch, pedal, GPS lat/lon/velocity/heading/height | **Wheel channels are off-limits.** GPS here is useful as ground truth on paired sequences only. |
| **`S-`** (smartphone) | 10 Hz, GPS 1 Hz, ~2.2M × 24 cols | AndroSensor on Huawei P20 Pro / Moto G7 Power / BlackBerry Priv: accel XYZ, **gravity XYZ**, gyro yaw/pitch/roll, magnetometer XYZ, orientation, GPS lat/lon/speed/accuracy/sats | **This is our training data.** |

Sequences are paired: `V-S1` ↔ `S-S1`.

The repo ships both a "Synchronised V and S datasets" folder and an "Unsynchronised V and S Dataset"
folder. Use the synchronised one; record which in the manifest.

### 1.2 Frames and ground truth

Navigation frame is **NED**; tracking is 2-D, yaw-only; true displacement between GPS fixes is
computed with **Vincenty's inverse geodesic formula**; VBOX GPS accuracy ≈ ±3 m. Full protocol in
[EVALUATION.md](EVALUATION.md) §2.

### 1.3 Naming convention

Base sets `V-S1..V-S4`, `V-M`, `V-St1/4/6/7`, `V-Y1/Y2`. Scenario series `Vta` (Vta1..Vta30),
`Vtb` (Vtb1..Vtb13), `Vw` (Vw1..Vw17, with a/b/c splits), `Vfa`/`Vfb`. Tyre-pressure codes A–E
annotate some sets — relevant to wheel odometry only, therefore irrelevant to us.

The train/test split we use is fixed in [EVALUATION.md](EVALUATION.md) §3. **It is defined in code,
not in a notebook**, and no sequence appears on both sides.

### 1.4 Data-quality notes

- **Stationary segments exist, but the longest is 8.4 min, not >20 min.** ⚠️ This bullet previously
  claimed ">20 min"; that did not survive being checked against the files (D-045). Sweeping all 168
  distinct `S-` files with the filter's own ZUPT criteria, the longest continuous,
  uniformly-sampled, still stretch is **507 s in `S-T2`**, followed by 448 s in `S-T7` and two in
  `S-A6`. Nothing else clears 120 s. They remain free ZUPT/ZARU ground truth and they are what the
  Allan run in [ERROR_BUDGET.md](ERROR_BUDGET.md) §9.1 is computed on — but they cap τ at ~51 s,
  which is why bias instability is reported there as an upper bound and rate random walk is
  derived rather than measured. Regenerate the inventory with
  `python -m eval.allan --inventory-only --paths-from data/manifest/allan_segments_input.txt`.
- `S-I.csv` looks like a dedicated stationary recording (9.7 min, Lagos, parked) and is **not
  usable as one block**: it contains a 285 s recorder pause, and past that pause it switches to a
  burst mode whose timestamps repeat at ~1 ms with 39% duplicates. Allan variance assumes a uniform
  grid, so the loader-side segment finder rejects it.
- `S-A4.csv` is **malformed and must not be loaded**: an extra empty field at column 6 shifts every
  column after it by one, so the header's `ACCELEROMETER X` sits over the `DATE` string. The
  leakage guard happens to reject it (a trailing comma leaves an `Unnamed: 24`), but it is caught
  by accident rather than by design. TODO(seat D): record it in `data/manifest/` as excluded.
- A **"GPS outages" index file** flags poor-reception samples. Naturally-degraded samples are not the
  same thing as our injected outages; keep them separate and say which is which.
- Smartphone vibration noise ≈ 0.15 g on accel and ≈ 0.08 rad/s on yaw at hard brakes and bumps.
  This is what the gravity channels are there to help correct, and it is why a bump detector matters.
- `V-` data is UK-only; `S-` spans three countries.

### 1.5 Licence and citation

Distributed openly on GitHub for research benchmarking. There is **no prominent SPDX licence file in
the repo**, so treat it as research-use and cite Onyekpe et al. 2021 before redistributing anything.
Do not commit dataset bytes to this repo under any circumstance — see [../data/README.md](../data/README.md).

---

## 2. The three traps

Each of these has cost a team its submission somewhere.

1. **Phone data is only 10 Hz.** You cannot demonstrate a 200 Hz pipeline on it. Use `S-` for the
   app story and state explicitly in every caption and slide which stream produced which plot.
2. **Wheel speed is present but banned.** It sits in the same download, in adjacent columns, and it
   is trivially easy to leak into a feature set by accident. The dataloader allowlist and the CI test
   ([EVALUATION.md](EVALUATION.md) §1.3) exist for exactly this. Audit twice.
3. **No Indian roads.** IO-VNBD is UK/France/Nigeria. Delhi/NCR has underpasses, expressway tunnels
   and basement parking; collecting a few hours ourselves and running a **domain-shift ablation**
   (train on IO-VNBD, test on our own data) is something almost no other team will submit.

---

## 3. Baseline hyperparameters to reproduce

From the Onyekpe / WhONet papers. Sprint 1 reproduces these before anything of ours is trained.

| Setting | Value |
|---|---|
| Window length | 1 second (10 samples at 10 Hz) |
| Loss | MAE |
| Optimizer / LR | Adamax, 7e-4 |
| Batch / dropout | 128 / 0.05 |
| Model size | Vanilla RNN, 1 hidden layer, 72 units (~8,200 params) |
| Normalisation | Features scaled 0–1; white Gaussian noise injected on GNSS-derived training input |
| Outage simulation | Non-overlapping synthetic outages of 10 / 30 / 60 / 120 / 180 s on held-out scenarios |
| Framework (theirs) | Keras/TF — we reimplement in PyTorch |

Some items (the INS paper's loss and optimizer) are not fully surfaced in the published text. Where
we have to choose, record the choice in [DECISION_LOG.md](DECISION_LOG.md) rather than letting it
sit silently in a config file.

### Reported IO-VNBD numbers, for context

WhONet (**wheel odometry — the ceiling, not our target**) vs the physics baseline:

| Outage | Physics CTE / CRSE | WhONet CTE / CRSE | Max dist/seq | # seqs |
|---|---|---|---|---|
| 30 s | 0.84 / 2.31 m | 0.23 / 0.67 m | 987 m | 688 |
| 60 s | 1.02 / 4.56 m | 0.30 / 1.31 m | 1,960 m | 342 |
| 120 s | 1.78 / 9.11 m | 1.78 / 2.62 m | 3.9 km | 168 |
| 180 s | 2.90 / 13.67 m | 0.49 / 3.93 m | 5.6 km | 111 |

⚠️ **Two known defects in this table's source.** The intro quotes sequence counts of
809/399/197/129 while the tables give 688/342/168/111. And the 120 s CTE is identical (1.78 m) for
both methods, which is almost certainly a typo. Cite the tables, report both counts, and flag the
discrepancy ourselves ([EVALUATION.md](EVALUATION.md) §7.4).

---

## 4. Supplementary datasets

For pretraining and augmentation only. Nothing here replaces IO-VNBD for the screening numbers.

| Dataset | What | Why we might use it | Priority |
|---|---|---|---|
| **comma2k19** | 33 h highway driving, phone-grade IMU + GNSS + CAN | Best supplement for car-speed learning and GNSS-outage simulation at phone sensor grade | On the cut list — first to go if time runs short |
| **KITTI (raw/odometry)** | Car, OXTS RT3003 IMU + GPS | What AI-IMU used; good for validating the adaptive-R_NHC mechanism | Useful, but the IMU is far better than a phone — never quote its numbers as ours |
| **Google Smartphone Decimeter Challenge (2021–23)** | Real Android raw GNSS + IMU in cars, urban and highway | Closest match to our actual sensor and deployment story; multi-GNSS without NavIC | Optional |
| **Oxford RobotCar** | Car, long-term, IMU + GNSS | Industrial IMU; limited extra value | Low |
| **ADVIO** | Handheld VIO with ground truth, phone-grade | Phone sensor grade but pedestrian motion | Low |
| **RoNIN / OxIOD / RIDI / TLIO-Aria** | Pedestrian inertial | Backbone pretraining only, **never weights** ([DECISION_LOG.md](DECISION_LOG.md) D-017) | Low |
| **EuRoC / TUM-VI** | Drone and handheld VIO, no GNSS | Not vehicular. Skip. | None |

---

## 5. Our own collection (seat C)

Delhi/NCR, Sprint 2 onward. Targets:

- Road tunnels and underpasses — the central demo case.
- A multi-level basement car park — the honest hard case.
- At least one flyover-over-service-road pair, because that is the OSM tagging ambiguity most likely
  to break map matching in an Indian city.
- A stationary segment of several hours for our own Allan variance ([ERROR_BUDGET.md](ERROR_BUDGET.md) §9).

Log with the seat-A foreground logger, uncalibrated sensor types, real timestamps. Every collection
run gets a manifest row: device, mount, route, date, weather, driver, and the logger commit SHA.
