# Graph Report - SIH-26168  (2026-09-13)

## Corpus Check
- 118 files · ~410,928 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2133 nodes · 4082 edges · 117 communities (102 shown, 15 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 247 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d736e8fc`
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
- TelemetryPanel
- gradlew
- sample_rate_hz
- assert_features_are_clean

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 74 edges
2. `FilterConfig` - 67 edges
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
- `Alignment` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (117 total, 15 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.13
Nodes (24): BaselineTrajectory, course_over_ground(), Score any baseline against the paired `V-` truth over one window.      Every n, One baseline's answer over one outage window, at the protocol's 1 s prediction c, Heading made good over each epoch, radians, from NED displacements.      Used, score(), Tests for the two Gate 1 baselines.  Every numerical case here is hand-compute, `atan2` of a sub-centimetre displacement is a uniformly-distributed angle, and a (+16 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.03
Nodes (71): gammas(), Gamma_0, Gamma_1, Gamma_2 of docs/SE23_PROPAGATION.md section 8.1.      The se, chi2_quantile(), closed_form_gammas(), _mean_nees(), Executable check of the derivation in docs/SE23_PROPAGATION.md.  **Why this ex, (mean NEES, band low, band high) over NEES_RUNS deterministic seeds., Test 11, propagation alone: P0, Q_c, Van Loan and the nominal step against real (+63 more)

### Community 2 - "test_filter.py"
Cohesion: 0.04
Nodes (77): chi2_gate(), detect_mount_disturbance(), initial_covariance(), is_stationary(), nhc_is_valid(), Mahalanobis gate. True means *accept* the measurement.      This single functi, Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG (+69 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.05
Nodes (57): Outage, One injected outage window, as sample indices into a sequence., Number of 1 s prediction epochs in this outage., assert_uniform_grid(), evaluate_sequence(), Slice one outage window's epoch boundaries out of a position series.      Row, This stem cannot be graded, and the run says so rather than reporting a number a, Every window of every length for one sequence, all three methods.      One GNS (+49 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.05
Nodes (51): AssertionError, generate_outages(), mask_gnss(), ndarray, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic, assert_no_family_straddles_the_split(), assert_split_disjoint() (+43 more)

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
Cohesion: 0.40
Nodes (5): _preferred_copy(), Path, Pick deterministically between multiple copies of the same stem.      Every on, `candidates[0]` off a glob made the choice by filesystem ordering, and the two c, test_load_split_picks_between_divergent_copies_deterministically()

### Community 9 - "InEKF"
Cohesion: 0.09
Nodes (25): _parse_local_seconds(), Make a seconds-since-midnight series monotonic across a midnight rollover., Parse the `S-` `date` column into seconds since midnight, **as shipped**., Local seconds since midnight per row, **not** unwrapped. NaN where the row does, The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-0, seconds_of_day(), seconds_of_day_utc(), unwrap_time_of_day() (+17 more)

### Community 10 - "run.py"
Cohesion: 0.07
Nodes (50): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Learned forward-speed pseudo-measurement with its predicted variance., apply_alignment(), attempt_alignment(), _check_physical(), course_sigma_rad(), _cumulative() (+42 more)

### Community 11 - "ndarray"
Cohesion: 0.10
Nodes (32): adjoint(), ndarray, Error-state Kalman update, with the correction **subtracted** (D-050)., Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Section 7.2. Returns `(v_veh_hat, H_veh)` with the mount column carried., chi-squared-gated GNSS position update. Returns whether the fix was accepted., Horizontal GNSS velocity update. Returns whether it was applied.          The, Non-holonomic pseudo-measurement. Caller checks nhc_is_valid() first. (+24 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.07
Nodes (44): exp_so3(), log_so3(), pca_mount_yaw(), propagate_nominal(), Rodrigues. Gamma_0 *is* the SO(3) exponential., Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler s, Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, se23_log() (+36 more)

### Community 15 - "inekf.py"
Cohesion: 0.08
Nodes (31): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Sequence (+23 more)

### Community 16 - "cadence.py"
Cohesion: 0.10
Nodes (29): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+21 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (27): Ground truth from the paired `V-` VBOX GPS, and the cadence measurement behind i, Not a style point. A velocity column here becomes a speed label the first time s, `TruthTrack` is deliberately not a `Sequence`. There is no call that hands it to, The failure a new folder layout produces must say what to add, not just that it, `per_epoch_errors` compares displacements, so a constant offset between two traj, A finding, pinned so it cannot quietly change.      All 72 `S-` stems in the s, The pool is 72 stems, and it is 72 exactly rather than "roughly 72".      Read, If a split entry were outside the pool, the pool would be the wrong set to re-pi (+19 more)

### Community 18 - "truth.py"
Cohesion: 0.10
Nodes (21): _approx_residuals_m(), _best_lag_s(), _nearest(), ndarray, Ground truth from the paired `V-` VBOX GPS.  **Why this module exists.** `docs, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t, Latitude/longitude at each epoch time, shape ``(n, 2)``. (+13 more)

### Community 19 - "Stamp"
Cohesion: 0.14
Nodes (15): git_sha(), make_stamp(), Path, Provenance stamping.  Every figure and table in the submission carries the com, Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes., Everything needed to regenerate an artefact., One-line stamp for a figure caption or table footer., False if this artefact came from a dirty or non-git tree. (+7 more)

### Community 20 - "test_allan.py"
Cohesion: 0.12
Nodes (33): DeviceImuSequence, is_raw_imu_sidecar(), load_raw_imu_sidecar(), DataFrame, Path, The logger's raw inertial sidecar, read for Allan variance on our own hardware., One stream's rows, numeric, de-duplicated on `event_ns` (first wins), stamp-sort, A raw sidecar, shaped like a `Sequence` so the Allan module needs no second code (+25 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 22 - "load_sequence"
Cohesion: 0.11
Nodes (30): load_sequence(), Load one sequence CSV.      Raises LeakageError if the file contains any disal, align_to_sequence(), load_truth(), Read lat, lon and time of day from one `V-` file.      The header is read on i, Compare a loaded `S-` sequence's own GPS fixes against the paired `V-` track., load_windows(), Windows for every stem that can supply them, and the reason each of the others c (+22 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.11
Nodes (22): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, (RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].      Always r, yaw_error(), Metric unit tests, each against a hand-computed case.  Every number in the sub, An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi, The mean hides the tail and the tail is what a judge finds., Three epochs, each under-predicted by 1 m along-track.      Hand-computed: per (+14 more)

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
Cohesion: 0.10
Nodes (26): AllanCurve, analyse_segment(), bias_instability(), coefficients(), imu_arrays(), _loglog_slope(), NoiseCoefficients, octave_taus() (+18 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.16
Nodes (15): manifest_path_for(), paired_truth_path(), Locate one shipped file by stem and stream, via the checksum manifest.      Vi, The `V-` file paired with an `S-` stem: this sequence's ground truth., _manifest_rows(), Rows from the committed manifest -- the same file the loaders resolve paths thro, `V-vta9.csv` in the synchronised folder, `V-Vta9.csv` in the unsynchronised one., Eleven stems ship on one stream only (D-044). A stem with no paired truth must b (+7 more)

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.07
Nodes (35): _as_displayed(), _kotlin(), Path, The two Android surfaces, held to the rules `tests/test_replay.py` holds the web, One line, with Kotlin's `"..." + "..."` joins closed up.      A caption long eno, The submission logger must be strictly offline (D-041). Without the permission,, Checked at the dependency rather than the call site: ensure android-ui does not, Drift-% and yaw error are computed in `eval/run.py::trajectory_record` and read (+27 more)

### Community 31 - "test_replay.py"
Cohesion: 0.05
Nodes (39): epoch_windows(), `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, `y` is `(distance, d_heading, d_distance)` and `TARGET_COLUMNS` indexes into it., 15 m/s due north for 300 s: every 1 s epoch is 15 m of travel and no change of h, D-089's rule, one level down. A VBOX blink must not cost a whole drive.      F, test_a_truth_gap_drops_epochs_rather_than_the_sequence(), test_epoch_windows_recovers_the_drive_it_was_given(), test_the_three_target_columns_are_what_they_claim_to_be() (+31 more)

### Community 32 - "Decision Log"
Cohesion: 0.07
Nodes (28): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Demo Operator UI — Live Online OpenStreetMap Integration (13 Sep 2026), Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 0 — the Allan seeds regenerate from the commit their stamp names (13 Sep 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026) (+20 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.09
Nodes (38): FilterConfig, Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, AxisMeasurement, candidate_gyro(), _course_and_gyro(), innovation_sequence(), main(), measure() (+30 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-115 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.11
Nodes (23): audit_table(), build_parser(), main(), _median(), ArgumentParser, Training entry point for the Onyekpe INS baseline reproduction (P-06).      py, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md), The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in th (+15 more)

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
Cohesion: 0.11
Nodes (23): LeakageError, A disallowed channel reached a feature path.      Deliberately an AssertionErr, assert_truth_only(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, Time Since Start of Day (seconds)' is a 'V-' column and a different quantity. If, The aliases must not have widened the guard. These are the real 'V-' column name (+15 more)

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.09
Nodes (33): normalise(), Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Generic paren-stripping collapsed all three to the single name 'orientation'., The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder writes, test_a_truncated_date_format_string_still_normalises(), test_both_shipped_gyro_spellings_reach_the_same_canonical_names(), test_the_satellite_column_ships_with_and_without_the_gps_prefix(), test_the_three_orientation_columns_stay_three_columns() (+25 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.15
Nodes (19): Enum, crse(), CrseConvention, evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc (+11 more)

### Community 49 - "Sequence"
Cohesion: 0.14
Nodes (7): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi, Tensor, ValueError

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
Cohesion: 0.08
Nodes (39): a_ri(), _cue_statistic(), _effective_samples(), expm_series(), g_ri(), mount_yaw_from_dynamics(), _moving_average(), orthonormalise() (+31 more)

### Community 54 - "normalise"
Cohesion: 0.13
Nodes (18): assert_no_leakage(), Raise LeakageError if any disallowed channel is present.      Called by the lo, Before the aliases, every one of these normalised to a name that was not on the, test_the_headers_iovnbd_actually_ships_pass_the_guard(), The same call the loader makes, on the same strings, before any drive is recorde, test_the_header_passes_the_leakage_guard_itself(), The leakage audit.  PS 26168 disallows wheel odometry. If this test ever passe, Whatever else changes, this module may never read a vehicle-dynamics channel. (+10 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.18
Nodes (13): Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., wrap_to_pi(), P-06: the Onyekpe reproduction's data path, split rule and leakage guard.  Del, The real failure this rule exists for: `S1` is 43% of the windows and `Vw14` 32%, 359 degrees to 1 degree is +2, not -358. Unwrapped, a single wrap puts a 6.2 rad, Two constants, two modules, one meaning. `train` asserts this at run time; this, D-071. Fitting on train+test leaks the held-out range into training and **no den, test_a_degenerate_split_raises_rather_than_training_on_it() (+5 more)

### Community 57 - "LoggerState"
Cohesion: 0.23
Nodes (5): Estimate, Location, LocalNavigationEstimator, toRadians(), TrackPoint

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.11
Nodes (18): loss_fn(), make_optimizer(), OnyekpeBaseline, Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, Hyperparameter (+10 more)

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
Cohesion: 0.15
Nodes (19): naive_strapdown(), **Naive strapdown baseline.** Mechanise the raw IMU with no constraints, no lear, _level_imu(), **Deliberately asserting the null result**, because the obvious intuition is wro, Due east at 15 m/s must come out as (0, 15) per epoch, not (15, 0)., A perfectly still, level phone, plus whatever bias the case is about.      A s, The 10 mg case again, this time all the way through to the graded number., The null case. If this drifts, every number below it is measuring the integrator (+11 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "io_vnbd.py"
Cohesion: 0.17
Nodes (16): epoch_times(), gnss_available(), **GNSS-available baseline.** What the system reports when the signal is never de, Epoch boundary times for one outage window: `length_s // cadence_s + 1` of them., With a fix on every epoch boundary the hold is the identity, so this isolates th, Fixes at t = 0 and t = 9, epochs at t = 0..10. Hand-computed: epochs 1-8 hold fi, A window opening before the first fix has nothing to hold. Holding the *next* fi, `n` displacements need `n + 1` positions. Off by one here silently shortens ever (+8 more)

### Community 67 - "uk_utc_offset_s"
Cohesion: 0.20
Nodes (10): assert_non_overlapping(), Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, build_parser(), main(), plan_sweep(), ArgumentParser, Path, Generate and validate the outage sweep. Validation is not optional. (+2 more)

### Community 68 - "ValueError"
Cohesion: 0.19
Nodes (11): initial_state_from_truth(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is, Navigation-from-body rotation for a level vehicle on a given heading., `(R0, v0)` for the naive strapdown baseline, taken from ground truth at the outa, yaw_only_rotation(), generate_sweep(), Synthetic GNSS-outage injection.  Protocol: docs/EVALUATION.md section 3. Leng (+3 more)

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
Cohesion: 0.40
Nodes (5): _nees_inputs(), _nees_p0(), ndarray, The Monte-Carlo prior.      **This is the test's experimental design, not a pr, (omega, specific force, truly stopped) for step `k`: cruise, brake, stop, pull a

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.22
Nodes (10): Aggregate across sequences.      Reports the **median and 95th percentile** of, summarise(), gate1_ratio(), `{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`, The Gate 1 number: physics-only median drift over GNSS-available median drift, a, summarise_by_method_and_length(), A ratio quoted without its sample size is the number a judge asks about second., No 60 s windows means no Gate 1 number. Saying so is the only correct output. (+2 more)

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
Cohesion: 0.09
Nodes (33): find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so, The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestam, Idling with an occupant passes the ZUPT detector and must still be excluded from (+25 more)

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
Cohesion: 0.22
Nodes (9): _last_sunday(), Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, uk_utc_offset_s(), Hand-computed from the rule, not from this function's own output.      BST run, A date-only rule would be an hour wrong for part of two days a year., test_bst_boundaries_are_the_published_ones_for_the_years_the_dataset_spans(), test_deep_winter_and_deep_summer_need_no_boundary_arithmetic() (+1 more)

### Community 108 - "_aided_filter"
Cohesion: 0.50
Nodes (4): detector_settings(), The stationarity rule the segments were found under, for the summary's provenanc, The summary records the stationarity rule its segments were found under, and it, test_the_committed_artefacts_were_made_under_the_current_detector()

### Community 109 - "NavigationScreen"
Cohesion: 0.43
Nodes (6): FloatingActionPill(), headingToDirection(), Modifier, NavigationScreen(), TunnelModeTogglePill(), androidx

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
Cohesion: 0.22
Nodes (10): assert_feature_safe(), Stricter guard for tensors entering a model or filter: inertial channels only., assert_features_are_clean(), Run the repo's own leakage guard over the exact columns the model is fed. Return, The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject(), The two guards have to disagree in the right direction: the truth loader may rea, test_truth_columns_can_never_become_model_features() (+2 more)

## Knowledge Gaps
- **321 isolated node(s):** `GNSS`, `INS`, `INIT`, `LIGHT`, `DARK` (+316 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FilterConfig` connect `seconds_of_day_utc` to `gauss_markov_bias_driving_noise`, `test_baselines.py`, `test_filter.py`, `test_harness_wiring.py`, `test_se23_derivation.py`, `run.py`, `test_ffi_contract.py`, `_aided_filter`, `test_mount.py`, `inekf.py`, `assert_no_leakage`, `allan.py`, `overlapping_allan_deviation`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `InEKF` connect `run.py` to `seconds_of_day_utc`, `test_filter.py`, `test_harness_wiring.py`, `test_se23_derivation.py`, `test_ffi_contract.py`, `ndarray`, `test_mount.py`, `inekf.py`, `Sequence`, `assert_no_leakage`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `load_sequence()` connect `load_sequence` to `seconds_of_day_utc`, `test_protocol.py`, `main`, `ValueError`, `FilterConfig`, `LeakageError`, `test_leakage.py`, `inekf.py`, `cadence.py`, `chi2_gate`, `Sequence`, `test_truth.py`, `normalise`, `allan.py`, `overlapping_allan_deviation`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._