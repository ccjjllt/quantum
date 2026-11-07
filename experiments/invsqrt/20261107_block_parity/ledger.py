"""Q/C ledger for the block/wavelet parity family.

Reads the measured numbers from block_fit.json and the counted gadget costs
from kernels.json (it does not re-derive any of them), and prices the cheapest
realisation of the family with the official cost formula

    eps   = pi * min_margin / n_rot
    T     = 0.56 log2(1/eps) + 5.3
    C     = paid_toffoli_like + T / 4          (no T gates in this family)
    Q     = num_qubits
    score = Q * C

Construction priced (cheapest variant, both selectors counted in kernels.py):

    for each block h (m = 22 - b high bits, X-flips for zero controls):
        selector:  unary-iteration walk   -> ~1 CCX per entry   (measured 0.998)
                   or per-block AND ladder -> m-1 CCX per entry (measured m-1)
        one rotation on the selector qubit for c_{h,empty} + sum_{S!=0} c_{h,S}
        for every S != 0 with c_{h,S} != 0:
            1 CCX (AND of selector and local parity) + 1 rotation
            (measured marginal: exactly 1 CCX and 1 rotation per term)

so
    n_rot = K                     (one rotation per term, no extra constant)
    paid  = B_walk + (K - B)      [walk]       or   B(m-1) + (K - B)  [ladder]
    Q     = 22 + m + 1

Output: artifacts/20261107_block_parity/ledger.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261107_block_parity"
BASE_C = 1_575.818980278
BASE_SCORE = 97_700.776777236
BASE_Q = 62
FRONT_ROT = 694.840824
C61 = BASE_SCORE / 61               # 1,601.6520  full-domain 61Q budget
TOL_MIN = 621_138_291 / 2.0**64     # 3.36719742258e-11 turns


def c_rot(n_rot: int, margin: float) -> float:
    eps = math.pi * margin / n_rot
    return (0.56 * math.log2(1.0 / eps) + 5.3) / 4.0


def price(K: int, B: int, m: int, margin: float, selector: str) -> dict:
    n_rot = K
    paid = (B + (K - B)) if selector == "walk" else (B * (m - 1) + (K - B))
    cr = c_rot(n_rot, margin)
    rot_C = n_rot * cr
    C = paid + rot_C
    Q = 22 + m + 1
    return {"K": K, "B": B, "m": m, "n_rot": n_rot, "Q": Q,
            "paid": paid, "c_rot": cr, "rotation_C": rot_C, "C": C,
            "score": Q * C, "margin": margin,
            "rot_share": rot_C / C, "paid_share": paid / C}


def affordable(max_C: float, B: int, m: int, margin: float,
               selector: str = "walk") -> int:
    """Largest K whose priced circuit costs < max_C (n_rot = K is monotone)."""
    lo, hi = 1, 4_000_000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if price(mid, B, m, margin, selector)["C"] < max_C:
            lo = mid
        else:
            hi = mid - 1
    return lo


def main() -> None:
    fit = json.loads((OUT / "block_fit.json").read_text())
    ker = json.loads((OUT / "kernels.json").read_text())
    res: dict = {"base_C": BASE_C, "base_score": BASE_SCORE, "base_Q": BASE_Q,
                 "front_rot": FRONT_ROT, "C61": C61, "tol_min": TOL_MIN,
                 "kernels": {
                     "indicator_paid_m_minus_1": {k: v["manual"]["toffoli_like"]
                                                  for k, v in ker["indicator"].items()},
                     "rotation2_marginal_paid": ker["rotation2"]["marginal_paid"],
                     "walk_per_entry": {k: v["walk_per_entry"]
                                        for k, v in ker["unary_iteration"].items()},
                     "exact_x16": ker["exact_x16"]["verifier"],
                     "b12_shape_Q": ker["b12_shape_Q"]["qubits"]},
                 "bs": {}}

    print("A. numerics: minimum passing K per block size (measured, full domain)")
    print(f"{'b':>3} {'B':>7} {'K_pass':>9} {'worst':>9} {'margin':>10} "
          f"{'K_LB':>8}  best worst ratio at K = 41/96/200/500/1000/2000")
    for b in sorted(fit["bs"], key=int):
        r = fit["bs"][b]
        ladder = [r["best_at_K"].get(str(k), {}).get("worst") for k in
                  (41, 96, 200, 500, 1000, 2000)]
        print(f"{int(b):3d} {r['hb']:7d} {r['Kpass']:9d} {r['worst_at_Kpass']:9.4f} "
              f"{r['margin_at_Kpass']:10.2e} {r['K_lower_bound']:8d}  "
              + " ".join(f"{v:.2e}" if v else "-" for v in ladder))
        res["bs"][b] = {
            "B": r["hb"], "nb": r["nb"], "m": 22 - int(b),
            "Kpass": r["Kpass"], "worst": r["worst_at_Kpass"],
            "margin": r["margin_at_Kpass"], "K_lower_bound": r["K_lower_bound"],
            "kmin": r["kmin"], "kmax": r["kmax"], "block0_k": r["block0_k"],
            "ladder_worst": dict(zip((41, 96, 200, 500, 1000, 2000), ladder)),
            "gains": r["gains"], "design": r["design"],
            "shared": r["shared"], "haar": r["haar"], "lp": r["lp"],
        }

    print("\nB. cheapest ledger at the minimum passing K (selector = walk)")
    print(f"{'b':>3} {'K':>7} {'paid':>7} {'n_rot':>7} {'c_rot':>6} {'rot C':>10} "
          f"{'C':>11} {'Q':>3} {'score':>11} {'x front+rot':>12}")
    best = None
    for b in sorted(fit["bs"], key=int):
        r = fit["bs"][b]
        m = 22 - int(b)
        p = price(r["Kpass"], r["hb"], m, r["margin_at_Kpass"], "walk")
        pl = price(r["Kpass"], r["hb"], m, r["margin_at_Kpass"], "ladder")
        print(f"{int(b):3d} {p['K']:7d} {p['paid']:7d} {p['n_rot']:7d} "
              f"{p['c_rot']:6.3f} {p['rotation_C']:10.0f} {p['C']:11.0f} "
              f"{p['Q']:3d} {p['score']:11.0f} {p['C']/FRONT_ROT:11.1f}x")
        res["bs"][b]["ledger_walk"] = p
        res["bs"][b]["ledger_ladder"] = pl
        if best is None or p["C"] < best[1]["C"]:
            best = (b, p)
    bbest, pb = best
    print(f"\n  cheapest: b={bbest}, C={pb['C']:.1f}, Q={pb['Q']}, "
          f"score={pb['score']:.0f}")
    print(f"  rotation synthesis = {pb['rotation_C']:.1f}C "
          f"({100*pb['rot_share']:.1f}% of C), paid CCX = {pb['paid']}C "
          f"({100*pb['paid_share']:.1f}%)")
    print(f"  gap vs front+rotation {FRONT_ROT}C: {pb['C']-FRONT_ROT:+,.1f}C "
          f"({pb['C']/FRONT_ROT:.1f}x)")
    print(f"  gap vs 61Q full-domain {C61:.1f}C: {pb['C']-C61:+,.1f}C "
          f"({pb['C']/C61:.1f}x)")
    print(f"  gap vs baseline C {BASE_C}: {pb['C']/BASE_C:.1f}x, "
          f"score {pb['score']/BASE_SCORE:.1f}x baseline")
    res["cheapest"] = {"b": int(bbest), "ledger": pb,
                       "gap_front_rot": pb["C"] - FRONT_ROT,
                       "ratio_front_rot": pb["C"] / FRONT_ROT,
                       "gap_C61": pb["C"] - C61,
                       "ratio_C61": pb["C"] / C61,
                       "ratio_base_C": pb["C"] / BASE_C,
                       "ratio_base_score": pb["score"] / BASE_SCORE}

    print("\nB2. design variant with headroom (worst ratio <= 0.5, margin >= tol_min/2)")
    for b in sorted(fit["bs"], key=int):
        r = fit["bs"][b]
        d = r.get("design")
        if not d:
            continue
        m = 22 - int(b)
        p = price(d["K"], r["hb"], m, 0.5 * TOL_MIN, "walk")
        res["bs"][b]["ledger_design"] = p
        print(f"  b={int(b):3d}: K={p['K']:7d} (worst {d['worst']:.3f}) "
              f"c_rot {p['c_rot']:.3f} C={p['C']:9.0f} "
              f"({p['C']/FRONT_ROT:6.1f}x front+rot)")

    print("\nC. budget ceilings: how many terms fit? (ideal margin = tol_min)")
    ceil = {}
    for b in ("10", "11", "12"):
        r = fit["bs"][b]
        m = 22 - int(b)
        ka = affordable(FRONT_ROT, r["hb"], m, TOL_MIN)
        kb = affordable(C61, r["hb"], m, TOL_MIN)
        # measured best worst-ratio with at most ka terms
        st = [s for s in r["waterfill"] if s["K"] <= ka]
        wa = min((s["worst"] for s in st), default=float("nan"))
        st = [s for s in r["waterfill"] if s["K"] <= kb]
        wb = min((s["worst"] for s in st), default=float("nan"))
        ceil[b] = {"K_afford_front_rot": ka, "K_afford_C61": kb,
                   "worst_at_Kafford_front_rot": wa, "worst_at_Kafford_C61": wb}
        print(f"  b={b}: K <= {ka} fits front+rotation {FRONT_ROT}C "
              f"(worst ratio there {wa:.2e}); K <= {kb} fits {C61:.1f}C "
              f"(worst ratio {wb:.2e})")
    res["ceilings"] = ceil

    print("\nD. margin sensitivity at the cheapest passing circuit (b=%d)" % int(bbest))
    r = fit["bs"][str(bbest)]
    m = 22 - int(bbest)
    sens = {}
    for margin in (r["margin_at_Kpass"], 1e-13, 1e-11, TOL_MIN, 1e-9):
        p = price(r["Kpass"], r["hb"], m, margin, "walk")
        sens[f"{margin:.3e}"] = p
        print(f"  margin {margin:.2e} turns: c_rot {p['c_rot']:.3f}, "
              f"C {p['C']:.0f}, {p['C']/FRONT_ROT:.1f}x front+rot")
    res["margin_sensitivity"] = sens

    print("\nE. method-independent floor: Bessel lower bound K_LB and its C")
    floor = {}
    for b in sorted(fit["bs"], key=int):
        r = fit["bs"][b]
        m = 22 - int(b)
        p = price(r["K_lower_bound"], r["hb"], m, TOL_MIN, "walk")
        floor[b] = p
        print(f"  b={int(b):3d}: K_LB={r['K_lower_bound']:7d} -> cheapest "
              f"possible C = {p['C']:9.0f} ({p['C']/FRONT_ROT:6.1f}x front+rot)")
    fl_best = min(floor.values(), key=lambda v: v["C"])
    print(f"  best over b: C = {fl_best['C']:.0f} = "
          f"{fl_best['C']/FRONT_ROT:.1f}x front+rotation budget")
    res["floor"] = {"by_b": floor, "best": fl_best}

    (OUT / "ledger.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'ledger.json'}")


if __name__ == "__main__":
    main()
