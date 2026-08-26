# AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168

## TL;DR
- **The winning architecture is a tightly-coupled learned-INS: a neural network that regresses forward velocity (or displacement) + covariance from a gravity-aligned/body-frame IMU window, fused into an Invariant EKF (InEKF) that also carries phone-to-vehicle misalignment as a state and applies non-holonomic constraints (NHC) — i.e. an AI-IMU/TLIO hybrid retargeted to the ground-vehicle domain, with HMM map matching on offline OSM as an outer correction layer.** Pedestrian-domain networks (RoNIN, IONet, TLIO, IDOL) do NOT transfer to cars and must be retrained; only AI-IMU (Brossard), WhONet/Onyekpe (wheel, reference-only), and vehicle speed-from-IMU works (VeTorch/Cortés) are directly relevant.
- **The <10% drift benchmark is achievable, but almost entirely because of the constraints, not the raw IMU.** Pure smartphone-IMU strapdown drifts to hundreds of metres in 60 s; the sub-5%/sub-10% figures in the literature come from NHC + ZUPT + learned velocity + map matching. The dominant error term is **heading (yaw) drift from gyro bias**, which converts linearly into lateral position error — attack this first.
- **IO-VNBD is the mandated screening dataset; use the smartphone ("S-") channels (10 Hz accel/gyro/mag + gravity + 1 Hz GPS), NOT the wheel-speed ("V-") channels, since wheel odometry is disallowed.** The published Onyekpe pipeline (window = 1 s, MAE loss, Adamax, LR 7e-4, batch 128, NED frame, GNSS outages simulated at 10/30/60/120/180 s) is your baseline to reproduce and beat.

---

## Task 1 — Systematic Comparison of Learned Inertial Odometry Architectures

### 1.1 Comparison table

