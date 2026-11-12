"""Lower bound on the number of product CCX per circuit.

Write a word bit's delta as  f(a) = sum_{P in 0..15} [a_low = P] * h_P(a_high),  where
a = 16*q + P.  This decomposition is unique (indicator decomposition) and h_P is an
arbitrary function of the 7 high bits (a 128-bit vector).

A product gate A*B with A = sum_P x_P a_P and B = sum_Q x_Q c_Q contributes
a_P * c_Q to column P|Q (as a function of the high bits).  Therefore the 16x128
GF(2) matrix h whose P-th row is h_P has GF(2) rank at most the number of product
gates used for that bit.  Summing over bits gives a *rigorous* lower bound on the
product CCX count of any loader in this construction family.

Current: 193 products / 40 bits = 4.83 per bit (k=4).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lifetimes as L


def gf2_rank_rows(rows):
    basis = []
    for x in rows:
        v = x
        for b in basis:
            v = min(v, v ^ b)
        if v:
            basis.append(v)
            basis.sort(reverse=True)
    return len(basis)


def per_bit_rank(tt):
    """tt: 2048-bit truth table over 11 address bits. Returns rank of the 16x128 matrix."""
    rows = []
    for P in range(16):
        v = 0
        for q in range(128):
            if (tt >> (16 * q + P)) & 1:
                v |= 1 << q
        rows.append(v)
    return gf2_rank_rows(rows), rows


def main():
    kmx = Path('/Users/zhaohuaxiang/ccjjllc/quantum') if False else Path(
        '/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_re/kmx_maoxin')
    cur = {0: 212, 1: 212, 2: 212, 3: 212, 4: 193, 5: 193, 6: 193, 7: 193, 8: 193,
           9: 189, 10: 190, 11: 191, 12: 191, 13: 191, 14: 191}
    tot = 0
    tot_rank = 0
    for k in range(15):
        p = kmx / f'angle_k_{k}.kmx'
        lines, qname, nq = L.parse(p)
        f = [0] * nq
        for q, nm in qname.items():
            if nm.startswith('sel'):
                f[q] = L.VAR[int(nm[3:])]
        for i, ln in enumerate(lines):
            parts = ln.split()
            if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
                continue
            g = parts[0]
            qs = [int(x[1:]) for x in parts[1:] if x.startswith('q')]
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
        ranks = []
        for q, nm in sorted(qname.items()):
            if nm.startswith('w') and f[q]:
                r, _ = per_bit_rank(f[q])
                ranks.append(r)
        ranks = [r for r in ranks if r]
        # every word bit must be covered; bits with zero delta need no product
        tot += len(ranks)
        tot_rank += sum(ranks)
        print(f'k={k:2d} bits_with_delta={len(ranks):2d} rank_sum={sum(ranks):3d} '
              f'rank_hist={ {r: ranks.count(r) for r in sorted(set(ranks))} } '
              f'current_products={cur[k]:3d}  floor_products={sum(ranks):3d} '
              f'floor+cache={sum(ranks) + (cur[k] - 0):3d}')
    print(f'\nTOTAL rank_sum={tot_rank} (bits={tot})  current products=2,956  '
          f'ratio={2956 / tot_rank:.2f}x')


if __name__ == '__main__':
    main()
