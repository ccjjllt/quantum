"""P0 step1: extract gengsr 303-flip pattern vs c1321 baseline, apply to b9eced3e.

Reads (read-only outside this experiment):
  worktree artifacts/20261108_public_frontier/release/dfthcsos/submission.npz (c1321df2)
  worktree artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz (b9eced3e)
  main repo  artifacts/20261110_gengsr_252268/release/dfthcsos/submission.npz (gengsr, read-only)
Official verifier code is imported read-only for decode + evaluate_words.

Writes (this experiment only):
  artifacts/20261110_p0_gauge/flip_rows.json
  artifacts/20261110_p0_gauge/new_angle_words.npy
  artifacts/20261110_p0_gauge/new_U.npy
  artifacts/20261110_p0_gauge/word_metrics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

WORKTREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKTREE / "data" / "competition" / "verifiers"))

from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors  # noqa: E402
from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

MAIN_REPO = Path("/Users/zhaohuaxiang/ccjjllt/quantum")
C1321 = WORKTREE / "artifacts/20261108_public_frontier/release/dfthcsos/submission.npz"
B9 = WORKTREE / "artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz"
GENGSR = MAIN_REPO / "artifacts/20261110_gengsr_252268/release/dfthcsos/submission.npz"
OUT = WORKTREE / "artifacts/20261110_p0_gauge"
OUT.mkdir(parents=True, exist_ok=True)

BROT = 8
N = 76


def main() -> None:
    base = np.load(C1321)
    b9 = np.load(B9)
    geng = np.load(GENGSR)
    edges = np.asarray(base["tree_edges"])

    # b9 must share the baseline words/U/tree for the pattern to transfer verbatim.
    assert np.array_equal(b9["angle_words"], base["angle_words"]), "b9 words != c1321 words"
    assert np.array_equal(b9["U"], base["U"]), "b9 U != c1321 U"
    assert np.array_equal(b9["tree_edges"], base["tree_edges"]), "tree mismatch"
    assert np.array_equal(geng["tree_edges"], base["tree_edges"]), "gengsr tree mismatch"

    vb = reconstruct_u_vectors(np.asarray(base["angle_words"]) / (1 << (BROT - 1)), edges)
    vg = reconstruct_u_vectors(np.asarray(geng["angle_words"]) / (1 << (BROT - 1)), edges)
    vb /= np.linalg.norm(vb, axis=1, keepdims=True)
    vg /= np.linalg.norm(vg, axis=1, keepdims=True)
    dots = np.einsum("ij,ij->i", vb, vg)
    dev = np.minimum(np.abs(dots - 1.0), np.abs(dots + 1.0))
    flips = [int(i) for i in np.where(dots < 0)[0]]
    plus = int(np.sum(dots > 0))
    print(f"dots: +1 x{plus}, -1 x{len(flips)}, maxdev={float(dev.max()):.3g}")
    assert plus + len(flips) == 1220 and len(flips) == 303, (plus, len(flips))
    assert float(dev.max()) < 1e-14, float(dev.max())

    one_body = [r for r in flips if r < N]
    two_body = [r for r in flips if r >= N]
    print(f"flips: one-body {len(one_body)}, two-body {len(two_body)}")

    # Verify gengsr U rows are exact negations on flipped two-body rows.
    R, B = 8, 143
    for r in two_body:
        rho, b = (r - N) // B, (r - N) % B
        a, c = np.asarray(base["U"][rho, b]), np.asarray(geng["U"][rho, b])
        assert np.array_equal(c, -a) or np.allclose(c, -a, atol=0), r
    # Non-flipped two-body U rows must be identical.
    flat_flip = set(flips)
    for r in range(N, N + R * B):
        if r in flat_flip:
            continue
        rho, b = (r - N) // B, (r - N) % B
        assert np.array_equal(base["U"][rho, b], geng["U"][rho, b]), f"nonflip U differs at row {r}"

    # New word table: full gengsr copy (= b9 words + 303 flips + 382 don't-care word
    # variants that decode to identical vectors; see README §1/§4).
    new_words = np.asarray(geng["angle_words"]).copy()
    new_U = np.asarray(geng["U"]).copy()  # == b9 U with flipped two-body rows negated
    # Sanity: hybrid (b9 words with only flip rows replaced by gengsr rows) differs
    # from full copy only on don't-care rows; both decode identically.
    hybrid = np.asarray(b9["angle_words"]).copy()
    hybrid[flips] = new_words[flips]
    vh = reconstruct_u_vectors(hybrid / (1 << (BROT - 1)), edges)
    vn = reconstruct_u_vectors(new_words / (1 << (BROT - 1)), edges)
    vh /= np.linalg.norm(vh, axis=1, keepdims=True)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True)
    assert np.max(np.abs(vh - vn)) < 1e-12, np.max(np.abs(vh - vn))
    print(f"hybrid-vs-full max vec diff: {float(np.max(np.abs(vh - vn))):.3g} (don't-care only)")

    np.save(OUT / "new_angle_words.npy", new_words)
    np.save(OUT / "new_U.npy", new_U)
    (OUT / "flip_rows.json").write_text(json.dumps({"count": len(flips), "rows": flips,
                                                    "one_body": len(one_body),
                                                    "two_body": len(two_body)}, indent=2) + "\n")

    inp_b9 = load_inputs(str(B9))
    m_new = evaluate_words(inp_b9, new_words, edges, BROT)
    inp_b9b = load_inputs(str(B9))
    m_base = evaluate_words(inp_b9b, np.asarray(b9["angle_words"]), edges, BROT)
    rec = {}
    for label, m in (("b9_baseline_b9w", m_base), ("b9_inputs_new_words", m_new)):
        rec[label] = {k: (float(m[k]) if isinstance(m[k], (float, np.floating)) else m[k])
                      for k in ("error_1", "error_2", "Lambda", "E_SOS", "E_gap", "lambda_eff", "gap_in_domain")}
    rec["gates"] = {"error_1_mHa": 20.0, "error_2_mHa": 20.0, "Lambda_floor": 49.0,
                    "E_gap_floor_Ha": 3.914898}
    rec["pass_gates_new"] = bool(m_new["error_1"] <= 0.020 and m_new["error_2"] <= 0.020
                                 and m_new["gap_in_domain"] and np.isfinite(m_new["lambda_eff"])
                                 and float(m_new["Lambda"]) > 49.0 and float(m_new["E_gap"]) > 3.914898)
    (OUT / "word_metrics.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
