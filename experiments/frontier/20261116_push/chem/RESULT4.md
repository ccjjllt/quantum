# RESULT4 — a new (8,143,44) word table by re-coding, and C=43/42 by a joint w refit

Date: 2026-11-16 (fourth session). Chemistry only. `RESULT.md`, `RESULT2.md`, `RESULT3.md`,
`LAMBDA.md`, `CODE2.md`, `LOADER_R5_PORT.md` stand unchanged. **No submission, no Kaggle run
needed** (nothing passed the local gates; scope in §8). All work here is classical numpy on the
shipped package: the official metric code path (`dfthcsos/scoreinfra/dfthc_math.py`, which is
pure numpy), the public `dfthc_refit` fit machinery (`refit_weights.error_terms` /
`WeightProblem` / `onebody`), the ported planner of `code2/` and the verifier's own
`costs_prepare.SpinFreeData_V1`. Every `error_2` below is the exact verifier formula, validated
against the shipped official numbers to 1e-9 (appendix A).

## 0. Verdict

1. **Direction 1 (new words at the same (8,143,44) shape by re-coding) fails on precision, not
   on the plan.** The slope-matched bit-0 code is real and exactly as valuable as the algebra
   predicts — the census gains **+20 forced cuts per loader** (71 → 91: the five per-word bit-0
   relations go from 11 to 15 cuts each) and it is reachable with **parity-only flips**
   (`v -> v ^ 1`), which keep the value's bits 1..7 and therefore leave the bit-1/bit-2 XOR codes
   intact. But the cheapest useful re-code (**one word column pair, 592 flips, 0.65 % of the
   table**) has a fixed-words `error_2` floor of **36.16 mHa after a full 352-parameter w refit**
   — 1.8× the 20 mHa gate — and the full-loader version (2,872 flips) is **63.24 mHa**. The
   whole remaining `error_2` headroom at this shape is **0.17 mHa** (§4).
2. **Direction 2 (C=43/42/41 at (8,143,C) with a joint w fit) fails on the same gate.** The ANGLE
   word table does not depend on C, so C is exactly "drop one column of `w` per group and refit";
   the 4,025 loaders stay byte-identical. Measured fixed-words `error_2` floors over a free
   344/336/328-weight refit: **21.23 / 23.26 / 25.53 mHa** (gate 20). The reason is structural:
   the 8-bit rounding costs ~5.6 mHa linearly on top of the recorded 14.2 mHa continuous fit
   (14.07 mHa if added in quadrature), so the continuous budget at C=43 is **14.2-14.4 mHa**,
   while C=43 needs `rho = 14.2-14.4 / floor(344) = 1.74-1.76` where `floor(344) = 8.168` and the
   family's best measured `rho` is 1.93. A fresh U fit cannot close a 10 % `rho` gap in the wrong
   direction. Independently, the `lambda_eff` at the C=43 point is 49.26 against a break-even of
   47.17.
3. **Both failures are one fact, now quantified**: the shipped point sits exactly at the top of
   its own `error_2` Pareto curve. At fixed words the `error_2` floor is **19.83 mHa** with
   `lambda_eff 48.52`; the operating point is 20.0000 with 46.92. Those two points give the
   exchange rate **1 mHa of `error_2` ≈ 9.4 units of `Lambda` ≈ 2,900 Toffoli-equivalents of
   cost** (0.17 mHa = 1.60 Lambda = 10.0 M = 500 T-equivalents). A T-for-precision trade
   therefore needs **< 0.00035 mHa per Toffoli gained**; the re-code costs **6-9 mHa per
   Toffoli**, ~2·10^4 outside the budget, for any code and any shape-neutral word change.
4. **The shape family is closed too (new scan, §5).** Exact merges of the shipped table
   ((4,286,88), (2,572,176)) preserve `error_2` and the 1,220 rows *exactly* but cost
   `T_heur` 10,030 / 16,677 and +18 / +36 qubits; the rows-1,220, K=352, B/C=3.25 splits
   (11,104,32) and (13,88,27) have far cheaper heuristics (5,087 / 4,700) but hit the
   `B >= 129` 8-bit inner-QROAM cliff (Q 697). **(8,143,44) is the corner of the whole
   (R,B,C) family at K≈352, rows≈1,220**, by a wide margin.
