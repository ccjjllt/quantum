"""CP-SAT decision for a symmetric rank-k decomposition of GF(2^12).

Same encoding as gf8_cpsat.py, with N=12 and 144 slice bits.  A symmetric
30-term GF(2^12) would make the k=12 tower 3*30=90 terms.
"""
import json
import sys
from pathlib import Path

import kickmix as km
from ortools.sat.python import cp_model

N = 12


def main(k_target=30, time_limit=14400):
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

    model = cp_model.CpModel()
    x = {u: model.NewBoolVar(f'x{u}') for u in pool}
    y = {(u, k): model.NewBoolVar(f'y{u}_{k}') for u in pool for k in range(N)}
    for u in pool:
        for k in range(N):
            model.AddImplication(y[u, k], x[u])
        model.AddMaxEquality(x[u], [y[u, k] for k in range(N)])
    model.Add(sum(x.values()) == k_target)

    for k in range(N):
        for b in range(N * N):
            lits = [y[u, k] for u in pool if (pool[u] >> b) & 1]
            want = (slices[k] >> b) & 1
            if want:
                model.AddBoolXOr(lits)
            else:
                model.AddBoolXOr(lits + [model.NewConstant(1)])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    out = {'N': N, 'k_target': k_target, 'status': solver.StatusName(status),
           'wall_time': solver.WallTime(), 'conflicts': solver.NumConflicts(),
           'branches': solver.NumBranches()}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = []
        for u in pool:
            if solver.Value(x[u]):
                coeff = [solver.Value(y[u, k]) for k in range(N)]
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
    target = Path(__file__).resolve().parents[3] / f'artifacts/20261106_phase_recovery/gf12_cpsat_{k_target}.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != 'chosen'}, indent=1))
    if 'k' in out:
        print('k', out['k'], 'verified', out['verified_all_inputs'])


if __name__ == '__main__':
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    t = int(sys.argv[2]) if len(sys.argv) > 2 else 14400
    main(k, t)
