# Training Environment

**Seat M.** Where `models/` is trained, and what a number produced there is allowed to be used for.

This file exists for the same reason [D-116](DECISION_LOG.md) exists. The team phone spent three
weeks as "assumed 100 Hz" and turned out to be 125.0 Hz the day someone measured it; a training box
gets the same treatment. **Nothing below is claimed as measured until
[`models/rocm_check.py`](../models/rocm_check.py) has run on the host and its JSON is committed.**
Until then the hardware column is a declaration and the setup section is a recipe, not a result.

---

## 1. The host

| | |
|---|---|
| GPU | AMD Radeon **RX 7700 XT**, Navi 32, **`gfx1101`**, 12 GB GDDR6 |
| Host OS | Windows 11 *(the OS the committed device Allan stamp was produced under — `eval/figures/device/.../allan_stamp.json` records `Windows-11-10.0.26200-SP0`)* |
| Training OS | WSL2 (Ubuntu) |
| Stack | ROCm + the PyTorch ROCm wheel |
| Measured | **not yet** — no `rocm_check` output is committed |

**`gfx1101` is not on ROCm's officially supported GPU list.** The supported RDNA3 target is
`gfx1100` (RX 7900 XTX / W7900). The ordinary way a 7700 XT is made to work is to point HSA at the
7900's kernels:

```bash
export HSA_OVERRIDE_GFX_VERSION=11.0.0
```

That is an unsupported configuration. It is used widely and it usually works, but "usually works" is
not a property this repo lets into a number without a test, which is what section 5 is about.

The WSL2 path narrows the supported list further than bare-metal Linux does. Assume nothing here
works until `rocm_check` says it does.

---

## 2. Install

Order matters; the second step is the one people skip and then spend an evening on.

**1. Windows side.** Install the AMD Software: Adrenalin driver that carries the WSL/ROCm
components. AMD ships this as a separate "Radeon Software for WSL" path — follow AMD's current ROCm
WSL install page rather than a blog post, because the supported driver/ROCm pairing changes between
releases.

**2. Do not install `amdgpu-dkms` inside WSL.** The kernel driver lives on the Windows side and is
projected into the distro through `/dev/dxg`. Installing the DKMS kernel module inside WSL is the
most common way to end up with a `rocminfo` that lists no agents.

**3. ROCm userspace, inside WSL.** Install the ROCm runtime packages for the version AMD's WSL page
names. Then, still inside WSL:

```bash
rocminfo | grep -i gfx        # expect an agent line naming gfx1101
rocm-smi                      # expect the card, its VRAM and its temperature
```

If `rocminfo` lists no agent, stop. No amount of PyTorch configuration fixes that.

**4. PyTorch.** The ROCm build is a *different wheel from the same package name* — it will silently
be the CPU build if the index URL is wrong.

```bash
python -m venv .venv && source .venv/bin/activate
pip install --index-url https://download.pytorch.org/whl/rocm6.2 torch
pip install -e ".[ml,dev]"
```

Check the current `rocm<version>` path on pytorch.org before pasting that line; the wheel index is
versioned and the old paths stop being published. `pip install -e ".[ml]"` on its own resolves
`torch>=2.0` from PyPI, which is the **CUDA/CPU** wheel — install torch from the ROCm index *first*,
then the extra, so the requirement is already satisfied.

**5. Persist the override.** Put it in the venv's activate script or `~/.bashrc`, not in your shell
history:

```bash
echo 'export HSA_OVERRIDE_GFX_VERSION=11.0.0' >> ~/.bashrc
```

---

## 3. Verify

```bash
python -m models.rocm_check                                      # prints a report
python -m models.rocm_check --out eval/figures/train_host/rx7700xt.json   # and records it
```

It reports the kernel and whether it is WSL, which ROCm tools are on `PATH` and what `rocminfo`
lists, whether the override is set, the torch build (`torch.version.hip` is non-`None` on a ROCm
wheel and `torch.version.cuda` is `None` — if that is the other way round you installed the CUDA
wheel), the device name, arch and VRAM, sustained fp32 and fp16 matmul throughput, and whether a
seeded run is bit-identical to itself.

Exit status is `0` when a device was found and `1` when it was not, so it works as a precondition
check in front of a long run.

**Commit the JSON.** A report that only ever existed in a terminal is the thing D-116 was written
against.

---

## 4. What actually uses the GPU today: nothing

