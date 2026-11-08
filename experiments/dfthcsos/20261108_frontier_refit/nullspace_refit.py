from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_nullspace_refit(
    in_npz: Path,
    words_npy: Path,
    out_dir: Path,
    verifier_dir: Path,
    loader_dir: Path | None = None,
    step: float = 4.0e-7,
    target_margin_ha: float = 2.5e-11,
) -> dict:
    sys.path.insert(0, str(verifier_dir))
    import verify as v  # noqa: E402
    from scoreinfra import dfthc_math  # noqa: E402

    d = np.load(in_npz)
    words = np.load(words_npy)
    tree_edges = d["tree_edges"].copy()
    inp = v.load_inputs(in_npz)

    angles = np.asarray(words, dtype=np.float64) / (2 ** (8 - 1))
    u_all = dfthc_math.reconstruct_u_vectors(angles, tree_edges)
    u_all = u_all / np.linalg.norm(u_all, axis=1, keepdims=True)
    one_body_vecs, u_b_rho = dfthc_math.split_u_vectors(u_all, inp.w)
    oei = np.asarray(inp.ref["oei"], dtype=np.float64)
    tei = np.asarray(inp.ref["tei"], dtype=np.float64)
    h1_thc = oei - 0.5 * np.einsum("prrq->pq", tei)

    def compute_all_and_grads_wB(
        w: np.ndarray, w_B: np.ndarray
    ) -> tuple[tuple[float, float, float, float, float, float], dict | None]:
        W_rc = w_B - np.sum(w, axis=1)
        X_rc = dfthc_math.reconstruct_x(u_b_rho, w)
        X_rc = np.tril(X_rc) + np.swapaxes(np.tril(X_rc, k=-1), -1, -2)
        h1_p = dfthc_math.build_h1_prime(
            h1_thc, inp.S, inp.beta_1, inp.ref["electrons"], W_rc, X_rc
        )
        ev, evec = np.linalg.eigh(h1_p)
        j0 = 58
        overlaps = np.abs(one_body_vecs @ evec)
        q_idx, i_idx = dfthc_math.linear_sum_assignment(-overlaps)
        matched_ev = np.empty_like(ev)
        matched_ev[q_idx] = ev[i_idx]
        h1_qrom = np.einsum(
            "j,jp,jq->pq", matched_ev, one_body_vecs, one_body_vecs, optimize=True
        )
        recon = (
            h1_qrom
            + 0.5 * inp.ref["electrons"] * inp.S
            - inp.beta_1 * np.eye(76)
            + np.einsum("rc,rcpq->pq", W_rc, X_rc, optimize=True)
        )
        diff1 = recon - h1_thc
        err1 = float(np.linalg.norm(diff1))
        R1 = diff1 / err1

        h2_delta = dfthc_math.reconstruct_h2(X_rc) - tei
        diag = np.arange(76)
        h2_delta[:, :, diag, diag] -= 0.5 * inp.S[:, :, None]
        h2_delta[diag, diag, :, :] -= 0.5 * inp.S[None, :, :]
        err2 = float(np.linalg.norm(h2_delta.ravel()))

        signs = np.sign(ev)
        signs[j0] = 1.0
        lam_h1 = float(np.sum(signs * ev))
        l1_w = np.linalg.norm(w, ord=1, axis=1)
        L_rc = l1_w + np.abs(w_B)
        lam_h2 = float(0.25 * np.sum(L_rc**2))
        Lam = lam_h1 + lam_h2
        E_SOS = float(
            inp.ref["ecore"]
            - inp.ref["electrons"] * inp.beta_1
            - (lam_h1 - np.sum(ev))
            - 0.5 * np.sum(W_rc**2)
        )
        E_gap = float(inp.energy_upper - E_SOS)
        lam_eff = float(np.sqrt(E_gap * (2.0 * Lam - E_gap)))

        v_j0 = evec[:, j0]
        P_j0 = np.outer(v_j0, v_j0)
        gW_ev = -np.einsum("rcpq,pq->rc", X_rc, P_j0)
        gX_ev = -W_rc[:, :, None, None] * P_j0[None, None, :, :]

        D_sign = np.einsum("j,pj,qj->pq", signs, evec, evec)
        D_neg = np.einsum("j,pj,qj->pq", signs - 1.0, evec, evec)
        gW_eg = W_rc - np.einsum("rcpq,pq->rc", X_rc, D_neg)
        gX_eg = -W_rc[:, :, None, None] * D_neg[None, None, :, :]

        sig_B = np.sign(w_B)
        gW_Lam = -np.einsum("rcpq,pq->rc", X_rc, D_sign)
        gwB_Lam_direct = 0.5 * L_rc * sig_B
        gX_Lam = -W_rc[:, :, None, None] * D_sign[None, None, :, :]
        gw_Lam_direct = 0.5 * L_rc[:, None, :] * np.sign(w)

        d_le_d_eg = (Lam - E_gap) / lam_eff
        d_le_d_Lam = E_gap / lam_eff
        gW_le = d_le_d_eg * gW_eg + d_le_d_Lam * gW_Lam
        gwB_le_direct = d_le_d_Lam * gwB_Lam_direct
        gX_le = d_le_d_eg * gX_eg + d_le_d_Lam * gX_Lam
        gw_le_direct = d_le_d_Lam * gw_Lam_direct

        c_qrom = np.einsum("jp,pq,jq->j", one_body_vecs, R1, one_body_vecs)
        c_ev = np.zeros(76)
        c_ev[i_idx] = c_qrom[q_idx]
        D_e1 = np.einsum("j,pj,qj->pq", c_ev, evec, evec)
        M_e1 = R1 - D_e1
        gW_e1 = np.einsum("rcpq,pq->rc", X_rc, M_e1)
        gX_e1 = W_rc[:, :, None, None] * M_e1[None, None, :, :]

        gX_e2 = (2.0 / err2) * np.einsum(
            "pqkl,rckl->rcpq", h2_delta, X_rc, optimize=True
        )
        gW_e2 = np.zeros_like(W_rc)

        def x_to_w(gX: np.ndarray, gW: np.ndarray) -> np.ndarray:
            return (
                np.einsum("rcpq,rbp,rbq->rbc", gX, u_b_rho, u_b_rho, optimize=True)
                - gW[:, None, :]
            )

        gw_ev = x_to_w(gX_ev, gW_ev)
        gw_eg = x_to_w(gX_eg, gW_eg)
        gw_le = x_to_w(gX_le, gW_le) + gw_le_direct
        gw_e1 = x_to_w(gX_e1, gW_e1)
        gw_e2 = x_to_w(gX_e2, gW_e2)

        return (lam_eff, err1, err2, E_gap, float(ev[j0]), Lam), {
            "le": (gw_le, gW_le + gwB_le_direct),
            "e1": (gw_e1, gW_e1),
            "e2": (gw_e2, gW_e2),
            "eg": (gw_eg, gW_eg),
            "ev": (gw_ev, gW_ev),
        }

    w0 = d["W"].copy()
    wB0 = d["H2_I"].copy()
    vals0, grads = compute_all_and_grads_wB(w0, wB0)
    assert grads is not None
    w_mask = np.abs(w0) > 1e-12
    wB_mask = np.abs(wB0) > 1e-12

    def pack(pair: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        return np.concatenate([pair[0][w_mask], pair[1][wB_mask]])

    def unpack(vec: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nw = int(np.sum(w_mask))
        dw = np.zeros_like(w0)
        dwB = np.zeros_like(wB0)
        dw[w_mask] = vec[:nw]
        dwB[wB_mask] = vec[nw:]
        return dw, dwB

    g_le = pack(grads["le"])
    A = np.vstack(
        [
            pack(grads["e1"]),
            pack(grads["e2"]),
            pack(grads["eg"]),
            pack(grads["ev"]),
        ]
    )
    coeffs = np.linalg.lstsq(A.T, g_le, rcond=None)[0]
    proj = g_le - A.T @ coeffs
    proj_norm = float(np.linalg.norm(proj))
    d_null = -proj / proj_norm
    A_pinv = np.linalg.pinv(A)

    # First evaluate pure nullspace step at identical gate margins
    target_same = np.array([vals0[1], vals0[2], vals0[3], vals0[4]], dtype=np.float64)
    x_same = step * d_null
    for _ in range(4):
        dw_s, dwB_s = unpack(x_same)
        v_s, _ = compute_all_and_grads_wB(w0 + dw_s, wB0 + dwB_s)
        res_s = np.array([v_s[1], v_s[2], v_s[3], v_s[4]]) - target_same
        if float(np.max(np.abs(res_s))) < 1e-14:
            break
        x_same -= A_pinv @ res_s
    dw_s, dwB_s = unpack(x_same)
    vals_same, _ = compute_all_and_grads_wB(w0 + dw_s, wB0 + dwB_s)

    # Next evaluate nullspace step + tighter safe gate margins
    target_tight = np.array(
        [
            0.02 - target_margin_ha,
            0.02 - target_margin_ha,
            3.914898 + target_margin_ha,
            0.0,
        ],
        dtype=np.float64,
    )
    x_tight = step * d_null
    for _ in range(4):
        dw_t, dwB_t = unpack(x_tight)
        v_t, _ = compute_all_and_grads_wB(w0 + dw_t, wB0 + dwB_t)
        res_t = np.array([v_t[1], v_t[2], v_t[3], v_t[4]]) - target_tight
        if float(np.max(np.abs(res_t))) < 1e-14:
            break
        x_tight -= A_pinv @ res_t
    dw_t, dwB_t = unpack(x_tight)
    w_best = w0 + dw_t
    wB_best = wB0 + dwB_t
    vals_best, _ = compute_all_and_grads_wB(w_best, wB_best)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_npz = out_dir / "submission.npz"
    save_dict = {k: d[k].copy() for k in d.keys()}
    save_dict["W"] = w_best
    save_dict["H2_I"] = wB_best
    np.savez(out_npz, **save_dict)

    if loader_dir is not None:
        for k in range(15):
            src_kmb = (loader_dir / f"angle_k_{k}.kmb").resolve()
            dst_kmb = out_dir / f"angle_k_{k}.kmb"
            if dst_kmb.exists() or dst_kmb.is_symlink():
                dst_kmb.unlink()
            os.symlink(src_kmb, dst_kmb)

    toffoli_per_step = 14966
    num_qubits = 427
    score_0 = toffoli_per_step * num_qubits * vals0[0]
    score_same = toffoli_per_step * num_qubits * vals_same[0]
    score_best = toffoli_per_step * num_qubits * vals_best[0]

    summary = {
        "input_npz": str(in_npz),
        "input_sha256": sha256_file(in_npz),
        "output_npz": str(out_npz),
        "output_sha256": sha256_file(out_npz),
        "step": step,
        "target_margin_ha": target_margin_ha,
        "smooth_support": {
            "W_nnz": int(np.sum(w_mask)),
            "W_total": int(w_mask.size),
            "H2_I_nnz": int(np.sum(wB_mask)),
            "H2_I_total": int(wB_mask.size),
        },
        "kkt_multipliers_err1_err2_egap_ev58": [float(x) for x in coeffs],
        "projected_gradient_norm": proj_norm,
        "baseline": {
            "error_1_ha": vals0[1],
            "error_2_ha": vals0[2],
            "e_gap_ha": vals0[3],
            "ev58_ha": vals0[4],
            "Lambda": vals0[5],
            "lambda_eff": vals0[0],
            "exact_score": score_0,
        },
        "same_margin_nullspace": {
            "error_1_ha": vals_same[1],
            "error_2_ha": vals_same[2],
            "e_gap_ha": vals_same[3],
            "ev58_ha": vals_same[4],
            "Lambda": vals_same[5],
            "lambda_eff": vals_same[0],
            "exact_score": score_same,
            "delta_lambda_eff": vals_same[0] - vals0[0],
            "delta_score": score_same - score_0,
        },
        "refit": {
            "error_1_ha": vals_best[1],
            "error_2_ha": vals_best[2],
            "e_gap_ha": vals_best[3],
            "ev58_ha": vals_best[4],
            "Lambda": vals_best[5],
            "lambda_eff": vals_best[0],
            "exact_score": score_best,
            "delta_lambda_eff": vals_best[0] - vals0[0],
            "delta_score": score_best - score_0,
        },
    }
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analytical KKT nullspace + margin refit on Public Frontier dfthcsos submission.npz"
    )
    parser.add_argument(
        "--in-npz",
        type=Path,
        default=Path(
            "artifacts/20261108_public_frontier/release/dfthcsos/submission.npz"
        ),
    )
    parser.add_argument(
        "--words-npy",
        type=Path,
        default=Path("artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy"),
    )
    parser.add_argument(
        "--loader-dir",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/release/dfthcsos"),
    )
    parser.add_argument(
        "--verifier-dir",
        type=Path,
        default=Path("data/competition/verifiers/dfthcsos"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/dfthcsos_refit"),
    )
    parser.add_argument("--step", type=float, default=4.0e-7)
    parser.add_argument("--target-margin-ha", type=float, default=2.5e-11)
    args = parser.parse_args()

    summary = run_nullspace_refit(
        in_npz=args.in_npz,
        words_npy=args.words_npy,
        out_dir=args.out_dir,
        verifier_dir=args.verifier_dir,
        loader_dir=args.loader_dir,
        step=args.step,
        target_margin_ha=args.target_margin_ha,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
