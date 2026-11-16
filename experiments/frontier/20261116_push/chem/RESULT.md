# dfthcsos chemistry: T decomposition and the loader/heuristic block

Date: 2026-11-16 (session ~08:00–13:30 UTC). Scope: chemistry only.
All circuit simulation and every official verification below ran on **Kaggle CPU kernels**
(`enable_gpu: false`, `enable_tpu: false`, no internet). Local work was classical
(numpy/scipy) algebra on `submission.npz` and on the verifier's pure-Python cost model.
No Kaggle submission was made.

## 0. Verdict first

1. **The verified baseline is exactly the published one.** Kaggle CPU kernel
   `qingyu1232/qcc-chem-t-decomposition-and-loader-slack` ran the **unchanged** official
   `dfthcsos/verify.py` on `marculera/dfthc-c44-build` at the default salt and at two extra
   salts (`dfthcsos-20261116-a/-b`): all three **PASS** with
   `score 294,800,582.44`, `T = 14,712`, `Q = 427`, `lambda_eff = 46.927643`.
2. **T splits 8,050 loader / 6,662 heuristic**, and *both* halves are pinned:
   `T = 2 x 4,025 (ANGLES, measured) + 317 (outer) + 4,095 (inner) + 2,250 (Givens)`.
3. **No >=1% T reduction is available from any lever we can reach.** T=14,000 (the +0.47 GM
   step) needs 712 T, which is either 9 more products (`dT/dC = 78` each) or **365 fewer
   loader Toffolis per pass (-9.1%, i.e. 33 fewer feature columns per loader)**. The first is
   blocked by a precision budget of ~3e-5 mHa on error_2 (one product costs ~1.3 mHa); the
   second is a fit-level re-coding problem in which
   the whole public field moved **8 Toffolis in 72 h** (4,033 -> 4,025, +0.005 GM).
4. Chemistry should be treated as **frozen at 294.7-294.8 M**. The largest remaining chemistry
   headroom is the `lambda_eff` floor: `46.9216 -> >= 46.786` = **+0.086 GM**, not a step.

## 1. Hypothesis tested

Priority-1 hypothesis from the brief: *"print the exact `resources` breakdown, then attack the
dominant part"*. If the ANGLE loaders dominate, a loader improvement is the only >=1% lever;
if the heuristic dominates, a shape change is. Both were measured, then both were pushed
against their hard constraints with the official cost model and with the shipped circuit
algebra.

## 2. Exact resource breakdown (official verifier, `resources` dict)

Kernel: `qingyu1232/qcc-chem-t-decomposition-and-loader-slack`
(build = `marculera/dfthc-c44-build`, `submission.npz` sha256
`302e608cbbcb45e8c9155cdd26e7a6217ffc582991c306b587ec2fa8ae32e2e9`,
`angle_k_14.kmb` sha256 `ab06b98fc22fce8a33b591db9caf73e93d407342a6c0f3d2e2e1416dffffdfd7`).

```
T_total 14,712 = angles_toffoli         8,050   (54.7%)   4,025 per pass x 2 passes
               + outer_state_prep         317   ( 2.2%)
               + inner_state_prep       4,095   (27.8%)
               + givens_rotations       2,250   (15.3%)   2*(76-1)*(2*8-1)
Q_total    427 = persistent 124 (angles 40 + outer 40 + inner 44) + temporary 303
                 (max(outer_temp 90, inner_temp 303, angles_temp 77); temp 303 is inner's)
cap            : angles_qubits 128 (11 selection + 40 word + 77 workspace), within_cap True
metrics        : error_1 19.9992 mHa, error_2 19.99997 mHa (gates 20), Lambda 283.2165,
                 E_gap 3.914902 Ha (floor 3.914898), lambda_eff 46.927643
per-loader     : [294, 288, 269, 269, 263, 263, 263, 263, 263, 264, 265, 265, 265, 265, 266]
                 qubits [128, 126, 125 x 11, 126 x 3]   (sum 4,025)
```

Local cross-check of the weights that the brief calls the current best
(`chem_sub1/submission.npz`, same words, refit weights) through the packaged
`dfthc_math.evaluate_dfthc_angle_words` + `reference` (classical only, no simulation):
`e1 20.0000, e2 20.00000, Lambda 283.1446, E_gap 3.914898, lambda_eff 46.921613`
-> `46.921613 * 14,712 * 427 = 294,762,697.44`, matching the reported 294,762,697.44.
The published 294,762,632.08 is the same T/Q with `lambda_eff = 46.92160` (not re-verified here).

