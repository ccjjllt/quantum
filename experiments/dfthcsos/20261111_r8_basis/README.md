# R8 basis reduction B 143→129/131/135 (2026-11-11): B135 continuous 16.71 mHa; quantization ongoing

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
No verifier result yet; this record covers the continuous fit, the naive
quantization failures, the Lera quantize/refine/tensorqrom pipeline discovery,
and the exact cost model.  R3 is closed.

## 1. Cost model (official `heuristic_costs(76,8,B,44,8)`)

Loader T uses the measured baseline scale 8,246 / 1,220 = 6.759016 T per
vector (`N + R*B`); Q = persistent + 40 + max(temp, 77) = 427 for all B.
Score at the baseline lambda_eff 46.90753743257459, baseline 298,600,061.56.

| B | vectors | heuristic T | loader T | T | Q | score | delta |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 129 | 1,108 | 6,634 | 7,488.99 | 14,122.99 | 427 | 282,876,692.5 | −5.27 % |
| 131 | 1,124 | 6,638 | 7,597.13 | 14,235.13 | 427 | 285,122,888.1 | −4.51 % |
| 135 | 1,156 | 6,646 | 7,813.42 | 14,459.42 | 427 | 289,615,279.3 | −3.01 % |
| 143 | 1,220 | 6,662 | 8,246.00 | 14,908.00 | 427 | 298,600,061.6 | 0 |

## 2. Seeds: truncate the 143-basis and refit W

`make_b129_seed.py`: per rho, keep the top B basis rows by `||W[r,b,:]||`
(or `sum_c |W|`), then solve a linear least squares for W so that
`sum_b W_new[r,b,c] u_b u_b^T` matches the current `X[r,c]` on the packed
lower triangle.  Seed continuous e2:

| B | seed e2 |
|---:|---:|
| 129 | 349.42 mHa |
| 131 | 296.37 mHa |
| 135 | 191.37 mHa |

## 3. Continuous L-BFGS trajectories (packed-pair e2, same objective as R5/R4)

500-step chunks; `slim_train.py`, `prob_r5.npz`:

| total steps | B129 | B131 | B135 |
|---:|---:|---:|---:|
| 500 | 39.65 | 35.71 | 29.84 |
| 1,000 | 30.02 | 27.74 | 24.14 |
| 2,000 | 25.08 | 23.50 | 20.90 |
| 5,000 | 21.55 | 20.42 | 18.51 |
| 10,000 | — | — | 17.52 |
| 15,000 | — | — | 17.00 |
| 20,000 | — | — | **16.71** |

B135 crosses the 20 mHa continuous gate at 5k (18.51) and reaches 16.71 at
20k (856.7 s CPU).  B131 is 20.42 at 5k and **19.12 at 10k** (continuation
running to 20k); B129 21.55 at 5k.  The control R5/B129/C68 (751 vectors)
reached 67.82 at 5k; the B-axis trajectories are much better because
R*C=352 is unchanged.

## 4. Naive 8-bit quantization fails

Direct signed Givens re-encoding of the continuous U, `evaluate_words` at
brot=8:

| B | continuous e2 | quantized e1 | quantized e2 | lambda_eff |
|---:|---:|---:|---:|---:|
| 129 (5k) | 21.55 | 67.05 mHa | 239.15 mHa | 90.80 |
| 135 (5k) | 18.51 | 67.08 mHa | 243.77 mHa | 83.60 |

The continuous U is not quantization-friendly.  A projected L-BFGS variant
(`qat_b.py`: 500 joint steps + hard projection + 200 W-only steps per chunk)
plateaued at **180.99 mHa** after 5 chunks on B135; it was killed.

## 5. Lera quantize pipeline (the live path) and the loader-cost blocker

The Lera V7 source is **public**: dataset `marculera/dfthc-merge-pipeline`,
`dfthc_refit/` (Apache-2.0/other; VERSION `dcf1294d…`).  It contains
`quantize.py` (progressive signed-gauge rounding with Adam/L-BFGS refits),
`refine.py` (one-body + lambda refit), and `tensorqrom.py` (the shared
product-cache loader synthesis that was missing locally).  `build.py
--qrom tensor` builds the 15 loaders and runs the official verifier.

