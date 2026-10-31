"""Recover one trajectory per address and inspect the submitted angle-word structure.

This is a reduced-shot diagnostic, not full official validation. ANF statistics
are a structural proxy, not synthesized Toffoli counts.
"""

import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data/competition/verifiers"))
from dfthcsos.scoreinfra.circuits import load_circuits, recover_words_from_circuits

BASE = ROOT / "artifacts/20261030_public_best/candidate/dfthcsos"
OUT = ROOT / "artifacts/20261030_public_audit/dfthcsos"
with np.load(BASE / "submission.npz", allow_pickle=False) as z:
    saved_words = z["angle_words"]
circuits = load_circuits(BASE)
start = time.monotonic()
words, layout, toffoli = recover_words_from_circuits(
    circuits, num_vectors=1220, num_angles=75, shots_per_address=1, seed=20261030
)
scope = {"scope": "One shot per address, all 1220 addresses, forward/reverse circuit family; not full default validation",
         "seed": 20261030, "shots": 1220, "seconds": time.monotonic() - start,
         "npz_table_matches_recovered_words": bool(np.array_equal(words, saved_words)),
         "brot": layout.brot, "J": layout.batch_size, "double_pass_Toffoli": toffoli}
if not scope["npz_table_matches_recovered_words"]:
    raise ValueError("Saved words differ from simulated circuit outputs")
np.save(OUT / "recovered_words.npy", words)
degrees = np.array([i.bit_count() for i in range(16)])

def analyze(j):
    padded = np.pad(words, ((0, 0), (0, (-words.shape[1]) % j)))
    batches = padded.reshape(len(words), -1, j)
    delta = batches.copy()
    delta[:, 1:, :] ^= batches[:, :-1, :]
    # Blocks a=16*h..16*h+15 use four low address bits; last four addresses excluded.
    block_words = delta[:1216].reshape(76, 16, -1, j)
    bits = ((block_words[..., None] >> np.arange(8)) & 1).astype(np.uint8)
    anf = bits.copy()
    for shift in (1, 2, 4, 8):
        for mask in range(16):
            if mask & shift:
                anf[:, mask] ^= anf[:, mask ^ shift]
    nonlinear = np.sum(anf[:, degrees > 1], axis=1)
    return {"J": j, "num_loaders": batches.shape[1], "scope": "76 complete 16-address blocks; final 4 addresses excluded",
            "affine_fraction_per_bit_all_loaders": np.mean(nonlinear == 0, axis=(0, 1, 2)).tolist(),
            "affine_fraction_per_bit_after_first_loader": np.mean(nonlinear[:, 1:] == 0, axis=(0, 1, 2)).tolist(),
            "nonlinear_ANF_coefficients_per_bit": np.sum(nonlinear, axis=(0, 1, 2)).tolist(),
            "nonlinear_ANF_coefficients_total": int(np.sum(nonlinear))}

batch5 = words.reshape(1220, 15, 5)
delta5 = batch5.copy()
delta5[:, 1:] ^= batch5[:, :-1]
anf5 = ((delta5[:1216].reshape(76, 16, 15, 5)[..., None] >> np.arange(8)) & 1).astype(np.uint8)
for shift in (1, 2, 4, 8):
    for mask in range(16):
        if mask & shift:
            anf5[:, mask] ^= anf5[:, mask ^ shift]
nonlinear5 = np.sum(anf5[:, degrees > 1], axis=1)
report = {"recovery": scope, "ANF_by_batch_size": [analyze(j) for j in range(1, 11)],
          "J5_affine_fraction_by_loader": [
              {"k": k, "all_blocks": np.mean(nonlinear5[:, k] == 0, axis=(0, 1)).tolist(),
               "two_body_full_blocks_only": np.mean(nonlinear5[5:, k] == 0, axis=(0, 1)).tolist()}
              for k in range(15)]}
(OUT / "table_structure.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
