# android/ — foreground logger & demo UI

**Seat A.**

Two jobs: collect trustworthy data (Sprint 0 onward), and demo the system (Sprint 3). The core is
the deliverable; the app is the demo. Wrap it last.

## Non-negotiable platform facts

These are not preferences. Each one silently corrupts the data if ignored.

| Constraint | Consequence |
|---|---|
| **Since Android 9, background continuous sensors deliver no events.** | A **foreground service** with a persistent notification is mandatory for continuous logging. |
| **Since API 31, `registerListener()` caps at 200 Hz** without `HIGH_SAMPLING_RATE_SENSORS`; `SensorDirectChannel` caps near 50 Hz. | Declare the permission. Play Store review requires justifying it. |
| **If the user disables mic access via device toggles, motion sensors are rate-limited regardless of the permission.** | Detect and warn, or a collection run silently produces useless data. |
| **Use `TYPE_ACCELEROMETER_UNCALIBRATED` / `TYPE_GYROSCOPE_UNCALIBRATED`.** | Calibrated types silently subtract an OS bias estimate that the filter is *also* estimating. The two fight and the bias state is corrupted. |
| **Sensor timestamps are a monotonic device clock in ns, with jitter and batching. GNSS is UTC.** | Convert both to one base, model the offset, interpolate GNSS onto IMU epochs. **Never assume a nominal Δt.** |
| Sustained 200 Hz sensing + inference heats the SoC and throttles. | Budget for it; measure it over a real drive. |

## Threading

High-rate filter thread reading a lock-free ring buffer · NN inference at 1–10 Hz on a second thread
posting measurement updates · GNSS callback on a third · UI on main, reading a state snapshot.

## GNSS

Rely on **GPS + GLONASS + Galileo + BeiDou**. **NavIC is a bonus, not a dependency** — hardware
support exists on several chipsets, but signals are often filtered out by low-level drivers and
Android's GNSS API lacks standardised NavIC identifiers. Do not build anything that needs it.

Outage detection: `GnssStatus` per-satellite C/N₀ and count, `Location.getAccuracy()`, fix age.
Do not wait for the OS to declare loss — it reports a "good" coasted fix for a while after real
signal loss. Cross-check against the INS prediction and gate on innovation.

## Demo UI

Vector map, smooth 10 Hz car icon, mode indicator, and a **visible uncertainty ellipse**. Judges
respond to watching the covariance grow inside the tunnel and collapse on exit — it makes the
architecture legible in a way a trajectory plot does not.

On tunnel exit: reject the first multipath-corrupted fixes and run a short backward smoother so the
drawn path corrects smoothly instead of snapping.

## Contract

The `core/ffi/` interface is agreed **in writing with seat S before either side writes against it.**

## Status

Scaffold only. Sprint 0: logger skeleton, and measure the actual achieved sample rate and timestamp
jitter on every team device. Write the numbers down — the nominal rate is not the real rate.
