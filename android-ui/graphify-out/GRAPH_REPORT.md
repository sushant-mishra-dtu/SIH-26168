# Graph Report - android-ui  (2026-09-14)

## Corpus Check
- 49 files · ~40,224 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 476 nodes · 770 edges · 24 communities (22 shown, 2 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bf63bc14`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TunnelFsm
- TelemetryState
- Theme.kt
- ManeuverType
- SensorForegroundService
- MapView
- LocalNavigationEstimator
- NavigationScreen
- Step 4: Mapped Corridor Verification (Simulated Local Street Run)
- TunnelGeometryTest
- CovarianceTest
- TunnelTrigger
- InekfLocationProvider
- SpeedHud
- project
- IDR Navigator — operator UI prototype
- GuidanceBanner
- SwipeDirection
- RouteTrackerTest
- IdrMapboxNavigation
- gradlew

## God Nodes (most connected - your core abstractions)
1. `TunnelFsm` - 57 edges
2. `TunnelFsmTest` - 41 edges
3. `TelemetryState` - 23 edges
4. `SensorForegroundService` - 19 edges
5. `TunnelTrigger` - 19 edges
6. `LocalNavigationEstimator` - 16 edges
7. `NavigationScreen()` - 16 edges
8. `CovarianceTest` - 14 edges
9. `ManeuverType` - 12 edges
10. `InekfLocationProvider` - 11 edges

## Surprising Connections (you probably didn't know these)
- `NavigationScreen()` --calls--> `GeoCoordinate`  [INFERRED]
  app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt → app/src/main/java/com/sih/idr/demo/backend/routing/NavigationRoute.kt
- `NavigationScreen()` --calls--> `SearchItem`  [INFERRED]
  app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt → app/src/main/java/com/sih/idr/demo/backend/routing/SearchPreset.kt
- `NavigationScreen()` --calls--> `GuidanceBanner()`  [INFERRED]
  app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt → app/src/main/java/com/sih/idr/demo/ui/components/GuidanceBanner.kt
- `NavigationScreen()` --calls--> `HazardChips()`  [INFERRED]
  app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt → app/src/main/java/com/sih/idr/demo/ui/components/HazardChips.kt
- `NavigationScreen()` --calls--> `NavigationBottomSheet()`  [INFERRED]
  app/src/main/java/com/sih/idr/demo/ui/screens/NavigationScreen.kt → app/src/main/java/com/sih/idr/demo/ui/components/NavigationBottomSheet.kt

## Import Cycles
- None detected.

## Communities (24 total, 2 thin omitted)

### Community 0 - "TunnelFsm"
Cohesion: 0.08
Nodes (4): TunnelFsm, TunnelFsmConfig, TunnelTransition, TunnelFsmTest

### Community 1 - "TelemetryState"
Cohesion: 0.09
Nodes (16): AndroidSensorBackend, DeadReckoningBackend, StateFlow, StateFlow, NavigationMode, GNSS, INIT, INS (+8 more)

### Community 2 - "Theme.kt"
Cohesion: 0.09
Nodes (32): TunnelOverride, AUTO, FORCE_OFF, FORCE_ON, Color, Modifier, NavigationBottomSheet(), TunnelOptionSegment() (+24 more)

### Community 3 - "ManeuverType"
Cohesion: 0.10
Nodes (18): GeoCoordinate, ManeuverType, ARRIVE, SLIGHT_LEFT, SLIGHT_RIGHT, STRAIGHT, TUNNEL_ENTRY, TUNNEL_EXIT (+10 more)

### Community 4 - "SensorForegroundService"
Cohesion: 0.09
Nodes (19): Bundle, Context, Location, resetOrigin(), SensorForegroundService, setTunnelOverride(), start(), stop() (+11 more)

### Community 5 - "MapView"
Cohesion: 0.08
Nodes (25): androidx, ImageVector, Modifier, MapControlButton(), MapStackHooks, RecenterPill(), ZoomCapsule(), ComponentActivity (+17 more)

### Community 6 - "LocalNavigationEstimator"
Cohesion: 0.12
Nodes (16): Estimate, Location, LocalNavigationEstimator, toRadians(), TrackPoint, TunnelExitSummary, FixVerdict, ACCEPTED (+8 more)

### Community 7 - "NavigationScreen"
Cohesion: 0.08
Nodes (18): Bundle, ComponentActivity, MainActivity, ArrivalCard(), Modifier, DestinationSearchBar(), Modifier, ExitProgressBar() (+10 more)

### Community 8 - "Step 4: Mapped Corridor Verification (Simulated Local Street Run)"
Cohesion: 0.08
Nodes (25): Desk-Run Verification Checklist: Autonomous Tunnel Mode (D-126), Execution Procedure, Execution Procedure, Execution Procedure, Execution Procedure, Observable UI State, Observable UI State, Observable UI State (+17 more)

### Community 9 - "TunnelGeometryTest"
Cohesion: 0.16
Nodes (10): TunnelAssetLoader, computeCentrelineLengthM(), distanceM(), LatLon, portalDistanceM(), TunnelDef, TunnelFix, TunnelGeometry (+2 more)

### Community 10 - "CovarianceTest"
Cohesion: 0.13
Nodes (4): ErrorEllipse, mahalanobisSquared(), sanitise(), CovarianceTest

### Community 11 - "TunnelTrigger"
Cohesion: 0.12
Nodes (17): TunnelTrigger, BARO_PISTON, CHI2_FORCED, CHI2_PASS, CN0_COLLAPSE, CN0_LOST, CN0_RECOVERED, FIX_REAPPEARED (+9 more)

### Community 12 - "InekfLocationProvider"
Cohesion: 0.16
Nodes (9): InekfLocationProvider, Location, toMapboxLocation(), DeviceLocationProvider, GetLocationCallback, Job, LocationObserver, Looper (+1 more)

### Community 13 - "SpeedHud"
Cohesion: 0.22
Nodes (8): isSpeedOverLimit(), Modifier, limitTickAngleDeg(), SpeedGaugeConstants, SpeedHud(), speedMpsToKmh(), speedToGaugeFraction(), SpeedHudTest

### Community 14 - "project"
Cohesion: 0.23
Nodes (6): CorridorGeometry, Modifier, project(), ProjectedPoint, TunnelCorridor(), CorridorGeometryTest

### Community 15 - "IDR Navigator — operator UI prototype"
Cohesion: 0.20
Nodes (9): Building, IDR Navigator — operator UI prototype, Installing without building, Mapbox tokens (D-122), Open work, The rules this module is held to, The tunnel machine (D-126), Two map engines, one screen (D-121) (+1 more)

### Community 16 - "GuidanceBanner"
Cohesion: 0.31
Nodes (4): GuidanceBanner(), headingToDirection(), Modifier, GuidanceBannerTest

### Community 17 - "SwipeDirection"
Cohesion: 0.36
Nodes (7): Dp, Modifier, SwipeDirection, DOWN, UP, swipeToDismiss(), verticalSwipe()

### Community 20 - "gradlew"
Cohesion: 0.83
Nodes (3): gradlew script, die(), warn()

## Knowledge Gaps
- **74 isolated node(s):** `GNSS`, `INS`, `INIT`, `STRAIGHT`, `TURN_RIGHT` (+69 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TelemetryState` connect `TelemetryState` to `Theme.kt`, `MapView`, `NavigationScreen`, `project`, `GuidanceBanner`?**
  _High betweenness centrality (0.267) - this node is a cross-community bridge._
- **Why does `TunnelOverride` connect `Theme.kt` to `TunnelFsm`, `SensorForegroundService`?**
  _High betweenness centrality (0.264) - this node is a cross-community bridge._
- **Why does `NavigationBottomSheet()` connect `Theme.kt` to `TelemetryState`, `NavigationScreen`?**
  _High betweenness centrality (0.252) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `TelemetryState` (e.g. with `.forced_shownWhenTunnelForced()` and `.gnssSuppressed_shownWhenTunnelModeActive()`) actually correct?**
  _`TelemetryState` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `GNSS`, `INS`, `INIT` to the rest of the system?**
  _74 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `TunnelFsm` be split into smaller, more focused modules?**
  _Cohesion score 0.07536231884057971 - nodes in this community are weakly interconnected._
- **Should `TelemetryState` be split into smaller, more focused modules?**
  _Cohesion score 0.08558558558558559 - nodes in this community are weakly interconnected._