/*
 * idr_core.h -- the FFI surface of the IDR 26168 filter core.
 *
 * ============================================================================================
 * THIS IS AN INTERFACE DEFINITION. THERE IS NO IMPLEMENTATION BEHIND IT YET, BY DECISION.
 *
 * D-022 defers the C++/Rust port to October; D-043 ships this header at screening so the
 * architecture is an artefact rather than a promise. Both the Android build (JNI) and the
 * 200 Hz FOG edge build bind to this and to nothing else. The Python reference in
 * core/reference/inekf.py is the specification: where the two disagree, the Python and the
 * derivation in docs/SE23_PROPAGATION.md are right and this file is a bug.
 *
 * Do not add a build system here. Do not start the JNI layer. Do not implement the port.
 * ============================================================================================
 *
 * CONVENTIONS, ONCE, FOR EVERY ENTRY POINT BELOW
 *
 *   Units          SI throughout, radians for angle. Rates are per second. No degrees, no g,
 *                  no km/h crosses this boundary -- the `S-` stream ships km/h and degrees and
 *                  the conversion belongs on the caller's side of the wall, where it is
 *                  visible, not inside a filter step where it is not.
 *
 *   Navigation     NED, local-tangent, origin at the session's first accepted fix.
 *   frame          x north, y east, z DOWN. Gravity is +9.80665 on z.
 *
 *   Body frame     The phone's own axes, exactly as the IMU reports them. The caller does not
 *                  pre-rotate: the mount rotation is filter state (see R_sv).
 *
 *   Vehicle frame  x forward, y right, z down. R_sv maps BODY -> VEHICLE.
 *
 *   Error state    18 elements, in this order and no other:
 *                    [0:3)   attitude       (rad)
 *                    [3:6)   velocity       (m/s)
 *                    [6:9)   position       (m)
 *                    [9:12)  gyro bias      (rad/s)
 *                    [12:15) accel bias     (m/s^2)
 *                    [15:18) mount rotation (rad, vehicle-frame left-multiplied -- D-030, so
 *                            element 17 reads DIRECTLY as mount-yaw error in the vehicle
 *                            frame and compares against the ~1 deg budget requirement with no
 *                            change of basis)
 *                  The error is RIGHT-invariant, eta = X_hat X^-1 (D-028). Corrections are
 *                  SUBTRACTED (D-050); section 8.3 of the derivation writes a plus and is
 *                  superseded on that point.
 *
 *   Covariance     18x18, row-major, symmetric. Always the error-state covariance, never a
 *                  total-state one.
 *
 *   Ownership      The caller owns every buffer it passes in and every buffer it passes out.
 *                  This library allocates nothing the caller must free, keeps no pointer past
 *                  the call that received it, and copies whatever it needs to retain. The one
 *                  exception is the opaque handle from idr_create, which idr_destroy frees.
 *
 *   Threading      A handle is NOT thread-safe. One handle per thread, or serialise. There is
 *                  no global state, so two handles never interact.
 *
 *   Errors         Every call returns idr_status. A non-OK return leaves the filter state
 *                  EXACTLY as it was -- no partial update, ever. A rejected measurement is not
 *                  an error: it returns IDR_OK with *applied = 0.
 *
 *   Timing         dt comes from real timestamps and is never nominal (D-013): five `S-` stems
 *                  restart their clock mid-recording, and propagating a nominal interval
 *                  integrates the wrong dt silently. A non-positive dt is IDR_ERR_BAD_DT.
 */

#ifndef IDR_CORE_H
#define IDR_CORE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define IDR_ERROR_STATE_DIM 18

typedef enum {
    IDR_OK = 0,
    IDR_ERR_NULL_ARG = 1,      /* a required pointer was NULL                                */
    IDR_ERR_BAD_DT = 2,        /* dt <= 0: the timestamps went backwards                     */
    IDR_ERR_NOT_FINITE = 3,    /* a NaN or Inf reached the filter -- fix the loader          */
    IDR_ERR_NOT_INITIALISED = 4,
    IDR_ERR_SINGULAR = 5       /* innovation covariance would not factor                     */
} idr_status;

/* Opaque. Its layout is not part of this contract and will change. */
typedef struct idr_filter idr_filter;

/*
 * Tuning. Every field is a MEASURED quantity or a stated modelling choice, never a knob, and
 * each names where its value comes from. Defaults live in core/reference/inekf.py FilterConfig
 * and are seeded from IO-VNBD's own stationary segments (D-045) -- NOT from a datasheet and NOT
 * from a team phone (D-038).
 */
typedef struct {
    double gyro_arw;          /* rad/s/sqrt(Hz)   measured, D-045                             */
    double accel_vrw;         /* m/s^2/sqrt(Hz)   measured, D-045                             */
    double gyro_bias_rw;      /* rad/s^2/sqrt(Hz) DERIVED from a Gauss-Markov model, not
                                 measured -- a 507 s record cannot reach the +1/2 slope        */
    double accel_bias_rw;     /* m/s^3/sqrt(Hz)   derived, as above                            */
    double mount_rw;          /* rad/s/sqrt(Hz)   ZERO by decision (D-048): no source in the
                                 repo gives it a magnitude, and a guessed value here is
                                 invisible inside the covariance the gate reads. A knock is
                                 handled by idr_reinflate_mount instead.                       */
    double imu_rate_hz;       /* the stream's MEASURED rate; zaru_sigma depends on it          */
    double zupt_sigma;        /* m/s                                                           */
    double zaru_sigma;        /* rad/s -- must equal gyro_arw * sqrt(imu_rate_hz) (D-056).
                                 It is the gyro white noise per sample, not a free parameter.  */
    double nhc_sigma_lateral; /* m/s   model slack for camber, suspension, tyre slip           */
    double nhc_sigma_vertical;/* m/s                                                            */
    double chi2_gate_3dof;    /* chi-squared 0.99 at 3 dof                                     */
} idr_config;

