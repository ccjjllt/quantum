# RESULT6 — fresh shapes R=7, 9, 10, 12: priced exactly, fitted on Kaggle CPU, all blocked

Date: 2026-11-16/17. Chemistry only. `RESULT.md`–`RESULT5.md`, `LAMBDA.md`, `CODE2.md` stand.
No submission. Closed territory (not repeated): (8,143,44) re-code/re-quant/refit, C=43/42/41
joint-w refit, (4,286,88)/(2,572,176) merges, (11,104,32)/(13,88,27) splits, B<143 / C<=40
truncation, R=5/6 merge-shrink, lambda rotations/offsets, loader code search, k9/k10/k12/k14
emitter (+2..+4 losses). This note covers only the never-measured R values 7, 9, 10, 12.

## 0. Verdict

1. **R=7, (7,143,44): dead by the rank wall, measured.** K=308 → floor 14.481 mHa; rows 1,077 →
   continuous gate 15.23 mHa → needs `rho <= 1.05` where the family measures 1.93. Kaggle
   joint U/W fit (group26 → merge /4 → shrink, §3): continuous **53.350 mHa** (3.5x gate),
   quantized **66.158 mHa** (3.3x gate 20); e1 12.139 passes, E_gap 4.0936 above floor.
2. **R=9, (9,135,38): the borderline shape — measured FAIL, and the rho law was optimistic.**
   Needed `rho <= 1.68`, law predicted 1.62; the fit lands at **rho = 4.87** (continuous 40.842
   vs gate 14.09, quantized 53.311). The copy shrink 90 → 38 (-58 %) dominates the B/C=3.55
   advantage. T/cost would have failed anyway (T_heur 6,549 + 1,291 rows → T ≈ 15,067).
3. **R=10, (10,120,32): dead twice over, measured.** Continuous **41.456** (2.9x gate), quantized
   **56.212**; and the exact Q cliff (B=120 < 129 → Q=697) prices cost at 437.7 M regardless.
4. **R=12, (12,100,28): dead twice over, measured.** Continuous **47.295** (3.3x gate),
   quantized **61.753**; Q=697 → cost 438.9 M regardless.
5. No candidate reaches `cost <= 294,762,300` (GM >= 28.09490) at T < 14,712 or Q < 427.
   No official verifier run (78,080 shots) was made: nothing passed the local gate — the
   probes' gate logic correctly skipped every build/verify.

## 1. Candidates and exact pricing (verifier's own SpinFreeData_V1, chi=10, brot=8)

rows = 76 + R*B, K = R*C. Q = 40 + outer_pers + inner_pers + max(outer_temp, inner_temp, 77).
Target: T*Q <= 6,282,686 at lambda_eff 46.9216 (shipped T*Q = 6,282,024).

| shape | rows | K | B/C | T_heur (o/i/g) | Q | L row-scaled | T | T*Q | cost @46.9216 |
|---|---|---|---|---|---|---|---|---|---|
| (8,143,44) shipped | 1,220 | 352 | 3.25 | 6,662 (317/4,095/2,250) | 427 | 4,025 | 14,712 | 6,282,024 | 294.76 M |
| **(7,143,44)** | 1,077 | 308 | 3.25 | 6,230 (303/3,677/2,250) | 427 | 3,553 | 13,336 | 5,694,472 | 267.2 M *if e2 passed* |
| (9,135,38) | 1,291 | 342 | 3.55 | 6,549 (315/3,984/2,250) | 428 | 4,259 | 15,067 | 6,448,676 | 302.5 M |
| (10,120,32) | 1,276 | 320 | 3.75 | 4,965 (307/2,408/2,250) | 697 | 4,209 | 13,383 | 9,327,951 | 437.7 M |
| (12,100,28) | 1,276 | 336 | 3.57 | 5,002 (312/2,440/2,250) | 697 | 4,209 | 13,420 | 9,353,740 | 438.9 M |

L row-scaled = 4,025 * rows/1,220 (model, ranking only — no loader ports exist at these row
counts; cf. RESULT4 §5). T = 2L + T_heur. Model per-loader T (L/R, ranking only):
(7,143,44) 507/loader, (9,135,38) 473/loader, (10,120,32) 421/loader, (12,100,28) 351/loader
— not comparable to the shipped 268/loader (different R, different row counts) and no loader
was built. **No loader was built or verified for any fresh shape.**

The Q cliff is exact, not a model: B < 129 → inner temp 574 (k2 falls on the wrong side),
Q = 697 vs 427/428 for B >= 129. R=10/12 cannot hold rows 1,100-1,300 at B >= 129
(R=10 needs B >= 129 → rows >= 1,366; R=12 → rows >= 1,624), so every in-range R=10/12
shape pays +270 qubits = +5.9 GM. Dead on arrival.

