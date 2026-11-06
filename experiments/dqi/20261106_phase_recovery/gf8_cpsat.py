"""CP-SAT decision for a symmetric rank-18 decomposition of GF(2^8).

Variables x_u choose pool matrices u u^T; y_{u,k} are their coefficients on the
k-th output slice.  x_u = OR_k y_{u,k}, sum x_u = 18.  For every slice bit the
XOR of y_{u,k} over pool matrices with that bit set equals the slice bit.
This is a complete decision for the symmetric rank (the pool has 255 matrices).
"""
import json
import sys
from pathlib import Path

import kickmix as km
from ortools.sat.python import cp_model

N = 8


def main(k_target=18, time_limit=600):
    f = km.GF2Field(N)
    # pool matrix u u^T as 64-bit integer, bit (i*N+j)
    pool = {}
    for u in range(1, 1 << N):
        m = 0
        for i in range(N):
            if u >> i & 1:
                for j in range(N):
                    if u >> j & 1:
                        m |= 1 << (i * N + j)
        pool[u] = m
    # slices M_k[i,j] = coefficient of x^k in x^i * x^j
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
        for b in range(64):
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
    out = {'k_target': k_target, 'status': solver.StatusName(status),
           'wall_time': solver.WallTime(),
           'conflicts': solver.NumConflicts(), 'branches': solver.NumBranches()}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = []
        for u in pool:
            if solver.Value(x[u]):
                coeff = [solver.Value(y[u, k]) for k in range(N)]
                chosen.append({'u': u, 'coeff': coeff})
        out['chosen'] = chosen
        out['k'] = len(chosen)
        # verify all inputs
        ok = True
        for a in range(1 << N):
            for b in range(1 << N):
                got = 0
                for term in chosen:
                    u, c = term['u'], term['coeff']
                    if ((u & a).bit_count() & 1) and ((u & b).bit_count() & 1):
                        got ^= sum((c[k] & 1) << k for k in range(N))
                if got != f.mul(a, b):
                    ok = False
                    break
            if not ok:
                break
        out['verified_all_inputs'] = ok
    target = Path(__file__).resolve().parents[3] / f'artifacts/20261106_phase_recovery/gf8_cpsat_{k_target}.json'
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in out if k != 'chosen'}, indent=1))
    if 'k' in out:
        print('k', out['k'], 'verified', out['verified_all_inputs'])


if __name__ == '__main__':
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    t = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    main(k, t)
