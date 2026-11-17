# RESULT7 — the `--coded` quantizer where plain already passes: measured, both fail

Date: 2026-11-17. Chemistry only. `RESULT.md`–`RESULT6.md`, `CODE2.md`,
`LOADER_R5_PORT.md` stand. No submission. Closed territory (not repeated):
R5/6/7/9/10/12 shrink fits, C43/42/41 truncation, post-hoc word re-code at
(8,143,44) (36–63 mHa floor), emitter k9/k10/k12/k14 (+2..+4), B<143/C<=40
truncation. This note covers ONLY the documented follow-up: the public
`quantize.py --coded` quantizer applied where plain already passes, with all
fits on Kaggle CPU (account jiyujia) and local work limited to
hashes/cost-model arithmetic plus reading public code (no local simulation).

## 0. Verdict

1. **(a) Shipped (8,143,44) bdae words, fresh `--coded "1-14"` rounding + full
   352-weight refit: e2 does NOT stay ≤ 20, and Σcuts does NOT rise 71 → 91 —
   it FALLS 71 → 55.** Quantize pins at 21.22, refine lands e2 **21.216 mHa**
   (e1 11.701 passes, E_gap 4.077 above floor, lambda_eff 47.9334), and the
   full 352-weight `refit_weights.py` floor is **21.216 mHa to 9 decimals —
   zero movement in 844 s**. The gate fails by **1.22 mHa**. The census
   (validated byte-exact against the shipped 891-cut table) gives **715 total
   cuts**: loaders 4–14 drop 71 → 55 each because the public `--coded`
   enforces **bit-0 affine only** — the XOR-of-five bit-1 (11) and bit-2 (5)
   codes are lost in fresh rounding, and `--coded` never slope-matches, so no
   constant-delta 91 appears anywhere. At shipped caches the model loader cost
   would RISE 263 → 310/loader (+47 T × 11 loaders).
2. **(b) R=9 merged (9,180,90) seed (continuous 14.820 pre-shrink), `--coded
   "0-14"` at the merged size: e2 does NOT survive — 36.229 mHa quantized,
   pure-w floor ≈ 35.89.** The 21.4 mHa rounding penalty is structural (vectors
   frozen at bad angles; 300 L-BFGS iterations over all 145,800 weights move
   0.34 mHa). Cuts: **55/loader × 15 = 825** (bit-0 affine everywhere incl.
   loaders 0–1; XOR codes 0 — the quantizer does not make them). Cost is
   independently dead: exact `SpinFreeData_V1` gives T_heur **13,631**, Q 432;
   with model loaders (310 each) T = 22,931 → **464.8 M** at shipped lambda
   (cap needs L/pass ≤ 455 vs model 4,650).
3. **Tool gap found and documented (not worked around in public code):**
   `refine.py`'s one-body coded path crashes when ALL 75 columns are coded —
   the kicks-loop `polish(..., even=all-coded)` can produce a trial row with
   every word outside [-66,63], yielding zero candidates and a `decode`
   crash. Probe (a) (5 plain columns) survives; probe (b) does not. Census and
   floor for (b) were recovered WITHOUT modifying public code (Hamming
   `code_bits` one-body rows + pure-e2 L-BFGS with exact, finite-difference-checked
   gradient).
4. **No official verifier run (78,080 shots, default + 2 salts) was made:**
   nothing passed the local gate — the probes' gate logic correctly skipped
   every build/verify, same policy as RESULT4 §8 / RESULT6. Chemistry stays at
   **294,762,632.08**. Target `cost <= 294,762,300` not met. No submission.

## 1. Probe (a): fresh `--coded "1-14"` at (8,143,44)

Kernel `jiyujia/qcc-chem-coded-re-quant-8-143-44-batches-1-14` (COMPLETE, 1.0 h).
Input: `marculera/dfthc-c44-build/submission.npz` (U (8,143,76), W
(8,143,44); words identical to bdae per RESULT4 App. A). Pipe: public
`dfthc_refit`; schedule identical to the RESULT6 probes
(`--free 0.7,…,0.0`, stage 400 / final 1000, `--kappa 5e-5`,
`--lbfgs-until 0`, `--x64`, `--brot 8`); the ONLY change vs a plain
re-quantization is `--coded "1-14"` (the shipped code batches, cols 5–74).