**Loader-cost blocker (measured).**  `tensorqrom.build_family` on a
1,156-row signed-gauge table (first 1,156 baseline rows, and a 135-per-rho
selection; `trials=1/2`): static **4,532–4,534/pass = 9,064–9,068 T**,
15 circuits, 127 qubits, `words_match=True`.  `trials=6` gives
**4,530/pass = 9,060 T** (per-loader 302 CCX each).  `fourqrom`
(J=3) gives 8,400/pass = 16,800 T, 25 circuits, qmax 104.  That is
**higher** than the public loaders' 4,123/pass (8,246 T), not the
6.759 T/vector linear projection (7,813 T).  The B=135 break-even loader T
is 14,908 − 6,646 = **8,262 T**; `tensorqrom` is ~798 T above it, and
`fourqrom` is far above it.

Exact scores at the baseline lambda_eff 46.907537:

| B | plan | loader T | Q | T | score | delta |
|---:|---|---:|---:|---:|---:|---:|
| 135 | public (not reusable for a new table) | 8,246 | 427 | 14,892 | 298,279,589.3 | −0.107 % |
| 135 | tensorqrom J=5 | 9,060 | 427 | 15,706 | 314,583,617.3 | +5.353 % |
| 135 | fourqrom J=3 | 16,800 | 411 | 23,446 | 452,015,384.4 | +51.378 % |
| 131 | tensorqrom J=5 | 9,060 | 427 | 15,698 | 314,423,381.2 | +5.299 % |
| 129 | tensorqrom J=5 | 9,060 | 427 | 15,694 | 314,343,263.1 | +5.272 % |

The −3.0 % cost model is therefore not achievable with the generic
product-cache plan; the public hand-optimized loaders remain better per row.
The GPU run will measure the real quantized table's T (which may be more
structured); only that can override this estimate.  Even if it does, the
one-body rows and the table ordering would need the public loader plan to be
re-synthesized, which is not available.

Quick local Adam schedule on B135 (400 steps/stage):
stage 0 164.15 → 33.21; stage 1 46.62 → 33.68; stage 2 34.47 → 33.46;
stage 3 33.61 → 33.37 mHa; then flat at ~33.3.  A local `--free 0.5,0.0
--lbfgs-iters 5000` stage reached 50.03 mHa from 190.64.  The short refits
are not enough.  The full default-freeze L-BFGS recipe
(`--lbfgs-until 0.5 --lbfgs-iters 12000 --stage-steps 800`) is running on
the Kaggle GPU (`qingyu1232/qcc-r3-b135-quantize`) from the 20k structure.

## 6. R3 closed

R3/B129 seeds from `seed_numpy.py` were ~1,140–1,298 mHa.  GPU 50k results
(`qingyu1232/qcc-r3-gpu-train`, 1,751.2 s total):
(3,129,114) 87.53 mHa, (3,129,120) 95.92, (3,129,150) 96.35.  Far from 20;
closed without quantization.

## 7. Files / SHAs

`artifacts/20261111_r3_probe/` (gitignored):
- `seed_8x129x44_truncfit.npz` (B129 seed)
- `seed_8x131x44_truncfit.npz`, `seed_8x135x44_truncfit.npz`
- `train_8x129x44_5000.npz`, `train_8x131x44_5000.npz`
- `train_8x135x44_5000.npz`, `train_8x135x44_20000.npz`
  SHA `0866dabe…ec62bd3`
- `struct_8x135x44_20000.npz` SHA `96411985…104fe7`
- `quant_8x135x44.npz` (quick Adam, ~33.3 mHa; intermediate)
- `gpu_out/summary.json` (R3)
- `lera_pipeline/dfthc_refit/` (public Lera V7 source)

## 8. Verification scope

- Continuous e2 is the training objective, **not** the official
  `evaluate_words`; the quantized numbers in §4 are official arithmetic but
  fail the 20 mHa gate.
- No 78,080-shot verifier run yet.  The GPU quantize/refine/tensorqrom build
  is in progress; only a completed official PASS with score < 298,600,061.56
  would be a candidate.
