# 7-bit ANGLE words (2026-11-11): T saving ~7 %, accuracy fails by 100x

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
Exact-arithmetic probe only (`evaluate_words`), no circuit, no verifier.

Question: do 7-bit words reduce the loader T enough to justify retraining?
They would save ~810 loader T + 300 Givens T (−7.45 % T), but direct 7-bit
re-quantization misses the 20 mHa gate by ~100× (e1) and ~22× (e2); the
8-bit baseline is already at the quantization floor, so 7-bit needs a
different factorization, not a cheap refit.

## 1. Direct re-quantization (`requantize.py`)

Output: `artifacts/20261111_7bit_probe_output.txt`.
Baseline words `(1220, 75)`, 256 levels, `brot=8`; 7-bit grid is
`theta/pi = k/64` (128 levels).

| table | error_1 | error_2 | Lambda | E_gap | lambda_eff |
|---|---:|---:|---:|---:|---:|
| 8-bit baseline | 0.019999980 Ha (19.99998 mHa) | 0.019999980 Ha (19.99998 mHa) | 282.976 | 3.914898020 | 46.907537 |
| 7-bit nearest | 2.041712 Ha (2,041.7 mHa) | 0.450762 Ha (450.8 mHa) | 289.798 | 10.737335 | 78.153908 |
| 7-bit floor | 2.026030 Ha (2,026.0 mHa) | 0.457003 Ha (457.0 mHa) | 288.929 | 9.868213 | 74.866869 |

The direct probe is 100× over the 20 mHa e1 gate and 22× over e2.  The
lambda_eff rises from 46.91 to 78.15 (+66.6 %).  Even with the 7-bit T saving,
the score would be **460,462,974.84** (T=13,798, Q=427) versus 276,367,296.04
at the unchanged lambda_eff: the lambda_eff rise adds 184.1e6 and dwarfs the
22.2e6 T saving.

## 2. T estimate (analytical, no 7-bit circuit built)

The 215 load CCX per loader are the 40 data bits (5 words × 8 bits); at 7 bits
the same load structure is 35 bits → 215·35/40 = 188 (−27 CCX/loader/pass).
The 75 prefix/setup CCX are width-independent.  Across 15 loaders and two
passes: −810 T.  Givens: `2·75·(2·beta−1)` with beta=7 gives 1,950 vs 2,250,
−300 T.  Total T 14,908 → **13,798** (−7.45 %); at unchanged lambda_eff the
score would be ~276.4e6.  This is an estimate; the loader would need a new
synthesis, which is not available for the current table (the synth line is
closed: k0 0 candidates, Maoxin 215 is the public best).

## 3. Why retraining is not a cheap recovery

- The 8-bit baseline's e2 is 19.99998 mHa, i.e. the 8-bit quantization is
  already using the entire 20 mHa budget; the continuous solution is at the
  floor.
- 7-bit halves the angle resolution; if the continuous solution were perfect,
  the quantization error would roughly double to ~40 mHa, still 2× the gate.
  The measured R5/R4 continuous basins are ~40 mHa (R5/B135/C70 40.24 @50k;
  R4/B131/C83 73.07 @20k), so there is no reservoir of continuous accuracy to
  absorb the coarser grid.
- The `brot=6` direction was already closed on the same logic: T×Q −18.61 %
  but e1 floor 9,620 mHa, training gradient identically zero
  (`ABANDONED.md`).  7-bit is a milder version; it still needs a new word
  table, a new factorization and a new 7-bit loader synthesis, with no
  evidence the 20 mHa gate is reachable.

## 4. Verdict

**Closed.**  Do not start a 7-bit training.  The loader T saving is real but
secondary; the accuracy floor is ~2× the gate before any training, and the
8-bit table is already at the quantization limit.

## 5. Verification scope

- `evaluate_words` exact arithmetic on the baseline tree/weights; no shots,
  no circuit, no `recover_words_from_circuits`, no `verify.py`.
- The T estimate is analytical; the 7-bit loader was not synthesized.
