"""Product-retention scan for a DQI .kmx circuit (uses public retain.py from invsqrt).

Step 1 (this script): scan the circuit, report duplicate-product statistics and what
retention would buy for 0/1/2 extra host qubits. Writes stats JSON, no rewrite unless
--rewrite is given.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import retain  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('kmx')
    ap.add_argument('--first-new-bit', type=int, required=True)
    args = ap.parse_args()

    t0 = time.time()
    regq = retain.read_registers(args.kmx)
    print(f'read_registers: {len(regq)} quantum registers in {time.time()-t0:.1f}s', flush=True)
    t = time.time()
    occ, idle, n = retain.scan(args.kmx, regq)
    print(f'scan: {n} lines, {len(occ)} distinct products, '
          f'{sum(len(v) for v in occ.values())} occurrences, {time.time()-t:.1f}s', flush=True)
    dup = sum(len(v) - 1 for v in occ.values() if len(v) > 1)
    print(f'repeated products: {sum(1 for v in occ.values() if len(v) > 1)}, duplicate pairs: {dup}', flush=True)
    idle_q = sorted(idle, key=lambda q: -sum(w[1] - w[0] for w in idle[q]))
    print(f'idle qubits: {len(idle)}; top: {idle_q[:6]}', flush=True)

    out = {'lines': n, 'products': len(occ), 'duplicate_pairs': dup,
           'idle_qubits': len(idle), 'regq': len(regq), 'variants': {}}
    for extra in ([], ['q892'], ['q892', 'q893']):
        t = time.time()
        repl, post, stats = retain.plan(occ, idle, args.first_new_bit, n, extra=tuple(extra))
        stats['wall_s'] = round(time.time() - t, 1)
        stats['n_repl_lines'] = len(repl)
        print(f'extra={extra or "none"}: {stats}', flush=True)
        out['variants'][','.join(extra) or 'none'] = stats
    Path(args.kmx + '.retention_stats.json').write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
