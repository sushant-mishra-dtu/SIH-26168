# Graph Report - SIH-26168  (2026-09-13)

## Corpus Check
- 97 files · ~190,506 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1904 nodes · 3706 edges · 100 communities (85 shown, 15 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 238 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b9de8837`
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
- data/ — gitignored
- drift_percent
- eval/ — the harness
- SessionExporterTest
- gradlew
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
- idr-26168

## God Nodes (most connected - your core abstractions)
1. `InEKF` - 74 edges
2. `FilterConfig` - 63 edges
3. `evaluate_sequence()` - 43 edges
4. `Sequence` - 38 edges
5. `Outage` - 38 edges
6. `LeakageError` - 35 edges
7. `synthetic_drive()` - 35 edges
8. `load_sequence()` - 32 edges
9. `TruthPairingError` - 32 edges
10. `BaselineTrajectory` - 31 edges

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

## Communities (100 total, 15 thin omitted)

### Community 0 - "test_baselines.py"
Cohesion: 0.06
Nodes (63): course_over_ground(), epoch_times(), gnss_available(), initial_state_from_truth(), naive_strapdown(), ndarray, The two Gate 1 baselines: naive strapdown INS, and GNSS-available.  Gate 1 is, Navigation-from-body rotation for a level vehicle on a given heading. (+55 more)

### Community 1 - "test_se23_derivation.py"
Cohesion: 0.05
Nodes (64): a_ri(), expm_series(), g_ri(), process_noise_psd(), IMU propagation. Always runs, GNSS or not -- this is the spine.          `dt`, Scaling-and-squaring Taylor matrix exponential.      scipy is deliberately not, Right-invariant error-state matrix, section 5.2. Ordering matches the IDX_* slic, Noise mapping, section 5.3. Columns are `[w_g, w_a, w_bg, w_ba, w_sv]`, 15 wide. (+56 more)

### Community 2 - "test_filter.py"
Cohesion: 0.04
Nodes (75): chi2_gate(), detect_mount_disturbance(), initial_covariance(), is_stationary(), nhc_is_valid(), Detect the phone being knocked, so R_sv covariance can be re-inflated.      A, `P0`, block by block, with every entry traceable to a section of docs/ERROR_BUDG, Re-express a covariance built on *plain* errors in the filter's right-invariant (+67 more)

### Community 3 - "test_harness_wiring.py"
Cohesion: 0.08
Nodes (31): Outage, One injected outage window, as sample indices into a sequence., Number of 1 s prediction epochs in this outage., Slice one outage window's epoch boundaries out of a position series.      Row, This stem cannot be graded, and the run says so rather than reporting a number a, The naive strapdown baseline over one window, initialised from truth (D-064)., Seconds to add to a sequence-relative time to put it on the truth track's clock., SequenceUnusable (+23 more)

### Community 4 - "test_protocol.py"
Cohesion: 0.12
Nodes (13): Protocol invariants: the split, the outage sweep, and run determinism.  These, Both wet stems are refused and nothing in the dataset is documented as wet, so t, `docs/EVALUATION.md` section 3 and `eval/splits.py` must stay in exact agreement, Eleven IO-VNBD stems ship on the "V-" ECU stream only. A split entry naming one, Pins `LONG_OUTAGE` against EVALUATION.md section 3 as re-picked by D-092., test_different_seeds_diverge(), test_dirty_tree_is_flagged_as_unreproducible(), test_evaluation_doc_matches_splits_module() (+5 more)

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
Cohesion: 0.16
Nodes (18): AxisMeasurement, candidate_gyro(), _course_and_gyro(), main(), measure(), ndarray, Measure which `S-` gyroscope column carries the vehicle's yaw rate, and what it, `(course_rate, gyro_mean, course_change, gyro_integral, keep)` over fix interval (+10 more)

### Community 10 - "run.py"
Cohesion: 0.06
Nodes (59): FilterConfig, mount_yaw_from_dynamics(), Tuning. Process noise is seeded from a measured Allan-variance run, never guesse, Mount yaw by least squares between the phone's horizontal specific force and the, innovation_sequence(), `(innovation norms, chi-squared distances, accepted count)` over the first `n_fi, apply_alignment(), attempt_alignment() (+51 more)

### Community 11 - "ndarray"
Cohesion: 0.07
Nodes (53): adjoint(), _cue_statistic(), _effective_samples(), exp_so3(), gammas(), log_so3(), _moving_average(), orthonormalise() (+45 more)

### Community 12 - "ReplayActivity"
Cohesion: 0.07
Nodes (19): AppCompatActivity, Bundle, Button, TextView, View, ReplayActivity, Canvas, View (+11 more)

### Community 13 - "test_mount.py"
Cohesion: 0.04
Nodes (63): InEKF, pca_mount_yaw(), Error-state Invariant EKF on SE_2(3).      Sprint 1 (seat S) implements propag, Learned forward-speed pseudo-measurement with its predicted variance., Initialise the phone->vehicle rotation `R_sv` by PCA on horizontal specific forc, test_filter_initialises_with_a_well_formed_covariance(), test_zaru_at_a_genuine_stop_is_applied(), _drive_with_a_knock() (+55 more)

### Community 14 - "SessionClock"
Cohesion: 0.08
Nodes (8): dateFormat(), SessionClock, Timebase, ELAPSED_REALTIME, UNKNOWN, UPTIME, SessionClockTest, java

### Community 15 - "inekf.py"
Cohesion: 0.09
Nodes (35): MountInit, NavState, What the PCA initialiser found: the mount rotation, and how well it is pinned do, Nominal state. Covariance is carried separately as an 18x18 on the error state., Heading in radians. The quantity the whole error budget turns on., BaselineTrajectory, One baseline's answer over one outage window, at the protocol's 1 s prediction c, Refuses. The drift-% denominator is not measured off 9 s fixes. (+27 more)

### Community 16 - "cadence.py"
Cohesion: 0.08
Nodes (34): build_parser(), CadenceRow, _fixed(), main(), measure_cadence(), ArgumentParser, Path, GNSS cadence, and whether the paired `V-` track can stand in as ground truth. (+26 more)

### Community 17 - "test_truth.py"
Cohesion: 0.05
Nodes (49): _last_sunday(), Day of the month of its last Sunday. March and October both have 31 days., Seconds to subtract from a UK *local* timestamp to get UTC: `BST_OFFSET_S` or ze, Parse the `S-` `date` column into seconds since midnight, **as shipped**., seconds_of_day(), uk_utc_offset_s(), Ground truth from the paired `V-` VBOX GPS, and the cadence measurement behind i, Not a style point. A velocity column here becomes a speed label the first time s (+41 more)

### Community 18 - "truth.py"
Cohesion: 0.10
Nodes (28): align_to_sequence(), _approx_residuals_m(), _best_lag_s(), _nearest(), _parse_local_seconds(), ndarray, Ground truth from the paired `V-` VBOX GPS.  **Why this module exists.** `docs, A 10 Hz reference trajectory: time of day, latitude, longitude. Nothing else. (+20 more)

### Community 19 - "Stamp"
Cohesion: 0.11
Nodes (21): DroppedWindow, One outage window the paired `V-` track does not cover, and why (D-089)., Write `summary.json`, `windows.csv` and one `trajectory_<seq>.json` per plotted, write_artefacts(), git_sha(), make_stamp(), Path, Provenance stamping.  Every figure and table in the submission carries the com (+13 more)

### Community 20 - "test_allan.py"
Cohesion: 0.22
Nodes (16): find_stationary_segments(), Find stretches long and clean enough to compute an Allan curve on.      Statio, ndarray, S-I really does contain a 285 s hole. Allan variance assumes a uniform grid, so, The far side of S-I's pause logs at ~1 ms with 39% of samples sharing a timestam, Idling with an occupant passes the ZUPT detector and must still be excluded from, The vectorised criterion must be the same criterion as `is_stationary`, not a lo, _sequence() (+8 more)

### Community 21 - "Method — SIH 2026, PS 26168"
Cohesion: 0.07
Nodes (28): 0. How to read the numbers in this document, 10. Deployment, 11.1 Inputs, and the channel restriction, 11.2 The protocol, 11.3 Metrics, 11.4 Two defects in the protocol as drafted, found by checking, 11. Evaluation protocol, 12. Results (+20 more)

### Community 22 - "load_sequence"
Cohesion: 0.08
Nodes (37): DataFrame, _canonicalise(), _distinct_fixes(), load_sequence(), load_split(), _preferred_copy(), Path, IO-VNBD "S-" smartphone-stream loader.  Every read passes through the leakage (+29 more)

### Community 23 - "test_metrics.py"
Cohesion: 0.10
Nodes (24): cte(), Cumulative True Error: the *signed* sum of per-epoch errors, in metres.      S, Metric unit tests, each against a hand-computed case.  Every number in the sub, An estimate 0.02 rad past +pi is 0.02 rad of error, not 6.26.      Getting thi, 60 s outage, 10 m/s, perfect heading, 2% under-prediction of distance.      Tr, Three epochs, each under-predicted by 1 m along-track.      Hand-computed: per, The pair exists precisely because they disagree: +2 and -2 cancel in CTE but not, There is no else-fallthrough in crse(): an unknown member must raise, not quietl (+16 more)

### Community 24 - "Implementation Plan v2 — consolidated plan of record"
Cohesion: 0.07
Nodes (27): 10. What we say about the limits, 1. What has not changed, 2. Audit — what is done, what needs redoing, what is left, 2A. Done, verified in code, no rework, 2B. Needs redoing or correcting — nine items, 2C. Not started — the actual remaining work, 3. The architecture, after consolidation, 4. Reconciling the Master Implementation Plan (+19 more)

### Community 25 - "allan.py"
Cohesion: 0.19
Nodes (13): AllanReport, _fixed(), main(), Path, Everything one run of this module produced, ready to stamp and write., Per-axis, per-segment coefficients for one sensor, optionally white-band fits on, Largest value of `attribute` over every axis of every segment.          `Filte, (min, max) of `attribute`, for reporting the range rather than a false point est (+5 more)

### Community 26 - "test_geo.py"
Cohesion: 0.13
Nodes (23): path_length(), ndarray, Geodesy. Ground truth lives here, so this module is deliberately boring and well, Wrap an angle in radians to (-pi, pi].      Yaw error is meaningless unwrapped, Geodesic distance in metres between two WGS-84 points.      Returns 0.0 for co, Cumulative geodesic path length in metres along a fix sequence.      This is t, vincenty_inverse(), wrap_to_pi() (+15 more)

### Community 27 - "AI/ML-Enhanced Inertial Dead Reckoning & GNSS+INS Fusion for Ground Vehicles — Engineering Survey for SIH 2026 PS 26168"
Cohesion: 0.08
Nodes (23): 1.1 Comparison table, 1.2 Known non-transfer to ground vehicles (flag explicitly), 2.1 Dataset structure, schema, units, frames, 2.2 Naming convention & splits (from WhONet paper), 2.3 Exact experimental hyperparameters, 2.4 Reported IO-VNBD numbers (WhONet vs physics baseline), 8.1 Spec ranges (order-of-magnitude; consult datasheets for a given part), 8.2 Error propagation → error budget vs <10% benchmark (+15 more)

### Community 28 - "overlapping_allan_deviation"
Cohesion: 0.13
Nodes (25): AllanCurve, analyse_segment(), bias_instability(), coefficients(), _loglog_slope(), NoiseCoefficients, overlapping_allan_deviation(), random_walk_coefficient() (+17 more)

### Community 29 - "TruthPairingError"
Cohesion: 0.11
Nodes (25): load_truth(), manifest_path_for(), paired_truth_path(), Path, Locate one shipped file by stem and stream, via the checksum manifest.      Vi, The `V-` file paired with an `S-` stem: this sequence's ground truth., Read lat, lon and time of day from one `V-` file.      The header is read on i, evaluate() (+17 more)

### Community 30 - "test_android_logger_schema.py"
Cohesion: 0.09
Nodes (32): normalise(), Normalise a raw CSV header to our canonical snake_case form.      AndroSensor, test_a_truncated_date_format_string_still_normalises(), test_the_satellite_column_ships_with_and_without_the_gps_prefix(), _const(), _header_from_kotlin(), _int_const(), _kotlin() (+24 more)

### Community 31 - "test_replay.py"
Cohesion: 0.05
Nodes (43): evaluate_sequence(), Every window of every length for one sequence, all three methods.      One GNS, What the aided pass did, for `summary.json`: how it aligned, what it was fed, an, The epoch of a window comes from the row's own timestamp, never from its row ind, The wiring end to end: loader arrays -> filter and both baselines -> one metrics, The same closed form as tests/test_baselines.py, but reached through the loader,, The same track with its samples between two relative times deleted.      This, D-089. A 3 s hole leaves 4 of the window's 61 epochs uncovered -- Vw12's failure (+35 more)

### Community 32 - "Decision Log"
Cohesion: 0.08
Nodes (24): CI — the SO(3) orthogonality bound (1 Sep 2026), Consolidation — 27 Aug 2026, Decision Log, Gate 0 — R-4, the CRSE convention (31 Aug 2026), Gate 1 — measured for the first time, and it fails (6 Sep 2026), Gate 1 — P-06: the Onyekpe INS reproduction, trained (2 Sep 2026), Gate 1 — the fix that holds the aided pass, and the split the data forces (13 Sep 2026), Rebase — the logger's speed column against D-102 (4 Sep 2026) (+16 more)

### Community 33 - "seconds_of_day_utc"
Cohesion: 0.15
Nodes (16): fix_arrays(), imu_stream(), `(gyro, accel, t_rel_s)` for one sequence: `(n, 3)`, `(n, 3)`, `(n,)`.      Ax, `(sample_idx, ned (n, 3), sigma_m (n,))` for the distinct `S-` GPS fixes., Proper right-handed triad (+gyro_yaw, -gyro_roll, +gyro_pitch) established by D-, `gps_accuracy_m` is the phone's own statement about the fix, so the covariance t, The architectural claim, exercised: during an injected outage the GNSS update is, `run_filter` used to construct `InEKF(cfg)` and propagate from R = R_sv = I, v = (+8 more)

### Community 34 - "SE₂(3) Propagation — the derivation the code is written from"
Cohesion: 0.09
Nodes (22): 10. Open before Gate 1, 1. Conventions — fix these once, 2.1 The adjoint — derived, because §6 depends on it, 2. The state and the group, 3. Continuous dynamics, 4. Group-affine — and the caveat that matters, 5.1 Derivation of the right-invariant error dynamics, 5.2 The matrix (+14 more)

### Community 35 - "Error Budget"
Cohesion: 0.10
Nodes (21): 10.1 ZARU's measurement noise is not a tuning parameter, 10.2 Filter consistency at Gate 1 — measured, 10.3 What D-111 changed in `P₀` and `Q`, and why — measured in motion, 10. Initial covariance `P₀` — measured, derived, and the one entry that is neither, 1. Reference scenario, 2. Why the obvious approach fails, 3.1 What the whole budget buys, 3.2 What residual bias actually costs (+13 more)

### Community 36 - "main"
Cohesion: 0.11
Nodes (22): audit_table(), build_parser(), main(), _median(), ArgumentParser, Median, not mean: the protocol reports drift % as median and p95 (EVALUATION.md), The stated-versus-omitted table, as text. Printed by `--audit`, and quoted in th, The Onyekpe reproduction's hyperparameter audit (P-06).  Tests the *audit*, no (+14 more)

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
Cohesion: 0.33
Nodes (6): normalise_truth_header(), Normalise a `V-` header to a canonical name, or to a generic form the allowlist, The `V-` stream carries 'Indicated Longitudinal Acceleration'. A loose longitude, The exact `V-` header spelling is not recorded anywhere in this repo. The aliase, test_longitudinal_accel_is_not_mistaken_for_longitude(), test_plausible_latitude_spellings_all_normalise()

### Community 44 - "speed_head.py"
Cohesion: 0.18
Nodes (10): calibration_fraction(), gaussian_nll(), Tensor, Learned forward-speed head: regresses speed **and its variance** from an IMU win, Fraction of errors falling inside +/- n_sigma. **Gate 2 requires >= 0.95 at n_si, Dilated causal conv block. Causal because at deployment there is no future windo, TCN regressing (forward speed, log-variance) from a body-frame IMU window., Heteroscedastic Gaussian NLL: the loss that makes the variance head mean somethi (+2 more)

### Community 46 - "test_leakage.py"
Cohesion: 0.07
Nodes (43): assert_feature_safe(), assert_no_leakage(), LeakageError, Channel allowlist and the leakage guard.  PS 26168 disallows wheel odometry. I, Raise LeakageError if any disallowed channel is present.      Called by the lo, Stricter guard for tensors entering a model or filter: inertial channels only., A disallowed channel reached a feature path.      Deliberately an AssertionErr, assert_truth_only() (+35 more)

### Community 47 - "Submission audit"
Cohesion: 0.15
Nodes (13): 0. The blocker, stated once, 10. Portal cut-off time and deliverable format, 1. Every quoted number traces to a stamped artefact (D-042), 2. No artefact carries a `-dirty` stamp, 3. Leakage audit, pass #2, 4. Yaw error appears on every figure that shows position error, 5. Drift % is reported as median **and** p95, 6. Gate checkboxes (+5 more)

### Community 48 - "core.py"
Cohesion: 0.22
Nodes (15): Enum, crse(), CrseConvention, evaluate_outage(), per_epoch_errors(), ndarray, The four metrics. This module owns every number in the submission.  Read docs/, Signed per-epoch displacement error in metres, one value per 1 s prediction epoc (+7 more)

### Community 49 - "Sequence"
Cohesion: 0.29
Nodes (4): ndarray, Refuses. Ground truth is not the `S-` GPS -- see `eval/loaders/truth.py`., Inertial feature matrix, shape (n, 15). Guarded on the way out., Seconds since the start of the recording at each distinct GPS fix.          Fi

### Community 50 - "Handover — seat A, Android: the map view and production readiness"
Cohesion: 0.17
Nodes (10): 1. What you are actually picking up, 2. Hard constraints — each one silently ruins the work if ignored, 3. "Add the map" is two tasks, and only one is unblocked, 3a. Trajectory view — buildable today, no filter needed, 3b. Road geometry underneath it — blocked, and not on you, 4. "Production ready" — what it means here, in priority order, 5. Known gaps in the code as written, 6. Environment, so you do not lose a morning (+2 more)

### Community 51 - "1. IO-VNBD — the mandated screening dataset"
Cohesion: 0.17
Nodes (12): 1.1 Two parallel streams, 1.2 Frames and ground truth, 1.3 Naming convention, 1.4 Data-quality notes, 1.5 Licence and citation, 1. IO-VNBD — the mandated screening dataset, 2. The three traps, 3. Baseline hyperparameters to reproduce (+4 more)

### Community 52 - "octave_taus"
Cohesion: 0.29
Nodes (7): imu_arrays(), ndarray, Pull `(t_s, accel, gyro)` out of a loaded sequence as float arrays.      Rows, Mean over every length-`window` slice, via cumulative sums. Shape (n - window +, Half-open [start, stop) index pairs of every run of True., _rolling_mean(), _true_runs()

### Community 53 - "assert_no_leakage"
Cohesion: 0.20
Nodes (10): generate_outages(), mask_gnss(), ndarray, Synthetic GNSS-outage injection.  Protocol: docs/EVALUATION.md section 3. Leng, Boolean mask, True where a GNSS fix is available.      The filter consumes thi, Tile a sequence with non-overlapping outages of one length.      Deterministic, Starting an outage at sample zero measures filter initialisation, not dead recko, test_gnss_mask_is_false_exactly_during_outages() (+2 more)

### Community 54 - "normalise"
Cohesion: 0.20
Nodes (11): assert_non_overlapping(), generate_sweep(), Verify the non-overlap guarantee. Cheap to check, expensive to discover violated, The full sweep across every held-out sequence, keyed by outage length.      ``, plan_sweep(), Generate and validate the outage sweep. Validation is not optional., Sequences too short for 180 s contribute nothing at that length -- the same mech, A guard never observed to fire is not known to work. (+3 more)

### Community 55 - "test_baseline_training.py"
Cohesion: 0.13
Nodes (23): epoch_windows(), The held-back families, by a stated rule rather than by choice (D-098).      W, One sequence's training windows. `x` is (n, 10, 6); `y` is (n, 3).      The th, `(x, y)` for one paired sequence: 1 s IMU windows and what the vehicle actually, Heading differences live on a circle; 359 degrees to 1 degree is 2, not -358., StemWindows, validation_families(), wrap_to_pi() (+15 more)

### Community 57 - "LoggerState"
Cohesion: 0.20
Nodes (5): GnssReadout, Snapshot, LoggerState, Snapshot, StreamReadout

### Community 58 - "regress_heading_on_integrated_gyro"
Cohesion: 0.25
Nodes (10): Per column, the slope and R^2 of `d_heading ~ d_gyro[:, c]`.      The column t, regress_heading_on_integrated_gyro(), `eval.axis_check` -- the estimator that decides which gyro column is the vehicle, Heading change and integrated yaw rate are the same angle, so the slope is exact, A column carrying the negated yaw rate fits at slope -1, not +1.      The sign, Regression dilution is why the real 1 Hz-GNSS stems fit at |slope| < 1.      N, test_a_noisy_axis_still_wins_but_its_r2_says_how_much_to_believe_it(), test_mismatched_shapes_are_refused_rather_than_broadcast() (+2 more)

### Community 59 - "train"
Cohesion: 0.11
Nodes (16): loss_fn(), make_optimizer(), OnyekpeBaseline, Onyekpe "Learning to Localise" INS baseline -- the number we must beat.  Requi, Vanilla RNN correcting INS displacement error and orientation-rate error., Should land near the published ~8,200. A large divergence means the architecture, Adamax at 7e-4, as published. Not Adam -- the papers specify Adamax and the dist, Hyperparameter (+8 more)

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
Nodes (10): assert_no_family_straddles_the_split(), The frozen train/test split.  **Defined in code, not in a notebook.** A split, The parent recording a stem belongs to: `Vw14a` -> `Vw14`, `S3a` -> `S3`, `Vw4`, No parent recording may have one segment in TRAIN and another in the held-out se, stem_family(), Lettered stems are segments of one drive. `Vw14b` held out while `Vw14a` and `Vw, A guard never observed to fire is not known to work. This one caught `Vw16a`/`Vw, test_no_parent_recording_is_split_across_train_and_test() (+2 more)

### Community 64 - "epoch_windows"
Cohesion: 0.20
Nodes (10): closed_form_gammas(), _nees_inputs(), _nees_p0(), ndarray, The cutoff must sit where the closed form is *still accurate*, not where it is 0, The textbook expressions with no small-angle guard. Used only to show where they, The Monte-Carlo prior.      **This is the test's experimental design, not a pr, (omega, specific force, truly stopped) for step `k`: cruise, brake, stop, pull a (+2 more)

### Community 65 - "Working Agreements"
Cohesion: 0.22
Nodes (9): Branches and commits, CI gates, Decision log discipline, Documentation, Escalation, Reproducibility, Review, Seats and ownership (+1 more)

### Community 66 - "io_vnbd.py"
Cohesion: 0.22
Nodes (9): AssertionError, assert_split_disjoint(), Every held-out sequence, deduplicated and ordered., No sequence may appear in both train and test.      Checked in CI. This is the, test_sequences(), The whole point of the re-pick: a stem with no usable truth must not be in the s, test_held_out_set_is_the_union_of_long_and_challenging(), test_no_held_out_sequence_is_one_the_pairing_refused() (+1 more)

### Community 67 - "uk_utc_offset_s"
Cohesion: 0.29
Nodes (8): gate1_ratio(), `{method: {length_s: summary}}`, each summary from `eval.metrics.core.summarise`, The Gate 1 number: physics-only median drift over GNSS-available median drift, a, summarise_by_method_and_length(), A ratio quoted without its sample size is the number a judge asks about second., No 60 s windows means no Gate 1 number. Saying so is the only correct output., test_gate_1_reports_that_it_could_not_be_measured_rather_than_a_number(), test_the_gate_1_ratio_carries_the_window_count_it_rests_on()

### Community 68 - "ValueError"
Cohesion: 0.14
Nodes (8): Widen the mount block of `P` after a detected knock, so `R_sv` is re-estimated., Vincenty path length between two times, in metres.          The `L` in drift-%, Aggregate across sequences.      Reports the **median and 95th percentile** of, summarise(), Tensor, The mean hides the tail and the tail is what a judge finds., test_summary_reports_tail_not_just_mean(), ValueError

### Community 69 - "Glossary"
Cohesion: 0.25
Nodes (8): Constraints, Filtering, Glossary, Map matching, Methods worth knowing by name, Metrics, Navigation, Sensors

### Community 70 - "maps/ — OSM graph & HMM map matcher"
Cohesion: 0.25
Nodes (7): Car-park mode, Contract, Known failure modes, Library choice — *pending, log it*, maps/ — OSM graph & HMM map matcher, Status, What lives here

### Community 71 - "train_baseline_rnn.py"
Cohesion: 0.40
Nodes (5): train', 'test', or 'unassigned'.      'unassigned' is not an error -- IO-VNBD, split_of(), A mandatory plot drawn from the training set would be meaningless., test_mandatory_plot_sequences_are_held_out(), test_split_of_reports_unassigned_rather_than_guessing()

### Community 72 - "core/ — filter core & edge engine"
Cohesion: 0.29
Nodes (6): Contract, core/ — filter core & edge engine, Design constraints, Measured throughput of the Python reference, Status, What lives here

### Community 73 - "fetch"
Cohesion: 0.48
Nodes (6): fetch(), main(), Path, Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte., Download to a .part file and rename on success, so an interrupted run leaves no, sha256_of()

### Community 74 - "make_optimizer"
Cohesion: 0.50
Nodes (3): Longest averaging time this segment supports at MAX_TAU_FRACTION., One continuous, uniformly-sampled, stationary stretch of an `S-` sequence., StationarySegment

### Community 75 - "OnyekpeBaseline"
Cohesion: 0.50
Nodes (4): _nhc_mount_run(), Straight drive at `speed` with a true 5-degree mount yaw the filter does not kno, SE_2(3) test 9. Section 7.2's `-v_veh_hat^` column made quantitative.      For, test_nhc_learns_the_mount_yaw_and_learns_it_faster_at_speed()

### Community 76 - "models/ — learned components"
Cohesion: 0.29
Nodes (6): Contract, Export, Input representation, models/ — learned components, Status, What lives here

### Community 79 - "data/ — gitignored"
Cohesion: 0.33
Nodes (5): data/ — gitignored, Fetching it, Manifest, Reminders, What we need locally

### Community 80 - "drift_percent"
Cohesion: 0.33
Nodes (6): drift_percent(), Final position error as a percentage of ground-truth distance travelled., 50 m of final error over a 1,000 m outage is 5%., A stationary outage has no meaningful drift percentage. Excluding it is a decisi, test_drift_percent_hand_computed(), test_drift_percent_rejects_zero_distance()

### Community 83 - "eval/ — the harness"
Cohesion: 0.40
Nodes (5): Contract, eval/ — the harness, Metrics, briefly, Status, What lives here

### Community 85 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

### Community 89 - "gauss_markov_bias_driving_noise"
Cohesion: 0.07
Nodes (26): gauss_markov_bias_driving_noise(), octave_taus(), Log-spaced cluster times from `dt` up to `MAX_TAU_FRACTION` of the record., Process-noise amplitude for a bias modelled as first-order Gauss-Markov., Tests for the Allan-variance seeding of Q.  The estimator is checked against p, The old default, 3e-3 rad/s/sqrt(Hz), is 10.3 deg/sqrt(hr) -- outside the 0.5-5, Before the aliases, every one of these normalised to a name that was not on the, Generic paren-stripping collapsed all three to the single name 'orientation'. (+18 more)

## Knowledge Gaps
- **296 isolated node(s):** `SatSample`, `Snapshot`, `StreamReadout`, `GnssReadout`, `Summary` (+291 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FilterConfig` connect `run.py` to `gauss_markov_bias_driving_noise`, `test_se23_derivation.py`, `test_filter.py`, `seconds_of_day_utc`, `test_harness_wiring.py`, `test_baselines.py`, `FilterConfig`, `make_optimizer`, `ndarray`, `test_ffi_contract.py`, `test_mount.py`, `inekf.py`, `Stamp`, `test_allan.py`, `allan.py`, `overlapping_allan_deviation`, `test_replay.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `InEKF` connect `test_mount.py` to `test_se23_derivation.py`, `test_filter.py`, `test_harness_wiring.py`, `ValueError`, `seconds_of_day_utc`, `FilterConfig`, `InEKF`, `run.py`, `ndarray`, `test_ffi_contract.py`, `OnyekpeBaseline`, `inekf.py`, `Stamp`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `load_sequence()` connect `load_sequence` to `ValueError`, `train_baseline_rnn.py`, `test_leakage.py`, `inekf.py`, `cadence.py`, `test_truth.py`, `allan.py`, `overlapping_allan_deviation`, `TruthPairingError`, `test_android_logger_schema.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `InEKF` (e.g. with `AxisMeasurement` and `Alignment`) actually correct?**
  _`InEKF` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `FilterConfig` (e.g. with `AllanCurve` and `AllanReport`) actually correct?**
  _`FilterConfig` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `ValueError` (e.g. with `.propagate()` and `.reinflate_mount()`) actually correct?**
  _`ValueError` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `evaluate_sequence()` (e.g. with `TruthPairingError` and `ZeroDistanceOutage`) actually correct?**
  _`evaluate_sequence()` has 3 INFERRED edges - model-reasoned connections that need verification._