# Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126)

This document is the operational checklist for verifying the autonomous tunnel state machine,
the 3D perspective tunnel corridor, the exit progress bar, the speed HUD, and the contextual
hazard chips on a physical Android test device without access to a physical tunnel corridor.

> **Honesty & Vocabulary Rules (D-124, D-081, D-112).**
> - No Android surface prints "drift", a drift %, or a "grade" (R-A). Position uncertainty is
>   labelled `est. σ` (from the estimator covariance); a tunnel exit shows `exit residual vs GNSS`.
> - Every displayed figure derives strictly from measured sensor events, the estimator state, or
>   the declared asset file (R-B, R-F). When a value has no data source, the element is hidden.
> - The on-device estimator is an uncalibrated smartphone IMU demo and is explicitly **not** the
>   evaluated offline InEKF benchmark (D-081).

---

## Pre-Run Setup & Build Verification

1. **Verify Automated Guards & Unit Tests**:
   ```powershell
   # From repo root: Python text-surface guard assertions (must pass 163 tests, 0 skipped)
   .\.venv\Scripts\python.exe -m pytest tests/test_android_demo_surface.py -q

   # From android-ui/: JVM unit tests
   $env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot"
   .\gradlew.bat --no-daemon :app:testOsmDebugUnitTest
   ```

2. **Assemble and Install Debug APK**:
   ```powershell
   # Compile OSM flavour (default, zero account tokens needed)
   .\gradlew.bat --no-daemon :app:assembleOsmDebug

   # Install to connected device
   adb install -r app/build/outputs/apk/osm/debug/app-osm-debug.apk
   ```

3. **Start Live Telemetry Tracing in Logcat**:
   Open a separate shell to monitor autonomous FSM state transitions and verdicts (D-080):
   ```powershell
   adb logcat -v time -s IDRTunnelFsm
   ```

---

## Test Execution Steps

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     STEP 1      │       │     STEP 2      │       │     STEP 3      │
│  Indoor Walk    │ ────► │  Manual Force   │ ────► │ Return Outdoors │
│  (GNSS Timeout) │       │  Override Pill  │       │ (Reconvergence) │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │     STEP 4      │
                                                    │ Mapped Corridor │
                                                    │  (Drive / Walk) │
                                                    └─────────────────┘
