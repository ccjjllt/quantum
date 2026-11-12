"""Step 1: reproduce the current table's numbers, cache the reduction, measure the lambda/error slope."""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_lib as g  # noqa: E402

ART = g.ART


def main() -> None:
    data = g.load_current()
    inp = g.load_inputs(g.SUB)
    m0 = g.rw.official(data, 8)
    print('current official 8-bit:', json.dumps({k: round(v, 6) for k, v in m0.items()}), flush=True)
    hc = g.heuristic_costs(76, *inp.w.shape, 8)
    print('heuristic costs', json.dumps({k: int(v) for k, v in hc.items()}), flush=True)

    t0 = time.time()
    sp = g.Space(data['U'], inp)
    print('Space built in %.0f s; span %d, outside %.3f mHa'
          % (time.time() - t0, sp.Cmat.shape[0], 1e3 * np.sqrt(sp.outside2)), flush=True)
    with open(ART / 'space.pkl', 'wb') as f:
        pickle.dump({'G': sp.G, 'Q0': sp.Q0, 'Ts': sp.Ts, 'Cmat': sp.Cmat, 'Q': sp.Q,
                     'outside2': sp.outside2, 'normT2': sp.normT2}, f, protocol=4)
    np.save(ART / 'p.npy', sp.p)

    w0, W0 = data['W'], data['H2_I'] - data['W'].sum(axis=1)
    print('current continuous error_2 %.3f mHa' % (1e3 * sp.error2(w0)), flush=True)
    print('slope probe: refit at several error targets', flush=True)
    out = {}
    for tgt in (19.999, 19.5, 19.0, 18.0):
        t = time.time()
        w, W, e2, gap, Lam, lam = sp.refit(w0, W0, target_mha=tgt, outer=8, inner=150,
                                           log=lambda *a: None)
        out[tgt] = dict(e2=1e3 * e2, gap=gap, Lam=Lam, lam_eff=lam, sec=round(time.time() - t, 1))
        print('  target %.3f -> e2 %.3f mHa  E_gap %.5f  Lambda %.3f  lambda_eff %.4f  (%.0f s)'
              % (tgt, 1e3 * e2, gap, Lam, lam, time.time() - t), flush=True)
    with open(ART / 'step1.json', 'w') as f:
        json.dump({'official': m0, 'heuristic': {k: int(v) for k, v in hc.items()}, 'slope': out}, f, indent=1)


if __name__ == '__main__':
    main()
