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

## Fetching it

`eval/fetch.py` downloads every file the manifest names and verifies each one's SHA-256 against
it, deleting any file that does not match rather than keeping it with a warning:

```
.venv/bin/python -m eval.fetch --sync-only    # the 288 synchronised files, 0.86 GB
```

The CSVs are Git-LFS objects. The LFS **batch** endpoint is refused by the agent git proxy
(D-059), which is what made the dataset look unreachable; `media.githubusercontent.com/media/...`
serves the same objects anonymously and is not refused (D-091 note in phases.md section 11).

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
- The stationary segments are free ZUPT/ZARU ground truth and are what `Q_c` is measured from — but
  **there is no >20 min segment.** An earlier version of this line promised one; it did not survive
  being checked against the files (D-045). Sweeping all 168 distinct `S-` files, the longest
  continuous, uniformly-sampled, genuinely-still stretch is **484 s in `S-T2`**, then 426 s in
  `S-T7` (507 / 448 s before D-120 excluded the settle at each end). Nothing else clears 120 s.
  Consequence: τ_max ≈ 48 s, so bias instability is an upper
  bound and rate random walk is *derived* rather than measured
  ([../docs/ERROR_BUDGET.md](../docs/ERROR_BUDGET.md) §9.2).
- **`S-A4.csv` is malformed and must not be loaded** — an extra empty field at column 6 shifts every
  column after it by one. The leakage guard rejects it by accident (a trailing comma leaves an
  `Unnamed: 24`), not by design. TODO(seat D): record it here as excluded.
- **Every `S-` stem ships twice under different checksums**, differing by up to 8.9% in rows. The
  manifest must say which copy is graded — see [../docs/EVALUATION.md](../docs/EVALUATION.md) §1.1.
  Until it does, "reproduce this on another machine" is not a real instruction.