| Method (year) | Model family / layers | Input rep. | Output rep. | Coupling | Training data | Reported accuracy | Params/latency | Code | Domain / transfer |
|---|---|---|---|---|---|---|---|---|---|
| **IONet** (2018, AAAI) | 2-layer Bi-LSTM (seq2seq) | 200-sample IMU window (accel+gyro), device frame | 2D polar displacement (Δpos, Δheading) per window | Decoupled (concatenate windows) | OxIOD (handheld) | Outperforms PDR/SINS; generalises to trolley/stroller | not reported | OxIOD public; IONet not official | **Pedestrian**; assumes segmentable planar motion — weak for car |
| **RIDI** (2018, ECCV) | SVM/CNN regress accel corrections | IMU in stabilised frame + placement class | Low-freq velocity to correct double-integration | Decoupled (corrects accel then integrates) | RIDI (handheld, 4 placements) | ~cm/s velocity; positional drift small indoors | small | github.com/higerra/ridi_imu | **Pedestrian**; relies on human placement priors |
| **RoNIN** (2020, ICRA) | ResNet-18 / LSTM / TCN | 200-sample gyro-gravity-aligned IMU window | 2D velocity vector in heading-agnostic frame | Decoupled | RoNIN (42.7 h, 100 subjects) | ATE ~ a few m; strong on unseen subjects | ResNet-18 ~ 4.6M | github.com/Sachini/ronin (data+code) | **Pedestrian**; velocity magnitude tied to gait — fails on car speeds |
| **TLIO** (2020, RA-L) | 1D ResNet regress 3D disp + 3×3 diag covariance | gravity-aligned IMU window | 3D displacement + covariance | **Tightly-coupled** stochastic-cloning EKF (full pose/vel/bias) | 60 h headset pedestrian | **27% lower yaw & 33% lower position drift vs the best RoNIN velocity-concatenation baseline; >99% of error within ±3σ** (Liu et al., IEEE RA-L 5(4), 2020; arXiv:2007.01867) | ResNet ~ small; runs on device | github.com/CathIAS/TLIO | **Pedestrian (headset)**; the *filter framework* transfers, the network doesn't |
| **IDOL** (2021, AAAI) | 2-stage: orientation net + localization net (LSTM) | IMU + learned orientation | 3D orientation then 2D position | Loosely (EKF for orientation) | IDOL/RoNIN-like handheld | Beats RoNIN/RIDI on handheld | moderate | github.com/KlabCMU/IDOL | **Pedestrian** |
| **RNIN-VIO** (2021, ISMAR) | ResNet+LSTM inertial net inside VIO | IMU window | relative motion + used in tightly-coupled VIO | Tightly (with visual) | large handheld/AR | robust under fast motion / vision loss | moderate | partial | **Pedestrian/AR**; needs camera |
| **PDRNet** (2021) | CNN classifier + regressor | phone IMU, activity-classified | 2D disp per mode | Decoupled | pedestrian | mode-dependent | small | — | **Pedestrian** |
| **AI-IMU Dead-Reckoning** (2019/2020, T-IV) | **CNN regresses measurement-noise covariance** of NHC pseudo-measurements | IMU window (accel+gyro) | Adaptive R for lateral/vertical velocity ≈0 pseudo-meas | **Tightly-coupled IEKF** (SE₂(3) + biases) | **KITTI odometry** (car); trained seqs 00,01,04–11, seq 02 held out | **1.10% average translational error, IMU-only, competing with LiDAR/stereo methods** (Brossard/Barrau/Bonnabel, IEEE T-IV 2020; arXiv:1904.06064) | **CNN adapter ~6,210 params (+12 for P0/Q); Adam LR 1e-4; real-time** | github.com/mbrossar/ai-imu-dr | **Ground vehicle** — directly applicable |
| **Onyekpe "Learning to Localise" INS** (2021, Appl.Sci.) | IDNN / vRNN / LSTM / GRU | accel + gyro, NED, 1 s window | INS displacement-error + orientation-rate correction | Decoupled correction of INS | **IO-VNBD** (car) | **up to 89.55% improvement on INS displacement & 93.35% on orientation-rate vs raw INS** (Appl.Sci. 11(3):1270, DOI 10.3390/app11031270); quick-accel scenario NN max CRSE 8.62 m / 0.33 rad/s vs INS 79.05 m / 0.67 rad/s over ~220 m | small RNN | github.com/onyekpeu (IO-VNBD) | **Ground vehicle, smartphone-grade** — most directly relevant valid method |
| **WhONet / R-WhONet** (2021/2025) | vanilla RNN (72 units, ~8.2k params) / transfer-learned | **4 wheel-speed channels** | displacement error correction | Decoupled | IO-VNBD + CUPAC | 180 s: CTE 0.49 m / CRSE 3.93 m vs 2.90/13.67 physics; up to 93% reduction | ~8k params | github.com/onyekpeu/WhONet | **Ground vehicle but WHEEL-ODOMETRY — NOT a valid PS26168 solution; upper-bound reference only** |
| **VeTorch / inertial speed learning** (2023–2025) | TCN encoder, PCA alignment, federated personalisation | phone IMU, aligned to vehicle frame | forward vehicle **velocity** | Loosely (speed pseudo-meas to EKF) | phone-in-car + OBD/GPS ground truth | vehicle speed from phone IMU; SmoothL1 loss | moderate | partial | **Ground vehicle, smartphone** — directly relevant |
| **Cortés/Solin/Kannala** (2018, MLSP) | CNN regress momentary speed | 2 s IMU window (iPhone) | scalar **speed** as EKF constraint | Loosely (speed pseudo-meas + ZUPT into EKF) | handheld iPhone | constrains drift vs free INS | small | — | **Handheld**; concept transfers to car speed |
| **AirIMU** (2023) | net learns IMU correction + preintegration **uncertainty** | raw IMU | corrected IMU + covariance | Tightly (pose-graph/EKF) | full IMU spectrum incl. **KITTI car**, 262 km heli | +31.6% in IMU-GPS PGO ablation | moderate | github.com/haleqiu/AirIMU | **Multi-domain incl. vehicle** — relevant for the FOG/edge engine |
| **AirIO** (2025) | body-frame velocity net + attitude encoding + AirIMU | **body-frame** IMU + attitude | body-frame velocity + covariance | Tightly (uncertainty-aware EKF) | UAV | +66.7% from body-frame rep; +23.8% from attitude | moderate | air-io.github.io | **Drone**; body-frame insight transfers |
| **CTIN** (2022, AAAI) | ResNet encoder + local/global multi-head self-attention + Transformer decoder | IMU window | velocity + trajectory + uncertainty (multi-task) | Decoupled | RIDI, OxIOD, RoNIN, IDOL | lower ATE/RTE than RoNIN variants; RoNIN-dynamic ATE 6.89 m | larger (attention) | partial | **Pedestrian** |
| **iMoT** (2024) | Inertial Motion Transformer w/ uncertainty | IMU window | velocity + uncertainty | Decoupled | RIDI/RoNIN/OxIOD/IDOL | RoNIN dynamic ATE 5.31 m vs TLIO 6.77, CTIN 6.89 | larger | partial | **Pedestrian** |
| **EqNIO** (2024/ICLR25) | **Sub-equivariant** O(2) net; canonicalises to gravity-aligned frame; wraps TLIO/RoNIN | IMU → equivariant canonical frame | equivariant displacement + covariance | Both (drop-in) | TLIO/Aria/RIDI/OxIOD | new SOTA inertial-only; better generalisation to unseen orientation | wrapper overhead | openreview C8jXEugWkq | **Pedestrian data but symmetry principle is exactly what solves arbitrary phone mounting** |
| **FTIN / STARIO / IONext / GNIO / TinyIO** (2025–26) | frequency-time fusion / lightweight reparam / gated / next-gen conv | IMU (+freq features) | displacement + covariance | Decoupled/filter | RoNIN/RIDI/OxIOD/TLIO/IMUNet | FTIN: RoNIN ATE −43.0%, RTE −13.1% vs RoNIN-ResNet | lightweight variants | arXiv 2025 | **Pedestrian**; useful lightweight backbones |
| **SNN + InEKF** (2026) | **Spiking NN** adapts InEKF noise covariance | IMU | adaptive covariance for InEKF | Tightly (InEKF) | low-cost MEMS robot | brain-inspired, low compute | very low power | arXiv 2601.08248 | **Robot/vehicle**; interesting for FPGA/edge low-power |
| **MosaicIMU / KISS-IMU** (2026) | mixture-of-experts / self-supervised motion-balanced | IMU | velocity + uncertainty | filter | multi-carrier | generalisation across carriers | moderate | arXiv 2606/2603 | Mixed; cross-domain generalisation research |

### 1.2 Known non-transfer to ground vehicles (flag explicitly)
- **RoNIN, IONet, RIDI, IDOL, CTIN, iMoT, PDRNet, RNIN-VIO** were trained on and validated only on **pedestrian/handheld** data. Their velocity regressors implicitly learn a **human gait/speed prior** (walking speeds ~0.5–2 m/s, quasi-periodic acceleration). A car at 60 km/h (16.7 m/s) with smooth cruise and no periodicity is far outside their training distribution; the networks saturate and grossly under-predict speed. RoNIN additionally regresses a heading-agnostic velocity magnitude tuned to gait cadence. **Use these only for their architectural backbones and filter frameworks, not their weights.**
- **AirIO** is drone-domain but its central finding — keep IMU in the **body frame** and encode attitude — is a directly transferable design principle for the car problem.
- **The transferable core** is: (a) TLIO's tightly-coupled displacement+covariance EKF structure; (b) AI-IMU's learned adaptive covariance on NHC pseudo-measurements on KITTI (the only method with a clean 1.10% translational error on cars); (c) EqNIO's equivariant canonicalisation, which is the principled answer to arbitrary phone mounting; (d) Onyekpe's IO-VNBD INS-correction RNNs.

