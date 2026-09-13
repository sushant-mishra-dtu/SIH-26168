# Autonomous Tunnel Mode & Navigation Upgrades: Google Maps & Mappls Feature Roadmap

**Project:** Smart India Hackathon 2026 — Problem Statement 26168  
**Domain:** Intelligent Dead Reckoning (IDR) for GNSS-Denied Ground Vehicle Navigation  
**Scope:** Research, Architectural Specification, and Upgrade Proposals for Autonomous Tunnel Navigation, Map Matching, and Consumer-Grade Navigation Features (Benchmarked against Google Maps and Mappls / MapmyIndia)  
**Status:** Design Proposal & Research Specification (Zero code changes made)  

> **Reviewer note (13 Sep 2026).** The app will use the **Mapbox Navigation SDK for Android** as its navigation UI. The review of that SDK against this document lives in [UI_UX_NAVIGATION_PLAN.md §7](UI_UX_NAVIGATION_PLAN.md#7-review-inputs--building-this-plan-on-the-mapbox-navigation-sdk-for-android) and supersedes four parts of this proposal: **§1.1.B** portal geofencing (the SDK's `upcomingRoadObjects` / `inTunnel` provide it), **§3.3** and the **Tier 3/4 blueprint** (MapLibre + Valhalla/GraphHopper are replaced by Mapbox + a pre-downloaded `TileStore` region; custom routers do not exist in SDK v3), **§3.5 "Exit Quality Telemetry"** and the **§3.1 HUD drift figure** (D-112: no Android surface may display *drift* or a grade — the on-device quantity is an *exit residual vs GNSS*), and the **§2 benchmark row on tunnel continuity** (the SDK ships its own dead reckoning, which must be disabled — `enableSensors(false)` — and out-fed so that the InEKF is provably the estimator driving the puck).

---

## Executive Summary

While commercial navigation applications such as **Google Maps** and **Mappls (MapmyIndia)** provide rich visual experiences, turn-by-turn guidance, and traffic telemetry, they exhibit significant degradation when entering **GNSS-denied environments** (tunnels, underground expressways, flyover underpasses, multi-level basements, and dense urban canyons). When satellite signals drop:
- Standard consumer apps often freeze the position icon, display a "Searching for GPS" banner, or extrapolate movement using crude constant-velocity coasting along a precomputed route polyline.
- As soon as the vehicle accelerates, stops, or navigates a curved tunnel (e.g., the *Atal Tunnel*, *Delhi Pragati Maidan Tunnel*, or *Mumbai Coastal Road Undersea Tunnel*), the visual marker either falls behind, overtakes reality, or jumps violently across parallel surface roads.

This proposal outlines the architectural upgrade path to elevate our **IDR-26168 platform** into a consumer-grade, production-ready navigation suite. The core objective is **autonomous, zero-touch switching**:
1. Continuously navigate using high-precision GNSS when available.
2. The instant the vehicle enters a tunnel or loses satellite visibility, **autonomously engage "Tunnel Mode" (Intelligent Dead Reckoning)** within milliseconds without manual user intervention.
3. Preserve position, heading, and speed continuity under an **Invariant EKF on $\mathrm{SE_2}(3)$**, kinematic constraints (NHC/ZUPT/ZARU), and 1D centerline map-matching.
4. Provide a rich driver UX matching Google Maps and Mappls: automatic night/tunnel mode inversion, 3D tunnel corridor visualization, exit distance countdowns, Indian highway safety advisories (headlight warnings, speed breakers, lane guidance), and smooth, jump-free GNSS re-convergence upon exit.

---

## 1. Autonomous Tunnel & GNSS Loss Detection Engine

Currently, our prototype demo supports a manual toggle pill for tunnel simulation. In production, this must be **100% autonomous and instant**. A vehicle travelling at $60\text{ km/h}$ covers $16.7\text{ m/s}$; a detection lag of 3 seconds results in a 50-meter blind zone. 

To achieve sub-500ms trigger latency while avoiding false positives (such as passing under a narrow pedestrian footbridge or dense tree canopy), we specify a **Multi-Sensor Bayesian Fusing State Machine (FSM)**.

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 Multi-Sensor Triggers                  │
                  ├───────────────────┬───────────────────┬────────────────┤
                  │   GNSS Quality    │  Ambient Hardware │ Map Geofencing │
                  │  • C/N0 collapse  │  • Light (lux)    │ • Portal radius│
                  │  • Sat count < 3  │  • Barometer ΔP   │ • Route vector │
                  │  • HDOP / PDOP >5 │  • Cell RSRP drop │   heading match│
                  └─────────┬─────────┴─────────┬─────────┴────────┬───────┘
                            │                   │                  │
                            ▼                   ▼                  ▼
                   ┌──────────────────────────────────────────────────────┐
                   │    Autonomous Transition Engine (Hysteresis FSM)     │
                   └──────────────────────────┬───────────────────────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
              [Filter Action]            [Map Action]            [UI / UX]
              • Freeze Gyro Bias         • Snap to 1D Spline     • Dark Mode Inversion
              • Tighten NHC Covariance   • Lock Tunnel Corridor  • 3D Tube View
              • Engage Speed Head        • Supress Off-Route     • Exit Countdown
```

### 1.1 Trigger Detection Layers

#### A. GNSS Carrier-to-Noise Ratio ($C/N_0$) and Geometry Collapse
Standard location listeners only report a fix or timeout after several seconds. By tapping Android's raw `GnssStatus.Callback` and `GnssMeasurementsEvent.Callback`:
- **Average $C/N_0$ Collapse:** Track top-4 satellites' carrier-to-noise ratio. Outdoor clear sky ranges between $36\text{ to }48\text{ dB-Hz}$. Upon tunnel entry, average $C/N_0$ drops sharply below $18\text{ dB-Hz}$ within $\mathbf{300\text{ ms}}$.
- **Used-in-Fix Count:** Drops rapidly from $12\text{+} \to 0$.
- **Dilution of Precision (HDOP/PDOP):** High multipath at the tunnel mouth causes pseudorange residuals to spike, driving HDOP $> 4.5$.

#### B. Map-Based Predictive Portal Geofencing (Zero-Latency Pre-Arming)
Google Maps and Mappls maintain road graph attributes with tags: `tunnel=yes`, `layer=-1`, `covered=yes`.
- When following an active route, compute along-track distance to the next tunnel portal $D_{\text{portal}}$.
- **Pre-Arming ($D_{\text{portal}} < 40\text{ m}$):** Take a high-precision snapshot of gyro zero-rate bias ($b_g$), vehicle heading, and forward velocity.
- **Entry Confirmation ($D_{\text{portal}} \le 0\text{ m}$):** Immediately arm Tunnel Mode without waiting for GNSS watchdog timeouts.

#### C. Ambient Light Sensor (`Sensor.TYPE_LIGHT`)
- Modern smartphones placed on windshield/dashboard mounts expose the ambient lux sensor.
- Daylight illuminance ranges from $10,000\text{ to }100,000\text{ lux}$; illuminated tunnels rarely exceed $50\text{ to }250\text{ lux}$.
- A sudden negative derivative $\frac{d(\text{lux})}{dt} < -5,000\text{ lux/s}$ coinciding with a GNSS $C/N_0$ drop provides an unambiguous optical confirmation of tunnel entry.

#### D. Barometric Piston Effect (`Sensor.TYPE_PRESSURE`)
- Entering an enclosed tunnel at speed creates an aerodynamic pressure wave (the *tunnel piston effect*), causing a sharp transient pressure spike ($\Delta P \approx +0.3\text{ to }0.8\text{ hPa}$) within $200\text{ ms}$, easily detected by smartphone barometers before temperature stabilizes.

### 1.2 Finite State Machine (FSM) Specification

```
                     GNSS_HEALTHY
                          │
          [C/N0 drops OR Portal dist < 40m]
                          ▼
                   PRE_ARMED_ENTRY
                          │
         [Signal Lost (>1.2s) OR In-Tunnel Portal]
                          ▼
                  TUNNEL_ACTIVE_IDR  ◄────────────┐
                          │                       │
           [Satellites reappear: C/N0 > 24]       │ [χ² test fails:
                          ▼                       │  multipath artifact]
                  EXIT_VERIFICATION ──────────────┘
                          │
           [χ² test passes for 2 consecutive fixes]
                          ▼
                 SEAMLESS_RECONVERGENCE
                          │
                          ▼
                     GNSS_HEALTHY
```

| State | Entry Condition | Filter Action | UI State |
|---|---|---|---|
| **GNSS_HEALTHY** | $\ge 4$ sats, $C/N_0 > 28\text{ dB-Hz}$, $\text{HDOP} < 2.0$ | Continuous InEKF propagation + GNSS update | Day/Night default, satellite lock badge |
| **PRE_ARMED_ENTRY** | $D_{\text{portal}} < 40\text{ m}$ OR $C/N_0$ sudden drop | Snapshot $b_g$, freeze scale factors, pre-warm NHC | Status pill changes to amber: *"Entering Tunnel..."* |
| **TUNNEL_ACTIVE_IDR** | No GNSS fix $> 1.2\text{ s}$ OR passed portal node | Suppress GNSS, enable SE₂(3) DR, 1D spline snap | Auto-Dark theme, 3D Tunnel Corridor, exit bar |
| **EXIT_VERIFICATION** | Satellites detected at exit portal | Buffer GNSS fixes, run $\chi^2$ innovation gate | *"Restoring GPS..."* (No visual jump allowed) |
| **SEAMLESS_RECONVERGENCE** | $\chi^2$ innovation passes consecutively | Smooth Kalman update, shrink covariance ellipse | *"GPS Restored"*, drift telemetry displayed |

---

## 2. Feature Benchmarking: Google Maps vs. Mappls vs. Proposed IDR Upgrades

| Feature Category | Google Maps | Mappls (MapmyIndia) | Proposed IDR Upgrade |
|---|---|---|---|
| **Tunnel Navigation Continuity** | Uses basic coasting; supports Bluetooth Beacons in select global tunnels (Waze Beacons). In uninstrumented tunnels, arrow frequently freezes or jumps. | Uses route speed extrapolation; alerts user upon entering, but loses precision in long or curved tunnels. | **Self-contained Intelligent Dead Reckoning**: Continuous 200 Hz IMU propagation on SE₂(3 Lie Group), zero-acceleration double integration, learned speed head, and 1D centerline matching. Independent of external beacons. |
| **Tunnel Entry Transition** | 3–6 second lag before switching to dead-reckoning/extrapolation. | Prompt notification, but arrow stutters if speed varies from historical traffic. | **Sub-500ms autonomous transition** via combined GNSS $C/N_0$ collapse, ambient light, and road portal geofencing. |
| **Tunnel Interior UX** | Standard map in dark mode. | 2D/3D map with portal icon. | **3D Illuminated Tunnel Tube Corridor** with distance-to-exit bar, remaining tunnel length, and emergency alcove / SOS markers. |
| **Indian Road Specifics** | Basic speed camera alerts; variable road name accuracy. | **Market Leader**: Junction views, 3D flyover splits, speed breakers, potholes, sharp curves, toll plaza lane advice. | **Integrate Mappls-grade Indian road hazards**: Advance warnings for rumble strips, unlit tunnels, steep ghat curves, and toll booths before tunnel entrances. |
| **Map Matching in Tunnels** | Snaps to road network; can glitch onto surface streets above shallow tunnels. | Snaps to highway centerline; occasionally jumps onto parallel service lanes. | **Covariance-driven 1D HMM Spline Matcher**: Constrains vehicle laterally along the 3D tunnel centerline, using vertical altitude to reject surface roads. |
| **Offline Operation** | Requires pre-downloading offline areas; vector tiles sometimes lack rich 3D metadata. | Dedicated offline navigation packs. | **Embedded Offline Vector Maps (MapLibre Native / Tangram-ES)** with pre-cached tunnel geometries and offline turn-by-turn routing (Valhalla/GraphHopper). |
| **Re-acquisition Jump** | Arrow can jump 30–80m backwards or sideways upon exiting a tunnel due to initial multipath fixes. | Arrow snaps abruptly to newly acquired coordinates. | **Chi-squared ($\chi^2$) Innovation Gating & Smooth Kalman Blending**: Rejects exit multipath spikes; smoothly converges without visual teleportation. |

---

## 3. High-Value Navigation Upgrades (Detailed Specifications)

### 3.1 3D Tunnel Interior Visualization & Tunnel UI Mode
When driving through long tunnels (e.g., *Atal Tunnel: 9.02 km*, *Syama Prasad Mookerjee Tunnel: 9.28 km*, or Delhi's *Pragati Maidan Tunnel: 1.3 km*), viewing a generic outdoor flat map is disorienting.

#### Specification:
1. **Dynamic Theme Inversion (Auto-Dark / Tunnel Vision):**
   - Automatically invert the map canvas to high-contrast deep black/charcoal (`#121212`) upon entering, protecting driver night vision.
2. **3D Tunnel Corridor Perspective:**
   - Switch camera perspective to a 3D isometric or forward chase view ($45^\circ$ tilt angle).
   - Render the road as an illuminated 3D tube corridor with glowing tunnel walls, lane markings, and ceiling lights moving realistically with vehicle speed.
3. **Tunnel Telemetry HUD Overlay:**
   - **Tunnel Name Banner:** e.g., *"Pragati Maidan Tunnel — Main Bore"*.
   - **Exit Progress Bar:** Dynamic progress bar showing:
     - Remaining distance (e.g., *"Tunnel exit in 750 m"*).
     - Estimated time to exit at current speed.
     - Speed limit advisory inside tunnel (e.g., *"Speed Limit: 50 km/h"*).
   - **Safety Warnings:**
     - *"Turn on low-beam headlights"*
     - *"Maintain 50m safe distance"*
     - *"No lane change allowed inside tunnel"*

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [▲ 500m]  Exit Tunnel towards Ring Road / Sarai Kale Khan               │
│ ═══════════════════════════════════════════════════════════════════════ │
│ TUNNEL PROGRESS: [████████████████████░░░░░░░░░░░░] 620m / 1,300m       │
│                                                                         │
│                               / \                                       │
│                              /   \                                      │
│                             /  ▲  \  <-- 3D Illuminated Tunnel Tube     │
│                            /   │   \                                    │
│                           /    │    \                                   │
│                          /     │     \                                  │
│                                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  SPEED: 48 km/h  │  ESTIMATOR: IDR InEKF  │  DRIFT: ±2.8m (0.4%)        │
│  [ HEADLIGHTS ON ]   [ SPEED LIMIT 50 ]      [ NO OVERTAKING ]          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Indian Driving Realities (Mappls Benchmark Upgrades)
Indian driving conditions introduce unique challenges that degrade standard global algorithms:

1. **Pre-Tunnel Speed Breakers and Rumble Strips:**
   - Indian highway tunnels almost universally feature high-amplitude rumble strips or speed bumps at entry and exit portals to enforce speed deceleration.
   - *Issue:* Without filtering, standard accelerometer-based velocity integrators register vertical shock as massive horizontal deceleration.
   - *Upgrade:* **Shock Acceleration Wavelet Rejection**: Isolate the high-frequency $Z$-axis shock spike ($> 20\text{ Hz}$) from vehicle longitudinal acceleration, preventing phantom velocity drops.
2. **Stop-and-Go Traffic Inside Tunnels (ZUPT / ZARU):**
   - Tunnels often experience complete gridlock. While stationary, open-loop dead reckoning drifts rapidly due to integrated sensor bias.
   - *Upgrade:* **Zero Velocity Update (ZUPT)** and **Zero Angular Rate Update (ZARU)**: Lock forward velocity to exactly $0.0\text{ m/s}$ and yaw rate to zero whenever wheels stop moving. Covariance growth is frozen during stops.
3. **3D Complex Multi-Level Junctions & Flyover Splits:**
   - Elevated corridors (such as Delhi's Barapullah, Mumbai's Eastern Freeway, or Bengaluru's Electronic City flyover) pass above or plunge beneath surface streets.
   - *Upgrade:* **Barometric Vertical Separation**: Use high-precision pressure delta tracking ($\Delta h = -8.43 \cdot \Delta P\text{ m/hPa}$) to distinguish whether the vehicle is on the elevated flyover, surface road, or subterranean underpass.

---

### 3.3 Full Offline Navigation Stack (The Connectivity Void)
Most tunnels have zero 4G/5G cellular coverage. An app that relies on streaming raster map tiles turns blank (empty grid), and cloud routing engines fail if the user re-routes inside a tunnel.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OFFLINE NAVIGATION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────┐          ┌────────────────────────────────┐  │
│  │   Vector Tile Cache   │          │     Offline Routing Engine     │  │
│  │  (MapLibre / MBTiles) │          │     (Valhalla / GraphHopper)   │  │
│  │  • Offline Roads      │          │  • Offline Turn-by-Turn        │  │
│  │  • 3D Tunnel Meshes   │          │  • In-Tunnel Rerouting         │  │
│  │  • Hazard Geometries  │          │  • Lane Guidance Manifolds     │  │
│  └───────────┬───────────┘          └───────────────┬────────────────┘  │
│              │                                      │                   │
│              ▼                                      ▼                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                InEKF Lie Group 1D Spline Matcher                  │  │
│  │   • Snaps vehicle to offline polyline spline                      │  │
│  │   • Longitudinal motion along spline; zero lateral drift          │  │
│  └──────────────────────────────────┬────────────────────────────────┘  │
│                                     │                                   │
│                                     ▼                                   │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                Android Compose Native Navigation UI               │  │
│  │   • Course-Up 60fps Vector Map                                    │  │
│  │   • Turn Guidance Banner + Distance Countdown                     │  │
│  │   • Dual-Language Audio Voice Prompts (Hindi + English)           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Proposed Component Upgrades:
- **Vector Map Renderer:** Migrate map canvas from OSMDroid raster tiles to **MapLibre Native (Android SDK)**. Vector tiles allow dynamic 60fps rotation (Course-Up), 3D camera pitching, smooth zoom transitions, and embedded custom 3D tunnel meshes.
- **Offline Routing Core:** Embed **Valhalla** or **GraphHopper Mobile** via C++/Android NDK. Provides real-time turn-by-turn guidance and dynamic re-routing completely offline.
- **Voice Guidance (Hindi & English):** Android Text-to-Speech (TTS) integration delivering natural Indian English and Hindi alerts (*"500 meter mein tunnel exit hai, baayein rukaav par dhyaan dein"*).

---

### 3.4 1D Manifold Map-Matching along Tunnel Centerlines
In open terrain, position uncertainty expands in two dimensions (North and East covariance ellipse). Inside a tunnel, this 2D assumption is physically invalid: **a vehicle cannot drift laterally through concrete tunnel walls**.

#### Mathematical Formulation:
- Represent the tunnel trajectory as a parametric 3D cubic spline:
  $$\mathbf{r}(s) = \begin{bmatrix} x(s) \\ y(s) \\ z(s) \end{bmatrix}, \quad s \in [0, L]$$
- Where $s$ represents along-track distance and $L$ is tunnel length.
- The InEKF dead-reckoning state estimates along-track displacement $\hat{s}$ and forward velocity $v$.
- Cross-track error $e_{\perp}$ is constrained to zero with an artificial pseudo-measurement:
  $$z_{\perp} = 0 = \mathbf{n}(s)^T (\mathbf{p} - \mathbf{r}(s)) + \nu_{\perp}, \quad \nu_{\perp} \sim \mathcal{N}(0, R_{\perp})$$
- Setting $R_{\perp} = 0.05\text{ m}^2$ prevents any lateral divergence, converting the navigation problem into a pure 1D longitudinal tracking problem.
- **Outcome:** Heading drift is effectively bounded by the road geometry, reducing lateral position error to near zero throughout the tunnel.

---

### 3.5 Tunnel Exit & GNSS Re-convergence (Anti-Jump Filter)
The most common flaw in consumer GPS applications is the **"Exit Shock"**:
- When exiting a tunnel, the GNSS receiver acquires satellite signals with severe multipath reflections off canyon/portal walls, diluted geometry, and clock offsets.
- A naive system accepts these fixes immediately, causing the vehicle icon to jump 50 meters into a side street or backward into the tunnel.

#### Robust Re-acquisition Strategy:
1. **$\chi^2$ Innovation Gating:**
   When a new GNSS fix $\mathbf{z}_k$ arrives at time $k$, compute the normalized innovation squared (Mahalanobis distance):
   $$d^2 = \mathbf{y}_k^T \mathbf{S}_k^{-1} \mathbf{y}_k$$
   where $\mathbf{y}_k = \mathbf{z}_k - \mathbf{h}(\hat{\mathbf{x}}_k^-)$ and $\mathbf{S}_k = \mathbf{H}_k \mathbf{P}_k^- \mathbf{H}_k^T + \mathbf{R}_k$.
   - If $d^2 > \chi^2_{p, 0.99}$ (typically $9.21$ for 2 DoF), the measurement is **rejected** as an exit multipath artifact.
2. **Huber-Weighted Soft Absorption:**
   - Rather than binary accept/reject, apply a Huber loss function to downweight large residuals.
   - The filter smooths the incoming position updates over 1.5 to 2.5 seconds, gradually pulling the dead-reckoning trajectory onto the verified GNSS track without visual jerking or coordinate snapping.
3. **Exit Quality Telemetry:**
   - Log and display the cumulative dead-reckoning performance:
     $$\text{Drift Percentage} = \frac{\|\mathbf{p}_{\text{InEKF}} - \mathbf{p}_{\text{GNSS\_verified}}\|}{D_{\text{tunnel}}} \times 100\%$$
   - Demonstrates compliance with SIH-26168's $< 10\%$ drift threshold directly on the user interface.

---

## 4. Architectural Implementation Blueprint

To deliver these capabilities systematically without disrupting the validated core filter, the architecture is structured into four modular tiers:

```
[ Tier 1: Sensor & Hardware Layer ]
  ├── GnssMeasurements & GnssStatus (Raw C/N0, Doppler, Satellite Azimuth/Elevation)
  ├── High-Sampling-Rate Uncalibrated Sensors (200 Hz Gyroscope, Accelerometer)
  └── Auxiliary Peripherals (Ambient Light Sensor, Barometric Altimeter, Compass)
                          │
[ Tier 2: Estimation & Fusion Engine (Native C++ / Rust via JNI) ]
  ├── Error-State Invariant EKF on SE₂(3 Lie Group)
  ├── Autonomous Trigger FSM (Sub-500ms C/N0 & Portal Detector)
  ├── Kinematic Non-Holonomic Constraints (NHC) + ZUPT / ZARU Detectors
  └── Chi-Square Innovation Gating & Huber Multipath Rejection
                          │
[ Tier 3: Map & Geodata Engine ]
  ├── Offline Vector Routing (Valhalla / GraphHopper Embedded)
  ├── 1D Spline Road-Manifold Projector (Centerline Snapping)
  └── Indian Road Hazard Knowledge Base (Speed Breakers, Toll Plazas, Portals)
                          │
[ Tier 4: Presentation & UI Layer (Android Jetpack Compose) ]
  ├── MapLibre 60fps Native Vector Surface (Course-Up / 3D Pitch)
  ├── 3D Tunnel Interior Tube Renderer
  ├── Auto-Dark / Tunnel Vision Theme Engine
  ├── Google Maps / Mappls Turn-by-Turn Guidance Cards
  └── Audio Engine (Bilingual Voice Guidance in Hindi & English)
```

---

## 5. Phased Implementation Roadmap

### Phase 1: Autonomous Detection FSM & UI Tunnel Mode
*Objective: Eliminate manual toggle pill; make tunnel entry and exit fully automated.*
- Implement `AutonomousTunnelDetector.kt` monitoring:
  - Raw $C/N_0$ drop across tracked satellites.
  - Ambient light sensor lux gradient ($d(\text{lux})/dt$).
  - Proximity to mapped tunnel portal coordinates ($< 40\text{ m}$).
- Wire detector to auto-trigger existing `toggleTunnelMode()` backend logic.
- Implement auto-switching to dark theme and Google Maps navigation banner.

### Phase 2: Offline Mapping & 1D Spline Road Matching
*Objective: Ensure navigation continues when mobile data connection drops inside tunnels.*
- Integrate MapLibre Native SDK for 60fps vector tile rendering and 3D camera pitching.
- Package local offline MBTiles containing city expressway and tunnel geometries.
- Implement 1D spline projection along tunnel polylines to eliminate lateral drift.

### Phase 3: Indian Road Safety Intelligence (Mappls Parity)
*Objective: Integrate Indian road hazard intelligence and voice guidance.*
- Add pre-tunnel advisory cues: "Turn On Headlights", speed limit reminders, and no-overtaking warnings.
- Integrate shock wavelet filter to reject speed breaker / rumble strip impact from longitudinal odometry.
- Integrate Android TTS for English & Hindi voice navigation.

### Phase 4: Anti-Jump Re-acquisition & Sub-Meter Validation
*Objective: Perfect the exit transition and verify against ground truth.*
- Implement $\chi^2$ innovation gating on incoming GNSS fixes upon exiting tunnels.
- Add live drift audit telemetry card (showing cumulative distance, elapsed outage, and drift percentage).
- Benchmark against simulated and field-recorded tunnel runs (Atal Tunnel / Delhi Pragati Maidan data logs).

---

## 6. Conclusion

By implementing an **Autonomous Trigger Engine**, **1D Spline Road-Manifold Matching**, **MapLibre 3D Tunnel Visualizations**, and **Mappls-style Indian Road Hazard Intelligence**, the IDR-26168 system will surpass standard smartphone navigation apps in reliability. It transforms our robust mathematical InEKF core into an intuitive, production-grade navigation experience capable of navigating through India's most demanding underground and urban corridors without losing track of position for even a single meter.
