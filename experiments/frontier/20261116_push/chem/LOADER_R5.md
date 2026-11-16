# LOADER_R5 — can a 791-row ANGLE loader be built at ≤ 237 T/circuit?

Design/plan exercise only (no fit, no build). Target shape (R,B,C) = (5,143,75),
rows = 76 + 5·143 = **791**, 10 selection bits. Budget for T < 14,000:
`L/pass ≤ 3,555` ⇔ **≤ 237 T per loader** (15 circuits). Current shipped point:
268.3 per loader (4,025/pass, T = 14,712).

## 0. Answer

* **The cap is not the problem — it gets easier.** 10 selection + 40 word = 50
  persistent qubits, so the workspace grows from 77 to **78**, while the plan needs
  only ~51 (43 high + 6 low + pivots). At 791 rows the 128-qubit pressure that
  forced the shipped compromises is relaxed by 27 qubits.
* **The budget is plausible but not automatic.** The shipped cost algebra is
  `loader = 6 (low cache) + #{high monomials of weight ≥ 2} + (525 − Σcuts)/2`,
  and `525 = 15 low monomials × 35 outputs` is **independent of the row count**.
  At 791 rows the cache term drops 69 → 43, so the same cut coverage as today
  (Σcuts = 139) gives **242/loader → T = 14,149 (GM +0.36)** — a real win, but
  5 T over the 237 budget. ≤ 237 needs **Σcuts ≥ 149** (+7 %); the 211 projection
  needs **Σcuts = 201** (+45 %).
* **Fewer rows means more cuts, and that is the mechanism the projection relies
  on.** The cut per block is the nullspace of the h < hmax target slices: with
  76 constraints (1,220 rows) a 3-low × 35-out block (105-dim) leaves ≥ 29
  directions, with 49 constraints (791 rows) it leaves ≥ 56. Over the planner's
  5 blocks that is ≥ 280 cuts → ≤ 122 products → **~171/loader** *if* the pairing
  admits them. The shipped point (139 observed vs 145 by this bound) validates
  the arithmetic. So the honest range at 791 rows is **171–242 per loader**,
  i.e. **≤ 237 is likely, ≤ 211 is possible**, and even the pessimistic end is a
  +0.36 GM step.
* **The published code ships the planner, not its inputs.** `planner.py`,
  `parity_recover.py` (the Lovász matroid-parity rank certificate),
  `extract_matching.py`, `transport_cuts.py`, `gauge_plan_fit.py`,
  `low_helper_cache.py`, `padding_completion.py` and the emitter `emit_plan.py`
  are all in `syed_v12/src/dfthcsos_source/`. Missing: `prove_loader_branches.py`
  (imported by `compile_loaders.py`), the v18 input trees, and the hardcoded
  1220/1232/77/11 geometry. The port is bounded, not research.

## 1. The exact cost algebra (from the shipped code)

`research/scripts/planner.py`:

```
products = (525 - sum c) / 2      # NDIM = 15 low monomials x 35 outputs = 525
                                  # parity_recover.py: NOUT = 35, NDIM = 15*NOUT
cost/loader = products + #{high monomials of weight>=2} + low cache
```

with `c` = cut dimensions found by `BlockPlan`/`greedy`/`local_search`/`top_down`
and certified by `parity_recover.candidates` + `alternating_field` (rank/2 is a
constructive lower bound on the maximum independent product pairing — i.e. the
matroid-parity step is shipped). The shipped certificate records
`products 193`, `independent_columns 386`, `sum_cuts 139`, which satisfies
`(525 − 139)/2 = 193` exactly — the algebra is confirmed against the shipped plan.

Per-loader numbers at 791 rows (high index = ⌈791/16⌉ = 50 values ⇒ monomials
1…49, of which 43 have weight ≥ 2; low cache 6):

