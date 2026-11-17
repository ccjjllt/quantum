"""Shape arithmetic for the dfthcsos leg — pure formulas, no circuit simulation.

Inputs, all local and small:
  * the verifier's own cost model ``scoreinfra/costs_prepare.SpinFreeData_V1``,
  * the rank-K floor of ``error_2`` from a stored H spectrum
    (``artifacts/H_spectrum.npy``: the 2,926 eigenvalues of H, produced by
    earlier work from the packaged FCIDUMP — no integrals are read here),
  * the measured rho law of RESULT2 (4 measured shapes) and the measured
    points (8,129,44) 19.83, (5,135,70) 40.24, (4,131,83) 73.07 mHa,
  * closed-form bookkeeping rows = 76 + R*B, K = R*C, rows-76 = K*(B/C).

No kickmix import, no simulation, no eigendecomposition of any integral tensor.

Three loader models are printed for each shape (all are MODELS, not measurements):
  lin   L/pass = 4025 * rows/1220                      (optimistic, used before)
  cons  L/pass = 15 * (6 + high(rows) + 193)           (products frozen)
  cut   L/pass = 15 * (6 + high(rows) + (525-cuts)/2)  (allowed-cut bound)
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

sys.path.insert(0, "data/competition/verifiers")
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

N = 76
CHI = 10
LAM = 46.92160235
ANG_TEMP = 77
J = 5

SPECTRUM = np.load("artifacts/H_spectrum.npy")
NEG2 = float(np.sum(np.minimum(SPECTRUM, 0) ** 2))
BASE = 294_762_512.64351326      # v13 chem cost, T 14,706, Q 427, same lambda
GM0 = 28.129941265314777


def floor_mha(K: int) -> float:
    ev = SPECTRUM
    return 1e3 * math.sqrt(float(np.sum(np.maximum(ev[K:], 0) ** 2)) + NEG2) if K < len(ev) else 0.0


def shape(R: int, B: int, C: int, brot: int = 8, J: int = J) -> dict:
    m = SpinFreeData_V1(R=R, B=B, C=C, N=N, chi=CHI, beta=brot)
    o, i, g = m.outer_state_prep(), m.inner_state_prep(), m.givens_rotations()
    oq, iq = m.outer_state_prep_qubit_cost(), m.inner_state_prep_qubit_cost()
    b2 = math.ceil(math.log2(B)) + CHI + 1
    k2 = m.find_qroam_size_to_minimize_global_temp_ancilla(b2)
    out = dict(R=R, B=B, C=C, brot=brot, J=J, rows=N + R * B, K=R * C,
               b_over_c=B / C, outer=o, inner=i, givens=g, T_h=o + i + g,
               b2=b2, k2=k2, outer_pers=oq["persistent"], outer_temp=oq["temporary"],
               inner_pers=iq["persistent"], inner_temp=iq["temporary"],
               angles_pers=J * brot, angles_temp=ANG_TEMP)
    out["temp"] = max(out["outer_temp"], out["inner_temp"], out["angles_temp"])
    out["Q"] = out["angles_pers"] + out["outer_pers"] + out["inner_pers"] + out["temp"]
    out["angles_qubits"] = 11 + J * brot + ANG_TEMP
    out["cap_ok"] = out["angles_qubits"] <= 128
    return out


def gate_c(rows: int, p_1220: float = 13.8) -> float:
    p = p_1220 * math.sqrt(rows / 1220.0)
    return math.sqrt(max(0.0, 400.0 - p * p))


def rho_law(b_over_c: float) -> float:
    return 1.93 * (3.25 / b_over_c) ** 1.95


def high_masks(rows: int) -> int:
    hmax = math.ceil(rows / 16)
    top = hmax - 1
    n_pow = len([h for h in range(1, top + 1) if h & (h - 1) == 0])
    return top - n_pow


def loaders(rows: int, model: str) -> float:
    if model == "lin":
        return 4025.0 * rows / 1220.0
    high = high_masks(rows)
    hmax = math.ceil(rows / 16)
    if model == "cons":
        return 15.0 * (6 + high + 193)
    if model == "cut":
        cuts = 5 * (105 - (hmax - 1))
        cuts = min(cuts, 525)
        return 15.0 * (6 + high + (525 - cuts) / 2)
    raise ValueError(model)


def cost(T, Q, lam=LAM):
    return lam * T * Q


def dgm(cc: float, base: float = BASE) -> float:
    return GM0 * ((base / cc) ** (1 / 3) - 1)


def main() -> None:
    print("== 0. control: shipped shape must be (T_h 6662, Q 427) ===============")
    c = shape(8, 143, 44)
    print({k: c[k] for k in ("rows", "K", "b_over_c", "outer", "inner", "givens",
                             "T_h", "inner_temp", "temp", "Q", "k2")})
    assert (c["T_h"], c["Q"]) == (6662, 427)
    print(f"  loader models at rows 1220: lin {loaders(1220,'lin'):.0f} "
          f"cons {loaders(1220,'cons'):.0f} cut {loaders(1220,'cut'):.0f} "
          f"(shipped measured 4025)")

    print("\n== 1. rank floors ====================================================")
    print("  " + "  ".join(f"K={K}:{floor_mha(K):.2f}" for K in
                           (235, 282, 300, 322, 340, 352, 375, 400, 450, 512, 600, 700)))

    print("\n== 2. requested shapes (T_h/Q exact; e2 predicted from the rho law) =")
    req = [(8, 143, 44), (8, 96, 44), (8, 76, 44), (8, 64, 44), (8, 64, 64),
           (6, 96, 59), (6, 64, 59), (4, 128, 88)]
    print(f"{'shape':>13} {'rows':>5} {'K':>4} {'B/C':>5} {'Th':>5} {'k2':>2} {'itemp':>5} "
          f"{'Q':>4} {'floor':>6} {'gate':>5} {'rhoLaw':>6} {'e2pred':>6} "
          f"{'Lcons':>6} {'Tcons':>6} {'costC':>7} {'dGM_C':>6} {'Llin':>6} {'costL':>7} {'dGM_L':>6}")
    out = []
    for (R, B, C) in req:
        s = shape(R, B, C)
        fl, gt, rh = floor_mha(s["K"]), gate_c(s["rows"]), rho_law(s["b_over_c"])
        Lc, Ll = loaders(s["rows"], "cons"), loaders(s["rows"], "lin")
        Tc, Tl = 2 * Lc + s["T_h"], 2 * Ll + s["T_h"]
        cc, cl = cost(Tc, s["Q"]), cost(Tl, s["Q"])
        print(f"{R:2d},{B:4d},{C:3d} {s['rows']:5d} {s['K']:4d} {s['b_over_c']:5.2f} "
              f"{s['T_h']:5d} {s['k2']:2d} {s['inner_temp']:5d} {s['Q']:4d} {fl:6.2f} "
              f"{gt:5.2f} {rh:6.2f} {rh*fl:6.1f} {Lc:6.0f} {Tc:6.0f} {cc/1e6:7.2f} "
              f"{dgm(cc):+6.2f} {Ll:6.0f} {cl/1e6:7.2f} {dgm(cl):+6.2f}")
        out.append(dict(s, floor=fl, gate=gt, rho=rh, e2_pred=rh * fl,
                        L_cons=Lc, T_cons=Tc, cost_cons=cc, dGM_cons=dgm(cc),
                        L_lin=Ll, T_lin=Tl, cost_lin=cl, dGM_lin=dgm(cl)))

    print("\n== 3. exact B-axis table at R=8, C=44 (the Q cliff) =================")
    print(f"{'B':>4} {'rows':>5} {'b2':>3} {'k2':>2} {'itemp':>5} {'Q':>4} {'T_h':>5} "
          f"{'Lcons':>6} {'Tcons':>6} {'costC_M':>7} {'dGM_C':>6}")
    for B in (32, 48, 63, 64, 80, 96, 110, 120, 128, 129, 136, 143, 144, 160):
        s = shape(8, B, 44)
        Lc = loaders(s["rows"], "cons")
        Tc = 2 * Lc + s["T_h"]
        cc = cost(Tc, s["Q"])
        print(f"{B:4d} {s['rows']:5d} {s['b2']:3d} {s['k2']:2d} {s['inner_temp']:5d} "
              f"{s['Q']:4d} {s['T_h']:5d} {Lc:6.0f} {Tc:6.0f} {cc/1e6:7.2f} {dgm(cc):+6.2f}")

    print("\n== 4. brot axis at (8,143,44) ========================================")
    print(f"{'brot':>4} {'givens':>6} {'inner':>6} {'k2':>2} {'itemp':>5} {'Q':>4} {'T_h':>5}")
    for brot in range(6, 13):
        s = shape(8, 143, 44, brot=brot)
        print(f"{brot:4d} {s['givens']:6d} {s['inner']:6d} {s['k2']:2d} "
              f"{s['inner_temp']:5d} {s['Q']:4d} {s['T_h']:5d}")

    print("\n== 5. full grid scan: precision feasibility vs cost ==================")
    grid = []
    for R in range(4, 17):
        for B in range(32, 385):
            for C in range(24, 129):
                try:
                    s = shape(R, B, C)
                except Exception:
                    continue
                if not s["cap_ok"]:
                    continue
                s["floor"] = floor_mha(s["K"])
                s["gate"] = gate_c(s["rows"])
                s["rho"] = rho_law(s["b_over_c"])
                s["e2_pred"] = s["rho"] * s["floor"]
                grid.append(s)
    print(f"  {len(grid)} shapes with angles_qubits <= 128")
    for tag, ok in (("rho_law", lambda s: s["e2_pred"] <= s["gate"]),
                    ("best_rho_1.93", lambda s: 1.93 * s["floor"] <= s["gate"])):
        feas = [s for s in grid if ok(s)]
        print(f"\n  -- feasible under {tag}: {len(feas)}")
        for model in ("cons", "lin"):
            rank = []
            for s in feas:
                L = loaders(s["rows"], model)
                T = 2 * L + s["T_h"]
                rank.append((cost(T, s["Q"]), T, L, s))
            rank.sort(key=lambda t: t[0])
            print(f"     top 8 by cost ({model} loaders):")
            for cc, T, L, s in rank[:8]:
                print(f"       {cc/1e6:8.2f} M  dGM {dgm(cc):+6.2f}  "
                      f"R={s['R']:2d} B={s['B']:3d} C={s['C']:3d} rows={s['rows']:4d} "
                      f"K={s['K']:3d} B/C={s['b_over_c']:4.2f} T_h={s['T_h']:5d} "
                      f"Q={s['Q']:3d} floor={s['floor']:5.2f} e2p={s['e2_pred']:5.1f} "
                      f"T={T:6.0f}")

    print("\n== 6. the rows -> e2 curve at K ~= 352 (measured + this session) ======")
    meas = [((8, 143, 44), 14.20, "measured continuous (RESULT4)"),
            ((8, 129, 44), 19.83, "measured continuous (RESULT2 4b)"),
            ((5, 135, 70), 40.24, "measured continuous (RESULT2 4b)"),
            ((4, 131, 83), 73.07, "measured continuous (RESULT2 4b)")]
    print(f"{'shape':>13} {'rows':>5} {'K':>4} {'B/C':>5} {'floor':>6} {'gate':>5} "
          f"{'e2':>6} {'e2/gate':>7}  note")
    for (R, B, C), e2, note in meas:
        s = shape(R, B, C)
        print(f"{R:2d},{B:4d},{C:3d} {s['rows']:5d} {s['K']:4d} {s['b_over_c']:5.2f} "
              f"{floor_mha(s['K']):6.2f} {gate_c(s['rows']):5.2f} {e2:6.2f} "
              f"{e2/gate_c(s['rows']):7.2f}  {note}")
    print("\n  what K is needed for e2_pred <= gate at rows<=600 (=B/C 524/K)?")
    for K in (350, 400, 450, 500, 550, 600, 650, 700, 800):
        rows = 600
        bc = (rows - 76) / K
        e2p = rho_law(bc) * floor_mha(K)
        print(f"    K={K:4d} B/C={bc:5.2f} floor={floor_mha(K):6.2f} rho={rho_law(bc):6.2f} "
              f"e2_pred={e2p:7.1f} gate={gate_c(rows):5.2f} "
              f"{'PASS' if e2p <= gate_c(rows) else 'fail'}")

    json.dump(dict(shapes=out), open("experiments/frontier/20261117_deep/chem/shape_arith.json", "w"), indent=1)


if __name__ == "__main__":
    main()