## 2. Precision walls (exact floors + measured rho law; fits confirm)

Rank floor floor(K) from the exact H spectrum (2926 pairs; reproduces shipped 19.99997 mHa).
Continuous gate gate_c = sqrt(400 - p^2), p = 13.8*sqrt(rows/1220) (quadrature rounding model,
RESULT2 §2). rho = e2_cont/floor; family law rho ~= 1.93*(3.25/(B/C))^1.95 (±15 %, 4 points).

| shape | floor(K) | gate_c | rho needed | rho predicted | e2_cont predicted | verdict |
|---|---|---|---|---|---|---|
| (7,143,44) | 14.481 | 15.23 | 1.05 | 1.93 | 27.9 | FAIL (1.8x) |
| (9,135,38) | 8.385 | 14.09 | 1.68 | 1.62 | 13.6 | borderline PASS (cont) / T FAIL |
| (10,120,32) | 11.743 | 14.17 | 1.21 | 1.46 | 17.1 | FAIL + Q cliff |
| (12,100,28) | 9.130 | 14.17 | 1.55 | 1.61 | 14.7 | FAIL (103 %) + Q cliff |

## 3. Kaggle fits (dfthc_refit joint U/W, CPU; coded quantizer note in §5)

Kernels: CPU only (`enable_gpu: false`), no internet. Path per probe: seed → `public_seed`
convert (group seeds) → `structure.merge` (exact, k at a time) → `shrink.py --device` joint
U/W L-BFGS fades+refits → `quantize.py --brot 8 --x64` (plain; see §5) → `refine.py` →
`refit_weights.py` (only if e2 < 19.95). `build.py` + official 78,080-shot verifier (+2 salts)
only on a passing gate — never reached, correctly never run.

| kernel | shape | seed → merge | schedule | cont e2 @target | quant e2 | e1 | E_gap | lambda_eff |
|---|---|---|---|---|---|---|---|---|
| jiyujia/qcc-chem-fresh-shape-r-7-b-143-c-44 | (7,143,44) | group26 → /4 | 200x100,170x80,150x60,143x44 | **53.350** | **66.158** | 12.139 | 4.093626984 | 49.4461 |
| jiyujia/qcc-chem-fresh-shape-r-9-b-135-c-38 | (9,135,38) | group26 → /3 | 160x70,145x54,135x44,135x38 | **40.842** | **53.311** | 12.043 | 4.097772874 | 49.5718 |
| jiyujia/qcc-chem-fresh-shape-r-10-b-120-c-32 | (10,120,32) | B10c54, --merged | 120x44,120x38,120x32 | **41.456** | **56.212** | 10.990 | 4.095513725 | 49.5249 |
| jiyujia/qcc-chem-fresh-shape-r-12-b-100-c-28 | (12,100,28) | group24 → /2 | 110x48,105x38,100x32,100x28 | **47.295** | **61.753** | 10.457 | 4.094399780 | 49.2575 |

r12 trajectory (continuous e2, mHa): seed 19.371 (10-bit words) → merged (12,120,60) pre-fit
16.270 → 110x48: 27.760 → 105x38: 37.344 → 100x32: 47.786 → **100x28: 47.295** (final, 1,500
it). Quantize stages stall at 61.75-61.78 from stage 1 on (frozen 0.5 → 1.0 changes nothing:
the continuous point is 3.3x past the gate, rounding adds the usual ~14). refine: e2 pinned
61.753, Lambda 380.95 → 298.34, E_gap 174.65 → 4.094, e1 168.9 → 10.457 mHa. refit skipped
(e2 > 19.95). Elapsed 78 min. Status COMPLETE; `summary.json` in kernel output.

r10 trajectory (continuous e2, mHa): B10c54 seed (10,120,54) pre-fit 16.163 → 16.291
— the seed itself already misses the 1,276-row continuous gate (14.17) — → 120x44: 25.294 →
120x38: 32.895 → **120x32: 41.456** (final, 1,200 it). Quantize stalls at 56.2 from stage 0 on.
refine: e2 pinned 56.212, Lambda 389.61 → 301.49, E_gap 174.65 → 4.0955, e1 166.1 → 10.990 mHa.
refit skipped. Elapsed 96 min. Status COMPLETE.

r7 trajectory: group26 seed (26,60,30) 10-bit words e2 19.84 → merged (7,240,120) pre-fit
19.838 → **14.206** (the full-size merged seed passes the continuous gate) → 200x100: 25.961
→ 170x80: 34.008 → 150x60: 46.414 → **143x44: 53.350** (final, 1,500 it). Quantize stalls at
66.16 from stage 1 on. refine: e2 pinned 66.158, Lambda 383.45 → 300.67, E_gap 174.65 → 4.0936,
e1 171.7 → 12.139 mHa. refit skipped. Elapsed 135 min. Status COMPLETE.

