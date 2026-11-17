# RESULT2 — Λ minimisation at the shipped shape (8,143,44,brot=8)

Date: 2026-11-17. Chemistry only. Local work: closed-form arithmetic on the shipped
npz + the verifier's own formulas. **No integrals read, no simulation, no verifier
run locally.** Eigen / e2 / e1 work is on Kaggle CPU (kernel refs in §6).

Baseline: shipped `(8,143,44,brot=8)`, v13 member sha `93326853…b9c9e`
(T 14,706, Q 427, λ_eff 46.921716818, cost **294,643,137.73**, GM 28.15083).

## 0. Verdict first

1. The requested ratio is **88.7**, and it is an **artefact** of the stated bound —
   not evidence of a 20× Λ win (§1). It cannot be used either way.
2. The real structure: **52 % of `lam_h2` is the `|W|` cross term**, and `W` does not
   enter `error_2` at all. Moving the same `ΣW²` onto the smallest-L1 cells gives
   `lam_h2` **270.115 → 160.638** at unchanged `ΣW²` (§2). If `lam_h1` and `E_gap`
   survive, that is **Λ 173.67 → λ_eff 36.667 (−21.9 %) → chem 230.2 M → GM 30.56
   (+2.41)**. This is the only single-leg gold-crossing lever found in this round.
3. The whole question is therefore one 352-dim problem (§3), and its two binding
   gates are `E_gap` (which `ΣW²` must hold at the floor) and `error_1` (the 76
   one-body rows must be re-encodable at 8 bits for the new `h1_prime`). Kernel
   `qingyu1232/qcc-chem-lambda-offset-min` measures both (§6).
4. **Decision rule (corrected)**: Λ ≤ 250 ⇒ λ_eff 44.0695 (−6.08 %) ⇒ chem 276.7 M
   ⇒ **GM 28.745 > gold 28.71339**. Λ ≤ 265 ⇒ +0.32 GM. Λ ≥ 281 ⇒ closed.

Corrected Λ → score table (`E_gap` 3.914898 fixed, GM anchored on 28.15083,
`GM = 28.15083·(λ0/λ)^(1/3)`; the earlier table in this file had the cube-root
applied in the wrong direction):

| Λ | λ_eff | Δλ | chem cost | GM | ΔGM |
|---:|---:|---:|---:|---:|---:|
| 283.14 (now) | 46.9216 | — | 294.6 M | 28.151 | — |
| 270 | 45.8118 | −2.37 % | 287.7 M | 28.376 | +0.226 |
| 265 | 45.3825 | −3.28 % | 285.0 M | 28.466 | +0.315 |
| 260 | 44.9491 | −4.20 % | 282.3 M | 28.557 | +0.406 |
| **250** | **44.0695** | **−6.08 %** | **276.7 M** | **28.745** | **+0.595 (gold)** |
| 248 | 43.8915 | −6.46 % | 275.6 M | 28.784 | +0.633 |
| 200 | 39.3781 | −16.08 % | 247.3 M | 29.845 | +1.694 |
| 173.67 (concentration, k=1) | 36.6671 | −21.85 % | 230.2 M | 30.563 | +2.412 |

## 1. The ratio that was asked for, and why it does not decide

Exact from `submission.npz` (U, w = `W`, offsets = `H2_I`), 2,926 pairs, vech with
√2 on off-diagonals:

```
lam_h2 = 0.25 * sum_rc ( sum_b |w_rcb| + |W_rc| )^2 = 270.1150617930869
lam_h1 = 13.0289 (kernel)      Lambda = 283.14396
```

| quantity | value |
|---|---:|
| `‖H‖_F` | 12.184 |
| `‖Y‖_F²` = Σ_k ‖y_k‖² | 53.177 |
| `0.25·‖H‖_F` | 3.046 |
| ratio `lam_h2 / (0.25·‖H‖_F)` | **88.7** |

The rule says ≥ 1.3 ⇒ "≥ 23 % of Λ space". **But the bound is not achievable, for
three measured reasons**, so 88.7 overstates the slack by an unknown factor:

1. `‖y_k‖ ≤ ‖w_k‖₂` is used, but `y = P w` with `σ_max(P_ρ) = 2.55–2.69` (SVD of
   each group's 2,926×143 frame; cond 30–83). Correct chain → `lam_h2 ≥
   0.25·Σ(‖y_k‖/σ_max)² = 1.93` (ratio 140 — even weaker, i.e. the corrected bound is
   *looser*, not tighter).
2. `0.25‖H‖_F` silently assumes orthogonal columns (`‖YYᵀ‖_F ≈ Σ‖y_k‖²`): measured
   `Σ‖y_k‖² = 53.18` vs `‖YYᵀ‖_F ≈ 12.18` (4.4×).
3. The L1/‖w‖₂ concentration is already ≈ 1.5 at the shipped point
   (`mean L1 = 1.180` vs `mean ‖y‖ = 0.376`), so that slack is spent.

Both bounds are formal objects that allow every column to sit on the same top
singular direction — impossible for 352 columns that must span rank 352. **The
decisive number is the 352-dim optimisation, not the ratio.**

## 2. Where the 270.12 lives (exact, new) — and the `|W|` lever

```
a_rc = sum_b |w_rcb|:   sum a^2 = 522.380,  mean 1.180,  min 0.717,  max 3.074
W_rc:                   sum |W| = 179.503,  sum W^2 = 105.441,  mean |W| 0.510
lam_h2 = 0.25 * [ sum a^2 + 2*sum a|W| + sum W^2 ]
       = 0.25 * [ 522.380 + 452.639 + 105.441 ]  ->  sum a|W| = 226.320
lam_h2(W = 0) = 130.595     (i.e. the cross term is 52 % of the total)
```

`W` enters **only** `h1_prime` and `E_SOS`; it does **not** enter `error_2`. So the
whole Λ lever is: keep `ΣW²` (which holds `E_gap` at the floor) and move the same
`|W|` norm onto the cells with the smallest `a_rc` (Cauchy–Schwarz: minimise
`2Σa|W|` at fixed `ΣW²` ⇒ put all the norm on `a_min`). Closed-form numbers
(`ΣW²` = 105.441 fixed, `lam_h1` unchanged):

| distribution of `ΣW²` | `lam_h2` | Λ | λ_eff | chem cost | GM | ΔGM |
|---|---:|---:|---:|---:|---:|---:|
| actual (352 cells × 0.51) | 270.115 | 283.14 | 46.9216 | 294.6 M | 28.151 | — |
| 44 smallest-`a` cells | 185.942 | 198.97 | 39.2755 | 246.6 M | 29.87 | +1.72 |
| 16 smallest-`a` cells | 173.243 | 186.27 | 37.9885 | 238.5 M | 30.20 | +2.05 |
| 4 smallest-`a` cells | 164.522 | 177.55 | 36.98 | 232.4 M | 30.44 | +2.29 |
| **1 cell (`a_min`)** | **160.638** | **173.67** | **36.6671** | **230.2 M** | **30.563** | **+2.41** |

The k=1 value is the hard floor **of the fixed-`ΣW²` sub-problem**: `2·Σa|W| ≥
2·a_min·√(ΣW²) = 14.73`, so `lam_h2 ≥ 0.25(522.380 + 14.73 + 105.441) = 160.638`.
Allowing `ΣW²` to grow can only raise `F` (both terms grow), so the only way the
optimum differs from 173.67 is through `(lam_h1 − tr h1)`:
`E_gap = const + (lam_h1 − tr h1) + 0.5ΣW²` must stay ≥ 3.914898, so if
concentrating `|W|` **decreases** `(lam_h1 − tr h1)`, `ΣW²` must rise to compensate
and the gain shrinks; if it **increases**, the gain is larger than the table.

**This is exactly the "large displacement" that the local projected-gradient result
in `LAMBDA.md` could not see** (that test started at the gate and stepped locally).

## 3. The exact 352-dim problem (what the kernel solves)

```
minimise   lambda_eff(W) = sqrt( E_gap(W) * ( 2*Lambda(W) - E_gap(W) ) )
           Lambda(W) = 0.25*[ sum a^2 + 2*sum a|W| + sum W^2 ] + sum|eig(H1p(W))|
           H1p(W)    = h1_thc - (eta/2) S + beta1 I - sum_rc W_rc X_rc
           E_gap(W)  = EUPPER - ecore + eta*beta1 + (lam_h1 - tr h1) + 0.5*sum W^2
s.t.       E_gap  >= 3.914898            (floor; binding)
           error_1(W) <= 20 mHa          (with the 76 one-body rows RE-ENCODED at 8 bits)
```
`a`, `X_rc`, `lam_h1`, `tr h1` are computed once from the FCIDUMP + shipped npz;
each objective evaluation is one 76×76 `eigvalsh` (sub-millisecond). Gradients:
`dΛ/dW_rc = 0.5(a_rc+|W_rc|)sign(W_rc) − tr(sign(H1p)·X_rc)` (closed form),
`error_1` numerically.

The two things that can kill it, both measured in the kernel:

* **`E_gap`**: concentrating `|W|` changes `lam_h1` (hence `lam_h1 − tr h1`); the
  kernel prints the trade `ΣW²(k)` needed to hold `E_gap` at the floor and the
  resulting `Λ`.
* **`error_1`**: the 76 one-body rows are *independent* unit vectors (each has its
  own 75 tree angles), so any orthonormal basis is encodable in the continuous
  limit; the only real loss is the 8-bit rounding (the shipped table achieves
  19.999998 mHa). The kernel re-fits each row's 75 angles to the new eigenbasis of
  `H1p(W)`, rounds to 8 bits, and reports the resulting `error_1` — including the
  "shipped rows, no re-encode" value, which shows how much the W move breaks the
  old basis.

## 4. What is already closed (do not redo)

* orthogonal rotation of each group's 44 Y-columns at fixed words: 0.0000 %
  (`RESULT3.md` §1) — that is the *small* move, and it is a true local optimum.
* offset projected gradient at fixed words: no admissible step (`LAMBDA.md`) — the
  *local* statement.
* word re-code / C truncation / B-axis shapes: closed (`RESULT4/6/7`, `RESULT.md`).
* public low-Λ baselines: only `FeMoCo76o113e_65_60_60` is submit-able, Λ 308.45
  (scout) — worse.

## 5. Scope

* Exact (local): `lam_h2`, the `a`/`|W|`/`ΣW²` decomposition, `σ_max` per group,
  `‖H‖_F`, `‖Y‖_F²`, the closed-form concentration table, `λ_eff(Λ)`.
* Kernel-only: `lam_h1`, `tr h1`, `E_gap(W)`, the optimisation, the 8-bit
  re-encoding of the 76 one-body rows.
* Not run locally: no simulation, no verifier, no submission.

## 6. Kernels

| kernel | purpose | status |
|---|---|---|
| `qingyu1232/qcc-chem-lambda-offset-min` | §3: Λ/λ_eff minimisation over the 352 offsets, `E_gap` floor + `error_1` re-encode, concentration curve (k = 1/4/16/44/352) and `error_1` budgets 20/22/25/30/50/100/∞ | RUNNING (2026-11-17) |
| `qingyu1232/qcc-chem-bc-axis-shape-fits` | shape-axis continuous fits (`RESULT.md`, negative) | RUNNING |

Measured output lands here when COMPLETE; nothing is assumed.

## 7. If Λ ≤ 250 with both gates satisfied

Then: re-encode the 76 one-body rows at 8 bits (kernel step already measured),
keep w/U/words of the other 1,144 rows, re-plan the 15 loaders at the **unchanged
1,220-row / 77-high / 11-selection geometry** (the ported planner supports exactly
that geometry, `CODE2.md` §4–5), run the unmodified official `verify.py` at 78,080
shots on Kaggle CPU, and require `cost < 294,643,137.73` (target < 276.4 M).