5. Consequence: chemistry stays at **294,762,632.08** (`T 14,712`, `Q 427`,
   `lambda_eff 46.92160235`). The only live chemistry lever remains the 80 T of loader headroom,
   and it is behind the missing emitter/planner pieces of `CODE2.md` §5 and §7, not behind the
   words.

## 1. What the shipped table's code actually is (measured, new)

Exact structure of `bdae_dataset/submission.npz` (= marculera's 4,025 words, refit weights),
measured over the 76 blocks of 16 addresses (`code3/inspect2.py`, `code3/xor_structure.py`):

| item | measurement |
|---|---|
| bit 0 of columns 5..74 | **affine in the 4 low address bits in 76/76 blocks** (per block a free slope `a ∈ GF(2)^4` and constant `c`) |
| bit 0 of columns 0..4 | free (non-affine): this is why loaders 0 and 1 carry no code and cost 294/288 |
| bits 1..7 of every column | free (non-affine in essentially all blocks) |
| loader delta bit 1, XOR of the 5 words | **exactly affine in t in 76/76 blocks** (0 blocks with any nonzero nonlinear ANF coefficient) |
| loader delta bit 2, XOR of the 5 words | quadratic: the 5 cubic monomials vanish, hence 5 cuts |

That reproduces the shipped forced-cut census exactly: `5 words × 11` (bit 0) `+ 11` (bit-1 XOR)
`+ 5` (bit-2 XOR) `= 71` per loader, 55 for loaders 2-3, 0 for loaders 0-1. The bit-1 code is the
interesting one: each column's bit 1 is a degree-≤4 function of `t`, but the XOR over the ten
columns of a loader's delta is affine — i.e. the code is a *joint* (XOR) constraint that the
quantizer satisfies by construction, not a per-column one.

**The extra cuts that are geometrically available**: for a word whose delta bit 0 is *constant*
(not merely affine) in `t`, the four degree-1 monomials `a0,a1,a2,a3` are cut as well, so that
word contributes **15** cuts instead of 11. Five words → 75 instead of 55, i.e. **+20 cuts =
−10 products = −10 T per loader** if all five deltas become constant. The condition is exactly
`slope(column 5k+j, block h) == slope(column 5k-5+j, block h)` for every block, i.e. one 4-bit
agreement per block.

## 2. Direction 1 — the re-code, measured

### 2.1 Recipe (exact)

For loader `k`, word `j`, block `h`, let `a_R(h)`, `a_L(h)` be the bit-0 affine slopes of columns
`5k+j` and `5k-5+j`. Set `m = a_R(h) ^ a_L(h)`; for every `t` with `parity(m & t) = 1`, replace the
word `v` of the modified column by `v ^ 1`. `v ^ 1` toggles the value's bit 0 only (it is the
parity flip), so `bits 1..7` are untouched and the bit-1/bit-2 XOR codes survive — this matters:
a `±1` *value* move (`v+1`, `v-1`) carries into the higher bits and destroyed both XOR codes
(measured: `xor_b1` 11 → 0, `xor_b2` 5 → 0, i.e. the naive re-code would have *lost* 16 cuts and
gained 20).

Measured census of the re-coded table (`code3/recode.py`, columns 20-24 = loader 4, side
"modify group k"):

```
shipped  k4: lsb0..lsb4 (11,0) each, xor_b1 (11,0), xor_b2 (5,0)      forced 71 + 0
re-coded k4: lsb0..lsb4 (11,4) each, xor_b1 (11,0), xor_b2 (5,0)      forced 71 + 20 = 91
re-coded k5: unchanged (delta only re-based on group 4)               forced 71 + 0
```

`code3/words_recode_k4.npy` holds the re-coded 1,220 × 75 table (2,872 changed cells).

### 2.2 The plan side: +20 cuts does not convert, and the padding breaks

Ported planner (`code2/compile_basis.plan_one`, rank-74 basis, seeds 7, `LS_SECONDS=90`):

