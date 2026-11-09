"""Error-budget reallocation via analytic KKT Jacobian (exact arithmetic).

Recomputes the KKT multipliers at b9eced3e, then gives three analytic
exchange numbers:
  (a) e2 19.999999975 -> 19.99999 mHa (still 10 nHa below the 20 mHa gate);
  (b) e1 over the same interval (contrast: worthless);
  (c) E_gap +/-1 uHa tighten/loosen + the e2-vs-Egap cross ratio.
Plus one exact Newton-retraction check that the (a) linear prediction holds.

No verifier shots. Results -> artifacts/20261109_joint_budget/budget_exchange.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers" / "dfthcsos"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify as v  # noqa: E402
from scoreinfra import dfthc_math  # noqa: E402

from joint_newton import J0, build, decode  # noqa: E402

CAND = ROOT / "artifacts" / "20261108_public_frontier" / "dfthcsos_refit" / "submission.npz"
WORDS = ROOT / "artifacts" / "20261106_syed_v9" / "dfthcsos" / "recovered_words.npy"
TQ = 14966 * 427


def main() -> None:
    out_dir = ROOT / "artifacts" / "20261109_joint_budget"
    out_dir.mkdir(parents=True, exist_ok=True)
    d = np.load(CAND)
    base_dict = {k: np.asarray(d[k]) for k in d.files}
    words0 = np.load(WORDS)
    tree = np.load(
        ROOT / "artifacts" / "20261108_public_frontier" / "release"
        / "dfthcsos" / "submission.npz")["tree_edges"]
    inp = v.load_inputs(CAND)
    oei = np.asarray(inp.ref["oei"], dtype=np.float64)
    tei = np.asarray(inp.ref["tei"], dtype=np.float64)
    h1_thc = oei - 0.5 * np.einsum("prrq->pq", tei)
    w0 = d["W"].copy()
    wB0 = d["H2_I"].copy()

    u0 = decode(words0, tree)
    ob0, ub0 = dfthc_math.split_u_vectors(u0, inp.w)
    compute = build(inp, ob0, ub0, h1_thc)
    base, grads = compute(w0, wB0)
    le0, e1_0, e2_0, Eg0, ev0, Lam0 = base

    w_mask = np.abs(w0) > 1e-12
    wB_mask = np.abs(wB0) > 1e-12

    def pack(pair):
        return np.concatenate([pair[0][w_mask], pair[1][wB_mask]])

    def unpack(vec):
        dw = np.zeros_like(w0)
        dwB = np.zeros_like(wB0)
        nw = int(np.sum(w_mask))
        dw[w_mask] = vec[:nw]
        dwB[wB_mask] = vec[nw:]
        return dw, dwB

    g_le = pack(grads["le"])
    A = np.vstack([pack(grads["e1"]), pack(grads["e2"]),
                   pack(grads["eg"]), pack(grads["ev"])])
    coeffs, _, _, _ = np.linalg.lstsq(A.T, g_le, rcond=None)
    proj = g_le - A.T @ coeffs
    proj_norm = float(np.linalg.norm(proj))
    c1, c2, ceg, cev = [float(x) for x in coeffs]

    def dscore(dle):
        return dle * TQ

    # (a) e2 -> 19.99999 mHa
    e2_new = 0.01999999
    dt_e2 = e2_new - e2_0
    dle_a = c2 * dt_e2
    # (b) e1 -> 19.99999 mHa
    e1_new = 0.01999999
    dt_e1 = e1_new - e1_0
    dle_b = c1 * dt_e1
    # (c) E_gap +/-1 uHa
    dt_eg = 1e-6
    dle_c_tight = ceg * dt_eg     # requiring +1uHa more gap
    dle_c_loose = -ceg * dt_eg    # allowing -1uHa less gap
    cross_e2_per_egap = abs(ceg / c2)  # Ha e2 per Ha Egap (dimensionless)

    # Exact Newton check of (a): retarget e2, hold e1/Egap/ev58.
    target_a = np.array([e1_0, e2_new, Eg0, ev0])
    x = np.zeros(int(np.sum(w_mask)) + int(np.sum(wB_mask)))
    hist = []
    converged = False
    for it in range(15):
        dw, dwB = unpack(x)
        vals, gr = compute(w0 + dw, wB0 + dwB)
        res = np.array([vals[1], vals[2], vals[3], vals[4]]) - target_a
        hist.append(float(np.max(np.abs(res))))
        if hist[-1] < 1e-14:
            converged = True
            break
        Ait = np.vstack([pack(gr["e1"]), pack(gr["e2"]),
                         pack(gr["eg"]), pack(gr["ev"])])
        x = x - np.linalg.pinv(Ait) @ res
    dw, dwB = unpack(x)
    mp = dict(base_dict)
    mp["W"] = w0 + dw
    mp["H2_I"] = wB0 + dwB
    m = v.evaluate_words(v.load_inputs(mp), words0, tree, 8)
    dle_a_exact = float(m["lambda_eff"]) - le0

    result = {
        "baseline": {"e1_Ha": e1_0, "e2_Ha": e2_0, "Egap_Ha": Eg0,
                     "lambda_eff": le0},
        "kkt_recomputed_b9eced3e": {
            "dlam_de1": c1, "dlam_de2": c2, "dlam_dEgap": ceg,
            "dlam_dev58": cev, "proj_norm": proj_norm,
            "smooth_W": int(np.sum(w_mask)),
            "smooth_H2I": int(np.sum(wB_mask))},
        "exchange_a_e2_relax": {
            "from_mHa": e2_0 * 1e3, "to_mHa": e2_new * 1e3,
            "dt_Ha": dt_e2, "dlam_linear": dle_a,
            "dscore_linear": dscore(dle_a),
            "newton_exact_dlam": dle_a_exact,
            "newton_exact_dscore": dscore(dle_a_exact),
            "newton_converged": converged, "newton_iters": it + 1},
        "exchange_b_e1_relax": {
            "from_mHa": e1_0 * 1e3, "to_mHa": e1_new * 1e3,
            "dt_Ha": dt_e1, "dlam_linear": dle_b,
            "dscore_linear": dscore(dle_b)},
        "exchange_c_egap": {
            "dt_uHa": dt_eg * 1e6,
            "tighten_dlam_per_uHa": dle_c_tight,
            "tighten_dscore_per_uHa": dscore(dle_c_tight),
            "loosen_dscore_per_uHa": dscore(dle_c_loose),
            "e2_nHa_per_1uHa_egap": cross_e2_per_egap * 1e3,
            "e2_uHa_per_1uHa_egap": cross_e2_per_egap},
        "scope": "analytic Jacobian (linear) + one exact Newton check; no shots",
    }
    (out_dir / "budget_exchange.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
