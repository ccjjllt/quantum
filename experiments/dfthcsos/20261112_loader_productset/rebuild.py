"""Rewrite a Maoxin angle loader so that every CCX whose output function is already
*available* is replaced by free CX gates (and every identically-zero CCX is deleted).

Why this is exactly semantics-preserving on the 1220 addresses the verifier simulates:

  * `CCX a b t` XORs the function  Q = f[a] & f[b]  into t.  If Q == 0 (over the real
    addresses) the gate is a no-op and can be deleted.
  * If some *live* qubit u already holds Q, then `CX u t` has exactly the same effect
    on t, and nothing else in the circuit changes.
  * If Q is a GF(2) sum of functions that are each held by a live qubit
    (cache monomials, address bits, the constant 1), then one CX per term (plus an X
    on the target for the constant) has exactly the same effect.
  In every case t receives the same XOR, so *all* downstream state is bit-identical on
  the real addresses, hence words, workspace cleanliness and the reverse pass are
  unchanged.

Nothing else is touched: pivot rebuilds, X/R/HMR/CZ and their classical bits are kept.

Usage:
  python rebuild.py                 # rewrite all 15, print counts
  python rebuild.py 4               # only k=4
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import ALL, KMXDIR, REAL, Basis, replay, VAR  # noqa: E402

OUTDIR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/20261112_loader_productset/kmx_slim')


def build_slim(path: Path, verbose: bool = False):
    lines = path.read_text().splitlines()
    header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    d = replay(path)
    nq = d['nq']
    mask = REAL
    # static generator set for decompositions: unique nonzero cache monomials + 1 + addr bits
    gens: list[int] = []
    for _, tt in d['cache']:
        v = tt & mask
        if v and v not in gens:
            gens.append(v)
    gens.append(mask)
    gens += [v & mask for v in VAR]
    gpiv: dict[int, tuple[int, int]] = {}
    for j, g in enumerate(gens):
        w, combo = g, 1 << j
        while w:
            p = w.bit_length() - 1
            if p in gpiv:
                w ^= gpiv[p][0]
                combo ^= gpiv[p][1]
            else:
                gpiv[p] = (w, combo)
                break

    def decompose(v: int):
        w, combo = v, 0
        while w:
            p = w.bit_length() - 1
            if p not in gpiv:
                return None
            w ^= gpiv[p][0]
            combo ^= gpiv[p][1]
        return combo

    f = [0] * nq
    for q, nm in d['qname'].items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
    out_lines: list[str] = []
    n_ccx_in = n_ccx_out = 0
    n_cx_in = n_cx_out = 0
    subst_zero = subst_cx1 = subst_cxN = 0
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        op = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if op == 'CCX':
            n_ccx_in += 1
            a, b, t = qs
            tt = f[a] & f[b]
            ttm = tt & mask
            live = {}
            for q in range(nq):
                if q != t and ttm and (f[q] & mask) == ttm:
                    live[q] = True
            if ttm == 0:
                subst_zero += 1
                # no-op: do not emit, do not change f
                continue
            if live:
                u = min(live)
                out_lines.append(f'CX q{u} q{t}')
                n_cx_out += 1
                subst_cx1 += 1
                f[t] ^= tt
                continue
            combo = decompose(ttm)
            if combo is not None:
                terms = [gens[j] for j in range(len(gens)) if combo >> j & 1]
                plan, ok = [], True
                for gv in terms:
                    if gv == mask:
                        plan.append(('X', None))
                        continue
                    cand = [q for q in range(nq) if q != t and (f[q] & mask) == gv]
                    if not cand:
                        ok = False
                        break
                    plan.append(('CX', min(cand)))
                if ok:
                    for kind, u in plan:
                        out_lines.append(f'X q{t}' if kind == 'X' else f'CX q{u} q{t}')
                        n_cx_out += 1
                    subst_cxN += 1
                    f[t] ^= tt
                    continue
            out_lines.append(ln)
            n_ccx_out += 1
            f[t] ^= tt
        elif op == 'CX':
            n_cx_in += 1
            a, t = qs[0], qs[1]
            val = f[a]
            if val == 0:
                subst_zero += 1
                continue
            out_lines.append(ln)
            n_cx_out += 1
            f[t] ^= val
        elif op == 'X':
            out_lines.append(ln)
            for q in qs:
                f[q] = ~f[q] & ALL
        elif op in ('R', 'HMR'):
            out_lines.append(ln)
            for q in qs:
                f[q] = 0
        else:
            out_lines.append(ln)
    text = '\n'.join(header + out_lines) + '\n'
    stats = dict(ccx_in=n_ccx_in, ccx_out=n_ccx_out, cx_in=n_cx_in, cx_out=n_cx_out,
                 zero=subst_zero, cx1=subst_cx1, cxN=subst_cxN,
                 saved=n_ccx_in - n_ccx_out, nq=nq, header=len(header))
    return text, stats


def main() -> None:
    ks = [int(sys.argv[1])] if len(sys.argv) > 1 else list(range(15))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    tot = 0
    tot_new = 0
    for k in ks:
        text, st = build_slim(KMXDIR / f'angle_k_{k}.kmx')
        (OUTDIR / f'angle_k_{k}.kmx').write_text(text)
        tot += st['ccx_in']
        tot_new += st['ccx_out']
        print(f'k={k:2d}  CCX {st["ccx_in"]:4d} -> {st["ccx_out"]:4d}  (saved {st["saved"]:3d}:'
              f' zero {st["zero"]:3d}, 1-CX {st["cx1"]:3d}, multi-CX {st["cxN"]:3d})'
              f'  CX {st["cx_in"]} -> {st["cx_out"]}')
    print(f'\nTOTAL CCX {tot} -> {tot_new}   (saved {tot - tot_new})')
    lam = 46.9074
    for T in (tot, tot_new):
        print(f'  T={T:5d} -> T_total={2 * T + 6662:6d} -> cost={lam * (2 * T + 6662) * 427 / 1e6:.2f}M')
    print(f'wrote {OUTDIR}')


if __name__ == '__main__':
    main()
