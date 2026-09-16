# UI/UX Design Plan: Consumer-Grade Navigation & Autonomous Tunnel Mode

**Project:** Smart India Hackathon 2026 — Problem Statement 26168  
**Document:** UI/UX Architecture & Interaction Design Plan  
**Benchmarks:** Google Maps (Fluidity & Glanceability) + Mappls / MapmyIndia (Indian Road Intelligence & 3D Junction Guidance)  
**Status:** Design Specification (No code modifications)  

---

## 1. Design Philosophy & High-Level Vision

A driver traveling at $60\text{ km/h}$ enters a darkened tunnel at $16.7\text{ m/s}$. In this high-cognitive-load environment, the navigation interface must deliver **instant glanceability, distraction-free legibility, and zero cognitive disorientation**.

When commercial apps like Google Maps or Mappls lose satellite signal, they often stutter, freeze the arrow, or display jarring warning dialogs. Our interface must do the exact opposite: **instantly and autonomously celebrate the transition into Intelligent Dead Reckoning**.

### Key Design Pillars
1. **Glanceability Under 200ms:** Information hierarchy prioritized for split-second driver cognition (high contrast typography, minimum 16sp labels, large iconography).
2. **Autonomous Lighting & Vision Inversion:** Automatic switch to deep obsidian black (`#0B0F19`) and glowing luminescent accents (`#38BDF8` Sky Cyan, `#10B981` Emerald, `#FBBF24` Amber) to preserve driver scotopic (night) vision.
3. **Continuous Spatial Motion:** The vehicle puck must NEVER freeze or stutter. It glides forward with smooth 60fps interpolation driven by the 200 Hz SE₂(3) InEKF Lie group edge filter.
4. **Contextual Indian Driving Realities (Mappls Benchmark):** Integration of high-value Indian road intelligence: advance warnings for rumble strips, unlit tunnels, speed limits, lane changes, and emergency SOS alcoves.
5. **Zero-Teleportation Re-convergence:** When emerging from the tunnel, the vehicle icon glides smoothly onto the verified GPS track without coordinate snapping or map twitching.

---

## 2. Dynamic Visual State Machine

The user experience progresses through five distinct visual stages:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   STAGE 1       │       │   STAGE 2       │       │   STAGE 3       │
│  Open Sky GNSS  │ ────► │  Approach Alert │ ────► │ Autonomous 3D   │
│  (Normal Drive) │       │ (40m to Portal) │       │ Tunnel Mode     │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
┌─────────────────┐       ┌─────────────────┐                │
│   STAGE 5       │       │   STAGE 4       │                │
│ Open Sky Steady │ ◄──── │  Anti-Jump Exit │ ◄──────────────┘
│  (Drift Toast)  │       │ Re-acquisition  │
└─────────────────┘       └─────────────────┘
```

---

### Stage 1: Open Sky Navigation (Normal Drive)
* **Visual Mode:** Standard Clean Vector Map (Day or Night based on system time / sun elevation).
* **Camera:** Dynamic Course-Up tracking, $20^\circ$ subtle tilt, auto-zooming dynamically based on speed ($50\text{ km/h} \to \text{Zoom 17}$, $100\text{ km/h} \to \text{Zoom 15.5}$).
* **Header:** Google Maps-style emerald/forest green navigation card (`#0F9D58`) with crisp turn maneuvers and next cross-street.
* **Puck:** Emerald navigation chevron with a tight $\pm 2.5\text{ m}$ pulsing GPS accuracy halo.
* **Status Badge:** Subtle green pill: `● GNSS 3D Fix (14 Sats)`.

---

### Stage 2: Approach & Portal Pre-Arming Zone ($D_{\text{portal}} < 100\text{ m}$)
*Trigger: Map geofence detects approaching tunnel portal or initial $C/N_0$ carrier-to-noise drop.*
* **Visual Transition:** The navigation banner splits into a dual-tiered card.
* **Hazard Alert Banner (Mappls Style):**
  * Yellow/Amber warning card slides down smoothly from top:
    * 💡 *"Turn on Low-Beam Headlights"*
    * ⚠️ *"Speed Limit: 50 km/h in Tunnel • No Overtaking"*
* **Filter Pre-Arming Indicator:**
  * Status badge shifts to amber: `◐ Pre-Arming IDR • Gyro Bias Frozen`.
  * The system quietly locks the gyro zero-rate bias snapshot before high-speed maneuvers inside the bore.

---

### Stage 3: Autonomous 3D Tunnel Interior Mode (Active IDR)
*Trigger: Autonomous FSM triggers on GNSS loss ($< 18\text{ dB-Hz}$) + ambient light sensor drop ($< 150\text{ lux}$).*

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ↱  In 450m, Exit Tunnel towards Ring Road / Nizamuddin                  │
│ ─────────────────────────────────────────────────────────────────────── │
│ TUNNEL PROGRESS: [████████████████████░░░░░░░░░░░░] 680m / 1,300m       │
│                                                                         │
│                           /               \                             │
│                          /      ( 50 )     \   <-- Speed Limit Badge    │
│                         /                   \                           │
│                        /   ▲   ▲   ▲   ▲     \  <-- Ceiling Lamp Lights │
│                       /                     \                           │
│                      /        /  ║  \        \                          │
│                     /        /   ║   \        \                         │
│                    /        /    ▲    \        \  <-- InEKF Vehicle Puck│
│                   /        /     ║     \        \     with Covariance   │
│                  /        /      ║      \        \    Confidence Ring   │
│                                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  SPEED: 48 km/h  │  ESTIMATOR: SE₂(3) InEKF  │  DRIFT EST: ±3.1m (0.4%) │
│  [ HEADLIGHTS ON ]   [ MAINTAIN DISTANCE ]   [ SOS ALCOVE: 120M ]       │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Visual Features in Tunnel Mode:
1. **Camera Shift:** Smoothly interpolates to a $45^\circ$ **3D Forward Chase Perspective**, putting the driver inside the bore.
2. **3D Illuminated Tunnel Tube Mesh:**
   * High-contrast dark obsidian map background (`#0B0F19`).
   * Translucent glowing neon cyan road corridor (`#0284C7` to `#38BDF8`).
   * Lateral tunnel wall wireframes with subtle distance markings every 100 meters.
   * Moving ceiling beacon lights that travel backward along the ceiling in direct sync with vehicle forward velocity.
3. **Tunnel Progress & Exit Countdown Bar:**
   * Dynamic horizontal progress bar embedded directly below the turn instruction banner.
   * Text: *"Pragati Maidan Tunnel — Bore 1 • Exit in 620 m (45s)"*.
4. **Indian Safety & Hazard Badges:**
   * Pill chips above the telemetry sheet:
     * `[ 💡 HEADLIGHTS ]`
     * `[ 🚫 NO LANE CHANGE ]`
     * `[ 🚨 SOS ALCOVE IN 120M ]`
