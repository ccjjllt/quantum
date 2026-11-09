"""Joint W + 1-LSB Newton retraction probe (exact arithmetic only).

Starting point: b9eced3e (artifacts/20261108_public_frontier/dfthcsos_refit/
submission.npz), fixed tree, fixed brot=8.
Experiment: flip ONE angle LSB (r76c74 +1, the min-|de1| candidate from
multikink_probe.json: de1=+3.96uHa, de2=+0.23uHa, dle=-57.7uHa), then
Newton-retract the 40549+349 smooth W/H2_I coordinates to restore the four
gate constraints (e1/e2/E_gap/lambda58) to baseline. Measures whether W can
absorb the +3.96uHa error for <100uHa lambda cost while keeping part of the
-57uHa gain.

Second candidate r1219c74 +1 (dle=-258uHa, de1=+9.75uHa) is probed with the
same machinery as a contrast row.

No verifier shots, no new circuits, no submission.npz output.
Results -> artifacts/20261109_joint_budget/joint_newton.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers" / "dfthcsos"))
import verify as v  # noqa: E402
from scoreinfra import dfthc_math  # noqa: E402

CAND = ROOT / "artifacts" / "20261108_public_frontier" / "dfthcsos_refit" / "submission.npz"
WORDS = ROOT / "artifacts" / "20261106_syed_v9" / "dfthcsos" / "recovered_words.npy"
TQ = 14966 * 427
J0 = 58  # pinned spectral kink index


def decode(words, tree):
    angles = np.asarray(words, dtype=np.float64) / 128.0
    u_all = dfthc_math.reconstruct_u_vectors(angles, tree)
    return u_all / np.linalg.norm(u_all, axis=1, keepdims=True)


def build(inp, ob, ub, h1_thc):
    """Closure factory: exact metrics + analytic W-grads for fixed (ob, ub)."""
    tei = np.asarray(inp.ref["tei"], dtype=np.float64)

    def compute(w, wB):
        Wrc = wB - np.sum(w, axis=1)
        Xrc = dfthc_math.reconstruct_x(ub, w)
        Xrc = np.tril(Xrc) + np.swapaxes(np.tril(Xrc, k=-1), -1, -2)
        h1p = dfthc_math.build_h1_prime(
            h1_thc, inp.S, inp.beta_1, inp.ref["electrons"], Wrc, Xrc)
        ev, evec = np.linalg.eigh(h1p)
        overlaps = np.abs(ob @ evec)
        q_idx, i_idx = dfthc_math.linear_sum_assignment(-overlaps)
        matched = np.empty_like(ev)
        matched[q_idx] = ev[i_idx]
        h1_qrom = np.einsum("j,jp,jq->pq", matched, ob, ob, optimize=True)
        recon = (h1_qrom + 0.5 * inp.ref["electrons"] * inp.S
                 - inp.beta_1 * np.eye(76)
                 + np.einsum("rc,rcpq->pq", Wrc, Xrc, optimize=True))
        diff1 = recon - h1_thc
        err1 = float(np.linalg.norm(diff1))
        R1 = diff1 / err1
        h2d = dfthc_math.reconstruct_h2(Xrc) - tei
        diag = np.arange(76)
        h2d[:, :, diag, diag] -= 0.5 * inp.S[:, :, None]
        h2d[diag, diag, :, :] -= 0.5 * inp.S[None, :, :]
        err2 = float(np.linalg.norm(h2d.ravel()))
        signs = np.sign(ev)
        signs[J0] = 1.0
        lam_h1 = float(np.sum(signs * ev))
        Lrc = np.linalg.norm(w, ord=1, axis=1) + np.abs(wB)
        lam_h2 = float(0.25 * np.sum(Lrc**2))
        Lam = lam_h1 + lam_h2
        Esos = float(inp.ref["ecore"] - inp.ref["electrons"] * inp.beta_1
                     - (lam_h1 - np.sum(ev)) - 0.5 * np.sum(Wrc**2))
        Egap = float(inp.energy_upper - Esos)
        le = float(np.sqrt(Egap * (2.0 * Lam - Egap)))

        # --- analytic gradients (same derivation as nullspace_refit.py) ---
        v_j0 = evec[:, J0]
        P_j0 = np.outer(v_j0, v_j0)
        gW_ev = -np.einsum("rcpq,pq->rc", Xrc, P_j0)
        gX_ev = -Wrc[:, :, None, None] * P_j0[None, None, :, :]
        D_sign = np.einsum("j,pj,qj->pq", signs, evec, evec)
        D_neg = np.einsum("j,pj,qj->pq", signs - 1.0, evec, evec)
        gW_eg = Wrc - np.einsum("rcpq,pq->rc", Xrc, D_neg)
        gX_eg = -Wrc[:, :, None, None] * D_neg[None, None, :, :]
        sig_B = np.sign(wB)
        gW_Lam = -np.einsum("rcpq,pq->rc", Xrc, D_sign)
        gwB_Lam_direct = 0.5 * Lrc * sig_B
        gX_Lam = -Wrc[:, :, None, None] * D_sign[None, None, :, :]
        gw_Lam_direct = 0.5 * Lrc[:, None, :] * np.sign(w)
        d_le_d_eg = (Lam - Egap) / le
        d_le_d_Lam = Egap / le
        gW_le = d_le_d_eg * gW_eg + d_le_d_Lam * gW_Lam
        gwB_le_direct = d_le_d_Lam * gwB_Lam_direct
        gX_le = d_le_d_eg * gX_eg + d_le_d_Lam * gX_Lam
        gw_le_direct = d_le_d_Lam * gw_Lam_direct
        c_qrom = np.einsum("jp,pq,jq->j", ob, R1, ob)
        c_ev = np.zeros(76)
        c_ev[i_idx] = c_qrom[q_idx]
        D_e1 = np.einsum("j,pj,qj->pq", c_ev, evec, evec)
        M_e1 = R1 - D_e1
        gW_e1 = np.einsum("rcpq,pq->rc", Xrc, M_e1)
        gX_e1 = Wrc[:, :, None, None] * M_e1[None, None, :, :]
        gX_e2 = (2.0 / err2) * np.einsum("pqkl,rckl->rcpq", h2d, Xrc, optimize=True)
        gW_e2 = np.zeros_like(Wrc)

        def x_to_w(gX, gW):
            return (np.einsum("rcpq,rbp,rbq->rbc", gX, ub, ub, optimize=True)
                    - gW[:, None, :])

        grads = {
            "le": (x_to_w(gX_le, gW_le) + gw_le_direct, gW_le + gwB_le_direct),
            "e1": (x_to_w(gX_e1, gW_e1), gW_e1),
            "e2": (x_to_w(gX_e2, gW_e2), gW_e2),
            "eg": (x_to_w(gX_eg, gW_eg), gW_eg),
            "ev": (x_to_w(gX_ev, gW_ev), gW_ev),
        }
        return (le, err1, err2, Egap, float(ev[J0]), Lam), grads

    return compute


def main() -> None:
    out_dir = ROOT / "artifacts" / "20261109_joint_budget"
    out_dir.mkdir(parents=True, exist_ok=True)
    d = np.load(CAND)
    base_dict = {k: np.asarray(d[k]) for k in d.files}
    words0 = np.load(WORDS)
    tree = np.load(CAND)["tree_edges"].copy() if "tree_edges" in d else None
    if tree is None:
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
    compute0 = build(inp, ob0, ub0, h1_thc)
    base, g0 = compute0(w0, wB0)
    le0, e1_0, e2_0, Eg0, ev0, Lam0 = base
    # cross-check against official kernel
    chk = v.evaluate_words(inp, words0, tree, 8)
    assert abs(chk["error_1"] - e1_0) < 1e-12, (chk["error_1"], e1_0)
    assert abs(chk["error_2"] - e2_0) < 1e-12, (chk["error_2"], e2_0)
    assert abs(chk["lambda_eff"] - le0) < 1e-9, (chk["lambda_eff"], le0)

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

    target = np.array([e1_0, e2_0, Eg0, ev0])
    rows = []
    base_row = {"case": "baseline b9eced3e", "e1_Ha": e1_0, "e2_Ha": e2_0,
                "Egap_Ha": Eg0, "Lambda": Lam0, "lambda_eff": le0,
                "dscore": 0.0}
    rows.append(base_row)

    def official(w_new, wB_new, words_new):
        """Official kernel numbers at arbitrary (W, words); exact, no shots."""
        mp = dict(base_dict)
        mp["W"] = np.asarray(w_new)
        mp["H2_I"] = np.asarray(wB_new)
        inp2 = v.load_inputs(mp)
        m = v.evaluate_words(inp2, np.asarray(words_new), tree, 8)
        return {k: float(m[k]) for k in
                ("error_1", "error_2", "Lambda", "E_gap", "lambda_eff")}

    def retract(compute2, w0, wB0, target_vec, rows_keys, pack, unpack,
                maxit=15, tol=1e-14):
        x = np.zeros(int(np.sum(w_mask)) + int(np.sum(wB_mask)))
        hist = []
        converged = False
        it = 0
        for it in range(maxit):
            dw, dwB = unpack(x)
            vals, grads = compute2(w0 + dw, wB0 + dwB)
            cur = np.array([vals[1], vals[2], vals[3], vals[4]])
            if len(target_vec) == 3:
                cur = cur[:3]
            res = cur - target_vec
            hist.append(float(np.max(np.abs(res))))
            if hist[-1] < tol:
                converged = True
                break
            Arows = [pack(grads["e1"]), pack(grads["e2"]), pack(grads["eg"])]
            if len(target_vec) == 4:
                Arows.append(pack(grads["ev"]))
            A = np.vstack(Arows)
            x = x - np.linalg.pinv(A) @ res
        dw, dwB = unpack(x)
        w_move_fro = float(np.sqrt(np.sum(dw**2) + np.sum(dwB**2)))
        w_move_max = float(np.max(np.abs(np.concatenate(
            [dw.ravel(), dwB.ravel()]))))
        return (w0 + dw, wB0 + dwB, it + 1, converged, hist,
                w_move_fro, w_move_max)

    for (r, c, dd, tag) in [(76, 74, 1, "r76c74+1 (primary)"),
                            (1219, 74, 1, "r1219c74+1 (contrast)")]:
        words2 = words0.copy()
        words2[r, c] = int(words2[r, c]) + dd
        u2 = decode(words2, tree)
        ob2, ub2 = dfthc_math.split_u_vectors(u2, inp.w)
        compute2 = build(inp, ob2, ub2, h1_thc)
        off_flip = official(w0, wB0, words2)
        rows.append({"case": tag + " W-only (no retraction) OFFICIAL",
                     "e1_Ha": off_flip["error_1"], "e2_Ha": off_flip["error_2"],
                     "Egap_Ha": off_flip["E_gap"], "Lambda": off_flip["Lambda"],
                     "lambda_eff": off_flip["lambda_eff"],
                     "dscore": (off_flip["lambda_eff"] - le0) * TQ})
        # Variant (a): restore all 4 model gates (kink-preserving).
        w_a, wB_a, n_a, conv_a, hist_a, fro_a, mx_a = retract(
            compute2, w0, wB0, target, None, pack, unpack)
        off_a = official(w_a, wB_a, words2)
        rows.append({"case": tag + " + W Newton (4 gates, kink kept) OFFICIAL",
                     "e1_Ha": off_a["error_1"], "e2_Ha": off_a["error_2"],
                     "Egap_Ha": off_a["E_gap"], "Lambda": off_a["Lambda"],
                     "lambda_eff": off_a["lambda_eff"],
                     "dscore": (off_a["lambda_eff"] - le0) * TQ,
                     "newton_iters": n_a, "converged_1e14": conv_a,
                     "maxres_Ha": hist_a[-1], "res_hist": hist_a,
                     "w_move_fro": fro_a, "w_move_max": mx_a})
        # Variant (b): retract only the 3 true verifier gates, kink free.
        w_b, wB_b, n_b, conv_b, hist_b, fro_b, mx_b = retract(
            compute2, w0, wB0, target[:3], None, pack, unpack)
        off_b = official(w_b, wB_b, words2)
        rows.append({"case": tag + " + W Newton (3 gates, kink free) OFFICIAL",
                     "e1_Ha": off_b["error_1"], "e2_Ha": off_b["error_2"],
                     "Egap_Ha": off_b["E_gap"], "Lambda": off_b["Lambda"],
                     "lambda_eff": off_b["lambda_eff"],
                     "dscore": (off_b["lambda_eff"] - le0) * TQ,
                     "newton_iters": n_b, "converged_1e14": conv_b,
                     "maxres_Ha": hist_b[-1], "res_hist": hist_b,
                     "w_move_fro": fro_b, "w_move_max": mx_b})

    (out_dir / "joint_newton.json").write_text(
        json.dumps({"TQ": TQ, "target": target.tolist(),
                    "smooth_W": int(np.sum(w_mask)),
                    "smooth_H2I": int(np.sum(wB_mask)),
                    "rows": rows,
                    "scope": "exact arithmetic only; no kickmix shots"},
                   indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