/* Fills `cfg` with the measured defaults. Always call this before overriding a field, so a
 * future field added here cannot be left uninitialised by an older caller. */
idr_status idr_default_config(idr_config *cfg);

/*
 * Create a filter. `p0` is the 18x18 initial error-state covariance, row-major, or NULL for
 * the per-block default of D-055. It is copied; the caller keeps ownership.
 *
 * `r_sv` is the 3x3 body->vehicle rotation, row-major, or NULL for identity. The PCA
 * initialiser that produces it also produces its spread, which belongs in p0's mount block
 * (D-073) -- passing a rotation without widening that block asserts a confidence the
 * initialiser did not report.
 */
idr_status idr_create(const idr_config *cfg, const double *p0, const double *r_sv,
                      idr_filter **out);
void idr_destroy(idr_filter *f);

/*
 * Propagation. ALWAYS runs, GNSS or not -- this is the spine, and there is no second mode.
 * `gyro` and `accel` are 3-vectors of RAW body-frame samples: rate in rad/s and specific force
 * in m/s^2, bias NOT removed by the caller (the filter estimates it).
 */
idr_status idr_propagate(idr_filter *f, const double gyro[3], const double accel[3], double dt);

/*
 * The update family. Every one of these takes measurements the caller has already GATED.
 *
 * Gating stays with the caller and cannot move in here (D-052): stationary detection needs
 * accelerometer variance over a window and NHC validity needs yaw rate and lateral
 * acceleration, and none of those is a property of the state -- they are properties of the IMU
 * stream, which the filter does not hold. Moving them inside would mean the filter keeping a
 * raw-sample buffer purely to re-derive what the caller already has, and would hide the rule
 * the error budget depends on: ZUPT and ZARU are offered TOGETHER at every detected stop
 * (D-004). A stop where only one is offered is a bug, not a tuning choice.
 *
 * `applied` receives 1 if the measurement was used and 0 if it was declined at a gate. Declined
 * is IDR_OK, not an error, and it leaves state and covariance untouched -- see idr_update_gnss.
 */
idr_status idr_update_zupt(idr_filter *f);

/* `gyro` is the RAW sample for this step, not a bias-corrected one (D-052): section 7.3 asserts
 * the true rate is zero, so the raw reading IS the bias. chi-squared gated (D-057) -- the stop
 * detector's window lags a stop->moving transition by up to one window, and a ZARU fired one
 * sample into motion injects the whole yaw rate as bias error. */
idr_status idr_update_zaru(idr_filter *f, const double gyro[3], int *applied);

/* `r_nhc` is the 2x2 lateral/vertical measurement covariance, row-major, or NULL for the config
 * values. The adaptive head supplies it per step (D-040): it adapts R, never Q. */
idr_status idr_update_nhc(idr_filter *f, const double *r_nhc);

/* Learned forward-speed pseudo-measurement. `variance` is the head's OWN predicted variance and
 * not a tuned constant -- that is the entire point of training a variance head, and it is why
 * Gate 2 measures calibration rather than accuracy. */
idr_status idr_update_speed(idr_filter *f, double speed_mps, double variance);

/*
 * GNSS position, chi-squared gated. `position_ned` is 3 metres NED from the session origin;
 * `cov` is the 3x3 measurement covariance, row-major, from the receiver's own reported
 * accuracy where it has one.
 *
 * *** A REJECTED FIX APPLIES NOTHING. ***
 *
 * Not a smaller correction, not a re-initialisation, not a mode flag: `*applied` is 0 and
 * neither the state nor the covariance is touched. That absence is the architectural claim
 * (D-001). During a tunnel the caller simply does not call this; on exit it calls it again and
 * multipath is rejected by the same gate that rejects nothing else. There is no branch to
 * switch, so there is no transition latency and no position jump, and "seamless transition
 * within milliseconds" is satisfied by construction rather than by handling.
 */
idr_status idr_update_gnss(idr_filter *f, const double position_ned[3], const double cov[9],
                           int *applied);

/*
 * Widen the mount block after a detected knock. Variance is ADDED, not reset -- a reset would
 * shrink the covariance of a filter that had already lost track. The state is untouched: a
 * knock is news about uncertainty, and the gyro energy that detected it does not say how far
 * the phone turned (D-076). NHC then re-estimates R_sv, with gain equal to forward speed.
 */
idr_status idr_reinflate_mount(idr_filter *f, double sigma_rad);

/*
 * Output. `rotation` is 9 doubles row-major (nav<-body), `velocity_ned` and `position_ned` are
 * 3 each, `gyro_bias` and `accel_bias` 3 each, `r_sv` 9. Any may be NULL to skip it. Buffers
 * are the caller's.
 */
idr_status idr_get_state(const idr_filter *f, double *rotation, double *velocity_ned,
                         double *position_ned, double *gyro_bias, double *accel_bias,
                         double *r_sv);

/* The full 18x18 error-state covariance, row-major, into a caller buffer of at least
 * IDR_ERROR_STATE_DIM * IDR_ERROR_STATE_DIM doubles. This is what the uncertainty ellipse, the
 * chi-squared gate and the map matcher's emission sigma all read, which is why P0 being wrong
 * is expensive and quiet. */
idr_status idr_get_covariance(const idr_filter *f, double *cov_out, size_t n_doubles);

/* Heading in radians, the quantity the whole error budget turns on. Logged separately from
 * position, always (H-6). */
idr_status idr_get_yaw(const idr_filter *f, double *yaw_rad);

#ifdef __cplusplus
}  /* extern "C" */
#endif

#endif /* IDR_CORE_H */
