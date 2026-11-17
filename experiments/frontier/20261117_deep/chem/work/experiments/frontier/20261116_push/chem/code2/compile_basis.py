# Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
"""Loader compile with a rank-74 low basis (our own planner) + the v18 matching and emitter.

Per loader: (1) find five rank-74 blocks (minrank.find_basis) -> low basis B; (2) annihilators from
the 75 determined high slices in that basis; (3) rank-guided top-down cut selection to a perfect
pairing; (4) v18 matching -> explicit products, converted to physical low forms; (5) GF(2) solve for
the off-domain slice -> literal padding rows; (6) v18 emitter; (7) exact all-branch proofs.
"""
import sys, time, json, hashlib, random
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
V18 = ROOT
sys.path.insert(0, str(V18 / 'compiler'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'compiler'))
from planner import (BlockPlan, complete_words, cross_tensor, NDIM, basis, descend_path, descend_smart, physical_cuts,
                     solve_padding, padded_words, local_search)
from minrank import slices, find_basis, find_basis_generic
from lowbasis import inverse15, transform_target, to_physical
from extract_matching import matching
from emit_plan import emit
prove_one = None

PARTS5 = [[3 * i, 3 * i + 1, 3 * i + 2] for i in range(5)]
import os
LS_SECONDS = int(os.environ.get("LS_SECONDS", "45"))
SMART = True
PER_BLOCK = 10
STOP_AT = 145          # stop trying seeds once a plan with this many cuts (190 products) is found


def plan_one(target, seeds=(7,), trials=40, verbose=True, time_limit=600, generic=False):
    T = slices(target)
    best = None
    t0 = time.time()
    for seed in seeds:
        if time.time() - t0 > time_limit:
            break
        rng = random.Random(seed)
        rows = None
        for att in range(6):
            if generic or att >= 3:
                rows = find_basis_generic(T, rng, verbose=False, time_limit=120)
            else:
                rows = find_basis(T, rng, max_xy=6000)
            if rows is not None:
                break
        if rows is None:
            if verbose:
                print(f'   seed {seed}: no rank-74 basis found ({time.time()-t0:.0f}s)', flush=True)
            continue
        B = inverse15(rows)
        tt = transform_target(target, B)
        bp = BlockPlan(tt, PARTS5, [], per_coord=True, hmax=76)
        path = descend_smart(bp, seed=seed, per_block=PER_BLOCK, time_limit=600) if SMART else descend_path(bp, seed=seed, trials=trials)
        perfect = [c for c, (R, d, r) in path.items() if r == d and d % 2 == 0]
        if not perfect:
            if verbose:
                print(f'   seed {seed}: full {[len(f) for f in bp.full]} no perfect pairing on the descent path ({time.time()-t0:.0f}s)', flush=True)
            continue
        c = max(perfect)
        R, d, r = path[c]
        cuts = [list(bp.F[i]) + list(R[i]) for i in range(5)]
        if LS_SECONDS > 0:
            bp.best = cuts
            cuts = local_search(bp, cuts, seconds=LS_SECONDS, seed=seed + 3, verbose=False)
            c = sum(map(len, cuts)); d = NDIM - c
        phys = physical_cuts(PARTS5, cuts, Binv=rows)
        F = solve_padding(phys, target[76])
        if verbose:
            print(f'   seed {seed}: full {[len(f) for f in bp.full]} perfect at sum c {c} -> products {d // 2}; padding {"ok" if F is not None else "UNSOLVABLE"} ({time.time()-t0:.0f}s)', flush=True)
        if F is None:
            continue
        if best is None or c > best['sum_c']:
            best = {'sum_c': c, 'rows': rows, 'B': B, 'cuts': cuts, 'F': F, 'd': d}
        if best is not None and best['sum_c'] >= STOP_AT:
            break
    return best


def compile_one(W, k, outdir, seeds=(7, 8), trials=40, verbose=True, generic=False):
    Wc = complete_words(np.asarray(W, dtype=np.uint8))
    target = cross_tensor(Wc, k)
    if verbose:
        print(f'k{k}', flush=True)
    best = plan_one(target, seeds=seeds, trials=trials, verbose=verbose, generic=generic)
    if best is None:
        return None
    s_new = {'parts': PARTS5, 'cuts': best['cuts']}
    pairs, cert = matching(s_new)
    B = best['B']
    prods = [{'l1': int(to_physical(p[2], B)), 'l2': int(to_physical(p[3], B)), 'out': int(p[4])} for p in pairs]
    Wpad = padded_words(W, k, best['F'])
    prefix = hashlib.sha256(np.ascontiguousarray(np.asarray(W, dtype=np.uint8)).tobytes()).hexdigest()
    s = {'k': k, 'explicit_products': prods,
         'explicit_certificate': dict(cert, method='own planner: rank-74 low basis (MinRank kernel attack), 75-slice annihilators, '
                                      'rank-guided top-down cuts, v18 matching; off-domain slice by GF(2) padding solve',
                                      sum_cuts=int(best['sum_c']), low_basis_dual_rows=[int(x) for x in best['rows']]),
         'padding_completion': {'version': 1, 'first_unused_address': 1220, 'word_width': 75,
                                'words': Wpad[1220:].astype(int).tolist(), 'real_word_prefix_sha256': prefix}}
    outdir.mkdir(parents=True, exist_ok=True)
    kmx = outdir / f'angle_k_{k}.kmx'
    rep = emit(s, Wc, kmx)
    proofs = [prove_one(kmx, np.asarray(W, dtype=np.int64), k, rev) for rev in (False, True)]
    (outdir / f'angle_k_{k}.plan_state.json').write_text(json.dumps(s, indent=1) + '\n')
    res = {'k': k, 'products': rep['product_count'], 'toffoli': rep['toffoli_count'], 'qubits': rep['num_qubits'],
           'sum_cuts': int(best['sum_c']), 'proof_toffoli': proofs[0]['toffoli_count'], 'kmx_sha256': proofs[0]['source_sha256']}
    if verbose:
        print('COMPILED', json.dumps(res), flush=True)
    return res


if __name__ == '__main__':
    cand = np.load(ROOT / sys.argv[1])
    W = cand['words'] if 'words' in cand.files else cand['angle_words']
    outdir = ROOT / sys.argv[2]
    ks = [int(x) for x in sys.argv[3].split(',')]
    seeds = tuple(int(x) for x in sys.argv[4].split(',')) if len(sys.argv) > 4 else (7, 8)
    trials = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    out = []
    generic = len(sys.argv) > 6 and sys.argv[6] == 'generic'
    for k in ks:
        r = compile_one(W, k, outdir, seeds=seeds, trials=trials, generic=generic)
        out.append(r)
        (outdir / 'compile_summary.json').write_text(json.dumps(out, indent=1) + '\n')
