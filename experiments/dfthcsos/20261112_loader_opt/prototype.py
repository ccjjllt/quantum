"""Prototype: remove only the provably dead CCX (zero-effect ANDs + ANDs whose ancilla is
never read) and verify exactly.

Checks
  1. symbolic: every qubit's final function and the workspace state are unchanged
  2. kickmix: num_toffoli_like / num_qubits before vs after
  3. words: full 1220-address comparison on both verifier paths (z = batch_{k-1} and
     z = batch_k) for the single prototype circuit

Only circuit k=4 is simulated (the family total is a static count).
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import lifetimes as L

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
KMX = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_re/kmx_maoxin')
WORDS = ROOT / 'artifacts/20261112_eae_candidate/dfthcsos/submission.npz'


def masks(path):
    """Return (set of removed line indices, cache-AND count, zero count) with proof."""
    lines, qname, nq = L.parse(path)
    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = L.VAR[int(nm[3:])]
    reads = {}
    live = {}
    drop = set()
    for i, ln in enumerate(lines):
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            reads[a] = reads.get(a, 0) + 1
            f[b] ^= f[a]
            if b in live:
                if reads.get(b, 0) - live[b]['reads'] == 0:
                    drop.add(live[b]['line'])
                live.pop(b)
        elif g == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            reads[a] = reads.get(a, 0) + 1
            reads[b] = reads.get(b, 0) + 1
            if tt == 0:
                drop.add(i)
            elif not qname.get(t, '').startswith('w'):
                live[t] = dict(line=i, reads=reads.get(t, 0))
            f[t] ^= tt
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & L.ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
                if q in live:
                    if reads.get(q, 0) - live[q]['reads'] == 0:
                        drop.add(live[q]['line'])
                    live.pop(q)
    for q, rec in live.items():
        if reads.get(q, 0) - rec['reads'] == 0:
            drop.add(rec['line'])
    return lines, drop


def replay(lines, qname, nq, skip):
    f = [0] * nq
    for q, nm in qname.items():
        if nm.startswith('sel'):
            f[q] = L.VAR[int(nm[3:])]
    for i, ln in enumerate(lines):
        if i in skip:
            continue
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        g = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if g == 'CX':
            a, b = qs
            f[b] ^= f[a]
        elif g == 'CCX':
            a, b, t = qs
            f[t] ^= f[a] & f[b]
        elif g == 'X':
            for q in qs:
                f[q] = ~f[q] & L.ALL
        elif g in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
    return f


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    path = KMX / f'angle_k_{n}.kmx'
    lines, qname, nq = L.parse(path)
    lines2, drop = masks(path)
    # the AND being dropped may live across a CX rewrite; recompute reads inside masks
    lines, drop = masks(path)
    f0 = replay(lines, qname, nq, set())
    f1 = replay(lines, qname, nq, drop)
    same = all(f0[q] == f1[q] for q in range(nq))
    work = [q for q in range(nq) if not qname.get(q, '').startswith(('w', 'sel'))]
    clean = all(f1[q] == 0 for q in work)
    print(f'k={n}: dropping {len(drop)} gates -> same_final={same} workspace_clean={clean}')
    print('  dropped line numbers:', sorted(x + 1 for x in drop))
    # static T count from the text
    def count_ccx(ls, skip):
        c = 0
        for i, ln in enumerate(ls):
            if i in skip:
                continue
            p = ln.split()
            if p and p[0] in ('CCX', 'CCZ', 'CSWAP'):
                c += 1
        return c
    print(f'  CCX {count_ccx(lines, set())} -> {count_ccx(lines, drop)}')

    # ---- kickmix: build the trimmed circuit and simulate both verifier paths
    import kickmix as km
    sys.path.insert(0, str(ROOT / 'data/competition/verifiers'))
    from dfthcsos.scoreinfra.circuits import register_layout

    fam = [km.Circuit.from_file(KMX / f'angle_k_{k}.kmx', format='auto') for k in range(15)]
    layout = register_layout(fam)
    print(f'  layout: J={layout.batch_size} brot={layout.brot} sel={len(layout.selection)}')

    def build(lines_subset, dst):
        reg_lines = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
        body = [ln for i, ln in enumerate(lines) if i not in lines_subset and ln.split()
                and not ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
        dst.write_text('\n'.join(reg_lines + body) + '\n')
        return dst

    tmp = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode')
    tmp.mkdir(parents=True, exist_ok=True)
    orig = km.Circuit.from_file(path, format='auto')
    trimmed = km.Circuit.from_file(build(drop, tmp / f'k{n}_trim.kmx'), format='auto')
    for nm, c in (('orig', orig), ('trim', trimmed)):
        st = c.operation_statistics()
        print(f'  {nm}: qubits={c.num_qubits} ops={len(c)} toffoli_like={st.num_toffoli_like}')

    W = np.load(WORDS)['angle_words']
    J = layout.batch_size
    batch = W[:, n * J:(n + 1) * J]
    prev = W[:, (n - 1) * J:n * J] if n else np.zeros_like(batch)

    def words_after(circ, z):
        sim = km.Simulator(batch_size=1220, debug_print=False, seed=1, counting_operations=True)
        sim.use_same_registers_as(circ)
        addrs = np.arange(1220)
        sim.write_across_shots(layout.selection,
                               np.array([[(a >> i) & 1 for a in addrs]
                                         for i in range(len(layout.selection))], bool))
        for j, reg in enumerate(layout.words):
            sim.write_across_shots(reg, np.array([[(z[a, j] >> k) & 1 for a in addrs]
                                                  for k in range(layout.brot)], bool))
        sim.do(circ)
        out = np.zeros((1220, layout.batch_size), np.int64)
        for j, reg in enumerate(layout.words):
            b = np.array(sim.read_across_shots(reg), bool)
            out[:, j] = (b.T.astype(np.int64) << np.arange(layout.brot)).sum(axis=1)
        return out

    for label, z in (('fwd z=batch[k-1]', prev), ('rev z=batch[k]', batch)):
        a = words_after(orig, z)
        b = words_after(trimmed, z)
        print(f'  {label}: orig==trim {np.array_equal(a, b)}  '
              f'orig==batch {(a == batch).all()}  trim==batch {(b == batch).all()}')


if __name__ == '__main__':
    main()
