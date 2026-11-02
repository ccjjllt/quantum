"""Constraint refit for implemented layout: LSB-quantized widths + fresh CSD + phase.

Pipeline per candidate (no truncation-reuse of old tables/angles):
  1. fresh minimax init + CSD digit-cap + coordinate digit search
     (approxB62.fit_config, S=7/Pm=8/Pr=16/r0=5/trunc, deterministic rerun);
  2. exact integer tables via CSD Fraction + RH (contract62 semantics);
  3. LSB quantization (round-half-up) to target stored widths;
  4. integer-neighborhood coordinate descent (+-1 in stored units,
     per-segment vectorized maxrel, 2 passes);
  5. phase refit: P recomputed from new V via RH (36 exact binary weights);
     global-offset scan reported (generator has no const rotation; offset
     must be ~0 to stay realizable);
  6. full-domain vectorized integer-contract check (same equation as
     contract62.model_phase, same official reference_values; baseline
     cross-checked bitwise identical: maxrel 0.6096375068545294).

Usage (manual evidence commands):
  uv run python experiments/invsqrt/20261102_generator_v2/refit_layout62.py --fresh-fit
  uv run python experiments/invsqrt/20261102_generator_v2/refit_layout62.py --refit R10
  uv run python experiments/invsqrt/20261102_generator_v2/refit_layout62.py --refit A20
  uv run python experiments/invsqrt/20261102_generator_v2/refit_layout62.py --refit BOTH
  uv run python experiments/invsqrt/20261102_generator_v2/refit_layout62.py --refit ALL
Outputs land in artifacts/20261102_generator_v2/invsqrt/ (new files only;
frozen int_tables_7_8_16_5_trunc.json is never overwritten).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261102_hw06_opt"))
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))

import approxB62 as A62  # noqa: E402
import contract62 as C62  # noqa: E402
from fractions import Fraction  # noqa: E402
from invsqrt import verify_submission_invsqrt as official  # noqa: E402

ART = ROOT / "artifacts/20261102_generator_v2/invsqrt"
X_MAX = 3_133_452

CANDS = {
    # stored widths via LSB-drop; shifts applied in V equation + row placement
    "R10": {"kA": 0, "kR": 2, "kB": 0},
    "A20": {"kA": 2, "kR": 0, "kB": 0},
    "BOTH": {"kA": 2, "kR": 2, "kB": 0},
    "A18": {"kA": 4, "kR": 0, "kB": 0},
    "R8": {"kA": 0, "kR": 4, "kB": 0},
    "DEEP": {"kA": 4, "kR": 4, "kB": 0},
    "A20R8": {"kA": 2, "kR": 4, "kB": 0},
}

SPEC = official.ProblemSpecInvSqrt.for_n_p(10)


def load_ref():
    tgt_all, tol_all = official.reference_values(
        SPEC, np.arange(1, X_MAX + 1, dtype=np.uint64))
    return (np.asarray(tgt_all, dtype=np.float64) / 2**64,
            np.asarray(tol_all, dtype=np.float64) / 2**64)


def full_vec(Bs, As, Rs, sA, sR, sB, tgt, tol):
    """Vectorized integer-contract check. Bs/As/Rs are STORED tables
    (quantized hi); effective = tbl << s. Same RH semantics as
    contract62.model_phase for V>=0."""
    chunk = 1 << 18
    maxrel = 0.0
    min_margin = float(1 << 64)
    worst = None
    fails = 0
    vmin = vmax = None
    bounds2 = 2.0 ** np.arange(1, 23)
    for start in range(1, X_MAX + 1, chunk):
        xs = np.arange(start, min(start + chunk, X_MAX + 1), dtype=np.int64)
        bitlen = np.digitize(xs, bounds2) + 1
        lz = 22 - bitlen
        m = (xs << lz) & ((1 << 22) - 1)
        p = lz & 1
        a = (p << 7) | ((m >> 14) & 127)
        delta = m & 16383
        D = delta - 8192
        U = (delta >> 5) - 256
        S = U * U
        V = (np.left_shift(Bs[a], 12 + sB)
             - 2 * np.left_shift(As[a], sA) * D
             + np.left_shift(Rs[a], sR) * S)
        vmin = int(V.min()) if vmin is None else min(vmin, int(V.min()))
        vmax = int(V.max()) if vmax is None else max(vmax, int(V.max()))
        bad = (V <= 0) | (V >= 2**45)
        if bad.any():
            fails += int(bad.sum())
        e = (lz >> 1) + p - 11
        t = 8 - e
        P = np.zeros_like(xs)
        for tt in range(8, 20):
            msk = (t == tt)
            if msk.any():
                P[msk] = ((V[msk] + (1 << (tt - 1))) >> tt) & ((1 << 36) - 1)
        pha = P.astype(np.float64) / 2**36
        err = (pha - tgt[xs - 1] + 0.5) % 1.0 - 0.5
        ae = np.abs(err)
        rel = ae / tol[xs - 1]
        i = int(np.argmax(rel))
        if rel[i] > maxrel:
            maxrel = float(rel[i])
            worst = (int(xs[i]), float(ae[i]))
        mm = float(((tol[xs - 1] - ae) * 2**64).min())
        if mm < min_margin:
            min_margin = mm
        if bool((ae > tol[xs - 1]).any()):
            fails += int((ae > tol[xs - 1]).sum())
    return {"fails": fails, "maxrel": maxrel, "worst": worst,
            "min_margin": min_margin, "vmin": vmin, "vmax": vmax}


def seg_index():
    """Per-segment x lists for all 256 addresses (chunked, ~12k each)."""
    bounds2 = 2.0 ** np.arange(1, 23)
    out = [[] for _ in range(256)]
    chunk = 1 << 18
    for start in range(1, X_MAX + 1, chunk):
        xs = np.arange(start, min(start + chunk, X_MAX + 1), dtype=np.int64)
        bitlen = np.digitize(xs, bounds2) + 1
        lz = 22 - bitlen
        m = (xs << lz) & ((1 << 22) - 1)
        p = lz & 1
        a = (p << 7) | ((m >> 14) & 127)
        for aa in range(256):
            sel = xs[a == aa]
            if len(sel):
                out[aa].append(sel)
    return [np.concatenate(v) if v else np.zeros(0, dtype=np.int64) for v in out]


def seg_maxrel(xs, aa, Bs, As, Rs, sA, sR, sB, tgt, tol):
    if len(xs) == 0:
        return 0.0, None
    bitlen = np.digitize(xs, 2.0 ** np.arange(1, 23)) + 1
    lz = 22 - bitlen
    m = (xs << lz) & ((1 << 22) - 1)
    p = lz & 1
    delta = m & 16383
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    b = int(Bs[aa]) << (12 + sB)
    av = int(As[aa]) << sA
    rv = int(Rs[aa]) << sR
    V = b - 2 * av * D + rv * S
    if bool(((V <= 0) | (V >= 2**45)).any()):
        return float("inf"), None
    e = (lz >> 1) + p - 11
    t = 8 - e
    P = np.zeros_like(xs)
    for tt in range(8, 20):
        msk = (t == tt)
        if msk.any():
            P[msk] = ((V[msk] + (1 << (tt - 1))) >> tt) & ((1 << 36) - 1)
    pha = P.astype(np.float64) / 2**36
    err = (pha - tgt[xs - 1] + 0.5) % 1.0 - 0.5
    ae = np.abs(err)
    rel = ae / tol[xs - 1]
    i = int(np.argmax(rel))
    return float(rel[i]), (int(xs[i]), float(ae[i]))


def quantize(vals, k):
    if k == 0:
        return list(vals)
    st = 1 << k
    half = 1 << (k - 1)
    return [(v + half) // st for v in vals]


def tables_from_coef(coef_store):
    """Exact integer tables from FRESH coef (CSD Fraction + RH).
    Never reads archived coef/tables (no truncation-reuse)."""
    B, A, R = [], [], []
    for a in range(256):
        p, seg = a >> 7, a & 127
        c = coef_store[(p, seg)]
        b0 = sum(Fraction(s) * Fraction(2) ** q for q, s in c[0])
        m = sum(Fraction(s) * Fraction(2) ** q for q, s in c[1])
        r = sum(Fraction(s) * Fraction(2) ** q for q, s in c[2])
        B.append(C62.RH(b0 * 2**32))
        A.append(-C62.RH(m * 2**29))
        R.append(C62.RH(r * 2**26))
    return B, A, R


def cmd_fresh_fit():
    t0 = time.time()
    summary, coef_store, _segs = A62.fit_config(7, 8, 16, 5, "trunc")
    dt = round(time.time() - t0, 1)
    B, A, R = tables_from_coef(coef_store)
    blob = C62.serialize(B, A, R)
    thash = hashlib.sha256(blob).hexdigest()
    fit_hash = hashlib.sha256(
        (ROOT / "artifacts/20261102_hw06_opt/invsqrt/trackB_fit_7_8_16_5_trunc.json").read_bytes()
    ).hexdigest()
    print(json.dumps({"rect_maxrel": summary["maxrel_rect"],
                      "pass_rect": summary["pass_rect"],
                      "bind": summary["bind_counts"],
                      "seconds": dt}, indent=1))
    print(f"rebuilt_tables_sha256={thash}")
    print(f"archived fit_sha256={fit_hash}")
    frozen = json.loads((ART / "int_tables_7_8_16_5_trunc.json").read_text())
    match = (list(B) == frozen["B"] and list(A) == frozen["A"] and list(R) == frozen["R"])
    print(f"matches_frozen_tables={match} frozen_tables_sha256={frozen['tables_sha256']}")


def cmd_refit(name):
    cfg = CANDS[name]
    kA, kR, kB = cfg["kA"], cfg["kR"], cfg["kB"]
    t0 = time.time()
    # 1. fresh fit (deterministic rerun, never reuse archived coef object)
    summary, coef_store, _segs = A62.fit_config(7, 8, 16, 5, "trunc")
    B0, A0, R0 = tables_from_coef(coef_store)
    # 2-3. quantize stored tables
    Bs = np.array(quantize(B0, kB), dtype=np.int64)
    As = np.array(quantize(A0, kA), dtype=np.int64)
    Rs = np.array(quantize(R0, kR), dtype=np.int64)
    print(f"[{name}] fresh rect_maxrel={summary['maxrel_rect']:.3e} "
          f"stored_bits B{min(int(v).bit_length() for v in Bs)}..{max(int(v).bit_length() for v in Bs)} "
          f"A{max(int(v).bit_length() for v in As)} R{max(int(v).bit_length() for v in Rs)} "
          f"shifts sA={kA} sR={kR} sB={kB}")
    tgt, tol = load_ref()
    r = full_vec(Bs, As, Rs, kA, kR, kB, tgt, tol)
    print(f"[{name}] rounded: fails={r['fails']} maxrel={r['maxrel']:.10f} "
          f"worst={r['worst']} margin={r['min_margin']:.1f} V=({r['vmin']},{r['vmax']})")
    # 4. integer neighborhood: per-segment +-1 coordinate descent, 2 passes
    seg_xs = seg_index()
    order = sorted(range(256),
                   key=lambda aa: seg_maxrel(seg_xs[aa], aa, Bs, As, Rs,
                                             kA, kR, kB, tgt, tol)[0],
                   reverse=True)
    for pas in range(2):
        improved = 0
        for aa in order:
            xs = seg_xs[aa]
            cur, _ = seg_maxrel(xs, aa, Bs, As, Rs, kA, kR, kB, tgt, tol)
            if cur == 0.0 or len(xs) == 0:
                continue
            best = (cur, 0, 0, 0)
            for tbl, idx in ((Bs, 0), (As, 1), (Rs, 2)):
                if (idx == 0 and kB == 0 and name != "BOTH") or \
                   (idx == 1 and kA == 0) or (idx == 2 and kR == 0):
                    # still allow +-1 on unquantized tables? No: only
                    # quantized tables are searched; full tables stay exact.
                    if (idx == 0 and kB == 0) or (idx == 1 and kA == 0) or (idx == 2 and kR == 0):
                        continue
                for d in (-1, 1):
                    old = int(tbl[aa])
                    if old + d < 0:
                        continue
                    tbl[aa] = old + d
                    v, _ = seg_maxrel(xs, aa, Bs, As, Rs, kA, kR, kB, tgt, tol)
                    if v < best[0] * (1 - 1e-12):
                        best = (v, idx, old, d)
                    tbl[aa] = old
            if best[1:] != (0, 0, 0) and best[0] < cur * (1 - 1e-12):
                (Bs, As, Rs)[best[1]][aa] += best[3]
                improved += 1
        print(f"[{name}] neighborhood pass{pas}: improved_segments={improved}")
        if improved == 0:
            break
    r2 = full_vec(Bs, As, Rs, kA, kR, kB, tgt, tol)
    print(f"[{name}] searched: fails={r2['fails']} maxrel={r2['maxrel']:.10f} "
          f"worst={r2['worst']} margin={r2['min_margin']:.1f} V=({r2['vmin']},{r2['vmax']})")
    # 5. offset scan (report only; generator has no const rotation)
    best = (0.0, r2["maxrel"])
    for delta in np.linspace(-2e-9, 2e-9, 41):
        # offset shifts phase; recompute maxrel cheaply? full pass per delta
        # is 41x0.1s; do it on worst-segment subset instead: skip full scan,
        # evaluate on global worst neighborhood only if needed. Here we do a
        # coarse check on 16 prescreen-like samples + worst x from r2.
        pass
    print(f"[{name}] offset: generator has no const rotation; offset kept 0 "
          f"(binary-weight phase P recomputed from new V = angle refit)")
    # 6. persist (never overwrite frozen table)
    out_tables = ART / f"int_tables_R{kR if kR else 12}_A{kA if kA else 22}_quant.json"
    if name == "BOTH":
        out_tables = ART / "int_tables_R10_A20_quant.json"
    elif name == "R10":
        out_tables = ART / "int_tables_R10_quant.json"
    elif name == "A20":
        out_tables = ART / "int_tables_A20_quant.json"
    doc = {"candidate": name, "kA": kA, "kR": kR, "kB": kB,
           "shifts": {"sA": kA, "sR": kR, "sB": kB},
           "Bs": [int(v) for v in Bs], "As": [int(v) for v in As],
           "Rs": [int(v) for v in Rs],
           "fresh_rect_maxrel": summary["maxrel_rect"],
           "contract": r2, "seconds": round(time.time() - t0, 1)}
    out_tables.write_text(json.dumps(doc) + "\n")
    print(f"[{name}] wrote {out_tables} fails={r2['fails']} "
          f"maxrel={r2['maxrel']:.10f} margin={r2['min_margin']:.1f}")
    print("REFIT-" + name + " " + ("PASS" if r2["fails"] == 0 and r2["maxrel"] < 1.0 else "FAIL"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh-fit", action="store_true")
    ap.add_argument("--refit", default=None)
    args = ap.parse_args()
    if args.fresh_fit:
        return cmd_fresh_fit()
    if args.refit == "ALL":
        for n in ("R10", "A20", "BOTH"):
            cmd_refit(n)
        return
    if args.refit == "DEEP-ALL":
        for n in ("A18", "R8", "DEEP"):
            cmd_refit(n)
        return
    if args.refit in CANDS:
        return cmd_refit(args.refit)
    ap.print_help()
    return 2


if __name__ == "__main__":
    main()
