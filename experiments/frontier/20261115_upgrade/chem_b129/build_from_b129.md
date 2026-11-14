# B=129 build/verify plan (only if continuous error_2 ≤15 mHa)

The shrink run writes `b129/out/8x129x44.npz` (continuous U/W). If its final
`error_2` is **≤15 mHa**, continue with the public Apache-2.0 pipeline; otherwise
stop and keep the 27.31193 submission.

## 1. Round / refine / refit / build

Use `dfthc_refit/run.py` with a recipe that finishes an existing continuous fit:

```toml
start = "/kaggle/working/b129/out/8x129x44.npz"

[round]
brot = 8
stage_steps = 3000
final_steps = 8000

[refit]
target = 19.99

[build]
qrom = "tensor"
shots = 64
```

Run on Kaggle CPU/GPU:

```bash
python dfthc_refit/run.py recipe.toml --start /kaggle/working/b129/out/8x129x44.npz
```

The runner writes `submission/` (15 ANGLE `.kmb` + `submission.npz`) and
`result.json` with the official verifier verdict. The hard gate is
`error_1,error_2 ≤ 20 mHa`, `E_gap > 3.914898`, `Lambda > 49`,
`T ≤ 14,430`, `Q = 427`, and **chem cost ≤288.8M** (GM ≥27.50).

## 2. Package

If and only if the gates pass, assemble:

- invsqrt HW-26 `1ba197b02771` (78,673.569211)
- DQI `821bf8d1` (360,209,905,486.02, 0 errors)
- new `dfthcsos/submission.npz` + 15 angle loaders from `submission/`

Compute the 18-file ZIP, record SHA-256, verify all pins, and submit through the
competition submission API. Do not submit if chem cost >288.8M.

## Status

`qingyu1232/qcc-chem-b129-full` is running on Kaggle T4; no local simulation.
The B139-only screen was superseded / left as a duplicate.
