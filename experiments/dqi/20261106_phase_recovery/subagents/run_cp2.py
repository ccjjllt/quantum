"""Run a CP SAT query with a wall-clock limit, printing to stdout unbuffered.

Usage: python run_cp2.py <json> <k> <secs> [--sym]
"""
import json
import signal
import sys

sys.path.insert(0, 'experiments/dqi/20261106_phase_recovery/subagents')
import cp_sat
from pysat.solvers import Solver


def main():
    jp, k, secs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    sym = '--sym' in sys.argv
    exp = json.load(open(jp))
    X, Y, outs, T = cp_sat.build(exp, k)
    J, I, L = len(outs), len(X), len(Y)
    print(f'build J={J} I={I} L={L} terms={len(T)}', flush=True)
    e = cp_sat.Enc()
    A = [[e.var() for _ in range(J)] for _ in range(k)]
    U = [[e.var() for _ in range(I)] for _ in range(k)]
    V = [[e.var() for _ in range(L)] for _ in range(k)]
    for t in range(k):
        e.add(*A[t])
        e.add(*U[t])
        e.add(*V[t])
    Z = {}
    for t in range(k):
        for j in range(J):
            for i in range(I):
                for l in range(L):
                    z = e.var()
                    Z[(t, j, i, l)] = z
                    e.add(-z, A[t][j])
                    e.add(-z, U[t][i])
                    e.add(-z, V[t][l])
                    e.add(-A[t][j], -U[t][i], -V[t][l], z)
    for j in range(J):
        for i in range(I):
            for l in range(L):
                rhs = T.get((j, i, l), 0)
                prev = Z[(0, j, i, l)]
                for t in range(1, k):
                    nxt = e.var()
                    e.xor3(prev, Z[(t, j, i, l)], nxt)
                    prev = nxt
                e.eq_const(prev, rhs)
    if sym:
        # generators sorted by integer value of A (non-strict: <=)
        for t in range(k - 1):
            eq = None
            leq = None
            for b1, b2 in zip(A[t], A[t + 1]):
                lt = e.var()
                e.add(-lt, -b1)
                e.add(-lt, b2)
                e.add(b1, -b2, lt)
                if leq is None:
                    leq = lt
                    eq = e.var()
                    e.add(-eq, -b1, b2)
                    e.add(-eq, b1, -b2)
                    e.add(b1, b2, eq)
                    e.add(-b1, -b2, eq)
                    # eq <-> (b1 == b2)
                    e.add(-eq, b1, b2)
                    e.add(-eq, -b1, -b2)
                else:
                    nleq = e.var()
                    e.add(-leq, nleq)
                    e.add(-lt, nleq)
                    e.add(leq, lt, -nleq)
                    neq = e.var()
                    e.add(-eq, neq)
                    e.add(-lt, neq)
                    e.add(eq, lt, -neq)
                    # neq <-> eq & ~lt
                    e.add(-neq, eq)
                    e.add(-neq, -lt)
                    e.add(-eq, lt, neq)
                    leq, eq = nleq, neq
            e.add(leq)
    print(f'vars={e.n} clauses={len(e.clauses)}', flush=True)

    class TO(Exception):
        pass

    def handler(sig, frm):
        raise TO

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(secs)
    s = Solver(name='cadical153', bootstrap_with=e.clauses)
    try:
        ok = s.solve()
    except TO:
        print('TIMEOUT', flush=True)
        return
    finally:
        signal.alarm(0)
    print('result', ok, flush=True)
    if ok:
        m = set(x for x in s.get_model() if x > 0)
        sol = []
        for t in range(k):
            av = sum(1 << j for j in range(J) if A[t][j] in m)
            uv = sum(1 << i for i in range(I) if U[t][i] in m)
            vv = sum(1 << l for l in range(L) if V[t][l] in m)
            sol.append({'a': av, 'u': uv, 'v': vv})
        out = jp.replace('.json', f'_cp{k}.json')
        json.dump({'k': k, 'X': X, 'Y': Y, 'outs': outs, 'sol': sol},
                  open(out, 'w'), indent=1)
        print(json.dumps(sol), flush=True)
        print('wrote', out, flush=True)


if __name__ == '__main__':
    main()
