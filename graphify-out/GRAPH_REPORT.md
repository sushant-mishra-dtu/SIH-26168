# Graph Report - SIH-26168  (2026-09-13)

## Corpus Check
- 118 files · ~407,508 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2118 nodes · 4050 edges · 122 communities (103 shown, 19 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 247 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ad687eb2`
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
- _replay_record
- yaw_error
- TelemetryPanel
- gradlew
- sample_rate_hz
- assert_features_are_clean
- .aided_pass_summary
- test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window
- test_evaluate_outage_end_to_end

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 74 edges
2. `FilterConfig` - 63 edges
3. `evaluate_sequence()` - 43 edges
4. `Sequence` - 42 edges
5. `Outage` - 38 edges
6. `LeakageError` - 35 edges
7. `synthetic_drive()` - 35 edges
8. `load_sequence()` - 32 edges
9. `TruthPairingError` - 32 edges
10. `BaselineTrajectory` - 31 edges

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

## Communities (122 total, 19 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.05
Nodes (79): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+71 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.06
Nodes (42): a_ri(), Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_* slic, _gqg(), Executable check of the derivation in docs/SE23_PROPAGATION.md.  **Why this exis, `zaru_sigma` is not a free parameter, and this pins the identity that makes it n, A test that has never been seen to fail is not known to work (Gate 0's rule)., The residual from evaluating A at the step start is O(dt^2), which is what prove, The property the whole construction exists for. Assert it directly, per section (+34 more)

### Community 2 - "test_filter.py"
Cohesion: 0.06
Nodes (46): detect_mount_disturbance(), is_stationary(), nhc_is_valid(), Detect the phone being knocked, so R_sv covariance can be re-inflated.      A 5-, Detect a stopped vehicle for ZUPT/ZARU.      Both conditions must hold: low acce, Whether the non-holonomic constraint may be applied this step.      NHC says the, slice, The vectorised criterion must be the same criterion as `is_stationary`, not a lo (+38 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.07
Nodes (55): assert_uniform_grid(), evaluate_sequence(), gate1_ratio(), This stem cannot be graded, and the run says so rather than reporting a number a, Every window of every length for one sequence, all three methods.      One GNSS-, The Gate 1 number: physics-only median drift over GNSS-available median drift, a, Per-sample `dt`, refusing a stream that is not the 10 Hz grid the sweep assumes., Seconds to add to a sequence-relative time to put it on the truth track's clock. (+47 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.06
Nodes (48): assert_non_overlapping(), generate_outages(), generate_sweep(), mask_gnss(), ndarray, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic (+40 more)

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
Cohesion: 0.09
Nodes (30): AxisMeasurement, candidate_gyro(), _course_and_gyro(), main(), measure(), Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it, `(course_rate, gyro_mean, course_change, gyro_integral, keep)` over fix interval, Everything one stem has to say, or None if it cannot say anything. (+22 more)

### Community 10 - "run.py"
Cohesion: 0.11
Nodes (23): attempt_alignment(), fix_course_arrays(), fix_covariance(), in_motion_config(), ndarray, In-motion alignment at open fix `k`, completing the initialisation `initialise_f, 3x3 fix covariance from the receiver's horizontal accuracy., `(course_rad, speed_mps)` per distinct fix, or None when the stream carries neit (+15 more)

### Community 11 - "ndarray"
Cohesion: 0.19
Nodes (18): adjoint(), Error-state Kalman update, with the correction **subtracted** (D-050)., Pack (R, v, p) into the 5x5 SE_2(3) matrix of section 2., Section 2.1. Used by the GNSS update to move a left-invariant observation into t, se23_exp(), unpack(), x_of(), _numeric_h() (+10 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.09
Nodes (34): _cue_statistic(), _effective_samples(), pca_mount_yaw(), Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, AR(1) effective sample size of a serially correlated series, never below 2., `(t, positive)` for a sign cue: how many standard errors the mean product sits f, _drive_with_a_knock(), _driving_specific_force() (+26 more)

### Community 15 - "inekf.py"
Cohesion: 0.08
Nodes (45): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., OutageMetrics, The vehicle did not move over this window, so drift-% has no value (D-093)., Aggregate across sequences.      Reports the **median and 95th percentile** of (+37 more)

### Community 16 - "cadence.py"
Cohesion: 0.08
Nodes (41): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+33 more)

### Community 17 - "test_truth.py"
Cohesion: 0.05
Nodes (57): _last_sunday(), _parse_local_seconds(), Make a seconds-since-midnight series monotonic across a midnight rollover., Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, Parse the `S-` `date` column into seconds since midnight, **as shipped**., Local seconds since midnight per row, **not** unwrapped. NaN where the row does, The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-0 (+49 more)

### Community 18 - "truth.py"
Cohesion: 0.10
Nodes (20): _approx_residuals_m(), _best_lag_s(), _nearest(), ndarray, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t, Latitude/longitude at each epoch time, shape ``(n, 2)``., Local NED positions at each epoch time, relative to the first, shape ``(n, 2)``. (+12 more)

### Community 19 - "Stamp"
Cohesion: 0.14
Nodes (14): git_sha(), make_stamp(), Provenance stamping.  Every figure and table in the submission carries the com, Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes., One-line stamp for a figure caption or table footer., Seed every RNG we use and return the stamp describing this run.      Call once, Write the provenance line into a matplotlib figure itself.      In the figure,, seed_everything() (+6 more)

### Community 20 - "test_allan.py"
Cohesion: 0.12
Nodes (33): DeviceImuSequence, is_raw_imu_sidecar(), load_raw_imu_sidecar(), DataFrame, Path, The logger's raw inertial sidecar, read for Allan variance on our own hardware., One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-sort, A raw sidecar, shaped like a `Sequence` so the Allan module needs no second code (+25 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 22 - "load_sequence"
Cohesion: 0.10
Nodes (22): The check has to be sharp enough to catch the failure it exists for. At 16 m/s o, A pair that agrees only after a time shift is a finding about the dataset. Apply, `np.arange` accumulates float error, and a lag of -1.8e-14 in a committed artefa, `EVALUATION.md` section 2 was drafted as '1 Hz GNSS' from a paper written agains, Three stems -- Vta1a, Vta2, Vta1b -- really do update at 1 Hz, so the measuremen, Deduplicating across every GNSS column counted a row whose lat/lon repeated but, Fixes are not evenly spaced -- 9 s median, 109 s worst gap on a held-out stem --, They had no caller and no test when the cadence was measured, which is the shape (+14 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.13
Nodes (19): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, Metric unit tests, each against a hand-computed case.  Every number in the sub, The mean hides the tail and the tail is what a judge finds., Three epochs, each under-predicted by 1 m along-track.      Hand-computed: per, The pair exists precisely because they disagree: +2 and -2 cancel in CTE but not, There is no else-fallthrough in crse(): an unknown member must raise, not quietl, Hand-computed on four epochs of exactly 1 m error each.      Was a two-way tes (+11 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.15
Nodes (16): AllanReport, _fixed(), gauss_markov_bias_driving_noise(), main(), Path, Process-noise amplitude for a bias modelled as first-order Gauss-Markov., Everything one run of this module produced, ready to stamp and write., Per-axis, per-segment coefficients for one sensor, optionally white-band fits on (+8 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (25): geodetic_to_ned(), path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Local NED (north, east) offsets in metres relative to an origin fix.      Smal, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t (+17 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.09
Nodes (35): AllanCurve, analyse_segment(), bias_instability(), coefficients(), imu_arrays(), _loglog_slope(), NoiseCoefficients, overlapping_allan_deviation() (+27 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.29
Nodes (7): _manifest_rows(), Rows from the committed manifest -- the same file the loaders resolve paths thro, `V-vta9.csv` in the synchronised folder, `V-Vta9.csv` in the unsynchronised one., The cadence tool resolves `S-` files the same way, so the case and folder handli, test_manifest_lookup_serves_both_streams(), test_pairing_is_case_insensitive_where_the_dataset_is_not(), test_pairing_prefers_the_categorised_copy()

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.07
Nodes (35): _as_displayed(), _kotlin(), Path, The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, One line, with Kotlin's `"..." + "..."` joins closed up.      A caption long eno, The submission logger must be strictly offline (D-041). Without the permission,, Checked at the dependency rather than the call site: ensure android-ui does not, Drift-% and yaw error are computed in `eval/run.py::trajectory_record` and read (+27 more)

### Community 31 - "test_replay.py"
Cohesion: 0.08
Nodes (17): The replay renderer (P-13) and the artefact it reads.  Two things are tested,, The drift-and-crash case: a renamed field renders as `undefined` and the page dr, `length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page in, No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot, It has to survive someone editing the page a month from now without this convers, The specific failure D-039 exists to prevent. Asserted against the code path: th, Drift-% and yaw error come out of the artefact. If the page computed them it cou, A screenshot of the demo has to be self-evidencing (H-5), and an artefact from a (+9 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (27): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026), Gate 1 — the fix that holds the aided pass, and the split the data forces (13 Sep 2026) (+19 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.09
Nodes (36): FilterConfig, initial_covariance(), Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, Re-express a covariance built on *plain* errors in the filter's right-invariant, right_invariant_from_plain(), innovation_sequence(), ndarray (+28 more)

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
Cohesion: 0.17
Nodes (13): assert_truth_only(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, Including `GPS Velocity`, which is neither wheel-derived nor banned by name. Tru, test_the_truth_guard_rejects_every_other_vehicle_channel(), `EVALUATION.md` section 1.2 permits the `V-` GPS as *ground truth*. Truth is a p, The `V-` stream carries 'Indicated Longitudinal Acceleration'. A loose longitude (+5 more)

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.05
Nodes (68): assert_feature_safe(), assert_no_leakage(), LeakageError, normalise(), Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Raise LeakageError if any disallowed channel is present.      Called by the lo, Stricter guard for tensors entering a model or filter: inertial channels only. (+60 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.20
Nodes (15): Enum, crse(), CrseConvention, evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc (+7 more)

### Community 49 - "Sequence"
Cohesion: 0.18
Nodes (7): ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi, Sequence

### Community 50 - "Handover — seat A, Android: the map view and production readiness"
Cohesion: 0.10
Nodes (20): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — **built**, in `9fdd261`, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+12 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "octave_taus"
Cohesion: 0.09
Nodes (18): Bundle, Context, IBinder, Intent, Location, LocationListener, Sensor, SensorEvent (+10 more)

### Community 53 - "assert_no_leakage"
Cohesion: 0.12
Nodes (24): expm_series(), g_ri(), mount_yaw_from_dynamics(), _moving_average(), orthonormalise(), process_noise_psd(), ndarray, Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.  **This is t (+16 more)

### Community 54 - "normalise"
Cohesion: 0.08
Nodes (23): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propagat, Learned forward-speed pseudo-measurement with its predicted variance.          T, The two must not drift apart: a `P0` nobody uses is documentation, not a prior., The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages, The asymmetry is measured, not assumed (D-057): gating ZUPT takes its NEES from, Placeholders raise. A stub that returns None would let the harness produce plaus, The architectural claim, asserted rather than described.      There is no tunnel (+15 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.13
Nodes (23): epoch_windows(), The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., StemWindows, validation_families(), wrap_to_pi() (+15 more)

### Community 57 - "LoggerState"
Cohesion: 0.23
Nodes (5): Estimate, Location, LocalNavigationEstimator, toRadians(), TrackPoint

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.13
Nodes (15): loss_fn(), make_optimizer(), OnyekpeBaseline, Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, 0-1 feature scaling, fitted on the training windows **only** (D-071).      The (+7 more)

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
Cohesion: 0.22
Nodes (9): AssertionError, assert_no_family_straddles_the_split(), The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, No parent recording may have one segment in TRAIN and another in the held-out se, stem_family(), Lettered stems are segments of one drive. `Vw14b` held out while `Vw14a` and `Vw, A guard never observed to fire is not known to work. This one caught `Vw16a`/`Vw, test_no_parent_recording_is_split_across_train_and_test() (+1 more)

### Community 64 - "epoch_windows"
Cohesion: 0.14
Nodes (18): gammas(), The hat map: `skew(a) @ b == np.cross(a, b)`., Gamma_0, Gamma_1, Gamma_2 of docs/SE23_PROPAGATION.md section 8.1.      The seri, skew(), closed_form_gammas(), The cutoff must sit where the closed form is *still accurate*, not where it is 0, phi = 0 is the ZUPT case. It happens at every traffic light, not rarely., The left-invariant pose block *does* vary with yaw. If it did not, the test abov (+10 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "io_vnbd.py"
Cohesion: 0.12
Nodes (16): chi2_quantile(), _mean_nees(), (mean NEES, band low, band high) over NEES_RUNS deterministic seeds., Test 11, propagation alone: P0, Q_c, Van Loan and the nominal step against real, Test 11 with ZUPT applied at every detected stop. Measured 18.929, band [16.843,, Test 11 with ZARU at every detected stop -- **the case D-053 could not turn on.*, Test 11 with the full kinematic-constraint pair, which is how D-004 says they ru, Test 11, everything on. **This asserts one side of the band, and says why.** (+8 more)

### Community 67 - "uk_utc_offset_s"
Cohesion: 0.20
Nodes (9): build_parser(), DroppedWindow, ArgumentParser, Path, One outage window the paired `V-` track does not cover, and why (D-089).      A, `{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`, Write `summary.json`, `windows.csv` and one `trajectory_<seq>.json` per plotted, summarise_by_method_and_length() (+1 more)

### Community 68 - "ValueError"
Cohesion: 0.25
Nodes (3): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Tensor, ValueError

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.22
Nodes (8): Car-park mode, Contract, Known failure modes, Library choice — **settled: build it, do not adopt one (D-036)**, maps/ — OSM graph & HMM map matcher, Status, The pipeline, as designed, What lives here

### Community 71 - "train_baseline_rnn.py"
Cohesion: 0.13
Nodes (11): android/ — foreground logger & demo UI, Contract, Demo UI, GNSS, Non-negotiable platform facts, Threading, Building, IDR Navigator — operator UI prototype (+3 more)

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.29
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of()

### Community 74 - "make_optimizer"
Cohesion: 0.21
Nodes (12): ExtendedColors, IDRAnimations, IDRColors, IDRDarkPalette, IDRLightPalette, IDRPalette, NavigatorTheme(), ThemeMode (+4 more)

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.16
Nodes (15): exp_so3(), log_so3(), Rodrigues. Gamma_0 *is* the SO(3) exponential., se23_log(), _nees_inputs(), _nees_p0(), _nees_run(), _nhc_mount_run() (+7 more)

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.17
Nodes (13): propagate_nominal(), Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler s, _numeric_transition(), The gravity-sign test. A level phone at rest reads specific force -g in the body, Propagate true and estimated states from the SAME raw readings; differentiate th, Recorded because it is a free accuracy win Sprint 1 should take (section 8.1 not, The defining property: with no bias error, the attitude block of Phi is exactly, **The discriminating half**, without which the test above bounds nothing.      D (+5 more)

### Community 79 - "data/ — gitignored"
Cohesion: 0.40
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.33
Nodes (6): drift_percent(), Final position error as a percentage of ground-truth distance travelled., 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, test_drift_percent_hand_computed(), test_drift_percent_rejects_zero_distance()

### Community 81 - "chi2_gate"
Cohesion: 0.17
Nodes (9): chi2_gate(), chi-squared-gated GNSS position update. Returns whether the fix was accepted., Horizontal GNSS velocity update. Returns whether it was applied.          The re, Zero-angular-rate update, chi-squared gated. Returns whether it was applied., Mahalanobis gate. True means *accept* the measurement.      This single function, A 50 m jump on tunnel exit, against a 2 m-sigma covariance., After a long outage the filter is genuinely uncertain, so a big correction is co, test_inflated_covariance_admits_a_larger_correction() (+1 more)

### Community 82 - "TelemetryState"
Cohesion: 0.24
Nodes (7): StateFlow, NavigationMode, GNSS, INIT, INS, TelemetryState, TelemetryStore

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 86 - "MapView"
Cohesion: 0.29
Nodes (9): generateCirclePoints(), getVehicleIcon(), Context, Modifier, MapControlButton(), MapView(), Drawable, GeoPoint (+1 more)

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.07
Nodes (39): find_stationary_segments(), octave_taus(), Find stretches long and clean enough to compute an Allan curve on.      Statio, Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record., ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against pro, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so (+31 more)

### Community 98 - "Timebase"
Cohesion: 0.25
Nodes (6): dateFormat(), Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, java

### Community 99 - "AndroidSensorBackend"
Cohesion: 0.32
Nodes (3): AndroidSensorBackend, DeadReckoningBackend, StateFlow

### Community 106 - "MainActivity"
Cohesion: 0.36
Nodes (3): Bundle, MainActivity, ComponentActivity

### Community 107 - "train_baseline_rnn.py"
Cohesion: 0.25
Nodes (6): build_parser(), Hyperparameter, _median(), ArgumentParser, Training entry point for the Onyekpe INS baseline reproduction (P-06).      py, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md)

### Community 108 - "_aided_filter"
Cohesion: 0.25
Nodes (8): _aided_filter(), A filter mid-drive: heading north-east at 12 m/s, 200 m from the origin, with it, `z = v_hat[:2] - v_gnss`, `H = [-v_hat^, I, 0...]` on the horizontal rows, with, Ungated by default, for D-057's reason applied to the velocity: a refused Dopple, `gate=False` applies a fix the gate would refuse. The harness uses it after thre, test_gnss_velocity_update_is_ungated_by_default_and_gated_at_two_dof_on_request(), test_gnss_velocity_update_pulls_the_velocity_onto_the_measurement(), test_the_caller_can_override_the_position_gate()

### Community 109 - "NavigationScreen"
Cohesion: 0.43
Nodes (6): FloatingActionPill(), headingToDirection(), Modifier, NavigationScreen(), TunnelModeTogglePill(), androidx

### Community 110 - "_replay_record"
Cohesion: 0.33
Nodes (6): _cumulative(), Displacements -> positions relative to the window start, with the leading zero., Assemble one window's trajectory record for the renderer., One outage window, in the form the replay renderer reads. **Every field is measu, _replay_record(), trajectory_record()

### Community 111 - "yaw_error"
Cohesion: 0.40
Nodes (5): (RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].      Always r, yaw_error(), An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi, test_yaw_error_wraps_across_the_branch_cut(), test_yaw_error_zero_when_identical()

### Community 112 - "TelemetryPanel"
Cohesion: 0.83
Nodes (3): Modifier, MetricCard(), TelemetryPanel()

### Community 113 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 114 - "sample_rate_hz"
Cohesion: 0.50
Nodes (4): The rate the stationarity window is sized in. IO-VNBD is 10 Hz by protocol; a de, sample_rate_hz(), No `sample_rate_hz` attribute means 10 Hz, exactly as before this loader existed, test_an_iovnbd_sequence_still_windows_at_the_protocol_rate()

### Community 115 - "assert_features_are_clean"
Cohesion: 0.50
Nodes (4): assert_features_are_clean(), Run the repo's own leakage guard over the exact columns the model is fed. Return, The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject()

## Knowledge Gaps
- **320 isolated node(s):** `GNSS`, `INS`, `INIT`, `LIGHT`, `DARK` (+315 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InEKF` connect `normalise` to `seconds_of_day_utc`, `test_filter.py`, `uk_utc_offset_s`, `ValueError`, `test_harness_wiring.py`, `test_se23_derivation.py`, `FilterConfig`, `InEKF`, `run.py`, `ndarray`, `test_ffi_contract.py`, `_aided_filter`, `test_mount.py`, `inekf.py`, `OnyekpeBaseline`, `chi2_gate`, `propagate_nominal`, `assert_no_leakage`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `FilterConfig` connect `seconds_of_day_utc` to `test_baselines.py`, `test_se23_derivation.py`, `test_filter.py`, `uk_utc_offset_s`, `test_harness_wiring.py`, `io_vnbd.py`, `FilterConfig`, `run.py`, `test_ffi_contract.py`, `_aided_filter`, `test_mount.py`, `OnyekpeBaseline`, `inekf.py`, `assert_no_leakage`, `normalise`, `gauss_markov_bias_driving_noise`, `overlapping_allan_deviation`, `allan.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `Sequence` connect `Sequence` to `gauss_markov_bias_driving_noise`, `uk_utc_offset_s`, `test_harness_wiring.py`, `test_leakage.py`, `inekf.py`, `cadence.py`, `truth.py`, `sample_rate_hz`, `test_allan.py`, `allan.py`, `overlapping_allan_deviation`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._