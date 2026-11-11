# R3 GPU run + B135 Lera quantize build (2026-11-11)

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
This record covers the GPU route and the Lera quantize/refine/tensorqrom
pipeline; the shape trajectories and exact cost model are in
`../20261111_r8_basis/README.md`.

## 1. R3/B129 closed

Seeds from `seed_numpy.py` (cluster/chol/omp) were 1,177.32 mHa (C114),
1,297.78 (C120), 1,140.50 (C150).  GPU kernel
`qingyu1232/qcc-r3-gpu-train` (T4, dataset `qingyu1232/qcc-r3-train-bundle`),
50k L-BFGS each, output `gpu_out/summary.json`:

| shape | 50k continuous e2 | GPU s |
|---|---:|---:|
| (3,129,114) | 87.53 mHa | 525.7 |
| (3,129,120) | 95.92 mHa | 525.4 |
| (3,129,150) | 96.35 mHa | 698.1 |

Total 1,751.2 s.  Far from the 20 mHa gate; closed without quantization.

## 2. B135 GPU quantize route

The Lera V7 source was recovered from the public dataset
`marculera/dfthc-merge-pipeline` (`dfthc_refit/`, VERSION
`dcf1294d7af494ceb584df81df3e58943014313a`).  It provides the missing
`quantize.py`, `refine.py`, and `tensorqrom.py`/`fourqrom.py` loader
synthesis.  The starter-kit `dfthc` code was downloaded from
`sohier/verifiable-circuit-compilation-starter-kit`; the unused
`solution_io` import in `train_df_thc_sga.py` was commented out (documented
in the file).

Bundle `qingyu1232/qcc-r3-train-bundle` (private) now holds
`struct_8x135x44_20000.npz` (SHA `96411985…104fe7`), `lera/dfthc_refit/`,
and `starter_pkg/`.  Kernel `qingyu1232/qcc-r3-b135-quantize` runs:
`quantize.py --brot 8 --lbfgs-until 0.5 --lbfgs-iters 12000 --stage-steps
800 --final-steps 1500`, then `refine.py --brot 8`, then
`build.py --brot 8 --qrom tensor --shots 64`.

Status: **COMPLETE with error_2 rejection**.  GPU total 1,479.1 s.  Stage 0
190.39 → 32.42 mHa, stage 1 43.33 → 33.26, stages 2–13 flat ~33.1.
`refine.py`: error_1 **11.204 mHa**, error_2 **33.1236 mHa**, lambda_eff
**49.862795**.  `build.py --shots 64` rejected:
`error_2 = 33.1236 mHa > 20 mHa`.  The generated submission has
T = 6,646 + 9,056 = 15,702, Q = 427, score **334,317,772.35** (+11.96 %).
No verifier PASS.  Output SHA: `submission.npz` `48672070…b98a62a`,
`quant` `97c05d49…f2ce401`, `refine` `692c099f…c01f484`, log
`9a35c291…f45e903e`.

## 3. Local quantization attempts (failed)

- Direct signed 8-bit re-encode: B129 239.15 mHa / λeff 90.80, B135
  243.77 mHa / λeff 83.60 (`quantize_b.py`).
- Projected L-BFGS (`qat_b.py`, 500 steps + projection + 200 W-only steps
  per chunk): B135 quantized e2 243.8 → 199.4 → 193.2 → 185.2 → 181.0 mHa;
  plateau, killed.
- Lera `quantize.py` quick Adam (400 steps/stage): stage 0 164.15 → 33.21,
  then 33.68/33.46/33.37, flat ~33.3; killed.
- Lera `quantize.py --free 0.5,0.0 --lbfgs-iters 5000`: 190.64 → 50.03 mHa
  (stage 0), killed.  The aggressive freeze schedule is too coarse.

## 4. Loader-cost blocker (see the R8 record for the table)

`tensorqrom` 1,156 rows: 4,530/pass = 9,060 T (J=5, 127 qubits);
`fourqrom` J=3: 8,400/pass = 16,800 T (qmax 104).  B=135 break-even loader T
is 8,262; the public 8,246 is the only plan under it and cannot be
re-synthesized for the new table.  Generic loaders make the B-axis +5.3 %
(worse), even if the quantized accuracy passes.

## 5. Files

`artifacts/20261111_r3_probe/` (gitignored): seeds, training outputs,
`struct_8x135x44_20000.npz`, `gpu_out/` (R3), `bundle/`, `lera_pipeline/`,
`starter_pkg/`, kernel dirs, logs.
`gpu_quantize.py`, `train_r3.py`, `make_b129_seed.py`, `quantize_b.py`,
`qat_b.py` are the runnable probes.

## 6. Verification scope

R3: continuous e2 only (no quantization/verifier).  B135: the official
`build.py --shots 64` verifier **rejected** on `error_2 = 33.1236 mHa >
20 mHa`; no PASS.  The exact official arithmetic (`evaluate_words`) on the
generated submission gives e1 11.204 mHa, e2 33.1236 mHa, lambda_eff
49.862795; the score 334,317,772.35 is a cost projection, not a PASS.
