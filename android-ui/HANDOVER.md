# Handover — operator UI (`android-ui/`): the traced curve, and what is still wrong with it

**Written:** 14 Sep 2026, at the end of the session that landed D-128.
**Branch:** `claude/speedometer-curve-tunnel-mode-skg6mg` — `af76134`. Not merged to `main`.
**Predecessor:** D-127 (`6c0e827`, same day) — read that first; this session is its follow-up.

This is the operator UI's counterpart to [`android/HANDOVER.md`](../android/HANDOVER.md), which
covers the logger. Where the two disagree about the module's future, §7 and §9 item 6 of that file
win: **whether `android-ui/` exists at all is still an open decision**, and nothing here settles it.

---

## 1. What you are actually picking up

Verifiable, not remembered:

| Claim | How to check |
|---|---|
| 31 shared Kotlin sources under `app/src/main` | `find android-ui/app/src/main -name "*.kt" \| wc -l` |
| 137 JUnit scenarios in the module | `grep -rc '@Test' --include=*.kt android-ui/app/src/test \| awk -F: '{s+=$2} END {print s}'` |
| **CI is green on `af76134`** — assemble + unit tests, both Gradle roots | run [34814081039](https://github.com/sushant-mishra-dtu/SIH-26168/actions/runs/34814081039) |
| A v0.1.3 APK exists as a CI artifact, **not** in the repo | same run, artifact `app-osm-debug`, 15.9 MiB, expires 13 Dec 2026 |
| `releases/app-osm-debug.apk` is still **v0.1.0** | `releases/README.md` table; it predates D-127 *and* D-128. **Superseded later on 14 Sep:** the v0.1.3 CI artifact was copied in from a browser session after the merge to `main` (§5 item 3 done) |
| The text-surface guards were **not run** this session — no `pytest` in the sandbox; D-128's additions were checked against them by reading | `pytest tests/test_android_demo_surface.py` — run it before merging |
| Nothing here has been on a phone since 13 Sep | no `android/measured/` sidecar, no screenshot, after D-127 or D-128 |

**The one thing to carry forward:** two consecutive sessions have now fixed the traced curve from
source reading and a screenshot, and **neither fix has been seen on a device.** D-127 and D-128
are both marked *not verified on a device* in the decision log. The next person's first job is a
drive, not more code.

---

## 2. What the two sessions changed, and why it was four separate bugs

The 14 Sep road test produced one symptom — *the traced curve is wrong* — and it had four causes
in two layers. D-127 took the first two, D-128 the rest.

| # | Defect | Where it was | Row |
|---|---|---|---|
| 1 | Heading was the handset's azimuth, so any mounting angle rotated the whole track | `onOrientation`, `atan2(R[1], R[4])` | D-127 |
| 2 | Standstill was 12 samples ≈ 60 ms, so smooth tarmac zeroed the speed — and the DR branch propagates along the speed | `STATIONARY_FRAME_COUNT` | D-127 |
| 3 | **The gyro's null offset was never estimated** | `CourseTracker.onGyro` integrated the raw projected rate | D-128 |
| 4 | **The anti-lockout rule applied nothing, and the exit teleported** | `LocalNavigationEstimator.onLocation` | D-128 |

### Why #3 is the one that matters in a tunnel

The GNSS course anchor had always hidden the bias — and a tunnel is precisely the removal of that
anchor. Simulated over the failing run's own numbers (20 s, 14 m/s, 280 m on IDR):

| gyro bias | uncompensated | after one traffic-light ZARU |
|---|---|---|
| 0.5 °/s | 10° heading, **24.4 m** lateral | 0.16 m |
| 1.0 °/s | 20° heading, **48.4 m** lateral | 0.33 m |
| 2.0 °/s | 40° heading, **93.9 m** lateral | 0.65 m |

AGENTS.md's first risk row has always named the remedy ("ZARU at every detected stop, bias
snapshot at tunnel entry") and `TunnelState.PRE_ARMED_ENTRY` has claimed the snapshot in its KDoc
since D-126. Neither existed in this module. Learned from GNSS-tracked driving alone, with no stop
at all, two minutes converges to 1.01 ± 0.05 °/s under 3° 1σ bearing noise and 1.01 ± 0.14 °/s
under 8° (20 seeds each).

### Why #4 was two bugs wearing one banner

The screenshot said *"applied by the anti-lockout rule, not a pass"*. It was not applied: the gate
branch computed `FORCED`, incremented the counters, told the FSM, and returned before touching the
pose, under a comment written for the rejected case. So the 20 rejections re-acquired nothing. And
when the machine did leave the suppressing states, the first fix went in at α up to 0.85 in one
step and was written straight into the polyline — the spike with a vertex in open ground.

---

## 3. What the fix does *not* claim

Read this before trusting the curve.

- **The bias is a scalar about the world vertical, not the gyro's 3-axis offset vector.** It is the
  projection of that vector onto gravity. Re-attitude the phone mid-drive and the number is stale
  until the next ZARU re-learns it. The InEKF carries the vector properly; this does not.
- **The bias is frozen for the length of a bore, by design.** `onGnssDenied()` holds the
  observation window shut across an outage, so a long tunnel runs on whatever the last clean
  stretch of driving measured. A bias that *drifts* inside the bore is uncorrected and unmodelled.
  This is the right trade at 20 s and an open question at 5 minutes.
- **The slew is a display rule and nothing else.** It never feeds back into the estimate; the state
  takes the correction whole. It hides a step, it does not reduce the error. `est. σ` carries the
  offset while it runs so the ellipse still covers the estimate, and a correction over
  `MAX_SLEW_M` (75 m) is drawn as the step it is rather than pretended away.
- **Nothing constrains the pose to the bore.** `TunnelGeometry.locate()` already computes
  `lateralM` against the declared centreline and the FSM consumes only the along-track distance.
  A dead-reckoned pose 48 m sideways of a 30 m-wide corridor is still drawn there. See §5 item 2.
- **`headingRad()` still falls back to the phone's azimuth when no GNSS course has ever been
  anchored.** A trip that *starts* inside a tunnel therefore steers off the handset — D-127's bug,
  reachable through a door D-127 left open. Not hit in practice after 6.7 km of driving; still
  wrong. See §5 item 4.

---

## 4. The APK problem — read this before promising anyone a link

This cost the better part of an hour on 14 Sep. The facts, each checked:

- **The repository is private** (`visibility: private`). GitHub answers anonymous requests to a
  private repo with **404**, not 403 — so every "this link is broken" report here is an auth
  problem wearing a not-found costume.
- `releases/README.md`'s **"Direct Mobile Download"** raw link therefore 404s for anyone not
  signed in. That line is wrong as written and is still in the file.
- **A GitHub Release does not fix it.** Release assets on a private repo need auth too, and
  `release.yml` attaches the *committed* `releases/app-osm-debug.apk` — still v0.1.0. Tagging
  `v0.1.3` today would publish the pre-D-127 build under the new version's name.
- **CI artifact bytes cannot be fetched from this sandbox.** GitHub redirects artifact downloads to
  `productionresultssa15.blob.core.windows.net`, which the egress policy refuses (403 on CONNECT).
  So an agent session cannot download the APK to commit it into `releases/`.
- **An Android build cannot be produced in this sandbox either**, for the D-127-era reason:
  AGP and the SDK resolve from `dl.google.com`, also refused.

**So the only working route today** is: signed-in browser → the run page → *Artifacts* →
`app-osm-debug` → unzip → install. And note that CI debug builds are signed with a *per-runner*
debug keystore, so installing the v0.1.3 artifact over the v0.1.2 artifact may fail on a signature
mismatch — uninstall first if it does.

**To make this stop hurting**, someone with a browser needs to do once: download the artifact, copy
the APK to `releases/app-osm-debug.apk`, update the table in `releases/README.md`, commit, then
tag. That is §5 item 3.

---

## 5. What is open, in order

| # | Work | Blocked on | Done when |
|---|---|---|---|
| 1 | **Drive it.** D-127 and D-128 are both unverified on hardware | a car, a mount, the v0.1.3 APK | a tunnel or underpass run where the traced curve follows the road; the diagnostics chip read at the portal and written down |
| 2 | **Constrain the dead-reckoned pose to the tunnel corridor** | item 1 — do not add a second correction before seeing what the first one leaves | lateral error inside a declared bore bounded by the corridor half-width instead of by the gyro; `TunnelGeometry.lateralM` consumed, not just computed |
| 3 | ~~**Refresh `releases/app-osm-debug.apk` and fix the broken raw-download line**~~ — done after the merge, from a signed-in browser session | a browser session (§4) | the table says v0.1.3, the APK in the folder is the v0.1.3 build, and the "Direct Mobile Download" line says what it actually requires |
| 4 | **Close the `!hasCourse` fallback to the handset azimuth** (§3, last bullet) | a decision on what a trip starting inside a tunnel should do | either the heading is held rather than taken from the phone, or the case is documented as out of scope with a test naming it |
| 5 | **The backward smoother** that `android/HANDOVER.md` §9 item 13 asks for | items 1–2 | the drawn path *corrects* the coasted segment retrospectively rather than only bending onto the fix at the exit — D-128 does the forward half of this and not the backward half |
| 6 | **Decide whether this module exists at all** | a decision, not code — `android/HANDOVER.md` §7, §9 item 6 | unchanged by this session and still the largest open question about everything above |

Item 1 gates items 2 and 5. Do not stack another estimator correction on two unverified ones.

---

## 6. Verifying it on a phone — what to read, and what a failure looks like

The diagnostics chip in the bottom sheet's drawer is the instrument, for the reason D-127 added it:
every bug in this list rendered identically to correct behaviour. It now reads four fields —
heading source, mount offset, **`bias ±x.x°/s`**, motion mode.

| At the portal the chip says | What it means | What to do |
|---|---|---|
| `course · bias +0.8°/s · vehicle` | calibrated; the bore should trace straight | this is the pass case — screenshot it |
| `course · bias +0.0°/s · vehicle` | **nothing has calibrated yet** — no standstill and no clean 4 s GNSS window | expect the curve to bend; stop at a light before the portal and watch the value move |
| `phone azimuth · …` | no GNSS course has ever anchored | §3 last bullet; the track is steering off the handset |
| `held · …` | the course is frozen because the phone is being handled | re-seat the mount; it should clear in 0.8 s |

At the exit, the toast is the other instrument: *metres on IDR*, *elapsed*, *exit residual vs
GNSS*, the χ² counts, and whether it was forced. Under D-128 a forced re-acquisition now means the
pose actually moved, so **the exit residual is a residual against a fix that was applied** — if it
reads large *and* the track still snaps visibly, the slew is being out-run by `MAX_SLEW_M` and §5
item 2 is the answer, not a bigger cap.

---

## 7. Where the reasoning lives

- [`docs/DECISION_LOG.md`](../docs/DECISION_LOG.md) **D-128** — this session, with the measurements.
  **D-127** — heading and speed. **D-126** — the FSM. **D-124/D-125** — what a screen may print.
- [`CHANGELOG.md`](../CHANGELOG.md) v0.1.3 — the shorter question: what changed on the phone.
- [`AGENTS.md`](../AGENTS.md) — risk row 1 is why §2 #3 exists at all.
- [`DESK_RUN.md`](DESK_RUN.md) — the desk procedure for the tunnel machine, written before D-128
  and **not yet updated for the bias chip field**.