r9 trajectory: group26 → merged (9,180,90) pre-fit 19.838 → **14.820** → 160x70: 24.800 →
145x54: 35.992 → 135x44: 44.430 → **135x38: 40.842** (final, 1,500 it). Quantize stalls at
53.31 from stage 1 on. refine: e2 pinned 53.311, Lambda 384.12 → 301.89, E_gap 174.66 → 4.0978,
e1 160.0 → 12.043 mHa. refit skipped. Elapsed 130 min. Status COMPLETE.

Measured `rho = e2_cont/floor`: r7 53.35/14.481 = **3.68**, r9 40.84/8.385 = **4.87**,
r10 41.46/11.743 = **3.53**, r12 47.30/9.130 = **5.18** — all 2-3x above the 1.5-2.2 law
values. The law (corner fits at B/C ≈ 3.25) is optimistic for shrunk shapes: cutting
40-60 % of bases/copies multiplies e2 at every step (same pattern as the R=5 full-budget
run: predicted 30.2, realised 53.65). No optimizer closes this: the failure is the shrink
path, not the iteration budget (final refits of 1,200-1,500 iterations move < 1 mHa once
the copy fade breaks the span).

## 4. Blocker per shape

- (7,143,44): **FAIL, measured.** Continuous 53.350 mHa (3.5x gate 15.23), quantized
  66.158 mHa; e1 12.139 passes, E_gap 4.094 above floor. The full-size merged seed passes
  (14.206) and every shrink step multiplies e2 — the rank wall with rho >= 3.7, not 1.05 (§3).
- (9,135,38): **FAIL, measured.** Continuous 40.842 (rho 4.87 vs needed 1.68), quantized
  53.311; e1 12.043 passes. Doubly blocked: T_heur 6,549 + 1,291 rows → T ≈ 15,067 even with
  a row-scaled loader, i.e. cost >= ~302 M (§1). The B/C=3.55 advantage does not survive the
  90 → 38 copy shrink.
- (10,120,32): **FAIL, measured.** Continuous 41.456 mHa (2.9x gate 14.17), quantized
  56.212 mHa; e1 10.990 passes, E_gap 4.096 above floor. Q = 697 exact → cost >= 437.7 M.
  Two independent blockers (§3).
- (12,100,28): **FAIL, measured.** Continuous 47.295 mHa (3.3x gate 14.17), quantized
  61.753 mHa (3.1x gate 20); e1 10.457 passes, E_gap 4.094 above floor. Q = 697 exact →
  cost >= 438.9 M regardless. Two independent blockers (§3).

## 5. Quantizer note (why plain --brot 8, not --coded)

The probes run the shipped `quantize.py --brot 8 --x64` WITHOUT `--coded`. `--coded`
(bit-0 affine/Reed-Muller constraint, `quantize.py --coded "batches"`) only ADDS constraints
for the loader's benefit (RESULT4 §2: the code is the quantizer's noise-shaping DOF; forcing
it costs first-order precision). Gate order is therefore: plain must pass before coded is even
relevant. No loader port exists at 1,077/1,291/1,276 rows (only the 791-row R=5 port,
LOADER_R5_PORT, verified at 238 T), so no batch range can be priced — coded rounding is
recorded as follow-up, correctly not run.

## 6. Files, kernels, verification scope

- Probe template: `fresh_shape_probe/main_template.py`; per-shape dirs `fresh_shape_probe/r{7,9,10,12}/`
  (`main.py` + `kernel-metadata.json`).
- Kernels (CPU, no internet), all status COMPLETE; full logs + `summary.json` in kernel output:
  - `jiyujia/qcc-chem-fresh-shape-r-7-b-143-c-44` (135 min: convert 1 + fit 82 + quantize 44 + refine 8)
  - `jiyujia/qcc-chem-fresh-shape-r-9-b-135-c-38` (130 min)
  - `jiyujia/qcc-chem-fresh-shape-r-10-b-120-c-32` (96 min)
  - `jiyujia/qcc-chem-fresh-shape-r-12-b-100-c-28` (78 min)
- Local exact math: `SpinFreeData_V1` pricing + `H_spectrum.npy` floors (this repo, seconds).
- Verification actually run: none (no candidate passed the local gate, so per the brief the
  unchanged official verifier at 78,080 shots + 2 salts was correctly not run). The
  294,762,632.08 baseline and its 3-salt PASS (RESULT.md §8) are unchanged.
- No candidate package, no submission.