| Σcuts | products | per loader | L/pass | T | chem cost | GM | ΔT |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 139 (today's coverage) | 193 | **242** | 3,630 | 14,149 | 283.5 M | **28.46** | −563 |
| 149 | 188 | **237** | 3,555 | 13,999 | 280.5 M | 28.56 | −713 |
| 160 | 182 | 231 | 3,465 | 13,819 | 276.9 M | 28.68 | −893 |
| 180 | 172 | 221 | 3,315 | 13,519 | 270.9 M | 28.89 | −1,193 |
| 201 (the 211 projection) | 162 | **211** | 3,165 | 13,219 | 264.9 M | **29.11** | −1,493 |
| 220 | 152 | 201 | 3,015 | 12,919 | 258.8 M | 29.34 | −1,793 |

(`T = 2·L/pass + T_heur`, `T_heur(5,143,75) = 6,889`, `Q = 427` unchanged; cost at
`lambda_eff = 46.9216`.)

## 2. Why the row reduction helps twice, and why the "174" projection is wrong

Two independent effects of rows = 76 + R·B:

1. **Cache (linear in high index).** 77 → 50 high values ⇒ 69 → 43 high
   monomials: **−26 T/loader**. This is the *only* term that the "row-scaled"
   estimate (268 × 791/1220 = 174) captured, and it is the reason that estimate is
   wrong: it also scaled the product term.
2. **Cut space (inverse in the constraint count).** Each block is
   `3 low monomials × 35 outputs = 105` dimensions and is constrained by one
   vector per high slice (h < hmax):

   | rows | hmax | constraints | nullspace / block | × 5 blocks | ⇒ products ≥ |
   |---:|---:|---:|---:|---:|---:|
   | 1,220 | 77 | 76 | 29 | 145 | 190 |
   | 934 | 59 | 58 | 47 | 235 | 145 |
   | **791** | **50** | **49** | **56** | **280** | **122** |

   The shipped plan realises 139 of the 145 bound at 1,220 rows, so the bound is
   tight and the 791-row bound (~280 cuts, capped by NDIM = 525) is credible. The
   *usable* cut set is then limited by the pairing certificate
   (`alternating_field` rank), which is exactly what `planner.greedy`/`top_down`
   optimise.

So: **≤ 237 needs Σcuts ≥ 149, which is 7 % above today's coverage but 47 % below
the block bound.** The 211 projection needs 201, which is 72 % of the bound. Both
are inside the arithmetic window; neither is guaranteed.

## 3. What is shipped vs what is missing

Shipped (all in `syed_v12/src/dfthcsos_source/`, Apache-2.0):

| file | role |
|---|---|
| `research/scripts/planner.py` | block-cut planner: `BlockPlan`, `greedy`, `local_search`, `top_down`, `complete_words`, `cost = (NDIM − Σc)/2` |
| `compiler/parity_recover.py` | `candidates`, `alternating_field` — the matroid-parity rank certificate (Lovász) |
| `compiler/extract_matching.py` | `matching` — pairs the selected columns |
| `compiler/transport_cuts.py`, `gauge_plan_fit.py` | block-local cuts, `cross_tensor`, `complete_forced` |
| `compiler/low_helper_cache.py`, `helper_coordinates.py`, `padding_completion.py` | the 6-AND low algebra, the borrowed-top-bit helpers, the free padding rows |
| `compiler/emit_plan.py`, `emit_k0.py`, `high_subspace_emitter.py` | the deterministic emitter (plan JSON → circuit) and the loader-0 special schedule |
| `plans/angle_k_*.json` | the 15 frozen plans of the shipped table |

Missing / hardcoded:

1. **`prove_loader_branches.py`** — imported by `compile_loaders.py` (`prove_one`),
   not in the tree. It is the exhaustive branch proof, i.e. the *verification*
   harness, not the planner. (The official verifier can substitute for it.)
2. **The v18 input trees** — `compile_loaders.py` and `planner.py` point at
   `inputs/chem_goal_v18/{deliverables/six_cache_words_combined_v18/compiler,refit}`,
   which are not shipped. All the *imported* modules exist in `compiler/`; only the
   driver's path constants and the payload-relation inputs are absent.
3. **The geometry constants**, hardcoded for the 1,220-row/7-high-bit case:
   * `complete_words`: `(1232, 1220, 75)` grid, `reshape(77, 16, 75)`, loops
     `range(77)` → needs `(800, 791, 75)`, `reshape(50, 16, 75)`, `range(50)`;
   * `emit_plan.emit`: `for h in range(1, 77)` → `range(1, 50)`; the high-bit
     seed `hi = {1 << b: 4 + b for b in range(7)}` → `range(6)` (address bits 4..9
     with 10 selection qubits); the word-qubit map `11 + 8*(i//7) + i%7` →
     `10 + …`; `assert nextq <= 128` stays;
   * `planner.BlockPlan/coord_relations` default `hmax=77` → 50;
   * `k0_windows.json` (the loader-0 window schedule) and `emit_k0.py` reference
     1,232 addresses;
   * `NOUT = 35` and the 4-low/6-high split are **unchanged** (5 words × 7 bits +
     the polarisation bit), so the plan *format* and the algebra are reusable.

That is a mechanical port of ~1 day, not a new planner. The genuinely
table-dependent piece is the **coded-word search** that raises Σcuts (marculera's
§3 codes: bit 0 affine per 16-block, the XOR-of-five words affine at bit 1 and
degree 2 at bit 2). The shipped *planner* consumes a table; it does not choose the
codes. At 791 rows the codes are a free parameter of the new fit, and §2 says the
cut space is 47–72 % larger, so the same code family should score higher.

## 4. Alternatives, priced

| family | cost at 791 rows | verdict |
|---|---|---|
| shipped five-block ESOP (this document) | 171–242/loader (Σcuts 139→280) | the only competitive option |
| `tensorqrom8` (`dfthc_refit/tensorqrom.py`) | **307/loader** (4,601/pass) | 29 % over the 237 budget; its cache is `(L−1−⌊log₂(L−1)⌋) + (H−1−⌊log₂(H−1)⌋) = 11 + 44 = 55` and its term count is much higher than the paired-column algebra |
| `fourqrom` (`three words per circuit` ⇒ 25 circuits, `one lookup step per four rows`) | ≈ 198/lookup step × 25 circuits ⇒ ≈ 5k/pass | worse |
| `build.py --qrom reference` | reference QROM, far worse | not a candidate |

So there is **no published fallback**: the ≤ 237 loader exists only in the
five-block ESOP family, and only through its planner.

## 5. Trigger and next actions (when the pending fit lands)

1. Fit gate first (kernel `qingyu1232/qcc-chem-merge-shrink-full-budget`): need
   quantized e2 ≤ 19.9 mHa (continuous ≤ 16.7) at (5,143,75) or (6,143,64).
2. Then port the planner: `complete_words` grid (800/791/50), `hmax = 50`, the
   emitter's `hi` chain over 6 high bits and the `10 + 8*(…)` word map, and run
   `planner.BlockPlan → greedy → local_search → top_down` with
   `extract_matching.matching` + `parity_recover.alternating_field` on the new
   table. Read off Σcuts; the target is ≥ 149 for T < 14,000 and ≥ 201 for the
   211 projection.
3. Emit with `emit_plan.emit` (the plan JSON format is unchanged), then verify
   with the official 78,080-shot verifier (which replaces the unshipped
   `prove_loader_branches`).
4. Worst case (Σcuts stays at 139): 242/loader, T = 14,149, cost 283.5 M,
   **GM +0.36** — still the largest chemistry step available, so the loader work
   is worth starting even if the projection's 211 is not reached.

## 6. Scope

This is a design study: no fit was run, no circuit was built, nothing was
verified. All cost figures follow the shipped algebra
(`RESULT.md` §4, `planner.py`, `parity_recover.py`) and the official heuristic
`T_heur(5,143,75) = 6,889`, `Q = 427` (from `costs_prepare.SpinFreeData_V1`).
The 791-row table does not exist yet; the pending full-budget fit is the gate.
