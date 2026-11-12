"""Scan (J, lowbits) full-8-bit ANGLE batches on the current 1220x75 word table; exact T/Q/cost.

The current table is NOT in the signed gauge (only 79% of words have bit7 == bit6), and the gauge
map w -> ((w+64) % 128) - 64 is not metric-preserving here (tested: error_1 0.02 -> 14.3 Ha), so the
loader must emit all `brot` bits. `tensorqrom8.py` is a copy of the dfthc_refit `tensorqrom.py`
with a `full=True` mode that loads all bits and does not borrow the word's top bit as scratch
(without scratch the peak is `n_sel + J*brot + high-cache + low-cache`).

Costs come from the official `resource_costs`/`heuristic_costs`/`evaluate_words`, with the static
Toffoli-like count passed as `angles_toffoli` (every CCX/CCZ/CSWAP here is unconditional, so static
== executed per shot; cross-checked on the current Maoxin v22 family: static 4097 == verifier
`angles_toffoli_per_pass` 4097).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
WT = ROOT / '.worktree/dfthcsos'
HERE = WT / 'experiments/dfthcsos/20261112_jbatch'
sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
sys.path.insert(0, str(ROOT / 'artifacts/20261112_chem_pipeline/dfthc_refit'))
sys.path.insert(0, str(HERE))

import tensorqrom8 as tq  # noqa: E402
from dfthcsos.verify import evaluate_words, heuristic_costs, load_inputs, resource_costs  # noqa: E402

SUB = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'
OUT = WT / 'artifacts/20261112_jbatch'
CURRENT = 297557548.71265644


def static_toffoli(circuits):
    tot, per, qmax = 0, [], 0
    for c in circuits:
        s = c.operation_statistics()
        per.append(int(s.num_toffoli_like))
        tot += int(s.num_toffoli_like)
        qmax = max(qmax, int(c.num_qubits))
    return tot, per, qmax


def check_words(directory: Path, words: np.ndarray) -> dict:
    """Local structural check (not official verification): recover words at 1 shot per address."""
    from dfthcsos.scoreinfra.circuits import load_circuits, recover_words_from_circuits
    fam = load_circuits(directory)
    got, _, toff = recover_words_from_circuits(
        fam, num_vectors=1220, num_angles=75, shots_per_address=1, seed=0)
    return {'words_equal': bool(np.array_equal(got, words)),
            'toffoli_per_pass': toff / 2,
            'n_circuits': len(fam)}


def main() -> None:
    plan = []
    for a in sys.argv[1:]:
        parts = [int(x) for x in a.split(',')]
        J, lowbits = parts[0], parts[1]
        trials = parts[2] if len(parts) > 2 else 6
        gsize = parts[3] if len(parts) > 3 else 0
        plan.append((J, lowbits, trials, gsize))
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
    for J, lowbits, trials, gsize in plan:
        t0 = time.time()
        tag = f'J{J}_l{lowbits}' + (f'_g{gsize}t{trials}' if gsize else f'_t{trials}')
        try:
            O = J * 8
            sizes = ([gsize] * ((O + gsize - 1) // gsize) if gsize
                     else [6] * (O // 6) + ([O % 6] if O % 6 else []))
            fam = tq.build_family(words, brot=8, j=J, lowbits=lowbits, sizes=sizes,
                                  trials=trials, jobs=10, full=True)
        except Exception as exc:  # noqa: BLE001
            print('FAIL', tag, repr(exc), flush=True)
            rows.append({'tag': tag, 'J': J, 'lowbits': lowbits,
                         'status': f'fail: {exc!r}', 'sec': round(time.time() - t0, 1)})
            continue
        T, per, qmax = static_toffoli(fam)
        res = resource_costs(inp, fam, 8, 2 * T)
        cost = float(metrics['lambda_eff']) * res['toffoli'] * res['qubits']
        d = OUT / tag
        d.mkdir(parents=True, exist_ok=True)
        for k, c in enumerate(fam):
            c.to_file(str(d / f'angle_k_{k}.kmb'), format='kmb')
        np.savez(d / 'submission.npz', **params, tree_edges=tree, angle_words=words)
        row = {
            'tag': tag, 'J': J, 'lowbits': lowbits, 'trials': trials, 'group_size': gsize,
            'status': 'ok', 'K': len(fam),
            'angles_T_pass': T, 'per_circuit': per, 'circuit_qmax': qmax,
            'T_total': res['toffoli'], 'Q_total': res['qubits'],
            'angles_persistent': res['angles_persistent_qubits'],
            'angles_temporary': res['angles_temporary_qubits'],
            'cost': cost, 'ratio_vs_current': cost / CURRENT,
            'within_cap': res['angles_within_cap'], 'sec': round(time.time() - t0, 1),
        }
        print('ROW', json.dumps(row), flush=True)
        rows.append(row)
    (OUT / 'scan_rows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    print('WROTE', OUT / 'scan_rows.jsonl')


if __name__ == '__main__':
    main()
