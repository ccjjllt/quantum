"""z-safe rewrite: only touch gates whose controls are *address-only*.

The loader is a XOR oracle |a>|z> -> |a>|z + delta[a]>, so the word registers hold an
arbitrary input z.  A qubit is "address-only" (z-independent) iff its function is built
without reading any word bit.  Every rewrite below is then an identity for all z, and
phase-neutral:

  * `CCX a b t` with a, b address-only and `a & b == 0` (over the 1220 real addresses)
    -> delete.  t stays |0>; its `del_and(a,b,t)` correction is `CZ a b if b`, which can
    never fire because a&b == 0, so the measurement kickback stays phase-neutral.
  * `CX a t` with a address-only and `a == 0` -> delete.
  * `CCX a b t` with a, b address-only and `a & b` held by a *live address-only* qubit u
    -> `CX u t` (identical XOR into t for every z; no HMR involved).
  * `CCX a b t` with a, b address-only and `a & b` a GF(2) sum of live address-only
    monomials / address bits / the constant 1 -> one CX per term (X t for the constant).

Nothing else is touched.  Gates that read a word bit (the `b7` flag monomials and their
CX fan-out) are *not* rewritten, because they are only "zero" at z = 0.

Usage: python rebuild2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from loaderlib import ALL, KMXDIR, REAL, replay, VAR  # noqa: E402

OUTDIR = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
             '20261112_loader_productset/kmx_slim2')


def build(path: Path):
    lines = path.read_text().splitlines()
    header = [ln for ln in lines if ln.startswith(('APPEND_TO_REGISTER', 'REGISTER'))]
    d = replay(path)
    nq = d['nq']
    mask = REAL
    # candidate generator functions for decompositions: address-only cache monomials,
    # the constant 1 and the address bits (all z-independent by construction)
    gens: list[int] = [mask] + [v & mask for v in VAR]
    for _, tt in d['cache']:
        v = tt & mask
        if v and v not in gens:
            gens.append(v)
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
    zflag = [True] * nq          # conservative default
    for q in range(nq):
        zflag[q] = False
    word_set = set()
    for q, nm in d['qname'].items():
        if nm.startswith('sel'):
            f[q] = VAR[int(nm[3:])]
        else:
            word_set.add(q)
            zflag[q] = True
    out: list[str] = []
    stat = dict(ccx_in=0, ccx_out=0, cx_in=0, cx_out=0, zero_ccx=0, zero_cx=0,
                cx1=0, cxN=0, skipped_z=0)
    for ln in lines:
        parts = ln.split()
        if not parts or parts[0] in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        op = parts[0]
        qs = [int(p[1:]) for p in parts[1:] if p.startswith('q')]
        if op == 'CCX':
            stat['ccx_in'] += 1
            a, b, t = qs
            tt = f[a] & f[b]
            ttm = tt & mask
            za, zb = zflag[a], zflag[b]
            if not za and not zb and ttm == 0:
                stat['zero_ccx'] += 1
                continue
            if not za and not zb and ttm:
                live = [q for q in range(nq)
                        if q != t and not zflag[q] and (f[q] & mask) == ttm]
                if live:
                    out.append(f'CX q{min(live)} q{t}')
                    stat['cx1'] += 1
                    stat['cx_out'] += 1
                    stat['ccx_out'] += 0
                    f[t] ^= tt
                    zflag[t] = False
                    continue
                combo = decompose(ttm)
                if combo is not None:
                    plan, ok = [], True
                    for j in range(len(gens)):
                        if not (combo >> j) & 1:
                            continue
                        gv = gens[j]
                        if gv == mask:
                            plan.append(('X', None))
                            continue
                        cand = [q for q in range(nq)
                                if q != t and not zflag[q] and (f[q] & mask) == gv]
                        if not cand:
                            ok = False
                            break
                        plan.append(('CX', min(cand)))
                    if ok:
                        for kind, u in plan:
                            out.append(f'X q{t}' if kind == 'X' else f'CX q{u} q{t}')
                            stat['cx_out'] += 1
                        stat['cxN'] += 1
                        f[t] ^= tt
                        zflag[t] = False
                        continue
            if za or zb:
                stat['skipped_z'] += 1
            out.append(ln)
            stat['ccx_out'] += 1
            f[t] ^= tt
            zflag[t] = za or zb
            if t in word_set:
                zflag[t] = True
        elif op == 'CX':
            stat['cx_in'] += 1
            a, t = qs[0], qs[1]
            if not zflag[a] and (f[a] & mask) == 0:
                stat['zero_cx'] += 1
                continue
            out.append(ln)
            stat['cx_out'] += 1
            f[t] ^= f[a]
            zflag[t] = zflag[t] or zflag[a]
            if t in word_set:
                zflag[t] = True
        elif op == 'X':
            out.append(ln)
            for q in qs:
                f[q] = ~f[q] & ALL
        elif op in ('R', 'HMR'):
            out.append(ln)
            for q in qs:
                f[q] = 0
                zflag[q] = False
        else:
            out.append(ln)
    text = '\n'.join(header + out) + '\n'
    return text, stat


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    tot_in = tot_out = 0
    for k in range(15):
        text, st = build(KMXDIR / f'angle_k_{k}.kmx')
        (OUTDIR / f'angle_k_{k}.kmx').write_text(text)
        tot_in += st['ccx_in']
        tot_out += st['ccx_out']
        print(f'k={k:2d} CCX {st["ccx_in"]:4d} -> {st["ccx_out"]:4d} '
              f'(saved {st["ccx_in"] - st["ccx_out"]:3d} = zeroCCX {st["zero_ccx"]:3d}'
              f' + cx1 {st["cx1"]:3d} + cxN {st["cxN"]:3d})  zeroCX {st["zero_cx"]:3d}'
              f'  kept-because-z {st["skipped_z"]:3d}')
    print(f'\nTOTAL CCX {tot_in} -> {tot_out}   (saved {tot_in - tot_out})')
    lam = 46.9074
    for T in (tot_in, tot_out):
        print(f'  T={T:5d} -> T_total={2 * T + 6662:6d} -> cost={lam * (2 * T + 6662) * 427 / 1e6:.2f}M')
    print(f'wrote {OUTDIR}')


if __name__ == '__main__':
    main()
