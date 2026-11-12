"""Scan J/lowbits/sizes on the current 1220x75 table with tensorqrom8 (full 8-bit output).

Same reporting contract as the jbatch scan, but writes into this experiment's artifacts dir.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
WT = ROOT / '.worktree/dfthcsos'
HERE = WT / 'experiments/dfthcsos/20261112_loader_re'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(HERE))

import tensorqrom8 as tq  # noqa: E402
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs, resource_costs  # noqa: E402

SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
OUT = WT / 'artifacts/20261112_loader_re/scan'
CURRENT = 297557548.71265644


def static_toffoli(circuits):
    per, tot, qmax = [], 0, 0
    for c in circuits:
        s = c.operation_statistics()
        per.append(int(s.num_toffoli_like))
        tot += int(s.num_toffoli_like)
        qmax = max(qmax, int(c.num_qubits))
    return tot, per, qmax


def main() -> None:
    plan = []
    for a in sys.argv[1:]:
        p = [int(x) for x in a.split(',')]
        plan.append((p[0], p[1], p[2] if len(p) > 2 else 6, p[3] if len(p) > 3 else 0, p[4] if len(p) > 4 else 0))
    OUT.mkdir(parents=True, exist_ok=True)
    with np.load(SUB, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
        tree = np.asarray(z['tree_edges'], np.int64)
        params = {k: np.asarray(z[k]) for k in ('U', 'W', 'H2_I', 'H1_I', 'Hsym_lower')}
    inp = load_inputs(SUB)
    metrics = evaluate_words(inp, words, tree, 8)
    hc = heuristic_costs(inp.num_orbitals, inp.w.shape[0], inp.w.shape[1], inp.w.shape[2], 8)
    print('metrics', json.dumps({k: float(metrics[k]) for k in ('error_1', 'error_2', 'lambda_eff')}))
    print('heuristic', json.dumps({k: int(v) for k, v in hc.items()}))
    rows = []
    for J, lowbits, trials, gsize, kmax in plan:
        t0 = time.time()
        tag = f'J{J}_l{lowbits}_t{trials}' + (f'_g{gsize}' if gsize else '')
        try:
            O = J * 8
            sizes = ([gsize] * ((O + gsize - 1) // gsize) if gsize
                     else [6] * (O // 6) + ([O % 6] if O % 6 else []))
            fam = tq.build_family(words, brot=8, j=J, lowbits=lowbits, sizes=sizes,
                                  trials=trials, jobs=10, full=True)
        except Exception as exc:  # noqa: BLE001
            print('FAIL', tag, repr(exc), flush=True)
            rows.append({'tag': tag, 'status': f'fail: {exc!r}', 'sec': round(time.time() - t0, 1)})
            continue
        T, per, qmax = static_toffoli(fam)
        res = resource_costs(inp, fam, 8, 2 * T)
        cost = float(metrics['lambda_eff']) * res['toffoli'] * res['qubits']
        d = OUT / tag
        d.mkdir(parents=True, exist_ok=True)
        for k, c in enumerate(fam):
            c.to_file(str(d / f'angle_k_{k}.kmb'), format='kmb')
        np.savez(d / 'submission.npz', **params, tree_edges=tree, angle_words=words)
        row = {'tag': tag, 'J': J, 'lowbits': lowbits, 'trials': trials, 'group_size': gsize,
               'status': 'ok', 'K': len(fam), 'angles_T_pass': T, 'per_circuit': per,
               'circuit_qmax': qmax, 'T_total': res['toffoli'], 'Q_total': res['qubits'],
               'cost': cost, 'ratio_vs_current': cost / CURRENT,
               'within_cap': res['angles_within_cap'], 'sec': round(time.time() - t0, 1)}
        print('ROW', json.dumps(row), flush=True)
        rows.append(row)
    with (OUT / 'scan_rows.jsonl').open('a') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')


if __name__ == '__main__':
    main()