5. **InEKF Uncertainty Halo (Real-Time Confidence):**
   * The vehicle puck is surrounded by a translucent amber confidence ring.
   * **At traffic jams (ZUPT Active):** Ring turns solid emerald and stops expanding — visually proving to the user that dead-reckoning error is locked and not drifting while stopped!
   * **During active driving:** Expands smoothly at $0.035\text{ m/m}$ traveled, reflecting honest filter covariance.

---

### Stage 4: Exit Portal & Anti-Jump Re-acquisition
*Trigger: Satellite $C/N_0$ reappears above $24\text{ dB-Hz}$ at the tunnel mouth.*
* **Zero Teleportation Guarantee:**
  * While the $\chi^2$ innovation gate verifies incoming fixes against the dead-reckoning trajectory, the UI displays a soft pulsating badge: `◎ Verifying GPS Fix...`.
  * The vehicle puck **never jumps**. If raw GPS reports a multipath artifact 40m to the right, the screen ignores it until satellite geometry clears the tunnel portal.
* **Seamless Kalman Convergence:**
  * Over a 1.5-second spring interpolation, the vehicle puck smoothly merges with the verified GNSS track.

---

### Stage 5: Open Sky Steady State & Performance Drift Summary
* **Temporary Floating Toast (5 seconds):**
  ```
  ╔══════════════════════════════════════════════════════════════╗
  ║  ✓ GPS Restored • Navigated 1,300m on IDR                    ║
  ║  Elapsed: 1m 38s  •  Filter Drift: 3.8m (0.29%)  •  Grade: A ║
  ╚══════════════════════════════════════════════════════════════╝
  ```
* Provides immediate psychological confidence that the system navigated the dead zone flawlessly.
* Map canvas transitions smoothly back to default Day/Night view.

---

## 3. Screen Layout Blueprint & UI Component Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [STATUS BAR: Time, Battery, Network, 200 Hz IMU Badge]                  │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ TOP NAVIGATION DRAWER (Google Maps Style)                          │ │
│ │ • Primary Maneuver Icon (Turn Left / Keep Right / Exit Tunnel)       │ │
│ │ • Distance to Next Maneuver + Road Name                             │ │
│ │ • Tunnel Progress Bar (Progress Fill, Remaining Meters, ETA)        │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│                                                                         │
│                         [ FULL-BLEED 3D MAP CANVAS ]                    │
│                                                                         │
│  [SPEED HUD]                                          [QUICK ACTIONS]   │
│  ┌───────────────┐                                    ┌──────────────┐  │
│  │   48  km/h    │                                    │  🧭 Compass   │  │
│  │  ───────────  │                                    │  (Course-Up) │  │
│  │  LIMIT:  50   │                                    ├──────────────┤  │
│  └───────────────┘                                    │  🎯 Recenter │  │
│                                                       ├──────────────┤  │
│                                                       │  🔊 Voice    │  │
│                                                       │  (Hindi/En)  │  │
│                                                       ├──────────────┤  │
│                                                       │  💡 Headlight│  │
│                                                       │     Alert    │  │
│                                                       └──────────────┘  │
│                                                                         │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ BOTTOM TELEMETRY SHEET (Mappls + Telemetry Fusion)                  │ │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │ │
│ │ │  REMAINING  │ │   ELAPSED   │ │   MODE      │ │  DRIFT ACCURACY │ │ │
│ │ │   4.2 km    │ │   12 min    │ │  IDR InEKF  │ │   ±2.8m (0.4%)  │ │ │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ │ │
│ │                                                                     │ │
│ │ [ Live Sensors: 200 Hz IMU ● ZUPT Active ● Satellites: 0 (Tunnel) ] │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. UI Design Token System (Theme Extensions)

Expanding our current `Theme.kt` with a dedicated **Tunnel Vision Palette**:

```kotlin
object IDRTunnelPalette : IDRPalette {
    override val isDark: Boolean = true
    
    // Backgrounds: Deep Void Obsidian
    override val bgPrimary = Color(0xFF080B11)      // Ultra-deep black
    override val bgSheet   = Color(0xFF0F172A)      // Slate 900 glass
    override val bgCard    = Color(0xFF1E293B)      // Slate 800
    
    // Navigation Accents: High-Luminescence Neon
    override val primary   = Color(0xFF38BDF8)      // Electric Cyan corridor
    override val navGreen  = Color(0xFF10B981)      // Emerald exit marker
    override val statusWarn= Color(0xFFFBBF24)      // Amber warning beacon
    override val statusError= Color(0xFFF87171)     // Red speed alert
    
    // Tunnel Specific Custom Tokens
    val tunnelWallGlow     = Color(0x3338BDF8)      // Translucent cyan tube
    val tunnelCeilingLamp  = Color(0xFFFFE082)      // Warm incandescent lamp
    val tunnelRoadPavement = Color(0xFF131A29)      // Midnight asphalt
    val exitProgressFill   = Color(0xFF0284C7)      // Gradient progress bar
    val sosAlcoveRed       = Color(0xFFEF4444)      // Emergency SOS badge
}
```

---

## 5. Curated Websites for UI/UX References & Design Inspiration

To see, explore, and download industry-standard UI design references for navigation, 3D maps, automotive HMI, and tunnel visual transitions, use these curated platforms:

