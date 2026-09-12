# Graph Report - SIH-26168  (2026-09-12)

## Corpus Check
- 97 files · ~178,659 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1831 nodes · 3480 edges · 106 communities (90 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 179 edges (avg confidence: 0.66)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `56625660`
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
- _replay_record
- yaw_error
- eval/ — the harness
- SessionExporterTest
- gradlew
- wrap_to_pi
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
- test_a_real_metric_defect_is_not_swallowed_as_a_dropped_window
- test_only_sum_abs_makes_the_published_tables_consistent
- idr-26168

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 64 edges
2. `FilterConfig` - 50 edges
3. `evaluate_sequence()` - 42 edges
4. `LeakageError` - 35 edges
5. `synthetic_drive()` - 35 edges
6. `Sequence` - 34 edges
7. `Outage` - 33 edges
8. `load_sequence()` - 32 edges
9. `TruthTrack` - 31 edges
10. `TruthPairingError` - 28 edges

## Surprising Connections (you probably didn't know these)
- `AllanCurve` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `AllanReport` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `NoiseCoefficients` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `StationarySegment` --uses--> `FilterConfig`  [INFERRED]
  eval/allan.py → core/reference/inekf.py
- `DroppedWindow` --uses--> `FilterConfig`  [INFERRED]
  eval/run.py → core/reference/inekf.py

## Import Cycles
- None detected.

## Communities (106 total, 16 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.06
Nodes (67): BaselineTrajectory, course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is (+59 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.04
Nodes (59): adjoint(), gammas(), Section 2.1. Used by the GNSS update to move a left-invariant observation into t, Gamma_0, Gamma_1, Gamma_2 of docs/SE23_PROPAGATION.md section 8.1.      The se, se23_hat(), chi2_quantile(), closed_form_gammas(), _mean_nees() (+51 more)

### Community 2 - "test_filter.py"
Cohesion: 0.05
Nodes (55): chi2_gate(), detect_mount_disturbance(), initial_covariance(), is_stationary(), NavState, nhc_is_valid(), `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, Nominal state. Covariance is carried separately as an 18x18 on the error state. (+47 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.07
Nodes (55): The vehicle did not move over this window, so drift-% has no value (D-093)., ZeroDistanceOutage, evaluate_sequence(), This stem cannot be graded, and the run says so rather than reporting a number a, Seconds to add to a sequence-relative time to put it on the truth track's clock., Every window of every length for one sequence, all three methods.      One fil, SequenceUnusable, truth_clock_offset_s() (+47 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.06
Nodes (46): assert_non_overlapping(), generate_outages(), generate_sweep(), mask_gnss(), Outage, ndarray, Synthetic GNSS-outage injection.  Protocol: docs/EVALUATION.md section 3. Leng, Verify the non-overlap guarantee. Cheap to check, expensive to discover violated (+38 more)

### Community 5 - "RecordsTest"
Cohesion: 0.08
Nodes (14): Fix, GnssHub, Bundle, Handler, Summary, SatSample, Summary, CsvRow (+6 more)

### Community 6 - "RateStatsTest"
Cohesion: 0.06
Nodes (16): Snapshot, RateStats, Snapshot, fmt(), FloatArray, Handler, Snapshot, RawSample (+8 more)

### Community 7 - "7. The phases"
Cohesion: 0.04
Nodes (49): 0.1 Authority order, 0. What this file is, and what it is not, 10. Stop conditions — stop immediately and report, 11. Findings — agents may append here, 1.1 The loop — every task, no exceptions, 1.2 Rules about this file itself, 1.3 Session bootstrap prompt — paste this first, every session, 1. How to follow this file (+41 more)

### Community 8 - "FilterConfig"
Cohesion: 0.09
Nodes (43): FilterConfig, Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, AxisMeasurement, candidate_gyro(), _course_and_gyro(), innovation_sequence(), main(), measure() (+35 more)

### Community 9 - "InEKF"
Cohesion: 0.05
Nodes (37): InEKF, Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Section 7.1. `H_vb = [0, R_hat^T, 0, 0, 0, 0]` -- the attitude column is exactly, Zero-velocity update. Observes accelerometer bias.          Uses section **7.1, Learned forward-speed pseudo-measurement with its predicted variance., The measured failure D-053 recorded and P-04 diagnosed: `is_stationary` averages, The asymmetry is measured, not assumed (D-057): gating ZUPT takes its NEES from, Placeholders raise. A stub that returns None would let the harness produce plaus (+29 more)

### Community 10 - "run.py"
Cohesion: 0.09
Nodes (34): AssertionError, build_parser(), DroppedWindow, gate1_ratio(), _gnss_for(), main(), plan_sweep(), ArgumentParser (+26 more)

### Community 11 - "ndarray"
Cohesion: 0.10
Nodes (33): exp_so3(), log_so3(), ndarray, Rodrigues. Gamma_0 *is* the SO(3) exponential., Pack (R, v, p) into the 5x5 SE_2(3) matrix of section 2., Error-state Kalman update, with the correction **subtracted** (D-050)., Section 7.2. Returns `(v_veh_hat, H_veh)` with the mount column carried., chi-squared-gated GNSS position update. Returns whether the fix was accepted. (+25 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.08
Nodes (34): MountInit, pca_mount_yaw(), What the PCA initialiser found: the mount rotation, and how well it is pinned do, Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, _drive_with_a_knock(), _driving_specific_force(), `R_sv` -- the PCA initialiser, in-filter estimation, and the bump detector (P-11, `spread_rad` is the standard error of the principal-axis angle, so it must fall (+26 more)

### Community 14 - "SessionClock"
Cohesion: 0.08
Nodes (8): dateFormat(), SessionClock, Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, SessionClockTest, java

### Community 15 - "inekf.py"
Cohesion: 0.11
Nodes (30): a_ri(), expm_series(), g_ri(), orthonormalise(), process_noise_psd(), Reference InEKF on SE_2(3) -- state layout, gating, and interfaces.  **This is, Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, Nearest rotation matrix in the Frobenius sense, with the reflection branch exclu (+22 more)

### Community 16 - "cadence.py"
Cohesion: 0.10
Nodes (29): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+21 more)

### Community 17 - "test_truth.py"
Cohesion: 0.08
Nodes (28): _preferred_copy(), Path, Pick deterministically between multiple copies of the same stem.      Every on, Ground truth from the paired `V-` VBOX GPS, and the cadence measurement behind i, Not a style point. A velocity column here becomes a speed label the first time s, `TruthTrack` is deliberately not a `Sequence`. There is no call that hands it to, `per_epoch_errors` compares displacements, so a constant offset between two traj, A finding, pinned so it cannot quietly change.      All 72 `S-` stems in the s (+20 more)

### Community 18 - "truth.py"
Cohesion: 0.11
Nodes (21): _approx_residuals_m(), _best_lag_s(), _nearest(), _parse_local_seconds(), ndarray, Ground truth from the paired `V-` VBOX GPS.  **Why this module exists.** `docs, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else., Nearest-sample indices for a set of epoch times. Raises if any is further than t (+13 more)

### Community 19 - "Stamp"
Cohesion: 0.08
Nodes (26): FilterDivergedError, FilterInit, FilterRun, The filter's own state left the bounds a moving car can produce.      Caught i, Everything one pass of the filter produced, at every sample., What the filter was started from, so a run can be read for whether it was starte, git_sha(), make_stamp() (+18 more)

### Community 20 - "test_allan.py"
Cohesion: 0.12
Nodes (25): find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ndarray, Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so, The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestam, Idling with an occupant passes the ZUPT detector and must still be excluded from (+17 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 22 - "load_sequence"
Cohesion: 0.12
Nodes (28): load_sequence(), Load one sequence CSV.      Raises LeakageError if the file contains any disal, align_to_sequence(), load_truth(), Read lat, lon and time of day from one `V-` file.      The header is read on i, Compare a loaded `S-` sequence's own GPS fixes against the paired `V-` track., The check has to be sharp enough to catch the failure it exists for. At 16 m/s o, A pair that agrees only after a time shift is a finding about the dataset. Apply (+20 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.13
Nodes (27): crse(), cte(), evaluate_outage(), per_epoch_errors(), ndarray, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc, Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, Cumulative Root Square Error, in metres. See CrseConvention for which reading an (+19 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.13
Nodes (21): AllanReport, analyse_segment(), _fixed(), main(), NoiseCoefficients, Path, Allan variance from IO-VNBD's own stationary segments.  Seeds the InEKF proces, Longest averaging time this segment supports at MAX_TAU_FRACTION. (+13 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (23): path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t, vincenty_inverse(), wrap_to_pi() (+15 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.11
Nodes (23): AllanCurve, bias_instability(), coefficients(), overlapping_allan_deviation(), random_walk_coefficient(), An overlapping Allan deviation curve for one axis of one segment., Log-log interpolated deviation at an arbitrary tau., Overlapping Allan deviation of a rate signal.      `sigma^2(tau) = 1 / (2 tau^ (+15 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.10
Nodes (24): manifest_path_for(), paired_truth_path(), Locate one shipped file by stem and stream, via the checksum manifest.      Vi, The `V-` file paired with an `S-` stem: this sequence's ground truth., No usable paired `V-` file, or more than one that disagree.      Not a Leakage, TruthPairingError, LookupError, _manifest_rows() (+16 more)

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.13
Nodes (23): _const(), _header_from_kotlin(), _int_const(), _kotlin(), Path, The Android logger's CSV schema, checked against the loader that has to read it., The app records uncalibrated accel and gyro -- `android/README.md` requires it,, `eval/outages/inject.py` sizes every outage from `SAMPLE_RATE_HZ`. A file at a d (+15 more)

### Community 31 - "test_replay.py"
Cohesion: 0.08
Nodes (17): The replay renderer (P-13) and the artefact it reads.  Two things are tested,, The drift-and-crash case: a renamed field renders as `undefined` and the page dr, `length_s + 1` epoch boundaries against `10 * length_s` IMU samples. The page in, No CDN, no font, no map SDK, no analytics. A demo that needs the network cannot, It has to survive someone editing the page a month from now without this convers, The specific failure D-039 exists to prevent. Asserted against the code path: th, Drift-% and yaw error come out of the artefact. If the page computed them it cou, A screenshot of the demo has to be self-evidencing (H-5), and an artefact from a (+9 more)

### Community 32 - "Decision Log"
Cohesion: 0.09
Nodes (23): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026), Rebase — the logger's speed column against D-102 (4 Sep 2026), Seat A — the foreground logger (3 Sep 2026) (+15 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.10
Nodes (23): Make a seconds-since-midnight series monotonic across a midnight rollover., Parse the `S-` `date` column into seconds since midnight, **as shipped**., The same column, converted from UK local time to UTC -- the `V-` VBOX clock (D-0, seconds_of_day(), seconds_of_day_utc(), unwrap_time_of_day(), IO-VNBD includes night driving. Without this a sequence crossing midnight reads, The spelling the `S-` header advertises. Kept: it is what the format string prom (+15 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (20): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs, 3.3 Angular random walk is not the problem at these timescales (+12 more)

### Community 36 - "main"
Cohesion: 0.13
Nodes (18): audit_table(), main(), The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in th, The Onyekpe reproduction's hyperparameter audit (P-06).  Tests the *audit*, no, G-4 and D-009's discipline. An omitted hyperparameter is a choice *we* make, and, The inverse, which is the more dangerous direction: quietly relabelling a publis, The INS paper does not surface its loss or optimiser; those two rows come from W, Features are scaled 0-1 and the papers do not say on which set the scaler is fit (+10 more)

### Community 37 - "LoggerService"
Cohesion: 0.20
Nodes (5): Handler, LoggerService, HandlerThread, PowerManager, Service

### Community 38 - "MainActivity"
Cohesion: 0.16
Nodes (7): AppCompatActivity, Bundle, Button, TextView, MainActivity, IBinder, Intent

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
Cohesion: 0.18
Nodes (15): LeakageError, A disallowed channel reached a feature path.      Deliberately an AssertionErr, assert_truth_only(), normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, Raise unless every column is one of lat, lon, time of day.      An allowlist,, Including `GPS Velocity`, which is neither wheel-derived nor banned by name. Tru, test_the_truth_guard_rejects_every_other_vehicle_channel() (+7 more)

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.14
Nodes (12): The leakage audit.  PS 26168 disallows wheel odometry. If this test ever passe, Whatever else changes, this module may never read a vehicle-dynamics channel., The truth path is a separate module on purpose. `load_sequence` must not have ac, Structural, not procedural. `TruthTrack` holds four fields and none of them is a, Each of these is a real IO-VNBD 'V-' column name., LeakageError subclasses AssertionError so a bare `except Exception` does not swa, test_banned_vehicle_channels_raise(), test_guard_is_not_catchable_as_a_normal_error() (+4 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.18
Nodes (11): Enum, CrseConvention, OutageMetrics, The four metrics. This module owns every number in the submission.  Read docs/, How "Cumulative Root Square Error" is read. **Settled against the paper** -- D-0, Aggregate across sequences.      Reports the **median and 95th percentile** of, Result for a single outage sequence. Every field is reported; none is optional., summarise() (+3 more)

### Community 49 - "Sequence"
Cohesion: 0.18
Nodes (7): ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Refuses. The drift-% denominator is not measured off 9 s fixes., One loaded IO-VNBD sequence, guarded and canonicalised.      ``imu`` holds the, Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi, Sequence

### Community 50 - "Handover — seat A, Android: the map view and production readiness"
Cohesion: 0.17
Nodes (10): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — buildable today, no filter needed, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+2 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "octave_taus"
Cohesion: 0.17
Nodes (12): imu_arrays(), _loglog_slope(), octave_taus(), ndarray, Pull `(t_s, accel, gyro)` out of a loaded sequence as float arrays.      Rows, Mean over every length-`window` slice, via cumulative sums. Shape (n - window +, Half-open [start, stop) index pairs of every run of True., Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record. (+4 more)

### Community 53 - "assert_no_leakage"
Cohesion: 0.17
Nodes (12): assert_no_leakage(), Raise LeakageError if any disallowed channel is present.      Called by the lo, Before the aliases, every one of these normalised to a name that was not on the, The aliases must not have widened the guard. These are the real 'V-' column name, test_the_headers_iovnbd_actually_ships_pass_the_guard(), test_the_v_stream_header_is_still_rejected_wholesale(), The same call the loader makes, on the same strings, before any drive is recorde, test_the_header_passes_the_leakage_guard_itself() (+4 more)

### Community 54 - "normalise"
Cohesion: 0.17
Nodes (12): normalise(), Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, Generic paren-stripping collapsed all three to the single name 'orientation'., The categorised folder writes Yaw/Pitch/Roll and the uncategorised folder writes, Time Since Start of Day (seconds)' is a 'V-' column and a different quantity. If, test_a_truncated_date_format_string_still_normalises(), test_both_shipped_gyro_spellings_reach_the_same_canonical_names(), test_the_satellite_column_ships_with_and_without_the_gps_prefix() (+4 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.26
Nodes (11): The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, StemWindows, validation_families(), P-06: the Onyekpe reproduction's data path, split rule and leakage guard.  Del, The real failure this rule exists for: `S1` is 43% of the windows and `Vw14` 32%, Two constants, two modules, one meaning. `train` asserts this at run time; this, test_a_degenerate_split_raises_rather_than_training_on_it() (+3 more)

### Community 57 - "LoggerState"
Cohesion: 0.20
Nodes (5): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.20
Nodes (9): The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, stem_family(), 0-1 feature scaling, fitted on the training windows **only** (D-071).      The, Fit the baseline. Returns `(model, scaler, history, split_sizes)`.      Publis, Scaler, train(), D-071. Fitting on train+test leaks the held-out range into training and **no den, test_the_scaler_is_fitted_on_what_it_was_given_and_nothing_else() (+1 more)

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
Cohesion: 0.20
Nodes (10): assert_feature_safe(), Stricter guard for tensors entering a model or filter: inertial channels only., The phase wants the guard's output pasted, which is worth nothing if the guard c, test_the_leakage_guard_runs_over_the_feature_columns_and_can_reject(), The two guards have to disagree in the right direction: the truth loader may rea, GNSS is reference and gated-update only.      A model trained on GNSS features, test_gnss_is_allowed_but_never_a_feature(), test_truth_columns_can_never_become_model_features() (+2 more)

### Community 64 - "epoch_windows"
Cohesion: 0.20
Nodes (10): epoch_windows(), load_windows(), `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, Windows for every stem that can supply them, and the reason each of the others c, `y` is `(distance, d_heading, d_distance)` and `TARGET_COLUMNS` indexes into it., 15 m/s due north for 300 s: every 1 s epoch is 15 m of travel and no change of h, D-089's rule, one level down. A VBOX blink must not cost a whole drive.      F, test_a_truth_gap_drops_epochs_rather_than_the_sequence() (+2 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "io_vnbd.py"
Cohesion: 0.25
Nodes (7): DataFrame, Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, _canonicalise(), _distinct_fixes(), IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage, Normalise headers, then guard. Guard *after* normalisation so that a disguised w, One row per GPS position change, carrying its timestamp and IMU sample index.

### Community 67 - "uk_utc_offset_s"
Cohesion: 0.22
Nodes (9): _last_sunday(), Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, uk_utc_offset_s(), Hand-computed from the rule, not from this function's own output.      BST run, A date-only rule would be an hour wrong for part of two days a year., test_bst_boundaries_are_the_published_ones_for_the_years_the_dataset_spans(), test_deep_winter_and_deep_summer_need_no_boundary_arithmetic() (+1 more)

### Community 68 - "ValueError"
Cohesion: 0.25
Nodes (3): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Tensor, ValueError

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.25
Nodes (7): Car-park mode, Contract, Known failure modes, Library choice — *pending, log it*, maps/ — OSM graph & HMM map matcher, Status, What lives here

### Community 71 - "train_baseline_rnn.py"
Cohesion: 0.25
Nodes (7): assert_features_are_clean(), build_parser(), _median(), ArgumentParser, Training entry point for the Onyekpe INS baseline reproduction (P-06).      py, Run the repo's own leakage guard over the exact columns the model is fed. Return, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md)

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.29
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of()

### Community 74 - "make_optimizer"
Cohesion: 0.33
Nodes (6): loss_fn(), make_optimizer(), Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, Module, Optimizer

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.29
Nodes (4): OnyekpeBaseline, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Hyperparameter

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 78 - "propagate_nominal"
Cohesion: 0.33
Nodes (6): propagate_nominal(), Section 8.1. Exact under a constant-input assumption over dt, **not** an Euler s, The gravity-sign test. A level phone at rest reads specific force -g in the body, **The discriminating half**, without which the test above bounds nothing., test_reorthonormalisation_is_what_keeps_r_there(), test_stationary_phone_does_not_drift()

### Community 79 - "data/ — gitignored"
Cohesion: 0.33
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.33
Nodes (6): drift_percent(), Final position error as a percentage of ground-truth distance travelled., 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, test_drift_percent_hand_computed(), test_drift_percent_rejects_zero_distance()

### Community 81 - "_replay_record"
Cohesion: 0.33
Nodes (6): _cumulative(), Displacements -> positions relative to the window start, with the leading zero., Assemble one window's trajectory record for the renderer., One outage window, in the form the replay renderer reads. **Every field is measu, _replay_record(), trajectory_record()

### Community 82 - "yaw_error"
Cohesion: 0.40
Nodes (5): (RMSE, max absolute) yaw error in radians, wrapped to (-pi, pi].      Always r, yaw_error(), An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi, test_yaw_error_wraps_across_the_branch_cut(), test_yaw_error_zero_when_identical()

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 86 - "wrap_to_pi"
Cohesion: 0.50
Nodes (4): Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., wrap_to_pi(), 359 degrees to 1 degree is +2, not -358. Unwrapped, a single wrap puts a 6.2 rad, test_heading_differences_wrap()

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.67
Nodes (3): gauss_markov_bias_driving_noise(), Process-noise amplitude for a bias modelled as first-order Gauss-Markov., test_gauss_markov_driving_noise_matches_the_closed_form()

## Knowledge Gaps
- **294 isolated node(s):** `SatSample`, `Snapshot`, `StreamReadout`, `GnssReadout`, `Summary` (+289 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `InEKF` connect `InEKF` to `test_se23_derivation.py`, `test_filter.py`, `test_harness_wiring.py`, `ValueError`, `FilterConfig`, `run.py`, `ndarray`, `test_ffi_contract.py`, `test_mount.py`, `propagate_nominal`, `inekf.py`, `Stamp`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `FilterConfig` connect `FilterConfig` to `test_baselines.py`, `test_se23_derivation.py`, `test_filter.py`, `test_harness_wiring.py`, `InEKF`, `run.py`, `test_ffi_contract.py`, `ndarray`, `test_mount.py`, `inekf.py`, `Stamp`, `test_allan.py`, `allan.py`, `overlapping_allan_deviation`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `load_sequence()` connect `load_sequence` to `test_baselines.py`, `epoch_windows`, `io_vnbd.py`, `test_protocol.py`, `ValueError`, `train_baseline_rnn.py`, `FilterConfig`, `LeakageError`, `test_leakage.py`, `cadence.py`, `test_truth.py`, `Sequence`, `allan.py`, `test_android_logger_schema.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `DroppedWindow`) actually correct?**
  _`InEKF` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._