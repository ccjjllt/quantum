"""Approximate-decoding / approximate-multiplier frontier for DQI (read-only analysis).

Two questions:
  A. eps -> R -> allowed T.  eps_plus is a Clopper-Pearson upper bound at
     delta = 2^-128 over 102,400 shots, so eps is quantised by the failure count k.
     Includes the "how much T does one failure buy" frontier.
  B. Approximate GF(2^12) multiplier: take the real 42-term `mul_xor0` tensor,
     drop terms (rank 36 / 30), compute the EXACT probability that a call returns a
     wrong product, and the implied per-shot failure rate.

Run:
  .venv/bin/python experiments/dqi/20261112_approx/approx_frontier.py
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers/dqi'))
from verify_submission_dqi import (  # noqa: E402
    ProblemSpecDQI,
    clopper_pearson_upper_bound,
    optimal_dqi_weights,
    repetition_overhead,
)

N_SHOTS = 102_400
LOG2_DELTA = -128.0
R0 = 1.1912604648115832          # eae396ba, 0/0 failures
Q0 = 892
STATIC0 = 401_313
MEAN0 = 394_089.2726757813
RATIO = MEAN0 / STATIC0
GM0 = 25.40482
COST0 = R0 * Q0 ** 2 * MEAN0
FIELD_PY = ROOT / 'artifacts/20261112_frontier/build_v3/source/playbook/kit/decoder/exp/arithmetic/field.py'


def gm_of(cost: float) -> float:
    return GM0 + 20.0 * math.log10(COST0 / cost)


def cost_of(mean_t: float, rep: float = R0) -> float:
    return rep * Q0 ** 2 * mean_t


# ---------------------------------------------------------------- part A: eps -> T

def part_a(out: dict) -> None:
    rows = []
    for k in [0, 1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 50, 62, 80, 100, 135, 150, 200, 300]:
        e = clopper_pearson_upper_bound(k, N_SHOTS, LOG2_DELTA)
        rep = repetition_overhead(e)
        # mean T allowed so that cost stays at COST0 (net zero) at this R
        t_zero = MEAN0 * R0 / rep
        rows.append({
            'k': k, 'eps_plus': e, 'R': rep, 'dR_pct': 100 * (rep / R0 - 1),
            'meanT_for_net_zero': t_zero,
            'meanT_for_net_-10pct': 0.90 * t_zero,
            'meanT_for_net_-16.7pct': 0.833 * t_zero,
            'meanT_for_net_-20pct': 0.80 * t_zero,
        })
    out['eps_table'] = rows
    print('A1  k failures out of 102,400 (delta=2^-128)')
    print(f"{'k':>4} {'eps_plus':>11} {'R':>8} {'dR%':>6} {'meanT net0':>11} "
          f"{'-10%':>9} {'-16.7%':>9} {'-20%':>9}")
    for r in rows:
        print(f"{r['k']:>4} {r['eps_plus']:>11.3e} {r['R']:>8.4f} {r['dR_pct']:>+6.2f} "
              f"{r['meanT_for_net_zero']:>11,.0f} {r['meanT_for_net_-10pct']:>9,.0f} "
              f"{r['meanT_for_net_-16.7pct']:>9,.0f} {r['meanT_for_net_-20pct']:>9,.0f}")

    # inverse frontier: given a per-shot failure probability p, what net saving is reachable?
    print('\nA2  net saving reachable vs per-shot failure probability p (N*p failures expected)')
    fr = []
    for p in [0.0, 1e-6, 1e-5, 1e-4, 3e-4, 6e-4, 1e-3, 1.3e-3, 3e-3, 1e-2, 3e-2, 1e-1]:
        k = p * N_SHOTS
        e = clopper_pearson_upper_bound(int(round(k)), N_SHOTS, LOG2_DELTA)
        if e >= 1 / 16:
            fr.append({'p': p, 'k': k, 'eps_plus': e, 'max_net_saving': None, 'note': 'FAIL (eps>=1/16)'})
            continue
        rep = repetition_overhead(e)
        fr.append({'p': p, 'k': k, 'eps_plus': e, 'R': rep,
                   'r_penalty_pct': 100 * (rep / R0 - 1)})
        print(f"p={p:>8.1e}  E[k]={k:>8.1f}  eps={e:.3e}  R={rep:.4f}  "
              f"R penalty={100*(rep/R0-1):>+6.2f}%  (T must beat this)")
    out['p_frontier'] = fr

    # the user's targets at R = 1.1967 (k=1) and at R0
    print('\nA3  static T required at Q=892 (mean = static*0.98200)')
    tg = []
    for name, rep, cost in [
        ('GM 27.0', repetition_overhead(clopper_pearson_upper_bound(1, N_SHOTS, LOG2_DELTA)), 311.15e9),
        ('GM 28.0', repetition_overhead(clopper_pearson_upper_bound(1, N_SHOTS, LOG2_DELTA)), 279.0e9),
        ('GM 29.76', repetition_overhead(clopper_pearson_upper_bound(1, N_SHOTS, LOG2_DELTA)), 232.3e9),
    ]:
        mean_t = cost / (rep * Q0 ** 2)
        tg.append({'target': name, 'R': rep, 'meanT': mean_t, 'staticT': mean_t / RATIO,
                   'save_pct': 100 * (1 - mean_t / MEAN0)})
        print(f"{name:>9}  R={rep:.4f}  meanT<={mean_t:,.0f}  staticT<={mean_t/RATIO:,.0f}  "
              f"= {100*(1-mean_t/MEAN0):.1f}% below eae")
    out['targets'] = tg


# ------------------------------------------------- part B: approximate multiplier

def load_tensor_terms():
    """Return the 42 (mask, value) rank-one terms of the real 12-bit mul_xor0."""
    import importlib.util
    import kickmix
    sys.modules.setdefault('circ', kickmix)   # public tree imports kickmix as `circ`
    spec = importlib.util.spec_from_file_location('pubfield', FIELD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    terms = list(mod.tensor(12))
    assert len(terms) == 42, len(terms)
    assert all(v for _, v in terms)
    return terms


def rank_gf2(rows: list[int]) -> int:
    piv = {}
    r = 0
    for row in rows:
        while row:
            p = (row & -row).bit_length() - 1
            if p in piv:
                row ^= piv[p]
            else:
                piv[p] = row
                r += 1
                break
    return r


def err_prob_exact(terms, drop: set[int]) -> float:
    """Exact P(E(x,y) != 0) for E = sum_{i in drop} v_i (a_i.x)(a_i.y), x,y uniform in GF(2)^12.

    For fixed x: E(.,y) = N_x y with N_x = sum_i [a_i.x] v_i a_i^T  (12x12 over GF(2)).
    P_y(E != 0 | x) = 1 - 2^-rank(N_x).
    """
    mats = []
    for i in drop:
        mask, v = terms[i]
        cols = [v if (mask >> j) & 1 else 0 for j in range(12)]   # v * a_i^T : column j
        rows = []
        for b in range(12):
            row = 0
            for j in range(12):
                if (cols[j] >> b) & 1:
                    row |= 1 << j
            rows.append(row)
        mats.append((mask, rows))
    tot = 0.0
    for x in range(1 << 12):
        acc = [0] * 12
        for mask, rows in mats:
            if bin(mask & x).count('1') & 1:
                for b in range(12):
                    acc[b] ^= rows[b]
        tot += 1.0 - 2.0 ** (-rank_gf2(acc))
    return tot / (1 << 12)


def err_prob_sample(terms, drop: set[int], n: int = 200_000) -> float:
    rng = random.Random(12345)
    bad = 0
    for _ in range(n):
        x = rng.getrandbits(12)
        y = rng.getrandbits(12)
        e = 0
        for i in drop:
            mask, v = terms[i]
            if (bin(mask & x).count('1') & 1) and (bin(mask & y).count('1') & 1):
                e ^= v
        bad += e != 0
    return bad / n


def part_b(out: dict) -> None:
    terms = load_tensor_terms()
    print('\nB1  the real mul_xor0 tensor: 42 rank-one terms, all v != 0')
    print('    P(single dropped term errs on a uniform call) = 1/4 exactly, e.g.:')
    checks = []
    for i in [0, 7, 41]:
        p_ex = err_prob_exact(terms, {i})
        p_sm = err_prob_sample(terms, {i})
        checks.append({'drop': [i], 'exact': p_ex, 'sample': p_sm})
        print(f"    drop term {i:2d}: exact {p_ex:.6f}  sampled {p_sm:.6f}")
    out['single_term'] = checks

    rng = random.Random(7)
    subs = [set(rng.sample(range(42), 6)) for _ in range(12)]
    res = []
    print('\nB2  rank-36 candidates (drop 6 of 42), exact error probability per call')
    for s in subs:
        p = err_prob_exact(terms, s)
        res.append({'drop': sorted(s), 'p_call': p})
        print(f"    drop {sorted(s)} -> p_call = {p:.4f}")
    ps = [r['p_call'] for r in res]
    print(f"    min {min(ps):.4f}  median {sorted(ps)[len(ps)//2]:.4f}  max {max(ps):.4f}")
    out['rank36'] = {'candidates': res, 'min': min(ps), 'max': max(ps)}
    print('    theoretical floor for ANY nonzero bilinear error form: 1/4 (>=1/2 in practice).')

    r30 = [set(rng.sample(range(42), 12)) for _ in range(3)]
    r30ps = []
    print('\nB2b rank-30 candidates (drop 12 of 42), exact error probability per call')
    for s in r30:
        p = err_prob_exact(terms, s)
        r30ps.append(p)
        print(f"    drop 12 of 42 -> p_call = {p:.4f}")
    out['rank30'] = {'candidates': [sorted(s) for s in r30], 'p_call': r30ps}

    # per-shot failure for a single approximate block, and for the whole circuit
    print('\nB3  per-shot failure if a multiplier is approximated')
    blocks = {'one block (1 call/shot)': 1, 'convert only (1,196 calls)': 1196,
              'all GF12 blocks (~5,900 calls)': 5900}
    rows = []
    for name, ncall in blocks.items():
        for p in (0.25, min(ps), 0.5):
            eps = 1 - (1 - p) ** ncall
            k = eps * N_SHOTS
            ep = clopper_pearson_upper_bound(int(round(k)), N_SHOTS, LOG2_DELTA)
            rows.append({'case': name, 'p_call': p, 'eps_shot': eps,
                         'expected_failures': k, 'eps_plus': ep,
                         'verdict': 'FAIL (eps_plus>=1/16)' if ep >= 1 / 16 else 'scored'})
            print(f"    {name:>32}  p={p:.4f} -> eps_shot={eps:.3e}  "
                  f"E[failures]={k:>9.0f}  eps_plus={ep:.3f}  {'FAIL' if ep>=1/16 else 'ok'}")
    out['per_shot'] = rows

    # T ceiling of the whole idea, even if every error were free.
    # Motif census (eae_blocks.json): 288,868 motifs total, minus 390 x 99 (GF(2^24)),
    # minus ~135 x 15 (6-bit) -> ~5,910 GF(2^12) multiply occurrences (1 term = 1 T).
    # The tag census in 20261112_branch_recovery found only 3,406 blocks; it is a
    # known undercount (v21: 3,406 tag vs 5,183 instrumented).
    gf12_blocks = 5910
    print('\nB4  T ceiling of rank truncation (even with ZERO error cost)')
    print(f'    GF(2^12) multiply occurrences = {gf12_blocks} (motif census; tag census 3,406 is low)')
    rows = []
    for rank in (36, 30, 23):
        d12 = (42 - rank) * gf12_blocks
        rows.append({'rank': rank, 'blocks': gf12_blocks, 'saved_GF12': d12,
                     'pct_total': 100 * d12 / STATIC0})
        print(f"    GF(2^12) rank {rank:2d}: -{d12:>6,} T = -{100*d12/STATIC0:.2f}% of 401,313 "
              f"(GF24 untouched)")
    out['rank_t_ceiling'] = rows


# ------------------------------------------------------------- part C: weight pdf

def part_c(out: dict) -> None:
    sp = ProblemSpecDQI.benchmark_instance()
    w = optimal_dqi_weights(sp.m, sp.max_errors, sp.degree, sp.r)
    p = w ** 2
    print('\nC1  verifier error-weight distribution p(k) = w_k^2 (m=4095, l=35)')
    rows = []
    for k in range(36):
        rows.append({'k': k, 'p': float(p[k]), 'tail_ge_k': float(p[k:].sum()),
                     'expected_shots_ge_k': float(N_SHOTS * p[k:].sum())})
    for k in (0, 20, 25, 28, 30, 31, 33, 34, 35):
        r = rows[k]
        print(f"    k={k:>2}  p={r['p']:.4e}  P(K>=k)={r['tail_ge_k']:.4e}  "
              f"E[shots with K>=k]={r['expected_shots_ge_k']:,.2f}")
    out['weight_pdf'] = rows
    print('    -> 93.6% of shots have k in 28..35; the RARE end is LOW weight '
          f"(P(k<=18)={p[:19].sum():.2e} = {N_SHOTS*p[:19].sum():.2f} shots).")


def main() -> None:
    out = {}
    part_a(out)
    part_b(out)
    part_c(out)
    dest = Path(__file__).parent / 'results'
    dest.mkdir(exist_ok=True)
    (dest / 'approx_frontier.json').write_text(json.dumps(out, indent=1) + '\n')
    print('\nwrote', dest / 'approx_frontier.json')


if __name__ == '__main__':
    main()