### 1.1 Trajectory (Kaggle log, exact)

| stage | frozen | e2 before → after (mHa) |
|---|---:|---|
| 0 | 0.30 | 33.022 → **18.756** |
| 1 | 0.50 | 37.389 → 20.218 |
| 2 | 0.68 | 25.537 → 20.992 |
| 3 | 0.80 | 21.828 → 21.182 |
| 4–8 | 0.88–1.00 | pinned 21.33 → 21.22 |
| 9 (final) | 1.00 | → **21.216** |

The machinery works (stage 0 recovers to 18.756 < 20), then the coded
constraint bites progressively: each freeze adds error the refit cannot fully
absorb. refine: e1 11.7014139 / e2 21.2163048 / Lambda 283.82791666 /
E_gap 4.0768255358 / lambda_eff 47.93342561. refit skipped by the 19.95 gate.

### 1.2 Full 352-weight refit floor (separate kernel, COMPLETE, 14 min)

Kernel `jiyujia/qcc-chem-coded-814344-full-weight-refit-floor`: `refit_weights.py`
on the refined output (`--target 19.95`): start e2 21.2163 →
**RESULT identical to 9 decimals** (e2 21.216304826509962, rc=0, 844 s).
The fixed-words floor IS 21.216: the 1.22 mHa over the gate is not recoverable
by any weight move. Contrast RESULT4 §2.3 (post-hoc parity flips: 36–63 mHa
floors): fresh `--coded` rounding is far better than post-hoc re-coding
(21.2 vs 36–63) but still fails, because the 2-of-32 pattern restriction is
first-order (RESULT4 §2.3 mechanism confirmed with the real quantizer).

### 1.3 Census (numpy, ported from `code2/code_census.py`; self-check exact)

| loader | shipped (self-check) | fresh `--coded "1-14"` | Δ |
|---|---:|---:|---|
| 0, 1 | 0, 0 | 0, 0 | 0 (batch 0 deliberately uncoded, as shipped) |
| 2, 3 | 55, 55 | 55, 55 | 0 |
| 4–14 | **71** × 11 | **55** × 11 | **−16 each** (xor_b1 11 → 0, xor_b2 5 → 0) |
| total | **891** | **715** | −176 |

- Per-word bit-0: affine in 76/76 blocks for cols 5–74 (only batch-0 cols
  non-affine: 5 cols / 355 block-cols — exactly as designed).
- Bit-1/bit-2 columns: non-affine in all 75 cols (no XOR codes survive fresh
  rounding).
- Slope agreement with shipped on coded cols: **331/5,320 blocks (6 %)** —
  the quantizer re-discovers unrelated affine patterns (pattern choice is
  offset-driven; the shipped slopes came from a different pipeline).
- No loader shows 91 cuts (no constant deltas: `--coded` picks patterns per
  column independently and never slope-matches).

### 1.4 Per-loader T and cost (model, shipped cache 69+6)

products = (525−Σcuts)/2: 71 → 189 prod / 263 T; 55 → 235 prod / **310 T**.
So k4–14 would cost 310 vs shipped 263 (**+47 T/loader**, +517/pass before
the RESULT4 §2.2 +2 T re-emission overhead). Model total:
L/pass = 294+288+2·310+11·310 = 4,612; T = 2·4,612+6,662 = **15,886**;
cost at measured lambda_eff 47.9334 = **325.1 M (GM 25.47)** — a loss on
every axis (precision, cuts, cost). k0/k1 keep legacy T (words changed but
uncoded batches; moot behind the e2 gate).

## 2. Probe (b): `--coded "0-14"` at merged (9,180,90)

Kernels: `jiyujia/qcc-chem-coded-rounding-at-merged-9-180-90` (quantize
COMPLETE 108 min inside an ERROR kernel — see §4),
`jiyujia/qcc-chem-r9merged-census-and-e2-floor` + `-floor{,2,3,4,5,6}` series
(census COMPLETE; floor COMPLETE at v6). Input: merged checkpoint
`fit/seg0/9x180x90.npz` from the r9 probe (continuous 19.838 → **14.820**,
republished as dataset `jiyujia/qcc-chem-r9-merged-180x90`), all 75 columns
coded (`--coded "0-14"`; no shipped batches to preserve at this shape).