---

## Task 2 — IO-VNBD dataset & experimental setups

### 2.1 Dataset structure, schema, units, frames
- **Provenance:** Onyekpe, Palade, Kanarachos, Szkolnik, *Data in Brief* 35:106885 (2021), DOI 10.1016/j.dib.2021.106885; arXiv 2005.01701; repo github.com/onyekpeu/IO-VNBD (CSV + Python tools; folders "Synchronised V abd S datasets" and "Unsynchronised V and S Dataset"). Collected UK, France, Nigeria; ~5,700 km / 98 h combined (Data in Brief reports ~40 h/1,300 km "V-" and ~58 h/4,400 km "S-").
- **Two data streams:**
  - **Vehicle/ECU ("V-") — 10 Hz, ~1.4M × 29 columns**, via Racelogic VBOX HD2 CAN logger + VBOX GPS (10 Hz), Ford Fiesta. Columns include: no. GPS sats, time-of-day (s), GPS lat/lon (deg), GPS velocity (km/hr), GPS heading (deg), GPS height (km), GPS vertical velocity (km/hr), sample period (s), steering angle (deg), **wheel speed FL/FR/RL/RR (rad/s)**, yaw rate (deg/s), indicated vehicle speed (km/hr), indicated longitudinal accel (g), lateral accel (g), handbrake (0/1), gear requested, gear, engine speed (rpm), coolant temp (°C), clutch (0/1), brake pressure (psi), brake position (0/1), battery voltage (V), air temp (°C), accelerator pedal (%).
  - **Smartphone ("S-") — 10 Hz (GPS 1 Hz), ~2.2M × 24 columns**, via AndroSensor on Huawei P20 Pro / Moto G7 Power / BlackBerry Priv. Columns: GPS lat/lon (deg), GPS altitude (m), GPS speed (km/hr), GPS accuracy (m), GPS orientation (deg), GPS sats in range, time-since-start (ms), date, **accel X/Y/Z (m/s²), gravity X/Y/Z (m/s²), gyro yaw/pitch/roll (rad/s), magnetic X/Y/Z (µT), orientation yaw/pitch/roll (deg)**.
- **Coordinate frames:** navigation frame = **North-East-Down (NED)**; 2-D horizontal tracking (pitch/roll set to zero, yaw-only rotation R^n_b). True displacement between GPS fixes computed via **Vincenty's inverse geodesic formula**. GPS accuracy ≈ ±3 m (VBOX).
- **Known data-quality items:** dedicated stationary (>20 min) segments for bias estimation; a "GPS outages" index file flags poor-reception samples; smartphone vibration noise ≈0.15 g accel and ≈0.08 rad/s yaw at hard brakes/bumps (hence the gravity channels for correction); "V-" data UK-only, "S-" data across three countries. 8 drivers (A–H), aggressive/defensive styles, 32 scenario types (roundabout, hard-brake, wet/dirt/mud roads, drifts, potholes, valleys, motorway). Tyre-pressure codes A–E annotate sets (relevant to wheel-odometry only).
- **Licence:** distributed openly on GitHub for research benchmarking (repo README / Data in Brief "Data accessibility"); no prominent SPDX licence file in-repo, so treat as research-use and cite Onyekpe et al. 2021 before redistribution.

### 2.2 Naming convention & splits (from WhONet paper)
- Prefix **V-** = ECU, **S-** = smartphone; paired (V-S1 ↔ S-S1). Base sets V-S1..V-S4, V-M, V-St1/4/6/7, V-Y1/Y2; scenario series **Vta** (Vta1..Vta30), **Vtb** (Vtb1..Vtb13), **Vw** (Vw1..Vw17 with a/b/c splits), **Vfa/Vfb**.
- **Train (~1,590 min / 1,165 km):** V-S1, V-S2, V-S3c, V-S4, V-St1, V-M, V-Y2, plus many Vta/Vtb/Vw/Vfa/Vfb subsets.
- **Test — challenging (10 s outages):** roundabout (Vta11, Vfb02d), accel-change (Vfb02e, Vta12), hard-brake (Vw16b, Vw17, Vta9), sharp-corner/SLR (Vw6/7/8), wet (Vtb8/11/13); motorway easy = Vw12.
- **Test — long outages:** V-Vtb3, V-Vfb01c, V-Vfb02a, V-Vta1a, V-Vfb02b, V-Vfb02g, V-St6, V-St7, V-S3a. Second dataset CUPAC used similarly.

### 2.3 Exact experimental hyperparameters

| Item | "Learning to Localise" INS (Appl.Sci. 2021, **valid, IMU-based**) | WhONet (EAAI 2021, **wheel, reference**) |
|---|---|---|
| Model | IDNN / vRNN / LSTM / GRU (best per case) | vanilla RNN, 1 hidden layer, **72 units (~8,209 params)** |
| Input | accel + gyro (NED) | 4 wheel-speed channels (rad/s) |
| Output | INS displacement-error + orientation-rate correction | wheel-speed displacement-error correction |
| Window | **1 second** | 10 Hz, time-step 1, windows X1=t..t-0.9, X2=t-1..t-1.9 |
| Sampling | 10 Hz | 10 Hz |
| Normalization | white-Gaussian noise injected on GPS-derived training input | features scaled 0–1 |
| Loss | (not fully surfaced) | **MAE** |
| Optimizer/LR | (not fully surfaced) | **Adamax, LR 7e-4** |
| Dropout | — | 0.05 |
| Batch | — | 128 |
| Epochs | not stated | not stated |
| Framework | Keras/TF | Keras/TF |

