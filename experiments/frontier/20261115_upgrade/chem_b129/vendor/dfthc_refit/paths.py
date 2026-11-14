"""Data locations, locally (`data/` in the repo) and on Kaggle (`/kaggle/input/...`).

Elsewhere, set `DFTHC_DATA` to the competition data directory (the one holding `verifiers/`) and
`DFTHC_STARTER` to the starter kit's `starter_kit/` directory (needed only for training). Public
seed factorizations are looked up under `$DFTHC_DATA/public/<seed>/` or in `/kaggle/input`.

Importing this puts the verifiers (and on Kaggle the competition's kickmix build) and the
starter kit on `sys.path`.
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np

COMP = 'google-verifiable-quantum-circuit-compilation'
_LOCAL = Path(os.environ.get('DFTHC_DATA', Path(__file__).resolve().parents[2] / 'data'))


def _find_data() -> Path:
    for p in (Path('/kaggle/input/competitions') / COMP, Path('/kaggle/input') / COMP, _LOCAL):
        if (p / 'verifiers').is_dir():
            return p
    raise FileNotFoundError('competition data not found: set DFTHC_DATA to the directory holding verifiers/')


def _find_starter() -> Path | None:
    env = [Path(os.environ['DFTHC_STARTER'])] if os.environ.get('DFTHC_STARTER') else []
    for local in env + [_LOCAL / 'starter-kit' / 'starter_kit']:
        if (local / 'dfthc').is_dir():
            return local
    hits = glob.glob('/kaggle/input/**/dfthc/df_thc_sga.py', recursive=True)
    return Path(hits[0]).parents[1] if hits else None   # training needs it; checks and builds do not


DATA = _find_data()
ON_KAGGLE = str(DATA).startswith('/kaggle')
STARTER = _find_starter()
WORK = Path('/kaggle/working') if ON_KAGGLE else Path(__file__).resolve().parent / 'runs'

for _p in ([DATA / 'kickmix'] if ON_KAGGLE else []) + [DATA / 'verifiers'] + ([STARTER] if STARTER else []):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

DFTHCSOS = DATA / 'verifiers' / 'dfthcsos'
FCIDUMP = DFTHCSOS / 'FeMoCo76o113e.fcidump'
SHIFTS = DFTHCSOS / 'FeMoCo76o113e.fixed_shifts.npz'
BASELINE = DATA / 'sample_submission' / 'dfthcsos' / 'submission.npz'

UPPER_ENERGY = -22140.27335                                  # E_upper of FeMoCo76o113e (Ha)
FLOORS = {'lambda_floor': 49.0, 'sos_gap_floor': 3.914898}   # the verifier's acceptance floors
KEYS = ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower')               # a factorization .npz


def load(path: Path) -> dict[str, np.ndarray]:
    """A factorization .npz as float64 arrays."""
    with np.load(path) as z:
        return {k: np.array(z[k], dtype=np.float64) for k in KEYS}
