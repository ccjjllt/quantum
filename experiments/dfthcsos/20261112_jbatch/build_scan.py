"""Scan (J, lowbits) ANGLE batches on the current 1220x75 word table; report exact T/Q/cost.

Uses the official verifiers' `resource_costs`/`heuristic_costs`/`evaluate_words`, with the
static Toffoli-like count of the built circuits as `angles_toffoli` (every CCX/CCZ/CSWAP in a
tensorqrom circuit is unconditional, so static == executed per shot; checked against the
current Maoxin v22 family: static 4097 == verifier angles_toffoli_per_pass 4097).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
WT = ROOT / '.worktree/dfthcsos'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))

import kickmix as km  # noqa: E402
import tensorqrom as tq  # noqa: E402
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs, resource_costs  # noqa: E402

SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
OUT = WT / 'artifacts/20261112_jbatch'


def static_toffoli(circuits):
    tot = 0
    per = []
    qmax = 0
    for c in circuits:
        s = c.operation_statistics()
        per.append(int(s.num_toffoli_like))
        tot += int(s.num_toffoli_like)
        qmax = max(qmax, int(c.num_qubits))
    return tot, per, qmax


def main() -> None:
    plan = [tuple(int(x) for x in a.split(',')) for a in sys.argv[1:]]
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
    for J, lowbits in plan:
        t0 = time.time()
        tag = f'J{J}_l{lowbits}'
        try:
            fam = tq.build_family(words, brot=8, j=J, lowbits=lowbits, trials=6, jobs=10)
        except Exception as exc:  # noqa: BLE001
            print('FAIL', tag, repr(exc), flush=True)
            rows.append({'tag': tag, 'J': J, 'lowbits': lowbits, 'status': f'fail: {exc!r}',
                         'sec': round(time.time() - t0, 1)})
            continue
        T, per, qmax = static_toffoli(fam)
        res = resource_costs(inp, fam, 8, 2 * T)
        cost = float(metrics['lambda_eff']) * res['toffoli'] * res['qubits']
        row = {
            'tag': tag, 'J': J, 'lowbits': lowbits, 'status': 'ok', 'K': len(fam),
            'angles_T_pass': T, 'per_circuit': per, 'circuit_qmax': qmax,
            'T_total': res['toffoli'], 'Q_total': res['qubits'],
            'angles_persistent': res['angles_persistent_qubits'],
            'angles_temporary': res['angles_temporary_qubits'],
            'cost': cost, 'ratio_vs_current': cost / 297557548.71265644,
            'within_cap': res['angles_within_cap'], 'sec': round(time.time() - t0, 1),
        }
        print('ROW', json.dumps(row), flush=True)
        rows.append(row)
        d = OUT / tag
        d.mkdir(parents=True, exist_ok=True)
        for k, c in enumerate(fam):
            c.to_file(str(d / f'angle_k_{k}.kmb'), format='kmb')
        np.savez(d / 'submission.npz', **params, tree_edges=tree, angle_words=words)
    (OUT / 'scan_rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    print('WROTE', OUT / 'scan_rows.jsonl')


if __name__ == '__main__':
    main()
