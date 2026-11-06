# Lower-CCX equivalents of the Syed V9 DQI arithmetic kernels

Date: 2026-11-06. Worktree: `.worktree/dqi`, branch `codex/dqi-research`.
Baseline: Syed V9 DQI, 892 qubits, `meanT ≈ 395395`.
Scope: value-map equivalence of the five extracted quadratic-arithmetic windows
(`inverse12 norm`, `inverse12 products`, `inverse24 norm`, `inverse24 products`,
`multiply v`).  No official verifier was run, the official KMB was not modified,
and nothing was committed or pushed.

## 1. Headline result

**No strictly equivalent lower-CCX circuit was produced for any kernel in the
available time.** The baseline windows remain the best known implementations.
What was obtained instead is a rigorous lower bound, exact structural evidence,
and a full-circuit arithmetic ceiling that together explain why this direction
is hard and how far it could possibly go.

- Every extracted window is exactly a *value shear*
  `out_j ^= f_j(inputs)` with `f_j` of degree ≤ 2, inputs restored, and no
  dependence on the target register's initial value. This was proved
  symbolically for all inputs (exact ANF), not sampled.
- For `inverse12 norm` and `inverse12 products` the baseline windows were
  additionally verified by exhaustive classical simulation: `2^12 = 4096` and
  `2^18 = 262144` inputs respectively, **0 mismatches** in both cases.
- A circuit-independent lower bound holds: for any `X/CX/CCX/SWAP` circuit with
  the same input/output contract (ancillas allowed), the number of CCX is at
  least the GF(2) rank of the output quadratic forms. The bounds are
  `10, 12, 21, 24, 24` for the five kernels; for `inverse12 norm` the stronger
  bound `k ≥ 11` follows from the absence of any rank-1 matrix in `W`.
- Even if **all five** kernels simultaneously attained their strongest proven
  lower bounds, the full circuit would save **4,762 T**, i.e. 1.204 % of
  `meanT` (DQI cost −1.20 %, approximately GM +0.40 %). Using only the weaker
  span-rank bound gives the looser ceiling 4,925 T (1.246 % of `meanT`). Both
  are **below the 5,000 T "interesting" scale**. The complete named-kernel
  budget is 12,624 T (3.19 % of `meanT`, GM +1.07 %); the five-kernel programme
  alone cannot reach 5,000 T by local replacement.

Best equivalent circuit found per kernel (all unchanged from the baseline):

| kernel | CCX before | best CCX found | other gates (before = after) | verification scope |
|---|---:|---:|---|---|
| inverse12 norm | 15 | **15** | 202 CX | exhaustive, 4096/4096 inputs |
| inverse12 products | 25 | **25** | 835 CX | exhaustive, 262144/262144 inputs |
| inverse24 norm | 42 | **42** | 1942 CX (+ affine CNOTs) | exact symbolic ANF, all inputs |
| inverse24 products | 70 | **70** | 11560 CX (+ affine CNOTs) | exact symbolic ANF, all inputs |
| multiply v | 99 | **99** | 6294 CX | exact symbolic ANF, all inputs |

"Exact symbolic ANF, all inputs" means the extracted polynomial was propagated
symbolically over GF(2), so the equality holds for every assignment; it is not
a sample. It proves the baseline window's function, not a new circuit.

The strongest concrete obstruction is for `inverse12 norm`:

- `k = 10` is impossible because the 10-dimensional output span `W` contains
  **no non-zero rank-1 matrix** (exact enumeration of all 3969 rank-1
  `u v^T`, `u,v ∈ GF(2)^6 \ {0}`). Hence any decomposition needs `k ≥ 11`.
- The 15 baseline generators are all *symmetric* products
  `(u·x)(u·y)` (same 6-bit mask on both halves). Under that restriction the
  minimum is at least 14: the 63 matrices `u u^T` have 63 distinct classes in
  the 11-dimensional quotient `Sym_6/W`, and an exact search over all 1-, 2-
  and 3-dimensional quotient subspaces found no 11-, 12- or 13-term symmetric
  decomposition. Thus `k_sym ≤ 13` is excluded; `k_sym = 14` was not excluded.
