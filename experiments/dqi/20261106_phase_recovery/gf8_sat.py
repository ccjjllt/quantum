"""CNF/SAT decision for a symmetric rank-k GF(2^8) decomposition (PySAT)."""
import json
import sys
from pathlib import Path

import kickmix as km
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver

N = 8


def main(k_target=18, conflict_budget=20_000_000, solver_name='cadical195'):
    f = km.GF2Field(N)
    pool = {}
    for u in range(1, 1 << N):
        m = 0
        for i in range(N):
            if u >> i & 1:
                for j in range(N):
                    if u >> j & 1:
                        m |= 1 << (i * N + j)
        pool[u] = m
    slices = []
    for k in range(N):
        m = 0
        for i in range(N):
            for j in range(N):
                if (f.mul(1 << i, 1 << j) >> k) & 1:
                    m |= 1 << (i * N + j)
        slices.append(m)
    us = sorted(pool)
    top = 0
    xvar = {}
    for u in us:
        top += 1
        xvar[u] = top
    yvar = {}
    for u in us:
        for k in range(N):
            top += 1
            yvar[u, k] = top
    clauses = []
    for u in us:
        x = xvar[u]
        ys = [yvar[u, k] for k in range(N)]
        clauses.append([-x] + ys)
        for y in ys:
            clauses.append([-y, x])
    for k in range(N):
        for b in range(64):
            lits = [yvar[u, k] for u in us if (pool[u] >> b) & 1]
            if not lits:
                if (slices[k] >> b) & 1:
                    clauses.append([])  # impossible
                continue
            rhs = (slices[k] >> b) & 1
            # z = XOR of lits; chain
            prev = lits[0]
            for lit in lits[1:]:
                top += 1
                z = top
                a, c = prev, lit
                clauses += [[-a, -c, -z], [a, c, -z], [a, -c, z], [-a, c, z]]
                prev = z
            clauses.append([prev] if rhs else [-prev])
    card = CardEnc.equals([xvar[u] for u in us], bound=k_target, top_id=top,
                          encoding=EncType.seqcounter)
    top = max(top, card.nv)
    clauses += card.clauses
    out = {'k_target': k_target, 'vars': top, 'clauses': len(clauses),
           'solver': solver_name, 'conflict_budget': conflict_budget}
    with Solver(name=solver_name, bootstrap_with=clauses) as s:
        s.conf_budget(conflict_budget)
        res = s.solve_limited()
        out['status'] = 'SAT' if res is True else ('UNSAT' if res is False else 'UNKNOWN')
        out['conflicts'] = s.accum_stats().get('conflicts')
        if res is True:
            model = set(s.get_model())
            chosen = []
            for u in us:
                if xvar[u] in model:
                    coeff = [1 if yvar[u, k] in model else 0 for k in range(N)]
                    chosen.append({'u': u, 'coeff': coeff})
            out['chosen'] = chosen
            out['k'] = len(chosen)
            ok = True
            for a in range(1 << N):
                for b in range(1 << N):
                    got = 0
                    for t in chosen:
                        u, c = t['u'], t['coeff']
                        if ((u & a).bit_count() & 1) and ((u & b).bit_count() & 1):
                            got ^= sum((c[k] & 1) << k for k in range(N))
                    if got != f.mul(a, b):
                        ok = False
                        break
                if not ok:
                    break
            out['verified_all_inputs'] = ok
    target = Path(__file__).resolve().parents[3] / f'artifacts/20261106_phase_recovery/gf8_sat_{k_target}.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != 'chosen'}, indent=1))
    if 'chosen' in out:
        print('chosen k', out['k'], 'verified', out['verified_all_inputs'])


if __name__ == '__main__':
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 20_000_000
    main(k, budget)
