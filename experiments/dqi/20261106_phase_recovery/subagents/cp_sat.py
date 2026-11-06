"""SAT search for a k-term rank-1 (CP) decomposition of a bilinear kernel.

Tensor T[j,i,l] = coefficient of x_i y_l in output j.  Ask whether there are k
triples (a_t in {0,1}^J, u_t in {0,1}^I, v_t in {0,1}^L) with
    T[j,i,l] = XOR_t a_t[j] & u_t[i] & v_t[l].
A SAT witness is a valid GF(2) CP decomposition with k products.

Uses PySAT (run through an ephemeral env):
    uv run --no-project --with python-sat python cp_sat.py <export.json> --k 14

No official verifier is invoked.
"""
import argparse
import json
import sys

from pysat.solvers import Solver


class Enc:
    def __init__(self):
        self.n = 0
        self.clauses = []

    def var(self):
        self.n += 1
        return self.n

    def add(self, *xs):
        self.clauses.append(list(xs))

    def xor3(self, a, b, c):
        """c <-> a XOR b."""
        self.add(-a, -b, -c)
        self.add(a, b, -c)
        self.add(a, -b, c)
        self.add(-a, b, c)

    def eq_const(self, x, val):
        self.add(x if val else -x)


def build(exp, k):
    inputs = exp['inputs']
    outs = sorted(exp['outputs'], key=int)
    # bipartition from the quadratic graph
    adj = {}
    for o in exp['outputs'].values():
        for a, b in o['quadratic']:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    color = {}
    for v in sorted(adj):
        if v in color:
            continue
        color[v] = 0
        st = [v]
        while st:
            a = st.pop()
            for b in adj[a]:
                if b not in color:
                    color[b] = 1 - color[a]
                    st.append(b)
    X = sorted(v for v in adj if color[v] == 0)
    Y = sorted(v for v in adj if color[v] == 1)
    xi = {v: i for i, v in enumerate(X)}
    yi = {v: i for i, v in enumerate(Y)}
    T = {}
    for j, w in enumerate(outs):
        for a, b in exp['outputs'][w]['quadratic']:
            if a in yi:
                a, b = b, a
            T[(j, xi[a], yi[b])] = 1
    return X, Y, outs, T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('--k', type=int, required=True)
    ap.add_argument('--solver', default='cadical153')
    ap.add_argument('--timeout', type=int, default=0)
    ap.add_argument('--sym-break', action='store_true')
    a = ap.parse_args()
    exp = json.load(open(a.json))
    X, Y, outs, T = build(exp, a.k)
    J, I, L = len(outs), len(X), len(Y)
    print(f'k={a.k} X={len(X)} Y={len(Y)} outputs={len(outs)} terms={len(T)}')
    e = Enc()
    A = [[e.var() for _ in range(J)] for _ in range(a.k)]
    U = [[e.var() for _ in range(I)] for _ in range(a.k)]
    V = [[e.var() for _ in range(L)] for _ in range(a.k)]
    # nonzero generators
    for t in range(a.k):
        e.add(*A[t])
        e.add(*U[t])
        e.add(*V[t])
    # z[t,j,i,l] = A & U & V
    Z = {}
    for t in range(a.k):
        for j in range(J):
            for i in range(I):
                for l in range(L):
                    z = e.var()
                    Z[(t, j, i, l)] = z
                    e.add(-z, A[t][j])
                    e.add(-z, U[t][i])
                    e.add(-z, V[t][l])
                    e.add(-A[t][j], -U[t][i], -V[t][l], z)
    # XOR equations
    for j in range(J):
        for i in range(I):
            for l in range(L):
                rhs = T.get((j, i, l), 0)
                prev = Z[(0, j, i, l)]
                for t in range(1, a.k):
                    nxt = e.var()
                    e.xor3(prev, Z[(t, j, i, l)], nxt)
                    prev = nxt
                e.eq_const(prev, rhs)
    # sort generators by the binary value of a_t (valid symmetry break)
    if a.sym_break:
        for t in range(a.k - 1):
            # a_t <= a_{t+1} lexicographically (MSB = output 0)
            # build comparator: leq = OR over first differing bit
            bits1 = A[t]
            bits2 = A[t + 1]
            # eq_prefix and leq via simple state chain
            eq = None
            leq = None
            for b1, b2 in zip(bits1, bits2):
                # lt_here = ~b1 & b2
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
                else:
                    newleq = e.var()
                    e.add(-leq, newleq)
                    e.add(-lt, newleq)
                    e.add(leq, lt, -newleq)
                    neweq = e.var()
                    e.add(-eq, neweq)
                    e.add(-lt, neweq)
                    e.add(eq, lt, -neweq)
                    leq, eq = newleq, neweq
            e.add(leq)
    print(f'vars={e.n} clauses={len(e.clauses)}')
    solver = Solver(name=a.solver, bootstrap_with=e.clauses)
    if a.timeout:
        solver.set_phases([])  # no-op, keep API
    ok = solver.solve_limited(expect_interrupt=True)
    print('result:', ok)
    if ok:
        model = set(x for x in solver.get_model() if x > 0)
        sol = []
        for t in range(a.k):
            av = sum((1 << j) for j in range(J) if A[t][j] in model)
            uv = sum((1 << i) for i in range(I) if U[t][i] in model)
            vv = sum((1 << l) for l in range(L) if V[t][l] in model)
            sol.append({'a': av, 'u': uv, 'v': vv})
        print(json.dumps({'k': a.k, 'X': X, 'Y': Y, 'outs': outs,
                          'sol': sol}, indent=1))
        out = a.json.replace('.json', f'_cp{a.k}.json')
        json.dump({'k': a.k, 'X': X, 'Y': Y, 'outs': outs, 'sol': sol},
                  open(out, 'w'), indent=1)
        print('wrote', out)
    solver.delete()


if __name__ == '__main__':
    main()
