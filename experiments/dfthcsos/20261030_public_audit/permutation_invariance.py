"""Check a structured B-axis reordering in decoded-vector algebra, not circuits."""

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors, reconstruct_x, lambda_h2

base = ROOT / "artifacts/20261030_public_best/candidate/dfthcsos/submission.npz"
with np.load(base, allow_pickle=False) as z:
    words, weights, h2_i, tree = (z[k] for k in ("angle_words", "W", "H2_I", "tree_edges"))
vectors = reconstruct_u_vectors(words / 128.0, tree)
r, b, c = weights.shape
n = vectors.shape[1]
two_body = vectors[n:].reshape(r, b, n)
permuted = two_body.copy()
new_weights = weights.copy()
blocks_per_rank = []
for rho in range(r):
    start, end = n + rho * b, n + (rho + 1) * b
    blocks = [np.arange(a, a + 16) - start for a in range(((start + 15) // 16) * 16, end - 15, 16)]
    permutation = np.arange(b)
    for target, source in zip(blocks, reversed(blocks)):
        permutation[target] = source
    permuted[rho] = two_body[rho, permutation]
    new_weights[rho] = weights[rho, permutation]
    blocks_per_rank.append(len(blocks))
old_offset = h2_i - weights.sum(axis=1)
new_offset = h2_i - new_weights.sum(axis=1)
old_x, new_x = reconstruct_x(two_body, weights), reconstruct_x(permuted, new_weights)
result = {
    "scope": "Deterministically reverse complete 16-address-aligned blocks within each rho, permute decoded two-body vector rows and W's B axis together. Boundary rows fixed. No circuit generated and no official scoring run.",
    "blocks_per_rank": blocks_per_rank,
    "max_abs_X_difference": float(np.max(np.abs(new_x - old_x))),
    "max_abs_native_offset_difference": float(np.max(np.abs(new_offset - old_offset))),
    "lambda_H2_difference": lambda_h2(new_weights, new_offset) - lambda_h2(weights, old_offset),
    "mathematical_invariance": "X, sums of w and absolute w, native offsets, h1_prime, lambda_H2, Lambda, E_SOS and errors are invariant in exact arithmetic. Differences measured here are floating-point summation order only.",
    "optimization_limit": "The old ANGLE circuits do not implement the new table. New circuits must be synthesized. Preserved low-bit ANF counts are not evidence of lower executed Toffolis."
}
out = ROOT / "artifacts/20261030_public_audit/dfthcsos/permutation_invariance.json"
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
