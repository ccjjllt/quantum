"""Gate-level check of the model's product semantics with real stateful kickmix simulation.

Toy instance: 7 address bits a0..a6 (a0..a3 = r side, a4..a6 = q side).
Cache the r-side pairs (11 -> here 6) and the q-side multi-bit monomials, then
    form A = u(r) + v(q)   on pivot p1   (pure CX from cached ancillas / address bits / X)
    form B = u'(r) + v'(q) on pivot p2
    CCX p1 p2 target
and compare the target bit, over all 2**7 inputs, with the polynomial product A*B
computed in GF(2)[x]/(x_i^2 = x_i).

This validates the two claims the whole analysis rests on:
  * a "full low support" form (all 16 r-monomials XORed on one pivot) costs only CX;
  * one product CCX realizes exactly A*B, i.e. the full 16-column rectangle
    u(r) v'(q) + v(r) u'(q) + col0 + row0.
"""
from __future__ import annotations

import numpy as np
import kickmix as km

NA = 7
NS = 1 << NA


def var_mask(i: int) -> np.ndarray:
    return np.array([(a >> i) & 1 for a in range(NS)], np.uint8)


def anf_basis(mask: int) -> np.ndarray:
    out = np.ones(NS, np.uint8)
    for i in range(NA):
        if mask >> i & 1:
            out &= var_mask(i)
    return out


def product(u1: int, v1: int, u2: int, v2: int) -> np.ndarray:
    """(u1(r)+v1(q)) * (u2(r)+v2(q)) as a truth table over 2**7 inputs."""
    f = np.zeros(NS, np.uint8)
    for a in range(16):
        for b in range(16):
            if (u1 >> a & 1) and (u2 >> b & 1):
                f ^= anf_basis(a | b)          # u1*u2 (r-side only)
    for a in range(16):
        for q in range(8):
            if (u1 >> a & 1) and (v2 >> q & 1):
                f ^= anf_basis(a | (q << 4))
            if (v1 >> q & 1) and (u2 >> a & 1):
                f ^= anf_basis(a | (q << 4))
    for p in range(8):
        for q in range(8):
            if (v1 >> p & 1) and (v2 >> q & 1):
                f ^= anf_basis((p << 4) | (q << 4))
    return f


def r_mons() -> list[int]:
    """All 11 non-single r-monomials: 6 pairs + 4 triples + 1 quadruple (one AND each)."""
    pairs = [m for m in range(1, 16) if bin(m).count('1') == 2]
    trip = [m for m in range(1, 16) if bin(m).count('1') == 3]
    quad = [m for m in range(1, 16) if bin(m).count('1') == 4]
    return pairs + trip + quad


def q_mons() -> list[int]:
    """q-side monomials (bit index within the q block) cached with one AND each."""
    return [0b011, 0b101, 0b110, 0b111]