- **GNSS outage injection:** simulated on held-out test scenarios, prediction cadence 1 s, non-overlapping sequences of each outage length. Intro states **809 (30 s), 399 (60 s), 197 (120 s), 129 (180 s)** sequences; per-table evaluated counts differ (688/342/168/111 for IO-VNBD). Challenging scenarios use 10 s test sequences. Report both counts (source is internally inconsistent).
- **Metric definitions (note the task brief mislabels these):** **CTE = Cumulative True Error** (signed sum of per-second errors) and **CRSE = Cumulative Root Square Error** (RMS of per-second errors) — these are NOT cross-track error / ATE. No ATE is used in the Onyekpe papers.

### 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline)

| Outage | Physics CTE / CRSE (μ) | WhONet CTE / CRSE (μ) | Max dist/seq | # seqs |
|---|---|---|---|---|
| 30 s | 0.84 / 2.31 m | **0.23 / 0.67 m** | 987 m | 688 |
| 60 s | 1.02 / 4.56 m | **0.30 / 1.31 m** | 1,960 m | 342 |
| 120 s | 1.78 / 9.11 m | **1.78 / 2.62 m** (CTE tie likely a source typo) | 3.9 km | 168 |
| 180 s | 2.90 / 13.67 m | **0.49 / 3.93 m** | 5.6 km | 111 |

WhONet reports "up to 93% reduction after any 180 s" and ~8.62 m error after 5.6 km. These are **wheel-odometry** numbers — they set the practical upper bound; a smartphone-IMU-only solution will be worse and should be benchmarked against the "Learning to Localise" INS-only numbers instead.

---

## Task 3 — Phone-to-vehicle alignment & misalignment estimation

**Problem:** recover rotation R_sv (smartphone→vehicle) with unknown, possibly time-varying pitch/roll/yaw. Standard decomposition:
- **Roll & pitch from gravity:** with the vehicle stationary or at constant velocity on level road, accelerometer output ≈ gravity g. z-axis unit vector ẑ_v = mean(a)/‖mean(a)‖ recovers the vertical, fixing 2 DOF (roll, pitch). IO-VNBD provides explicit gravity X/Y/Z channels for exactly this.
- **Yaw (forward heading) from longitudinal manoeuvres via PCA:** level the horizontal acceleration using ẑ_v, remove gravity, buffer horizontal accel during straight-line accel/brake events, run **PCA**; the principal component is the along-track (forward) axis ŷ_v. Resolve the 180° ambiguity by sign of longitudinal accel vs speed change. Then x̂_v = ŷ_v × ẑ_v. This is the VeTorch/DeepTrack/road-grade pipeline and the HERE/TeleNav patents (US 8,086,405 "Compensation for mounting misalignment"; US 10,371,516 PCA-based misalignment; US 10,739,140 / 11,441,906 iterative NHC misalignment estimation).
- **Recursive in-filter estimation (recommended):** augment the navigation state with R_sv (as a small-angle error state δθ_sv) and estimate it recursively in the Kalman filter under NHC — the "IMU Alignment for Smartphone-based Automotive Navigation" formulation: apply NHC (lateral & vertical vehicle velocity ≈ 0) with the smartphone-to-vehicle orientation as an unknown state; the constraints couple phone dynamics to relative orientation, making it observable during turns/accelerations. This avoids one-shot init fragility.
- **Magnetometer-aided heading:** can seed yaw but is unreliable inside vehicles (cabin ferromagnetics, speakers, currents) — use only as a weak prior, not a primary source.
- **Learned alignment:** EqNIO's sub-equivariant canonicalisation is the modern answer — the network is equivariant to yaw roto-reflections around gravity, so it does not need to memorise every mount orientation. This is the single most relevant recent idea for "arbitrary phone mounting."
- **Re-alignment trigger:** detect mount disturbance (a step in the gravity vector direction, or a spike in high-frequency gyro energy inconsistent with vehicle dynamics) and re-run PCA / inflate the R_sv covariance so the filter re-converges.

---

## Task 4 — NHC, ZUPT/ZARU, pseudo-measurements, InEKF

- **Non-holonomic constraints:** in the vehicle body frame, lateral velocity v_y ≈ 0 and vertical velocity v_z ≈ 0 (no side-slip, no jumping). Pseudo-measurement: H·v_body = [v_y; v_z] with expected value 0 and covariance R_NHC. This bounds cross-track drift massively when GNSS is absent. Valid only when actually driving forward on-road; must be gated off during slips, sharp drifts, and reversing.
- **ZUPT (zero-velocity update):** detect vehicle stationary (traffic lights) from low accel variance + low gyro magnitude; apply v_body = 0 pseudo-measurement — resets velocity error and observes accelerometer bias. **ZARU (zero angular-rate update):** when stationary, ω = 0 pseudo-measurement observes gyro bias — critical because gyro bias is the dominant heading-drift driver.
- **Learned adaptive covariance (AI-IMU):** Brossard et al. use a CNN (adapter ~6,210 params) to output R_NHC dynamically at each step (tight vs loose enforcement) as a function of the IMU window — e.g. relax the lateral constraint during hard cornering, tighten it on straights. This is the key innovation that lets an IMU-only IEKF reach 1.10% translational error on KITTI (Adam LR 1e-4, optimizing relative translation error over 100 m sub-sequences). Replicate this exact mechanism for the phone problem.
- **InEKF / group-affine structure:** the state (R, v, p) lives on the matrix Lie group SE₂(3) (with bias augmentation → SE₂(3) ⋉ bias). When the dynamics are **group-affine**, the invariant error e = X̂⁻¹X (left-invariant) obeys a **log-linear** differential equation whose linearisation is **state-independent** — the error propagation matrix does not depend on the estimate. Consequences: (1) consistent covariance (no false observability of yaw as in a naïve EKF), (2) larger convergence basin under big initial misalignment (exactly the arbitrary-mount case), (3) easier tuning. Reported vehicle results (Sabra et al., *Sensors* 23(13):6097, 2023, DOI 10.3390/s23136097): a loosely-coupled INS/GNSS InEKF cut overall 2-D position RMS error from **19.4 m (EKF) to 3.3 m (−82.98%)** and max error from **73.9 m to 14.2 m (−80.78%)**. Recent SE₂(3)-EKF work adds adaptive NHC and Lie-group calibration of installation angle/lever-arm for GNSS outages.

