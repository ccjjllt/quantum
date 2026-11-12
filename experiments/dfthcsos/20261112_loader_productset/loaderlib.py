"""Exact GF(2) helpers + Maoxin .kmx replay, with a correct canonical-form reduction.

`reduce_mod` here zeroes *every* pivot position (a true projection onto a complement),
which the earlier one-liner did not: it stopped at the first non-pivot leading bit and
left lower pivot bits set.
"""
from __future__ import annotations

import re
from pathlib import Path

KMXDIR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
              '20261112_loader_re/kmx_maoxin')
N = 2048
ALL = (1 << N) - 1
NREAL = 1220
REAL = (1 << NREAL) - 1


def var_tt(i: int) -> int:
    period = 1 << i
    block = ((1 << period) - 1) << period
    out = 0
    for s in range(0, N, 2 * period):
        out |= block << s
    return out


VAR = [var_tt(i) for i in range(11)]


class Basis:
    """Row-echelon GF(2) basis of big-int truth tables, with exact membership test."""

    def __init__(self, vals=()):
        self.piv: dict[int, int] = {}
        for v in vals:
            self.add(v)
        self.desc = sorted(self.piv, reverse=True)

    def add(self, v: int) -> bool:
        while v:
            p = v.bit_length() - 1
            if p in self.piv:
                v ^= self.piv[p]
            else:
                self.piv[p] = v
                self.desc = sorted(self.piv, reverse=True)
                return True
        return False

    def __len__(self) -> int:
        return len(self.piv)

    def reduce(self, v: int) -> int:
        for p in self.desc:
            if (v >> p) & 1:
                v ^= self.piv[p]
        return v

    def contains(self, v: int) -> bool:
        return self.reduce(v) == 0

    def values(self):
        return list(self.piv.values())


def replay(path: Path):
    """Symbolic replay.  Returns gate records plus the final truth table of every qubit."""
    lines = path.read_text().splitlines()
    names, regs = {}, {}
    for ln in lines:
        m = re.fullmatch(r'APPEND_TO_REGISTER q(\d+) r(\d+)', ln)
        if m:
            regs.setdefault(int(m.group(2)), []).append(int(m.group(1)))
        m = re.fullmatch(r'REGISTER r(\d+) "(\w+)"', ln)
        if m:
            names[int(m.group(1))] = m.group(2)
    qname, word_qubits = {}, []
    for rid, qs in regs.items():
        nm = names[rid]
        for i, q in enumerate(qs):
            qname[q] = f'sel{i}' if nm == 'selection' else f'w{nm[5:]}.{i}'
            if nm != 'selection':
                word_qubits.append(q)
    nq = 0
    for ln in lines:
        for p in ln.split():
            if p.startswith('q'):
                nq = max(nq, int(p[1:]) + 1)

    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    gates = []           # dicts: op, ctrls, target, tt (for CCX)
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g, qs = parts[0], [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            gates.append(dict(op='CX', c=[qs[0]], t=qs[1]))
            f[qs[1]] ^= f[qs[0]]
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            gates.append(dict(op='CCX', c=[a, b], t=t, tt=tt))
            f[t] ^= tt
        elif g == 'X':
            gates.append(dict(op='X', c=[], t=None, qs=qs))
            for q in qs:
                f[q] = ~f[q] & ALL
        elif g in ('R', 'HMR'):
            gates.append(dict(op=g, c=[], t=None, qs=qs))
            for q in qs:
                f[q] = 0
        elif g in ('CZ', 'Z', 'CCZ', 'NEG'):
            gates.append(dict(op=g, c=qs, t=None))
        else:
            raise SystemExit(f'unknown {g}')
    cache = [(gd['t'], gd['tt']) for gd in gates
             if gd['op'] == 'CCX' and not qname.get(gd['t'], '').startswith('w')]
    prods = [(gd['t'], gd['tt'], gd) for gd in gates
             if gd['op'] == 'CCX' and qname.get(gd['t'], '').startswith('w')]
    outs = [f[q] for q in word_qubits]
    return dict(nq=nq, gates=gates, cache=cache, prods=prods, outs=outs, f=f,
                qname=qname, word_qubits=word_qubits, lines=lines,
                n_cx=sum(1 for g in gates if g['op'] == 'CX'),
                n_ccx=sum(1 for g in gates if g['op'] == 'CCX'))


def g0_basis(cache, mask=REAL) -> Basis:
    return Basis([v & mask for v in [tt for _, tt in cache] + [mask] + VAR])
