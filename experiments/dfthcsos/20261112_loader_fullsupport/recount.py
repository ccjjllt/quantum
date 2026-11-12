"""Independent re-count of the Maoxin .kmx files: reproduce the loader_opt counting convention.

T/pass = CCX + CCZ + CSWAP; cache AND = one `R` per init_and (R + CCX) with `HMR` + `CZ` at del_and;
products = CCX - cache.  Also prints Q per circuit and the derived score constants.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

D = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_re/kmx_maoxin')
LAMBDA = 46.9027
HEUR_T = 6662
Q_TOT = 427


def main() -> None:
    tot = Counter()
    for f in sorted(D.glob('*.kmx')):
        ops = Counter()
        nq = 0
        for ln in f.read_text().splitlines():
            p = ln.split()
            if not p or p[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
                continue
            ops[p[0]] += 1
            for tok in p[1:]:
                if tok.startswith('q'):
                    nq = max(nq, int(tok[1:]) + 1)
        k = int(re.search(r'(\d+)', f.stem).group(1))
        t = ops['CCX'] + ops['CCZ'] + ops['CSWAP']
        cache = ops['R']
        tot.update(ops)
        print(f'k={k:2d} Q={nq:3d} T={t:3d} (cache R={cache:2d}, products={t-cache:3d})'
              f' CX={ops["CX"]:6d} HMR={ops["HMR"]:2d} X={ops["X"]:3d}')
    t = tot['CCX'] + tot['CCZ'] + tot['CSWAP']
    print(f'TOTAL T/pass={t} cache={tot["R"]} products={t-tot["R"]} CX={tot["CX"]}'
          f' HMR={tot["HMR"]} X={tot["X"]}')
    print(f'T_total = 2*{t} + {HEUR_T} = {2*t+HEUR_T}')
    print(f'cost = {LAMBDA} * {2*t+HEUR_T} * {Q_TOT} = {LAMBDA*(2*t+HEUR_T)*Q_TOT:,.0f}')
    print(f'lambda_eff check: 297237077.47 / (14840*427) = {297237077.47/(14840*427):.4f}')
    print(f'saving per 1 T/pass = 2*lambda*427 = {2*LAMBDA*427:,.0f}')


if __name__ == '__main__':
    main()
