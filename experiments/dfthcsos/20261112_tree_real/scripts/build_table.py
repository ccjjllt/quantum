"""Build the loader for an existing word table (optionally re-gauged) and price it exactly."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse, json, time
import numpy as np
import common as C
import onebody


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--signed', action='store_true', help='re-express the table in the signed gauge')
    ap.add_argument('--full', action='store_true', help='load all 8 bits (default: 7-bit signed-gauge mode)')
    a = ap.parse_args()

    with np.load(a.npz, allow_pickle=False) as z:
        params = {k: np.array(z[k]) for k in C.KEYS}
        words = np.asarray(z['angle_words'], np.int64)
        edges = np.asarray(z['tree_edges'], np.int64)
    inputs = C.load_inputs_from(params)
    if a.signed:
        words = onebody.signed_gauge(words, edges, 8)
        assert not np.any((((words >> 7) ^ (words >> 6)) & 1)), 'gauge broken'
    m = C.metrics(inputs, words, edges, 8)
    print('metrics', json.dumps({k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}),
          flush=True)
    t0 = time.time()
    fam = C.build_family(words, jobs=a.jobs, full=a.full)
    cost = C.full_cost(inputs, fam, m, 8)
    print('cost', json.dumps({k: cost[k] for k in ('angles_T_pass', 'T_total', 'Q_total', 'lambda_eff', 'cost',
                                                   'angles_qubits', 'circuit_qmax')}), flush=True)
    out = C.HERE / f'work/{a.tag}'
    C.save_candidate(out, params, words, edges, fam)
    C.dump({'tag': a.tag, 'npz': a.npz, 'signed': a.signed, 'full': a.full,
            'build_sec': round(time.time() - t0, 1),
            **{k: float(m[k]) for k in ('error_1', 'error_2', 'Lambda', 'E_gap', 'lambda_eff')}, **cost},
           C.HERE / 'logs/rows.jsonl')


if __name__ == '__main__':
    main()
