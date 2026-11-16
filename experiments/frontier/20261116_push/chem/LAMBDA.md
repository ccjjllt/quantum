# λ refit at fixed words: closed at 294,762,632.08

Short version for the pipeline agent. Full context in `RESULT3.md` §1.

## Base and gates (measured, packaged verifier metrics)

`bdae290f` (boristown `submission.zip` → `dfthcsos/submission.npz`):

```
lambda_eff 46.92160235   cost 294,762,632.08   (T 14,712, Q 427)
error_1 19.999998 mHa (gate 20)   error_2 19.9999985 mHa (gate 20)
Lambda 283.144439   E_gap 3.9148980015 Ha (floor 3.914898)
```

Margins: **1.5e-6 mHa** on e2, **2e-6 mHa** on e1, **1.5e-9 Ha** on E_gap.

## What the refit can move

At fixed words the verifier reads only `w` and `H2_I` (submitted `U`, `H1_I`,
`Hsym_lower` are ignored / replaced by the fixed shifts). Three levers exist:

1. **Orthogonal rotation of a group's 44 copy columns** — the only *fully free*
   move: it preserves `w wᵀ` (e2), `w H2_Iᵀ` (h1′, e1) and `|H2_I|²` (E_gap)
   exactly and changes only Λ's L1 term `¼Σ(|H2_I|+Σ|w|)²`.
   **Exhausted.** L1 total 270.115287; an independent search (72-angle pair sweeps,
   6 Haar-random restarts per group, 8 groups; `rotate_columns.py`) finds
   **0.0000 %**. A random rotation gives 66.8 vs 33.8 on group 0, so this is a
   real optimum, not a flat function.
2. **Offsets `W = H2_I − Σ_b w`** (352 numbers, exact λ and E_gap gradients in
   `refine.py`'s `Problem`). **Blocked.** A projected gradient with the gates
   enforced accepts no step: every direction that lowers λ leaves E_gap at/below
   the floor or pushes e1 over 20 mHa.
3. **Changing `w` magnitudes/signs.** Blocked by e2 at the gate (1.5e-6 mHa).

The sign-mixing excess in the L1 term is 0.153859; removing it would be worth
−80,644 of cost, but it changes `w wᵀ` and therefore e2, so it is not free.

## Targets

| target | chem cost | λ_eff | Δλ vs bdae | result |
|---|---:|---:|---:|---|
| bdae (public best) | 294,762,632 | 46.9216024 | — | current |
| 28.09487 (rank 92) | ≤ 294,762,367 | ≤ 46.9215443 | −5.8e-5 | **not reachable** |
| 28.09490 | ≤ 294,761,300 | ≤ 46.9213852 | −2.2e-4 | **not reachable** |

Also consistent with the public record: every independent refit of this table
(46.9276 → 46.92174 → 46.921613 → 46.921602) converges to the same point within
1e-5, i.e. the corner is not a search artefact.

## Why the public `refine.py` could not be applied verbatim

`dfthc_refit/refine.py` hardcodes `edges = encode.log_depth_tree()` and regenerates
the one-body rows on that tree (`assemble(...)` -> `onebody.refresh` / `signed_words`).
The shipped frontier table uses a different Givens tree (its `tree_edges` start
`(0,1),(1,3),(3,7),(0,2),(2,6),(7,15)`), so feeding it `angle_words[76:]` + `W`
into `refine.py` decodes the two-body rows on the wrong tree: the run I made
(`qingyu1232/qcc-chem-lambda-refit-fixed-words`) returns e2 = 12,477 mHa and is
**void**. That is not a pipeline bug — it means the public refit is built for
packages that use its own tree (and rebuild their loaders). For a *same-circuits*
refit the two levers below are the only ones, and both were probed on the correct
(shipped) tree.

## Consequence

The silver threshold 28.09487 cannot be crossed with a chemistry λ refit. The
remaining chemistry options are a loader rebuild (2–9 gates, needs the coded-word
ESOP planner that is not published) or the pending full-budget R=5 merge run
(`qingyu1232/qcc-chem-merge-shrink-full-budget`, `RESULT3.md` §2.3).
