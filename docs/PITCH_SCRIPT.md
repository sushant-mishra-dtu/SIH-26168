# Pitch Script — "Technical Approach" slide, 60 seconds

Two versions of the same narration for the Technical Approach slide (SIH 2026, PS 26168),
timed for a sub-one-minute slot (~150 words at ~155 wpm). The walk order follows the numbered
blocks on the slide: **1 → 2 → 3 → 4 → 5 → Working Today**.

Every number traces to a document in this repo: [ERROR_BUDGET.md](ERROR_BUDGET.md) §2–§3,
[METHOD.md](METHOD.md) §2, [SE23_PROPAGATION.md](SE23_PROPAGATION.md), and D-116/D-119 for the
measured rate. **No performance figure appears here that `eval/run.py` did not produce (D-042)** —
both scripts are restricted to *[analysis]* and *[measured]* quantities.

---

## Script A — English (151 words, ~58 s)

> One pipeline, five layers.
>
> **[1 — Mobile & Core]** Phone sensors only. Kotlin, Compose, coroutines — zero extra hardware.
>
> **[2 — AI]** And we never double-integrate acceleration. Bias grows as half-b-t-squared —
> ten milli-g is a hundred and seventy-six metres in sixty seconds, and our whole tunnel budget
> is a hundred. So RoNIN and AI-IMU regress velocity *directly*, on-device, through ONNX Runtime.
>
> **[3 — Fusion engine]** Everything fuses in an Invariant EKF on SE-two-three. It's group-affine,
> so error propagation is state-independent and the yaw covariance stays honest. NHC kills sideways
> slip; ZUPT and ZARU re-zero gyro bias at every stop — because yaw is the killer: half b-g v t
> squared. A tenth of a degree per second is fifty-two metres *sideways* in one minute.
> Chi-squared gating drops multipath, so entering a tunnel needs no mode switch and no jump.
>
> **[4 — Offline nav]** HMM and Viterbi snap us onto an offline OSM graph. No network.
>
> **[5 — Agentic layer]** Three agents: alignment, blackout detection, arbitration.
>
> **[Working today]** Installable APK, seven hundred twenty-eight tests green, a hundred
> twenty-five hertz measured on a Galaxy A55.

---

## Script B — Hinglish (150 words, ~58 s)

> Ek hi pipeline, paanch layers.
>
> **[1 — Mobile & Core]** Sirf phone ke sensors. Kotlin, Compose, coroutines — zero extra hardware.
>
> **[2 — AI]** Aur hum acceleration ko kabhi double-integrate nahi karte. Bias half b t squared
> se badhta hai — das milli-g matlab saath second mein ek sau chhihattar metre, jabki poore tunnel
> ka budget hai sirf sau metre. Isliye RoNIN aur AI-IMU seedha velocity regress karte hain,
> on-device, ONNX Runtime pe.
>
> **[3 — Fusion engine]** Sab kuch fuse hota hai ek Invariant EKF mein, SE-two-three pe.
> Group-affine hai, isliye error propagation state-independent rehti hai aur yaw covariance honest
> rehta hai. NHC sideways slip khatam karta hai; ZUPT aur ZARU har stop pe gyro bias zero karte
> hain — kyunki asli dushman yaw hai: half b-g v t squared. Zero point one degree per second pe,
> ek minute mein bavan metre — sideways. Chi-squared gating multipath reject karta hai, toh tunnel
> mein na mode switch, na position jump.
>
> **[4 — Offline nav]** HMM aur Viterbi humein offline OSM graph pe snap karte hain. Network ki
> zaroorat nahi.
>
> **[5 — Agentic layer]** Teen agents: alignment, blackout detection, arbitration.
>
> **[Working today]** Installable APK, saat sau atthais tests green, ek sau pachchees hertz —
> Galaxy A55 pe measured.

---

## Delivery notes

- **Say the exponents, don't read the LaTeX.** "half b-g v t squared" lands; "½·b_g·v·t²" does not.
- **176 versus 100 is the whole pitch.** Pause after "a hundred" — that contrast is what makes
  blocks 2 and 3 necessary rather than decorative.
- **Point at block 3 for the longest beat.** It is the only block with a physics argument in it;
  the other four are engineering.
- The χ² gate is the "seamless transition" claim from the problem statement — say *no mode switch*
  explicitly, because that is the wording the evaluators are matching against.
- Running long? Cut block 5 to "three agents keep it honest", then cut block 1. Never cut the
  176 m line or the yaw line.
