# data/ — gitignored

**Nothing in this directory is committed except `manifest/` and this file.**

No dataset bytes, no checkpoints, no OSM extracts. `.gitignore` blocks the common cases; it will not
save you from `git add -f`.

Dataset background, schema, splits and traps: [../docs/DATASETS.md](../docs/DATASETS.md).

## What we need locally

| Dataset | Source | Priority |
|---|---|---|
| **IO-VNBD** | `github.com/onyekpeu/IO-VNBD` — use the *Synchronised V and S* folder | **Required.** The mandated screening dataset. |
| comma2k19 | 33 h highway, phone-grade IMU + CAN | Optional; first on the cut list |
| Our Delhi/NCR collection | Seat C, Sprint 2 onward | Required for the domain-shift ablation |

## Manifest

Every file we depend on gets a row in `manifest/`, committed:

- relative path
- source URL and **download date**
- **SHA-256**
- which stream (`S-` / `V-`) and, for our own collections: device, mount, route, weather, driver,
  and the logger commit SHA

The manifest is what makes "reproduce this on another machine" a real instruction rather than a
hope, and it is checked at Gate 0.

## Reminders

- **`S-` smartphone channels only.** The `V-` wheel-speed columns ship in the same download and are
  disallowed by PS 26168. The dataloader allowlist and CI leakage test enforce this — see
  [../eval/README.md](../eval/README.md).
- IO-VNBD has **no prominent SPDX licence file**. Treat as research-use; cite Onyekpe et al. 2021
  before redistributing anything.
- The dedicated **stationary segments (>20 min)** are free ZUPT/ZARU ground truth and a cross-check
  on our own Allan-variance numbers. Use them.