---

## Task 5 — Map matching & map-constrained filtering

- **Baseline HMM (Newson & Krumm 2009):** hidden states = candidate road segments near each observation; **emission probability** ∝ Gaussian in great-circle distance from fix to candidate projection; **transition probability** penalises |great-circle distance − on-road route distance| between consecutive candidates (β exponential). Viterbi decodes the most likely path. For an inertial trajectory input, replace the raw-GPS emission σ with the **filter's own position covariance** (from the EKF), and use the along-track distance the filter reports for the transition term — this is the principled way to feed a filtered INS track (with covariance) rather than noisy GPS fixes into the HMM.
- **Online variant (Goh et al.):** sliding-window / partial-path commitment — commit Viterbi states outside a lookback window, keep the last N observations tentative. Barefoot implements both Newson-Krumm (offline) and Goh (online). For a car app, commit segments older than ~5–10 s.
- **Ambiguity handling:** parallel roads / service-vs-flyover / multi-level require the transition model plus heading consistency (INS heading vs road bearing) and, for grade, barometer/road-slope; lane-level matching needs a lane graph (rarely in OSM) so stay at road-level.
- **Open-source implementations for on-device/offline:**
  - **GraphHopper map-matching** (Java, uses hmm-lib; embeds OSM; Android-capable) — most practical for a mobile app.
  - **bmwcarit/barefoot** (Java, online+offline HMM, server-oriented).
  - **bmwcarit/offline-map-matching** + **graphhopper/hmm-lib** (library-only, bring-your-own graph).
  - **fast-map-matching (FMM)** (C++/Python, precomputed UBODT upper-bounded origin-destination table → extremely fast; STMATCH variant needs no precomputation) — best raw speed; needs a shapefile/OSM conversion.
  - **Valhalla Meili** (C++, HMM, tiled routing, mobile-friendly tiles), **pgMapMatch** (Postgres/PostGIS, server), **bmm** (Bayesian particle, offline+online).
  - Rust: no dominant mature library; wrap FMM (C++) via FFI, or reimplement Viterbi over a compact CSR graph.