| table | planner result |
|---|---|
| shipped, k=4 | no perfect state found on the descent path in 99 s (`full [31,31,31,31,31]`), consistent with `CODE2.md` §4 (the shipped 147-cut state is not reachable from this machinery) |
| re-coded, k=4 | perfect at **Σcuts 155** → 185 products → 185+69+6 = **260 T**, but `solve_padding` = **UNSOLVABLE** for the off-domain slice h=76 |

So the 20 extra cuts convert at ~50 % in the planner (155 vs the 145 baseline the same planner
finds on this table), and the resulting plan cannot be completed: the 12 don't-care rows supply
only 60 free bits for the h=76 padding solve, and the 155-cut state over-determines it. Netting
this against the emitter gap (the shipped k4/k5 are 263 each; this planner re-emits an
*unmodified* loader at 190 products + 69 high + 6 low = 265, `CODE2.md` §4) the re-code is worth
**−1 to −2 T for the k4/k5 pair** (525-524 vs 526), i.e. +0.0006…+0.0013 GM. That is the *cost*
side, measured, and it is already marginal before any precision argument.

### 2.3 The precision side: 36 mHa at the floor, with the whole budget being 0.17 mHa

`error_2` at the **fixed** shipped weights, and then at the **fixed-words w optimum** (pure
`error_2` L-BFGS over all 352 weights, `code3/fliprate.py` + the floor fit):

| table | cells changed | e2 at fixed w | e2 floor over w |
|---|---:|---:|---:|
| shipped | 0 | 19.9999985 | **19.8279** (19.8502 at 400 it) |
| one word pair (col 20 vs 15, loader 4) | 592 (0.65 %) | 43.39 | **36.16** |
| whole loader 4 (cols 20-24) | 2,872 (3.14 %) | 84.58 | **63.24** |

Per-cell rate: **2.35-2.50 mHa²** of `error_2²` per flipped cell (592 → 1,483; 2,872 → 6,753), i.e. **6-9 mHa
of `error_2` per Toffoli** of the prize (63.24 mHa for the ~10 T/loader that survive the
planner: 6.3 mHa/T; 36.16 mHa for the 4 T of a single word pair: 9.0 mHa/T), and a single flip
in the two-body rows already costs +0.06 mHa.

The reason is structural, not a fit failure: a parity flip moves the angle to the *other* side of
the 1/128 grid, so |error| goes from `d` to `1-|d|` for 8 of the 16 words in the block — the code
is the quantizer's *noise-shaping* degree of freedom (the shipped `quantize.py --coded` picks one
of 32 affine patterns per (block, column) to minimise the curvature-weighted squared offset;
the slope-matching constraint leaves 2 of 32).

Stated against the gate: the **cheapest** re-code adds **16.3 mHa of `error_2` floor** on top of
the shipped floor (36.16 vs 19.83), while the gate leaves **0.17 mHa** and that 0.17 is already
converted into `lambda_eff` (§4). A fresh continuous fit can recover *part* of the 16.3 mHa by
moving the free angles through the rounding, but what the constraint takes away — 30 of the 32
patterns at every (block, column) of two columns — is exactly the mechanism the shipped quantizer
uses to shape the rounding error, so no training schedule closes a 96x gap. This is why the
public frontier moved 8 Toffolis in 72 h with new codes and never touched the word values. A fresh continuous fit can recover only part of the 36 (it can move the
free angles through the rounding, but not undo the 2-of-32 pattern restriction, whose cost is
first order), so this direction cannot pass at this shape for any word table that carries the
slope-matched code.

## 3. Direction 2 — the C axis with a joint w refit

C is not in the angle table (`U` is indexed `(R, B, ·)`; the copies live in `w` alone), so
lowering C keeps the 4,025 loader Toffolis and only changes `submission.npz`. The verifier's own
cost model (Q stays 427: `b1`, `k2_opt` and the inner temp are unchanged):

| C | outer | inner | T_heur | T | cost at lambda 46.9216 | break-even lambda |
|---:|---:|---:|---:|---:|---:|---:|
| 44 | 317 | 4,095 | 6,662 | 14,712 | 294.763 M | 46.9216 |
| 43 | 315 | 4,019 | 6,584 | 14,634 | **293.200 M** | 47.1717 |
| 42 | 312 | 3,943 | 6,505 | 14,555 | 291.617 M | 47.4277 |
| 41 | 310 | 3,867 | 6,427 | 14,477 | 290.054 M | 47.6833 |

