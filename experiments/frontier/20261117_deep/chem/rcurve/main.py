"""R-truncation accuracy curve of the shipped chemistry factorization (official metrics).

Answers, from real arrays and without any fitting: if we keep only the first R ranks of the
shipped `(8,143,44)` factorization (and drop the matching angle rows), what are the official
`error_1`, `error_2`, `Lambda`, `E_gap`, `lambda_eff`?

Why it matters: every cheaper chemistry shape needs fewer ranks (rows = 76 + R*B), and
`lambda_eff` is pinned.  A truncation is a *lower bound* on what a refit at that R could reach
(a refit optimises the same objective), so:
  * truncation <= 20 mHa  => R is certainly viable,
  * truncation >> 20 mHa  => R needs a refit that beats plain truncation by that factor.

Cost model: spin-free `lambda_eff * T * Q`; the loader part of T is measured from the emitted
loaders, so this kernel only reports the *metrics* and the model `T_h`/`Q`.

CPU only, nothing submitted.
"""
import json
import pathlib
import sys

import numpy as np

COMP = None
for _p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for _up in (_p.parents[1], _p.parents[2], _p.parents[3]):
        if (_up / "kickmix").is_dir():
            COMP = _up
            break
    if COMP:
        break
print("competition:", COMP, flush=True)
if COMP is None:
    raise SystemExit("no competition mount")
sys.path.insert(0, str(COMP / "verifiers"))
sys.path.insert(0, str(COMP / "kickmix"))

from dfthcsos.scoreinfra import reference as refm  # noqa: E402
from dfthcsos.scoreinfra import dfthc_math as M  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("cp", str(COMP / "verifiers/dfthcsos/scoreinfra/costs_prepare.py"))
CP = importlib.util.module_from_spec(spec)
sys.modules["cp"] = CP
spec.loader.exec_module(CP)
MODEL = CP.SpinFreeData_V1


def find_npz():
    for p in sorted(pathlib.Path("/kaggle/input").rglob("submission.npz")):
        s = str(p)
        if "competitions" in s or "sample_submission" in s:
            continue
        try:
            with np.load(p, allow_pickle=False) as z:
                if "angle_words" in z and z["angle_words"].shape[0] == 1220:
                    return p
        except Exception:
            continue
    return None


def main():
    npz = find_npz()
    print("shipped npz:", npz, flush=True)
    z = np.load(npz, allow_pickle=False)
    U, Wz, H2 = z["U"], z["W"], z["H2_I"]
    Hs, E, AW = z["Hsym_lower"], z["tree_edges"], z["angle_words"]
    R, B, N = U.shape
    print(f"shipped U {U.shape} W {Wz.shape} H2_I {H2.shape} angle_words {AW.shape}", flush=True)

    ref = refm.load_reference(refm.check_fcidump())
    print("reference loaded; orbitals", ref["orbitals"], flush=True)

    # native_inputs: w = W, W_rho_c = H2_I - sum_b w
    S = np.asarray(refm.symmetric_from_lower(Hs, N) if hasattr(refm, "symmetric_from_lower")
                   else np.zeros((N, N)), dtype=np.float64)
    beta_1 = float(z["H1_I"]) - 0.5 * float(np.trace(S))

    print(f"\n{'R':>2} {'rows':>5} {'K':>4} {'Q':>4} {'T_h':>5} {'error_1':>10} {'error_2':>10} "
          f"{'Lambda':>9} {'lambda_eff':>11} {'legal(<=0.02)':>13}", flush=True)
    out = {}
    for Rp in (8, 7, 6, 5, 4):
        try:
            rows = 76 + Rp * B
            words = np.asarray(AW[:rows], dtype=np.float64)
            u_all = M.reconstruct_u_vectors(words / 128.0, E)
            w = np.asarray(Wz[:Rp], dtype=np.float64)
            W_rho_c = np.asarray(H2[:Rp], dtype=np.float64) - np.sum(w, axis=1)
            met = M.evaluate_dfthc_vectors(u_all, w, W_rho_c, S, beta_1, ref,
                                           energy_upper=refm.UPPER_ENERGY)
            m = MODEL(R=Rp, B=B, C=Wz.shape[2], N=N, chi=10, beta=8)
            Q = 84 + 5 * 8 + max(m.outer_state_prep_qubit_cost()["temporary"],
                                 m.inner_state_prep_qubit_cost()["temporary"], 77)
            Th = m.outer_state_prep() + m.inner_state_prep() + m.givens_rotations()
            legal = met["error_1"] <= 0.02 and met["error_2"] <= 0.02
            out[Rp] = dict(rows=rows, K=Rp * Wz.shape[2], Q=Q, T_h=Th,
                           error_1=met["error_1"], error_2=met["error_2"],
                           Lambda=met["Lambda"], lambda_eff=met["lambda_eff"], legal=bool(legal))
            print(f"{Rp:>2} {rows:>5} {Rp*Wz.shape[2]:>4} {Q:>4} {Th:>5} "
                  f"{met['error_1']:>10.5f} {met['error_2']:>10.5f} {met['Lambda']:>9.3f} "
                  f"{met['lambda_eff']:>11.5f} {str(legal):>13}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"{Rp:>2} FAILED {type(exc).__name__}: {exc}", flush=True)
            out[Rp] = {"error": f"{type(exc).__name__}: {exc}"}

    print("\nSUMMARY " + json.dumps(out), flush=True)
    print("note: truncation is a LOWER BOUND on a refit at the same R", flush=True)
    print("DONE", flush=True)


main()