- **Building a compact offline OSM graph:** take a regional `.pbf` extract (Geofabrik), filter to `highway=*` drivable classes, build a routable graph (osmium/osmnx → nodes+edges, or GraphHopper's own import), store as CSR adjacency + edge geometry. Memory: a city-scale graph is tens of MB; a state-scale extract can be a few hundred MB — prune to bounding box for the demo. GraphHopper's contraction-hierarchy graphs are compact and designed for mobile.
- **No-road-graph environments (multi-level car parks):** HMM map matching is unusable. Fall back to **pure constrained DR + barometer**: barometer ΔP → floor/level detection (~0.12 hPa ≈ 1 m; a parking level ≈ 2.5–3 m ≈ 0.3–0.36 hPa step); ramp detection from sustained pitch (gravity-vector tilt) + baro rate; loop/turn geometry from gyro. This is a distinct mode; switch to it when GNSS is absent AND no OSM drivable edge is within the position covariance ellipse.

---

## Task 6 — GNSS outage detection & seamless mode switching

- **Android detection signals:** `GnssStatus` per-satellite **C/N₀ (dB-Hz)** and satellite count; `Location.getAccuracy()` (68% horizontal radius); fix age. Raw **`GnssMeasurement`** API (Android 7+ Nougat) exposes pseudoranges, ADR/carrier phase, Doppler, `Cn0DbHz`, and multipath indicators for tighter/low-level detection.
- **Degradation/NLOS/multipath cues:** low or rapidly fluctuating C/N₀, low elevation + high C/N₀ mismatch, pseudorange residual outliers, HDOP/PDOP spikes, sudden accuracy inflation, position jumps inconsistent with INS. ML NLOS classifiers use features {elevation, C/N₀, ΔC/N₀, pseudorange residual, PSD} (SVM/RF/GRU/CNN). Continuous time-series C/N₀ (Kubo et al., *Sensors* 20:4059, 2020) is more robust than instantaneous thresholds — require C/N₀ to recover for a hold-off period before re-trusting a satellite.
- **Latency:** the OS often reports a "good" fix for a short interval after real signal loss (last-known / coasted fix) before accuracy inflates — do not wait for the OS to declare loss; cross-check GNSS velocity/position against the INS prediction and gate on innovation.
- **Architecture — no hard switch (strongly recommended):** run **one continuously-running error-state EKF/InEKF**. The IMU (+NHC+ZUPT) is always the process/propagation model at 10–200 Hz; the GNSS update step is simply **gated** by a χ²/Mahalanobis innovation test on each fix. In a tunnel, no GNSS updates are applied — the filter naturally coasts on DR. There is no code-path switch, hence "millisecond-scale transition" is automatic.
- **Re-acquisition without a jump:** on GNSS return, the fix enters as a normal measurement update; because the filter carries an inflated (but bounded, thanks to NHC/map) covariance, the correction is covariance-consistent and smooth. For the *displayed* trajectory, run a short **backward RTS smoother** over the outage window (or a fixed-lag smoother) so the on-screen path is retro-corrected rather than snapping. Reject the first re-acquired fixes if they fail the innovation gate (common multipath on tunnel exit).

---

## Task 7 — On-device deployment & real-time engineering

- **Android sensor rate:** from **Android 12 (API 31)**, `registerListener()` motion/position sensors are **capped at 200 Hz** unless the app declares **`HIGH_SAMPLING_RATE_SENSORS`** permission; `SensorDirectChannel` is capped at `RATE_NORMAL` (~50 Hz) without it. Empirically some devices allow ~206 Hz without the permission; `SENSOR_DELAY_FASTEST` gives ~400+ Hz accel/gyro, ~100 Hz mag only with the permission. Play Store review: high-rate sensor use must be justified. Note: if the user disables microphone access via device toggles, motion/position sensors are rate-limited regardless of the permission. **Background restriction:** since Android 9, continuous sensors get no events in background — you MUST run a **foreground service** with a persistent notification for continuous logging.
- **iOS CoreMotion:** `deviceMotion`/raw accel/gyro typically up to ~100 Hz (device-dependent, historically ~100 Hz cap on many devices).
- **Calibrated vs uncalibrated:** use `TYPE_ACCELEROMETER_UNCALIBRATED` and `TYPE_GYROSCOPE_UNCALIBRATED` — they return raw values **plus** the currently estimated bias in separate fields, letting you keep raw + model bias explicitly in the filter (rather than the OS silently subtracting a possibly-wrong bias). Raw+bias separation matters because the InEKF estimates bias as a state; double-compensation corrupts it.
- **Timestamp jitter / clock alignment:** sensor `event.timestamp` is a monotonic device clock (ns) with jitter and batching; GNSS is UTC/GPS-time. Convert both to a common monotonic base, model the offset, and interpolate GNSS to IMU epochs. Never assume nominal Δt — use actual timestamps.
- **Thermal/battery:** sustained 200 Hz sensing + NN inference heats the SoC and throttles; budget for it. Run NN at low rate (see below), keep the filter cheap.
- **Threading:** high-rate filter thread (propagation at IMU rate, lock-free ring buffer for IMU samples) + a lower-rate NN inference thread (e.g. velocity/covariance net every 0.1–1 s) that posts measurement updates to the filter; GNSS callback thread posts gated updates. UI on the main thread reads a snapshot of state.
- **Inference stack:** **LiteRT / TensorFlow Lite** (best Android integration, NNAPI/GPU/DSP/NPU delegates), **ONNX Runtime Mobile**, **ExecuTorch** (PyTorch-native, good since you use PyTorch), **NCNN** (lightweight, no deps). For IMU regression, **FP16** is essentially lossless; **INT8** can hurt regression precision (velocity/covariance) — quantize the backbone but consider keeping the final regression head in FP16, and calibrate per-channel. Measure the covariance-head degradation explicitly (a mis-scaled covariance corrupts the EKF more than a slightly noisy mean).
- **Shared C++/Rust core:** write the InEKF + NHC/ZUPT + map-matching in **C++ or Rust**, expose to Android via **JNI** (or Rust `jni` crate), reuse the identical library as the **edge engine** consuming external FOG-grade IMU at ~200 Hz. Keep the NN as a separate swappable module (TFLite/ExecuTorch on phone; ONNX/TensorRT on edge).

---

## Task 8 — IMU error modelling & sensor-grade comparison

### 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part)

| Parameter | Consumer smartphone MEMS | Industrial/tactical MEMS | FOG (navigation) |
|---|---|---|---|
| Gyro bias instability | ~10–100 °/hr (often unspecified) | ~0.3–3 °/hr (tactical ≈ <1 °/hr) | <0.01–0.1 °/hr |
| Angular random walk (ARW) | ~0.5–5 °/√hr | ~0.1–0.3 °/√hr | <0.05 °/√hr |
| Accel bias instability | ~0.1–1 mg | ~10–50 µg | ~1–10 µg |
| Velocity random walk (VRW) | ~0.1–1 m/s/√hr | lower | very low |
| Scale-factor error | ~1–5 % | ~100–1000 ppm | ~10–100 ppm |
| g-sensitivity | significant, often unspecified | specified/low | negligible |
| Temp drift | large, uncompensated | compensated | well-compensated |

Reference anchors: tactical-grade MEMS ≈ gyro bias <1 °/hr, ARW <0.1 °/√hr (Micro-Magic U4930 quotes 0.3 °/hr; Inertial Labs IMU-P ~1 °/hr; EMCORE/ERICCO ER-MG-067 = 0.3 °/hr, 0.125 °/√hr); a navigation-grade MEMS example (satellite use) claims 0.006 °/hr bias, ~0.003 °/√hr ARW; FOGs are "an order of magnitude better than MEMS" on bias instability (better than 0.1 °/hr, ARW <0.05 °/√hr). Smartphone IMUs are typically **1–3 orders of magnitude worse** and often don't publish these numbers.

### 8.2 Error propagation → error budget vs <10% benchmark
- **Heading error from gyro bias:** a constant gyro bias b_g integrates to heading error Δψ(t) = b_g·t. For a car going straight at speed v over outage time t, the lateral (cross-track) position error is approximately e_lat ≈ v·∫₀ᵗ Δψ dτ ≈ ½·b_g·v·t².
  - Example — tunnel, v = 16.7 m/s (60 km/h), t = 60 s (distance 1 km): to stay under 100 m lateral (10% of 1 km), need ½·b_g·16.7·60² < 100 → b_g < 100/(½·16.7·3600) = **3.3×10⁻³ rad/s ≈ 0.19 °/s ≈ 683 °/hr**. That is *easy* on raw bias magnitude — BUT this assumes bias is the only term and is constant; in practice **bias instability + ARW + scale-factor + the yaw-rate error during turns** dominate, and uncorrected smartphone gyro drift plus misalignment error blow this up. The real killer is heading error accumulated **through turns** (scale-factor and bias during high rate) and unmodelled bias walk.
  - Example — 50 m in <1 min at low speed: to keep <5 m (10%), heading budget is tighter but the short distance helps; ZARU at the inevitable stop resets gyro bias.
- **Velocity/position from accel bias:** accel bias b_a double-integrates: e_pos ≈ ½·b_a·t². At b_a = 10 mg ≈ 0.098 m/s², over 60 s that's ~176 m if uncorrected — which is why you **must not** rely on double-integrated accel for speed; instead regress speed with the NN and/or use NHC+ZUPT, making along-track error driven by speed-estimate error, not accel bias.
- **Conclusion:** the benchmark is met by (1) killing heading drift (ZARU, magnetometer-weak-prior, map-matching heading), and (2) getting forward speed from the learned velocity net + NHC rather than accel integration. Attack **yaw** and **speed** — not accel bias directly.

### 8.3 Allan variance procedure for a phone IMU
Log the phone **stationary** for several hours (ideally temperature-stable), at max rate (need `HIGH_SAMPLING_RATE_SENSORS`). Compute the overlapping Allan deviation σ(τ) vs averaging time τ for each axis: the **−½ slope** region gives ARW/VRW (read σ at τ=1 s), the **flat minimum** gives bias instability (×0.664 factor), the **+½ slope** gives rate-random-walk. Use these to seed the InEKF process-noise (Q) for gyro/accel and bias random-walk. Repeat at a few temperatures to bound temp drift.

---

## Task 9 — What actually achieves the benchmark

- **Pure smartphone-IMU strapdown:** unusable within seconds–tens of seconds (IONet's motivating result; hundreds of metres error at car speeds in <1 min). Not viable alone.
- **AI-IMU (Brossard) on KITTI:** **1.10% average translational error** IMU-only over KITTI sequences — but KITTI IMU is an **automotive/industrial-grade** unit (not a phone), and it uses NHC + learned covariance in an IEKF. This is the strongest evidence the <10% (indeed <2%) target is reachable *with vehicle constraints* — the open question is the sensor grade.
- **Onyekpe INS-only (IO-VNBD, smartphone-grade channels):** up to 89.55% reduction of INS displacement error and 93.35% of orientation-rate error vs raw INS; on the quick-acceleration scenario the best NN gives max CRSE 8.62 m vs 79.05 m for raw INS over ~220 m. This is the most honest smartphone-grade vehicle benchmark; residuals degrade on roundabouts/aggressive dynamics.
- **WhONet (wheel odometry, upper bound):** 180 s outage CTE 0.49 m / CRSE 3.93 m; ~8.62 m after 5.6 km ≈ **0.15% of distance** — this is the ceiling you cannot reach without wheel speed. Use it only to contextualise: your phone-IMU-only system will land between raw-INS (bad) and WhONet (excellent).
- **Honest assessment:** **<10% of distance is achievable for tunnel/underpass scenarios (tens of seconds to ~1–2 min) with phone-grade sensors ONLY IF** you combine (a) learned forward-speed estimation, (b) NHC + ZUPT/ZARU, (c) continuous InEKF, and (d) map matching to bound cross-track error. Without map matching, expect to sometimes miss <10% on curvy tunnels/roundabouts because of heading drift. In **underground car parks (no map, longer dwell, low speed, many turns)** the target is much harder; barometer floor detection + tight NHC + loop geometry is the best you can do and drift may exceed 10% on long stays. Dominant residual error terms, in order: **(1) heading/yaw drift, (2) forward-speed estimate error, (3) phone-to-vehicle misalignment error, (4) scale factor during turns.**
- **Commercial context:** automotive dead-reckoning (u-blox, Trimble, etc.) hits <2% but uses wheel ticks/OBD and industrial IMUs — not comparable to the phone-only constraint. FOG-based systems reach <0.1%/km but at kg mass and high cost (the edge-engine target).

---

## Task 10 — Competitive & practical notes (India context)

- **NavIC/IRNSS on Android:** chipsets exposing NavIC include Qualcomm **Snapdragon 720G, 765/765G, 662, 460, 8 Gen 1**, Google **Tensor G2** (Pixel 7/7 Pro), Apple **A17 Pro** (iPhone 15 Pro). BUT a 2026 study — "Unlocking NavIC on smartphones: a technical reality check for GNSS researchers," *Remote Sensing Letters* 17(1), DOI 10.1080/2150704X.2025.2605287 — finds that "on many devices, NavIC signals (Constellation ID 7, Space Vehicle Identifiers 201–210) remain invisible or filtered out by low-level drivers even when hardware support exists," despite "the Indian government's 2025 mandate requiring NavIC compatibility"; Android's core GNSS API and logging tools **lack standardized NavIC identifiers and full dual-frequency support**. **Do not assume NavIC is usable via standard APIs** — treat it as bonus, rely on GPS/GLONASS/Galileo/BeiDou.
- **Indian OSM data quality:** generally good in metros for major roads; variable for service roads, flyover-vs-below tagging, and lane info — expect flyover/service-road ambiguity to be a real map-matching failure mode in Indian cities. Indian test sites: metro road tunnels and underpasses (Delhi, Mumbai, Bengaluru), multi-level mall/office car parks.
- **Prior competition entries:** SIH and similar GNSS-denied/inertial-nav problem statements recur; public writeups are sparse and usually not rigorous — few open repos of a full phone-only InEKF+map-matching stack exist, which is an opportunity. The strongest reusable open code is AI-IMU (mbrossar/ai-imu-dr), TLIO (CathIAS/TLIO), AirIMU (haleqiu/AirIMU), RoNIN (Sachini/ronin), WhONet & IO-VNBD (onyekpeu), GraphHopper/FMM for map matching.
- **Datasets beyond IO-VNBD** (for pretraining/augmentation):
  - **comma2k19** — 33 h highway driving, phone-grade IMU + GNSS + CAN; excellent for car-speed and GNSS-outage simulation.
  - **KITTI (raw/odometry)** — car, OXTS RT3003 IMU (industrial-grade) + GPS; used by AI-IMU; good but IMU better than a phone.
  - **Oxford RobotCar** — car, long-term, IMU+GNSS; industrial IMU.
  - **ADVIO** — authentic handheld VIO w/ ground truth (pedestrian, indoor/outdoor); phone-grade.
  - **Google Smartphone Decimeter Challenge (GSDC 2021–2023)** — Android raw GNSS + IMU from real phones in cars, incl. urban/highway; ideal for GNSS+INS fusion and NavIC-free multi-GNSS.
  - **TUM VI, EuRoC** — VIO benchmarks (handheld/drone), not vehicular/GNSS — limited relevance.
  - **RoNIN, OxIOD, RIDI, TLIO/Aria** — pedestrian, for backbone pretraining only.

---

## Recommendations (prioritized)

1. **Build one continuously-running error-state InEKF on SE₂(3)+biases** as the spine (shared C++/Rust core, JNI to Android, reused as edge engine). GNSS enters as a gated update; tunnels = no update. This gives seamless, jump-free transitions for free. **Benchmark to change course:** if InEKF tuning can't get 2-D RMSE within ~3–5× of the GNSS-available baseline during 60 s synthetic outages on IO-VNBD, revisit the constraint set before adding model complexity.
2. **Attack heading first.** Implement ZARU at every stop, weak magnetometer heading prior, and map-matching heading feedback. Instrument yaw error explicitly. This is the dominant error term against the <10% benchmark.
3. **Estimate forward speed with a learned net (TCN/1D-ResNet regressing body-frame forward velocity + covariance), fused as a pseudo-measurement** (Cortés/VeTorch pattern) — NOT double-integrated accel. Train on IO-VNBD "S-" channels + comma2k19 + GSDC; do NOT reuse RoNIN/IONet weights (gait prior). Predict covariance and feed it to the filter.
4. **Adopt AI-IMU's learned adaptive NHC covariance** (CNN outputs R_NHC per step). This is the proven mechanism that reaches 1.10% translational error on KITTI; port it to phone data.
5. **Handle arbitrary mounting via EqNIO-style equivariant canonicalisation OR in-filter R_sv estimation** (augment state, observe through turns under NHC). Add a mount-disturbance detector that re-inflates R_sv covariance.
6. **Add online HMM map matching (GraphHopper hmm-lib or FMM) over an offline OSM CSR graph**, with emission σ driven by the filter covariance and a sliding-window Viterbi committing segments >5–10 s old. This is what pushes cross-track error under 10% on curvy tunnels. For car parks (no graph), switch to barometer-floor + tight-NHC DR mode.
7. **Screening deliverable:** reproduce the Onyekpe "Learning to Localise" INS pipeline (1 s window, MAE, Adamax LR 7e-4, batch 128, NED, 10/30/60/180 s synthetic outages) on IO-VNBD **smartphone channels**, then show your InEKF+NHC+learned-speed pipeline beating it, with position plots on the mandated subset (V-St6, V-St7, V-S3a long-outage sets + a roundabout scenario). Report CTE/CRSE (their metrics) AND drift-as-%-of-distance.
8. **Deployment:** foreground service, `*_UNCALIBRATED` sensors + explicit bias states, actual timestamps, `HIGH_SAMPLING_RATE_SENSORS`; filter at IMU rate on one thread, NN at 1–10 Hz on another; TFLite/ExecuTorch FP16 (verify covariance-head accuracy before INT8); target 10 Hz output on phone, 200 Hz on the FOG edge build.

---

## Caveats
- Pedestrian-domain accuracy numbers (RoNIN/TLIO/CTIN ATE in metres) are **not comparable** to vehicle drift-%; they are included only to rank architectures, not to promise car performance.
- AI-IMU's 1.10% and WhONet's sub-1% figures use **better-than-phone sensors** (KITTI OXTS) or **wheel speed** respectively — neither is a phone-IMU-only result; do not quote them as achievable on a phone.
- IO-VNBD's WhONet paper is **internally inconsistent** on outage-sequence counts (809/399/197/129 vs 688/342/168/111) and reports a suspicious 120 s CTE tie (1.78 m for both physics and WhONet — likely a typo); verify against the tables when you cite.
- The task brief's "CTE/CRSE" labels differ from the papers' definitions (Cumulative True Error / Cumulative Root Square Error, not cross-track/ATE); align your report's terminology to avoid confusion.
- NavIC via standard Android APIs is **not reliably accessible** as of 2026 despite hardware support and government mandate; plan around GPS+GLONASS+Galileo+BeiDou.
- Several 2025–2026 architectures (FTIN, IONext, GNIO, MosaicIMU, SNN+InEKF) are recent preprints with limited independent replication — treat their headline numbers as provisional.
- The <10% benchmark in **underground multi-level car parks** (long dwell, no map, many low-speed turns) is the least certain to meet with phone-only sensors; be honest about this in the submission.