Implementation (`code3/caxis.py`): drop the `drop` weakest copies per group (importance
`||X_rc||_F`; weakest 0.224-0.292 vs strongest 0.620-0.779), keep them pinned at zero, refit the
surviving `w` (and the offsets `W`) with the exact `error_2` formula and gradients.

```
C=44  e2 floor 19.8279 mHa   (lambda_eff at the floor 48.52)
C=43  e2 floor 21.2267 mHa   (49.26 at the best lambda fit; e2 cannot go below 21.22)
C=42  e2 floor 23.2608 mHa   (49.91)
C=41  e2 floor 25.5276 mHa   (50.21)
```

Two independent walls, both exact:

* **rank/quantization wall.** Rank floors from the exact `H` spectrum (`code3/rank_floor_K.py`,
  reproduces the verifier on the shipped table): K = 328/336/344/352 → **10.267 / 9.130 /
  8.168 / 7.361 mHa**. The 8-bit rounding of this table costs 5.6 mHa linearly on top of the
  recorded 14.2 mHa continuous fit (14.07 mHa in quadrature), so the continuous budget at
  1,220 rows is **14.2-14.4 mHa**, and C=43 needs `rho <= 14.2-14.4 / 8.168 = 1.74-1.76`.
  Measured `rho` at the shipped point is 1.93; at C=43 the fixed-words fit already realises
  `21.23`, i.e. a continuous part of 15.6-15.9 mHa and `rho = 1.91-1.95`. Better `B/C` (3.33 vs
  3.25) cannot buy 10 %.
* **lambda wall.** Break-even for C=43 is `lambda_eff <= 294,762,632/(14,634·427) = 47.1716`
  (+0.250). The C=43 refit reaches 49.26 at its best `error_2`, i.e. +4.4 %.

Contrast for direction 2's arithmetic: if the gate *had* passed, C=43 is worth
`46.9216 · 14,634 · 427 = 293,199,862` (−1,562,770, −0.53 %, **+0.050 GM**), C=42 −1.07 %
(+0.101 GM) and C=41 −1.60 % (+0.152 GM), each conditional on holding `T_heur` at the cost
model's value while the *fit* clears 20 mHa. It is the single most valuable chemistry lever left,
and it is the one the precision gate closes hardest — by 1.2 / 3.3 / 5.5 mHa of measured
`error_2` floor.

## 4. Why both fail: the measured `error_2`/`Lambda` exchange rate

Both directions are "spend precision, buy Toffolis". The price of precision is now measured on
the shipped words (fixed words, exact `error_2`, exact verifier `Lambda`):

| point (fixed words, best w) | error_2 | Lambda | lambda_eff |
|---|---:|---:|---:|
| pure `error_2` minimum | 19.8279 | 289.35 | 48.52 |
| best `lambda` fit found here | 19.9766 | 289.27 | 47.43 |
| published (bdae290f) | 19.9999985 | 283.144 | 46.9216 |

The curve is very steep at the top: from 19.83 to 20.00 mHa (0.17 mHa) the frontier gives up
1.60 units of `Lambda` = 3.4 % of `Lambda` = 10.0 M of cost = **500 Toffoli-equivalents**. Hence

* **1 mHa of `error_2` ≈ 2,900 Toffoli-equivalents**, i.e. the affordable trade is
  **0.00035 mHa per Toffoli**;
* the re-code costs 6-9 mHa per Toffoli (measured, §2.3): ~2·10^4 over budget;
* C=43 needs 1.23 mHa (measured floor 21.23 vs the gate 20) and would gain 78 T, i.e. it needs
  `1 mHa ≈ 63 T` — 55× better than the market rate, which is exactly why it cannot be bought;
* and C=43 additionally asks for `rho <= 1.74` where the family measures 1.93.

## 5. The shape scan (new): (8,143,44) is the corner

Exact `SpinFreeData_V1` numbers from the verifier's own cost module (`code3/scan_shapes.py`;
Q includes the 40 ANGLE word qubits: the model reproduces (8,143,44) → `T_heur 6,662`,
`Q 427`, `outer 317 / inner 4,095 / Givens 2,250` exactly).

