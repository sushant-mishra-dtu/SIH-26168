# Graph Report - SIH-26168  (2026-09-13)

## Corpus Check
- 152 files · ~450,821 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2538 nodes · 4731 edges · 152 communities (123 shown, 29 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 311 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0e33dd50`
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
- test_the_doppler_velocity_is_along_and_across_the_course
- test_evaluate_outage_end_to_end
- test_summary_reports_tail_not_just_mean
- test_crse_default_is_the_papers_equation_16

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
- `AxisMeasurement` --uses--> `FilterConfig`  [INFERRED]
  eval/axis_check.py → core/reference/inekf.py
- `Alignment` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py
- `DroppedWindow` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py
- `FilterDivergedError` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py
- `FilterInit` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (152 total, 29 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.06
Nodes (64): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+56 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.07
Nodes (56): a_ri(), expm_series(), g_ri(), gammas(), process_noise_psd(), Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.  **This is, Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, The hat map: `skew(a) @ b == np.cross(a, b)`. (+48 more)

### Community 2 - "test_filter.py"
Cohesion: 0.04
Nodes (69): chi2_gate(), detect_mount_disturbance(), initial_covariance(), is_stationary(), nhc_is_valid(), Mahalanobis gate. True means *accept* the measurement.      This single functi, Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG (+61 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.05
Nodes (53): AssertionError, assert_non_overlapping(), generate_outages(), mask_gnss(), ndarray, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic (+45 more)

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
Cohesion: 0.05
Nodes (41): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Learned forward-speed pseudo-measurement with its predicted variance., The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages, The asymmetry is measured, not assumed (D-057): gating ZUPT takes its NEES from, Placeholders raise. A stub that returns None would let the harness produce plaus, The architectural claim, asserted rather than described.      There is no tunn, test_a_rejected_gnss_fix_changes_absolutely_nothing() (+33 more)

### Community 10 - "run.py"
Cohesion: 0.05
Nodes (71): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Sequence (+63 more)

### Community 11 - "ndarray"
Cohesion: 0.08
Nodes (36): adjoint(), ndarray, Error-state Kalman update, with the correction **subtracted** (D-050)., Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Section 7.2. Returns `(v_veh_hat, H_veh)` with the mount column carried., Horizontal GNSS velocity update. Returns whether it was applied.          The, Non-holonomic pseudo-measurement. Caller checks nhc_is_valid() first., Zero-velocity update. Observes accelerometer bias.          Uses section **7.1 (+28 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.07
Nodes (45): _cue_statistic(), _effective_samples(), exp_so3(), log_so3(), pca_mount_yaw(), propagate_nominal(), Rodrigues. Gamma_0 *is* the SO(3) exponential., Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler s (+37 more)

### Community 15 - "inekf.py"
Cohesion: 0.05
Nodes (79): assert_uniform_grid(), evaluate_sequence(), fix_arrays(), gate1_ratio(), imu_stream(), This stem cannot be graded, and the run says so rather than reporting a number a, Every window of every length for one sequence, all three methods.      One GNS, `(gyro, accel, t_rel_s)` for one sequence: `(n, 3)`, `(n, 3)`, `(n,)`.      Ax (+71 more)

### Community 16 - "cadence.py"
Cohesion: 0.09
Nodes (39): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+31 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 18 - "truth.py"
Cohesion: 0.09
Nodes (37): load_sequence(), load_split(), _preferred_copy(), Path, Load one sequence CSV.      Raises LeakageError if the file contains any disal, Pick deterministically between multiple copies of the same stem.      Every on, Load a named set of sequences from a directory. Missing files are reported toget, align_to_sequence() (+29 more)

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
Cohesion: 0.14
Nodes (17): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, Metric unit tests, each against a hand-computed case.  Every number in the sub, Three epochs, each under-predicted by 1 m along-track.      Hand-computed: per, The pair exists precisely because they disagree: +2 and -2 cancel in CTE but not, There is no else-fallthrough in crse(): an unknown member must raise, not quietl, Hand-computed on four epochs of exactly 1 m error each.      Was a two-way tes, Eq. (16)'s root is inside the sum, which is the whole difference from CTE (Eq. 1 (+9 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.08
Nodes (39): FilterConfig, Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, AllanCurve, AllanReport, analyse_segment(), bias_instability(), coefficients(), detector_settings() (+31 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (23): path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t, vincenty_inverse(), wrap_to_pi() (+15 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.17
Nodes (12): imu_arrays(), _loglog_slope(), octave_taus(), ndarray, Pull `(t_s, accel, gyro)` out of a loaded sequence as float arrays.      Rows, Mean over every length-`window` slice, via cumulative sums. Shape (n - window +, Half-open [start, stop) index pairs of every run of True., Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record. (+4 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.18
Nodes (6): androidx, MapStackHooks, ComponentActivity, MapStack, ComponentActivity, MapStack

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.12
Nodes (15): The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, The submission logger must be strictly offline (D-041). Without the permission,, D-122: the secret `sk.` downloads token lives in the per-machine Gradle user hom, Same rule as the web page: refuse the file rather than draw an older layout's fi, The one assertion here that catches a drift between two files rather than a rule, The failure D-039 and D-080 exist to prevent, asserted against the code path: th, D-126: the bundled tunnel asset JSON must parse, declare schema idr.tunnels.v1,, Every test below iterates over a dict. A rename that empties one of them would t (+7 more)

### Community 31 - "test_replay.py"
Cohesion: 0.08
Nodes (19): artefacts(), The replay renderer (P-13) and the artefact it reads.  Two things are tested,, A real harness run over the synthetic drive, written to disk exactly as `main` w, The drift-and-crash case: a renamed field renders as `undefined` and the page dr, `length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page in, No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot, It has to survive someone editing the page a month from now without this convers, The specific failure D-039 exists to prevent. Asserted against the code path: th (+11 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.14
Nodes (20): AxisMeasurement, candidate_gyro(), _course_and_gyro(), main(), measure(), ndarray, Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it, `(course_rate, gyro_mean, course_change, gyro_integral, keep)` over fix interval (+12 more)

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
Cohesion: 0.06
Nodes (43): assert_truth_only(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, _manifest_rows(), Ground truth from the paired `V-` VBOX GPS, and the cadence measurement behind i, Rows from the committed manifest -- the same file the loaders resolve paths thro, Not a style point. A velocity column here becomes a speed label the first time s (+35 more)

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
Cohesion: 0.24
Nodes (13): Enum, crse(), CrseConvention, evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc (+5 more)

### Community 49 - "Sequence"
Cohesion: 0.29
Nodes (4): ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi

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
Nodes (20): assert_feature_safe(), LeakageError, Stricter guard for tensors entering a model or filter: inertial channels only., A disallowed channel reached a feature path.      Deliberately an AssertionErr, The aliases must not have widened the guard. These are the real 'V-' column name, test_the_v_stream_header_is_still_rejected_wholesale(), The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject() (+12 more)

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
Cohesion: 0.18
Nodes (15): The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., StemWindows, validation_families(), wrap_to_pi(), P-06: the Onyekpe reproduction's data path, split rule and leakage guard.  Del, The real failure this rule exists for: `S1` is 43% of the windows and `Vw14` 32% (+7 more)

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
Cohesion: 0.29
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.39
Nodes (7): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of(), RuntimeError

### Community 74 - "make_optimizer"
Cohesion: 0.12
Nodes (17): Bundle, ComponentActivity, MainActivity, ExtendedColors, IDRAnimations, IDRColors, IDRDarkPalette, IDRLightPalette (+9 more)

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.11
Nodes (20): _approx_residuals_m(), _best_lag_s(), _nearest(), ndarray, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t, Latitude/longitude at each epoch time, shape ``(n, 2)``., Local NED positions at each epoch time, relative to the first, shape ``(n, 2)``. (+12 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.09
Nodes (25): build_parser(), DroppedWindow, ArgumentParser, Path, One outage window the paired `V-` track does not cover, and why (D-089)., `{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`, Write `summary.json`, `windows.csv` and one `trajectory_<seq>.json` per plotted, summarise_by_method_and_length() (+17 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.33
Nodes (6): drift_percent(), Final position error as a percentage of ground-truth distance travelled., 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, test_drift_percent_hand_computed(), test_drift_percent_rejects_zero_distance()

### Community 81 - "chi2_gate"
Cohesion: 0.25
Nodes (7): Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, _canonicalise(), _distinct_fixes(), DataFrame, IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage, Normalise headers, then guard. Guard *after* normalisation so that a disguised w, One row per GPS position change, carrying its timestamp and IMU sample index.

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
Cohesion: 0.17
Nodes (16): ImageVector, Modifier, MapControlButton(), RecenterPill(), Modifier, lonPerMetre(), MapView(), MissingTokenState() (+8 more)

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.09
Nodes (36): find_stationary_segments(), gauss_markov_bias_driving_noise(), Find stretches long and clean enough to compute an Allan curve on.      Statio, Process-noise amplitude for a bias modelled as first-order Gauss-Markov., ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so (+28 more)

### Community 98 - "Timebase"
Cohesion: 0.25
Nodes (6): dateFormat(), Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, java

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.32
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "MainActivity"
Cohesion: 0.13
Nodes (10): mount_yaw_from_dynamics(), _moving_average(), orthonormalise(), IMU propagation. Always runs, GNSS or not -- this is the spine.          `dt`, chi-squared-gated GNSS position update. Returns whether the fix was accepted., Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Nearest rotation matrix in the Frobenius sense, with the reflection branch exclu, Mount yaw by least squares between the phone's horizontal specific force and the (+2 more)

### Community 107 - "train_baseline_rnn.py"
Cohesion: 0.17
Nodes (12): normalise(), Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Generic paren-stripping collapsed all three to the single name 'orientation'., The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder writes, Time Since Start of Day (seconds)' is a 'V-' column and a different quantity. If, test_a_truncated_date_format_string_still_normalises(), test_both_shipped_gyro_spellings_reach_the_same_canonical_names(), test_the_satellite_column_ships_with_and_without_the_gps_prefix() (+4 more)

### Community 108 - "_aided_filter"
Cohesion: 0.09
Nodes (25): _parse_local_seconds(), Make a seconds-since-midnight series monotonic across a midnight rollover., Parse the `S-` `date` column into seconds since midnight, **as shipped**., Local seconds since midnight per row, **not** unwrapped. NaN where the row does, The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-0, seconds_of_day(), seconds_of_day_utc(), unwrap_time_of_day() (+17 more)

### Community 109 - "NavigationScreen"
Cohesion: 0.13
Nodes (15): DestinationSearchBar(), Modifier, ExitProgressBar(), Modifier, Modifier, NavigationHeader(), Modifier, TunnelStatusBadge() (+7 more)

### Community 110 - "Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap"
Cohesion: 0.20
Nodes (10): 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades, 4. Architectural Implementation Blueprint, 5. Phased Implementation Roadmap, 6. Conclusion, Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap, Executive Summary, Phase 1: Autonomous Detection FSM & UI Tunnel Mode, Phase 2: Offline Mapping & 1D Spline Road Matching (+2 more)

### Community 111 - "3. High-Value Navigation Upgrades (Detailed Specifications)"
Cohesion: 0.20
Nodes (10): 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode, 3.2 Indian Driving Realities (Mappls Benchmark Upgrades), 3.3 Full Offline Navigation Stack (The Connectivity Void), 3.4 1D Manifold Map-Matching along Tunnel Centerlines, 3.5 Tunnel Exit & GNSS Re-convergence (Anti-Jump Filter), 3. High-Value Navigation Upgrades (Detailed Specifications), Mathematical Formulation:, Proposed Component Upgrades: (+2 more)

### Community 112 - "TelemetryPanel"
Cohesion: 0.38
Nodes (5): Modifier, NavigationBottomSheet(), Modifier, MetricCard(), TelemetryPanel()

### Community 113 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "sample_rate_hz"
Cohesion: 0.31
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 115 - "assert_features_are_clean"
Cohesion: 0.25
Nodes (7): assert_features_are_clean(), build_parser(), _median(), ArgumentParser, Training entry point for the Onyekpe INS baseline reproduction (P-06).      py, Run the repo's own leakage guard over the exact columns the model is fed. Return, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md)

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
Cohesion: 0.23
Nodes (6): GeoCoordinate, NavigationRoute, RouteManeuver, RouteService, SearchItem, SearchPreset

### Community 132 - "test_the_headers_iovnbd_actually_ships_pass_the_guard"
Cohesion: 0.12
Nodes (18): assert_no_leakage(), Raise LeakageError if any disallowed channel is present.      Called by the lo, Before the aliases, every one of these normalised to a name that was not on the, test_the_headers_iovnbd_actually_ships_pass_the_guard(), The same call the loader makes, on the same strings, before any drive is recorde, test_the_header_passes_the_leakage_guard_itself(), The leakage audit.  PS 26168 disallows wheel odometry. If this test ever passe, Whatever else changes, this module may never read a vehicle-dynamics channel. (+10 more)

### Community 135 - "test_the_truth_allowlist_is_a_strict_subset_of_position_and_time"
Cohesion: 0.12
Nodes (16): chi2_quantile(), _mean_nees(), (mean NEES, band low, band high) over NEES_RUNS deterministic seeds., Test 11, propagation alone: P0, Q_c, Van Loan and the nominal step against real, Test 11 with ZUPT applied at every detected stop. Measured 18.593, band [16.843,, Test 11 with ZARU at every detected stop -- **the case D-053 could not turn on.*, Test 11 with the full kinematic-constraint pair, which is how D-004 says they ru, Test 11, everything on. **This asserts one side of the band, and says why.** (+8 more)

### Community 136 - "test_the_truth_track_carries_no_inertial_channel"
Cohesion: 0.18
Nodes (11): Outage, One injected outage window, as sample indices into a sequence., Number of 1 s prediction epochs in this outage., _gnss_for(), Slice one outage window's epoch boundaries out of a position series.      Row, The naive strapdown baseline over one window, initialised from truth (D-064)., The GNSS-available baseline over one window, or None if no fix precedes it., _strapdown_for() (+3 more)

### Community 137 - "train"
Cohesion: 0.20
Nodes (11): The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, stem_family(), loss_fn(), make_optimizer(), Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, Fit the baseline. Returns `(model, scaler, history, split_sizes)`.      Publis, train() (+3 more)

### Community 138 - "ManeuverType"
Cohesion: 0.20
Nodes (10): ManeuverType, ARRIVE, SLIGHT_LEFT, SLIGHT_RIGHT, STRAIGHT, TUNNEL_ENTRY, TUNNEL_EXIT, TURN_LEFT (+2 more)

### Community 139 - "evaluate"
Cohesion: 0.20
Nodes (8): generate_sweep(), The full sweep across every held-out sequence, keyed by outage length.      ``, evaluate(), 0-1 feature scaling, fitted on the training windows **only** (D-071).      The, Score the trained baseline over the frozen outage sweep. Returns `(by_length, dr, Scaler, D-071. Fitting on train+test leaks the held-out range into training and **no den, test_the_scaler_is_fitted_on_what_it_was_given_and_nothing_else()

### Community 140 - "android/ — foreground logger & demo UI"
Cohesion: 0.22
Nodes (6): android/ — foreground logger & demo UI, Contract, Demo UI, GNSS, Non-negotiable platform facts, Threading

### Community 141 - "uk_utc_offset_s"
Cohesion: 0.22
Nodes (9): _last_sunday(), Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, uk_utc_offset_s(), Hand-computed from the rule, not from this function's own output.      BST run, A date-only rule would be an hour wrong for part of two days a year., test_bst_boundaries_are_the_published_ones_for_the_years_the_dataset_spans(), test_deep_winter_and_deep_summer_need_no_boundary_arithmetic() (+1 more)

### Community 142 - "OnyekpeBaseline"
Cohesion: 0.22
Nodes (5): OnyekpeBaseline, Tensor, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Hyperparameter

### Community 144 - "sample_rate_hz"
Cohesion: 0.50
Nodes (4): The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a de, sample_rate_hz(), No `sample_rate_hz` attribute means 10 Hz, exactly as before this loader existed, test_an_iovnbd_sequence_still_windows_at_the_protocol_rate()

## Knowledge Gaps
- **425 isolated node(s):** `GNSS`, `INS`, `INIT`, `STRAIGHT`, `TURN_RIGHT` (+420 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NavigationScreen()` connect `NavigationScreen` to `ReconvergenceToast`, `io_vnbd.py`, `_nhc_mount_run`, `make_optimizer`, `TelemetryPanel`, `TelemetryState`, `sample_rate_hz`, `HazardChips`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `InEKF` connect `FilterConfig` to `test_se23_derivation.py`, `test_filter.py`, `seconds_of_day_utc`, `MainActivity`, `ndarray`, `run.py`, `test_ffi_contract.py`, `propagate_nominal`, `inekf.py`, `test_mount.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `Sequence` connect `run.py` to `gauss_markov_bias_driving_noise`, `OnyekpeBaseline`, `propagate_nominal`, `inekf.py`, `cadence.py`, `chi2_gate`, `truth.py`, `Sequence`, `test_allan.py`, `sample_rate_hz`, `normalise`, `allan.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._