- A SAT query for `k = 14` on the full 10-output tensor did **not** finish
  within the time-box. It is an inconclusive search, **not** an UNSAT proof.
- Independently of tensor rank, a naive clean-host fan-out construction cannot
  realise 15 CCX on 10 target wires: the 15 baseline generators have 15
  *distinct* output-support sets. The baseline instead uses dirty hosts and
  cancels the linear leakage through its particular schedule (verified by the
  exhaustive 4096-input simulation).

## 2. Contract and exact function extraction

The extracted windows contain only `X`, `CX`, `CCX`, `SWAP` (and no `INFO_TAG`
gates). For such a window every wire holds a polynomial over GF(2) in the
initial values of all wires. The extraction (`kernel_anf.py`) propagates the
full ANF of every wire with symmetric-difference monomial sets, then forms the
delta `final XOR initial`.

Result for all five windows:

- every changed wire's delta depends **only** on wires that are unchanged by
  the window (the independent inputs);
- every delta has degree exactly 2 (homogeneous quadratic, plus affine terms
  for the two `inverse24` kernels);
- the inputs are restored exactly;
- therefore each window implements `out_j ^= f_j(inputs)` for an arbitrary
  initial target value, and the homogeneous quadratic part is a well-defined
  bilinear/quadratic tensor.

The target registers are also clean at the first call: `wire_first_touch.py`
shows that `q861..q870` are first touched *inside* the first `inverse12 norm`
window (first touch is `CX q861 q862`; first target is
`CCX q840 q846 q861`), so they are `|0>` at that entry. This does not by itself
prove that every one of the 163 call sites enters with `|0>`, which matters for
any clean-host construction (see §5).

Per-kernel function shape (from `structure.json` and the re-extraction):

| kernel | wires | inputs | changed outputs | CCX | CX | affine delta terms | quadratic terms |
|---|---:|---:|---:|---:|---:|---:|---:|
| inverse12 norm | 22 | 12 | 10 | 15 | 202 | 0 | 104 |
| inverse12 products | 30 | 18 | 12 | 25 | 835 | 0 | 340 |
| inverse12 scalar | 18 | — | — | 18 | 437 (+16 SWAP, 6 R, 6 HMR, 81 CZ, 21 Z, 1 X) | — | — |
| inverse24 norm | 45 | 24 | 21 | 42 | 1942 | 140 | 1244 |
| inverse24 products | 60 | 36 | 24 | 70 | 11560 | 139 | 2957 |
| multiply v | 72 | 48 | 24 | 99 | 6294 | 0 | 1419 |

`inverse12 scalar` contains `R/HMR/CZ/Z` and was not treated as a pure value
map; it is excluded from the replacement analysis.

## 3. Rigorous lower bound: CCX ≥ rank of the output quadratic forms

Let the circuit use any number of wires, each initially a constant (`|0>`/`|1>`)
or the initial value of an input/target wire. All gates are `X`, `CX`, `CCX`,
`SWAP`; phase gates, if any, do not change values and can be dropped for this
argument. For a wire `w` let `P_w ∈ GF(2)[variables]` be its polynomial and let
`p_w` be the homogeneous degree-2 part. Let `S` be the span of all `p_w` over
all wires at all times.

Initially every `p_w = 0`. For a CCX with controls `a,b` and target `c`:

```
P_c  <-  P_c + P_a P_b
deg2(P_a P_b) = p_a * (P_b)_0 + (P_a)_0 * p_b + (P_a)_1 * (P_b)_1
```

where `(·)_0` is the constant part and `(·)_1` the homogeneous degree-1 part.
The first two terms are copies of `p_a` and `p_b`, already in `S`. The third is
a product of two linear forms: a single decomposable quadratic form. Hence one
CCX increases `dim S` by at most one, and `dim S ≤ #CCX` at all times.