**Exact merges of the shipped table** (`structure.merge` is exact: same `error_2`, same
1,220 rows, same 4,025 loader Toffolis, block-diagonal weights):

| shape | T_heur | Q | T | cost |
|---|---:|---:|---:|---:|
| **(8,143,44)** | **6,662** | **427** | **14,712** | **294.76 M** |
| (4,286,88) | 10,030 | 445 | 18,080 | 377.6 M |
| (2,572,176) | 16,677 | 463 | 24,727 | 537.0 M |

The merged shapes were previously treated only as a *route* to (4,143,75) (`RESULT3.md` §2.1);
priced as final shapes they are 28-82 % worse, because the inner state preparation scales with
`C·B`, not with `R·C`.

**Rows-1,220 / K=352 / B/C=3.25 splits** (same loaders, same rank floor 7.36, so precision is
comparable — only the heuristic changes):

| shape | rows | T_heur | Q | T | cost |
|---|---:|---:|---:|---:|---:|
| (8,143,44) | 1,220 | 6,662 | 427 | 14,712 | 294.76 M |
| (11,104,32) | 1,220 | **5,087** | 697 | 13,137 | 429.6 M |
| (13,88,27) | 1,220 | **4,700** | 697 | 12,750 | 417.0 M |

(11,104,32) would be a −1,575 T shape, but `B = 104 < 129` puts the 8-bit inner QROAM on the
wrong side of the `k2` cliff (`inner_state_prep_qubit_cost` → 569 temporary qubits instead of
303), and Q is worth 0.0219 GM per qubit: +270 qubits = +5.9 GM of loss. The same 8-bit cliff
also closes B = 135-142, which the row-scaled loader would otherwise like
(`code3` scan: B=135 would be 286.0 M with a pure row scaling) — those are the already-measured
closed B axis (`RESULT.md` §5: B=129 → continuous 19.83 mHa → quantized 24+), and the true
loader floor does not row-scale (the 69-high/6-low address cache is fixed).

## 6. Negative results recorded (do not redo)

| experiment | result |
|---|---|
| bit-0 slope re-code, full loader (2,872 parity flips) | census +20 cuts exactly as predicted; `e2` floor **63.24 mHa** (3.2× gate) |
| bit-0 slope re-code, one word pair (592 parity flips) | `e2` floor **36.16 mHa** (1.8× gate); per-cell rate 2.35-2.50 mHa² |
| `±1` *value* re-code (carries into bits 1-7) | destroys `xor_b1` (11→0) and `xor_b2` (5→0): net +4 cuts instead of +20 |
| re-coded k4 plan | Σcuts 155 (not 165); `solve_padding` UNSOLVABLE at h=76; net −1 to −2 T for the k4/k5 pair |
| C=43 / 42 / 41, free 344/336/328-weight refit | `e2` floors 21.23 / 23.26 / 25.53 mHa (gate 20); `lambda_eff` 49.26 / 49.91 / 50.21 |
| shape: (4,286,88), (2,572,176) | exact-`e2` merges, but `T_heur` 10,030 / 16,677 and Q 445 / 463 |
| shape: (11,104,32), (13,88,27) | `T_heur` 5,087 / 4,700 but Q 697 (8-bit inner-QROAM cliff at B < 129) |
| free `w` refit at C=44 | the fixed-words `e2` floor is 19.83 mHa: the shipped table is 99.1 % of its own floor, so there is no spare precision anywhere |

## 7. What the last 80 T would take (unchanged, for the record)

`CODE2.md` §1 headroom: k0 −31, k1 −25, k2/k3 −6 each, k9 −1, k10 −2, k11-13 −2 each, k14 −3
(= 80 T ≈ +0.051 GM — 40× the 2 T in the brief). Every one of those plans is already found; the
blockers are emitter/planner features, not words: the delta-helper load at batches 9/10/14, the
per-batch low cache at 11-13, the k0 window-schedule generator, the 68-high subspace cache, and
147 cuts on k11-13. Two things this session adds to that picture:

