"""Consolidated Q/C ledger for the parity-expansion route.

Reads the measured artifacts and prints:
  * the measured worst error/tolerance for every requested K,
  * the smallest measured K that passes (truncation ladder),
  * the official cost at that K (n_rot = K+1: K parity terms + 1 constant),
  * the exact cost gap against 694.840824C (front+rotation budget) and
    1,601.652C (61Q full-domain budget), and against score 97,700.7768 at Q=23,
  * the largest K that any budget can afford, and the measured error there.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/20261107_parity_expansion"
BASE_C = 1_575.818980278
BASE_SCORE = 97_700.776777236
FRONT_ROT = 694.840824
C61 = BASE_SCORE / 61
Q = 23


def rot_c(n_rot: int, margin: float) -> float:
    eps = math.pi * margin / n_rot
    return (0.56 * math.log2(1 / eps) + 5.3) / 4


def main() -> None:
    lad = json.loads((OUT / "ladder.json").read_text())
    rows = {r["K"]: r for r in lad["rows"]}
    fit = json.loads((OUT / "fit_grid.json").read_text())
    cheb = json.loads((OUT / "cheb.json").read_text()) if (OUT / "cheb.json").exists() else {}
    wp = json.loads((OUT / "walsh_phase.json").read_text())
    gad = json.loads((OUT / "gadget_check.json").read_text())

    # best measured ratio per K across every variant tried
    best: dict[int, tuple[float, str]] = {}
    for r in fit:
        if r["K"] in (41, 96, 200, 500, 1000, 2000):
            k, v, tag = r["K"], r["max_ratio"], f"A-{r['fit']}-{r['order']}"
            if k not in best or v < best[k][0]:
                best[k] = (v, tag)
    for r in wp:
        k, v, tag = r["K"], r["complex_max_ratio"], f"B-{r['ext']}"
        if k not in best or v < best[k][0]:
            best[k] = (v, tag)
    for kk, v in cheb.items():
        k, tag, val = int(kk), "A-chebyshev", v["max_ratio"]
        if k not in best or val < best[k][0]:
            best[k] = (val, tag)

    print("K          rotations   measured max error/tol   variant            pass")
    table = []
    for K in (41, 96, 200, 500, 1000, 2000):
        v, tag = best[K]
        table.append({"K": K, "n_rot": K + 1, "max_ratio": v, "variant": tag,
                      "pass": False})
        print(f"{K:8d}  {K+1:9d}   {v:>20.4e}   {tag:18s} no")
    for K in sorted(rows):
        if K >= 4194290 and rows[K]["pass"]:
            r = rows[K]
            table.append({"K": K, "n_rot": K + 1, "max_ratio": r["max_ratio"],
                          "variant": "ladder truncation", "pass": True,
                          "min_margin": r["min_margin"], "c_rot": r["c_rot"],
                          "C": r["C"], "score": r["score"]})
            print(f"{K:8d}  {K+1:9d}   {r['max_ratio']:>20.4e}   "
                  f"{'ladder truncation':18s} YES  C={r['C']:.1f}")
    Kpass = min(t["K"] for t in table if t["pass"])
    rp = rows[Kpass]
    print(f"\nminimum passing K = {Kpass} (= 2^22, the whole basis)")
    print(f"  rotations = {Kpass+1} (K parity terms + 1 constant), Q = {Q}")
    print(f"  min margin = {rp['min_margin']:.6e} turns, "
          f"eps = {math.pi*rp['min_margin']/(Kpass+1):.3e}, "
          f"C/rot = {rp['c_rot']:.4f}")
    print(f"  C = {rp['C']:.3f}   score = {rp['score']:.1f}")
    print(f"  gap vs front+rotation {FRONT_ROT}C : {rp['C']/FRONT_ROT:.1f}x "
          f"(excess {rp['C']-FRONT_ROT:,.1f}C)")
    print(f"  gap vs 61Q full-domain {C61:.3f}C : {rp['C']/C61:.1f}x "
          f"(excess {rp['C']-C61:,.1f}C)")
    print(f"  gap vs baseline C {BASE_C:.3f}: {rp['C']/BASE_C:.1f}x")
    print(f"  score gap vs {BASE_SCORE:.3f}: {rp['score']/BASE_SCORE:.1f}x")

    # largest K any budget can afford, using the exact margin-dependent price
    def score_at(K: int, margin: float) -> tuple[float, float]:
        cr = rot_c(K + 1, margin)
        return (K + 1) * cr, Q * (K + 1) * cr

    tol_min = lad["tol_min"]
    print(f"\nbudget ceilings (assuming an ideal fit, margin = tol_min = {tol_min:.4e}):")
    for K in (41, 96, 200, 300, 400, 500, 550, 590, 1000):
        C, sc = score_at(K, tol_min)
        print(f"  K={K:5d}: C={C:9.2f}  ({C/FRONT_ROT:.2f}x front+rot)   score={sc:10.1f}"
              f"  ({sc/BASE_SCORE:.3f}x baseline)")
    # exact ceiling for C < 694.840824 and for score < 97700.7768
    lo, hi = 1, 4_000_000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if score_at(mid, tol_min)[0] < FRONT_ROT:
            lo = mid
        else:
            hi = mid - 1
    print(f"  largest K with C < {FRONT_ROT}C : {lo}")
    lo, hi = 1, 4_000_000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if score_at(mid, tol_min)[1] < BASE_SCORE:
            lo = mid
        else:
            hi = mid - 1
    print(f"  largest K with Q*C < {BASE_SCORE:.3f} at Q={Q}: {lo}")
    for K in (96, 590):
        if K in rows:
            print(f"  measured ratio at K={K}: {rows[K]['max_ratio']:.4e} "
                  f"(gap factor {rows[K]['max_ratio']:.1e} above tolerance)")
    print(f"\ncoefficient floor: min |c| = {lad['min_coef']:.4e} = "
          f"{lad['min_coef']/tol_min:.1f} x tol_min")
    print(f"approach-B amplitude at rank 2000 = "
          f"{min(r['abs_max_ratio'] for r in wp):.4e} (top coefficient "
          f"{max(r['abs_max_ratio'] for r in wp):.4f})")
    print(f"gadget check: part1 official {gad['part1']['status']} at max_x=60, "
          f"Q={gad['part1']['num_qubits']}, "
          f"rotations={gad['part1']['rotation_count']:.0f}, "
          f"C={gad['part1']['toffoli_equivalent']:.3f}; part2 model vs simulator "
          f"max diff = {gad['part2']['max_phase_model_diff_units']} units "
          f"(2^-64 turns), ratio {gad['part2']['worst_ratio_simulator']:.6e}")
    json.dump({"table": table, "K_pass": Kpass, "gate_K_front_rot": lo,
               "C_at_pass": rp["C"], "score_at_pass": rp["score"]},
              open(OUT / "ledger.json", "w"), indent=2)


if __name__ == "__main__":
    main()
