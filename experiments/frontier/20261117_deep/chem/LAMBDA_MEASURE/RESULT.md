# RESULT — measured `lambda_eff` and measured `error_2` at (5,136,96)

Date: 2026-11-17 (this session). Chemistry (`dfthcsos`) only.
Local, with the competition's own code: `data/competition/verifiers/dfthcsos/scoreinfra/`
(`reference`, `dfthc_math`, `costs_prepare`) on the packaged FCIDUMP (SHA-256 checked).
No kickmix, no circuit, no simulation, **no official verifier run** (needs `.kmb`).
Every number below is either the verifier's own formula on a real array pair or the
exact full-space `error_2` of a fitted factorization (continuous vectors, not words).
Code: `infra.py fitlib.py repro.py calib.py ladder.py fit_shape.py refine.py control.py
grow.py probe.py merge5.py init_span.py lamopt.py wscan.py greedy.py rerank.py`.

## 0. Verdict

1. **`lambda_eff` was never the risk.** The `E_gap` gate alone forces
   **`Lambda >= 281.52`, i.e. `lambda_eff >= 46.786`, for every legal submission**
   (§1, exact and verified on two real factorizations). The shipped point is
   46.9217 = floor + 0.29 %. The two real factorizations measured here give
   **46.9217** (shipped) and **49.2547** (the official `65,60,60` baseline). At
   (5,136,96) the chemistry leg is 260.29 M (GM **29.339**) at 46.92 and 273.21 M
   (GM **28.869**) at the worst measured λ — **both above the gold line 28.71339**.
   The λ leg cannot kill this shape.
2. **The decisive risk is `error_2`, and it is now measured — with a surprise:
   accuracy is governed by `B` (basis vectors per group), not by `B/C`.**
   Exact fits: `B=143` gives **16.6 / 14.4 / 15.4** mHa at `B/C` 3.25 / 1.62 / 1.12
   and `K` 352 / 704 / 1024; `B=136` gives **17.5** mHa at the target's own
   `(C=96, B/C=1.42)`; `B=129` gives 27.2; `B=96` gives 89; `B=62` gives 280.
   The Q_AXIS `rho(B/C)` law is therefore wrong in both directions (the official
   baseline passes at `B/C = 1`; `B=143` at `B/C=1.12` gives 15.4 mHa). Its
   `e2 = 19.4 mHa` for (5,136,96) is right by accident.
3. **At (5,136,96) proper (R=5) the fit is not yet legal in my hands: 168 mHa at
   8 rounds (and 362 mHa from a merge init).** But that is an **initialization
   limit, not a capacity result**: the *same* `(B=136, C=96)` at `R=8` reaches
   **17.46 mHa** under the same protocol, and the rank-480 truncation of that
   solution is still 17.49 mHa. What the R=5 shape gives up is total basis
   dimension: 5x136 = 680 vs 8x136 = 1088. That reduction, not `B/C`, is the open
   question, and nothing measured excludes it.
4. **NO-GO today, CONDITIONAL GO next**: do not build a loader and do not model
   this shape as legal yet. The next step is one 5-group fit (or the production
   trainer with a continuation in `R`) at (5,136,96) that lands `error_2 <= 20 mHa`;
   the R=8 twin at the same `(B,C)` says 17.5 is reachable at that `(B,C)`.
5. **Zero accuracy slack in the shipped submission**: `error_2 = 0.019999999958`
   and `error_1 = 0.0199999985` (its stored `U` *is* the 8-bit word set — per-row
   best overlap 1.000000). So there is nothing to trade; a candidate must land
   under 20 mHa on its own.

## 1. `lambda_eff` is pinned by the `E_gap` gate

### 1.1 Exact structure (verified on real arrays)

With `w (R,B,C)`, offsets `W (R,C)`, `wB = W + sum_b w`, `a_rc = sum_b|w|`, `s_rc = sum_b w`:

```
lam_h2 = 0.25 sum_rc (a_rc + |wB_rc|)^2
E_gap  = Cg0 + 2*Nneg + 0.5*sum W^2        Cg0 = E_upper - ecore + eta*beta1 = -559.132473
Lambda = tr(h1p) + 2*Nneg + lam_h2
```

| factorization | `sum W^2` | `Nneg` | `E_gap` | `Lambda` | `lambda_eff` |
|---|---:|---:|---:|---:|---:|
| shipped `a73b25d2` (8,143,44) | 1079.846 | 11.562 | 3.9148980002 | 283.144211 | **46.921583** (official 46.9217168) |
| official baseline (65,60,60) | 1081.076 | 11.3 | 3.958022 | 308.448481 | **49.254686** (documented value) |