* the plans already found that are *wins* are **k9 (−1) and k14 (−3)** — 4 T, and both are
  unemittable (delta-helper at batches 9/14); k10 and k12 are ties. So the emitter work alone
  yields +0.0026 GM, not +0.05: the 56 T of k0/k1 is the real prize and it needs the windowed k0
  schedule generator and a >99-cut plan for k1, neither of which exists in any published tree;
* the loader-to-loader *net* accounting matters: re-emitting a loader with this planner costs
  +2 T against the shipped emitter (263 → 265), so any word/code change has to clear +2 T per
  touched loader before it pays.

## 8. Files, kernels, verification scope

New in `experiments/frontier/20261116_push/chem/code3/`:

| file | what it does |
|---|---|
| `evalkit.py` | local exact evaluator: official metrics (`evaluate_dfthc_angle_words`) + the fixed-vector `error_2` formula; reproduces the shipped 19.9999985 / 46.92160235 to 1e-9 in 0.5 s |
| `inspect2.py`, `xor_structure.py` | the per-(column, block) affine census of §1 and the XOR-of-ten bit-1/bit-2 structure |
| `scan_shapes.py` | the §5 shape scan with the verifier's own `SpinFreeData_V1` |
| `recode.py` | slope-matched parser re-code (parity flips), census of the forced cuts, `words_recode_k4.npy` |
| `plan_test.py` | ported planner on the shipped vs re-coded table (155/185/260, padding unsolvable) |
| `fliprate.py` | the `error_2` price of 1 / 8 / 592 / 2,872 parity flips |
| `caxis.py` | C=44/43/42/41 with a free w refit: `error_2` floors and `lambda_eff` |
| `rank_floor_K.py` | rank floors at K = 328-356 (extension of `rank_floor.py`) |

Verification actually run: **none on Kaggle, and none was possible** — no candidate passed the
local `error_2` gate, so there is nothing to hand to the official verifier. The local evaluation
was calibrated on the shipped package: `error_1 19.999205 / 19.999998`, `error_2 19.9999667 /
19.9999985`, `Lambda 283.216541 / 283.144439`, `E_gap 3.9149023070 / 3.9148980015`,
`lambda_eff 46.92764345 / 46.92160235` for `marculera_ds` / `bdae_dataset` respectively — i.e. the
official metric path, not a model. Every `error_2` floor quoted above is that same exact formula
over `w`; the only model in this note is the shape scan's row-scaled loader (§5), which is
flagged as such and used only for ranking.

**No candidate package, no submission, no Kaggle kernel.**

## 9. Recommendation

Keep chemistry frozen at 294,762,632.08. Concretely, for the remaining window:

* do **not** re-code, re-quantize or re-fit the words: the `error_2` market rate is 2,900
  Toffoli-equivalents per mHa and the shape has 0.17 mHa left, which is already monetised;
* do **not** cut C: the C=43 `error_2` floor is 21.23 mHa with the words fixed and its `rho`
  requirement (1.74) is below anything this shape family has measured (1.93), so a joint U/W fit
  cannot pass either;
* if any chemistry effort is spent, spend it on the emitter pieces of `CODE2.md` §5/§7 and
  accept a ceiling of +0.05 GM, with the realistic near-term being +0.0026 GM (k9/k14);
* direct the parallel effort at `invsqrt`/`dqi`, where a single Toffoli of effort is not
  competing with a saturated, precision-pinned frontier.

## Appendix A — calibration of the local evaluator

```
marculera_ds (4,025 build)   e1 19.999205  e2 19.9999667  Lambda 283.216541  E_gap 3.9149023070  lam_eff 46.92764345
bdae290f    (published best) e1 19.999998  e2 19.9999985  Lambda 283.144439  E_gap 3.9148980015  lam_eff 46.92160235
chem_sub1   (local refit)    e1 19.999998  e2 19.9999985  Lambda 283.144563  E_gap 3.9148980015  lam_eff 46.92161275
```

The three tables share **identical words** (verified `np.array_equal`), which is why every word
experiment above is run on `bdae_dataset` and every weight experiment on the same 1,220 × 75
table. `error_2` from `refit_weights.error_terms`/`WeightProblem` matches the official value to
8e-13 mHa on all three.
