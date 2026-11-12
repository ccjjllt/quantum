"""Follow-up checks.

1. negative control for the kickmix harness (delete one real CCX -> words must differ)
2. cache monomials that no gate ever reads (deletable)
3. does adding one extra cached monomial to G0 pay for itself (1 T) by freeing >= 2 products?
4. why the duplicate cache monomials are not caught by the live-qubit rule

Usage: python extra_checks.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np
import kickmix as km

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import ALL, KMXDIR, REAL, Basis, g0_basis, replay, VAR  # noqa: E402
from rebuild import build_slim  # noqa: E402

SLIM = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
            '20261112_loader_productset/kmx_slim')
N, NALL = 1220, 2048
SEL = [km.q(i) for i in range(11)]
WORD = [km.q(i) for i in range(11, 51)]
WS = [km.q(i) for i in range(51, 128)]


def run(circ, seed=20261112):
    sim = km.Simulator(batch_size=NALL, debug_print=False, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circ)
    addr = np.arange(NALL, dtype=np.int64)
    sim.write_across_shots(km.array(SEL),
                           ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool))
    sim.do(circ)
    return sim.read_across_shots(km.array(WORD))[:, :N].astype(np.uint8)


def main() -> None:
    # ---- 1. negative control on k=4 ----
    lines = (SLIM / 'angle_k_4.kmx').read_text().splitlines()
    ccx = [i for i, ln in enumerate(lines) if ln.startswith('CCX')]
    ref = run(km.Circuit.from_file(SLIM / 'angle_k_4.kmx', format='kmx'))
    for pick in (len(ccx) // 3, len(ccx) // 2):
        bad = lines[:ccx[pick]] + lines[ccx[pick] + 1:]
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.kmx', delete=False) as fh:
            fh.write(''.join(x + '\n' for x in bad))
            tmp = fh.name
        c = km.Circuit.from_file(tmp, format='kmx')
        print(f'negative control (drop CCX #{pick}): words still equal = '
              f'{np.array_equal(ref, run(c))}')

    # ---- 2. unused cache monomials / 4. duplicate timing ----
    tot_unused = 0
    for k in range(15):
        d = replay(KMXDIR / f'angle_k_{k}.kmx')
        reads = Counter()
        for gd in d['gates']:
            if gd['op'] in ('CX', 'CCX'):
                for c in gd['c']:
                    reads[c] += 1
        cache_q = [q for q, _ in d['cache']]
        unused = [q for q in cache_q if reads[q] == 0]
        tot_unused += len(unused)
        dupq = [q for q, tt in d['cache']
                if sum(1 for _, t2 in d['cache'] if (t2 & REAL) == (tt & REAL)) > 1]
        print(f'k={k:2d}: cache CCX={len(cache_q)} never-read={len(unused)}'
              f' duplicate-function={len(dupq)} {sorted(dupq)[:8]}')
    print(f'total never-read cache monomials: {tot_unused}')

    # ---- 3. add one monomial to G0: does it free >= 2 products? ----
    k = 4
    d = replay(KMXDIR / f'angle_k_{k}.kmx')
    G0 = g0_basis(d['cache'])
    pt = [tt & REAL for _, tt, _ in d['prods']]
    base = sum(1 for v in pt if G0.contains(v))
    masks = []
    for deg in range(1, 5):
        from itertools import combinations
        for S in combinations(range(11), deg):
            m = ALL
            for b in S:
                m &= VAR[b]
            masks.append(m)
    print(f'\nk={k}: products in G0 = {base}; {len(masks)} candidate monomials (deg 1..4)')
    best = []
    for m in masks:
        B = Basis(G0.values())
        B.add(m)
        n = sum(1 for v in pt if B.contains(v))
        best.append((n - base, m))
    best.sort(reverse=True, key=lambda x: x[0])
    print('best single additions (extra products freed):',
          [(f'+{g}', bin(m & REAL).count('1')) for g, m in best[:6]])
    print(f'adding 1 T frees {best[0][0]} products -> net {1 - best[0][0]:+d} T')


if __name__ == '__main__':
    main()
