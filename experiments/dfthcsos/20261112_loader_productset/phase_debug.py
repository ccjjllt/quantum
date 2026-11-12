"""Locate the measurement-kickback phase that the official verifier rejects.

Replicates the official `_check_state` phase test with kickmix directly (fast, one circuit
at a time) so we can bisect which rewrite introduces it.

Usage: python phase_debug.py [k]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import kickmix as km

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import KMXDIR, REAL, replay  # noqa: E402

N = 1220
SEL = [km.q(i) for i in range(11)]
WORD = [km.q(i) for i in range(11, 51)]
WS = [km.q(i) for i in range(51, 128)]


def simulate(circ, seed=20261112):
    sim = km.Simulator(batch_size=N, debug_print=False, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circ)
    addr = np.arange(N, dtype=np.int64)
    sim.write_across_shots(km.array(SEL),
                           ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool))
    sim.do(circ)
    return dict(
        phase=sim.read_phase_flipped_across_shots().copy(),
        sel=sim.read_across_shots(km.array(SEL)).copy(),
        word=sim.read_across_shots(km.array(WORD)).copy(),
        ws=sim.read_across_shots(km.array(WS)).copy(),
        toffoli=circ.operation_statistics().num_toffoli_like,
    )


def write_tmp(lines, tag):
    p = Path('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T') / f'ph_{tag}.kmx'
    p.write_text('\n'.join(lines) + '\n')
    return p


def variant(lines, drop_ccx_zero=False, drop_cx_zero=False, prod_sub=False):
    """Return a rewritten gate list; `lines` is a raw .kmx."""
    d = replay(Path(_write(lines, 'in')))
    return d


def _write(lines, tag):
    return str(write_tmp(lines, tag))


def classify(lines):
    """Replay and classify every gate: (index, op, is_zero_ccx, is_zero_cx)."""
    d = replay(Path(_write(lines, 'cls')))
    f = [0] * d['nq']
    sel = {q: int(nm[3:]) for q, nm in d['qname'].items() if nm.startswith('sel')}
    from loaderlib import ALL, VAR
    for q, i in sel.items():
        f[q] = VAR[i]
    out = []
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        op = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        z_ccx = z_cx = False
        if op == 'CCX':
            a, b, t = qs
            tt = f[a] & f[b]
            z_ccx = (tt & REAL) == 0
            f[t] ^= tt
        elif op == 'CX':
            a, t = qs
            v = f[a]
            z_cx = (v & REAL) == 0
            f[t] ^= v
        elif op == 'X':
            for q in qs:
                f[q] = ~f[q] & ALL
        elif op in ('R', 'HMR'):
            for q in qs:
                f[q] = 0
        out.append((op, z_ccx, z_cx))
    return out


def main() -> None:
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    lines = (KMXDIR / f'angle_k_{k}.kmx').read_text().splitlines()
    cls = classify(lines)
    gate_lines = [ln for ln in lines if not ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    assert len(cls) == len(gate_lines), (len(cls), len(gate_lines))

    def build(drop_zero_ccx=False, drop_zero_cx=False):
        out = []
        for (op, zc, zx), ln in zip(cls, gate_lines):
            if drop_zero_ccx and op == 'CCX' and zc:
                continue
            if drop_zero_cx and op == 'CX' and zx:
                continue
            out.append(ln)
        return header + out

    cases = {
        'orig': build(),
        'drop zero-CX only': build(drop_zero_cx=True),
        'drop zero-CCX only': build(drop_zero_ccx=True),
        'drop both (=slim)': build(drop_zero_ccx=True, drop_zero_cx=True),
    }
    ref = None
    for name, ls in cases.items():
        p = write_tmp(ls, name.replace(' ', '_'))
        r = simulate(km.Circuit.from_file(str(p), format='kmx'))
        nph = int(np.count_nonzero(r['phase']))
        if ref is None:
            ref = r
            print(f'{name:22s} CCX={r["toffoli"]:4d}  phase_flipped={nph}/{N}')
        else:
            same = np.array_equal(ref['word'], r['word'])
            print(f'{name:22s} CCX={r["toffoli"]:4d}  phase_flipped={nph}/{N}'
                  f'  words_same={same}')
        if nph:
            bad = np.flatnonzero(r['phase'])
            print(f'    first phase-flipped addresses: {bad[:8].tolist()}')


if __name__ == '__main__':
    main()