The final output polynomials are `z_j + f_j`, whose degree-2 parts are the
output forms `f_j`. They lie in `S`. If `r` is the GF(2) rank of the output
quadratic forms, then `#CCX ≥ r`. This is independent of ancilla count and of
the gate order. It is a lower bound on *any* value-equivalent circuit, not just
on fan-out constructions.

Exact ranks computed by Gaussian elimination on the ANF coefficient vectors:

| kernel | inputs | outputs | ambient quadratic dim | output span rank `r` | proven lower bound | baseline CCX | max local saving |
|---|---:|---:|---:|---:|---:|---:|---:|
| inverse12 norm | 12 | 10 | 66 | 10 | **11** (§4.1) | 15 | 4/call |
| inverse12 products | 18 | 12 | 153 | 12 | **12** | 25 | 13/call |
| inverse24 norm | 24 | 21 | 276 | 21 | **21** | 42 | 21/call |
| inverse24 products | 36 | 24 | 630 | 24 | **24** | 70 | 46/call |
| multiply v | 48 | 24 | 1176 | 24 | **24** | 99 | 75/call |

A second, per-output bound is useful for scheduling. If
`q = Σ_{t∈S_j} l_t m_t` is a sum of products of linear forms, its polar
(alternating) matrix has rank at most `2|S_j|`. For the bipartite kernels the
polar matrix is `[[0,M],[M^T,0]]`, so `|S_j| ≥ rank(M_j)`. The computed
per-output ranks `rank(M_j)` are:

- `inverse12 norm` (bipartite): `rank(M_j) = 6,6,6,6,6,6,4,6,5,3` (sum 54, baseline uses 58 generator-output incidences);
- `inverse12 products` (non-bipartite): every polar rank is 12, so every output needs `|S_j| ≥ 6` products;
- `inverse24 norm` (non-bipartite): polar ranks are mostly 24, with 20,20,22,22,16,16,22 on some outputs, so `|S_j| ≥ 12` (down to 8 for the rank-16 slices);
- `inverse24 products` (non-bipartite): every polar rank is 24, so `|S_j| ≥ 12`;
- `multiply v` (bipartite): every output slice is full rank 24 (polar rank 48), so `|S_j| ≥ 24`.

For `multiply v` this says every one of the 24 outputs needs at least 24
product terms contributing to it. The baseline uses 99 products in total; the
gap is real but the per-output bound only gives `k ≥ 24`.

## 4. Per-kernel findings

### 4.1 inverse12 norm (15 CCX, 163 calls)

Structure:

- 12 inputs `q840..q851`, 10 outputs `q861..q870`, bipartite `6+6`
  (`q840..q845` × `q846..q851`), homogeneous quadratic with **no affine
  terms**; span rank 10.
- The first six outputs `q861..q866` are linearly independent and span exactly
  the same 6-dimensional space as the six slices of multiplication in `GF(2^6)`
  with modulus `t^6 + t + 1` in the polynomial basis (all six contained; the
  other four outputs are not in that span). Up to an invertible output change
  of basis the 6-output sub-tensor is therefore `GF(2^6)` multiplication. This
  identifies a large part of the tensor, but does not by itself give a smaller
  decomposition.
- All 15 baseline CCX have controls `(u·x)` and `(u·y)` with the *same* 6-bit
  mask `u`, i.e. every generator is a symmetric rank-1 matrix `u u^T`,
  `u ∈ {0,1}^6 \ {0}`. The 15 generators are linearly independent and have
  58 generator-output incidences; their 15 output-support sets are all
  distinct.

Obstruction evidence:

1. `W` contains no non-zero rank-1 matrix. Exact enumeration of all
   `63 × 63 = 3969` matrices `u v^T` (and membership test in the 10-dimensional
   `W`) gives zero hits. Therefore a 10-term decomposition would have to be a
   rank-1 basis of `W`, which is impossible: **`k ≥ 11`**.
