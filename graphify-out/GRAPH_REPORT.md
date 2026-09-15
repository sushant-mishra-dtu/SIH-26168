# Graph Report - SIH-26168  (2026-09-15)

## Corpus Check
- 184 files · ~530,629 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3025 nodes · 5695 edges · 157 communities (128 shown, 29 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 372 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9480d349`
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
- uk_utc_offset_s
- OnyekpeBaseline
- TelemetryStore
- sample_rate_hz
- .aided_pass_summary
- test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window
- test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it
- test_the_doppler_velocity_is_along_and_across_the_course
- test_evaluate_outage_end_to_end
- test_summary_reports_tail_not_just_mean
- octave_taus
- wrap_to_pi
- Scaler
- README.md
- Hyperparameter
- test_white_noise_gives_the_analytic_allan_deviation

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 78 edges
2. `FilterConfig` - 69 edges
3. `TunnelFsm` - 57 edges
4. `evaluate_sequence()` - 43 edges
5. `Sequence` - 42 edges
6. `CourseTracker` - 41 edges
7. `TunnelFsmTest` - 41 edges
8. `Outage` - 39 edges
9. `CourseTrackerTest` - 38 edges
10. `synthetic_drive()` - 36 edges

## Surprising Connections (you probably didn't know these)
- `AllanCurve` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `AllanReport` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `NoiseCoefficients` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `StationarySegment` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `AxisMeasurement` --uses--> `FilterConfig`  [INFERRED]
  eval/axis_check.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (157 total, 29 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.05
Nodes (76): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+68 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.05
Nodes (75): a_ri(), adjoint(), expm_series(), g_ri(), gammas(), Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, Section 2.1. Used by the GNSS update to move a left-invariant observation into t, The hat map: `skew(a) @ b == np.cross(a, b)`. (+67 more)

### Community 2 - "test_filter.py"
Cohesion: 0.04
Nodes (77): detect_mount_disturbance(), initial_covariance(), is_stationary(), nhc_is_valid(), Whether the non-holonomic constraint may be applied this step.      NHC says t, Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, Re-express a covariance built on *plain* errors in the filter's right-invariant (+69 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.10
Nodes (7): axisAzimuth(), CourseTracker, FloatArray, pickReferenceAxis(), wrapAngle(), CourseTrackerTest, FloatArray

### Community 4 - "test_protocol.py"
Cohesion: 0.06
Nodes (39): AssertionError, generate_outages(), mask_gnss(), ndarray, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic, assert_no_family_straddles_the_split(), assert_split_disjoint() (+31 more)

### Community 5 - "RecordsTest"
Cohesion: 0.08
Nodes (14): Fix, GnssHub, Bundle, Handler, Location, LocationListener, Summary, SatSample (+6 more)

### Community 6 - "RateStatsTest"
Cohesion: 0.06
Nodes (16): Snapshot, RateStats, Snapshot, fmt(), FloatArray, Handler, Sensor, SensorEvent (+8 more)

### Community 7 - "7. The phases"
Cohesion: 0.04
Nodes (49): 0.1 Authority order, 0. What this file is, and what it is not, 10. Stop conditions — stop immediately and report, 11. Findings — agents may append here, 1.1 The loop — every task, no exceptions, 1.2 Rules about this file itself, 1.3 Session bootstrap prompt — paste this first, every session, 1. How to follow this file (+41 more)

### Community 8 - "FilterConfig"
Cohesion: 0.04
Nodes (46): InEKF, Per-axis ZARU measurement sigma, read from the stop detector's own window (D-131, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Zero-velocity update. Observes accelerometer bias.          Uses section **7.1, Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Learned forward-speed pseudo-measurement with its predicted variance., zaru_sigma_from_window() (+38 more)

### Community 10 - "run.py"
Cohesion: 0.05
Nodes (70): FilterConfig, Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, assert_non_overlapping(), generate_sweep(), Synthetic GNSS-outage injection.  Protocol: docs/EVALUATION.md section 3. Leng, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, The full sweep across every held-out sequence, keyed by outage length.      ``, Alignment (+62 more)

### Community 11 - "ndarray"
Cohesion: 0.10
Nodes (36): exp_so3(), log_so3(), slice, Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.  **This is, Rodrigues. Gamma_0 *is* the SO(3) exponential., Error-state Kalman update, with the correction **subtracted** (D-050)., Pack (R, v, p) into the 5x5 SE_2(3) matrix of section 2., se23_exp() (+28 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.10
Nodes (32): pca_mount_yaw(), Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, _drive_with_a_knock(), _driving_specific_force(), `R_sv` -- the PCA initialiser, in-filter estimation, and the bump detector (P-11, `spread_rad` is the standard error of the principal-axis angle, so it must fall, Accelerometer samples at 10 Hz are not independent draws, and using `n` would un, The loop D-055 left open: with an initialiser run, the mount prior is a measurem (+24 more)

### Community 15 - "inekf.py"
Cohesion: 0.09
Nodes (21): _cue_statistic(), _effective_samples(), mount_yaw_from_dynamics(), _moving_average(), orthonormalise(), process_noise_psd(), ndarray, IMU propagation. Always runs, GNSS or not -- this is the spine.          `dt` (+13 more)

### Community 16 - "cadence.py"
Cohesion: 0.06
Nodes (46): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+38 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 18 - "truth.py"
Cohesion: 0.07
Nodes (50): align_to_sequence(), assert_truth_only(), load_truth(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, Read lat, lon and time of day from one `V-` file.      The header is read on i, Compare a loaded `S-` sequence's own GPS fixes against the paired `V-` track. (+42 more)

### Community 19 - "Stamp"
Cohesion: 0.11
Nodes (16): FixVerdict, ACCEPTED, FORCED, REJECTED, TunnelFsmConfig, TunnelOverride, AUTO, FORCE_OFF (+8 more)

### Community 20 - "test_allan.py"
Cohesion: 0.12
Nodes (33): DeviceImuSequence, is_raw_imu_sidecar(), load_raw_imu_sidecar(), DataFrame, Path, The logger's raw inertial sidecar, read for Allan variance on our own hardware., One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-sort, A raw sidecar, shaped like a `Sequence` so the Allan module needs no second code (+25 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.07
Nodes (40): Enum, crse(), CrseConvention, cte(), per_epoch_errors(), ndarray, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc, Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S (+32 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.08
Nodes (37): AllanCurve, analyse_segment(), bias_instability(), coefficients(), imu_arrays(), _loglog_slope(), NoiseCoefficients, overlapping_allan_deviation() (+29 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (25): geodetic_to_ned(), path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Local NED (north, east) offsets in metres relative to an origin fix.      Smal, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t (+17 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.09
Nodes (9): MotionClassifier, MotionMode, PEDESTRIAN, UNKNOWN, VEHICLE, StepEvent, ReacquisitionSlew, MotionClassifierTest (+1 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.14
Nodes (23): audit_table(), build_parser(), _choose_target(), _evaluate_arrays(), _export_fp16(), load_windows(), main(), plot_calibration() (+15 more)

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.12
Nodes (15): The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, The submission logger must be strictly offline (D-041). Without the permission,, D-122: the secret `sk.` downloads token lives in the per-machine Gradle user hom, Same rule as the web page: refuse the file rather than draw an older layout's fi, The one assertion here that catches a drift between two files rather than a rule, The failure D-039 and D-080 exist to prevent, asserted against the code path: th, D-126: the bundled tunnel asset JSON must parse, declare schema idr.tunnels.v1,, Every test below iterates over a dict. A rename that empties one of them would t (+7 more)

### Community 31 - "test_replay.py"
Cohesion: 0.04
Nodes (88): assert_uniform_grid(), evaluate_sequence(), fix_arrays(), imu_stream(), This stem cannot be graded, and the run says so rather than reporting a number a, Every window of every length for one sequence, all three methods.      One GNS, `(gyro, accel, t_rel_s)` for one sequence: `(n, 3)`, `(n, 3)`, `(n,)`.      Ax, Per-sample `dt`, refusing a stream that is not the 10 Hz grid the sweep assumes. (+80 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.08
Nodes (32): chi2_gate(), propagate_nominal(), Mahalanobis gate. True means *accept* the measurement.      This single functi, Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler s, AxisMeasurement, candidate_gyro(), _course_and_gyro(), innovation_sequence() (+24 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-115 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.13
Nodes (18): audit_table(), main(), The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in th, The Onyekpe reproduction's hyperparameter audit (P-06).  Tests the *audit*, no, G-4 and D-009's discipline. An omitted hyperparameter is a choice *we* make, and, The inverse, which is the more dangerous direction: quietly relabelling a publis, The INS paper does not surface its loss or optimiser; those two rows come from W, Features are scaled 0-1 and the papers do not say on which set the scaler is fit (+10 more)

### Community 37 - "LoggerService"
Cohesion: 0.14
Nodes (7): Handler, IBinder, Intent, Service, LoggerService, HandlerThread, PowerManager

### Community 38 - "MainActivity"
Cohesion: 0.12
Nodes (10): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout, AppCompatActivity, Bundle, Button (+2 more)

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
Nodes (13): The `core/ffi/` interface definition (P-14).  There is no implementation to te, D-043 ships a definition at screening. A function body here would be the October, A surface that omits a call is a surface someone works around., The port cannot reproduce the filter's behaviour without the values it is tuned, `update_gnss` and `update_zaru` are gated (D-001, D-057) and return whether they, A rejected fix applies nothing" is the whole argument for "seamless transition w, The port happens in October, from this file, probably by someone who was not in, test_every_config_field_of_the_reference_filter_that_the_port_needs_is_present() (+5 more)

### Community 43 - "LeakageError"
Cohesion: 0.11
Nodes (24): manifest_path_for(), paired_truth_path(), Locate one shipped file by stem and stream, via the checksum manifest.      Vi, The `V-` file paired with an `S-` stem: this sequence's ground truth., No usable paired `V-` file, or more than one that disagree.      Not a Leakage, TruthPairingError, LookupError, load_windows() (+16 more)

### Community 44 - "speed_head.py"
Cohesion: 0.16
Nodes (14): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+6 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.11
Nodes (25): _const(), _header_from_kotlin(), _int_const(), _kotlin(), Path, The Android logger's CSV schema, checked against the loader that has to read it., The app records uncalibrated accel and gyro -- `android/README.md` requires it,, `eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a d (+17 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.15
Nodes (17): assert_features_are_clean(), build_windows(), monotonic_prefix_length(), Run the guard over exactly the columns about to enter the model tensor., One stem's feature windows and truth-derived targets.      ``absolute_speed_mp, Length through the first 10 Hz monotonic prefix of a sequence.      ``M``, ``S, Build causal two-second S- windows and their position-differenced speed labels., SpeedWindows (+9 more)

### Community 49 - "Sequence"
Cohesion: 0.07
Nodes (29): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Refuses. The drift-% denominator is not measured off 9 s fixes. (+21 more)

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
Cohesion: 0.25
Nodes (7): assert_features_are_clean(), build_parser(), _median(), ArgumentParser, Training entry point for the Onyekpe INS baseline reproduction (P-06).      py, Run the repo's own leakage guard over the exact columns the model is fed. Return, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.12
Nodes (17): TunnelTrigger, BARO_PISTON, CHI2_FORCED, CHI2_PASS, CN0_COLLAPSE, CN0_LOST, CN0_RECOVERED, FIX_REAPPEARED (+9 more)

### Community 57 - "LoggerState"
Cohesion: 0.06
Nodes (18): ErrorEllipse, mahalanobisSquared(), sanitise(), Estimate, FloatArray, Location, LocalNavigationEstimator, toRadians() (+10 more)

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.13
Nodes (21): epoch_windows(), The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, StemWindows, validation_families(), P-06: the Onyekpe reproduction's data path, split rule and leakage guard.  Del, The real failure this rule exists for: `S1` is 43% of the windows and `Vw14` 32% (+13 more)

### Community 60 - "idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles"
Cohesion: 0.17
Nodes (12): Architecture, Documentation, idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles, Non-negotiables, Quick start, Repo map, Schedule — 13 days, Six seats (+4 more)

### Community 61 - "AGENTS.md — PS 26168 Intelligent Dead Reckoning"
Cohesion: 0.20
Nodes (10): After screening, AGENTS.md — PS 26168 Intelligent Dead Reckoning, Citation hygiene, Cut list, in order, Evaluation protocol — fix before any model trains, Repo layout, Six seats, Sprints (+2 more)

### Community 62 - "Session"
Cohesion: 0.29
Nodes (4): Summary, Session, Summary, JSONObject

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
Cohesion: 0.33
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of()

### Community 74 - "make_optimizer"
Cohesion: 0.06
Nodes (36): Bundle, ComponentActivity, MainActivity, gyroBiasLabel(), headingSourceLabel(), Color, Modifier, motionModeLabel() (+28 more)

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.18
Nodes (17): benchmark(), collect(), deterministic_matmul(), HostReport, is_wsl(), main(), probe_torch(), Training-host probe.      python -m models.rocm_check     python -m models.ro (+9 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.17
Nodes (11): git_sha(), make_stamp(), Path, Provenance stamping.  Every figure and table in the submission carries the com, Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes., Everything needed to regenerate an artefact., One-line stamp for a figure caption or table footer., False if this artefact came from a dirty or non-git tree. (+3 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.11
Nodes (4): FakeEditor, FakeSharedPreferences, RecentSearchesTest, SharedPreferences

### Community 81 - "chi2_gate"
Cohesion: 0.09
Nodes (33): drift_percent(), evaluate_outage(), OutageMetrics, The four metrics. This module owns every number in the submission.  Read docs/, The vehicle did not move over this window, so drift-% has no value (D-093)., Final position error as a percentage of ground-truth distance travelled., Full metric set for one outage sequence.      ``est_disp`` / ``true_disp`` are, Aggregate across sequences.      Reports the **median and 95th percentile** of (+25 more)

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
Cohesion: 0.09
Nodes (26): androidx, ImageVector, Modifier, MapControlButton(), MapStackHooks, RecenterPill(), ZoomCapsule(), ComponentActivity (+18 more)

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.07
Nodes (41): find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so, The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestam, Idling with an occupant passes the ZUPT detector and must still be excluded from (+33 more)

### Community 98 - "Timebase"
Cohesion: 0.16
Nodes (10): TunnelAssetLoader, computeCentrelineLengthM(), distanceM(), LatLon, portalDistanceM(), TunnelDef, TunnelFix, TunnelGeometry (+2 more)

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.32
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "MainActivity"
Cohesion: 0.15
Nodes (13): calibration_summary(), per_stem_summary(), ndarray, Place a reset-clock prefix on the truth clock using only its own fixes., Path speed from truth positions at the actual samples in one input window., Concatenate a group of stems after selecting its target and valid delta labels., Coverage-first calibration and sharpness statistics, independent of torch., Apply :func:`calibration_summary` per held-out stem. (+5 more)

### Community 107 - "train_baseline_rnn.py"
Cohesion: 0.16
Nodes (17): _canonicalise(), _distinct_fixes(), load_sequence(), load_split(), _preferred_copy(), DataFrame, Path, IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage (+9 more)

### Community 108 - "_aided_filter"
Cohesion: 0.06
Nodes (44): _approx_residuals_m(), _best_lag_s(), _nearest(), _parse_local_seconds(), ndarray, Ground truth from the paired `V-` VBOX GPS.  **Why this module exists.** `docs, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t (+36 more)

### Community 109 - "NavigationScreen"
Cohesion: 0.15
Nodes (12): ArrivalCard(), Modifier, ExitProgressBar(), Modifier, HazardChipItem(), HazardChips(), ImageVector, Modifier (+4 more)

### Community 110 - "Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap"
Cohesion: 0.07
Nodes (27): 1.1 Trigger Detection Layers, 1.2 Finite State Machine (FSM) Specification, 1. Autonomous Tunnel & GNSS Loss Detection Engine, 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades, 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode, 3.2 Indian Driving Realities (Mappls Benchmark Upgrades), 3.3 Full Offline Navigation Stack (The Connectivity Void), 3.4 1D Manifold Map-Matching along Tunnel Centerlines (+19 more)

### Community 111 - "3. High-Value Navigation Upgrades (Detailed Specifications)"
Cohesion: 0.08
Nodes (24): Added, Added, Added, Added, Caught in review, before this build, Caught in review, before this build, Changelog — operator UI (`android-ui/`), Fixed (+16 more)

### Community 112 - "TelemetryPanel"
Cohesion: 0.12
Nodes (4): GeocodingResult, GeocodingService, GeoCoordinate, GeocodingServiceTest

### Community 113 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "sample_rate_hz"
Cohesion: 0.31
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 115 - "assert_features_are_clean"
Cohesion: 0.20
Nodes (10): 0. Parallel-work protocol, 1. The problem, in numbers you can re-derive, 2. What a legitimate fix looks like — and three traps in it, 3. Files, tests, and what pins what, 4. Acceptance — D-133 in the D-130 / D-131 format, 5. Probes that already exist — copy, fix one path line, do not rewrite, 6. Commands, 7. Time budget and the stop rule (+2 more)

### Community 116 - "UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode"
Cohesion: 0.15
Nodes (16): AllanReport, _fixed(), gauss_markov_bias_driving_noise(), main(), Path, Process-noise amplitude for a bias modelled as first-order Gauss-Markov., Everything one run of this module produced, ready to stamp and write., Per-axis, per-segment coefficients for one sensor, optionally white-band fits on (+8 more)

### Community 117 - "1.1 Trigger Detection Layers"
Cohesion: 0.12
Nodes (17): 10. Scratch probes — where the measurements behind D-110/D-115 live, 11. Questions nobody has answered yet, 1. What you are actually picking up, 2. The number, in the order it was measured, 3. Hard constraints — each one silently ruins the work if ignored, 4. How the harness makes the number (read before touching `eval/run.py`), 5. What D-115 already changed in the filter (so you do not redo it), 6.1 Fix 1 — a stop detector ZARU can fire from (+9 more)

### Community 118 - "2. Dynamic Visual State Machine"
Cohesion: 0.19
Nodes (13): RecentSearches, SearchItem, annotateSections(), buildMergedSuggestions(), buildOfflineSuggestions(), categoryIcon(), CategoryPill, DestinationSearchBar() (+5 more)

### Community 123 - "_as_displayed"
Cohesion: 0.33
Nodes (6): _as_displayed(), One line, with Kotlin's `"..." + "..."` joins closed up.      A caption long e, D-081, and the reason it is asserted rather than trusted: the caption is the fir, The same rule for the same reason, on the other surface. Mirrors     `test_repl, test_the_operator_ui_states_what_produced_its_numbers(), test_the_replay_caption_names_the_stream_and_the_rate_and_disclaims_200_hz()

### Community 124 - "HazardChips"
Cohesion: 0.20
Nodes (10): 0. Parallel-work protocol (both handovers carry this section verbatim), 1. The problem, in numbers you can re-derive, 2. What a legitimate fix looks like — and the trap in it, 3. Files, tests, and what pins what, 4. Acceptance — D-131 in the D-130 format, 5. Probes that already exist — copy, fix one `sys.path` line, do not rewrite, 6. Commands, 7. Time budget and the stop rule (+2 more)

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
Cohesion: 0.22
Nodes (9): _last_sunday(), Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, uk_utc_offset_s(), Hand-computed from the rule, not from this function's own output.      BST run, A date-only rule would be an hour wrong for part of two days a year., test_bst_boundaries_are_the_published_ones_for_the_years_the_dataset_spans(), test_deep_winter_and_deep_summer_need_no_boundary_arithmetic() (+1 more)

### Community 130 - "test_every_field_the_replay_view_reads_is_a_field_the_harness_writes"
Cohesion: 0.50
Nodes (4): Field-by-field, against the writer's own dict literal. A renamed key on either s, The body of `eval/run.py::trajectory_record`, which is where the keys are litera, test_every_field_the_replay_view_reads_is_a_field_the_harness_writes(), _trajectory_record_source()

### Community 131 - "_nhc_mount_run"
Cohesion: 0.11
Nodes (15): ManeuverType, ARRIVE, SLIGHT_LEFT, SLIGHT_RIGHT, STRAIGHT, TUNNEL_ENTRY, TUNNEL_EXIT, TURN_LEFT (+7 more)

### Community 132 - "test_the_headers_iovnbd_actually_ships_pass_the_guard"
Cohesion: 0.08
Nodes (39): assert_feature_safe(), assert_no_leakage(), LeakageError, normalise(), Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Raise LeakageError if any disallowed channel is present.      Called by the lo, Stricter guard for tensors entering a model or filter: inertial channels only. (+31 more)

### Community 135 - "test_the_truth_allowlist_is_a_strict_subset_of_position_and_time"
Cohesion: 0.28
Nodes (8): loss_fn(), make_optimizer(), Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, Fit the baseline. Returns `(model, scaler, history, split_sizes)`.      Publis, train(), Module, Optimizer

### Community 136 - "test_the_truth_track_carries_no_inertial_channel"
Cohesion: 0.25
Nodes (6): SearchPreset, SearchSource, ONLINE, PIN, PRESET, RECENT

### Community 137 - "train"
Cohesion: 0.22
Nodes (5): OnyekpeBaseline, Tensor, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Hyperparameter

### Community 138 - "ManeuverType"
Cohesion: 0.22
Nodes (9): 0. Parallel-work protocol (both handovers carry this section verbatim), 1. What P-08 is, and the one rule that scopes it, 2. What already exists — read before writing anything, 3. The design decisions the script has to make — with the evidence already on file, 4. Environment — what actually runs on this box (verified 15 Sep), 5. Deliverables, 6. Time budget, 7. Questions this work will answer (put the answers in D-132) (+1 more)

### Community 139 - "evaluate"
Cohesion: 0.36
Nodes (7): Dp, Modifier, SwipeDirection, DOWN, UP, swipeToDismiss(), verticalSwipe()

### Community 144 - "sample_rate_hz"
Cohesion: 0.50
Nodes (4): The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a de, sample_rate_hz(), No `sample_rate_hz` attribute means 10 Hz, exactly as before this loader existed, test_an_iovnbd_sequence_still_windows_at_the_protocol_rate()

### Community 145 - ".aided_pass_summary"
Cohesion: 0.25
Nodes (6): dateFormat(), Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, java

### Community 146 - "test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window"
Cohesion: 0.29
Nodes (7): Android Demo Builds, Available Builds, Direct Mobile Download, GitHub Releases, Installation, Latest CI build, Updating this file

### Community 147 - "test_in_motion_config_raises_q_to_the_stream_and_never_lowers_it"
Cohesion: 0.25
Nodes (8): 1. The host, 2. Install, 3. Verify, 4. What actually uses the GPU today: nothing, 5. Determinism, and what a GPU number may be used for, 6. What is allowed to train right now, 7. Known failure modes, Training Environment

### Community 148 - "test_the_doppler_velocity_is_along_and_across_the_course"
Cohesion: 0.40
Nodes (5): The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, stem_family(), Hold back complete TRAIN families using P-06's deterministic D-098 rule., validation_families(), test_stem_family_groups_lettered_segments_and_leaves_others_alone()

### Community 149 - "test_evaluate_outage_end_to_end"
Cohesion: 0.50
Nodes (4): detector_settings(), The stationarity rule the segments were found under, for the summary's provenanc, The summary records the stationarity rule its segments were found under, and it, test_the_committed_artefacts_were_made_under_the_current_detector()

### Community 150 - "test_summary_reports_tail_not_just_mean"
Cohesion: 0.50
Nodes (4): Section, NEARBY, RECENT, RESULTS

### Community 151 - "octave_taus"
Cohesion: 0.50
Nodes (4): octave_taus(), Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record., test_every_tau_is_an_exact_multiple_of_dt(), test_taus_stop_at_the_max_fraction_of_the_record()

### Community 152 - "wrap_to_pi"
Cohesion: 0.50
Nodes (4): Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., wrap_to_pi(), 359 degrees to 1 degree is +2, not -358. Unwrapped, a single wrap puts a 6.2 rad, test_heading_differences_wrap()

## Knowledge Gaps
- **521 isolated node(s):** `UNKNOWN`, `PEDESTRIAN`, `VEHICLE`, `GNSS`, `INS` (+516 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Session` connect `Session` to `LoggerService`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `NavigationScreen()` connect `NavigationScreen` to `io_vnbd.py`, `_nhc_mount_run`, `make_optimizer`, `TelemetryPanel`, `TelemetryState`, `sample_rate_hz`, `2. Dynamic Visual State Machine`, `LoggerState`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `SearchItem` connect `2. Dynamic Visual State Machine` to `_nhc_mount_run`, `test_the_truth_track_carries_no_inertial_channel`, `NavigationScreen`, `TelemetryPanel`, `drift_percent`, `MapView`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._