## 3. Exchange rates (chemistry marginal value at the 28.09 GM baseline)

| change | Delta chem cost | Delta GM |
|---|---:|---:|
| 1 Toffoli | 0.0068% | **0.00064** |
| 1 qubit | 0.234% | **0.0219** (= 34.5 Toffoli) |
| 1% `lambda_eff` | 1.0% | 0.333% = 0.0936 |
| loader 1 Toffoli/pass | 0.0136% | 0.0045 |
| T 14,712 -> 14,000 | -4.84% | +0.47 |
| T -> 13,000 | -11.6% | +1.19 |

## 4. Why the 8,050 loader Toffolis are pinned

Anatomy, recovered from the shipped circuits + `syed_v12` source (`compiler/emit_plan.py`,
`gauge_plan_fit.cross_tensor`, `parity_recover.outer`), per loader (268.3 avg):

* the loader loads **`delta = words_k XOR words_{k-1}`** (so the reverse pass clears the
  registers) and only the **low 7 bits of its five words = 35 outputs**; bit 7 rides on a
  "polarisation" helper that is CNOT-decoded at the end, so it is free;
* **69 high-monomial Toffolis** = *all* monomials of mask 1..76 with weight >= 2 (not a minimal
  set: every one of them is used). The 11 address bits split 4 low / 7 high; the high index has
  77 used values (1220 = 76*16 + 4);
* **product Toffolis: 2,900 in total (avg 193, range 188-219) = 386 paired feature columns / 2**
  in the reference plan: each Toffoli pairs two low monomials that share the same 35-bit output
  mask (CX fan-in/fan-out free, target written straight into a word qubit);
