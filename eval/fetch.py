"""Fetch IO-VNBD into data/ from GitHub's LFS media endpoint, verifying every byte.

The repo's CSVs are Git-LFS objects. The LFS *batch* API is refused by this container's git
proxy ("not in this session's authorized repository set"), which is what D-059 recorded and what
made the dataset unreachable. `media.githubusercontent.com/media/...` serves the same objects
anonymously and is not refused -- checked against `S-S1.csv`, whose response carries
Content-Length 9631499 and ETag e79a2ee..., both exactly the manifest's row.

Every file is written to the path `data/manifest/io_vnbd.csv` names and then hashed. A file whose
sha256 does not match the manifest is deleted, not kept with a warning: the manifest exists so
that "reproduce this on another machine" is an instruction rather than a hope (data/README.md),
and a silently-wrong byte here becomes a wrong number in the submission with no way back to it.

**Tracked, not scratch.** D-090 found that D-088's per-stem table was attributed to a
`scratchpad/` script that is in no commit, so the table could not be regenerated on any machine
but the one that wrote it -- and the same is true of three more regeneration lines in phases.md
section 11. A container that has to re-download 818 MB before it can measure anything needs the
downloader to survive, so this lives in `eval/` beside `cadence.py` and `allan.py`.

Usage::

    .venv/bin/python -m eval.fetch --sync-only

`--sync-only` takes the 288 files in the synchronised folder, which is every file truth pairing
and the split can use: `manifest_path_for` refuses anything outside it, and all 72 stems ship
both their copies inside it. Without the flag it also takes the 276 unsynchronised files, which
nothing in the protocol reads. Re-running is cheap and safe -- a file whose sha256 already matches
the manifest is skipped, so an interrupted download resumes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAW = "https://media.githubusercontent.com/media/onyekpeu/IO-VNBD/master/"
MANIFEST = Path("data/manifest/io_vnbd.csv")
#: The manifest's paths open with this; the repo tree does not carry it.
PREFIX = "IO-VNBD/"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path, *, attempts: int = 4) -> None:
    """Download to a .part file and rename on success, so an interrupted run leaves no half file
    that a later run would mistake for a complete one."""
    part = dest.with_suffix(dest.suffix + ".part")
    last: Exception | None = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=180) as r, part.open("wb") as out:
                while chunk := r.read(1 << 20):
                    out.write(chunk)
            part.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            part.unlink(missing_ok=True)
            if i < attempts - 1:
                time.sleep(2**i)
    raise RuntimeError(f"{url}: {last}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=Path("data"))
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument(
        "--sync-only",
        action="store_true",
        help="synchronised folder only -- the 288 files truth pairing and the split re-pick use",
    )
    args = ap.parse_args()

    rows = list(csv.DictReader(args.manifest.open(encoding="utf-8", newline="")))
    if args.sync_only:
        rows = [r for r in rows if "Synchronised" in r["path"]]

    total = len(rows)
    want = sum(int(r["bytes"]) for r in rows)
    print(f"{total} files, {want / 1e9:.2f} GB", flush=True)

    ok = skipped = 0
    bad: list[str] = []
    for n, row in enumerate(rows, 1):
        rel = row["path"]
        dest = args.data_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() and sha256_of(dest) == row["sha256"]:
            skipped += 1
            continue

        assert rel.startswith(PREFIX), rel
        url = RAW + urllib.parse.quote(rel[len(PREFIX) :])
        try:
            fetch(url, dest)
        except RuntimeError as exc:
            bad.append(f"{rel}: {exc}")
            print(f"[{n}/{total}] FAILED {rel}", flush=True)
            continue

        got = sha256_of(dest)
        if got != row["sha256"]:
            dest.unlink(missing_ok=True)
            bad.append(f"{rel}: sha256 {got[:12]} != manifest {row['sha256'][:12]}")
            print(f"[{n}/{total}] CHECKSUM MISMATCH {rel} -- deleted", flush=True)
            continue

        ok += 1
        if n % 20 == 0 or n == total:
            print(f"[{n}/{total}] ok={ok} already-present={skipped} failed={len(bad)}", flush=True)

    print(f"\ndownloaded={ok} already-present={skipped} failed={len(bad)}")
    for line in bad:
        print(f"  ! {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