def build(u1: int, v1: int, u2: int, v2: int) -> tuple[str, list[str]]:
    """Return (kmx text, names of the pivot qubits) for the toy circuit."""
    lines: list[str] = []
    rq = [f'q{i}' for i in range(4)]                 # r bits   -> q0..q3
    qq = [f'q{4 + i}' for i in range(3)]             # q bits   -> q4..q6
    next_q = 7
    r_anc: dict[int, str] = {}
    for m in r_mons():
        a = f'q{next_q}'; next_q += 1
        low = m & -m
        i = low.bit_length() - 1
        parent = m ^ low
        lines.append(f'R {a}')
        if bin(parent).count('1') == 1:
            j = parent.bit_length() - 1
            lines.append(f'CCX {rq[i]} {rq[j]} {a}')
        else:
            lines.append(f'CCX {r_anc[parent]} {rq[i]} {a}')
        r_anc[m] = a
    q_anc: dict[int, str] = {}
    for m in q_mons():
        a = f'q{next_q}'; next_q += 1
        bits = [i for i in range(3) if m >> i & 1]
        lines.append(f'R {a}')
        if len(bits) == 2:
            lines.append(f'CCX {qq[bits[0]]} {qq[bits[1]]} {a}')
        else:
            inner = q_anc[0b011]
            lines.append(f'CCX {inner} {qq[bits[2]]} {a}')
        q_anc[m] = a
    pa = f'q{next_q}'; next_q += 1
    pb = f'q{next_q}'; next_q += 1
    tgt = f'q{next_q}'; next_q += 1
    for pv, (u, v) in ((pa, (u1, v1)), (pb, (u2, v2))):
        if u & 1:
            lines.append(f'X {pv}')
        if v & 1:
            lines.append(f'X {pv}')
        for i in range(4):
            if u >> (1 << i) & 1:
                lines.append(f'CX {rq[i]} {pv}')
        for m, a in r_anc.items():
            if u >> m & 1:
                lines.append(f'CX {a} {pv}')
        for i in range(3):
            if v >> (1 << i) & 1:
                lines.append(f'CX {qq[i]} {pv}')
        for m, a in q_anc.items():
            if v >> m & 1:
                lines.append(f'CX {a} {pv}')
    lines.append(f'CCX {pa} {pb} {tgt}')
    return '\n'.join(lines), [pa, pb, tgt]


def simulate(text: str, nq: int) -> np.ndarray:
    """Return (nq, 2**7) bit table of every qubit after the circuit (measurement-free: CX/X/CCX only)."""
    circ = km.Circuit(text)
    sim = km.Simulator(batch_size=NS, debug_print=False, seed=1, counting_operations=True)
    sim.use_same_registers_as(circ)
    addrs = np.arange(NS, dtype=np.int64)
    sel = km.array([km.q(i) for i in range(NA)])
    sim.write_across_shots(
        sel, np.array([(addrs >> i) & 1 for i in range(NA)], dtype=bool))
    sim.do(circ)
    out = np.zeros((nq, NS), np.uint8)
    for i in range(nq):
        out[i] = np.array(sim.read_across_shots(km.array([km.q(i)])), bool)[0]
    return out


def main() -> None:
    cases = [
        # (u1, v1, u2, v2): full 16-monomial r-support on both pivots + q monomials
        (0xFFFF, 0b010, 0xFFFF, 0b101),
        (0xFFFF, 0b110, 0b0011, 0b011),
        (0b10001, 0b001, 0xFFFF, 0b111),
    ]
    for u1, v1, u2, v2 in cases:
        text, names = build(u1, v1, u2, v2)
        nq = 7 + len(r_mons()) + len(q_mons()) + 3
        got = simulate(text, nq)
        tgt = int(names[2][1:])
        want = product(u1, v1, u2, v2)
        ok = bool(np.array_equal(got[tgt], want))
        # the two pivots must hold the forms themselves
        pa, pb = int(names[0][1:]), int(names[1][1:])
        fa = np.zeros(NS, np.uint8)
        for a in range(16):
            if u1 >> a & 1:
                fa ^= anf_basis(a)
        for q in range(8):
            if v1 >> q & 1:
                fa ^= anf_basis(q << 4)
        fb = np.zeros(NS, np.uint8)
        for a in range(16):
            if u2 >> a & 1:
                fb ^= anf_basis(a)
        for q in range(8):
            if v2 >> q & 1:
                fb ^= anf_basis(q << 4)
        print(f'  u1={u1:05x} v1={v1:03b} u2={u2:05x} v2={v2:03b}: '
              f'pivotA ok={np.array_equal(got[pa], fa)} pivotB ok={np.array_equal(got[pb], fb)} '
              f'product ok={ok}  weight={int(want.sum())}/{NS}'
              f'  toffoli={int(circ_toffoli(text))}')


def circ_toffoli(text: str) -> int:
    return int(km.Circuit(text).operation_statistics().num_toffoli_like)


if __name__ == '__main__':
    main()
