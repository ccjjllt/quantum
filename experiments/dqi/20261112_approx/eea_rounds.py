"""How many EEA rounds does an actual DQI syndrome need? (classical, read-only)

Quantifies option "truncate the EEA / short-Hankel round count": if the decoder
stops after D division steps, it fails on every shot whose key-equation EEA needs
more than D steps.  We draw syndromes exactly as the verifier does (k errors,
uniform positions/values, k ~ p(k) = w_k^2) and run the standard RS key-equation
EEA on (x^70, S(x)) over GF(2^12), counting division steps and field mults.

Usage: .venv/bin/python experiments/dqi/20261112_approx/eea_rounds.py
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT / 'data/competition/verifiers/dqi'))
from verify_submission_dqi import ProblemSpecDQI, optimal_dqi_weights  # noqa: E402

MOD = 0x1053  # GF(2^12) modulus used by kickmix.GF2Field(12)
ORDER = (1 << 12) - 1
LOG = [0] * (1 << 12)
ANTILOG = [0] * ORDER


def build_tables() -> None:
    a = 1
    for e in range(ORDER):
        ANTILOG[e] = a
        LOG[a] = e
        a <<= 1
        if a & (1 << 12):
            a ^= MOD


def gmul(a: int, b: int, cnt: list[int]) -> int:
    cnt[0] += 1
    if a == 0 or b == 0:
        return 0
    return ANTILOG[(LOG[a] + LOG[b]) % ORDER]


def ginv(a: int) -> int:
    assert a
    return ANTILOG[(ORDER - LOG[a]) % ORDER]


def degree(p: list[int]) -> int:
    for i in range(len(p) - 1, -1, -1):
        if p[i]:
            return i
    return -1


def eea_steps(a: list[int], b: list[int], cnt: list[int]) -> int:
    """Euclid over GF(2^12)[x]; returns the number of division steps."""
    a, b = a[:], b[:]
    steps = 0
    while degree(b) >= 0:
        db = degree(b)
        inv = ginv(b[db])
        while degree(a) >= db:
            da = degree(a)
            coef = gmul(a[da], inv, cnt)
            shift = da - db
            if coef:
                for i in range(db + 1):
                    if b[i]:
                        a[i + shift] ^= gmul(coef, b[i], cnt)
            else:
                a[da] = 0
        a, b = b, a
        steps += 1
    return max(0, steps - 1)


def syndrome(rng: random.Random, k: int, spec: ProblemSpecDQI) -> list[int]:
    pos = rng.sample(range(spec.m), k)
    vals = [rng.randrange(1, 1 << 12) for _ in range(k)]
    out = []
    for i in range(1, spec.n + 1):
        acc = 0
        for p, v in zip(pos, vals):
            acc ^= ANTILOG[(LOG[v] + i * p) % ORDER]
        out.append(acc)
    return out


def main() -> None:
    build_tables()
    spec = ProblemSpecDQI.benchmark_instance()
    w = optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r)
    probs = (w ** 2).tolist()
    rng = random.Random(20261112)
    cnt = [0]
    hist = collections.Counter()
    trials = 300
    for _ in range(trials):
        k = rng.choices(range(len(probs)), weights=probs)[0]
        S = syndrome(rng, k, spec)
        c0 = cnt[0]
        steps = eea_steps([0] * 70 + [1], S, cnt)
        hist[steps] += 1
    total = sum(hist.values())
    print(f'EEA division steps on {trials} real syndromes (x^70 vs S(x), GF(2^12)[x])')
    print(f"{'steps':>6} {'count':>6} {'P(need>steps)':>14} {'P(need<=steps)':>15}")
    rows = []
    cum = 0
    for s in range(min(hist), max(hist) + 1):
        c = hist.get(s, 0)
        cum += c
        rows.append({'steps': s, 'count': c, 'p_exceed': 1 - cum / total})
        print(f"{s:>6} {c:>6} {1-cum/total:>14.4f} {cum/total:>15.4f}")
    print(f'range {min(hist)}..{max(hist)} steps; plain-Euclid field mults ~{cnt[0]/trials:.0f}/instance')
    print('reading: fixing the depth at D keeps p = P(steps > D) = the last column entry.')
    dest = Path(__file__).parent / 'results'
    dest.mkdir(exist_ok=True)
    (dest / 'eea_rounds.json').write_text(json.dumps(
        {'trials': trials, 'rows': rows, 'min': min(hist), 'max': max(hist),
         'mults_per_instance': cnt[0] / trials}, indent=1) + '\n')


if __name__ == '__main__':
    main()
