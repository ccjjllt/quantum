"""Run the *official* dfthcsos verifier (`verify` / `evaluate_circuits`) with
shots_per_address=1 on a directory of ANGLE_k circuits plus the packaged submission.npz.

Usage: python official_check.py <circuit_dir> [--shots 1] [--seed N]
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
VER = ROOT / 'data/competition/verifiers'
sys.path.insert(0, str(VER))
sys.path.insert(0, str(VER / 'dfthcsos'))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('circuits', type=Path)
    ap.add_argument('--shots', type=int, default=1)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--submission', type=Path,
                    default=ROOT / 'artifacts/20261113_chem_slim/submission.npz')
    args = ap.parse_args()

    from dfthcsos.verify import evaluate_circuits, load_inputs
    from dfthcsos.scoreinfra.circuits import load_circuits
    from dfthcsos.verify import load_tree_edges, rejection_reason

    inputs = load_inputs(args.submission)
    edges = load_tree_edges(None, args.circuits)
    family = load_circuits(args.circuits, format='kmx')
    print(f'{len(family)} circuits from {args.circuits}')
    try:
        r = evaluate_circuits(inputs, family, edges, shots_per_address=args.shots,
                              seed=args.seed)
    except Exception as exc:
        print(f'REJECTED: {type(exc).__name__}: {exc}')
        return
    reason = rejection_reason(r['metrics'], r['resources'])
    print(f'status: {"PASS" if reason is None else "REJECTED: " + reason}')
    print(f'score        = {r["score"]:.2f}')
    print(f'toffoli      = {r["resources"]["toffoli"]}')
    print(f'qubits       = {r["resources"]["qubits"]}')
    print(f'lambda_eff   = {r["metrics"]["lambda_eff"]:.6f}')
    print(f'verified_shots = {r["verified_shots"]}')
    print(f'sha256       = {r["submission_sha256"][:16]}')


if __name__ == '__main__':
    main()
