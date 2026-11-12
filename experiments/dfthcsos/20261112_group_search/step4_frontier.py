"""Step 4: the (Lambda, error) frontier of the current structure -- is the table already optimal?

If at Lambda = 283 the lowest reachable error_2 is ~19.8 mHa, then no re-initialisation or
regrouping can help within this shape and the group-search lane is closed.  If it is much lower
(e.g. 16) the table is a poor local optimum and there is room for a new init / partition.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_lib as g  # noqa: E402

ART = g.ART


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    sp = g.Space(data['U'], inp)
    w0, W0 = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    rows = {}
    print('frontier from the trained w (current partition, current directions):', flush=True)
    for Lam0 in (283.0, 300.0, 340.0, 450.0, 1000.0):
        w, W, e2, gap, Lam = sp.fit_error_at_lambda(w0, W0, Lam0, maxiter=800, log=print)
        rows[f'from_w_{Lam0}'] = dict(e2=1e3 * e2, Lam=Lam, gap=gap)
    # from a scaled-up start: push toward the low-error corner
    w_big = w0 * 3.0
    print('frontier from 3*w (same structure):', flush=True)
    for Lam0 in (283.0, 340.0, 450.0, 1000.0):
        w, W, e2, gap, Lam = sp.fit_error_at_lambda(w_big, W0, Lam0, maxiter=800, log=print)
        rows[f'big_{Lam0}'] = dict(e2=1e3 * e2, Lam=Lam, gap=gap)
    with open(ART / 'step4.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()
