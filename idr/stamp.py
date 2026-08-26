"""Provenance stamping.

Every figure and table in the submission carries the commit SHA and RNG seed that produced it.
A result whose provenance is unknown is deleted, not debugged -- see CONTRIBUTING.md.

The one question a judge will certainly ask is "where did this number come from?", and the only
answer that survives follow-up is a commit and a seed.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def git_sha(short: bool = True) -> str:
    """Current commit SHA, suffixed '-dirty' if the tree has uncommitted changes.

    Returns 'nogit' when git is unavailable. A '-dirty' stamp is a warning, not a failure: it
    means the artefact cannot be regenerated from any commit, so it must not reach the submission.
    """
    cmd = ["git", "rev-parse", "--short", "HEAD"] if short else ["git", "rev-parse", "HEAD"]
    try:
        sha = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        return f"{sha}-dirty" if dirty else sha
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "nogit"


@dataclass(frozen=True)
class Stamp:
    """Everything needed to regenerate an artefact."""

    commit: str
    seed: int
    timestamp_utc: str
    python: str
    platform: str
    numpy: str

    def caption(self) -> str:
        """One-line stamp for a figure caption or table footer."""
        return f"commit {self.commit} | seed {self.seed} | {self.timestamp_utc}"

    def is_reproducible(self) -> bool:
        """False if this artefact came from a dirty or non-git tree."""
        return self.commit not in ("nogit", "") and not self.commit.endswith("-dirty")

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def make_stamp(seed: int) -> Stamp:
    return Stamp(
        commit=git_sha(),
        seed=seed,
        timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=platform.platform(),
        numpy=np.__version__,
    )


def seed_everything(seed: int) -> Stamp:
    """Seed every RNG we use and return the stamp describing this run.

    Call once at the top of any entry point that produces a number. Torch is seeded only if it is
    already imported -- the harness must not pull in a 2 GB dependency to run a metric.
    """
    np.random.seed(seed)
    import random

    random.seed(seed)

    torch = sys.modules.get("torch")
    if torch is not None:  # pragma: no cover - exercised only in the ml extra
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)

    return make_stamp(seed)


def stamp_figure(fig, stamp: Stamp) -> None:  # pragma: no cover - needs matplotlib
    """Write the provenance line into a matplotlib figure itself.

    In the figure, not the filename: filenames get renamed when someone drops them into a deck,
    and the stamp has to survive that.
    """
    fig.text(
        0.99, 0.01, stamp.caption(), ha="right", va="bottom",
        fontsize=6, alpha=0.6, family="monospace",
    )
