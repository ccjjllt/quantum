"""Step 1: verify the shipped DQI tensors and census the extension/Toom construction family.

Usage: .venv/bin/python artifacts/20261112_mulrank/census.py
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE.parents[2] / 'artifacts' / '20261112_mulrank'
SRC = ART / 'source_copy'
sys.path[:0] = [str(HERE), str(SRC / 'playbook/kit/decoder'), str(SRC / 'playbook/kit/decoder/exp/arithmetic')]

import mulmath as mm
import field as ar
from exp.mul99.kernels import tensor99   # noqa: E402


def main():
    out = {}
    t0 = time.time()

    # ---- existing tensors -------------------------------------------------
    t12 = ar.tensor(12)
    t99 = tensor99()
    f12 = mm.F(12)
    f24 = mm.F(24)

    ok, bad = mm.check_basis_pairs(f12.f, t12, 12)
    print(f'tensor(12): {len(t12)} terms, basis-pair proof: {ok} {bad}')
    out['tensor12'] = dict(terms=len(t12), basis_pairs_ok=ok)

    ok, bad = mm.check_basis_pairs(f24.f, t99, 24)
    print(f'tensor99:   {len(t99)} terms, basis-pair proof: {ok} {bad}')
    out['tensor99'] = dict(terms=len(t99), basis_pairs_ok=ok)

    t = time.time()
    ok, n_checked = mm.verify_exhaustive(f12, t12, 12)
    print(f'tensor(12) exhaustive {n_checked} inputs: {ok} {n_checked if not ok else ""}'
          f'  ({time.time()-t:.1f}s)')
    out['tensor12']['exhaustive'] = dict(ok=ok, count=int(n_checked) if not isinstance(n_checked, tuple) else 0)

    # structured sets for n=24
    q = 1 << 24
    rng_all = mm.np.arange(4096, dtype=mm.np.int64)
    extra = []
    a, b = mm.np.meshgrid(rng_all, rng_all, indexing='ij')
    extra.append((a.ravel(), b.ravel()))                       # all x,y < 2^12
    r = mm.np.random.default_rng(7).integers(0, q, 2_000_000)
    extra.append((r, r))                                       # squares
    extra.append((mm.np.arange(q, dtype=mm.np.int64)[::128],
                  mm.np.zeros(q // 128 + (1 if q % 128 else 0), dtype=mm.np.int64)))  # y=0
    t = time.time()
    ok, n_checked, bad = mm.verify_random(f24, t99, 24, count=1_000_000, seed=11, extra=extra)
    print(f'tensor99 random+structured {n_checked} inputs: {ok} {bad}  ({time.time()-t:.1f}s)')
    out['tensor99']['random'] = dict(ok=ok, count=int(n_checked))

    # ---- census over the (k,d) extension family --------------------------
    # term count of a (k,d) plan = (2d-1) * terms(GF(2^k)), recursively.
    @mm.lru_cache(None)
    def best_plan(n):
        """Minimal term count over all valid Toom/extension plans for GF(2^n)."""
        if n == 1:
            return 1, 'base'
        if n == 2:
            return 3, 'quadratic (3)'
        if n == 3:
            return 6, 'explicit GF(8) tensor (6)'
        best = None
        for k in range(1, n):
            if n % k:
                continue
            d = n // k
            if 2 ** k < 2 * d - 2:   # 2d-2 real points plus the leading coefficient
                continue
            sub, _ = best_plan(k)
            if sub is None:
                continue
            cnt = (2 * d - 1) * sub
            if best is None or cnt < best[0]:
                best = (cnt, f'd={d} over GF(2^{k}) [{2*d-1} points] x {sub}')
        return best if best else (None, 'impossible')

    census = {}
    for n in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 20, 24):
        cnt, why = best_plan(n)
        census[n] = dict(terms=cnt, plan=why)
        print(f'GF(2^{n:<2d}): best extension plan = {cnt} terms   ({why})')
    out['census'] = census

    # concrete validation of each plan that changes the shipped one
    checks = {}
    for (n, k, d) in [(12, 3, 4), (12, 4, 3), (12, 6, 2), (24, 4, 6), (24, 6, 4)]:
        subterms = ar.tensor(k) if k in (2, 3, 6, 12) else None
        if subterms is None:
            continue
        terms, why = mm.extension_tensor_generic(n, k, d, subterms)
        if terms is None:
            print(f'GF(2^{n}) d={d} over GF(2^{k}): {why}')
            checks[f'{n}/{k}/{d}'] = dict(terms=None, why=why)
            continue
        ok, bad = mm.check_basis_pairs(mm.F(n).f, terms, n)
        print(f'GF(2^{n}) d={d} over GF(2^{k}): {len(terms)} terms, proof {ok} {bad}')
        checks[f'{n}/{k}/{d}'] = dict(terms=len(terms), ok=ok)
    out['concrete'] = checks

    (ART / 'census.json').write_text(json.dumps(out, indent=1) + '\n')
    print(f'wrote census.json  ({time.time()-t0:.1f}s total)')


if __name__ == '__main__':
    main()