* **6 low-cache Toffolis** (helpers give the 4-bit algebra in 6 ANDs instead of 11);
* so a loader = 69 + 6 + (188..219) = 263..294 Toffolis, avg 268.3; 15 loaders = 4,025.
* all 75 cache monomials are cleaned with **MBU (HMR + classically-controlled CZ)**, which is
  free in this cost model, so the loader has no uncompute Toffolis. There is no pairing slack
  left: 386 is even and fully paired, which the authors state as optimal ("dropping one spare
  class never lowers it").

Measured attempts to find slack (this session):

1. **Naive ESOP/ANF cost of the shipped table is 2,036 monomials per 40-bit loader** (uniform
   completion, rows 1220..2047 = 0) versus 193 shipped. The public plans' don't-care padding is
   worth a factor 5; there is no naive-ESOP shortcut.
2. **The union feature set of a loader is saturated**: over its 35 outputs, all 15 low
   monomials x all 77 high monomials have nonzero coefficients, so the product count is decided
   by the *column* count (386) and the pairing, not by a sparser support we could pick.
3. **Don't-care freedom cannot reach the forced part, and it buys nothing.** The ANF coefficient
   `a[m]` is the XOR of the table over the submasks of `m`, all of which are `<= m`; rows
   0..1219 are pinned, so every `a[m]` with `m < 1220` is forced and only `a[m]` with `m >= 1220`
   (the top high indices) can be moved by choosing the 828 unreachable addresses. The plan's
   whole coefficient set uses high masks 1..76, i.e. `m = 16*g + f <= 1231`, and only the 12
   coefficients `m = 1220..1231` (high mask 76, low 4..15) are free at all. Kernel
   `qingyu1232/qcc-chem-loader-don-t-care-descent` confirmed this empirically: a full sweep of
   all 33,120 single-bit don't-care flips (828 rows x 40 columns, per loader, full recompute)
   produced **0 improving moves for all 15 loaders** (`base 20,819 -> best 20,819` on that
   coarse objective). Corollary: the loader cost is a deterministic function of the shipped
   1,220 x 40 delta table; loader gains can only come from changing the *words* (rounding /
   pi-gauge / XOR-code choices), never from the padding rows. That is exactly the axis on which
   the public field moved 8 Toffolis in 72 h.
4. Public churn for reference: maoxin 4,057 (11-13) -> 4,044 -> 4,038 -> 4,033 (11-14) ->
   marculera 4,025 (11-15, codes on the XOR of five words). **8 Toffolis in 72 h.**

Territory already closed by the field and re-confirmed by the algebra above: exact Toffoli scan
of the loaders (no removable Toffoli in the correct data model), product-set/ESOP rewrites,
tree/row/gauge search, MBU for the products (illegal: the products write real word data).
Cheaper than a fixed 75-monomial address cache is impossible because the cache is
column-independent: it is needed to express *any* product's high factor.

## 5. Why the 6,662 heuristic Toffolis are pinned (official `SpinFreeData_V1`, exact)

Computed with `scoreinfra/costs_prepare.py` (pure formula, no simulation):

| (R,B,C) | T_heur | outer | inner | givens | dT |
|---|---:|---:|---:|---:|---:|
| **(8,143,44)** | **6,662** | 317 | 4,095 | 2,250 | 0 |
| 8,143,43 | 6,584 | 315 | 4,019 | 2,250 | -78 |
| 8,143,42 | 6,505 | 312 | 3,943 | 2,250 | -157 |
| 8,143,40 | 6,348 | 307 | 3,791 | 2,250 | -314 |
| 8,143,36 | 6,034 | 297 | 3,487 | 2,250 | -628 |
| 8,142,44 | 6,660 | 317 | 4,093 | 2,250 | -2 |
| 8,139,44 | 6,654 | 317 | 4,087 | 2,250 | -8 |
| 8,129,44 | 6,634 | 317 | 4,067 | 2,250 | -28 |
| 8,144,44 | 7,016 | 317 | 4,449 | 2,250 | **+354** |

* **B = 143 is the last B before the inner step jumps** (`ceil((B+1)/16) = 9` up to B=143,
  10 from B=144: +354 T). B=129 buys only 28 T of heuristic (its real value is the loader rows,
  -554 T, which is the closed B axis: continuous e2 19.83 mHa at B=129 -> quantized 24+ mHa).
* **C costs 78 T per product** (inner 76 + outer 2) = 0.050 GM per product, but the shipped
  table already sits on both error gates (19.9992 / 19.99997 mHa) and on the `E_gap` floor
  (3.914902 vs 3.914898), so the affordable C reduction is **<1 product**. Reaching C=36
  (needs 628 T = 10 products) requires ~13 mHa, i.e. a continuous two-body floor near 1 mHa
  when the measured continuous floor is 14.2-14.8 mHa and the 8-bit rounding penalty alone is
  ~13.7 mHa (quadrature). Not reachable by refitting; a quantization-aware fit at most buys
  4-5 products (+0.2 GM) even in the limit of zero rounding penalty.
* `Q = 427` remains the global minimum for R=8, B in [129,143], brot=8, J=5 (verified earlier
  and unchanged: `b2 = 19` forces k2=4, inner temp 303).
* **J axis, exact model** (cache 75 fixed + 4.83 T per loaded bit, anchored on 268 at 40 bits):

| J | K | L/pass | T | Q | chem cost | verdict |
|--:|--:|--:|--:|--:|--:|---|
| 3 | 25 | 4,770 | 16,202 | 411 | 312.5 M | +6% |
| 4 | 19 | 4,359 | 15,379 | 419 | 302.3 M | +2.6% |
| **5** | **15** | **4,025** | **14,712** | **427** | **294.8 M** | **best** |
| 6 | 13 | 3,986 | 14,634 | 435 | 298.7 M | +1.3% |

  J<5 would cut Q (worth 0.0219 GM per qubit) but the address cache is column-independent, so
  T rises more than Q falls. J=5 confirmed. Measured directly on the shipped delta table
  (`j_scaling.py`): a loader's address algebra is **saturated even for a 3-word subset** ---
  69 high masks and all 1,155 (low, high) feature columns appear for J=3, 4 and 5 alike. The
  per-loader cost is therefore set by the address algebra and the *mask distinctness* (which
  grows with the number of loaded output bits, ~4.83 T/bit), not by the word count: fewer
  loaders (larger J) is the right direction, and J=5 is the largest J that still leaves a
  workable 77-qubit workspace (J=6 fits but costs +8 Q = +1.87%).

## 6. What a real T step would require (precise blocking site)

To reach **T = 14,000 (+0.47 GM)** from the current point, exactly one of:

* **loader 4,025 -> 3,669 per pass** (-356, -8.8%): i.e. 386 -> **~324 feature columns per
  loader** (193 -> ~165 products) with the address cache untouched. This is a word-table
  re-coding problem (8-bit rounding choices x pi-gauge negations x XOR codes at bits 0-2), not a
  circuit-synthesis problem. Public rate of progress on it: 8 Toffolis / 72 h.
* **C 44 -> 35** (9 products, 702 T): requires the continuous two-body floor to fall from
  14.2-14.8 mHa to <= ~4 mHa at the same Lambda; no public or in-repo fit has come within
  9 mHa of that.
* a shape whose heuristic is >=700 T cheaper at equal precision: excluded by the table in §5
  (B=144 costs +354; B<=129 gains 28 and loses precision; C is the only large term).

To reach **T = 13,000 (+1.19 GM)** the loaders would have to drop to 3,169/pass (-21%), i.e.
bundling 30 columns fewer per loader than the current best plan family achieves; not in reach.

## 7. Negative results recorded (do not redo)

| experiment | result |
|---|---|
| naive ESOP/ANF loader on the shipped table | 2,036 monomials / 40-bit loader vs 193 shipped (5x worse) |
| union-feature sparsity of a loader | saturated (15 low x 77 high all present) -> no support-shrinking win |
| don't-care coordinate descent (828 free rows x 40 bits x 15 loaders) | 0 improving moves in a full sweep for every loader (`base 20,819 -> best 20,819`); consistent with the forced-coefficient theorem: only `a[m]`, `m = 1220..1231`, are free |
| B=144 / B=159 shapes | +354 T (step) or need 6 products of precision |
| J = 3,4,6 | +6%, +2.6%, +1.3% cost (cache is column-independent) |
| C reduction | 78 T/product, but <1 product of precision headroom on both gates and on E_gap |
| lambda refit | floor 46.786 vs 46.9216 now: +0.086 GM ceiling for the whole line |

## 8. Artifacts and verification scope

* Kaggle kernel (CPU, no internet): `qingyu1232/qcc-chem-t-decomposition-and-loader-slack`
  — output `chem_decomp.json`; official verifier run at salts `""`,
  `dfthcsos-20261116-a`, `dfthcsos-20261116-b`, all PASS, identical score.
* Kaggle kernel (CPU): `qingyu1232/qcc-chem-loader-don-t-care-descent` — 0 improving
  don't-care moves for all 15 loaders (§4.3), output `anneal.json`.
* Local classical scripts (no simulation): `anf_scan.py` (2048-point ANF census),
  `grid1232.py` (16x77 plan-grid feature census), `plan_cost.py` (paired-column algebra),
  `j_scaling.py` (address-algebra saturation vs J) in this directory.
* Best verified package (path/hash): `marculera/dfthc-c44-build` downloaded to
  `/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/`,
  `angle_k_{0..14}.kmb` + `submission.npz`, cost **294,800,582.44**. The published best
  (294,762,632.08) is the same circuits with refit weights; our local refit copy
  `…/qcc_push/chem_sub1/submission.npz` reproduces 294,762,697.44 metrics-only.
* Build verified: `marculera/dfthc-c44-build` (Apache-2.0), `submission.npz` sha256
  `302e608c…32e2e9`; per-loader counts and the 128-qubit cap re-measured by simulation.
* **Verification scope**: the 294,800,582.44 figure is a full official-verifier run (78,080
  shots, 3 salts) on a Kaggle CPU kernel. The 294,762,697.44 figure is a *metrics-only* recompute
  of the refit weights through the packaged `dfthc_math` (no circuit simulation) plus the
  verified T=14,712, Q=427 — it is not a fresh 78,080-shot verification. The 294,762,632.08
  figure is quoted from the public frontier, not re-verified here.
* No candidate package is produced: no lever in this block yields a T step.

## 9. Recommendation to the main session

Freeze chemistry. Its T is a joint optimum of (i) a loader construction that needs six
credits' worth of machinery to move 8 Toffolis in three days and (ii) a heuristic that is a
closed-form function of a shape pinned by a ~3e-5 mHa precision budget and a provable Q minimum.
Direct the remaining window at `invsqrt`/`dqi`, where the same 1 T of effort is not competing
with a saturated public frontier.
