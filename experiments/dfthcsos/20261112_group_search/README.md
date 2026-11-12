# dfthcsos group selection / initialization at (8,143,44), 8-bit — no-go (2026-11-12)

Target: a new DF-THC **group selection or initialization** that cuts the chemistry cost
from 297,237,044.95 (`5d5007a75784`, λeff 46.907378, T 14,840, Q 427) by ≥2.5% (≤289.8M),
i.e. λeff ≤ 45.734 at the same T/Q (≥1.76% / <292M needs λeff ≤ 46.081). Everything below is at
the same shape (R,B,C) = (8,143,44), 8-bit angles, same tree, and was screened on the official
metrics.

**Verdict: no-go.** No strategy improved λeff at all; the closest competitor to the table is a 2%
weight jitter + refit at 47.004 (+0.21%), and the best feasible refit of the table itself lands on
its own value to 0.001%. The table is not merely a good local optimum: it sits exactly on the
(Λ, error) frontier our refit code can reach, and the binding restriction is the 8×143×44
structure itself, not the grouping.

## What the group selection actually is

The model (from `dfthcsos.verify.evaluate_words`):

    A = Σ_rc x_rc x_rc^T,  x_rc = Σ_b w_rbc p_b,  p_b = vec(u_b u_b^T),
    error_2 = ||A - T||_F,  T = tei + (S⊗I + I⊗S)/2.

