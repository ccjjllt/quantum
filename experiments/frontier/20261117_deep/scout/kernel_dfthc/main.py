"""Scout: (1) official metrics of the dfthc-sos starter-kit FeMoCo76o113e
baseline, (2) the Frobenius lower bound on lambda_H2 / Lambda.

CPU-only Kaggle kernel. Uses the UNCHANGED official dfthcsos code paths for the
metrics. Nothing is submitted.

The lower bound used:
  sum_rc X_rc (x) X_rc  ~=  tei + (S (x) I + I (x) S)/2   (error_2 <= 0.020)
  ||X||_F <= ||w_rc||_1  because the u vectors are unit vectors
  lambda_H2 = 1/4 sum_rc (||w_rc||_1 + |w_B|)^2 >= 1/4 sum_rc ||w_rc||_1^2
            >= 1/4 * || sum_rc X_rc (x) X_rc ||_F
            >= 1/4 * (||tei + sym_shift||_F - 0.020)
so 1/4 ||tei + sym_shift||_F is a floor on lambda_H2, and since
Lambda = lambda_H1 + lambda_H2 and lambda_H1 >= 0, it floors Lambda too.
"""
import json
import pathlib
import sys

import numpy as np


def find_roots():
    comp = None
    for p in pathlib.Path("/kaggle/input").rglob("verifiers/dfthcsos/verify.py"):
        comp = p.parents[2]
        break
    kit = None
    for p in pathlib.Path("/kaggle/input").rglob("starter_kit/baselines"):
        kit = p
        break
    if comp is None or kit is None:
        raise SystemExit(f"missing mounts comp={comp} kit={kit}")
    return comp, kit


def main() -> None:
    comp, kit = find_roots()
    sys.path.insert(0, str(comp / "verifiers"))
    from dfthcsos.verify import heuristic_costs, load_inputs, passes_accuracy
    from dfthcsos.scoreinfra.dfthc_math import (build_h1_prime, evaluate_dfthc_vectors,
                                                reconstruct_x)
    from dfthcsos.scoreinfra.reference import ORBITALS, UPPER_ENERGY

    out = {"comp": str(comp), "kit": str(kit)}

    # ---------- 1. starter-kit baseline for the competition system ----------
    target = [p for p in sorted(kit.glob("*.npz")) if "FeMoCo76o113e" in p.name]
    base = []
    for p in target:
        inp = load_inputs(p)
        R, B, C = inp.w.shape
        U = np.asarray(inp.params["U"], dtype=np.float64)
        X = reconstruct_x(U, inp.w)
        X = np.tril(X) + np.swapaxes(np.tril(X, k=-1), -1, -2)
        ref = inp.ref
        tei = np.asarray(ref["tei"])
        h1_thc = np.asarray(ref["oei"]) - 0.5 * np.einsum("prrq->pq", tei)
        h1_prime = build_h1_prime(h1_thc, inp.S, inp.beta_1, ref["electrons"], inp.W, X)
        evals, evecs = np.linalg.eigh(h1_prime)
        u_all = np.vstack([evecs.T, U.reshape(R * B, ORBITALS)])
        met = evaluate_dfthc_vectors(u_all, inp.w, inp.W, inp.S, inp.beta_1, ref,
                                    energy_upper=UPPER_ENERGY)
        res = heuristic_costs(ORBITALS, R, B, C, 12)
        res["angles_qubits"] = int(res["qubits"])          # circuit width not built here
        row = {"file": p.name, "RBC": [R, B, C],
               "metrics": {k: met.get(k) for k in ("error_1", "error_2", "Lambda", "E_SOS",
                                                   "E_gap", "lambda_eff", "gap_in_domain")},
               "passes_accuracy": bool(passes_accuracy(met)),
               "heuristic_brot12": res}
        row["cost_estimate"] = float(met["lambda_eff"]) * res["toffoli"] * res["qubits"]
        base.append(row)
    out["baseline"] = base

    # ---------- 2. Frobenius floors ----------
    if base:
        inp = load_inputs(target[0])
        ref = inp.ref
        tei = np.asarray(ref["tei"], dtype=np.float64)
        S = np.asarray(inp.S, dtype=np.float64)
        N = ORBITALS
        eye = np.eye(N)
        shift = 0.5 * (np.einsum("pr,qs->pqrs", S, eye) + np.einsum("pq,rs->pqrs", eye, S))
        tgt = tei + shift
        norm_tei = float(np.linalg.norm(tei))
        norm_shift = float(np.linalg.norm(shift))
        norm_tgt = float(np.linalg.norm(tgt))
        out["frobenius"] = {
            "||tei||_F": norm_tei,
            "||sym_shift||_F": norm_shift,
            "||tei+sym_shift||_F": norm_tgt,
            "lambda_H2_floor = 0.25*||target||_F": 0.25 * norm_tgt,
            "lambda_H2_floor_minus_eps = 0.25*(||target||_F-0.020)": 0.25 * (norm_tgt - 0.020),
            "our_lambda_H2 (a73b25d2 family)": 270.1150617930869,
            "our_Lambda": 283.1458106129289,
            "our_lambda_H1": 283.1458106129289 - 270.1150617930869,
            "baseline_lambda_H2": 295.5758056640625,
            "baseline_Lambda": 308.4447937011719,
        }
        # Lambda implied by a floor-valued lambda_H2, at the fixed E_gap
        E = float(met["E_gap"]) if base else 3.914898
        out["floor_note"] = {
            "lambda_eff_at_floor_lambda_H2_only": float(np.sqrt(max(E * (2 * 0.25 * norm_tgt - E), 0.0))),
            "gold_needs_Lambda": 253.09,
            "GM28.20_needs_Lambda": 280.22,
        }

    print(json.dumps(out, indent=2), flush=True)
    pathlib.Path("/kaggle/working/dfthc_floors.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
