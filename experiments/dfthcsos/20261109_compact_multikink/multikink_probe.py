"""Multi-kink pinning + angle_words LSB probe (exact arithmetic only).

Reproduces, with the official dfthc_math kernels:
1. h1' spectrum at b9eced3e (2nd/3rd smallest |lambda|).
2. Ideal kink gains (zeroing eigenvalues) and why negatives violate E_gap floor.
3. Single-LSB flip sensitivity via verify.evaluate_words (no shots).
4. Constrained (KKT nullspace) push of ev59 with Newton retraction.

No verifier shots, no new circuits, no submission.npz output.
Numbers are printed and saved to artifacts/20261109_compact_multikink/.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data" / "competition" / "verifiers" / "dfthcsos"))
import verify as v  # noqa: E402
from scoreinfra import dfthc_math  # noqa: E402


CAND = ROOT / "artifacts" / "20261108_public_frontier" / "dfthcsos_refit" / "submission.npz"
WORDS = ROOT / "artifacts" / "20261106_syed_v9" / "dfthcsos" / "recovered_words.npy"
TREE_SRC = ROOT / "artifacts" / "20261108_public_frontier" / "release" / "dfthcsos" / "submission.npz"
TQ = 14966 * 427


def load_all():
    inp = v.load_inputs(CAND)
    words = np.load(WORDS)
    tree = np.load(TREE_SRC)["tree_edges"]
    angles = np.asarray(words, dtype=np.float64) / (2 ** 7)
    u_all = dfthc_math.reconstruct_u_vectors(angles, tree)
    u_all = u_all / np.linalg.norm(u_all, axis=1, keepdims=True)
    ob, ub = dfthc_math.split_u_vectors(u_all, inp.w)
    d = np.load(CAND)
    w0 = d["W"].copy()
    wB0 = d["H2_I"].copy()
    oei = np.asarray(inp.ref["oei"], dtype=np.float64)
    tei = np.asarray(inp.ref["tei"], dtype=np.float64)
    h1_thc = oei - 0.5 * np.einsum("prrq->pq", tei)
    return inp, words, tree, ob, ub, w0, wB0, h1_thc


def full_metrics(inp, ob, ub, h1_thc, w, wB):
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
    h2d = dfthc_math.reconstruct_h2(Xrc) - np.asarray(inp.ref["tei"])
    diag = np.arange(76)
    h2d[:, :, diag, diag] -= 0.5 * inp.S[:, :, None]
    h2d[diag, diag, :, :] -= 0.5 * inp.S[None, :, :]
    err2 = float(np.linalg.norm(h2d.ravel()))
    signs = np.sign(ev)
    signs[58] = 1.0
    lam_h1 = float(np.sum(signs * ev))
    Lrc = np.linalg.norm(w, ord=1, axis=1) + np.abs(wB)
    lam_h2 = float(0.25 * np.sum(Lrc**2))
    Lam = lam_h1 + lam_h2
    Esos = float(inp.ref["ecore"] - inp.ref["electrons"] * inp.beta_1
                 - (lam_h1 - np.sum(ev)) - 0.5 * np.sum(Wrc**2))
    Egap = float(inp.energy_upper - Esos)
    le = float(np.sqrt(Egap * (2 * Lam - Egap)))
    return (le, err1, err2, Egap, ev, Lam), (evec, Wrc, Xrc)


def main() -> None:
    out_dir = ROOT / "artifacts" / "20261109_compact_multikink"
    out_dir.mkdir(parents=True, exist_ok=True)
    inp, words, tree, ob, ub, w0, wB0, h1_thc = load_all()
    base = v.evaluate_words(inp, words, tree, 8)
    vals, _ = full_metrics(inp, ob, ub, h1_thc, w0, wB0)
    le0, e1_0, e2_0, Eg0, ev0, Lam0 = vals
    order = np.argsort(np.abs(ev0))
    spectrum = [{"rank": int(r), "j": int(j), "ev_Ha": float(ev0[j]),
                 "ev_mHa": float(ev0[j] * 1000.0)}
                for r, j in enumerate(order[:8])]

    # Ideal kink gains (keep everything else fixed).
    ideals = []
    for ek in [ev0[59], ev0[57], ev0[56], ev0[60]]:
        lam_h2 = Lam0 - float(np.sum(np.abs(ev0)))
        lam1p = float(np.sum(np.abs(ev0))) - abs(float(ek))
        Lamp = lam1p + lam_h2
        d_sos = abs(float(ek)) - float(ek)
        Egp = Eg0 - d_sos
        lep = math.sqrt(Egp * (2 * Lamp - Egp)) if Egp > 0 else float("nan")
        ideals.append({"ek_mHa": float(ek * 1000.0), "dscore_ideal": (lep - le0) * TQ,
                       "Egap_new": Egp,
                       "violates_Egap_floor": bool(Egp <= 3.914898)})

    # Single-LSB sensitivity (exact evaluate_words, no shots).
    lsb = []
    for (r, c) in [(76, 0), (76, 74), (500, 37), (1219, 74), (0, 0), (37, 10)]:
        for dd in (+1, -1):
            if r == 76 and c == 0 and dd == -1:
                pass
            w2 = words.copy()
            nv = int(w2[r, c]) + dd
            if nv < 0 or nv > 255:
                continue
            w2[r, c] = nv
            m = v.evaluate_words(inp, w2, tree, 8)
            lsb.append({
                "r": r, "c": c, "d": dd,
                "de1_uHa": (m["error_1"] - base["error_1"]) * 1e6,
                "de2_uHa": (m["error_2"] - base["error_2"]) * 1e6,
                "dle_uHa": (m["lambda_eff"] - base["lambda_eff"]) * 1e6,
                "pass_20mHa": bool(m["error_1"] <= 0.02 and m["error_2"] <= 0.02),
            })

    (out_dir / "multikink_probe.json").write_text(json.dumps({
        "candidate": str(CAND),
        "base_exact": {"error_1_Ha": e1_0, "error_2_Ha": e2_0,
                       "E_gap_Ha": Eg0, "Lambda": Lam0, "lambda_eff": le0},
        "spectrum_smallest_abs": spectrum,
        "ideal_kink_gains": ideals,
        "lsb_sensitivity_uHa": lsb,
        "scope": "exact arithmetic only (evaluate_words + dfthc_math); no kickmix shots",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"base_le": le0, "spectrum": spectrum,
                      "ideals": ideals, "lsb": lsb}, indent=2))


if __name__ == "__main__":
    main()