So A = P M P^T with M = Σ_rc w_rc w_rc^T **block diagonal by group, rank ≤ C per block**, and
Λ = |λ(h1')|₁ + ¼ Σ_rc (Σ_b|w_rbc| + |W_rc + Σ_b w_rbc|)².

The free variables are therefore (a) the 1144 directions u_b, and (b) which 143 of them form each
group. Because the 1144 rows are distinct, the grouping is exactly a **partition of the rows**, so
regrouping is free: same directions, same 8-bit words up to row order, same T/Q. This is the
cleanest possible test of "group selection", and it is what most of the work below measures.

Current table: the B=143 rows/group come from the `dfthc_refit` lineage at this shape (its README
documents the compact seed: pivoted-Cholesky leaves of the shifted Hamiltonian, clustered by
orbital profile), trained at (8,143,45), rounded to 8 bits with a coded bit 0 and refit
(`refined_845`, λeff 48.137), then taken to C=44 and refit to 46.907. The **grouping** — which 143
rows form each group — was never re-derived for the final shape; it is inherited from the seed's
clustering. That is the gap this experiment set out to test.

## Baseline and the reduction (numbers to beat)

Official 8-bit metrics of `submission.npz` (verified with `evaluate_words`):
error_1 = **19.99998 mHa**, error_2 = **19.99998 mHa**, Λ = **282.9740**, E_gap = **3.91489802**
(2e-8 above the strict floor), λeff = **46.907383278**.
`heuristic_costs(76,8,143,44,8)` = T 6,662, persistent 84, temp 303 → T_total = 2·4,097 + 6,662 =
**14,856** local, Q = 84 + 40 + max(303, angles_temp) = **427**; cost 46.907383·14,856·427 =
297,557,548.71 locally, and 297,237,077 with the public artifact's T=14,840 (the public receipt says
297,237,044.95, i.e. λeff 46.907378 — a 1e-7 relative difference in the npz's last digits).

Structural measurements (exact, `spectrum.py`, `step6`, `step9`):

| quantity | value |
|---|---|
| T trace / ‖T‖_F / top eigenvalue | 53.297 / 12.184 / 7.24 |
| best rank-352 (R·C) tail of T | 7.36 mHa |
| best rank-1144 tail of T | 0.298 mHa |
| T outside span{p_b} (current 1144 directions) | **12.136 mHa** |
| best rank-352 fit inside the span | 6.93 mHa |
| ceiling at fixed directions (any weights) | **13.977 mHa** |
| ideal M* = C⁻¹A*C⁻ᵀ: norm share inside the blocks | 0.970 |
| ideal M*: block-diagonal part alone | **1,529 mHa** (rank-44 cut 1,542); every 143×143 block rank 143 |

The last two rows are the key structural fact: almost all of the ideal coefficient matrix's mass is
inside the blocks, but each block is full rank 143 and the cancellation is so delicate that the
block part alone misses by 1.5 Ha. The binding restriction is the 8×143×44 structure — 352 rank-1
terms each confined to a 143-dimensional subspace — not the grouping.

## Strategies tried (all at the same shape, 8-bit)

Code lives in this directory: `gs_lib.py` (reduction, exact objective, AL refit,
error-at-fixed-Λ probe) plus one script per row; their outputs go to
`artifacts/20261112_group_search/`. The refit used here is the `refit_al.py` scheme
(augmented Lagrangian on log λeff with the exact gradients of `refit_weights.WeightProblem`),
reproducing the pipeline's own logs on the same table.

| # | strategy | result |
|---|---|---|
| 1 | **harder weight refit** (control): AL refit at error target 19.95 / 19.99 / 19.999 / 19.5 / 19.0 / 18.0 | 46.9254 (e2 19.980) / 46.9044 (20.0026) / 46.8986 (20.017, infeasible) / 46.9679 / 47.3934 / 47.7395 → **no feasible gain**; the table's 46.9074 at e2 19.99998 sits on the frontier |
| 2 | **random re-init** of w, two seeds, AL refit | 68.37 / 70.63 (+46%) |
| 3 | **jitter + refit**: w×(1+N(0,0.02)) and ×(1+N(0,0.1)) | 47.004 (+0.21%) / 47.264 (+0.76%) — monotone in jitter |
| 4 | **block-optimal init**: each group = its own best rank-44 PSD fit of T, W re-solved to reproduce h1' | e2 45.5 Ha; the AL cannot recover (E_gap −126) — fitting each block to T double counts, because the 8 spans overlap (Σ block traces ≫ trace T) |
| 5 | **joint BCD init** (block-coordinate, residual-compressed, top-44 eigenpairs) | 790 mHa after 8 sweeps and still descending — slow because the blocks share one span; far worse than the trained M |
| 6 | **random regrouping** (3 permutations) + block init + AL | e2 1,610 / 1,657 / 1,613 mHa |
| 7 | **co-occurrence partition**: spectral clustering of max(Q0,0) + pairwise-swap local search (maximises within-block mass of the target) + block init + AL | 3,186 mHa. The proxy says it is better (within-block mass 0.333 vs the current partition's 0.203) and the refit says it is 160× worse — the Q0-mass proxy is misleading, the G-metric coupling is what matters |
| 8 | **local exchange on the trained table**: swap k direction pairs between groups, carry the weights, AL refit | k=1 48.099 (+2.6%), 2 → 49.232, 5 → 51.351, 10 → 56.858, 40 → 78.310 |
| 9 | **greedy residual direction fill**: replace the k weakest rows by the top eigenvectors of T outside the current span | outside span 12.136 → 22.80 (k=32) / 44.89 (k=128) mHa; error floor at Λ≈290 → 48.6 / 129.6 mHa. The span is *tight*: every row carries T-mass |
| 10 | **eigen-leaf direction pool** (`df_init`-style): top-1144 leaves v_ki v_ki^T by σ_k λ_ki², and diversity-capped variants (≤2/4/8/16 leaves per eigenvector) | outside span **190.7 / 362–1236 mHa** vs the current 12.14. Leaf sets span "diagonal" subspaces and cover T terribly |

Rows 4–7 build a *new* weight matrix, so they also carry an initialisation handicap: the eight group
spans overlap heavily, so fitting each group to T independently double counts (Σ block traces ≈ 293
against trace T = 53.3) and the AL refit cannot repair it (rows 4, 5). Row 8 is the clean partition
test because it starts from the trained weights and only moves directions. The two together say
that the trained partition cannot be improved by local exchange, and that every constructive
re-initialisation we tried lands far outside the trained basin — consistent with the pipeline's own
result (`CLOSED_RESEARCH.md` F) that training from other seeds at these shapes lands at 30–37 mHa.

## Why this closes the lane

1. **The weights are already optimal.** The refit's own frontier, measured at the two feasible
   targets, is 46.9254 at e2 19.9802 and 46.9044 at e2 20.0026; interpolated to the table's
   e2 = 19.99998 that is 46.9069, i.e. the table's 46.9074 is on the frontier to 0.001%. Lower
   targets cannot be reached (the best error our probe could find at Λ ≤ 287 and even at Λ ≤ 1000
   is 19.808 mHa, 800 L-BFGS iterations from the trained w; 23.5 from 3w; every other start was
   worse), and every attempt to reduce the error costs Λ and makes λeff worse (rows 1, 3).
2. **The grouping is fully exploited.** One swap of two directions between groups costs +2.6% and
   the refit cannot recover it: each group's 143 vectors and 44 copies form one finely balanced
   cancellation, exactly as the "structural deletion" results in `CLOSED_RESEARCH.md` found for
   dropping rows.
3. **The directions are tight, not redundant.** Removing the 32 weakest rows (weights ~1e-5)
   raises the outside-span from 12.14 to 22.80 mHa, so there is no dead weight to replace; the
   principled leaf-based pools are 1–2 orders of magnitude worse.
4. **The 13.98 mHa "ceiling" is not reachable.** It needs the coefficient matrix of the ideal
   rank-352 fit: 97% of its norm already sits in the blocks, yet keeping only the block part gives
   1,529 mHa (and 1,542 after the rank-44 cut) — the fit is a cancellation between terms of size
   ‖T‖² ≈ 148 against a residual of 4e-4, so a 3% coefficient perturbation costs ~1,500 mHa. That
   cancellation is also why one swapped direction costs +2.6% and 2% weight jitter +0.21%: the
   trained M is far more special than any construction we could reach.

What would be needed to go below 292M is a different structure (shape, row count, or word table),
not a different grouping: at fixed (8,143,44) the reachable λeff is 46.90.

## Verification scope

- All metrics: official `dfthcsos.verify.evaluate_words` on the stored word table (baseline) or the
  verifier's exact λeff/E_gap/Λ formula on the refit weights (strategies), which
  `refit_weights.py` asserts matches the verifier to 1e-7 on this table.
- **No 78,080-shot verifier run**: no candidate reached λeff < 46.5 or cost < 292M, the bar set for
  rebuilding the 15 ANGLE circuits with the Maoxin v22 loader. Nothing here is a submittable
  candidate; the current table stands.

## Files

- `gs_lib.py` — reduction A = P M P^T, exact error/Λ/E_gap, AL refit, error-at-fixed-Λ probe,
  BCD/block inits, W re-solve.
- `analyze.py`, `spectrum.py` — current-table diagnostics and T's spectrum.
- `step1_baseline.py` … `step9_inits.py` — the rows of the table above (numbers in
  `artifacts/20261112_group_search/step*.json`).
- `artifacts/20261112_group_search/` — `part_*.npz`, `swap*.npz`, `fill*.npz`, `idealM_*.npz`,
  `refit_target*.npz` (best weights per strategy), `step*.json`.

Re-run any row with `uv run python experiments/dfthcsos/20261112_group_search/<script>.py`;
`gs_lib` sets `DFTHC_DATA` and the `sys.path` entries itself. Rough cost: `step1` 90 s (the
reduction + 4 refits), `step2` 3 min, `step8` 12 min, the rest under 1 min each (the T
eigendecomposition is cached in `T_eigh.npz`, regenerated if absent).
