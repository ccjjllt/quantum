"""Step 9: initialisation sensitivity -- random start, jittered start, block-optimal start.

All at the same shape, directions and partition (the only free thing is w, W), so this isolates
whether the trained table is a special basin or whether the shape admits something better.
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
    R, B, C = sp.R, sp.B, sp.C
    w0, W0 = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    rows = {}

    def run(tag, w, W, target=19.98, outer=10):
        e0 = sp.error2(w)
        res = sp.refit(w, W, target_mha=target, outer=outer, inner=200, log=lambda *a: None)
        ww, WW, e2, gap, Lam, lam = res
        rows[tag] = dict(e2_init=1e3 * e0, e2=1e3 * e2, Lam=Lam, gap=gap, lam_eff=lam)
        print('  %-22s init %10.2f mHa -> %7.3f mHa  Lambda %7.2f  E_gap %.5f  lambda_eff %8.4f'
              % (tag, 1e3 * e0, 1e3 * e2, Lam, gap, lam), flush=True)
        return ww, WW

    print('objective caches from one Space; target 19.98 mHa (feasible):', flush=True)
    run('trained', w0.copy(), W0.copy())
    rng = np.random.default_rng(11)
    for s in (0, 1):
        w = rng.normal(scale=float(np.std(w0)), size=w0.shape)
        W = sp.init_W(w, None, w0, W0)
        run(f'random{s}', w, W)
    for eps in (0.02, 0.10):
        w = w0 * (1.0 + eps * rng.normal(size=w0.shape))
        run(f'jitter{eps}', w, W0.copy())
    w = sp.block_init(np.arange(R * B), [np.arange(r * B, (r + 1) * B) for r in range(R)])
    run('block-optimal', w, sp.init_W(w, None, w0, W0))
    with open(ART / 'step9.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()