```

---

### Step 1: Indoor Walk & Autonomous Entry (`GNSS_TIMEOUT`)

*Objective:* Verify that losing satellite signals indoors triggers the autonomous transition into
`TUNNEL_ACTIVE_IDR` via timeout without user interaction, crossfading to the 3D tunnel corridor.

#### Execution Procedure
1. Stand outdoors under open sky with clear satellite line-of-sight.
2. Launch the **IDR Navigator** app. Grant location permissions if prompted.
3. Confirm status pill reads green **GNSS Lock**.
4. Tap the **Start** button in the bottom drawer to initiate active navigation and recording.
5. Walk indoors into a building interior (e.g. basement, hallway, or concrete structure) away from windows.
6. Continue walking for ~3–5 seconds until satellite signals collapse ($C/N_0$ drops or fix age exceeds 1.2 s).

#### Observable UI State
- **Autonomous Transition**: FSM shifts `GNSS_HEALTHY` $\to$ `TUNNEL_ACTIVE_IDR` via `TunnelTrigger.GNSS_TIMEOUT` (D-126).
- **Status Pill**: Turns amber with text `IDR · GNSS denied`.
- **Map Crossfade**: The 2D map smoothly crossfades (900 ms tween) into `TunnelCorridor` rendering the 3D obsidian tube, cyan wall boundary lines, structural ribs, ceiling lamps, and the vehicle puck with its 1-sigma uncertainty ellipse.
- **Motion Behavior (R-B)**: As you walk indoors, ceiling lamps and dashed lane lines scroll backwards based strictly on `poseElapsedMs` advance. At a dead stop, all scrolling freezes immediately.
- **Guidance Banner**:
  - Primary text: `In tunnel · inertial`
  - Secondary text: `Exit distance unknown` (since the phone is not inside a mapped tunnel asset)
- **Exit Progress Bar**: **Hidden** (`telemetry.tunnelFix?.inside == true` is false; no asset fix).
- **Contextual Hazard Chips** (R-F):
  - `[ 💡 Headlights ]` (active in `TUNNEL_ACTIVE_IDR`)
  - `[ 🚫 GNSS suppressed ]` (active while `tunnelModeActive == true`)
  - `[ 🔅 Low light ]` (animates in if indoor ambient illuminance drops below $50\text{ lux}$)
- **Speed HUD**: Circular gauge in bottom-left shows forward walking velocity (e.g. `4 km/h`) with sub-caption `filter speed` (D-081).

#### What to Screenshot
- **Screenshot 1A**: Full screen immediately after indoor entry showing the 3D `TunnelCorridor` tube, guidance banner reading `In tunnel · inertial`, the active hazard chips row, and the bottom telemetry drawer.

#### TelemetryState Fields to Read
| Location | Field / Metric | Expected Value Range |
|---|---|---|
| Telemetry Card 1 | `telemetry.speedMps * 3.6` | Measured walking speed ($2.0 \dots 6.0\text{ km/h}$) |
| Telemetry Card 2 | `telemetry.uncertaintyM` | `±4` to `±15` `m est. σ` (expanding honest covariance) |
| Telemetry Card 3 | `telemetry.satellites` | `0 Sats` |
| Secondary Info Row | `telemetry.sampleRateHz` | Measured IMU rate (e.g. `125 Hz IMU` on team A55) |
| Secondary Info Row | `telemetry.ambientLux` | Measured illuminance (e.g. `< 50 lx` if dimly lit) |
| Secondary Info Row | `telemetry.cn0Top4DbHz` | Hidden or null |
| Secondary Info Row | `telemetry.stepCount` | Step counter incrementing with walking cadence |
| Logcat Stream | `IDRTunnelFsm` | `tunnel GNSS_HEALTHY -> TUNNEL_ACTIVE_IDR via GNSS_TIMEOUT` |

---

### Step 2: Manual Tunnel Mode Options: Auto, On, and Off

*Objective:* Verify that the 3-option tunnel mode selector provides full operator control over the
state machine (D-126), supporting autonomous operation (`Auto`), manual forced dead reckoning (`On`),
and explicit tunnel suppression (`Off`), raising the `[ 🔒 Forced ]` chip only when forced on.

#### Execution Procedure
1. Locate the `Tunnel [ Auto | On | Off ]` selector in the secondary action row beneath the guidance banner.
2. Tap the `On` option:
   - Observe the option highlight in amber (`palette.statusWarn`).
   - Observe the FSM transition to `TUNNEL_ACTIVE_IDR` via trigger `MANUAL_ON`.
   - Observe the `[ 🔒 Forced ]` hazard chip animate into view.
3. Tap the `Off` option:
   - Observe the option highlight in soft red.
   - Observe the FSM pin into `GNSS_HEALTHY` via trigger `MANUAL_OFF` (tunnel suppression suppressed).
   - The `[ 🔒 Forced ]` chip animates out and tunnel corridor collapses.
4. Tap the `Auto` option:
   - Observe the option highlight in primary cyan.
   - The FSM returns to autonomous sensor-driven evaluation (C/N0, lux drop, baro piston, map portals, GNSS timeout).

#### Observable UI State
- **Selector State**:
  - `Auto`: primary cyan highlight, autonomous FSM active.
  - `On`: amber highlight, forced dead reckoning active.
  - `Off`: soft red highlight, forced GNSS healthy active.
- **Status Pill**:
  - When `On`: `IDR · GNSS denied (forced)`
  - When `Off`: `GNSS lock`
- **Guidance Banner**: Updates to `In tunnel · inertial (forced)` when `On`.
- **Hazard Chips**: `[ 🔒 Forced ]` chip is visible if and only if `On` is selected (`telemetry.tunnelOverride == TunnelOverride.FORCE_ON`).

#### What to Screenshot
- **Screenshot 2A**: Screen showing `Tunnel [ Auto | On* | Off ]` selector with `On` active, `In tunnel · inertial (forced)` banner text, and the visible `[ 🔒 Forced ]` chip.
- **Screenshot 2B**: Screen showing `Tunnel [ Auto | On | Off* ]` selector with `Off` active.

#### TelemetryState Fields to Read
| Location | Field / Metric | Expected Value Range |
|---|---|---|
| State Property | `telemetry.tunnelOverride` | `TunnelOverride.AUTO`, `FORCE_ON`, or `FORCE_OFF` |
| State Property | `telemetry.tunnelForced` | `true` (when `On`), `false` (when `Auto` or `Off`) |
| Top Status Pill | `telemetry.tunnelState` | `TUNNEL_ACTIVE_IDR` (when `On`), `GNSS_HEALTHY` (when `Off`) |
| Logcat Stream | `IDRTunnelFsm` | `tunnel ... via MANUAL_ON` / `MANUAL_OFF` |

---

### Step 3: Return Outdoors & Anti-Jump Reconvergence

*Objective:* Verify smooth $\chi^2$ innovation gating and anti-jump reconvergence when satellites
reappear, culminating in the D-124 exit toast.

#### Execution Procedure
1. Ensure the manual force toggle is **OFF** (`Tunnel: auto`).
2. Walk out of the building into clear open sky.
3. Keep the phone steady as satellite tracking resumes ($C/N_0$ rises $> 24\text{ dB-Hz}$ or new fixes arrive).

#### Observable UI State
- **State 4 (`EXIT_VERIFICATION`)**:
  - Status pill turns amber: `Verifying GPS fix`.
  - Guidance banner:
    - Primary text: `Checking GNSS`
    - Secondary text: `N/M fixes passed` (e.g. `1/1 fixes passed`)
  - **Zero Teleportation (D-124)**: The vehicle puck does not snap or jump violently. Fixes exceeding the $\chi^2$ Mahalanobis gate ($d^2 > 9.21$) are rejected.
- **State 5 (`SEAMLESS_RECONVERGENCE`)**:
  - Upon 2 consecutive accepted fixes, the FSM transitions via `CHI2_PASS`.
  - Banner reads: `GNSS re-acquired` • `blending`.
  - The vehicle puck smoothly blends dead-reckoned pose onto the verified GNSS track over 2 seconds.
- **Exit Summary Toast (`ReconvergenceToast`)**:
  - A dark floating dialog appears at the top displaying measured outage metrics:
    ```
    GNSS restored
    [dist] m on IDR · [duration]s
    exit residual vs GNSS: [res] m
    [accepted] passed, [rejected] rejected
    ```
  - Displays **only** honest measured quantities: distance on IDR, elapsed time, exit residual vs first accepted GNSS fix, and gate counts. Zero drift % or grades.
- **Steady State (`GNSS_HEALTHY`)**:
  - After 2000 ms settle time, FSM completes reconvergence.
  - Screen crossfades back from `TunnelCorridor` to 2D `MapView`.
  - Status pill returns to green `GNSS Lock`.
  - Guidance banner returns to `Heading <Direction>` and total distance traveled.

#### What to Screenshot
- **Screenshot 3A**: During `EXIT_VERIFICATION` showing `Checking GNSS` banner and pass counts.
- **Screenshot 3B**: The floating `ReconvergenceToast` showing `exit residual vs GNSS` and gate statistics.

#### TelemetryState Fields to Read
| Location | Field / Metric | Expected Value Range |
|---|---|---|
| Guidance Banner | `telemetry.tunnelState` | `EXIT_VERIFICATION` $\to$ `SEAMLESS_RECONVERGENCE` $\to$ `GNSS_HEALTHY` |
| Exit Toast | `telemetry.lastExit.distanceOnIdrM` | Measured indoor distance traveled (e.g. `45 m`) |
| Exit Toast | `telemetry.lastExit.elapsedMs` | Outage duration (e.g. `32000 ms`) |
| Exit Toast | `telemetry.lastExit.exitResidualM` | `1.5` to `12.0 m` (residual vs first accepted fix) |
| Exit Toast | `telemetry.lastExit.acceptedFixes` | $\ge 2$ |
| Exit Toast | `telemetry.lastExit.reacquiredByForce` | `false` |
| Telemetry Card 3 | `telemetry.satellites` | Recovered count (e.g. `14 Sats`) |
| Secondary Info Row | `telemetry.cn0Top4DbHz` | Recovered carrier-to-noise (e.g. `36 dB-Hz`) |
| Logcat Stream | `IDRTunnelFsm` | `via CHI2_PASS at ... ms`, then `via RECONVERGED` |

---

### Step 4: Mapped Corridor Verification (Simulated Local Street Run)

*Objective:* Verify that when the vehicle approaches and enters a declared tunnel corridor from
`tunnels.json`, the pre-arming warning appears at $\le 500\text{ m}$, the exit progress bar
activates upon entry, and the progress bar fills as distance is covered.

#### Preparation (Local Street Mapping)
1. Pick a straight 300–600 m street segment near your test location.
2. Note the start coordinate (entry portal) and end coordinate (exit portal) using Google Maps or GPS coordinates.
3. Open `android-ui/app/src/main/assets/tunnels.json` and temporarily replace the coordinates:
   ```json
   {
     "schema": "idr.tunnels.v1",
     "note": "Temporary test corridor coordinates for desk run.",
     "tunnels": [
       {
         "id": "desk-run-corridor",
         "name": "Local Test Street",
         "centreline": [
           { "lat": YOUR_START_LAT, "lon": YOUR_START_LON },
           { "lat": YOUR_END_LAT,   "lon": YOUR_END_LON }
         ],
         "postedLimitKmh": 50
       }
     ]
   }
   ```
4. Re-install the debug APK (`.\gradlew.bat --no-daemon :app:assembleOsmDebug` + `adb install -r ...`).

#### Execution Procedure
1. Start recording outdoors at least 600 m away from `YOUR_START_LAT`.
2. Drive or walk towards the entry coordinate along the street centerline.
3. Cross the entry portal coordinate and continue driving along the mapped segment to the exit coordinate.
4. After completing the test, restore `tunnels.json` to its original committed placeholder.

#### Observable UI State
- **Approach Zone ($D_{\text{entry}} \le 500\text{ m}$)**:
  - Guidance banner switches to:
    - Primary: `Tunnel ahead`
    - Secondary: `Local Test Street · <dist> m` (distance rounded to 10 m)
- **Pre-Arming Zone ($D_{\text{entry}} \le 40\text{ m}$)**:
  - FSM transitions to `PRE_ARMED_ENTRY` via `TunnelTrigger.PORTAL_NEAR`.
  - Status pill turns amber: `Pre-arming IDR`.
  - Hazard chips show `[ 💡 Headlights ]`.
- **Entry & Corridor Navigation ($0 \le \text{alongM} \le \text{lengthM}$)**:
  - FSM transitions to `TUNNEL_ACTIVE_IDR` via `TunnelTrigger.PORTAL_PASSED`.
  - `TunnelCorridor` 3D tube renders.
  - **Exit Progress Bar activates (`ExitProgressBar`)**:
    - Appears directly under Guidance Banner.
    - Left text: `<alongM> m / <lengthM> m`
    - Right text: `Exit in ~<tSec>s` (computed from current speed, rounded to 5 s)
    - Cyan progress bar fill expands from 0% to 100% proportionally as you move forward.
  - **Speed HUD**:
    - Shows vehicle speed.
    - Displays a white/amber tick at the 50 km/h limit position.
    - Arc transitions to amber if speed exceeds 50 km/h.
  - **Hazard Chips**:
    - `[ ⚡ Limit 50 km/h ]` chip is displayed (derived from asset `postedLimitKmh`).
  - **Portal Far Glow**: A cyan/white glow circle at the vanishing point expands in radius and brightness as remaining distance shrinks.

#### What to Screenshot
- **Screenshot 4A**: Approach zone showing `Tunnel ahead · Local Test Street · <dist> m`.
- **Screenshot 4B**: Inside corridor at ~50% progress showing `ExitProgressBar` filled halfway, `[ ⚡ Limit 50 km/h ]` chip, and `SpeedHud` tick mark.

#### TelemetryState Fields to Read
| Location | Field / Metric | Expected Value Range |
|---|---|---|
| State Property | `telemetry.tunnelFix.inside` | `true` while between entry and exit portals |
| State Property | `telemetry.tunnelFix.alongM` | Increasing from `0.0` to `lengthM` |
| State Property | `telemetry.tunnelFix.remainingM` | Decreasing from `lengthM` to `0.0` |
| State Property | `telemetry.tunnelFix.lateralM` | Cross-track offset ($< 30\text{ m}$) |
| Exit Progress Bar | Along / Length | `<alongM> m / <lengthM> m` matching geometry |
| Speed HUD | Gauge & Limit Tick | Speed reading with limit tick at 50 km/h |
| Hazard Chips | Posted Limit Chip | `Limit 50 km/h` |

---

## Post-Test Cleanup Checklist

- [ ] Revert any temporary changes made to `android-ui/app/src/main/assets/tunnels.json`:
  ```powershell
  git checkout android-ui/app/src/main/assets/tunnels.json
  ```
- [ ] Verify working tree cleanliness and surface test compliance:
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/test_android_demo_surface.py -q
  ```
- [ ] Save captured screenshots to desk run archive with session timestamp.
- [ ] Archive `adb logcat -s IDRTunnelFsm` transition trace for submission audit records.