Both sit just above the `E_gap` floor and both need `sum W^2 ~ 1080`. With `wB`
anti-aligned to `sum_b w` (the shipped structure: `sum W^2 = 4*lam_h2` to 0.06 %),
the floor gives

```
lam_h2 = 0.5 (E_gap - Cg0 - 2 Nneg) >= 281.52 - Nneg
Lambda >= tr + Nneg + 281.52 = sum_{lambda_j>0} lambda_j + 281.52 >= 281.52
```

so **`lambda_eff >= 46.786` always**. The measured slack is 1.62 (shipped) and
26.9 (baseline, whose `w` structure is "dirtier": `lam_h2 - 0.25 sum W^2 = +25.3`).
Range over real factorizations: **46.92 … 49.25**.

### 1.2 What that does to the (5,136,96) cost

`T_h = 7916` and `Q = 430` re-verified locally with `SpinFreeData_V1` (`brot=8, J=5`);
`T = 2L + T_h` uses the shipped loader density `L = 4022*rows/1220` — the one
modelled leg (no loader exists off 1220 rows; a 756-row loader would still be unbuilt).

| `lambda_eff` | chem cost | GM | vs gold 28.71339 |
|---:|---:|---:|---|
| 46.786 (hard floor) | 259.56 M | 29.3658 | +0.652 |
| **46.9217 (Q_AXIS held value)** | **260.29 M** | **29.3386** | **+0.625** |
| 47.50 | 263.50 M | 29.2187 | +0.505 |
| 48.00 | 266.28 M | 29.1169 | +0.404 |
| 49.2547 (worst measured) | 273.21 M | 28.8685 | +0.155 |

## 2. `error_2`: measured, exact, and the real constraint

### 2.1 Protocol and its validation

`f = ||Y Y^T - H||_F^2` in full 2926-dimensional vech space,
`Y[:,r*C+c] = P_r w_rc`, `P_r[:,b] = sqw * vech(u_b u_b^T)`, evaluated as
`||Y^T Y||^2 - 2<Y, H Y> + ||H||^2` (no eigenspace truncation), alternating
L-BFGS on `w` then `u` with analytic gradients.

Pipeline validation: shipped npz → `Lambda` 283.144211, `E_gap` 3.9148980002,
`lambda_eff` 46.921583 (official 46.921717), `error_2` 19.999999958 mHa; official
baseline → `lambda_eff` **49.254686** exactly (documented) and `error_2` 16.133 mHa.

> The earlier `k_bc_axis` kernel optimized an 800-rank truncation. At the shipped
> point that reads **14.58 mHa** where the exact value is **20.00**; the fitted
> solutions carry 13.7 mHa outside the top 800 modes. All numbers here are exact.

### 2.2 The measurements (gate 20 mHa; `B` is the basis size per group)

| shape | R | B | C | K | rows | B/C | floor | **e2** | e2/floor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (8,143,44) shipped shape | 8 | 143 | 44 | 352 | 1220 | 3.25 | 7.361 | **16.55** | 2.25 |
| (8,143,44) *as submitted* | 8 | 143 | 44 | 352 | 1220 | 3.25 | 7.361 | 20.00 | 2.72 |
| (8,143,88) | 8 | 143 | 88 | 704 | 1220 | 1.62 | 0.338 | **14.39** | 43 |
| (8,143,128) | 8 | 143 | 128 | 1024 | 1220 | 1.12 | 0.298 | **15.43** (2 rounds) | 52 |
| (8,136,96) *(target B,C)* | 8 | 136 | 96 | 768 | 1164 | 1.42 | 0.310 | **17.46** | 56 |
| (8,129,44) | 8 | 129 | 44 | 352 | 1108 | 2.93 | 7.361 | 27.2 (↓) | 3.7 |
| (8,96,44) | 8 | 96 | 44 | 352 | 844 | 2.18 | 7.361 | 89.2 (↓) | 12 |
| (8,62,44) | 8 | 62 | 44 | 352 | 572 | 1.41 | 7.361 | 280 (↓) | 38 |
| **(5,136,96) target** | 5 | 136 | 96 | 480 | 756 | 1.42 | 1.630 | **168 (↓)** | 103 |
| (5,136,96) merge init | 5 | 136 | 96 | 480 | 756 | 1.42 | 1.630 | 362 (↓) | 222 |
| baseline (65,60,60) | 65 | 60 | 60 | 3900 | 3976 | 1.00 | 0.00 | 16.13 | — |

`(↓)` = still descending ~2–6 % per round when the wall hit. `K` grows at fixed `B`
*improves* the absolute error (16.6 → 14.4 → 15.4) while `rho = e2/floor` explodes,
so `rho` is the wrong currency.

