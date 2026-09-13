# Graph Report - SIH-26168  (2026-09-13)

## Corpus Check
- 145 files · ~446,803 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2496 nodes · 4668 edges · 137 communities (114 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 304 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0a0c26be`
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

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 74 edges
2. `FilterConfig` - 67 edges
3. `TunnelFsm` - 57 edges
4. `evaluate_sequence()` - 43 edges
5. `Sequence` - 42 edges
6. `TunnelFsmTest` - 41 edges
7. `Outage` - 38 edges
8. `LeakageError` - 35 edges
9. `synthetic_drive()` - 35 edges
10. `load_sequence()` - 32 edges

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

## Communities (137 total, 23 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.06
Nodes (72): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+64 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.05
Nodes (60): a_ri(), expm_series(), g_ri(), process_noise_psd(), IMU propagation. Always runs, GNSS or not -- this is the spine.          `dt`, Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_* slic, Noise mapping, section 5.3. Columns are `[w_g, w_a, w_bg, w_ba, w_sv]`, 15 wide. (+52 more)

### Community 2 - "test_filter.py"
Cohesion: 0.05
Nodes (54): detect_mount_disturbance(), initial_covariance(), nhc_is_valid(), Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, Re-express a covariance built on *plain* errors in the filter's right-invariant, Whether the non-holonomic constraint may be applied this step.      NHC says t, right_invariant_from_plain() (+46 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.11
Nodes (25): assert_uniform_grid(), This stem cannot be graded, and the run says so rather than reporting a number a, Per-sample `dt`, refusing a stream that is not the 10 Hz grid the sweep assumes., Seconds to add to a sequence-relative time to put it on the truth track's clock., SequenceUnusable, truth_clock_offset_s(), End-to-end wiring for `eval/run.py`, on a synthetic sequence.  **Why synthetic.*, The `S-` and `V-` clocks differ by `START_OF_DAY_S` here, and nothing but the fi (+17 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.04
Nodes (71): AssertionError, assert_non_overlapping(), generate_outages(), mask_gnss(), ndarray, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic (+63 more)

### Community 5 - "RecordsTest"
Cohesion: 0.07
Nodes (14): Fix, GnssHub, Bundle, Handler, Location, LocationListener, Summary, SatSample (+6 more)

### Community 6 - "RateStatsTest"
Cohesion: 0.06
Nodes (16): Snapshot, RateStats, Snapshot, fmt(), FloatArray, Handler, Sensor, SensorEvent (+8 more)

### Community 7 - "7. The phases"
Cohesion: 0.04
Nodes (49): 0.1 Authority order, 0. What this file is, and what it is not, 10. Stop conditions — stop immediately and report, 11. Findings — agents may append here, 1.1 The loop — every task, no exceptions, 1.2 Rules about this file itself, 1.3 Session bootstrap prompt — paste this first, every session, 1. How to follow this file (+41 more)

### Community 8 - "FilterConfig"
Cohesion: 0.05
Nodes (40): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Section 7.2. Returns `(v_veh_hat, H_veh)` with the mount column carried., Non-holonomic pseudo-measurement. Caller checks nhc_is_valid() first., Zero-velocity update. Observes accelerometer bias.          Uses section **7.1, Learned forward-speed pseudo-measurement with its predicted variance., The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages (+32 more)

### Community 10 - "run.py"
Cohesion: 0.05
Nodes (77): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., No usable paired `V-` file, or more than one that disagree.      Not a Leakage, TruthPairingError, OutageMetrics (+69 more)

### Community 11 - "ndarray"
Cohesion: 0.08
Nodes (52): adjoint(), _cue_statistic(), _effective_samples(), exp_so3(), gammas(), log_so3(), mount_yaw_from_dynamics(), _moving_average() (+44 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.09
Nodes (34): pca_mount_yaw(), Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, _drive_with_a_knock(), _driving_specific_force(), `R_sv` -- the PCA initialiser, in-filter estimation, and the bump detector (P-11, `spread_rad` is the standard error of the principal-axis angle, so it must fall, Accelerometer samples at 10 Hz are not independent draws, and using `n` would un, The loop D-055 left open: with an initialiser run, the mount prior is a measurem (+26 more)

### Community 15 - "inekf.py"
Cohesion: 0.08
Nodes (33): evaluate_sequence(), Every window of every length for one sequence, all three methods.      One GNS, What the aided pass did, for `summary.json`: how it aligned, what it was fed, an, _date_strings(), ndarray, The epoch of a window comes from the row's own timestamp, never from its row ind, If this fails the fixture is wrong, and every assertion built on it means nothin, Proper right-handed triad (+gyro_yaw, -gyro_roll, +gyro_pitch) established by D- (+25 more)

### Community 16 - "cadence.py"
Cohesion: 0.05
Nodes (58): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+50 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 18 - "truth.py"
Cohesion: 0.03
Nodes (97): align_to_sequence(), _approx_residuals_m(), _best_lag_s(), _last_sunday(), load_truth(), _nearest(), normalise_truth_header(), _parse_local_seconds() (+89 more)

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
Cohesion: 0.11
Nodes (21): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, Metric unit tests, each against a hand-computed case.  Every number in the sub, 60 s outage, 10 m/s, perfect heading, 2% under-prediction of distance.      Tr, Three epochs, each under-predicted by 1 m along-track.      Hand-computed: per, The pair exists precisely because they disagree: +2 and -2 cancel in CTE but not, There is no else-fallthrough in crse(): an unknown member must raise, not quietl, Hand-computed on four epochs of exactly 1 m error each.      Was a two-way tes (+13 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.09
Nodes (32): AllanCurve, AllanReport, analyse_segment(), bias_instability(), coefficients(), detector_settings(), _fixed(), gauss_markov_bias_driving_noise() (+24 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (25): geodetic_to_ned(), path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Local NED (north, east) offsets in metres relative to an origin fix.      Smal, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t (+17 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.17
Nodes (12): imu_arrays(), _loglog_slope(), octave_taus(), ndarray, Pull `(t_s, accel, gyro)` out of a loaded sequence as float arrays.      Rows, Mean over every length-`window` slice, via cumulative sums. Shape (n - window +, Half-open [start, stop) index pairs of every run of True., Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record. (+4 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.11
Nodes (14): androidx, ImageVector, Modifier, MapControlButton(), MapStackHooks, RecenterPill(), ComponentActivity, MapStack (+6 more)

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.12
Nodes (15): The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, The submission logger must be strictly offline (D-041). Without the permission,, D-122: the secret `sk.` downloads token lives in the per-machine Gradle user hom, Same rule as the web page: refuse the file rather than draw an older layout's fi, The one assertion here that catches a drift between two files rather than a rule, The failure D-039 and D-080 exist to prevent, asserted against the code path: th, D-126: the bundled tunnel asset JSON must parse, declare schema idr.tunnels.v1,, Every test below iterates over a dict. A rename that empties one of them would t (+7 more)

### Community 31 - "test_replay.py"
Cohesion: 0.08
Nodes (17): The replay renderer (P-13) and the artefact it reads.  Two things are tested,, The drift-and-crash case: a renamed field renders as `undefined` and the page dr, `length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page in, No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot, It has to survive someone editing the page a month from now without this convers, The specific failure D-039 exists to prevent. Asserted against the code path: th, Drift-% and yaw error come out of the artefact. If the page computed them it cou, A screenshot of the demo has to be self-evidencing (H-5), and an artefact from a (+9 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.11
Nodes (30): AxisMeasurement, candidate_gyro(), _course_and_gyro(), innovation_sequence(), main(), measure(), ndarray, Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it (+22 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-115 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.11
Nodes (22): audit_table(), build_parser(), main(), _median(), ArgumentParser, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md), The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in th, The Onyekpe reproduction's hyperparameter audit (P-06).  Tests the *audit*, no (+14 more)

### Community 37 - "LoggerService"
Cohesion: 0.14
Nodes (7): Handler, IBinder, Intent, Service, LoggerService, HandlerThread, PowerManager

### Community 38 - "MainActivity"
Cohesion: 0.12
Nodes (10): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout, AppCompatActivity, Bundle, Button (+2 more)

### Community 39 - "The logger"
Cohesion: 0.11
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
Cohesion: 0.22
Nodes (9): assert_truth_only(), Raise unless every column is one of lat, lon, time of day.      An allowlist,, Including `GPS Velocity`, which is neither wheel-derived nor banned by name. Tru, test_the_truth_guard_rejects_every_other_vehicle_channel(), `EVALUATION.md` section 1.2 permits the `V-` GPS as *ground truth*. Truth is a p, The `V-` stream carries 'Indicated Longitudinal Acceleration'. A loose longitude, test_longitudinal_accel_is_not_mistaken_for_longitude(), test_other_v_gps_channels_are_rejected_even_though_they_are_not_wheel_speed() (+1 more)

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.11
Nodes (25): _const(), _header_from_kotlin(), _int_const(), _kotlin(), Path, The Android logger's CSV schema, checked against the loader that has to read it., The app records uncalibrated accel and gyro -- `android/README.md` requires it,, `eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a d (+17 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.20
Nodes (15): Enum, crse(), CrseConvention, evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc (+7 more)

### Community 49 - "Sequence"
Cohesion: 0.13
Nodes (11): The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a de, sample_rate_hz(), ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi (+3 more)

### Community 50 - "Handover — seat A, Android: the map view and production readiness"
Cohesion: 0.10
Nodes (20): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — **built**, in `9fdd261`, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+12 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "octave_taus"
Cohesion: 0.06
Nodes (29): Bundle, Context, IBinder, Intent, Location, LocationListener, Sensor, SensorEvent (+21 more)

### Community 53 - "assert_no_leakage"
Cohesion: 0.11
Nodes (19): D-080. A renderer has no business with a random number, and neither has a view t, The specific thing that was here: a `PREVIEW_TELEMETRY` constant, rendered whene, D-126: `TunnelFsm` decides when GNSS is suppressed and when a fix counts as veri, D-126 deviation 3 / D-115: the fix applied after N consecutive rejections is on, D-124, restating D-112 for every new screen: drift is error against truth as a p, D-080 / R-B: TunnelCorridor must advance strictly on the estimator's pose clock, R-F / D-126: hazard chips are strictly limited to the declared set derived from, D-081 caption discipline: the speedometer HUD explicitly names its source ('filt (+11 more)

### Community 54 - "normalise"
Cohesion: 0.12
Nodes (26): assert_feature_safe(), assert_no_leakage(), LeakageError, Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, Raise LeakageError if any disallowed channel is present.      Called by the lo, Stricter guard for tensors entering a model or filter: inertial channels only., A disallowed channel reached a feature path.      Deliberately an AssertionErr, The aliases must not have widened the guard. These are the real 'V-' column name (+18 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.12
Nodes (17): TunnelTrigger, BARO_PISTON, CHI2_FORCED, CHI2_PASS, CN0_COLLAPSE, CN0_LOST, CN0_RECOVERED, FIX_REAPPEARED (+9 more)

### Community 57 - "LoggerState"
Cohesion: 0.07
Nodes (14): ErrorEllipse, mahalanobisSquared(), sanitise(), Estimate, Location, LocalNavigationEstimator, toRadians(), NavigationMode (+6 more)

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.06
Nodes (42): The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, stem_family(), loss_fn(), make_optimizer(), OnyekpeBaseline, Tensor, Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Vanilla RNN correcting INS displacement error and orientation-rate error. (+34 more)

### Community 60 - "idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles"
Cohesion: 0.18
Nodes (11): Architecture, Documentation, idr-26168 — Intelligent Dead Reckoning for GNSS-Denied Ground Vehicles, Non-negotiables, Quick start, Repo map, Schedule — 13 days, Six seats (+3 more)

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
Cohesion: 0.15
Nodes (13): 7.0 Summary — the eight inputs that change the plan, 7.10 Build, account and pricing checklist, 7.11 What this changes in the two plans, 7.1 Two products — which one to build on, 7.2 The puck-ownership problem (read this one), 7.3 Honesty constraints this plan currently breaks, 7.4 Offline and the venue, 7.5 What the SDK already gives the tunnel FSM (+5 more)

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.22
Nodes (8): Car-park mode, Contract, Known failure modes, Library choice — **settled: build it, do not adopt one (D-036)**, maps/ — OSM graph & HMM map matcher, Status, The pipeline, as designed, What lives here

### Community 71 - "train_baseline_rnn.py"
Cohesion: 0.25
Nodes (8): Building, IDR Navigator — operator UI prototype, Mapbox tokens (D-122), Open work, The rules this module is held to, The tunnel machine (D-126), Two map engines, one screen (D-121), What the `mapbox` flavour does today

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.33
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.39
Nodes (7): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of(), RuntimeError

### Community 74 - "make_optimizer"
Cohesion: 0.12
Nodes (17): Bundle, ComponentActivity, MainActivity, ExtendedColors, IDRAnimations, IDRColors, IDRDarkPalette, IDRLightPalette (+9 more)

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.20
Nodes (10): closed_form_gammas(), _nees_inputs(), _nees_p0(), ndarray, The cutoff must sit where the closed form is *still accurate*, not where it is 0, The textbook expressions with no small-angle guard. Used only to show where they, The Monte-Carlo prior.      **This is the test's experimental design, not a pr, (omega, specific force, truly stopped) for step `k`: cruise, brake, stop, pull a (+2 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.14
Nodes (16): gate1_ratio(), `{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`, The Gate 1 number: physics-only median drift over GNSS-available median drift, a, Write `summary.json`, `windows.csv` and one `trajectory_<seq>.json` per plotted, summarise_by_method_and_length(), write_artefacts(), A ratio quoted without its sample size is the number a judge asks about second., No 60 s windows means no Gate 1 number. Saying so is the only correct output. (+8 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.33
Nodes (6): drift_percent(), Final position error as a percentage of ground-truth distance travelled., 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, test_drift_percent_hand_computed(), test_drift_percent_rejects_zero_distance()

### Community 81 - "chi2_gate"
Cohesion: 0.18
Nodes (15): _canonicalise(), _distinct_fixes(), load_sequence(), load_split(), _preferred_copy(), DataFrame, Path, IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage (+7 more)

### Community 82 - "TelemetryState"
Cohesion: 0.27
Nodes (5): StateFlow, TelemetryState, TelemetryStore, computeActiveHazardChipLabels(), HazardChipsTest

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 86 - "MapView"
Cohesion: 0.36
Nodes (7): ellipseGeoPoints(), getVehicleIcon(), Context, Modifier, MapView(), Drawable, GeoPoint

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.06
Nodes (53): FilterConfig, is_stationary(), Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, Detect a stopped vehicle for ZUPT/ZARU.      Both conditions must hold: low ac, find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ZUPT+ZARU at a detected stop, else NHC where it is valid -- the same step for th, _step_constraints() (+45 more)

### Community 98 - "Timebase"
Cohesion: 0.25
Nodes (6): dateFormat(), Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, java

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.32
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "MainActivity"
Cohesion: 0.17
Nodes (7): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Vincenty path length between two times, in metres.          The `L` in drift-%, Aggregate across sequences.      Reports the **median and 95th percentile** of, summarise(), The mean hides the tail and the tail is what a judge finds., test_summary_reports_tail_not_just_mean(), ValueError

### Community 107 - "train_baseline_rnn.py"
Cohesion: 0.18
Nodes (11): normalise(), Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Generic paren-stripping collapsed all three to the single name 'orientation'., The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder writes, Time Since Start of Day (seconds)' is a 'V-' column and a different quantity. If, test_both_shipped_gyro_spellings_reach_the_same_canonical_names(), test_the_three_orientation_columns_stay_three_columns(), test_the_v_streams_time_column_is_not_laundered_by_the_alias() (+3 more)

### Community 108 - "_aided_filter"
Cohesion: 0.20
Nodes (9): chi2_gate(), Mahalanobis gate. True means *accept* the measurement.      This single functi, Zero-angular-rate update, chi-squared gated. Returns whether it was applied., A 50 m jump on tunnel exit, against a 2 m-sigma covariance., After a long outage the filter is genuinely uncertain, so a big correction is co, test_consistent_fix_is_accepted(), test_inflated_covariance_admits_a_larger_correction(), test_multipath_outlier_is_rejected() (+1 more)

### Community 109 - "NavigationScreen"
Cohesion: 0.29
Nodes (9): ExitProgressBar(), Modifier, FloatingActionPill(), androidx, Color, Modifier, NavigationScreen(), TunnelOptionSegment() (+1 more)

### Community 110 - "Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap"
Cohesion: 0.20
Nodes (10): 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades, 4. Architectural Implementation Blueprint, 5. Phased Implementation Roadmap, 6. Conclusion, Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap, Executive Summary, Phase 1: Autonomous Detection FSM & UI Tunnel Mode, Phase 2: Offline Mapping & 1D Spline Road Matching (+2 more)

### Community 111 - "3. High-Value Navigation Upgrades (Detailed Specifications)"
Cohesion: 0.20
Nodes (10): 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode, 3.2 Indian Driving Realities (Mappls Benchmark Upgrades), 3.3 Full Offline Navigation Stack (The Connectivity Void), 3.4 1D Manifold Map-Matching along Tunnel Centerlines, 3.5 Tunnel Exit & GNSS Re-convergence (Anti-Jump Filter), 3. High-Value Navigation Upgrades (Detailed Specifications), Mathematical Formulation:, Proposed Component Upgrades: (+2 more)

### Community 112 - "TelemetryPanel"
Cohesion: 0.83
Nodes (3): Modifier, MetricCard(), TelemetryPanel()

### Community 113 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "sample_rate_hz"
Cohesion: 0.31
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 115 - "assert_features_are_clean"
Cohesion: 0.50
Nodes (4): assert_features_are_clean(), Run the repo's own leakage guard over the exact columns the model is fed. Return, The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject()

### Community 116 - "UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode"
Cohesion: 0.25
Nodes (6): 1. Design Philosophy & High-Level Vision, 3. Screen Layout Blueprint & UI Component Hierarchy, 4. UI Design Token System (Theme Extensions), 6. Implementation Checklist for Frontend Engineers (Jetpack Compose), Key Design Pillars, UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode

### Community 117 - "1.1 Trigger Detection Layers"
Cohesion: 0.29
Nodes (7): 1.1 Trigger Detection Layers, 1.2 Finite State Machine (FSM) Specification, 1. Autonomous Tunnel & GNSS Loss Detection Engine, A. GNSS Carrier-to-Noise Ratio ($C/N_0$) and Geometry Collapse, B. Map-Based Predictive Portal Geofencing (Zero-Latency Pre-Arming), C. Ambient Light Sensor (`Sensor.TYPE_LIGHT`), D. Barometric Piston Effect (`Sensor.TYPE_PRESSURE`)

### Community 118 - "2. Dynamic Visual State Machine"
Cohesion: 0.29
Nodes (7): 2. Dynamic Visual State Machine, Stage 1: Open Sky Navigation (Normal Drive), Stage 2: Approach & Portal Pre-Arming Zone ($D_{\text{portal}} < 100\text{ m}$), Stage 3: Autonomous 3D Tunnel Interior Mode (Active IDR), Stage 4: Exit Portal & Anti-Jump Re-acquisition, Stage 5: Open Sky Steady State & Performance Drift Summary, Visual Features in Tunnel Mode:

### Community 122 - "5. Curated Websites for UI/UX References & Design Inspiration"
Cohesion: 0.33
Nodes (6): 1. Mobbin (The Gold Standard for Real Mobile App Flows), 2. Mapbox Navigation & Vision SDK Showcase, 3. Mappls (MapmyIndia) Official Portal & App Gallery, 4. Dribbble & Behance (Automotive HMI & Concept UI), 5. Curated Websites for UI/UX References & Design Inspiration, 5. Google Material Design 3 for Cars / Android Auto

### Community 123 - "_as_displayed"
Cohesion: 0.33
Nodes (6): _as_displayed(), One line, with Kotlin's `"..." + "..."` joins closed up.      A caption long e, D-081, and the reason it is asserted rather than trusted: the caption is the fir, The same rule for the same reason, on the other surface. Mirrors     `test_repl, test_the_operator_ui_states_what_produced_its_numbers(), test_the_replay_caption_names_the_stream_and_the_rate_and_disclaims_200_hz()

### Community 124 - "HazardChips"
Cohesion: 0.60
Nodes (4): HazardChipItem(), HazardChips(), ImageVector, Modifier

### Community 125 - "yaw_error"
Cohesion: 0.40
Nodes (5): (RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].      Always r, yaw_error(), An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi, test_yaw_error_wraps_across_the_branch_cut(), test_yaw_error_zero_when_identical()

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
Cohesion: 0.50
Nodes (4): _nhc_mount_run(), Straight drive at `speed` with a true 5-degree mount yaw the filter does not kno, SE_2(3) test 9. Section 7.2's `-v_veh_hat^` column made quantitative.      For, test_nhc_learns_the_mount_yaw_and_learns_it_faster_at_speed()

## Knowledge Gaps
- **416 isolated node(s):** `GNSS`, `INS`, `INIT`, `GNSS_HEALTHY`, `PRE_ARMED_ENTRY` (+411 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InEKF` connect `FilterConfig` to `test_se23_derivation.py`, `test_filter.py`, `seconds_of_day_utc`, `test_harness_wiring.py`, `_nhc_mount_run`, `MainActivity`, `ndarray`, `_aided_filter`, `run.py`, `test_ffi_contract.py`, `test_mount.py`, `gauss_markov_bias_driving_noise`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `FilterConfig` connect `gauss_markov_bias_driving_noise` to `test_baselines.py`, `test_se23_derivation.py`, `test_filter.py`, `seconds_of_day_utc`, `test_harness_wiring.py`, `FilterConfig`, `run.py`, `ndarray`, `test_ffi_contract.py`, `test_mount.py`, `inekf.py`, `allan.py`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Session` connect `Session` to `LoggerService`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._