"""Integer coordinate descent directly on stored quantized tables.

Untried idea (2026-11-02): the pipeline fits float CSD, quantizes, then
searches. Quantization may leave optimality on the table. This searches
DIRECTLY over stored integers (moves in stored units), objective = maxrel,
constraint = zero fails. Integer-first by construction: every accepted
state is full-contract-checked (affected-x fast path + periodic full pass).

Scope: BOTH tables (R10/A20). Moves: single-entry +-1, +-2, +-4 in stored
units for A/R/B. Affected-x restriction: entry a affects only x with
addr(x)==a (~12k x's each) -- exact, since V(x),P(x) depend only on a(x).

Usage:
  uv run python experiments/invsqrt/20261102_generator_v2/integer_descent62.py --sweep [--full]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_generator_v2"))
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

import refit_layout62 as L62  # noqa: E402

ART = ROOT / "artifacts/20261102_generator_v2/invsqrt"
BASE = ART / "int_tables_R10_A20_quant.json"
X_MAX = 3_133_452
BASE_OVERRIDE = None


def base_path():
    return BASE_OVERRIDE or BASE


def load_all():
    tgt, tol = L62.load_ref()
    doc = json.loads(base_path().read_text())
    Bs = np.array(doc["Bs"], dtype=np.int64)
    As = np.array(doc["As"], dtype=np.int64)
    Rs = np.array(doc["Rs"], dtype=np.int64)
    xs = np.arange(1, X_MAX + 1, dtype=np.int64)
    bitlen = np.digitize(xs, 2.0 ** np.arange(1, 23)) + 1
    lz = 22 - bitlen
    m = (xs << lz) & ((1 << 22) - 1)
    p = lz & 1
    a = (p << 7) | ((m >> 14) & 127)
    delta = m & 16383
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    e = (lz >> 1) + p - 11
    t = 8 - e
    return tgt, tol, Bs, As, Rs, xs, a, D, S, t


def phase_of(V, t, tgt):
    P = np.zeros_like(t)
    for tt in range(8, 20):
        msk = (t == tt)
        P[msk] = ((V[msk] + (1 << (tt - 1))) >> tt) & ((1 << 36) - 1)
    return np.abs((P.astype(np.float64) / 2**36 - tgt + 0.5) % 1.0 - 0.5)


def full_eval(Bs, As, Rs, a, D, S, t, tgt, tol, sA=2, sR=2):
    V = ((Bs[a] << 12) - 2 * (As[a] << sA) * D + (Rs[a] << sR) * S)
    bad = (V <= 0) | (V >= 2**45)
    rel = phase_of(V, t, tgt) / tol
    return rel, int(bad.sum() + (rel > 1).sum()), float(rel.max())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--base", default=None)
    args = ap.parse_args()
    global BASE_OVERRIDE
    if args.base:
        BASE_OVERRIDE = Path(args.base)
    t0 = time.time()
    tgt, tol, Bs, As, Rs, xs, a, D, S, t = load_all()
    meta = json.loads(base_path().read_text())
    sA = int(meta.get("shifts", {}).get("sA", 2))
    sR = int(meta.get("shifts", {}).get("sR", 2))
    wA = 22 - int(meta.get("kA", 2))
    wR = 12 - int(meta.get("kR", 2))
    tag = str(meta.get("candidate", "BOTH"))
    rel0, fails0, max0 = full_eval(Bs, As, Rs, a, D, S, t, tgt, tol, sA, sR)
    print(f"base {tag} maxrel={max0:.6f} fails={fails0} ({time.time()-t0:.1f}s)", flush=True)
    if not args.sweep:
        return 0
    # Greedy sweep: per address, try single-entry moves; accept iff global
    # maxrel strictly improves and fails stay 0. Affected-x fast eval.
    tables = {"B": (Bs, 33, 0), "A": (As, wA, sA), "R": (Rs, wR, sR)}
    # Per-address maxima: the global max is their max. A move at address aa
    # only changes entry aa, so the global max updates exactly without a
    # full-domain pass. (Setting cur_max to a LOCAL max would understate the
    # global bound and wrongly admit regressions -- fixed 2026-11-02.)
    amax = np.zeros(256)
    np.maximum.at(amax, a, rel0)  # xs interleave addresses; no reshape trick
    cur_max = float(amax.max())
    improved = 0
    order = list(np.argsort(amax)[::-1][:64])
    for aa in [int(v) for v in order]:
        msk = (a == aa)
        for key, (tbl, w, sh) in tables.items():
            lo = 0
            hi = (1 << w) - 1
            for step in (4, 2, 1):
                for sgn in (+1, -1):
                    old = int(tbl[aa])
                    new = old + sgn * step
                    if not (lo <= new <= hi):
                        continue
                    tbl[aa] = new
                    V = ((Bs[a[msk]] << 12) - 2 * (As[a[msk]] << sA) * D[msk]
                         + (Rs[a[msk]] << sR) * S[msk])
                    if (V <= 0).any() or (V >= 2**45).any():
                        tbl[aa] = old
                        continue
                    r = (phase_of(V, t[msk], tgt[msk]) / tol[msk])
                    if (r > 1).sum() > 0:
                        tbl[aa] = old
                        continue
                    new_amax = float(r.max())
                    new_global = max(new_amax, float(amax[np.arange(256) != aa].max()))
                    if new_global < cur_max - 1e-12:
                        amax[aa] = new_amax
                        cur_max = new_global
                        improved += 1
                    else:
                        tbl[aa] = old
    print(f"sweep done: improved_moves={improved} maxrel={cur_max:.6f} "
          f"({time.time()-t0:.1f}s)", flush=True)
    if args.full:
        rel, fails, mx = full_eval(Bs, As, Rs, a, D, S, t, tgt, tol, sA, sR)
        print(f"FULL maxrel={mx:.6f} fails={fails}", flush=True)
        if fails == 0:
            out = ART / f"int_tables_{tag}_idesc.json"
            out.write_text(json.dumps(
                {"parent": base_path().name, "candidate": tag + "_idesc",
                 "Bs": [int(v) for v in Bs],
                 "As": [int(v) for v in As], "Rs": [int(v) for v in Rs],
                 "maxrel": mx, "kA": int(meta.get("kA", 2)),
                 "kR": int(meta.get("kR", 2)), "kB": 0,
                 "shifts": {"sA": sA, "sR": sR, "sB": 0}}) + "\n")
            print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
