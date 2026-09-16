# Graph Report - SIH 26' NEW AND FINAL  (2026-09-16)

## Corpus Check
- 186 files · ~537,750 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3059 nodes · 5867 edges · 150 communities (132 shown, 18 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 267 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1665ed1c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_baselines.py
- test_se23_derivation.py
- test_filter.py
- CourseTracker
- test_protocol.py
- RecordsTest
- RateStatsTest
- 7. The phases
- InEKF
- TunnelFsm
- run.py
- _nees_run
- ReplayActivity
- test_mount.py
- SessionClock
- inekf.py
- cadence.py
- Step 4: Mapped Corridor Verification (Simulated Local Street Run)
- test_truth.py
- TunnelState
- test_android_raw_sidecar.py
- Method — SIH 2026, PS 26168
- NavigationBottomSheet.kt
- test_metrics.py
- Implementation Plan v2 — consolidated plan of record
- allan.py
- test_geo.py
- AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168
- MotionClassifier
- main
- test_android_demo_surface.py
- test_harness_wiring.py
- Decision Log
- axis_check.py
- SE₂(3) Propagation — the derivation the code is written from
- Error Budget
- main
- LoggerService
- MainActivity
- The logger
- Evaluation Protocol
- Sprint 0 — by seat · Wed 26 – Fri 28 Aug
- test_ffi_contract.py
- test_replay.py
- gaussian_nll
- test_android_logger_schema.py
- Submission audit
- test_speed_head.py
- .features
- Handover — Android: everything left to do
- 1. IO-VNBD — the mandated screening dataset
- SensorForegroundService
- _strip_comments
- SensorHub
- GnssHub
- LineWriter
- LocalNavigationEstimator
- regress_heading_on_integrated_gyro
- test_baseline_training.py
- idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles
- AGENTS.md — PS 26168 Intelligent Dead Reckoning
- JSONObject
- normalise
- InekfLocationProvider
- Working Agreements
- SpeedHud.kt
- project
- 7. Review Inputs — Building This Plan on the Mapbox Navigation SDK for Android
- Glossary
- maps/ — OSM graph & HMM map matcher
- IDR Navigator — operator UI prototype
- core/ — filter core & edge engine
- fetch
- glassmorphic
- rocm_check.py
- models/ — learned components
- TrajectoryRecordTest
- Stamp
- data/ — gitignored
- FakeSharedPreferences
- core.py
- TelemetryState
- eval/ — the harness
- SessionExporterTest
- android/gradlew
- osm/java/com/sih/idr/demo/ui/components/MapView.kt
- Channels
- SessionExporter
- test_allan.py
- core/__init__.py
- reference/__init__.py
- eval/__init__.py
- loaders/__init__.py
- metrics/__init__.py
- outages/__init__.py
- idr/__init__.py
- models/__init__.py
- ValueError
- AndroidSensorBackend
- idr-26168
- ndarray
- _canonicalise
- TruthTrack
- NavigationScreen.kt
- Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap
- Changelog — operator UI (`android-ui/`)
- GeocodingService
- android-ui/gradlew
- GuidanceBanner.kt
- Handover — the gyro-bias block: ZARU now runs and the bias is still wrong
- demo/MainActivity.kt
- Handover — Filter & Gate 1: where the number stands and what is left
- SearchItem
- mapbox/java/com/sih/idr/demo/ui/components/MapView.kt
- _as_displayed
- Handover — ZARU gate: why 1,356 of 1,372 stops on S3a observe nothing, and the fix to measure
- Handover — operator UI (`android-ui/`): the traced curve, and what is still wrong with it
- _kotlin
- _ui_build_script
- LoggerState
- IdrMapboxNavigation.kt
- test_every_field_the_replay_view_reads_is_a_field_the_harness_writes
- NavigationRoute
- LeakageError
- parametrize
- Records
- train
- SearchPreset
- CrseConvention
- Handover — P-08: the speed + variance head, trained and calibrated (code, then a GPU run)
- MapStackHooks
- RouteTracker
- MapChrome.kt
- TelemetryStore
- Pitch Script — "Technical Approach" slide, 60 seconds
- Available Builds
- Training Environment
- train
- measured/README.md
- Hyperparameter

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 69 edges
2. `TunnelFsm` - 59 edges
3. `FilterConfig` - 54 edges
4. `CourseTracker` - 44 edges
5. `evaluate_sequence()` - 43 edges
6. `TunnelFsmTest` - 42 edges
7. `Sequence` - 39 edges
8. `CourseTrackerTest` - 38 edges
9. `synthetic_drive()` - 36 edges
10. `TelemetryState` - 34 edges

## Surprising Connections (you probably didn't know these)
- `test_attitude_closes_after_a_full_turn()` --calls--> `gammas()`  [EXTRACTED]
  tests/test_se23_derivation.py → core/reference/inekf.py
- `detector_settings()` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `course_sigma_rad()` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py
- `in_motion_config()` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py
- `_step_constraints()` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (150 total, 18 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.05
Nodes (76): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available. Gate 1 is a… (+68 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.06
Nodes (56): a_ri(), expm_series(), g_ri(), process_noise_psd(), IMU propagation. Always runs, GNSS or not -- this is the spine. `dt` comes from…, Scaling-and-squaring Taylor matrix exponential. scipy is deliberately not a…, Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_*…, Noise mapping, section 5.3. Columns are `[w_g, w_a, w_bg, w_ba, w_sv]`, 15… (+48 more)

### Community 2 - "test_filter.py"
Cohesion: 0.03
Nodes (93): chi2_gate(), detect_mount_disturbance(), initial_covariance(), is_stationary(), NavState, nhc_is_valid(), Detect a stopped vehicle for ZUPT/ZARU. Both conditions must hold: low…, Whether the non-holonomic constraint may be applied this step. NHC says the… (+85 more)

### Community 3 - "CourseTracker"
Cohesion: 0.11
Nodes (4): CourseTracker, FloatArray, CourseTrackerTest, FloatArray

### Community 4 - "test_protocol.py"
Cohesion: 0.05
Nodes (62): AssertionError, assert_non_overlapping(), generate_outages(), mask_gnss(), ndarray, Verify the non-overlap guarantee. Cheap to check, expensive to discover…, Boolean mask, True where a GNSS fix is available. The filter consumes this…, Tile a sequence with non-overlapping outages of one length. Deterministic and… (+54 more)

### Community 6 - "RateStatsTest"
Cohesion: 0.14
Nodes (4): Snapshot, RateStats, Snapshot, RateStatsTest

### Community 7 - "7. The phases"
Cohesion: 0.04
Nodes (49): 0.1 Authority order, 0. What this file is, and what it is not, 10. Stop conditions — stop immediately and report, 11. Findings — agents may append here, 1.1 The loop — every task, no exceptions, 1.2 Rules about this file itself, 1.3 Session bootstrap prompt — paste this first, every session, 1. How to follow this file (+41 more)

### Community 8 - "InEKF"
Cohesion: 0.04
Nodes (46): InEKF, Error-state Invariant EKF on SE_2(3). Sprint 1 (seat S) implements propagate()…, Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is…, Zero-velocity update. Observes accelerometer bias. Uses section **7.1**'s body-…, Zero-angular-rate update, chi-squared gated. Returns whether it was applied.…, Learned forward-speed pseudo-measurement with its predicted variance. The…, The measured failure D-053 recorded and P-04 diagnosed: `is_stationary`…, The counter D-131 fixes: S3a's aided pass offered 1,372 stops and the gate… (+38 more)

### Community 9 - "TunnelFsm"
Cohesion: 0.05
Nodes (21): TunnelFsm, TunnelFsmConfig, TunnelTransition, TunnelTrigger, BARO_PISTON, CHI2_FORCED, CHI2_PASS, CN0_COLLAPSE (+13 more)

### Community 10 - "run.py"
Cohesion: 0.04
Nodes (72): Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised. ``imu`` holds the…, Sequence, Alignment, apply_alignment(), attempt_alignment(), _check_physical(), course_sigma_rad() (+64 more)

### Community 11 - "_nees_run"
Cohesion: 0.12
Nodes (27): slice, Error-state Kalman update, with the correction **subtracted** (D-050). The sign…, Pack (R, v, p) into the 5x5 SE_2(3) matrix of section 2., se23_exp(), se23_log(), unpack(), x_of(), _nees_inputs() (+19 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.09
Nodes (18): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, SeekBar, Canvas (+10 more)

### Community 13 - "test_mount.py"
Cohesion: 0.07
Nodes (42): exp_so3(), log_so3(), propagate_nominal(), Rodrigues. Gamma_0 *is* the SO(3) exponential., Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler…, _drive_with_a_knock(), _driving_specific_force(), parametrize (+34 more)

### Community 14 - "SessionClock"
Cohesion: 0.08
Nodes (7): SessionClock, Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, SessionClockTest, java

### Community 15 - "inekf.py"
Cohesion: 0.06
Nodes (46): adjoint(), _cue_statistic(), _effective_samples(), gammas(), mount_yaw_from_dynamics(), MountInit, _moving_average(), orthonormalise() (+38 more)

### Community 16 - "cadence.py"
Cohesion: 0.07
Nodes (41): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth.… (+33 more)

### Community 17 - "Step 4: Mapped Corridor Verification (Simulated Local Street Run)"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 18 - "test_truth.py"
Cohesion: 0.03
Nodes (121): load_sequence(), Load one sequence CSV. Raises LeakageError if the file contains any disallowed…, align_to_sequence(), assert_truth_only(), _last_sunday(), load_truth(), manifest_path_for(), _nearest() (+113 more)

### Community 19 - "TunnelState"
Cohesion: 0.23
Nodes (10): TunnelState, EXIT_VERIFICATION, GNSS_HEALTHY, PRE_ARMED_ENTRY, SEAMLESS_RECONVERGENCE, TUNNEL_ACTIVE_IDR, HazardChipItem(), HazardChips() (+2 more)

### Community 20 - "test_android_raw_sidecar.py"
Cohesion: 0.11
Nodes (35): DeviceImuSequence, is_raw_imu_sidecar(), load_raw_imu_sidecar(), DataFrame, Path, The logger's raw inertial sidecar, read for Allan variance on our own hardware.…, One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-…, A raw sidecar, shaped like a `Sequence` so the Allan module needs no second… (+27 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 22 - "NavigationBottomSheet.kt"
Cohesion: 0.13
Nodes (18): MotionMode, PEDESTRIAN, UNKNOWN, VEHICLE, TunnelOverride, AUTO, FORCE_OFF, FORCE_ON (+10 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.10
Nodes (24): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres. Signed…, Metric unit tests, each against a hand-computed case. Every number in the…, 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a…, An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26. Getting this…, 60 s outage, 10 m/s, perfect heading, 2% under-prediction of distance. Truth:…, Three epochs, each under-predicted by 1 m along-track. Hand-computed: per-epoch… (+16 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.05
Nodes (59): AllanCurve, AllanReport, analyse_segment(), bias_instability(), coefficients(), detector_settings(), _fixed(), gauss_markov_bias_driving_noise() (+51 more)

### Community 26 - "test_geo.py"
Cohesion: 0.12
Nodes (24): path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and…, Wrap an angle in radians to (-pi, pi]. Yaw error is meaningless unwrapped: an…, Geodesic distance in metres between two WGS-84 points. Returns 0.0 for…, Cumulative geodesic path length in metres along a fix sequence. This is the…, vincenty_inverse(), wrap_to_pi() (+16 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "MotionClassifier"
Cohesion: 0.10
Nodes (5): MotionClassifier, StepEvent, ReacquisitionSlew, MotionClassifierTest, ReacquisitionSlewTest

### Community 29 - "main"
Cohesion: 0.21
Nodes (12): audit_table(), build_parser(), _export_fp16(), main(), plot_calibration(), ArgumentParser, Path, Return the stated-versus-chosen P-08 training settings. (+4 more)

### Community 30 - "test_android_demo_surface.py"
Cohesion: 0.14
Nodes (13): The two Android surfaces, held to the rules `tests/test_replay.py` holds the…, The submission logger must be strictly offline (D-041). Without the permission,…, Same rule as the web page: refuse the file rather than draw an older layout's…, The one assertion here that catches a drift between two files rather than a…, The failure D-039 and D-080 exist to prevent, asserted against the code path:…, D-126: the bundled tunnel asset JSON must parse, declare schema idr.tunnels.v1,…, Every test below iterates over a dict. A rename that empties one of them would…, test_both_modules_are_present_so_an_empty_glob_cannot_pass_this_file() (+5 more)

### Community 31 - "test_harness_wiring.py"
Cohesion: 0.04
Nodes (103): OutageMetrics, Result for a single outage sequence. Every field is reported; none is optional., assert_uniform_grid(), DroppedWindow, evaluate_sequence(), fix_arrays(), gate1_by_mount_class(), gate1_ratio() (+95 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "axis_check.py"
Cohesion: 0.11
Nodes (26): AxisMeasurement, candidate_gyro(), _course_and_gyro(), main(), measure(), ndarray, Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it…, `(course_rate, gyro_mean, course_change, gyro_integral, keep)` over fix… (+18 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-115 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.11
Nodes (22): audit_table(), build_parser(), main(), _median(), ArgumentParser, Median, not mean: the protocol reports drift % as median and p95…, The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in…, The Onyekpe reproduction's hyperparameter audit (P-06). Tests the *audit*, not… (+14 more)

### Community 37 - "LoggerService"
Cohesion: 0.15
Nodes (8): Handler, IBinder, Intent, Service, LoggerService, HandlerThread, Notification, PowerManager

### Community 38 - "MainActivity"
Cohesion: 0.24
Nodes (5): AppCompatActivity, Bundle, Button, TextView, MainActivity

### Community 39 - "The logger"
Cohesion: 0.12
Nodes (16): android/ — foreground logger & demo UI, Building it, Contract, Demo UI, Files it writes, First run, before any drive matters, GNSS, Non-negotiable platform facts (+8 more)

### Community 40 - "Evaluation Protocol"
Cohesion: 0.12
Nodes (17): 1.1 Allowlist — IO-VNBD `S-` (smartphone) stream only, 1.2 Denylist — the `V-` (ECU/CAN) stream, 1.3 Enforcement, 1. Input channels, 2. Frames and ground truth, 3. Outage injection, 4.1 CTE — Cumulative True Error, 4.2 CRSE — Cumulative Root Square Error (+9 more)

### Community 41 - "Sprint 0 — by seat · Wed 26 – Fri 28 Aug"
Cohesion: 0.12
Nodes (17): A — Android, After screening, C — Field data & submission, D — Data & evaluation *(critical path — everything waits on this)*, Gate 0 — Fri 28 Aug · *the harness is trustworthy*, Gate 1 — Tue 1 Sep · *the spine holds without learning*, Gate 2 — Fri 4 Sep · *the speed head is honest about itself*, Gate 3 — Mon 7 Sep · *submission ready, one day early* (+9 more)

### Community 42 - "test_ffi_contract.py"
Cohesion: 0.12
Nodes (14): parametrize, The `core/ffi/` interface definition (P-14). There is no implementation to…, D-043 ships a definition at screening. A function body here would be the…, A surface that omits a call is a surface someone works around., The port cannot reproduce the filter's behaviour without the values it is tuned…, `update_gnss` and `update_zaru` are gated (D-001, D-057) and return whether…, A rejected fix applies nothing" is the whole argument for "seamless transition…, The port happens in October, from this file, probably by someone who was not in… (+6 more)

### Community 43 - "test_replay.py"
Cohesion: 0.08
Nodes (17): The replay renderer (P-13) and the artefact it reads. Two things are tested,…, The drift-and-crash case: a renamed field renders as `undefined` and the page…, `length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page…, No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot…, It has to survive someone editing the page a month from now without this…, The specific failure D-039 exists to prevent. Asserted against the code path:…, Drift-% and yaw error come out of the artefact. If the page computed them it…, A screenshot of the demo has to be self-evidencing (H-5), and an artefact from… (+9 more)

### Community 44 - "gaussian_nll"
Cohesion: 0.16
Nodes (14): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU…, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at…, Dilated causal conv block. Causal because at deployment there is no future…, TCN regressing (forward speed, log-variance) from a body-frame IMU window.…, Heteroscedastic Gaussian NLL: the loss that makes the variance head mean… (+6 more)

### Community 46 - "test_android_logger_schema.py"
Cohesion: 0.13
Nodes (23): _const(), _header_from_kotlin(), _int_const(), _kotlin(), Path, The Android logger's CSV schema, checked against the loader that has to read…, The app records uncalibrated accel and gyro -- `android/README.md` requires it,…, `eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a… (+15 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "test_speed_head.py"
Cohesion: 0.17
Nodes (12): assert_features_are_clean(), monotonic_prefix_length(), Run the guard over exactly the columns about to enter the model tensor., Length through the first 10 Hz monotonic prefix of a sequence. ``M``, ``S2``…, _LinearTruth, ndarray, P-08's NumPy-only contracts: labels, leakage, calibration, and no-torch…, A one-metre-per-second northbound truth track for direct window-label checks. (+4 more)

### Community 49 - ".features"
Cohesion: 0.29
Nodes (4): ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix. Fixes are…

### Community 50 - "Handover — Android: everything left to do"
Cohesion: 0.10
Nodes (20): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — **built**, in `9fdd261`, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+12 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "SensorForegroundService"
Cohesion: 0.06
Nodes (22): EtaPaceModel, Bundle, Context, IBinder, Intent, Location, LocationListener, Sensor (+14 more)

### Community 53 - "_strip_comments"
Cohesion: 0.13
Nodes (15): The specific thing that was here: a `PREVIEW_TELEMETRY` constant, rendered…, D-126: `TunnelFsm` decides when GNSS is suppressed and when a fix counts as…, D-126 deviation 3 / D-115: the fix applied after N consecutive rejections is on…, D-080 / R-B: TunnelCorridor must advance strictly on the estimator's pose clock…, R-F / D-126: hazard chips are strictly limited to the declared set derived from…, D-081 caption discipline: the speedometer HUD explicitly names its source…, D-126: TunnelGeometry must remain pure Kotlin without Android framework…, _strip_comments() (+7 more)

### Community 54 - "SensorHub"
Cohesion: 0.13
Nodes (12): FloatArray, Handler, Sensor, SensorEvent, SensorEventListener, Snapshot, RawSample, SensorDescriptor (+4 more)

### Community 55 - "GnssHub"
Cohesion: 0.13
Nodes (10): Fix, GnssHub, Bundle, Handler, Location, LocationListener, Summary, SatSample (+2 more)

### Community 57 - "LocalNavigationEstimator"
Cohesion: 0.08
Nodes (14): ErrorEllipse, mahalanobisSquared(), sanitise(), Estimate, FloatArray, Location, LocalNavigationEstimator, toRadians() (+6 more)

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`. The column that is…, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the…, Heading change and integrated yaw rate are the same angle, so the slope is…, A column carrying the negated yaw rate fits at slope -1, not +1. The sign is…, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1. Noise…, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "test_baseline_training.py"
Cohesion: 0.11
Nodes (21): assert_features_are_clean(), The held-back families, by a stated rule rather than by choice (D-098). Whole…, Run the repo's own leakage guard over the exact columns the model is fed.…, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3). The three…, 0-1 feature scaling, fitted on the training windows **only** (D-071). The…, Scaler, StemWindows, validation_families() (+13 more)

### Community 60 - "idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles"
Cohesion: 0.17
Nodes (12): Architecture, Documentation, idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles, Non-negotiables, Quick start, Repo map, Schedule — 13 days, Six seats (+4 more)

### Community 61 - "AGENTS.md — PS 26168 Intelligent Dead Reckoning"
Cohesion: 0.20
Nodes (10): After screening, AGENTS.md — PS 26168 Intelligent Dead Reckoning, Citation hygiene, Cut list, in order, Evaluation protocol — fix before any model trains, Repo layout, Six seats, Sprints (+2 more)

### Community 62 - "JSONObject"
Cohesion: 0.22
Nodes (4): Summary, Session, Summary, JSONObject

### Community 63 - "normalise"
Cohesion: 0.15
Nodes (13): normalise(), Normalise a raw CSV header to our canonical snake_case form. AndroSensor…, Generic paren-stripping collapsed all three to the single name 'orientation'., The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder…, Time Since Start of Day (seconds)' is a 'V-' column and a different quantity.…, test_a_truncated_date_format_string_still_normalises(), test_both_shipped_gyro_spellings_reach_the_same_canonical_names(), test_the_satellite_column_ships_with_and_without_the_gps_prefix() (+5 more)

### Community 64 - "InekfLocationProvider"
Cohesion: 0.21
Nodes (9): InekfLocationProvider, Location, toMapboxLocation(), DeviceLocationProvider, GetLocationCallback, Job, LocationObserver, Looper (+1 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "SpeedHud.kt"
Cohesion: 0.23
Nodes (8): isSpeedOverLimit(), Modifier, limitTickAngleDeg(), SpeedGaugeConstants, SpeedHud(), speedMpsToKmh(), speedToGaugeFraction(), SpeedHudTest

### Community 67 - "project"
Cohesion: 0.24
Nodes (6): CorridorGeometry, Modifier, project(), ProjectedPoint, TunnelCorridor(), CorridorGeometryTest

### Community 68 - "7. Review Inputs — Building This Plan on the Mapbox Navigation SDK for Android"
Cohesion: 0.06
Nodes (32): 1. Design Philosophy & High-Level Vision, 1. Mobbin (The Gold Standard for Real Mobile App Flows), 2. Dynamic Visual State Machine, 2. Mapbox Navigation & Vision SDK Showcase, 3. Mappls (MapmyIndia) Official Portal & App Gallery, 3. Screen Layout Blueprint & UI Component Hierarchy, 4. Dribbble & Behance (Automotive HMI & Concept UI), 4. UI Design Token System (Theme Extensions) (+24 more)

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.25
Nodes (8): Car-park mode, Contract, Known failure modes, Library choice — **settled: build it, do not adopt one (D-036)**, maps/ — OSM graph & HMM map matcher, Status, The pipeline, as designed, What lives here

### Community 71 - "IDR Navigator — operator UI prototype"
Cohesion: 0.18
Nodes (9): Building, IDR Navigator — operator UI prototype, Installing without building, Mapbox tokens (D-122), Open work, The rules this module is held to, The tunnel machine (D-126), Two map engines, one screen (D-121) (+1 more)

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.33
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every…, Download to a .part file and rename on success, so an interrupted run leaves no…, sha256_of()

### Community 74 - "glassmorphic"
Cohesion: 0.14
Nodes (23): ExitProgressBar(), Modifier, Modifier, MetricCard(), TelemetryPanel(), glassBorderBrush(), glassmorphic(), IDRAnimations (+15 more)

### Community 75 - "rocm_check.py"
Cohesion: 0.18
Nodes (17): benchmark(), collect(), deterministic_matmul(), HostReport, is_wsl(), main(), probe_torch(), Training-host probe. python -m models.rocm_check python -m models.rocm_check… (+9 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "Stamp"
Cohesion: 0.15
Nodes (12): git_sha(), make_stamp(), Path, Provenance stamping. Every figure and table in the submission carries the…, Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes.…, Everything needed to regenerate an artefact., One-line stamp for a figure caption or table footer., False if this artefact came from a dirty or non-git tree. (+4 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "FakeSharedPreferences"
Cohesion: 0.12
Nodes (4): FakeEditor, FakeSharedPreferences, RecentSearchesTest, SharedPreferences

### Community 81 - "core.py"
Cohesion: 0.19
Nodes (17): crse(), drift_percent(), evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission. Read…, Signed per-epoch displacement error in metres, one value per 1 s prediction…, Cumulative Root Square Error, in metres. See CrseConvention for which reading… (+9 more)

### Community 82 - "TelemetryState"
Cohesion: 0.41
Nodes (4): TelemetryState, TunnelFix, computeActiveHazardChipLabels(), HazardChipsTest

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "android/gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 86 - "osm/java/com/sih/idr/demo/ui/components/MapView.kt"
Cohesion: 0.28
Nodes (13): ellipseGeoPoints(), getDestinationIcon(), getNumberedMarkerIcon(), getVehicleIcon(), Context, Dp, Modifier, MapView() (+5 more)

### Community 89 - "test_allan.py"
Cohesion: 0.06
Nodes (51): FilterConfig, Tuning. Process noise is seeded from a measured Allan-variance run, never…, find_stationary_segments(), The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a…, Find stretches long and clean enough to compute an Allan curve on. Stationarity…, sample_rate_hz(), skipif, ndarray (+43 more)

### Community 98 - "ValueError"
Cohesion: 0.17
Nodes (7): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated.…, Vincenty path length between two times, in metres. The `L` in drift-%. Path…, Aggregate across sequences. Reports the **median and 95th percentile** of…, summarise(), The mean hides the tail and the tail is what a judge finds., test_summary_reports_tail_not_just_mean(), ValueError

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.36
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "ndarray"
Cohesion: 0.20
Nodes (10): calibration_summary(), _evaluate_arrays(), per_stem_summary(), ndarray, Per-channel 0--1 scaler fitted only from the training windows (D-071)., Coverage-first calibration and sharpness statistics, independent of torch., Apply :func:`calibration_summary` per held-out stem., Run a fitted torch model and bring its two outputs back to NumPy. (+2 more)

### Community 107 - "_canonicalise"
Cohesion: 0.40
Nodes (5): _canonicalise(), _distinct_fixes(), DataFrame, Normalise headers, then guard. Guard *after* normalisation so that a disguised…, One row per GPS position change, carrying its timestamp and IMU sample index.

### Community 108 - "TruthTrack"
Cohesion: 0.13
Nodes (15): _approx_residuals_m(), _best_lag_s(), ndarray, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else.…, Nearest-sample indices for a set of epoch times. Raises if any is further than…, Latitude/longitude at each epoch time, shape ``(n, 2)``., Local NED positions at each epoch time, relative to the first, shape ``(n, 2)``., Per-epoch NED *displacements*, shape ``(n-1, 2)``. This is what… (+7 more)

### Community 109 - "NavigationScreen.kt"
Cohesion: 0.17
Nodes (17): TunnelExitSummary, ArrivalCard(), Modifier, formatElapsed(), Modifier, ReconvergenceToast(), Dp, Modifier (+9 more)

### Community 110 - "Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap"
Cohesion: 0.07
Nodes (27): 1.1 Trigger Detection Layers, 1.2 Finite State Machine (FSM) Specification, 1. Autonomous Tunnel & GNSS Loss Detection Engine, 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades, 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode, 3.2 Indian Driving Realities (Mappls Benchmark Upgrades), 3.3 Full Offline Navigation Stack (The Connectivity Void), 3.4 1D Manifold Map-Matching along Tunnel Centerlines (+19 more)

### Community 111 - "Changelog — operator UI (`android-ui/`)"
Cohesion: 0.07
Nodes (27): Added, Added, Added, Added, Added, Caught in review, before this build, Caught in review, before this build, Changelog — operator UI (`android-ui/`) (+19 more)

### Community 112 - "GeocodingService"
Cohesion: 0.12
Nodes (3): GeocodingResult, GeocodingService, GeocodingServiceTest

### Community 113 - "android-ui/gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "GuidanceBanner.kt"
Cohesion: 0.33
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 115 - "Handover — the gyro-bias block: ZARU now runs and the bias is still wrong"
Cohesion: 0.20
Nodes (10): 0. Parallel-work protocol, 1. The problem, in numbers you can re-derive, 2. What a legitimate fix looks like — and three traps in it, 3. Files, tests, and what pins what, 4. Acceptance — D-133 in the D-130 / D-131 format, 5. Probes that already exist — copy, fix one path line, do not rewrite, 6. Commands, 7. Time budget and the stop rule (+2 more)

### Community 116 - "demo/MainActivity.kt"
Cohesion: 0.29
Nodes (5): Bundle, ComponentActivity, MainActivity, ExtendedColors, NavigatorTheme()

### Community 117 - "Handover — Filter & Gate 1: where the number stands and what is left"
Cohesion: 0.12
Nodes (17): 10. Scratch probes — where the measurements behind D-110/D-115 live, 11. Questions nobody has answered yet, 1. What you are actually picking up, 2. The number, in the order it was measured, 3. Hard constraints — each one silently ruins the work if ignored, 4. How the harness makes the number (read before touching `eval/run.py`), 5. What D-115 already changed in the filter (so you do not redo it), 6.1 Fix 1 — a stop detector ZARU can fire from (+9 more)

### Community 118 - "SearchItem"
Cohesion: 0.18
Nodes (17): RecentSearches, SearchItem, annotateSections(), buildMergedSuggestions(), buildOfflineSuggestions(), categoryIcon(), CategoryPill, DestinationSearchBar() (+9 more)

### Community 122 - "mapbox/java/com/sih/idr/demo/ui/components/MapView.kt"
Cohesion: 0.36
Nodes (7): Dp, Modifier, lonPerMetre(), MapView(), OnMoveListener, MissingTokenState(), MoveGestureDetector

### Community 123 - "_as_displayed"
Cohesion: 0.33
Nodes (6): _as_displayed(), One line, with Kotlin's `"..." + "..."` joins closed up. A caption long enough…, D-081, and the reason it is asserted rather than trusted: the caption is the…, The same rule for the same reason, on the other surface. Mirrors…, test_the_operator_ui_states_what_produced_its_numbers(), test_the_replay_caption_names_the_stream_and_the_rate_and_disclaims_200_hz()

### Community 124 - "Handover — ZARU gate: why 1,356 of 1,372 stops on S3a observe nothing, and the fix to measure"
Cohesion: 0.20
Nodes (10): 0. Parallel-work protocol (both handovers carry this section verbatim), 1. The problem, in numbers you can re-derive, 2. What a legitimate fix looks like — and the trap in it, 3. Files, tests, and what pins what, 4. Acceptance — D-131 in the D-130 format, 5. Probes that already exist — copy, fix one `sys.path` line, do not rewrite, 6. Commands, 7. Time budget and the stop rule (+2 more)

### Community 125 - "Handover — operator UI (`android-ui/`): the traced curve, and what is still wrong with it"
Cohesion: 0.20
Nodes (10): 1. What you are actually picking up, 2. What the two sessions changed, and why it was four separate bugs, 3. What the fix does *not* claim, 4. The APK problem — read this before promising anyone a link, 5. What is open, in order, 6. Verifying it on a phone — what to read, and what a failure looks like, 7. Where the reasoning lives, Handover — operator UI (`android-ui/`): the traced curve, and what is still wrong with it (+2 more)

### Community 126 - "_kotlin"
Cohesion: 0.40
Nodes (5): _kotlin(), Path, D-123 rule R2, the single most important line in the Mapbox integration. The…, Every Kotlin source under `root`, keyed by its path relative to the repo. Keys…, test_the_mapbox_flavour_switches_the_sdks_own_dead_reckoning_off()

### Community 127 - "_ui_build_script"
Cohesion: 0.40
Nodes (5): Checked at the dependency rather than the call site. Downloadable fonts were a…, D-121: `osm` is the flavour CI can always build (no account, no token);…, test_each_map_engine_is_confined_to_its_own_product_flavour(), test_the_ui_module_declares_no_play_services_or_downloaded_font_dependency(), _ui_build_script()

### Community 128 - "LoggerState"
Cohesion: 0.29
Nodes (5): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout

### Community 129 - "IdrMapboxNavigation.kt"
Cohesion: 0.32
Nodes (4): IdrMapboxNavigation, Context, ComponentActivity, MapStack

### Community 130 - "test_every_field_the_replay_view_reads_is_a_field_the_harness_writes"
Cohesion: 0.50
Nodes (4): Field-by-field, against the writer's own dict literal. A renamed key on either…, The body of `eval/run.py::trajectory_record`, which is where the keys are…, test_every_field_the_replay_view_reads_is_a_field_the_harness_writes(), _trajectory_record_source()

### Community 131 - "NavigationRoute"
Cohesion: 0.10
Nodes (17): GeoCoordinate, ManeuverType, ARRIVE, SLIGHT_LEFT, SLIGHT_RIGHT, STRAIGHT, TUNNEL_ENTRY, TUNNEL_EXIT (+9 more)

### Community 132 - "LeakageError"
Cohesion: 0.08
Nodes (38): assert_feature_safe(), assert_no_leakage(), LeakageError, Channel allowlist and the leakage guard. PS 26168 disallows wheel odometry. IO-…, Raise LeakageError if any disallowed channel is present. Called by the loader…, Stricter guard for tensors entering a model or filter: inertial channels only.…, A disallowed channel reached a feature path. Deliberately an AssertionError…, Before the aliases, every one of these normalised to a name that was not on the… (+30 more)

### Community 133 - "parametrize"
Cohesion: 0.18
Nodes (11): parametrize, D-041 claims 100% offline for the evaluation logger (android/). The harness and…, D-122: the secret `sk.` downloads token lives in the per-machine Gradle user…, Drift-% and yaw error are computed in `eval/run.py::trajectory_record` and read…, D-080. A renderer has no business with a random number, and neither has a view…, D-124, restating D-112 for every new screen: drift is error against truth as a…, test_no_android_surface_carries_a_random_number_generator(), test_no_logger_source_reaches_for_the_network() (+3 more)

### Community 134 - "Records"
Cohesion: 0.39
Nodes (3): CsvRow, FloatArray, Records

### Community 135 - "train"
Cohesion: 0.15
Nodes (12): loss_fn(), make_optimizer(), OnyekpeBaseline, Tensor, Onyekpe "Learning to Localise" INS baseline -- the number we must beat.…, Vanilla RNN correcting INS displacement error and orientation-rate error. Input…, Should land near the published ~8,200. A large divergence means the…, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the… (+4 more)

### Community 136 - "SearchPreset"
Cohesion: 0.25
Nodes (6): SearchPreset, SearchSource, ONLINE, PIN, PRESET, RECENT

### Community 137 - "CrseConvention"
Cohesion: 0.25
Nodes (8): Enum, CrseConvention, How "Cumulative Root Square Error" is read. **Settled against the paper** --…, str, Hand-computed on four epochs of exactly 1 m error each. Was a two-way test…, D-054. The default is what every unqualified call in the harness gets, so pin…, test_crse_default_is_the_papers_equation_16(), test_the_three_crse_conventions_are_all_distinct()

### Community 138 - "Handover — P-08: the speed + variance head, trained and calibrated (code, then a GPU run)"
Cohesion: 0.22
Nodes (9): 0. Parallel-work protocol (both handovers carry this section verbatim), 1. What P-08 is, and the one rule that scopes it, 2. What already exists — read before writing anything, 3. The design decisions the script has to make — with the evidence already on file, 4. Environment — what actually runs on this box (verified 15 Sep), 5. Deliverables, 6. Time budget, 7. Questions this work will answer (put the answers in D-132) (+1 more)

### Community 139 - "MapStackHooks"
Cohesion: 0.33
Nodes (4): androidx, MapStackHooks, ComponentActivity, MapStack

### Community 142 - "MapChrome.kt"
Cohesion: 0.53
Nodes (5): ImageVector, Modifier, MapControlButton(), RecenterPill(), ZoomCapsule()

### Community 143 - "TelemetryStore"
Cohesion: 0.15
Nodes (6): StateFlow, NavigationMode, GNSS, INIT, INS, TelemetryStore

### Community 144 - "Pitch Script — "Technical Approach" slide, 60 seconds"
Cohesion: 0.50
Nodes (4): Delivery notes, Pitch Script — "Technical Approach" slide, 60 seconds, Script A — English (151 words, ~58 s), Script B — Hinglish (150 words, ~58 s)

### Community 146 - "Available Builds"
Cohesion: 0.29
Nodes (7): Android Demo Builds, Available Builds, Direct Mobile Download, GitHub Releases, Installation, Latest CI build, Updating this file

### Community 147 - "Training Environment"
Cohesion: 0.25
Nodes (8): 1. The host, 2. Install, 3. Verify, 4. What actually uses the GPU today: nothing, 5. Determinism, and what a GPU number may be used for, 6. What is allowed to train right now, 7. Known failure modes, Training Environment

### Community 148 - "train"
Cohesion: 0.21
Nodes (11): _choose_target(), One stem's feature windows and truth-derived targets. ``absolute_speed_mps`` is…, Hold back complete TRAIN families using P-06's deterministic D-098 rule., Concatenate a group of stems after selecting its target and valid delta labels., Fit a target-specific head and retain the weights with the lowest validation…, Train absolute speed first; use its held-back comparison to decide P-08's…, SpeedWindows, _stack() (+3 more)

## Knowledge Gaps
- **526 isolated node(s):** `UNKNOWN`, `PEDESTRIAN`, `VEHICLE`, `GNSS`, `INS` (+521 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SensorForegroundService` connect `SensorForegroundService` to `NavigationRoute`, `TunnelFsm`, `demo/MainActivity.kt`, `SensorHub`, `GnssHub`, `LocalNavigationEstimator`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `FilterConfig` connect `test_allan.py` to `test_baselines.py`, `test_se23_derivation.py`, `test_filter.py`, `axis_check.py`, `InEKF`, `run.py`, `test_ffi_contract.py`, `_nees_run`, `test_mount.py`, `inekf.py`, `allan.py`, `test_harness_wiring.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `LocalNavigationEstimator` connect `LocalNavigationEstimator` to `CourseTracker`, `NavigationScreen.kt`, `TunnelState`, `SensorForegroundService`, `MotionClassifier`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `InEKF` (e.g. with `apply_alignment()` and `attempt_alignment()`) actually correct?**
  _`InEKF` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 55 inferred relationships involving `ValueError` (e.g. with `expm_series()` and `.propagate()`) actually correct?**
  _`ValueError` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `FilterConfig` (e.g. with `detector_settings()` and `course_sigma_rad()`) actually correct?**
  _`FilterConfig` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `UNKNOWN`, `PEDESTRIAN`, `VEHICLE` to the rest of the system?**
  _526 weakly-connected nodes found - possible documentation gaps or missing edges._