Measured, not assumed — `grep -rn "\.to(\|\.cuda(\|device=" models/*.py` returns **no matches**
outside `rocm_check.py` itself. `models/train_baseline_rnn.py` (P-06, the Onyekpe INS reproduction)
builds its tensors and its model on the default device and never moves them. So:

> A perfectly working ROCm install changes this repository's runtime by zero seconds until the
> device is wired through `train_baseline_rnn.py` and `speed_head.py`.

That wiring is **not done and is deliberately not done in the commit that adds this file.** P-06 is
already trained and its result is reported under D-098/D-099/D-100; moving its tensors to a GPU
changes the kernels that produce a published number, and that is a decision-log change with a
re-run attached, not a convenience edit. It is named here so the gap is visible rather than
discovered at 2 a.m.

The honest sizing, meanwhile: the speed head's training set is roughly 58 h at 10 Hz, about
2×10⁶ windows, against a small 1D TCN. That is an hours-not-days job on a CPU. **Check whether the
GPU is the bottleneck before paying for the ROCm stack to be load-bearing.**

---

## 5. Determinism, and what a GPU number may be used for

[`idr.stamp.seed_everything`](../idr/stamp.py) calls
`torch.use_deterministic_algorithms(True, warn_only=True)`. **`warn_only=True` means a kernel with
no deterministic implementation warns and runs non-deterministically rather than raising.** That is
the right default for a harness that must not fall over, and the wrong thing to trust silently when
the result is going into a submission.

So `rocm_check` measures it instead of assuming it, and the rule is:

- **D-042 stands unchanged.** No figure enters the deck, the write-up or the demo unless
  `eval/run.py` produced it under the frozen protocol, stamped with commit and seed. Where the
  artefact came off this host, the `rocm_check` JSON is part of its provenance.
- A GPU-trained checkpoint is **not** bit-reproducible against a CPU-trained one, and an unsupported
  `HSA_OVERRIDE` target is not a configuration anyone else can reproduce on request. Treat the GPU
  as a way to get to an answer faster, and the committed checkpoint plus its seed as the artefact —
  not the training run.
- If `seeded run is bit-identical` comes back **NO**, say so in the row that reports any number
  trained here. It does not disqualify the number; concealing it would disqualify the method.

Checkpoints are not committed (CONTRIBUTING.md, "Never commit dataset bytes, model checkpoints, or
OSM extracts"). `.gitignore` covers the common cases and will not save you from `git add -f`.

---

## 6. What is allowed to train right now

**Nothing new.** Under **H-4** no learned component goes in until Gate 1 closes, and
[Gate 1 does not close](IMPLEMENTATION_PLAN.md) — the split the data forces is 6.2× on the S3 pair
against a required 3–5× (D-115). P-08 (the speed + variance head), P-09 (fusing it with its
predicted `R`) and P-10 (adaptive `R_NHC`) have not been started and do not start because a GPU
became available.

What this host *can* do today, without touching H-4:

```bash
python -m models.train_baseline_rnn --audit          # trains nothing, prints the hyperparameter table
python -m models.train_baseline_rnn --data data      # re-trains P-06, the published baseline (CPU)
```

The order is unchanged: close Gate 1 on the physics-only filter — the stop detector on the
bias-corrected gyro, the measured accelerometer turn-on prior, the bias snapshot at outage entry —
*then* P-08. **The GPU is not the bottleneck. The filter is.**

---

## 7. Known failure modes

| Symptom | Cause |
|---|---|
| `rocminfo` lists no agent | `amdgpu-dkms` installed inside WSL, or the Windows driver predates WSL/ROCm support |
| `torch.cuda.is_available()` is `False`, `rocminfo` is fine | CPU or CUDA wheel installed — check `torch.version.hip` is not `None` |
| `torch.version.cuda` is set, `torch.version.hip` is `None` | The PyPI wheel won. Reinstall from the ROCm index URL |
| Memory access fault / `HSA_STATUS_ERROR_MEMORY_APERTURE_VIOLATION` | `HSA_OVERRIDE_GFX_VERSION=11.0.0` not exported in *this* shell |
| Works in one terminal, fails in another | The override is in shell history, not in `~/.bashrc` or the venv activate script |
| OOM at a batch size that fits on a 16 GB card | The 7700 XT has **12 GB**, and WSL also caps the total memory the distro sees (`.wslconfig`) |

Add a row when you hit a new one. The next person to set this up is on the team.
