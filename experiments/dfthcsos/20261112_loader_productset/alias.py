"""Alias ancillas that compute the *same function*: keep one CCX, redirect every read.

In every Maoxin circuit the five flag monomials (q120,q121,q123,q124,q125 for k=1..8)
turn out to be the same function of the address over the 1220 real addresses, and
k=9..13 have two such pairs.  Each duplicate costs a CCX even though a live qubit
already holds the function, so it can be rebuilt with one CX (or simply aliased).

Rule: for qubits that are (a) neither selection nor word, (b) written by exactly one
CCX and never by a CX, (c) currently at the same nonzero function over the real
addresses, and (d) whose representative is already alive at every later read --
drop the duplicate CCX and redirect its reads to the representative.  Verified by
full kickmix simulation afterwards.

Usage: python alias.py
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import KMXDIR, REAL, replay  # noqa: E402

IN = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
          '20261112_loader_productset/kmx_slim')
OUT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
           '20261112_loader_productset/kmx_alias')


def slim_lines(lines: list[str]) -> tuple[list[str], int, int]:
    d = replay_text(lines)
    qn = d['qname']
    nq = d['nq']
    ccx_writes = defaultdict(list)
    write_tt = {}
    cx_writes = defaultdict(list)
    reads = defaultdict(list)
    for i, gd in enumerate(d['gates']):
        if gd['op'] == 'CCX':
            ccx_writes[gd['t']].append(i)
            write_tt[i] = gd['tt'] & REAL
            reads[gd['c'][0]].append(i)
            reads[gd['c'][1]].append(i)
        elif gd['op'] == 'CX':
            cx_writes[gd['t']].append(i)
            reads[gd['c'][0]].append(i)
        elif gd['op'] in ('R', 'HMR'):
            for q in gd['qs']:
                reads[q].append(i)
    groups = defaultdict(list)
    for q in range(nq):
        nm = qn.get(q, '')
        if nm.startswith(('sel', 'w')):
            continue
        if len(ccx_writes[q]) == 1 and not cx_writes[q]:
            v = write_tt.get(ccx_writes[q][0], 0)
            if v:
                groups[v].append(q)
    alias = {}
    for v, qs in groups.items():
        if len(qs) < 2:
            continue
        qs.sort(key=lambda q: ccx_writes[q][0])
        rep = qs[0]
        first_read = {}
        for q in qs[1:]:
            fr = min((i for i in reads[q] if i > ccx_writes[q][0]), default=10 ** 9)
            first_read[q] = fr
        for q in qs[1:]:
            if ccx_writes[rep][0] < first_read[q]:
                alias[q] = rep
    # rebuild
    header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    out = []
    drop = set()
    for q, rep in alias.items():
        drop.add(ccx_writes[q][0])
    for i, ln in enumerate(lines):
        if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER')):
            continue
        if i in drop:
            continue
        parts = ln.split()
        if parts and parts[0] in ('CX', 'CCX'):
            qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
            newq = [alias.get(q, q) for q in qs]
            if parts[0] == 'CX':
                if newq[0] == newq[1]:
                    continue
                ln = f'CX q{newq[0]} q{newq[1]}'
            else:
                ln = f'CCX q{newq[0]} q{newq[1]} q{newq[2]}'
        elif parts and parts[0] == 'X':
            qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
            ln = 'X ' + ' '.join(f'q{alias.get(q, q)}' for q in qs)
        out.append(ln)
    n_ccx = sum(1 for x in out if x.startswith('CCX'))
    return out, len(alias), n_ccx


def replay_text(lines: list[str]):
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.kmx', delete=False) as fh:
        fh.write('\n'.join(lines) + '\n')
        tmp = fh.name
    return replay(Path(tmp))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tot_in = tot_out = 0
    for k in range(15):
        lines = (IN / f'angle_k_{k}.kmx').read_text().splitlines()
        n_in = sum(1 for x in lines if x.startswith('CCX'))
        out, n_alias, n_out = slim_lines(lines)
        header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
        (OUT / f'angle_k_{k}.kmx').write_text('\n'.join(header + out) + '\n')
        tot_in += n_in
        tot_out += n_out
        print(f'k={k:2d}: aliased {n_alias}  CCX {n_in} -> {n_out}')
    print(f'\nTOTAL CCX {tot_in} -> {tot_out}')
    lam = 46.9074
    for T in (tot_in, tot_out):
        print(f'  T={T:5d} -> T_total={2 * T + 6662:6d} -> cost={lam * (2 * T + 6662) * 427 / 1e6:.2f}M')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
