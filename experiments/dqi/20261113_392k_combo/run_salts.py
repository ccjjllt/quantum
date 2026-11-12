"""Sweep official DQI verifier over many salts, 102,400 shots each.

Loads the circuit once, then runs the official verifier (unmodified, imported from
data/competition/verifiers/dqi) for each salt. Writes one JSON per salt plus a summary.

Usage: uv run python run_salts.py CIRCUIT.kmb OUTDIR SALT [SALT ...]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import kickmix as km

VERIFIER_DIR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dqi')
sys.path.insert(0, str(VERIFIER_DIR))

import verify_submission_dqi as V  # noqa: E402

SHOTS = 102_400
WORKERS = 4


def main() -> None:
    circuit_path = Path(sys.argv[1])
    outdir = Path(sys.argv[2])
    salts = sys.argv[3:]
    outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    circuit = km.Circuit.from_file(circuit_path)
    print(f'loaded in {time.time() - t0:.1f}s', flush=True)
    spec = V.ProblemSpecDQI.benchmark_instance(num_shots=SHOTS)
    results = []
    for i, salt in enumerate(salts, 1):
        t = time.time()
        label = salt
        kw = {'seed': int(salt.split(':', 1)[1])} if salt.startswith('seed:') else {'salt': salt}
        try:
            summary = V.verify(circuit, spec, max_workers=WORKERS, **kw)
        except Exception as ex:  # verifier raises on FAIL; record and continue
            summary = {'status': 'FAIL', 'error': str(ex), 'salt': salt}
        summary['salt'] = label
        summary['wall_s'] = round(time.time() - t, 1)
        (outdir / f'verify_salt_{salt}.json').write_text(json.dumps(summary, indent=2))
        results.append(summary)
        print(f"[{i}/{len(salts)}] {salt}: status={summary['status']} "
              f"ve={summary.get('value_errors')} pe={summary.get('phase_errors')} "
              f"R={summary.get('repetition_factor')} cost={summary.get('score')} "
              f"({summary['wall_s']}s)", flush=True)
    (outdir / 'salts_summary.json').write_text(json.dumps(results, indent=2))
    print(f'total {time.time() - t0:.1f}s', flush=True)


if __name__ == '__main__':
    main()