### 2.1 Trajectory: 14.820 → 36.229, then stuck

| stage | frozen | e2 before → after (mHa) |
|---|---:|---|
| 0 | 0.30 | 206.365 → 32.056 |
| 1 | 0.50 | 90.294 → 37.014 |
| 2–3 | 0.68–0.80 | 41.761 → 36.947 → 36.699 |
| 4–9 | 0.88–1.00 | pinned 36.77 → **36.229** |

The freeze jumps (206/90 mHa) dwarf the (a) case: at 121,500 angles the
coded constraint destroys far more noise-shaping DOF. refit skipped
(36.2 > 19.95).

### 2.2 Pure-e2 floor: 36.229 → 35.889 (300 L-BFGS it, still creeping)

`refit_weights` cannot run here (its lambda machinery NaNs on the
placeholder one-body rows, §4), so the RESULT4-§2.3-comparable floor was
measured directly: pure `error_2` L-BFGS over all **145,800** weights at fixed
vectors, exact gradient (`dF/dw_r = 4·K_rs·w_s·A_rs`, `dL/dw_r = 2·Q_r·w_r`;
directional finite-difference check rel 2.2e-2 at h=1e-6 — the residual is
curvature H≈640, confirmed converging 6.6e-2 → 2.2e-2 as h → 0).
Kernel `jiyujia/qcc-chem-coded-r9merged-pure-e2-floor-v6` (COMPLETE, 8 min):
**35.8887 mHa** at the 300-iteration limit (0.34 mHa gained; descent
< 0.01/it at stop). The gate fails by ~16 mHa and no weight move closes it —
same structural cause as RESULT4 §2.3 (frozen vectors at bad angles).

### 2.3 Census: 55/loader × 15 = 825, XOR 0

Full word table = `--coded` two-body words (byte-identical to quantize output)
+ one-body rows from signed-gauge eigenvectors with Hamming `code_bits`
(bit-0 affine per block given the two-body `following`; h1p-free, no crash —
§4). Per-loader Σcuts **55 everywhere** (lsb 55, xor_b1 0, xor_b2 0), identical
over the full range (blocks 1–101) and the two-body-only region (blocks 5+):
delta bit-0 is affine at every block (affine XOR affine needs no slope
match), XOR codes are absent (the quantizer never makes them). Bit-0 affine
cols: 75/75; bit-1/bit-2: 0/75. No loader port exists at 1,696 rows, so
per-loader T is model-only: 235 prod + 69 + 6 = **310/loader** (same caveats
as §1.4, plus no port at all).

### 2.4 Cost: dead twice (exact `SpinFreeData_V1`, chi=10, brot=8)

(9,180,90): outer 431 + inner 10,950 + Givens 2,250 → **T_heur 13,631**,
**Q 432** (persistent 42+45, temp max(175, 305, 77)=305; cf. RESULT6 §1).
Model T = 2·15·310 + 13,631 = **22,931** → **464.8 M at shipped lambda
(GM 17.82)**. Even T_heur alone is 276.3 M; the cap needs L/pass ≤ 455 vs
model 4,650. Primary blocker is e2 (§2.2); cost is an independent wall.

## 3. Negative results recorded (do not redo)

| experiment | result |
|---|---|
| fresh `--coded "1-14"` at (8,143,44) + full 352-w refit | e2 floor **21.216** (gate +1.22); cuts 891 → 715 (71 → 55 on k4–14); slope agreement 6 % |
| `--coded "0-14"` at merged (9,180,90) | quantized **36.229**, pure-w floor **≈35.89** (gate +15.9); cuts 825 (55 × 15, XOR 0) |
| `refit_weights.py` on coded tables | (a): runs, zero movement (true floor). (b): unrunnable — lambda `rotate_columns`/one-body machinery NaNs on placeholder one-body rows |
| public `refine.py` one-body coded path, all 75 cols coded | **crash** (kicks-loop polish, zero-candidate row → `decode` ValueError; §4). Not a candidate defect — public-code robustness gap |
| exact gradient for pure-e2 w-floor | verified by directional finite differences (2.2e-2 at h=1e-6, converging); reusable for future floor fits |
| exact pricing (9,180,90) | T_heur 13,631, Q 432 → ≥ 464.8 M with model loaders; cap needs L/pass ≤ 455 |

