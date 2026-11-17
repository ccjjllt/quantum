# RESULT3 — the `|W|`-concentration / sign lever at (8,143,44,brot=8)

Date: 2026-11-17. Chemistry only. Local work = closed-form arithmetic on the
shipped npz + official formulas. Eigen/e1 work on Kaggle CPU (kernel in §5).
No simulation locally, no verifier locally, nothing submitted.

Baseline `a73b25d2` (T 14,706, Q 427, λ_eff 46.921716818, cost 294,643,137.73,
GM 28.15083). **Target of this lever: Λ ≤ 250 ⇒ λ_eff 44.0695 (−6.08 %) ⇒ chem
276.7 M ⇒ GM 28.745 > gold 28.71339.**

## 0. The exact structure (why signing is free, and what it buys)

Official formulas (`scoreinfra/dfthc_math.py`):

```
lam_h2(W) = 0.25 * sum_rc ( a_rc + |W_rc| )^2                 a_rc = sum_b |w_rcb|   (fixed: w untouched)
E_SOS     = ecore - eta*beta1 - (lam_h1 - tr h1) - 0.5*sum W^2
E_gap     = E_upper - E_SOS = Cg + (lam_h1 - tr h1) + 0.5*sum W^2
H1p(W)    = h1_thc - (eta/2) S + beta1 I - sum_rc W_rc X_rc    (signed W!)
lam_h1    = sum|eig(H1p)| = tr h1 + 2*sum_{eig<0}|eig|
```

1. `lam_h2` and the `E_SOS` term see **`|W|` only** → the 352 signs are free for
   both.
2. `H1p` is **linear in the signed `W`** → `lam_h1` and `tr h1` depend on the sign
   pattern. With `Nneg = sum_{eig<0}|eig|`:

```
E_gap = Cg + 2*Nneg + 0.5*sum W^2          Lambda = lam_h2 + tr h1 + 2*Nneg
dLambda/d(sumW2) = +0.25   (lam_h2)         dE_gap/d(sumW2) = +0.5
dLambda/dNneg    = +2                       dE_gap/dNneg    = +2
```

So per unit of `E_gap`, `sum W^2` costs **0.5 Λ** while `Nneg` costs **1.0 Λ**:
`sum W^2` is the cheaper way to hold the gap, and the sign pattern is the *second*
knob (used when `sumW2` is pinned, or to trade `Nneg` against `tr h1`). The one
hard requirement of the k=1 profile is therefore:

> **`Nneg(W_concentrated) ≥ Nneg(shipped)` at `sum W^2 = 105.441`,** otherwise
> `sum W^2` must rise (each +1 costs 0.25 Λ) to hold `E_gap` at the floor.

## 1. The `|W|` profile table (closed form, exact `a` from the npz)

`a_rc` distribution: min 0.717, mean 1.180, max 3.074, `sum a^2 = 522.380`.
`sum W^2` fixed at 105.441, `|W| = sqrt(105.441/k)` on the k smallest-`a` cells:

| k | cross `Σa|W|` | `lam_h2` | Λ (+13.03) | λ_eff | chem | GM | ΔGM |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7.37 | 160.64 | 173.67 | 36.667 | 230.2 M | 30.56 | +2.41 |
| 4 | 14.73 | 164.52 | 177.55 | 37.02 | 232.4 M | 30.45 | +2.30 |
| 16 | 29.46 | 171.68 | 184.71 | 37.83 | 237.5 M | 30.15 | +2.00 |
| **44** | 48.82 | 181.72 | 194.75 | 38.84 | 243.9 M | **29.87** | **+1.72** |
| 88 | 69.03 | 192.05 | 205.08 | 39.87 | 250.3 M | 29.60 | +1.45 |
| 176 | 97.61 | 205.55 | 218.58 | 41.17 | 258.5 M | 29.29 | +1.14 |
| 352 (actual) | 226.32 | 270.12 | 283.14 | 46.92 | 294.6 M | 28.15 | — |

The k=1 value is the hard floor of the fixed-`sumW2` sub-problem:
`2Σa|W| ≥ 2·a_min·sqrt(sumW2) = 14.73`. `k = 16` and `k = 44` are the recommended
risk points: they already cross the gold line (+2.00 / +1.72 GM) with 16–44 nonzero
offsets instead of 1 — much gentler on `H1p`, hence on `Nneg` and on the `error_1`
re-encode.

## 2. The two-step algorithm (what the kernel runs)

```
step 1  choose the |W| profile   (k smallest-a cells, |W| = sqrt(S/k))
step 2  sign search              greedy single flips over the k signs, objective
                                 lam_eff(W) with a hard penalty on E_gap < floor
        (k up to 176, 6 passes, 5 values of S in {1.00,1.05,1.15,1.30,1.60}*S0)
step 3  local polish             Powell over all 352 entries of W (numeric, cheap)
step 4  error_1                  (a) with the shipped 76 one-body rows (shows the
                                 damage), (b) after re-fitting every row's 75 tree
                                 angles to eig(H1p) and rounding to 8 bits
```

Everything except step 4 is sub-millisecond per evaluation (one 76×76 `eigvalsh`).

## 3. Deliverability notes (all previously verified in this repo)

* `w` and `U` are untouched → **`error_2` is bit-identical** (19.9999997 mHa), and
  the 1,144 two-body rows of the word table do not change.
* Only the 76 one-body rows (rows 0..75 of the 1,220×75 table) change → the 15
  loaders' *tables* change in their first 76 rows only; the geometry stays
  1,220 rows / 77 high values / 11 selection bits, i.e. the ported planner's
  hardcoded case (`CODE2.md` §4–5). Loader T must be *re-measured*, not assumed:
  the delta table's first 76 rows feed the same cut/algebra machinery.
* `e1` tolerance is 20 mHa and the shipped point sits at 19.999998, so the
  re-encode has ~0 slack: the new eigenbasis of `H1p(W)` must quantize at least as
  well as the old one. This is the true gate.

## 4. Decision

| measured `Λ_min` with `E_gap ≥ floor` | verdict |
|---|---|
| ≤ 194 (k ≤ 44 feasible) | gold crossed with margin, +1.7 GM: build it |
| 194 < Λ ≤ 250 | gold crossed barely (+0.6 GM): build it, verify first |
| 250 < Λ ≤ 265 | +0.32 GM: still worth a build if `e1 ≤ 20` |
| > 265 | lever dies; chemistry is arithmetically closed |

## 5. Kernel

`qingyu1232/qcc-chem-lambda-offset-min` (CPU only, `enable_gpu=false`,
`enable_tpu=false`), pushed 2026-11-17, v2. Prints: shipped reproduction
(`lam_h1`, `lam_h2`, `E_gap`, `Nneg`, `g_now`), the k×mult sign-search table, the
Powell polish, `error_1` with shipped rows, and `error_1` after the 8-bit
re-encode. Outputs `/kaggle/working/lambda_min.json`, `W_best.npz`, `rows8.npz`.

**Measured results: appended in §6 when COMPLETE — nothing is assumed here.**

## 6. Measured output (kernel)

_(pending)_
