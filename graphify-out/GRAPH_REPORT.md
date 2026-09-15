# Graph Report - SIH-26168  (2026-09-15)

## Corpus Check
- 173 files · ~487,958 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2876 nodes · 5386 edges · 151 communities (125 shown, 26 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 352 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b8bc3ee0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_baselines.py
- test_se23_derivation.py
- test_filter.py
- test_harness_wiring.py
- test_protocol.py
- RecordsTest
- RateStatsTest
- 7. The phases
- FilterConfig
- InEKF
- run.py
- ndarray
- ReplayActivity
- test_mount.py
- SessionClock
- inekf.py
- cadence.py
- test_truth.py
- truth.py
- Stamp
- test_allan.py
- Method — SIH 2026, PS 26168
- load_sequence
- test_metrics.py
- Implementation Plan v2 — consolidated plan of record
- allan.py
- test_geo.py
- AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168
- overlapping_allan_deviation
- TruthPairingError
- test_android_logger_schema.py
- test_replay.py
- Decision Log
- seconds_of_day_utc
- SE₂(3) Propagation — the derivation the code is written from
- Error Budget
- main
- LoggerService
- MainActivity
- The logger
- Evaluation Protocol
- Sprint 0 — by seat · Wed 26 – Fri 28 Aug
- test_ffi_contract.py
- LeakageError
- speed_head.py
- test_leakage.py
- Submission audit
- core.py
- Sequence
- Handover — seat A, Android: the map view and production readiness
- 1. IO-VNBD — the mandated screening dataset
- octave_taus
- assert_no_leakage
- normalise
- test_baseline_training.py
- LineWriter
- LoggerState
- regress_heading_on_integrated_gyro
- train
- idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles
- AGENTS.md — PS 26168 Intelligent Dead Reckoning
- Session
- assert_feature_safe
- epoch_windows
- Working Agreements
- io_vnbd.py
- uk_utc_offset_s
- ValueError
- Glossary
- maps/ — OSM graph & HMM map matcher
- train_baseline_rnn.py
- core/ — filter core & edge engine
- fetch
- make_optimizer
- OnyekpeBaseline
- models/ — learned components
- TrajectoryRecordTest
- propagate_nominal
- data/ — gitignored
- drift_percent
- chi2_gate
- TelemetryState
- eval/ — the harness
- SessionExporterTest
- gradlew
- MapView
- Channels
- SessionExporter
- gauss_markov_bias_driving_noise
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- Timebase
- AndroidSensorBackend
- idr-26168
- MainActivity
- train_baseline_rnn.py
- _aided_filter
- NavigationScreen
- Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap
- 3. High-Value Navigation Upgrades (Detailed Specifications)
- TelemetryPanel
- gradlew
- sample_rate_hz
- assert_features_are_clean
- UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode
- 1.1 Trigger Detection Layers
- 2. Dynamic Visual State Machine
- 5. Curated Websites for UI/UX References & Design Inspiration
- _as_displayed
- HazardChips
- yaw_error
- _kotlin
- _ui_build_script
- ReconvergenceToast
- IdrMapboxNavigation
- test_every_field_the_replay_view_reads_is_a_field_the_harness_writes
- _nhc_mount_run
- test_the_headers_iovnbd_actually_ships_pass_the_guard
- test_no_logger_source_reaches_for_the_network
- test_the_replay_view_never_recomputes_a_displayed_metric
- test_the_truth_allowlist_is_a_strict_subset_of_position_and_time
- test_the_truth_track_carries_no_inertial_channel
- train
- ManeuverType
- evaluate
- android/ — foreground logger & demo UI
- uk_utc_offset_s
- OnyekpeBaseline
- TelemetryStore
- sample_rate_hz
- .aided_pass_summary
- test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window
- test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it
- test_evaluate_outage_end_to_end
- test_summary_reports_tail_not_just_mean

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 75 edges
2. `FilterConfig` - 67 edges
3. `TunnelFsm` - 57 edges
4. `evaluate_sequence()` - 43 edges
5. `Sequence` - 42 edges
6. `CourseTracker` - 41 edges
7. `TunnelFsmTest` - 41 edges
8. `CourseTrackerTest` - 38 edges
9. `Outage` - 38 edges
10. `LeakageError` - 35 edges

## Surprising Connections (you probably didn't know these)
- `test_attitude_closes_after_a_full_turn()` --calls--> `gammas()`  [EXTRACTED]
  tests/test_se23_derivation.py → core/reference/inekf.py
- `AllanCurve` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `AllanReport` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `NoiseCoefficients` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `StationarySegment` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (151 total, 26 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.06
Nodes (69): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+61 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.05
Nodes (64): a_ri(), expm_series(), g_ri(), process_noise_psd(), IMU propagation. Always runs, GNSS or not -- this is the spine.          `dt`, Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_* slic, Noise mapping, section 5.3. Columns are `[w_g, w_a, w_bg, w_ba, w_sv]`, 15 wide. (+56 more)

### Community 2 - "test_filter.py"
Cohesion: 0.04
Nodes (78): chi2_gate(), detect_mount_disturbance(), is_stationary(), nhc_is_valid(), Whether the non-holonomic constraint may be applied this step.      NHC says t, Mahalanobis gate. True means *accept* the measurement.      This single functi, Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, Re-express a covariance built on *plain* errors in the filter's right-invariant (+70 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.10
Nodes (7): axisAzimuth(), CourseTracker, FloatArray, pickReferenceAxis(), wrapAngle(), CourseTrackerTest, FloatArray

### Community 4 - "test_protocol.py"
Cohesion: 0.05
Nodes (50): AssertionError, assert_non_overlapping(), generate_outages(), mask_gnss(), ndarray, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic (+42 more)

### Community 6 - "RateStatsTest"
Cohesion: 0.06
Nodes (16): Snapshot, RateStats, Snapshot, fmt(), FloatArray, Handler, Sensor, SensorEvent (+8 more)

### Community 7 - "7. The phases"
Cohesion: 0.04
Nodes (49): 0.1 Authority order, 0. What this file is, and what it is not, 10. Stop conditions — stop immediately and report, 11. Findings — agents may append here, 1.1 The loop — every task, no exceptions, 1.2 Rules about this file itself, 1.3 Session bootstrap prompt — paste this first, every session, 1. How to follow this file (+41 more)

### Community 8 - "FilterConfig"
Cohesion: 0.05
Nodes (41): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Zero-velocity update. Observes accelerometer bias.          Uses section **7.1, Learned forward-speed pseudo-measurement with its predicted variance., The two must not drift apart: a `P0` nobody uses is documentation, not a prior., The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages, The asymmetry is measured, not assumed (D-057): gating ZUPT takes its NEES from (+33 more)

### Community 10 - "run.py"
Cohesion: 0.08
Nodes (45): mount_yaw_from_dynamics(), MountInit, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Mount yaw by least squares between the phone's horizontal specific force and the, attempt_alignment(), _check_physical(), _cumulative(), fix_course_arrays() (+37 more)

### Community 11 - "ndarray"
Cohesion: 0.08
Nodes (50): adjoint(), exp_so3(), gammas(), log_so3(), _moving_average(), propagate_nominal(), ndarray, slice (+42 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.08
Nodes (38): _cue_statistic(), _effective_samples(), orthonormalise(), pca_mount_yaw(), Nearest rotation matrix in the Frobenius sense, with the reflection branch exclu, Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, AR(1) effective sample size of a serially correlated series, never below 2., `(t, positive)` for a sign cue: how many standard errors the mean product sits f (+30 more)

### Community 14 - "SessionClock"
Cohesion: 0.08
Nodes (8): dateFormat(), SessionClock, Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, SessionClockTest, java

### Community 15 - "inekf.py"
Cohesion: 0.07
Nodes (48): The vehicle did not move over this window, so drift-% has no value (D-093)., ZeroDistanceOutage, Outage, One injected outage window, as sample indices into a sequence., Number of 1 s prediction epochs in this outage., evaluate_sequence(), Slice one outage window's epoch boundaries out of a position series.      Row, This stem cannot be graded, and the run says so rather than reporting a number a (+40 more)

### Community 16 - "cadence.py"
Cohesion: 0.07
Nodes (51): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+43 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 18 - "truth.py"
Cohesion: 0.10
Nodes (33): load_sequence(), load_split(), _preferred_copy(), Path, Load one sequence CSV.      Raises LeakageError if the file contains any disal, Pick deterministically between multiple copies of the same stem.      Every on, Load a named set of sequences from a directory. Missing files are reported toget, align_to_sequence() (+25 more)

### Community 19 - "Stamp"
Cohesion: 0.15
Nodes (12): FixVerdict, ACCEPTED, FORCED, REJECTED, TunnelFsmConfig, TunnelState, EXIT_VERIFICATION, GNSS_HEALTHY (+4 more)

### Community 20 - "test_allan.py"
Cohesion: 0.12
Nodes (33): DeviceImuSequence, is_raw_imu_sidecar(), load_raw_imu_sidecar(), DataFrame, Path, The logger's raw inertial sidecar, read for Allan variance on our own hardware., One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-sort, A raw sidecar, shaped like a `Sequence` so the Allan module needs no second code (+25 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.10
Nodes (22): drift_percent(), Final position error as a percentage of ground-truth distance travelled., (RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].      Always r, yaw_error(), Metric unit tests, each against a hand-computed case.  Every number in the sub, 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi (+14 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.10
Nodes (26): AllanCurve, analyse_segment(), bias_instability(), coefficients(), imu_arrays(), _loglog_slope(), NoiseCoefficients, octave_taus() (+18 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (23): path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t, vincenty_inverse(), wrap_to_pi() (+15 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.09
Nodes (9): MotionClassifier, MotionMode, PEDESTRIAN, UNKNOWN, VEHICLE, StepEvent, ReacquisitionSlew, MotionClassifierTest (+1 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.18
Nodes (6): androidx, MapStackHooks, ComponentActivity, MapStack, ComponentActivity, MapStack

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.12
Nodes (15): The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, The submission logger must be strictly offline (D-041). Without the permission,, D-122: the secret `sk.` downloads token lives in the per-machine Gradle user hom, Same rule as the web page: refuse the file rather than draw an older layout's fi, The one assertion here that catches a drift between two files rather than a rule, The failure D-039 and D-080 exist to prevent, asserted against the code path: th, D-126: the bundled tunnel asset JSON must parse, declare schema idr.tunnels.v1,, Every test below iterates over a dict. A rename that empties one of them would t (+7 more)

### Community 31 - "test_replay.py"
Cohesion: 0.06
Nodes (31): _date_strings(), ndarray, If this fails the fixture is wrong, and every assertion built on it means nothin, Proper right-handed triad (+gyro_yaw, -gyro_roll, +gyro_pitch) established by D-, `gps_accuracy_m` is the phone's own statement about the fix, so the covariance t, The shipped `DATE (YYYY-MO-DD HH-MI-SS_SSS)` spelling, in UK local time.      Ta, A level vehicle driving due north at a constant speed, as a `Sequence` + `TruthT, synthetic_drive() (+23 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.08
Nodes (41): FilterConfig, initial_covariance(), Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, AxisMeasurement, candidate_gyro(), _course_and_gyro(), main() (+33 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-115 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.05
Nodes (47): generate_sweep(), Synthetic GNSS-outage injection.  Protocol: docs/EVALUATION.md section 3. Leng, The full sweep across every held-out sequence, keyed by outage length.      ``, plan_sweep(), Generate and validate the outage sweep. Validation is not optional., loss_fn(), make_optimizer(), OnyekpeBaseline (+39 more)

### Community 37 - "LoggerService"
Cohesion: 0.14
Nodes (7): Handler, IBinder, Intent, Service, LoggerService, HandlerThread, PowerManager

### Community 38 - "MainActivity"
Cohesion: 0.12
Nodes (10): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout, AppCompatActivity, Bundle, Button (+2 more)

### Community 39 - "The logger"
Cohesion: 0.20
Nodes (10): Building it, Files it writes, First run, before any drive matters, One Gradle root, at `android/`, Status, The logger, The wrapper is committed, and had to be regenerated, `Unable to establish loopback connection` — it is not the JDK (+2 more)

### Community 40 - "Evaluation Protocol"
Cohesion: 0.12
Nodes (17): 1.1 Allowlist — IO-VNBD `S-` (smartphone) stream only, 1.2 Denylist — the `V-` (ECU/CAN) stream, 1.3 Enforcement, 1. Input channels, 2. Frames and ground truth, 3. Outage injection, 4.1 CTE — Cumulative True Error, 4.2 CRSE — Cumulative Root Square Error (+9 more)

### Community 41 - "Sprint 0 — by seat · Wed 26 – Fri 28 Aug"
Cohesion: 0.12
Nodes (17): A — Android, After screening, C — Field data & submission, D — Data & evaluation *(critical path — everything waits on this)*, Gate 0 — Fri 28 Aug · *the harness is trustworthy*, Gate 1 — Tue 1 Sep · *the spine holds without learning*, Gate 2 — Fri 4 Sep · *the speed head is honest about itself*, Gate 3 — Mon 7 Sep · *submission ready, one day early* (+9 more)

### Community 42 - "test_ffi_contract.py"
Cohesion: 0.12
Nodes (13): The `core/ffi/` interface definition (P-14).  There is no implementation to te, D-043 ships a definition at screening. A function body here would be the October, A surface that omits a call is a surface someone works around., The port cannot reproduce the filter's behaviour without the values it is tuned, `update_gnss` and `update_zaru` are gated (D-001, D-057) and return whether they, A rejected fix applies nothing" is the whole argument for "seamless transition w, The port happens in October, from this file, probably by someone who was not in, test_every_config_field_of_the_reference_filter_that_the_port_needs_is_present() (+5 more)

### Community 43 - "LeakageError"
Cohesion: 0.05
Nodes (52): assert_truth_only(), _last_sunday(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, uk_utc_offset_s() (+44 more)

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.13
Nodes (23): _const(), _header_from_kotlin(), _int_const(), _kotlin(), Path, The Android logger's CSV schema, checked against the loader that has to read it., The app records uncalibrated accel and gyro -- `android/README.md` requires it,, `eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a d (+15 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.13
Nodes (25): Enum, crse(), CrseConvention, cte(), evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/ (+17 more)

### Community 49 - "Sequence"
Cohesion: 0.08
Nodes (20): NavState, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Inertial feature matrix, shape (n, 15). Guarded on the way out. (+12 more)

### Community 50 - "Handover — seat A, Android: the map view and production readiness"
Cohesion: 0.10
Nodes (20): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — **built**, in `9fdd261`, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+12 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "octave_taus"
Cohesion: 0.09
Nodes (19): Bundle, Context, IBinder, Intent, Location, LocationListener, Sensor, SensorEvent (+11 more)

### Community 53 - "assert_no_leakage"
Cohesion: 0.11
Nodes (19): D-080. A renderer has no business with a random number, and neither has a view t, The specific thing that was here: a `PREVIEW_TELEMETRY` constant, rendered whene, D-126: `TunnelFsm` decides when GNSS is suppressed and when a fix counts as veri, D-126 deviation 3 / D-115: the fix applied after N consecutive rejections is on, D-124, restating D-112 for every new screen: drift is error against truth as a p, D-080 / R-B: TunnelCorridor must advance strictly on the estimator's pose clock, R-F / D-126: hazard chips are strictly limited to the declared set derived from, D-081 caption discipline: the speedometer HUD explicitly names its source ('filt (+11 more)

### Community 54 - "normalise"
Cohesion: 0.22
Nodes (10): assert_feature_safe(), Stricter guard for tensors entering a model or filter: inertial channels only., assert_features_are_clean(), Run the repo's own leakage guard over the exact columns the model is fed. Return, The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject(), The two guards have to disagree in the right direction: the truth loader may rea, test_truth_columns_can_never_become_model_features() (+2 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.12
Nodes (17): TunnelTrigger, BARO_PISTON, CHI2_FORCED, CHI2_PASS, CN0_COLLAPSE, CN0_LOST, CN0_RECOVERED, FIX_REAPPEARED (+9 more)

### Community 57 - "LoggerState"
Cohesion: 0.07
Nodes (15): ErrorEllipse, mahalanobisSquared(), sanitise(), Estimate, FloatArray, Location, LocalNavigationEstimator, toRadians() (+7 more)

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.11
Nodes (25): epoch_windows(), The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., StemWindows, validation_families(), wrap_to_pi() (+17 more)

### Community 60 - "idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles"
Cohesion: 0.17
Nodes (12): Architecture, Documentation, idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles, Non-negotiables, Quick start, Repo map, Schedule — 13 days, Six seats (+4 more)

### Community 61 - "AGENTS.md — PS 26168 Intelligent Dead Reckoning"
Cohesion: 0.20
Nodes (10): After screening, AGENTS.md — PS 26168 Intelligent Dead Reckoning, Citation hygiene, Cut list, in order, Evaluation protocol — fix before any model trains, Repo layout, Six seats, Sprints (+2 more)

### Community 62 - "Session"
Cohesion: 0.29
Nodes (4): Summary, Session, Summary, JSONObject

### Community 63 - "assert_feature_safe"
Cohesion: 0.12
Nodes (19): overlapping_allan_deviation(), random_walk_coefficient(), Overlapping Allan deviation of a rate signal.      `sigma^2(tau) = 1 / (2 tau^, Read the white-noise coefficient at tau = 1 s, and report the slope it was read, Gravity sits on the accelerometer's vertical axis at all times and must not appe, A rate random walk has slope +1/2. Its tau = 1 s value has the units of an ARW a, `sigma_min = 0.664 B`, so `B = sigma_min / 0.664`. Multiplying instead understat, Pure white noise descends monotonically, so its minimum is always the last point (+11 more)

### Community 64 - "epoch_windows"
Cohesion: 0.16
Nodes (9): InekfLocationProvider, Location, toMapboxLocation(), DeviceLocationProvider, GetLocationCallback, Job, LocationObserver, Looper (+1 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "io_vnbd.py"
Cohesion: 0.22
Nodes (8): isSpeedOverLimit(), Modifier, limitTickAngleDeg(), SpeedGaugeConstants, SpeedHud(), speedMpsToKmh(), speedToGaugeFraction(), SpeedHudTest

### Community 67 - "uk_utc_offset_s"
Cohesion: 0.23
Nodes (6): CorridorGeometry, Modifier, project(), ProjectedPoint, TunnelCorridor(), CorridorGeometryTest

### Community 68 - "ValueError"
Cohesion: 0.06
Nodes (32): 1. Design Philosophy & High-Level Vision, 1. Mobbin (The Gold Standard for Real Mobile App Flows), 2. Dynamic Visual State Machine, 2. Mapbox Navigation & Vision SDK Showcase, 3. Mappls (MapmyIndia) Official Portal & App Gallery, 3. Screen Layout Blueprint & UI Component Hierarchy, 4. Dribbble & Behance (Automotive HMI & Concept UI), 4. UI Design Token System (Theme Extensions) (+24 more)

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.25
Nodes (8): Car-park mode, Contract, Known failure modes, Library choice — **settled: build it, do not adopt one (D-036)**, maps/ — OSM graph & HMM map matcher, Status, The pipeline, as designed, What lives here

### Community 71 - "train_baseline_rnn.py"
Cohesion: 0.18
Nodes (9): Building, IDR Navigator — operator UI prototype, Installing without building, Mapbox tokens (D-122), Open work, The rules this module is held to, The tunnel machine (D-126), Two map engines, one screen (D-121) (+1 more)

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.29
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of()

### Community 74 - "make_optimizer"
Cohesion: 0.06
Nodes (40): TunnelOverride, AUTO, FORCE_OFF, FORCE_ON, Bundle, ComponentActivity, MainActivity, gyroBiasLabel() (+32 more)

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.11
Nodes (20): _approx_residuals_m(), _best_lag_s(), _nearest(), ndarray, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t, Latitude/longitude at each epoch time, shape ``(n, 2)``., Local NED positions at each epoch time, relative to the first, shape ``(n, 2)``. (+12 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.14
Nodes (15): git_sha(), make_stamp(), Path, Provenance stamping.  Every figure and table in the submission carries the com, Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes., Everything needed to regenerate an artefact., One-line stamp for a figure caption or table footer., False if this artefact came from a dirty or non-git tree. (+7 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.11
Nodes (4): FakeEditor, FakeSharedPreferences, RecentSearchesTest, SharedPreferences

### Community 81 - "chi2_gate"
Cohesion: 0.12
Nodes (22): OutageMetrics, Result for a single outage sequence. Every field is reported; none is optional., build_parser(), DroppedWindow, gate1_by_mount_class(), gate1_ratio(), ArgumentParser, Path (+14 more)

### Community 82 - "TelemetryState"
Cohesion: 0.42
Nodes (3): TelemetryState, computeActiveHazardChipLabels(), HazardChipsTest

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 86 - "MapView"
Cohesion: 0.20
Nodes (15): ImageVector, Modifier, MapControlButton(), RecenterPill(), ZoomCapsule(), ellipseGeoPoints(), getDestinationIcon(), getNumberedMarkerIcon() (+7 more)

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.09
Nodes (33): find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so, The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestam, Idling with an occupant passes the ZUPT detector and must still be excluded from (+25 more)

### Community 98 - "Timebase"
Cohesion: 0.16
Nodes (10): TunnelAssetLoader, computeCentrelineLengthM(), distanceM(), LatLon, portalDistanceM(), TunnelDef, TunnelFix, TunnelGeometry (+2 more)

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.32
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "MainActivity"
Cohesion: 0.20
Nodes (6): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Aggregate across sequences.      Reports the **median and 95th percentile** of, summarise(), The mean hides the tail and the tail is what a judge finds., test_summary_reports_tail_not_just_mean(), ValueError

### Community 107 - "train_baseline_rnn.py"
Cohesion: 0.11
Nodes (19): normalise(), Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, _canonicalise(), _distinct_fixes(), DataFrame, IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage, Normalise headers, then guard. Guard *after* normalisation so that a disguised w (+11 more)

### Community 108 - "_aided_filter"
Cohesion: 0.09
Nodes (25): _parse_local_seconds(), Make a seconds-since-midnight series monotonic across a midnight rollover., Parse the `S-` `date` column into seconds since midnight, **as shipped**., Local seconds since midnight per row, **not** unwrapped. NaN where the row does, The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-0, seconds_of_day(), seconds_of_day_utc(), unwrap_time_of_day() (+17 more)

### Community 109 - "NavigationScreen"
Cohesion: 0.12
Nodes (14): ArrivalCard(), Modifier, ExitProgressBar(), Modifier, HazardChipItem(), HazardChips(), ImageVector, Modifier (+6 more)

### Community 110 - "Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap"
Cohesion: 0.07
Nodes (27): 1.1 Trigger Detection Layers, 1.2 Finite State Machine (FSM) Specification, 1. Autonomous Tunnel & GNSS Loss Detection Engine, 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades, 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode, 3.2 Indian Driving Realities (Mappls Benchmark Upgrades), 3.3 Full Offline Navigation Stack (The Connectivity Void), 3.4 1D Manifold Map-Matching along Tunnel Centerlines (+19 more)

### Community 111 - "3. High-Value Navigation Upgrades (Detailed Specifications)"
Cohesion: 0.08
Nodes (24): Added, Added, Added, Added, Caught in review, before this build, Caught in review, before this build, Changelog — operator UI (`android-ui/`), Fixed (+16 more)

### Community 112 - "TelemetryPanel"
Cohesion: 0.15
Nodes (3): GeocodingResult, GeocodingService, GeocodingServiceTest

### Community 113 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "sample_rate_hz"
Cohesion: 0.31
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 115 - "assert_features_are_clean"
Cohesion: 0.13
Nodes (9): Fix, GnssHub, Bundle, Handler, Location, LocationListener, Summary, SatSample (+1 more)

### Community 116 - "UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode"
Cohesion: 0.15
Nodes (16): AllanReport, _fixed(), gauss_markov_bias_driving_noise(), main(), Path, Process-noise amplitude for a bias modelled as first-order Gauss-Markov., Everything one run of this module produced, ready to stamp and write., Per-axis, per-segment coefficients for one sensor, optionally white-band fits on (+8 more)

### Community 117 - "1.1 Trigger Detection Layers"
Cohesion: 0.12
Nodes (17): 10. Scratch probes — where the measurements behind D-110/D-115 live, 11. Questions nobody has answered yet, 1. What you are actually picking up, 2. The number, in the order it was measured, 3. Hard constraints — each one silently ruins the work if ignored, 4. How the harness makes the number (read before touching `eval/run.py`), 5. What D-115 already changed in the filter (so you do not redo it), 6.1 Fix 1 — a stop detector ZARU can fire from (+9 more)

### Community 118 - "2. Dynamic Visual State Machine"
Cohesion: 0.18
Nodes (15): annotateSections(), buildMergedSuggestions(), buildOfflineSuggestions(), categoryIcon(), CategoryPill, DestinationSearchBar(), iconBackground(), iconTint() (+7 more)

### Community 123 - "_as_displayed"
Cohesion: 0.33
Nodes (6): _as_displayed(), One line, with Kotlin's `"..." + "..."` joins closed up.      A caption long e, D-081, and the reason it is asserted rather than trusted: the caption is the fir, The same rule for the same reason, on the other surface. Mirrors     `test_repl, test_the_operator_ui_states_what_produced_its_numbers(), test_the_replay_caption_names_the_stream_and_the_rate_and_disclaims_200_hz()

### Community 125 - "yaw_error"
Cohesion: 0.20
Nodes (10): 1. What you are actually picking up, 2. What the two sessions changed, and why it was four separate bugs, 3. What the fix does *not* claim, 4. The APK problem — read this before promising anyone a link, 5. What is open, in order, 6. Verifying it on a phone — what to read, and what a failure looks like, 7. Where the reasoning lives, Handover — operator UI (`android-ui/`): the traced curve, and what is still wrong with it (+2 more)

### Community 126 - "_kotlin"
Cohesion: 0.40
Nodes (5): _kotlin(), Path, D-123 rule R2, the single most important line in the Mapbox integration. The SDK, Every Kotlin source under `root`, keyed by its path relative to the repo., test_the_mapbox_flavour_switches_the_sdks_own_dead_reckoning_off()

### Community 127 - "_ui_build_script"
Cohesion: 0.40
Nodes (5): Checked at the dependency rather than the call site. Downloadable fonts were a n, D-121: `osm` is the flavour CI can always build (no account, no token); `mapbox`, test_each_map_engine_is_confined_to_its_own_product_flavour(), test_the_ui_module_declares_no_play_services_or_downloaded_font_dependency(), _ui_build_script()

### Community 128 - "ReconvergenceToast"
Cohesion: 0.67
Nodes (3): formatElapsed(), Modifier, ReconvergenceToast()

### Community 130 - "test_every_field_the_replay_view_reads_is_a_field_the_harness_writes"
Cohesion: 0.50
Nodes (4): Field-by-field, against the writer's own dict literal. A renamed key on either s, The body of `eval/run.py::trajectory_record`, which is where the keys are litera, test_every_field_the_replay_view_reads_is_a_field_the_harness_writes(), _trajectory_record_source()

### Community 131 - "_nhc_mount_run"
Cohesion: 0.14
Nodes (14): GeoCoordinate, ManeuverType, ARRIVE, SLIGHT_LEFT, SLIGHT_RIGHT, STRAIGHT, TUNNEL_ENTRY, TUNNEL_EXIT (+6 more)

### Community 132 - "test_the_headers_iovnbd_actually_ships_pass_the_guard"
Cohesion: 0.09
Nodes (30): assert_no_leakage(), LeakageError, Raise LeakageError if any disallowed channel is present.      Called by the lo, A disallowed channel reached a feature path.      Deliberately an AssertionErr, Before the aliases, every one of these normalised to a name that was not on the, The aliases must not have widened the guard. These are the real 'V-' column name, test_the_headers_iovnbd_actually_ships_pass_the_guard(), test_the_v_stream_header_is_still_rejected_wholesale() (+22 more)

### Community 135 - "test_the_truth_allowlist_is_a_strict_subset_of_position_and_time"
Cohesion: 0.20
Nodes (10): closed_form_gammas(), _nees_inputs(), _nees_p0(), ndarray, The cutoff must sit where the closed form is *still accurate*, not where it is 0, The textbook expressions with no small-angle guard. Used only to show where they, The Monte-Carlo prior.      **This is the test's experimental design, not a pr, (omega, specific force, truly stopped) for step `k`: cruise, brake, stop, pull a (+2 more)

### Community 136 - "test_the_truth_track_carries_no_inertial_channel"
Cohesion: 0.25
Nodes (6): SearchPreset, SearchSource, ONLINE, PIN, PRESET, RECENT

### Community 137 - "train"
Cohesion: 0.39
Nodes (3): CsvRow, FloatArray, Records

### Community 139 - "evaluate"
Cohesion: 0.36
Nodes (7): Dp, Modifier, SwipeDirection, DOWN, UP, swipeToDismiss(), verticalSwipe()

### Community 140 - "android/ — foreground logger & demo UI"
Cohesion: 0.22
Nodes (6): android/ — foreground logger & demo UI, Contract, Demo UI, GNSS, Non-negotiable platform facts, Threading

### Community 144 - "sample_rate_hz"
Cohesion: 0.50
Nodes (4): The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a de, sample_rate_hz(), No `sample_rate_hz` attribute means 10 Hz, exactly as before this loader existed, test_an_iovnbd_sequence_still_windows_at_the_protocol_rate()

### Community 145 - ".aided_pass_summary"
Cohesion: 0.29
Nodes (6): Alignment, apply_alignment(), course_sigma_rad(), 1-sigma heading accuracy of the receiver's course at this speed.      A Dopple, One attempt's result: the vertical, the mount, and how well each is known., Write an alignment into the filter: `R_sv`, `R`, `v`, and a fresh `P` for everyt

### Community 146 - "test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window"
Cohesion: 0.29
Nodes (7): Android Demo Builds, Available Builds, Direct Mobile Download, GitHub Releases, Installation, Latest CI build, Updating this file

### Community 147 - "test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it"
Cohesion: 0.53
Nodes (5): Dp, Modifier, lonPerMetre(), MapView(), MissingTokenState()

### Community 149 - "test_evaluate_outage_end_to_end"
Cohesion: 0.50
Nodes (4): detector_settings(), The stationarity rule the segments were found under, for the summary's provenanc, The summary records the stationarity rule its segments were found under, and it, test_the_committed_artefacts_were_made_under_the_current_detector()

### Community 150 - "test_summary_reports_tail_not_just_mean"
Cohesion: 0.50
Nodes (4): _nhc_mount_run(), Straight drive at `speed` with a true 5-degree mount yaw the filter does not kno, SE_2(3) test 9. Section 7.2's `-v_veh_hat^` column made quantitative.      For, test_nhc_learns_the_mount_yaw_and_learns_it_faster_at_speed()

## Knowledge Gaps
- **486 isolated node(s):** `UNKNOWN`, `PEDESTRIAN`, `VEHICLE`, `GNSS`, `INS` (+481 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session` to `LoggerService`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `NavigationScreen()` connect `NavigationScreen` to `ReconvergenceToast`, `io_vnbd.py`, `_nhc_mount_run`, `make_optimizer`, `TelemetryState`, `sample_rate_hz`, `2. Dynamic Visual State Machine`, `HazardChips`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `SearchItem` connect `HazardChips` to `_nhc_mount_run`, `test_the_truth_track_carries_no_inertial_channel`, `ManeuverType`, `NavigationScreen`, `TelemetryPanel`, `drift_percent`, `test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it`, `2. Dynamic Visual State Machine`, `MapView`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._