## 4. Blocker details

**(a) Precision + code loss, both first-order.** The 1.22 mHa over the gate
survives the full 352-weight refit bit-exactly: the quantizer's pattern choice
is the noise-shaping DOF and the gate leaves 0.17 mHa (RESULT4 §4). The cut
regression is mechanical: `--coded` guarantees per-word bit-0 affine (55) but
neither the XOR-of-five bit-1/bit-2 codes (16 cuts — marculera's machinery,
not in the public pipe) nor slope-matched constant deltas (+20 — closed in
RESULT4 §2). A 91-cut loader needs all three; the public path delivers one.

**(b) e2 and cost, independently.** 35.89 vs gate 20 (w-refit moves 0.34 in
300 it); 464.8 M vs 294.8 M (T_heur alone 276 M is fine — the 4,650 model
loaders are not). The merged size is a precision trap: coding 121,500 angles
costs 21.4 mHa where the gate allows ~5 (14.82 → 20).

**Public-code crash (exact site).** `refine.py:200 assemble` →
`onebody.py:170 refresh` (kicks loop) → `onebody.py:42 polish` with
`even=<all 75 coded cols>` → `encode.py:85 decode` →
`dfthc_math.py:111 reconstruct_u_vectors`: `ValueError: not enough values to
unpack (expected 2, got 1)`. Cause: a kicked trial row with all 75 words
outside the signed range [−66,63] has no legal ±2 move in any column, so
`cands` is empty (`np.array([])` → decode crashes). Triggers only when every
column is even (all-coded); probe (a) with 5 plain columns is unaffected.
Left unmodified (public code); worked around via Hamming `code_bits`
(h1p=None) + pure-e2 floor (§2.2–2.3).

## 5. Files, kernels, verification scope

New in `experiments/frontier/20261116_push/chem/coded_probe/`:

| dir | kernel (resolving slug) | status |
|---|---|---|
| `a-8-143-44/` | `jiyujia/qcc-chem-coded-re-quant-8-143-44-batches-1-14` | COMPLETE (quantize+refine+census) |
| `a-refit/` | `jiyujia/qcc-chem-coded-814344-full-weight-refit-floor` | COMPLETE (floor 21.216) |
| `b-9-180-90/` | `jiyujia/qcc-chem-coded-rounding-at-merged-9-180-90` | quantize COMPLETE (36.229); refine ERROR (§4) |
| `b-census/` | `jiyujia/qcc-chem-coded-r9merged-census-and-e2-floor` | COMPLETE (census 825) |
| `b-floor[2-6]/` | `jiyujia/qcc-chem-coded-r9merged-pure-e2-floor-v6` | COMPLETE (floor 35.889; v1–v5: einsum label / assert / 409 lessons) |

New datasets: `jiyujia/qcc-chem-r9-merged-180x90` (r9 seg0 checkpoint, e2
14.820), `jiyujia/qcc-chem-coded-814344-refined` (21.216),
`jiyujia/qcc-chem-coded-r9merged-rounded` (36.229). Local exact pricing:
verifier's own `SpinFreeData_V1` (cost-model arithmetic only).

Verification actually run: **none** — no candidate passed the local e2 ≤ 20
gate, so the unchanged official verifier (64 shots/address = 78,080 shots,
default + 2 salts) was correctly not run on either candidate. The
294,762,632.08 baseline and its 3-salt PASS (RESULT.md §8) are unchanged.

**No candidate package, no submission.**

## 6. Recommendation

Close the `--coded`-quantizer line at both shapes: (a) fails precision by a
w-refit-proof 1.22 mHa while REGRESSING cuts 71 → 55 (+47 T/loader at shipped
caches); (b) fails precision by ~16 mHa and cost by ~170 M. The live
chemistry lever is unchanged: the emitter/planner pieces of `CODE2.md` §5/§7
(ceiling +0.05 GM, realistic +0.0026 GM on k9/k14) — or, if any fit effort is
spent, a joint U/W fit that produces the XOR joint codes the public
quantizer cannot (that is the 16-cut/loader gap, and it is a training-pipeline
feature, not a rounding flag). Direct remaining effort at `invsqrt`/`dqi`.