### 1. Mobbin (The Gold Standard for Real Mobile App Flows)
* **Website:** [mobbin.com](https://mobbin.com)
* **Why it's the best:** Mobbin archives thousands of real, production iOS and Android screen recordings and screenshots from top global apps.
* **Exact Apps to Inspect:**
  * **Google Maps** (Search `Google Maps` $\to$ Filter by `Navigation`, `Turn-by-Turn`, `Dark Mode`).
  * **Waze** (Inspect their tunnel beacon flow and hazard reporting cards).
  * **Apple Maps** (Look at their iOS 17/18 3D driving navigation view with elevated overpasses and detailed lane guidance).
  * **Uber Driver App** (Outstanding glanceable navigation HUD designed for in-car dashboard mounts).

### 2. Mapbox Navigation & Vision SDK Showcase
* **Website:** [mapbox.com/navigation](https://www.mapbox.com/navigation) and [docs.mapbox.com/android/navigation](https://docs.mapbox.com/android/navigation/guides/)
* **Why it's essential:** Mapbox is the underlying engine for Porsche, BMW, Toyota, and modern EV navigation. Their documentation and design guides showcase:
  * 3D camera tilt and Course-Up bearing manipulation.
  * Custom 3D building and tunnel extrusion meshes.
  * Night-vision navigation color schemes and turn-by-turn guidance banner components.
* **Reviewed 13 Sep 2026 — see [§7](#7-review-inputs--building-this-plan-on-the-mapbox-navigation-sdk-for-android).** The polished screenshot on that landing page is the *UX Framework* (beta), not the GA core SDK; the guides cover camera, puck, route line, maneuver, trip progress, speed limit, voice, offline `TileStore` and replay — but not tunnel extrusion meshes, and Hindi is not a supported instruction language.

### 3. Mappls (MapmyIndia) Official Portal & App Gallery
* **Website:** [mappls.com](https://www.mappls.com) and the **Mappls App on Google Play Store**
* **Why it's essential:** Mappls is the definitive benchmark for Indian driving conditions:
  * **3D Junction Views:** Realistic 3D photorealistic renderings of complex Indian flyovers and underpasses showing exactly which lane to take.
  * **Safety Alerts:** Speed breaker icons, pothole warnings, sharp curve alerts, and toll booth lane advice.
  * **Portal Warnings:** How they present tunnel entries and hill-station ghat navigation.

### 4. Dribbble & Behance (Automotive HMI & Concept UI)
* **Websites:** [dribbble.com](https://dribbble.com) and [behance.net](https://www.behance.net)
* **Target Search Queries:**
  * `"Automotive Navigation HMI"`
  * `"Tunnel Navigation UI"`
  * `"CarPlay Navigation Concept"`
  * `"Android Auto 3D Navigation"`
  * `"Instrument Cluster Head-Up Display (HUD)"`
* **What to look for:** Highly polished concepts of 3D wireframe tunnel tubes, futuristic digital speedometer dials, and night-vision dark modes.

### 5. Google Material Design 3 for Cars / Android Auto
* **Website:** [developers.google.com/cars/design](https://developers.google.com/cars/design)
* **Why it's essential:** Official safety standards for driver interfaces:
  * Glanceability rules (Drivers should understand navigation cues within a 2-second glance).
  * Minimum touch target dimensions ($48\times 48\text{ dp}$ minimum, $64\text{ dp}$ recommended for vehicles).
  * Contrast ratio requirements ($> 7:1$ for navigation text against dark map tiles).

---

## 6. Implementation Checklist for Frontend Engineers (Jetpack Compose)

When ready to implement, the UI components map to the following Jetpack Compose composables:

1. `TunnelNavigationHeader.kt`: Dual-tiered card with primary turn maneuver icon + animated horizontal exit progress bar.
2. `TunnelTube3DRenderer.kt`: Custom MapLibre OpenGL / Compose Canvas layer rendering the 3D illuminated tunnel tube, lateral walls, and scrolling ceiling lights.
3. `HazardAlertBanner.kt`: Animated banner for Mappls-style Indian alerts (Headlights on, speed breaker ahead, no overtaking).
4. `UncertaintyHaloPuck.kt`: Directional chevron puck surrounded by an InEKF covariance ellipse that locks during ZUPT stationary stops.
5. `TelemetryDrawer.kt`: Bottom sheet displaying speed HUD, distance to exit, elapsed time, live drift %, and IMU sample rate.
6. `ReconvergenceToast.kt`: Exit confirmation dialog summarizing tunnel drift and re-lock accuracy.

---

## 7. Review Inputs — Building This Plan on the Mapbox Navigation SDK for Android

*Added 13 Sep 2026 after reading this plan, [TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md](TUNNEL_MODE_AND_NAVIGATION_UPGRADES.md), the current `android-ui/` code, and the Mapbox guides at [docs.mapbox.com/android/navigation/guides](https://docs.mapbox.com/android/navigation/guides/). Versions read: core Navigation SDK **v3.30.1**, UX Framework **v1.30.0**, Maps SDK **v11.30.1**. Every class and option named below was checked against the 3.30.1 API reference unless it carries a "(verify)" tag. The decision to use the Mapbox UI is taken as given; these inputs are about doing it without breaking the project's honesty rules (D-079, D-080, D-081, D-112) or the offline guarantee (D-041, D-117), and about what the SDK already gives us that the two plans propose to build.*

### 7.0 Summary — the eight inputs that change the plan

| # | Input | What changes |
|---|---|---|
| 1 | **"The Mapbox UI" is two products.** The polished screenshot on the guides landing page is the **UX Framework ("Dash", `com.mapbox.navigationux:android`) — Public Preview / beta, evaluation terms, snapshot Maven repo.** The GA product is the **core SDK v3 + `ui-components`**, which are View widgets you assemble yourself. v2's Drop-In UI (`ui-dropin`) is *removed* in v3. | Pick one explicitly (§7.1). Recommendation: **core SDK v3**, with a time-boxed Dash spike only if the team wants search → route preview → arrival for free. |
| 2 | **Mapbox has its own dead reckoning.** The SDK "extrapolates a driver's current location, even when GPS signals are unavailable, using dead reckoning algorithms", and `NavigationOptions.enableSensors(true)` adds IMU-aided prediction "for example in tunnel" — with the warning that the SDK **ignores location updates which don't match data from sensors**. | Our InEKF must be the *only* estimator that moves the puck, and the screen must make that provable (§7.2). This is the single most important input here. |
| 3 | **The plan's "DRIFT ±2.8 m (0.4 %)" / "Filter Drift 3.8 m (0.29 %) • Grade: A" cards break D-112.** A phone has no ground truth; drift is the graded metric and cannot be produced on-device. | Relabel to *est. σ* and *exit residual vs GNSS*; delete "Grade" (§7.3). |
| 4 | **Mapbox is online-first.** Tiles, Directions API, Voice API, road-object data all come over the network; the on-device router only works over a pre-downloaded `TileStore` region. | Pre-download a Delhi-NCR tile region and rehearse in airplane mode; `android/` (the logger) stays network-free (§7.4). Needs a D-row amending D-111 for `android-ui/`. |
| 5 | **Most of the tunnel plumbing the tunnel doc proposes to build already exists in the SDK**: `RouteProgress.inTunnel`, `LocationMatcherResult.inTunnel`, `RouteProgress.upcomingRoadObjects` → `Tunnel(info, length)` with `distanceToStart`, matcher `zLevel`, Electronic Horizon `TUNNEL` enter/exit callbacks. | Portal geofencing, tunnel name/length banner and the flyover/underpass level come from the SDK; keep our own portal list only as a coverage fallback (§7.5). |
| 6 | **Hindi is not a supported instruction language** (English-India is). | Hindi voice is ours, via Android TTS `hi-IN`, for IDR/tunnel events only (§7.8). Do not promise bilingual turn-by-turn. |
| 7 | **Speed-based auto-zoom and the 0.035 m/m halo are not how the SDK or the filter behave.** `MapboxNavigationViewportDataSource` zooms on route geometry ahead, not speed; the halo figure is the demo estimator's hand-tuned growth, and the InEKF's uncertainty is an *ellipse* (lateral-dominant, yaw-driven), not a circle. | Stage 1 and Stage 3 wording (§7.6, §7.2 rule R4). |
| 8 | **Replay through the same UI is the venue safety net.** `MapboxNavigation.startReplayTripSession()` + `MapboxReplayer` play a recorded drive through the identical screen, with `isMock=true` keeping it honest. | Build the replay path first; the live drive is the second milestone (§7.9). |

### 7.1 Two products — which one to build on

```
                      core Navigation SDK v3 (GA)                 UX Framework "Dash" v1.30 (beta)
                      ─────────────────────────────               ─────────────────────────────────
 artifact             com.mapbox.navigationcore:android:3.30.1    com.mapbox.navigationux:android:1.30.0
                      + :ui-components (View widgets)             (+ :cluster for instrument cluster)
 map                  com.mapbox.extension:maps-compose:11.30.1   built in, Compose inside
 host                 any Composable / Activity                   DashNavigationFragment + Application.onCreate init
 what you get         camera, puck, route line/arrow, maneuver,   the whole app: search, trip planning, active
                      trip progress, speed limit, status,         guidance, arrival, EV, MapGPT, settings screen
                      voice, replay, EHorizon, TileStore
 our location source  NavigationOptions.locationOptions(          customLocationProviderFactoryConfig(
                        LocationOptions.locationProviderFactory)    LocationProviderFactory, LocationProviderType)
 custom UI            we own the whole screen                     Compose slots: setManeuver, setTripSummary,
                                                                  setMapLayer { top/middle/bottomSlot }
 theme switching      load NAVIGATION_NIGHT_STYLE or Standard     ui { uiModeSettings / uiModeMapper } (suspend
                      lightPreset=NIGHT, whenever we want         mapper — re-evaluation trigger: verify)
 camera per state     NavigationCamera + ViewportDataSource,      camera { activeGuidanceDefaults =
                      every option live                             SimpleDefaults(zoom, pitch); lookAheadMeters }
 terms / repo         standard ToS, releases Maven                nav-sdk-eval-terms, releases + snapshots Maven
```

**Recommendation: core SDK v3.** Reasons, in order:

1. Everything in Stages 2–5 of this plan is bespoke chrome (hazard banner, tunnel progress bar, covariance halo, reconvergence toast) plus FSM-driven camera and theme changes. The core SDK exposes each of those as a live option; Dash exposes them as init-time config plus `Dash.applyUpdate {}`.
2. Dash's value — search, route preview, arrival, EV, MapGPT — is outside PS 26168. Its cost — beta API churn, evaluation terms, a snapshot Maven repo, an `Application` subclass and Fragment host — is exactly the class of dependency D-111 warns about: works in rehearsal, breaks at the venue.
3. The existing `NavigationScreen.kt` already is the assembled screen; swapping `MapView.kt`'s OSMDroid `AndroidView` for a `MapboxMap` composable plus `NavigationCamera` is a smaller change than re-hosting the app inside `DashNavigationFragment`.

If the team wants the "complete product" look for the finale, time-box a **two-day Dash spike** against the checklist in §7.6 and log the outcome as a decision row. Do not run both.

### 7.2 The puck-ownership problem (read this one)

Quoted from the SDK docs, because the wording matters:

> "The Navigation SDK comes with a precise Location Provider that continually filters and processes GPS signals and extrapolates a driver's current location, even when GPS signals are unavailable, using dead reckoning algorithms" — *guides overview*
>
> `enableSensors(value)` — "Enables analyzing data from sensors for better location prediction in case of a weak GPS signal, for example in tunnel. Usage of sensors can increase battery consumption. Warning: don't enable sensors if you emulate location updates. **The SDK ignores location updates which don't match data from sensors.**" — *`NavigationOptions.Builder`*

So there are two dead-reckoning estimators in the pipeline the moment Mapbox is on screen. If we do nothing, a tunnel demo shows **Mapbox's** extrapolation, not ours; a judge who knows the SDK will ask, and we would have no answer. If we enable their sensors on top of our feed, they will silently drop our updates. Rules:

| Rule | What | Why |
|---|---|---|
| **R1** | Feed the InEKF pose through a custom `DeviceLocationProvider` (`LocationOptions.Builder().locationProviderFactory(DeviceLocationProviderFactory { … }, LocationProviderType.REAL)`) at a **steady cadence, including inside the tunnel** — 10 Hz is the filter's output rate; the SDK's default request is 1 Hz, so measure CPU at 10 Hz and fall back to 5 Hz if needed. | Mapbox's extrapolator only runs where there is a gap. Never give it one. Set `navigatorPredictionMillis` to match that cadence rather than leaving the default (its value: verify). |
| **R2** | `enableSensors(false)` — explicitly, in `NavigationOptions`, with a comment naming this section. | Otherwise our feed is cross-checked against the phone IMU by *their* filter and dropped when the two disagree. |
| **R3** | Fill every field of the `com.mapbox.common.location.Location` we emit: `horizontalAccuracy` = InEKF 1σ (metres), `bearing` = filter yaw, `speed` = filter forward speed, `altitude` from the barometer channel, `timestamp` from the session clock. Use `toCommonLocation()` / `toAndroidLocation()` for conversion. | Their map matcher weights updates by reported accuracy. An honest σ is also the only way `zLevel` and off-route detection behave sanely at a tunnel exit. |
| **R4** | Draw a **second, IDR-owned layer** — a `GeoJsonSource` with a `FillLayer` (covariance ellipse from the 2×2 position block of P) and a `SymbolLayer`/`CircleLayer` (raw InEKF pose) — separate from Mapbox's location component. Mapbox's puck shows *where the SDK snaps us*; ours shows *what the filter says*. Label both. | The plan's "InEKF uncertainty halo" cannot be Mapbox's accuracy ring: that ring is a circle from `horizontalAccuracy`, 2-D puck only. The filter's uncertainty is an ellipse whose long axis is lateral (AGENTS.md: lateral error ≈ ½·b_g·v·t²). Two pucks is also the only visual that proves which estimator is driving. |
| **R5** | Log `onNewRawLocation` (ours) and `onNewLocationMatcherResult` (theirs: `enhancedLocation`, `isTeleport`, `inTunnel`, `zLevel`, `roadEdgeMatchProbability`, `isDegradedMapMatching`) to a sidecar with timestamps. | A demo that cannot be audited afterwards is the failure D-080 exists to prevent. |
| **R6** | Test `DeviceProfile(deviceType = AUTOMOBILE)` against `HANDHELD`. | `HANDHELD` is "any typical Android smart phone with GPS" and is tuned for noisy raw GNSS; `AUTOMOBILE` is for "data directly from the vehicle". A filtered pose is closer to the second. Which one second-guesses our feed less is an experiment, not a guess. |
| **R7** | Pause off-route/reroute while the FSM is in `TUNNEL_ACTIVE_IDR` or `EXIT_VERIFICATION` (`MapboxNavigation#setRerouteEnabled(false)` — verify the exact call in 3.30.1; `RerouteOptions` is the config surface). | A lateral DR excursion at a portal would otherwise trigger a Directions request the tunnel has no network for, and a "Rerouting…" banner on top of our "Verifying GPS fix…" one. |

Data path this produces:

```
 IMU/GNSS/baro ──► InEKF (core/ffi) ──► DeadReckoningBackend ──┬──► custom DeviceLocationProvider ──► MapboxNavigation
                                     (TelemetryState + P block) │        (REAL, 10 Hz, σ as accuracy)        │
                                                                │                                             ├─► LocationMatcherResult
                                                                │                                             │   (snapped puck, inTunnel,
                                                                │                                             │    zLevel, isTeleport)
                                                                │                                             └─► RouteProgress
                                                                │                                                 (maneuvers, tunnel objects)
                                                                └──► IDR layer: pose + covariance ellipse (ours, drawn by us)
```

**Contract change this needs** (HANDOVER §4 item 12 / `DeadReckoningBackend`): `TelemetryState.uncertaintyM` (a scalar) has to become the 2×2 position covariance (`covNN, covNE, covEE`) plus WGS-84 `lat/lon` from the filter's global frame — the `latPerMetre` flat-earth conversion in `MapView.kt` is fine for a demo but should not be what feeds a map matcher.

### 7.3 Honesty constraints this plan currently breaks

| Where in this plan | Problem | Fix |
|---|---|---|
| §2 Stage 3 HUD "DRIFT EST: ±3.1 m (0.4 %)", §3 bottom sheet "DRIFT ACCURACY ±2.8 m (0.4 %)", tunnel doc §3.1 "DRIFT: ±2.8 m (0.4 %)" | **D-112**: drift is error against truth as a % of distance — the graded metric. A phone has no truth. D-112 already renamed this card to `m est. σ` once. | Card reads **`est. σ`** (from P). Never "drift", never a percentage. |
| §2 Stage 5 toast "Filter Drift: 3.8 m (0.29 %) • Grade: A", tunnel doc §3.5 "Drift Percentage" | Same. "Grade: A" is a self-awarded score on an unmeasurable quantity. | Show the one thing that *is* measured at an exit: **exit residual vs GNSS** = ‖p_IDR − p_GNSS,first accepted‖ and, separately, tunnel length from the road object. Caption it as a residual against a GNSS fix, not against truth. Drop "Grade". Also show χ² accepted/rejected counts — those are measured. |
| §3 status bar "200 Hz IMU Badge", §1 pillar 3 "200 Hz SE₂(3) InEKF" | **D-081 / D-112 / D-116**: 200 Hz is the FOG configuration captioned as *not demonstrated*; the team A55 delivers a measured 125.0 Hz. | Badge prints the **measured** rate from `RateStats`, or nothing. |
| §2 Stage 3 "expands smoothly at 0.035 m/m traveled" | That number is `LocalNavigationEstimator`'s hand-tuned `advance * 0.035f + 0.012f * dt`, not covariance propagation. | Halo comes from P once the FFI is behind `DeadReckoningBackend`; until then the caption says "demo estimator", as `NavigationScreen.kt` already does. |
| Whole tunnel HUD | **D-081 caption discipline**: every screen that can be screenshotted says what produced its numbers. | Keep the one-line caption from `NavigationScreen.kt` on the tunnel HUD too ("on-device InEKF · `S-` phone IMU at *N* Hz · not the evaluated harness"). Ugly on a slide is the point. |
| §4 `object IDRTunnelPalette : IDRPalette` | Does not compile as written: `IDRPalette` also requires `statusOk`, `textPrimary`, `textSecondary`, `textDim`, `overlayBg`, `border`, `speedLimitRing`. | Delegate: `object IDRTunnelPalette : IDRPalette by IDRDarkPalette { override val bgPrimary = … }` and add the tunnel-only tokens on a separate holder. |

### 7.4 Offline and the venue

D-111 (10 Sep) removed every network path from `android-ui/` because a demo that works on the rehearsal phone and fails at the venue is worse than a blank map; D-117 (13 Sep) then re-admitted online OSM tiles for the *operator demo UI only*, keeping `android/` (the logger) 100 % offline. Mapbox is a much larger network dependency than OSM tiles, so the D-117 split has to be re-stated as a decision row:

- **`android/` never gets Mapbox or `INTERNET`.** Unchanged. The logger is the evidence path.
- **`android-ui/` gets Mapbox, but the venue build must survive airplane mode.** Concretely:
  1. Pre-download a **`TileStore` region** for Delhi-NCR plus the demo corridor (both a Maps `TilesetDescriptor` and the navigation tiles from `mapboxNavigation.tilesetDescriptorFactory.getLatest()`), set `TileStoreOptions.DISK_QUOTA`, and pass **the same `TileStore` instance** to `MapboxMapsOptions.tileStore` and `RoutingTilesOptions` — the docs require this for the region to serve both. Size reference from the docs: Berlin at 15 km radius is 136 MB maps + 42 MB navigation; budget ~300 MB for NCR.
  2. **Predictive caching is not a substitute** — it caches around a drive that already happened online. Use it in addition, not instead.
  3. **Routing is hybrid and not pluggable**: Directions API when online, on-device router over cached tiles when not; custom routers were removed in v3 (`RouterOrigin.ONLINE` / `OFFLINE` only, `RouterOrigin.Custom` gone). This makes the tunnel doc's Valhalla/GraphHopper embedding moot on this stack, and "bring your own route" is limited — a demo route must be requested once online and then survives offline via the tile region.
  4. **Voice**: the Mapbox Voice API is online; `MapboxVoiceInstructionsPlayer` falls back to Android `TextToSpeech`. Pre-install `en-IN` (and `hi-IN`, §7.8) voices on the demo phone and rehearse muted-network.
  5. **Rehearsal rule**: the finale rehearsal is run with the SIM out and Wi-Fi off, and the tile region's `TileStore#getAllTileRegions` listing is screenshotted into the run log.
- **Tokens**: the secret `Downloads:Read` token lives in the *global* `gradle.properties`, never in the repo; the public token goes into `mapbox_access_token.xml` — which must not be committed either (D-111 removed a `com.google.android.geo.API_KEY` placeholder for the same reason). Inject from `local.properties` into a generated resource.

### 7.5 What the SDK already gives the tunnel FSM

The tunnel doc §1.1.B proposes a portal geofence over OSM `tunnel=yes` tags and §3.1 a tunnel-name banner. On this stack both come out of the route:

| Signal | API | Use in the FSM (tunnel doc §1.2) |
|---|---|---|
| Distance to next tunnel portal along the route | `RouteProgress.upcomingRoadObjects` filtered to `roadObject.objectType == RoadObjectType.TUNNEL`; `UpcomingRoadObject.distanceToStart` (negative once inside, until the end) | **PRE_ARMED_ENTRY**. Note this plan says < 100 m (Stage 2) and the tunnel doc says < 40 m (§1.1.B) — make them two thresholds: 100 m raises the hazard banner, 40 m snapshots the gyro bias. |
| Tunnel name and length | `(roadObject as Tunnel).info: TunnelInfo`, `.length`, `.isUrban` | The "Pragati Maidan Tunnel — Bore 1 · Exit in 620 m" banner and the progress bar's denominator. No own database needed where coverage exists. |
| "We are inside a tunnel" per the map | `RouteProgress.inTunnel`, `LocationMatcherResult.inTunnel` | A **fourth** trigger next to C/N₀, lux and baro. Map-data based, so it fires at the mapped portal regardless of signal — good for entry, useless for exit verification. |
| Which level we are on (flyover / surface / underpass) | `LocationMatcherResult.zLevel` | The tunnel doc §3.2.3 barometric vertical separation now has something to be *compared* against. Log both; disagreement is a finding. |
| Matcher confidence and its own doubt | `roadEdgeMatchProbability`, `roadEdgeId`, `isOffRoad` / `offRoadProbability`, `isDegradedMapMatching` (raised when map data is missing — expect it in uncached areas), `RouteProgress.stale` | Telemetry sheet "Live" row; a `stale` progress while we are feeding at 10 Hz means R1 is broken. |
| "Matcher changed its mind — jump the puck" | `LocationMatcherResult.isTeleport` | **EXIT_VERIFICATION must ignore this flag.** It is Mapbox telling the puck to snap; our anti-jump policy is the opposite. We control the animation through `NavigationLocationProvider.changePosition(location, keyPoints, latLngTransitionOptions, bearingTransitionOptions)`, so keep animating from our pose. |
| Route-snapping lost confidence | `RouteProgressState.UNCERTAIN` (after `TRACKING`) | Expect it at every exit. Map it to the Stage 4 "◎ Verifying GPS fix…" status, not to a reroute (R7). |
| Free-drive (no route) tunnel enter/exit, edge metadata (`tunnel`, `bridge`, `curvature`, `meanElevation`, `speedLimit`, `laneCount`) | Electronic Horizon: `NavigationOptions.eHorizonOptions`, `registerEHorizonObserver` → `onRoadObjectEnter/Exit` for `TUNNEL` | Only if we demo without a set route. It is **beta with pricing that "may change"** per the docs; do not make the demo depend on it. |
| Speed limit inside the bore | `LocationMatcherResult.speedLimitInfo` (needs `DirectionsCriteria.ANNOTATION_MAXSPEED` on the route request) | The Stage 3 "(50)" badge. **Expect `null` on many Indian roads** — the docs say so explicitly; design the empty state and never invent a limit. |
| Indian hazards (rumble strips, speed breakers, toll plazas) | `RoadObjectType.TOLL_COLLECTION`, `RESTRICTED_AREA`, `RAILWAY_CROSSING`, `MERGING_AREA`, `IC`, `JCT`; speed breakers are **not** a type — add them as `CUSTOM` objects via `roadObjectMatcher.matchPointObject(...)` + `roadObjectsStore.addCustomRoadObject(...)` from our own list | Stage 2/3 hazard chips. The Mappls-parity list in the tunnel doc §3.2 becomes a custom-road-object file, matched onto the graph by the SDK. |

Two cautions on this table:

- **Coverage is unverified for India.** Before relying on `TUNNEL` objects, drive (or replay) Pragati Maidan, the Barapullah underpasses and one NH tunnel and record whether the objects appear, with what name and length. Keep our own portal list as the fallback source of `CUSTOM` objects, and log which source fired.
- **The tunnel doc's "sub-500 ms via C/N₀" is not reachable through `GnssStatus.Callback`**, which reports at ~1 Hz on most phones; `GnssMeasurementsEvent` cadence and availability vary by chipset and have not been measured on the A55 (D-116 measured the IMU, not GNSS raw). The sub-second entry comes from `distanceToStart` pre-arming and the lux derivative; C/N₀ confirms. Measure the callback rate the D-116 way before quoting 300 ms anywhere.

### 7.6 Stage-by-stage mapping onto SDK components

| Plan element | Core SDK v3 | Dash equivalent | Notes |
|---|---|---|---|
| Stage 1 course-up follow camera, 20° tilt | `NavigationCamera` + `MapboxNavigationViewportDataSource`: `followingPadding`, `options.followingFrameOptions.defaultPitch = 20.0`, `focalPoint`, `bearingSmoothing`, `pitchNearManeuvers` | `camera { activeGuidanceDefaults = SimpleDefaults(zoom = 17, pitch = 20.0) }` | Initialise the data source with a real location before the first `requestNavigationCameraToFollowing()` — it starts at (0, 0). |
| Stage 1 "auto-zoom by speed (50 km/h → z17, 100 km/h → z15.5)" | **Not what the SDK does.** Following-frame zoom is driven by the route geometry ahead and the next maneuver (`maxZoom` / `minZoom` clamp, `frameGeometryAfterManeuver`, `intersectionDensityCalculation`). | `lookAheadMeters` (default 1000 m) is the zoom driver; set to 1.0 to keep `SimpleDefaults`. | Either accept geometry-driven zoom (recommended — it is what Google Maps actually does at maneuvers) or disable the SDK's zoom updates and drive `maxZoom` from speed yourself. Rewrite the Stage 1 line. |
| Stage 1 green maneuver card with next street | `MapboxManeuverView` + `MapboxManeuverApi(MapboxDistanceFormatter(DistanceFormatterOptions))`, fed from `RouteProgressObserver`; includes primary/secondary/sub instruction, **lane guidance**, upcoming list; road shields via `getRoadShields` (online) | `setManeuver { state, modifier -> … }` with `ManeuverUiState` | Replaces `TunnelNavigationHeader.kt`'s maneuver half; keep our progress-bar half as a Compose strip below it. |
| Stage 1 "● GNSS 3D Fix (14 sats)" pill | Ours (from `GnssStatus`, D-row "GNSS integrity HUD — only from a real feed") | ours | Unchanged. |
| Puck that "never freezes" | `mapView.location` + `NavigationLocationProvider.changePosition(enhancedLocation, keyPoints, latLngTransitionOptions, bearingTransitionOptions)`; `LocationPuck2D(bearingImage=…)` or `LocationPuck3D(modelUri=…)` for the chase view; `puckBearingEnabled = true` | built in | `keyPoints` is the SDK's mechanism for the 60 fps glide between updates. Plus the IDR layer of R4. |
| Stage 2 amber hazard banner | ours (Compose), triggered by `distanceToStart` | ours, above the fragment | `MapboxStatusView` (`StatusFactory.buildStatus(message, duration, icon)`; duration 0 = sticky) is the right widget for the *short* messages ("◐ Pre-arming IDR"); the two-line hazard card stays custom. |
| Stage 3 auto-dark | Load `NavigationStyles.NAVIGATION_NIGHT_STYLE` (classic) or, on the **Standard** style, `setStyleImportConfigProperty("basemap", "lightPreset", "night")` (`LightPresets.DAWN/DAY/DUSK/NIGHT`) | `ui { uiModeSettings = …; uiModeMapper = custom }` — return `UiMode.DARK` while the FSM is in tunnel (when the mapper is re-evaluated: verify) | A style *reload* on the classic styles is visible; the Standard-style light preset is a runtime property and animates. Prefer Standard for the theme flip, unless the caveats below bite. |
| Stage 3 45° chase perspective | `followingFrameOptions.defaultPitch = 45.0`, `maxZoom`, `pitchNearManeuvers.enabled = false` inside the bore, then `evaluate()` | `Dash.applyUpdate { camera { … } }` (which camera fields are live after init: verify) | Change only pitch/zoom on entry; keep `bearingSmoothing` so the camera does not yaw on our heading noise. |
| Stage 3 "3D illuminated tunnel tube" | **Tier it.** v1: route line restyled for the bore (`RouteLineColorResources`, high `line-emissive-strength` under the night preset) + two offset `LineLayer`s as glowing walls + the vanishing route line as the on-map progress. v2: a `FillExtrusionLayer` corridor polygon (semi-transparent, `fill-extrusion-height` ≈ 6 m). v3: a glTF tube via `ModelLayer` (Maps v11) — a rendering project on its own. | `setMapLayer { middleSlot { … } }` with the same layers, Compose-style | The **ceiling-light scroll is a Compose overlay**, not a map layer. Ship v1 with the progress bar first; the classic navigation styles already draw tunnels with a dashed casing, which reads correctly. |
| Stage 3 tunnel progress bar | ours, denominator from `Tunnel.length`, numerator from `-distanceToStart`; on-map: `MapboxRouteLineApiOptions.vanishingRouteLineEnabled(true)` + `OnIndicatorPositionChangedListener` → `updateTraveledRouteLine` | ours | The vanishing line is the SDK's "traveled part" and doubles as the corridor progress. |
| Stage 3 "(50)" speed badge | `MapboxSpeedInfoView` + `MapboxSpeedInfoApi.updatePostedAndCurrentSpeed(speedLimitInfo, distanceFormatterOptions)`; units via `DistanceFormatterOptions.unitType(UnitType.METRIC)` | `speedLimitsOptions { showSpeedLimits; showSpeedWarnings }` | `null` limit → hide the badge (see §7.5). |
| Stage 3 SOS-alcove / hazard chips | `CUSTOM` road objects (§7.5) | same | Distance from `RoadObjectDistanceInfo` for EHorizon objects, `distanceToStart` for route objects. |
| Stage 4 "◎ Verifying GPS fix…" | `MapboxStatusView` sticky status; ignore `isTeleport`; R7 | `MapboxStatusView` is core-only; Dash: ours | Puck smoothing is `latLngTransitionOptions` (a `ValueAnimator` lambda) — the "1.5 s spring" lives there. |
| Stage 5 toast | `MapboxStatusView` for 5 s, text per §7.3 | ours | No "Grade". |
| §3 bottom sheet REMAINING / ELAPSED | `MapboxTripProgressView` + `MapboxTripProgressApi(TripProgressUpdateFormatter)` (ETA, distance remaining, time remaining) | `setTripSummary { modifier, state -> … }` with `TripSummaryModel` (`legDistanceRemaining`, `legTimeRemaining`, `isOffline`, `traveledToRemainingRatio`) | Replaces the first two cards; MODE and est. σ stay ours. `isOffline` is worth surfacing on the sheet — it is a measured fact about the trip. |
| §3 quick actions: compass / recenter | `navigationCamera.requestNavigationCameraToFollowing()` for re-center; `requestNavigationCameraToOverview()` for the route overview; state via `NavigationCameraState` (IDLE, FOLLOWING, OVERVIEW + transitions) | built in | Drop `MapView.kt`'s `followVehicle` hand-rolled logic. |
| Next-maneuver arrow on the map | `MapboxRouteArrowApi.addUpcomingManeuverArrow(routeProgress)` + `MapboxRouteArrowView`; `RouteArrowOptions.withAboveLayerId(RouteLayerConstants.TOP_LEVEL_ROUTE_LINE_LAYER_ID)` | built in | Not in this plan; it is free and it is what the Stage 3 "In 450 m, exit tunnel" banner points at. |
| Junction views / signboards | `MapboxJunctionView` exists but the data is **gated — "require an access token from an account with access to this feature"**; signboards similar | — | The Mappls "3D junction view" parity item is not something we can promise on Mapbox without an account upgrade. Say so in the benchmark table. |

Standard-style caveats that decide classic vs Standard: route line and arrow go into the `MIDDLE` slot with no slot choice yet; the buildings API is not Standard-compatible. For v1 of the tunnel demo the classic `NAVIGATION_DAY/NIGHT` styles are the lower-risk choice; the Standard light preset is the nicer theme flip. Decide once, in the D-row.

### 7.7 Theme tokens → Mapbox surfaces

The §4 palette only reaches Compose chrome. To hold the 7 : 1 contrast target against the **map**, the same tokens have to be applied to:

| Surface | Where the token goes |
|---|---|
| Map canvas (`#0B0F19` obsidian, `#131A29` asphalt) | A Studio-published copy of `navigation-night-v1` with the background and road colours changed, referenced by `mapbox://styles/<account>/<id>` — or the Standard night preset with a custom import config. Whoever builds the style needs the hex list from §4. |
| Route line (`#0284C7 → #38BDF8` corridor) | `RouteLineColorResources.Builder().routeDefaultColor(...).routeLineTraveledColor(...).restrictedRoadColor(...)` in `MapboxRouteLineViewOptions`; `MapboxRouteLineViewDynamicOptionsBuilder` lets the colour flip at runtime on tunnel entry without recreating the view. |
| Maneuver arrow | `RouteArrowOptions` colours. |
| Puck | `LocationPuck2D(bearingImage = …)` drawables per `RouteProgressState` (the docs show exactly this pattern) — our chevron for TRACKING, amber for UNCERTAIN, red for OFF_ROUTE. |
| Maneuver / trip progress / speed / status widgets | XML style attributes on the View widgets (they are not Compose) — e.g. `statusViewProgressBarTint`; Dash: `component-styles` and the colour/font/string asset overrides. |
| `IDRTunnelPalette` | Fix the incomplete object (§7.3) and add `tunnelWallGlow`, `tunnelCeilingLamp`, `exitProgressFill`, `sosAlcoveRed` on a separate `TunnelTokens` holder so `IDRPalette` implementers do not all grow tunnel fields. |

### 7.8 Voice and language

- **Hindi is not in the SDK's supported-language table** for either text or spoken instructions; **English (India)** is (UI ✅ / spoken ✅). Turn-by-turn instructions therefore stay `en-IN` (`RouteOptions.language(Locale("en", "IN").toLanguageTag())` — verify the exact tag the Directions API accepts — with `steps(true)`, `voiceInstructions(true)`, `voiceUnits(DirectionsCriteria.METRIC)`).
- Hindi is ours: the IDR/tunnel announcements this plan lists ("500 meter mein tunnel exit hai …") are generated by *our* FSM and spoken through Android `TextToSpeech` with a `hi-IN` voice — the same fallback engine the SDK itself uses when its Voice API is unreachable. Keep them short and never overlap a Mapbox instruction: use `MapboxAudioGuidance.getRegisteredInstance()` for the SDK side and queue ours behind its `stateFlow()`.
- The §3 "🔊 Voice (Hindi/En)" toggle therefore controls two engines. Say so in the UI copy, and mute both together (`audioGuidance.mute()` persists across sessions via `DataStore`).

### 7.9 Replay is the venue safety net

`mapboxNavigation.startReplayTripSession()` swaps the location provider for `MapboxReplayer` (`ReplayLocationProvider` in v3); `mapboxReplayer.pushEvents(events); play()` replays a recorded drive through the **identical** screen — camera, maneuvers, tunnel objects, our FSM, everything. This is how the tunnel transition is shown on a table at the finale with no GNSS in the room, and it is the first milestone to build, before the live drive:

1. Convert a logger session (`android/` sidecar, or IO-VNBD via the harness) into `ReplayEventUpdateLocation` events carrying the *InEKF output* (not raw GNSS), with `LocationExtraKeys.IS_MOCK = true` — the SDK requires the flag for `MOCKED`/`MIXED` providers, and it is also our honesty marker.
2. Banner per D-081: "REPLAY · session `S-IDR-…` · `S-` stream at *N* Hz", visible in every screenshot.
3. Do **not** `enableSensors` in replay — the docs warn the SDK will reject mocked updates that disagree with the live IMU on the table.
4. `HistoryRecorderOptions` can additionally record the SDK's own view of the trip (`.pbf.gz`) for replay/debug. It is a convenience, not the evidence path; the sidecar stays authoritative.

### 7.10 Build, account and pricing checklist

- **Compatibility**: SDK needs Kotlin ≥ 1.7 (we are on 2.2.10), `minSdk` ≥ 21 (we are on 26), Java 8+ (17), NDK 23 or 27 — use the `-ndk27` artifacts (`com.mapbox.navigationcore:android-ndk27`, `com.mapbox.extension:maps-compose-ndk27`) for 16 KB page support on `targetSdk 35`. AGP 9.4 / Kotlin 2.2 against a 3.30.1 artifact is untested by us — the first task is a hello-world build, not a feature.
- **Repos**: Mapbox Maven at `api.mapbox.com/downloads/v2/releases/maven` with `username = "mapbox"` and the secret token as password, inside `dependencyResolutionManagement` (not `pluginManagement` — the docs flag this mistake). Dash also needs the `snapshots` repo and `packagingOptions` excludes (`META-INF/DEPENDENCIES`, `META-INF/INDEX.LIST`, `dash-sdk.properties`).
- **UI widgets are Views**: `MapboxManeuverView`, `MapboxTripProgressView`, `MapboxSpeedInfoView`, `MapboxStatusView` go into Compose via `AndroidView`, exactly as `MapView.kt` hosts OSMDroid today. The map itself should be the `MapboxMap` composable from `maps-compose`.
- **Lifecycle**: one `MapboxNavigation` per process via `MapboxNavigationApp.setup { NavigationOptions.Builder(context)… }` + `attach(lifecycleOwner)`; keep it alive across screens (destroying it ends the billed trip and restarts the matcher's `INITIALIZED` warm-up).
- **Pricing facts to plan around**: billed per **trip** (Active Guidance ≤ 12 h, Free Drive ≤ 1 h) plus **MAU**; a 30 s grace period per session; **every test device counts as an MAU**; a Maps MAU is billed in addition when a map is shown; API calls made *during* a session are included, calls outside one are not — so start a Free Drive session before requesting routes. There is a free tier; the team account owner should check the current per-item prices on the pricing page before the field campaign, and keep the number of test phones small.
- **Terms**: Dash is under `nav-sdk-eval-terms`; core SDK under the standard ToS. Attribution is required on any Mapbox map shown.

### 7.11 What this changes in the two plans

**Replaced by the SDK** (drop from the roadmaps):

- MapLibre Native migration (this plan §6.2; tunnel doc §3.3 "Vector Map Renderer", Tier 4 blueprint).
- Valhalla / GraphHopper embedded routing (tunnel doc §3.3, Tier 3) — hybrid router + `TileStore`.
- Own portal database and `AutonomousTunnelDetector` geofence (tunnel doc §1.1.B, Phase 1) — `upcomingRoadObjects` / `inTunnel`, with our list demoted to `CUSTOM` fallback objects.
- Own turn-guidance card, lane guidance, ETA/remaining cards (this plan §3, §6.1, §6.5 first two cards) — `MapboxManeuverView`, `MapboxTripProgressView`.
- Own re-center / overview camera logic (`MapView.kt`) — `NavigationCamera`.

**Kept, and now sharper**:

- The FSM (tunnel doc §1.2) with one more entry trigger (`inTunnel`) and two exit-side flags to *override* (`isTeleport`, `UNCERTAIN`).
- The χ² gate and Huber blending (tunnel doc §3.5) — they run in our provider, upstream of Mapbox, which is the only place they can.
- `HazardAlertBanner.kt`, `UncertaintyHaloPuck.kt` (as the IDR map layer of R4, an ellipse), `TelemetryDrawer.kt` (est. σ, mode, measured rate, `isOffline`), `ReconvergenceToast.kt` (exit residual, no grade), the Hindi TTS for IDR events.

**Deferred / stretch**: the glTF 3D tube (`TunnelTube3DRenderer.kt` → v1 glow corridor first), junction views (gated feature), Electronic Horizon in free drive (beta), Android Auto / instrument cluster (Dash has it built in; core SDK has `android-auto-components`) — none of it before the replay milestone works end-to-end in airplane mode.

**Decision-log rows this needs** (candidates, in order):

1. Core SDK v3 vs UX Framework — and the classic-vs-Standard style choice. **→ D-121.**
2. `android-ui/` re-admits `INTERNET` for Mapbox under a `TileStore`-region rehearsal rule; `android/` unchanged (amends D-111, extends D-117). **→ D-122.**
3. Puck ownership: custom `DeviceLocationProvider` fed by the InEKF, `enableSensors(false)`, two labelled pucks, both streams logged (R1–R7). **→ D-123** (R1–R4 in code; R5–R7 deferred to the replay/live milestones).
4. On-device display vocabulary: `est. σ` and `exit residual vs GNSS` only; no "drift", no "grade" on any Android surface (restates D-112 for the new screens). **→ D-124.**
5. Who owns the Mapbox account and tokens, and the MAU budget for test devices. **Open** — recorded as such in D-122.
6. `TelemetryState` grows the 2×2 position covariance and filter-frame WGS-84 (HANDOVER item 12 contract). **→ D-125.**

**Status, 13 Sep 2026.** Rows 1–4 and 6 landed with the `mapbox` product flavour of `android-ui/` (`android-ui/README.md`): the §7.10 hello-world — `MapboxMap` under the existing screen, the R4 IDR layer, `enableSensors(false)`, the 10 Hz `InekfLocationProvider` — plus the covariance contract, the tunnel palette fix of §7.3, the guard tests and CI gating. The `osm` flavour builds and passes its unit tests without any Mapbox account; **the `mapbox` flavour has not yet been compiled**, because no downloads token exists on the dev box — the first `assembleMapboxDebug` with a token is the §7.10 verification step, and any API-name slips against 3.30.1 / 11.30.1 will surface there. Next: the replay milestone of §7.9.

**Status, later on 13 Sep 2026.** The tunnel FSM of the tunnel doc §1.2 landed as **D-126** (`backend/tunnel/TunnelFsm.kt`, pure Kotlin, 33 JUnit scenarios): it now drives the estimator's GNSS suppression from C/N₀, used-in-fix, lux, baro and the χ² gate verdicts, with the manual pill demoted to a force override and the Stage 5 toast showing the D-124 vocabulary. The `inTunnel` / portal-distance inputs of §7.5 exist on the machine and await the trip session.
