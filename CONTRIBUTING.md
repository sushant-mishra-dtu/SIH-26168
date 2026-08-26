# Working Agreements

Six people, twenty-five days, one number that decides everything. These are the rules that keep the
numbers defensible and the seats from colliding.

---

## Seats and ownership

| Tag | Seat | Owns |
|---|---|---|
| **S** | Filter core & edge engine | `core/` |
| **M** | Learning | `models/` |
| **D** | Data & evaluation | `eval/`, `data/manifest/` |
| **P** | Maps & geodata | `maps/` |
| **A** | Android | `android/` |
| **C** | Field data & submission | `docs/METHOD.md`, deck, video |

**Cross-boundary changes need the owning seat's review.** The two interfaces most likely to cause a
collision are `core/ffi/` (S ↔ A) and the metrics signatures in `eval/metrics/` (D ↔ everyone).
Agree those contracts in writing **before** either side writes code against them.

---

## Branches and commits

- Default branch: `main`. It stays green.
- Branch names: `<seat>/<short-topic>` — `s/inekf-propagation`, `d/outage-harness`, `m/speed-head`.
- Commit messages: imperative subject line, and **say why in the body when the why is not obvious**.
- Never commit to `main` directly once CI exists.
- Never commit dataset bytes, model checkpoints, or OSM extracts. `.gitignore` blocks the common
  cases; it will not save you from `git add -f`.

---

## CI gates

These run on every push. They are not advisory.

1. **Leakage test** — fails on any `V-` column, or any name matching
   `wheel|steer|rpm|engine|brake|clutch|gear|pedal|handbrake`, reaching a feature tensor.
2. **Metric unit tests** — CTE, CRSE, drift %, yaw error each checked against a hand-computed case.
3. **Determinism test** — same commit + same seed → identical metrics output.
4. **Build** — `core/` compiles; `models/` imports; `eval/` runs on the smoke fixture.

If a test is failing, fix the test or fix the code. Do not skip it, and do not merge around it.

---

## Reproducibility

These exist because a number nobody can regenerate is a number nobody can defend, and the one
question a judge will certainly ask is "where did this come from?"

1. **Every figure and table carries the commit SHA and RNG seed that produced it.** Put it in the
   figure itself, not in a filename that gets renamed.
2. **One command regenerates every figure in the submission.** If regeneration needs manual steps,
   the figures will silently drift from the numbers in the text.
3. **Fixed seeds, reported.** Where run-to-run variance matters, report across ≥3 seeds.
4. **A result with unknown provenance is deleted, not debugged.**
5. Data lives outside git. `data/manifest/` carries source URL, download date and SHA-256 per file,
   and it is committed.

---

## Decision log discipline

Add a row to [docs/DECISION_LOG.md](docs/DECISION_LOG.md) whenever you make a choice that:

- a reviewer might reasonably have made differently, or
- was forced by something not visible in the code (a paper that omitted a hyperparameter, a device
  that would not sample above 100 Hz, a dataset folder that turned out to be unsynchronised), or
- changes anything in [docs/EVALUATION.md](docs/EVALUATION.md).

**Append only.** To reverse a decision, add a new row that supersedes the old one. Never edit
history — what we believed and when is exactly what the method document needs.

This is not bureaucracy. It is the method write-up, accumulated a line at a time instead of
reconstructed from memory in the final week.

---

## Documentation

- **[docs/EVALUATION.md](docs/EVALUATION.md) is frozen after Gate 0.** Changing it requires a
  decision-log row naming what changed, why, and which results it invalidated.
- **[docs/METHOD.md](docs/METHOD.md) is filled as work lands**, by the seat that did the work.
- **[docs/ERROR_BUDGET.md](docs/ERROR_BUDGET.md) is revised at each gate** with measured numbers
  replacing assumed ones.
- Update the relevant component README when you change an interface.

---

## Review

- Anything touching `eval/` needs seat D's review — it owns every number in the submission.
- Anything touching a public interface in `core/ffi/` needs both S and A.
- Small, frequent PRs. A 2,000-line PR on 18 September will not get a real review.
- Reviewing is not optional politeness. It is the second pair of eyes on numbers that will be
  defended in front of judges.

---

## Escalation

**If a gate is at risk, say so the day you know, not the day it is due.** The sprint plan has a
buffer week and an ordered cut list precisely so that early bad news is cheap. Late bad news is not.

Cut list, in order: UI polish → EqNIO canonicalisation → car-park mode → comma2k19 pretraining.

Never cut: the evaluation harness, the leakage audit, the yaw instrument, the honest-limits section.