2. Under the symmetric restriction `u u^T`, all 63 pool matrices have distinct
   classes in the 11-dimensional quotient `Sym_6/W`. An exact subspace search
   for `d = 1,2,3` (i.e. `k = 11,12,13`) found no solution: the pool vectors in
   any such quotient subspace never fill the 10+d-dimensional preimage. Hence
   **no symmetric decomposition with `k ≤ 13`**. The first possible symmetric
   improvement is `k = 14`, which would require a 4-dimensional quotient
   subspace containing at least 14 of the 63 classes and filling its preimage;
   this was not found and was not exhaustively searched.
3. A SAT query for a general (not necessarily symmetric) `k = 14`
   decomposition was encoded (`cp_sat.py`, `run_cp2.py`) with 3-way product
   auxiliaries and XOR chains. It did not return within the time-box (the
   solver's C call did not honour the Python alarm and had to be killed). This
   is **inconclusive**, not an UNSAT certificate.
4. Scheduling obstruction: a clean-host fan-out circuit computes a product into
   a target wire known to be `|0>`, then copies it to the other outputs with
   free CNOTs. With 10 target wires and 15 distinct output-support sets this
   needs 15 clean host slots; only 10 exist. The baseline instead reuses dirty
   hosts (e.g. `q862` hosts several products) and cancels the induced linear
   leakage through its schedule. Any new decomposition must come with such a
   schedule, or with a verified-all-call-sites clean-target guarantee, to be
   installable at its nominal CCX count.

Best equivalent circuit found: the baseline window itself, 15 CCX / 202 CX,
verified exhaustively (all 4096 input assignments, targets initialised to 0,
inputs restored, outputs equal to the exact ANF) with **0 mismatches**.
No 14-CCX circuit was produced.

### 4.2 multiply v (99 CCX, 6 calls)

- 48 inputs (`q48..q71` × `q72..q95`, 24+24), 24 outputs
  (`q843..q860`, `q877..q882`), bipartite, homogeneous quadratic, no affine
  terms; span rank 24.
- Every output slice `M_j` is a full-rank `24 × 24` matrix (polar rank 48), so
  every output needs at least 24 product terms.
- The 99 baseline CCX generators are linearly independent (rank 99); each
  product is computed once and fanned out.
- The tensor is a natural candidate for a fast bilinear algorithm (24-bit
  convolution / multiplication-like structure), which could plausibly reach
  roughly 47 terms for a truncated 24-bit convolution (Winograd/Toom-Cook
  rank `2n-1` over large fields), but a decomposition over **GF(2) with binary
  linear forms only** was not constructed. The support pattern is not a single
  anti-diagonal in the current basis, so a linear change of basis would be
  needed to expose a Toeplitz/convolution tensor; this was not completed.
- Bound interval: `24 ≤ k ≤ 99`. Weighted maximum saving `(99-24) × 6 = 450 T`.
  No improvement was produced.

### 4.3 inverse12 products (25 CCX, 163 calls)

- 18 inputs, 12 outputs, non-bipartite in the current basis; span rank 12; every
  output has polar rank 12, so each output needs at least 6 products; baseline 25.
- Bound interval: `12 ≤ k ≤ 25`. Weighted maximum saving
  `(25-12) × 163 = 2119 T`. This is the largest single-kernel ceiling of the
  five, but no decomposition was produced. The natural next step is a linear
  change of basis that makes the quadratic graph bipartite (then the 12-output
  bipartite machinery applies), or a CP search with shared products.

### 4.4 inverse24 norm (42 CCX, 23 calls)

- 24 inputs, 21 outputs, span rank 21; per-output lower bounds mostly 12, some
  10/11/8; baseline 42.
- Bound interval: `21 ≤ k ≤ 42`. Weighted maximum saving `(42-21) × 23 = 483 T`.
  No improvement was produced.

### 4.5 inverse24 products (70 CCX, 23 calls)

- 36 inputs, 24 outputs, span rank 24; every output has polar rank 24, so each
  output needs at least 12 products; baseline 70.
- Bound interval: `24 ≤ k ≤ 70`. Weighted maximum saving
  `(70-24) × 23 = 1058 T`. No improvement was produced.

## 5. Full-circuit arithmetic (call counts shown explicitly)

The counts below are the values supplied with the task / recorded in the
`20261106_high_return_research` census; I did not re-count them in this
time-box. `T` means one executed Toffoli-like gate; `meanT = 395395`.

| kernel | CCX/call | calls | T now | proven LB | T at LB | max saving |
|---|---:|---:|---:|---:|---:|---:|
| inverse12 norm | 15 | 163 | 2,445 | 11 | 1,793 | **652** |
| inverse12 products | 25 | 163 | 4,075 | 12 | 1,956 | **2,119** |
| inverse12 scalar | 18 | 163 | 2,934 | — | — | — (not analysed) |
| inverse24 norm | 42 | 23 | 966 | 21 | 483 | **483** |
| inverse24 products | 70 | 23 | 1,610 | 24 | 552 | **1,058** |
| multiply v | 99 | 6 | 594 | 24 | 144 | **450** |
| **total, five analysed** | | | **9,690** | | **4,928** | **4,762** |
| **total, all named incl. scalar** | | | **12,624** | | | |

Using only the span-rank bound (10 instead of the stronger 11 for
`inverse12 norm`) the five-kernel saving ceiling is 4,925 T; the proven-bound
figure 4,762 T is the tighter statement.

Conversion (using the repository's `1 % DQI cost ≈ 0.336 % GM` and
`ΔmeanT / 395395` as the cost fraction):

- 4,762 T = **1.2044 %** of `meanT` → DQI −1.20 %, approximately **GM +0.405 %**.
- 4,925 T (looser span-rank-only ceiling) = 1.2456 % → GM +0.418 %.
- 12,624 T (eliminate every named-kernel CCX) = **3.193 %** → **GM +1.073 %**.
- 1 CCX per `inverse12 products` call = 163 T = 0.0412 % → GM +0.014 %.
- 8 CCX per call = 1,304 T = 0.3298 % → GM +0.111 % (consistent with the
  task's "~GM +0.1 %").

Consequence: **even the unattainable best case of the five analysed kernels is
4,762 T (4,925 T under the weaker span-rank-only bound), below the 5,000 T
threshold.** Reaching 5,000 T from these kernels is impossible by the proven
span-rank bound. To exceed it one must also address `inverse12 scalar`
(2,934 T total, not a pure value map), unlabelled arithmetic windows, uncompute
copies, or reduce `Q`/`R`; none of those is a local kernel replacement.

## 6. What would be needed to break the obstruction

- `inverse12 norm`: find an explicit 14-term (or 11–13-term) CP decomposition
  `M_j = Σ_t A_{j,t} u_t v_t^T` over GF(2). The SAT encoding is in
  `cp_sat.py`/`run_cp2.py`; the `k = 14` run needs a better symmetry break, a
  native XOR solver (CryptoMiniSat) or a dedicated tensor-rank search. Even a
  14-term decomposition must come with a 10-wire dirty-host schedule (or a
  proof that all 163 call sites enter with clean targets) to be installable at
  14 CCX. A 15-term alternative is not a gain.
- `multiply v`: identify the underlying bilinear map (test a linear basis
  change against 24-bit truncated convolution / `GF(2^24)` multiplication), then
  use a binary-linear-form Toom-Cook/Winograd decomposition. A 47-term
  decomposition would save `52 × 6 = 312 T`; the rank bound 24 would save 450 T.
- `inverse12 products`: find a linear change of basis making the quadratic
  graph bipartite; then the 12-output bipartite rank-1 span search applies
  (lower bound 12, baseline 25, ceiling 2,119 T). This is the largest single
  kernel ceiling and the most valuable next experiment.
- `inverse24 norm/products`: the same basis-change/CP approach; ceilings 483 T
  and 1,058 T respectively.

None of these can lift the five-kernel total above 4,762 T (4,925 T under the
weaker span-rank-only bound); a ≥5,000 T result requires a different budget line
(scalar, unlabelled windows, or width).

## 7. Verification scope, commands, artifacts

Verification actually performed:

- exact symbolic ANF of every wire for all five windows (`kernel_anf.py`),
  including degree, affine terms, input-restoration and target-initial-value
  independence — **all inputs, symbolic, not sampled**;
- exact classical simulation of the `inverse12 norm` window on all
  `2^12 = 4096` input assignments: **0 mismatches**
  (`verify_inverse12_norm.log`);
- exact classical simulation of the `inverse12 products` window on all
  `2^18 = 262144` input assignments: **0 mismatches**
  (`verify_inverse12_products.log`);
- exact rank and rank-1/subspace enumerations for `inverse12 norm`
  (`rank1_span.py`, `symmetric_span.py`);
- SAT encoding for `k = 14` (inconclusive; no UNSAT claim).

Not performed: official verifier, full-circuit KMB replacement, Kaggle
submission, commit/push, any change to `data/competition/`.

Commands (run from the worktree root, `.venv/bin/python` is Python 3.12 with
native `kickmix`):

```sh
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/kernel_anf.py \
    analyze artifacts/20261106_high_return_research/kernels/inverse12_norm.kmx
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/export_kernel.py \
    artifacts/20261106_high_return_research/kernels/inverse12_norm.kmx \
    artifacts/20261106_phase_recovery/subagents/inverse12_norm.json
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/rank1_span.py \
    artifacts/20261106_phase_recovery/subagents/inverse12_norm.json
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/symmetric_span.py \
    artifacts/20261106_phase_recovery/subagents/inverse12_norm.json
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/verify_window.py \
    artifacts/20261106_high_return_research/kernels/inverse12_norm.kmx \
    artifacts/20261106_phase_recovery/subagents/inverse12_norm.json
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/ccx_profile.py \
    artifacts/20261106_high_return_research/kernels/inverse12_products.kmx
.venv/bin/python experiments/dqi/20261106_phase_recovery/subagents/wire_first_touch.py \
    artifacts/20261106_syed_v9/release/dqi.kmb 861 862 863 864 865 866 867 868 869 870
# SAT attempt (inconclusive; needs an external kill or a native XOR solver):
uv run --no-project --with python-sat python \
    experiments/dqi/20261106_phase_recovery/subagents/run_cp2.py \
    artifacts/20261106_phase_recovery/subagents/inverse12_norm.json 14 60
```

Scripts (all under `experiments/dqi/20261106_phase_recovery/subagents/`):

- `kernel_anf.py` — exact ANF propagation, quadratic extraction, span ranks;
- `export_kernel.py` — JSON export of inputs/outputs/affine/quadratic terms;
- `rank1_span.py` — bipartite rank-1 membership and rank-1 basis search;
- `symmetric_span.py` — exact symmetric `u u^T` minimum search via the
  `Sym_6/W` quotient;
- `ccx_profile.py` — per-CCX control-degree and affine-form listing;
- `window_context.py` — tag-aware context dump around a window;
- `wire_first_touch.py` — first write/target of selected wires in the full KMB;
- `verify_window.py` — exhaustive value-map checker for small kernels;
- `cp_sat.py`, `run_cp2.py` — CP/SAT encodings (the `run_cp2.py` path is the
  usable one; the `k = 14` run is inconclusive).

Generated data under `artifacts/20261106_phase_recovery/subagents/`:

- `inverse12_norm.json`, `inverse12_products.json`, `inverse24_norm.json`,
  `inverse24_products.json`, `multiply_v.json` — exact exports;
- `inverse12_norm_mult6.json` — the 6-output multiplication sub-tensor;
- `savings.json` — the full-circuit table;
- `verify_inverse12_norm.log`, `anf_inverse12_norm.log`,
  `verify_inverse12_products.log` — run logs.

No generated circuit file is claimed as an improvement; the only verified
equivalent circuits in this report are the baseline `inverse12 norm` and
`inverse12 products` windows, whose exact functions and all-inputs behaviour are
documented above (the other three are verified symbolically at the ANF level,
not by exhaustive simulation).
