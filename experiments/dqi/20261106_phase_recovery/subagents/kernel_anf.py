"""Exact ANF extraction and bilinear-tensor analysis for extracted DQI kernels.

Reads a .kmx window (X/CX/CCX/SWAP only), propagates the exact Boolean ANF of
every wire as a polynomial in the *initial* values of all wires in the window,
and reports for each wire the delta polynomial (final XOR initial).

The contract checked here is the value map only:
    out_w  ^=  f_w(inputs)
with f_w independent of the initial values of the output wires.  That is what
the window really does when embedded in the larger circuit; the phase action of
the surrounding DQI code is not modelled.

Usage:
    python kernel_anf.py analyze <kernel.kmx> [--json out.json]
    python kernel_anf.py rank <kernel.kmx>

No official verifier is invoked.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


def parse(path):
    lines = []
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        lines.append(line)
    return lines


def wire_of(line):
    return [int(q) for q in re.findall(r'\bq(\d+)\b', line)]


def poly_mul(a, b):
    out = {}
    for ma in a:
        for mb in b:
            m = ma | mb
            if m in out:
                del out[m]
            else:
                out[m] = 1
    return out


def propagate(lines):
    wires = sorted({q for line in lines for q in wire_of(line)})
    index = {q: i for i, q in enumerate(wires)}
    n = len(wires)
    state = {q: {1 << index[q]: 1} for q in wires}
    initial = {q: dict(v) for q, v in state.items()}
    records = []          # per-CCX control ANFs for reporting
    counts = Counter()
    max_monomials = 0
    for line in lines:
        op = line.split()[0]
        counts[op] += 1
        if op == 'INFO_TAG':
            continue
        if ' if ' in line or op not in ('X', 'CX', 'CCX', 'SWAP'):
            raise SystemExit(f'unsupported gate/condition: {line}')
        ws = wire_of(line)
        if op == 'X':
            w = ws[0]
            state[w] = dict(state[w])
            if 0 in state[w]:
                del state[w][0]
            else:
                state[w][0] = 1
        elif op == 'CX':
            a, b = ws
            for m, c in state[a].items():
                if m in state[b]:
                    del state[b][m]
                else:
                    state[b][m] = 1
        elif op == 'SWAP':
            a, b = ws
            state[a], state[b] = state[b], state[a]
        else:
            a, b, c = ws
            records.append({'line': line, 'a': dict(state[a]), 'b': dict(state[b]),
                            'target': c})
            prod = poly_mul(state[a], state[b])
            st = dict(state[c])
            for m in prod:
                if m in st:
                    del st[m]
                else:
                    st[m] = 1
            state[c] = st
        max_monomials = max(max_monomials, max(len(v) for v in state.values()))
    delta = {}
    for q in wires:
        st = dict(state[q])
        for m in initial[q]:
            if m in st:
                del st[m]
            else:
                st[m] = 1
        if st:
            delta[q] = st
    return {'wires': wires, 'index': index, 'n': n, 'delta': delta,
            'counts': dict(counts), 'max_monomials': max_monomials,
            'ccx_records': records}


def monomial_vars(mask, wires):
    return [wires[i] for i in range(len(wires)) if mask >> i & 1]


def split_quadratic(info):
    """Return dict wire -> (constant, linear dict, quadratic dict) in input vars.

    Input variables are the wires with empty delta (unchanged by the window).
    Raises if any delta mentions a changed wire's initial value.
    """
    wires = info['wires']
    changed = set(info['delta'])
    inputs = [w for w in wires if w not in changed]
    input_index = {w: i for i, w in enumerate(inputs)}
    out = {}
    for w, poly in info['delta'].items():
        const = 0
        linear = {}
        quad = {}
        degree = 0
        for mask in poly:
            vs = monomial_vars(mask, wires)
            bad = [v for v in vs if v not in input_index]
            if bad:
                raise SystemExit(f'wire {w}: delta depends on changed wire {bad}')
            degree = max(degree, len(vs))
            if len(vs) == 0:
                const ^= 1
            elif len(vs) == 1:
                linear[vs[0]] = 1
            elif len(vs) == 2:
                quad[tuple(vs)] = 1
            else:
                raise SystemExit(f'wire {w}: degree {len(vs)} > 2')
        out[w] = {'const': const, 'linear': linear, 'quadratic': quad,
                  'degree': degree}
    return inputs, out


def gf2_rank(rows, ncols):
    """Rank of a list of ints (bit rows over ncols bits)."""
    basis = []
    for r in rows:
        x = r
        for b in basis:
            x = min(x, x ^ b)
        if x:
            basis.append(x)
            basis.sort(reverse=True)
    return len(basis)


def report(path):
    lines = parse(path)
    info = propagate(lines)
    inputs, outs = split_quadratic(info)
    print(f'file: {path}')
    print(f'wires: {len(info["wires"])}  gates: {info["counts"]}  '
          f'max ANF monomials/wire: {info["max_monomials"]}')
    print(f'inputs ({len(inputs)}): {inputs}')
    print(f'outputs ({len(outs)}): {sorted(outs)}')
    for w in sorted(outs):
        d = outs[w]
        print(f'  out {w}: deg={d["degree"]} const={d["const"]} '
              f'linear={len(d["linear"])} quad={len(d["quadratic"])}')
    # original CCX generators: control linear forms
    print('CCX generator list (control ANF at time of gate):')
    idx = {w: i for i, w in enumerate(info['wires'])}
    for rec in info['ccx_records']:
        def fmt(p):
            terms = []
            for m in sorted(p):
                terms.append('*'.join(str(x) for x in monomial_vars(m, info['wires'])) or '1')
            return '+'.join(terms)
        print(f'  {rec["line"]:28s} a={fmt(rec["a"]):40s} b={fmt(rec["b"])}')


def ranks(path):
    lines = parse(path)
    info = propagate(lines)
    inputs, outs = split_quadratic(info)
    ii = {w: i for i, w in enumerate(inputs)}
    # homogeneous quadratic part as vector over pairs
    pairs = list(combinations(range(len(inputs)), 2))
    pidx = {p: j for j, p in enumerate(pairs)}
    vecs = {}
    for w in sorted(outs):
        v = 0
        for (a, b) in outs[w]['quadratic']:
            i, j = sorted((ii[a], ii[b]))
            v ^= 1 << pidx[(i, j)]
        vecs[w] = v
    rows = list(vecs.values())
    print(f'{path}: n_inputs={len(inputs)} n_outputs={len(outs)} '
          f'quadratic-space-dim={len(pairs)}')
    print(f'  span rank of output quadratic forms = {gf2_rank(rows, len(pairs))}')
    # per-output matrix rank if bipartite
    return inputs, outs, vecs, pairs


if __name__ == '__main__':
    cmd = sys.argv[1]
    path = sys.argv[2]
    if cmd == 'analyze':
        report(path)
    elif cmd == 'rank':
        ranks(path)
    else:
        raise SystemExit('unknown command')
