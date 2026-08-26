# maps/ — OSM graph & HMM map matcher

**Seat P.**

The outer correction layer. Map matching is what pushes cross-track error under 10% on curvy
tunnels — but it is deliberately **not** in the error budget allocation. It buys margin back; it is
not a term we plan to spend, because it does not exist in a car park.

## What lives here

- OSM `.pbf` extract → filtered drivable `highway=*` → compact **CSR** adjacency + edge geometry.
- Online HMM matcher: emission ∝ Gaussian in distance to candidate road; transition penalises the
  mismatch between straight-line and on-road route distance; Viterbi decode.
- Car-park fallback mode.

## Contract

**Emission σ comes from the filter's own position covariance — not from an assumed GPS noise model.**
This is the adaptation worth writing up: we already compute the uncertainty, so a matcher tuned for
raw-GPS noise is throwing information away. Use the filter's along-track distance for the transition
term as well.

**Sliding-window commitment.** Commit segments older than ~5–10 s; keep recent ones tentative.

**Heading feedback is an outer loop into the filter**, and it is one of the few things that bounds
yaw drift. Coordinate the interface with seat S.

## Library choice — *pending, log it*

| Option | Notes |
|---|---|
| **FMM / fast-map-matching** | C++/Python, precomputed UBODT, very fast. Best if the matcher lives inside the C++/Rust core via FFI. |
| **GraphHopper map-matching** | Java, uses `hmm-lib`, imports OSM directly, Android-friendly. Most practical if the matcher lives app-side. |
| Valhalla Meili | C++, tiled, mobile-oriented. |
| BMW Barefoot | Java, offline + online HMM variants, server-oriented. |

Rust has no dominant mature library — wrapping FMM via FFI or reimplementing Viterbi over the CSR
graph are the realistic paths.

## Known failure modes

- **Flyover vs service road.** Indian OSM tagging is weakest exactly here, and this is the most
  likely map-matching failure in a Delhi demo. Heading consistency and barometer/road-slope help;
  lane-level matching needs a lane graph OSM rarely has, so stay at road level.
- **Parallel roads** — needs the transition model plus INS-heading vs road-bearing consistency.
- **Bad heading snaps confidently onto the wrong road**, converting a metric error into a
  categorically wrong answer. Map matching cannot rescue a trajectory whose yaw is already gone.

## Car-park mode

No road graph exists underground. Switch when GNSS is absent **and** no drivable OSM edge lies
within the position covariance ellipse. Then: tight NHC + barometer floor detection (a level ≈
2.5–3 m ≈ 0.3–0.36 hPa) + ramp detection from sustained pitch + loop geometry from gyro.

This is the hardest case and drift may exceed 10% on a long stay. Say so in the write-up.

## Status

Scaffold only. Sprint 0: pull a Geofabrik Delhi/NCR `.pbf`, measure the filtered extract size,
choose the matcher path, sketch the CSR layout. Extracts are gitignored — regenerate, never commit.