### 2.3 What the data say about (5,136,96)

* The target's **`(B,C) = (136,96)` and `B/C = 1.42` are legal at `R=8`**:
  `17.46 mHa` after 8 rounds, still descending. So `B/C = 1.42` is *not* the wall
  (that was the Q_AXIS model's claim, and the official baseline at `B/C = 1`
  passing at 16.13 mHa already contradicted it).
* The rank-480 truncation of that solution is **17.49 mHa**, i.e. a legal
  480-column `Y` exists. What (5,136,96) additionally demands is that those 480
  columns live in **5 subspaces of 136 rank-1 projectors** instead of 8: total
  basis dimension 680 instead of 1088.
* My 5-group fits (truncation init, in-span matching pursuit, merge of the R=8
  solution) all stall at 168–362 mHa. The merge init (9239 mHa) is the worst
  start, the plain truncation init (333 mHa) the best; neither is a converged
  statement about the family, both are statements about the init.
* Control that bounds the protocol's transient: at the *shipped* shape, damaging
  14 of 143 basis vectors gives 42.9 mHa after 8 rounds against a true 16.55 — a
  2.6x transient at equal budget. Applying 2.6x to the R=5 fits still leaves
  65–140 mHa, so the group-count reduction is likely doing real damage; but the
  R=8 twin proves the `(B,C)` pair itself is fine.

**Net: (5,136,96) accuracy is unresolved, leaning plausible. The open question is
the group count (680 vs 1088 total basis dims), not `B/C` and not `B`.**

## 3. Cost ranking (exact `T_h/Q`, shipped loader density, λ = 46.9217)

| shape | rows | K | cost M | GM |
|---|---:|---:|---:|---:|
| **(5,136,96)** | 756 | 480 | **260.29** | **29.339** |
| (6,136,96) | 892 | 576 | 297.31 | 28.067 |
| (6,136,72) | 892 | 432 | 266.76 | 29.099 |
| (8,136,96) *(the accuracy-proven twin)* | 1164 | 768 | 370.90 | 26.072 |
| (8,129,44) | 1108 | 352 | 279.29 | 28.658 |
| (8,143,44) shipped | 1220 | 352 | 294.64 | 28.151 |

The whole prize sits in `R=5`: `R=6` already gives +0 / −0.07 GM. So the shape is
worth exactly as much as the R=5 fit question is worth.

## 4. Corrections this session forces on the earlier model

1. **`rho(B/C)` law is invalid.** Accuracy tracks `B` and `K`, not `B/C`:
   `B=143` gives 14–17 mHa for `B/C` 3.25 → 1.12; `B=96` gives 89 mHa at
   `B/C=2.18`; the official baseline passes at `B/C=1`.
2. **No 8-bit rounding tax of 14 mHa.** The shipped's stored vectors *are* its
   8-bit words (overlap 1.000000) and measure 20.0 mHa; the quantization
   contribution is small. The "hypot(e2_cont, 14.08·sqrt(rows/1220))" structure
   double-counted and made the model pessimistic on that axis and optimistic on
   the structural one.
3. **The 800-rank objective used by `k_bc_axis` is not the metric** (14.58 vs
   20.00 at the shipped point). Any earlier "measured" e2 from that kernel is a
   lower bound of unknown slack.
4. **`sum W^2 ~ 1080`** is forced by the `E_gap` floor (both real factorizations
   land at 1079.8 and 1081.1), which is why `Lambda` is pinned at 283–308.

## 5. Scope / next step

* Verified locally: FCIDUMP checksum, `E_upper`, `S`/`beta1`, official metrics on
  two real factorizations, `SpinFreeData_V1` T_h/Q for every shape, exact
  full-space error_2 for every fit. Not run: kickmix, circuits, the verifier, any
  submission.
* Next step (cheap, decisive): one fit at **(5,136,96)** with either (a) the
  production trainer warm-started from the R=8 `(136,96)` solution with a
  group-merge schedule (`R: 8 → 7 → 6 → 5`), or (b) a Gauss-Newton step on the
  Gram residual instead of L-BFGS. Success criterion `error_2 <= 20 mHa`
  (continuous) **before** any loader work; the twin at the same `(B,C)` says the
  target is ~17.5 mHa, so the bar is realistic.
* Do not reuse `lambda_eff = 46.9217` blindly once a legal `(U,w)` exists at the
  new shape: it is a floor + a slack term. Expect 46.9–47.2 if the `w` structure
  is shipped-like, up to 49.25 if it is baseline-like. Either way the shape wins.
