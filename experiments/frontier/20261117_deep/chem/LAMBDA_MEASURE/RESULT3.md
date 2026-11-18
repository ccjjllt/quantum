# RESULT3 — the C axis at frozen `U`: measured curve, and why it is closed

Date 2026-11-18 (this session). Chemistry (`dfthcsos`) only. Follows
`LAMBDA_MEASURE/RESULT.md` and `RESULT2.md`.

Question (retargeted by the parent session): keep `U`, `tree_edges` and
`angle_words` **exactly as shipped**, refit only the weights `w` (and re-choose
`W`), and push `C` down from 44 to 42 (then 40) to buy `T_h`.  Stated gate:
continuous `error_2 <= 16.5` mHa at `C = 42`, floor 9.13 mHa.

Everything below is measured with the competition's own metric code
(`scoreinfra/dfthc_math.py`, unmodified) and the exact full-space objective
`||Y Y^T - H||_F` over the (2926, 2926) vech target of the packaged FCIDUMP.
No kickmix, no circuit, no `verify.py` run, no submission, no git push.

## 0. Verdict

1. **The gate premise is wrong for this task, in our favour — and it still does
   not save the axis.** With `U` frozen at the shipped 8-bit words, `error_2` as
   submitted **is** the fitted number: the verifier decodes the words and
   measures those vectors, so no 11.2 mHa quantisation tax is paid (§1).  The
   shipped `0.019999999958` *is* its fixed-`U` value; the 16.55 mHa belongs to a
   different, continuous `U`.  For a frozen-`U` candidate the gate is **20 mHa**.
2. **At `C = 44` the frozen dictionary does 19.8276 mHa and no better.**  Four
   unrelated starts (shipped `w`, the continuous-`U` 16.55 weights, and two
   noise starts) converge to that value to 4 digits; the two remaining starts
   land in worse basins at 19.8895 and 20.6126, and the Kaggle CPU run
   reproduces the 19.8276 exactly.  The shipped `w` is 0.87 % above it, i.e. the
   submission already sits on this dictionary's `C`-frontier (§2).
3. **`C = 42` is not reachable, and neither is `C = 43`.**  Measured on Kaggle:
   `C = 43` gives **21.2264**, `C = 42` gives **23.2501** — 1.23 and 3.25 mHa
   over the gate.  Two independent reasons: (a) the frozen dictionary's
   block-free span bound alone is 14.498 / 15.037 mHa and the fit carries a
   *structural* excess of 13.96 mHa at `C = 44` that **grows** as columns are
   removed (15.50 at `C = 43`, 17.73 at `C = 42`); (b) the `C < 44` basins are
   not `lambda_eff`-lean (`sum_b |w|` 632 vs 423, `Lambda` 534 vs 290), so their
   `lambda_eff` is ~65 against a break-even of 47.17 / 47.43 (§5, §6).
4. **The excess is structural, not an optimiser artefact.**  Two different
   dictionaries (the shipped words and the continuous-`U` 16.55 solution) give
   the same ~13 mHa excess over their own span bound.  It is the price of
   forcing the `K` columns into `R` spans of `C` columns each, and it is exactly
   the capacity `RESULT2`'s rank merges destroyed.
5. **Payoff, for the record** (exact `SpinFreeData_V1`, loader unchanged):
   `C = 43` +0.050 GM, `C = 42` +0.101, `C = 40` +0.203.  None is collectable.
   After this round the only chemistry lever left is the loader
   (k2/k3 → 264, −20 T, **+0.013 GM**); the `lambda_eff` floor is *not*
   available because the shipped weights already spend the whole `error_2`
   budget (§7).  **The fit line is closed from both sides.**

## 1. The quantisation tax does not apply to a frozen-`U` candidate

The verifier never trusts the npz's `U`; it decodes `angle_words` on
`tree_edges` and evaluates those vectors (`evaluate_dfthc_angle_words` →
`evaluate_dfthc_vectors`).  Locally, on the shipped npz:

| path | error_1 | error_2 | Lambda | E_gap | lambda_eff |
|---|---:|---:|---:|---:|---:|
| `evaluate_dfthc_angle_words` (the verifier's path) | 0.0199999985 | 0.019999999958 | 283.144211 | 3.914898000246 | 46.921583 |
| `evaluate_dfthc_vectors` on the decoded table | 0.0199999985 | 0.019999999958 | 283.144211 | same | 46.921583 |
| pair-space `\|\|YY^T-H\|\|_F` (2926-dim, no truncation) | — | 0.019999999958 | — | — | — |

Three routes agree to 12 digits, and the stored `U` equals its own word set
(per-row overlap 1.0000000).  So:

* a candidate that keeps `angle_words` and refits `w` is measured on **exactly
  the vectors we fit**; the `sqrt(20.00^2 - 16.55^2) = 11.2 mHa` quadrature term
  is a *re-emission* cost, not a property of `error_2`;
* the shipped submission's margin on the gate is **4.2e-11** absolute
  (2.1e-9 relative): it passes exactly on the boundary.  Our `C = 44` refit
  would have 0.86 %;
* the same table also validates the whole fitting pipeline: the pair-space
  `error_2` equals the official one at every `C` in §3 (12 digits), on Kaggle
  as well as locally.

Consequence for the `B` axis: any candidate that changes `rows` must re-emit
`angle_words`, so its quantisation tax is real and the 16.5 mHa premise stays
correct there.  §7 keeps that distinction.

## 2. The fixed-`U` fit: solver, validation, and the `C = 44` optimum

New solver `wsolve.py`.  With `G_r = P_r^T P_r`, `Q_r = P_r G_r^{-1/2}`
(orthonormal) and `y_r = G_r^{1/2} w_r` the model is `Y_r = Q_r y_r`, and with
`C_rs = Q_r^T Q_s`, `H_rs = Q_r^T H Q_s`:

```
M_rs = y_r^T C_rs y_s ,  f = sum_rs ||M_rs||^2 - 2 sum_r tr(y_r^T H_rr y_r) + ||H||^2
g_r  = 4 [ sum_s C_rs (y_s M_sr) - H_rr y_r ]
A(dy)_r = 2 [ sum_s C_rs (dy_s M_sr) + sum_s (C_rs y_s)(dy_s^T C_sr y_r) ]
```

one objective+gradient is ~1e8 flops and one Gauss-Newton operator application
~2e8, both in `B x C` blocks; the normal equations are solved by conjugate
gradients with Levenberg-Marquardt damping and a backtracking line search on the
exact objective.  This is a *joint* solve of the whole `B x C` block per group —
no per-column coordinate descent, no frozen `u_b`.

Validation (machine-checked, `check_wsolve.py`):

| check | result |
|---|---|
| `w_from_y(y_from_w(w)) - w` | 2.5e-15 |
| cheap `f` vs exact `\|\|YY^T-H\|\|_F^2` at the shipped point | 3.99999998e-4 vs 3.99999998e-4 |
| gradient vs the full-space `4 Q^T R Y` | 1.0e-11 rel |
| GN operator vs `J^T J dy` (`J dY = dY Y^T + Y dY^T`) | 2.4e-15 rel |
| pair-space `error_2` vs the official metric, shipped point | 19.999999958 vs 19.999999958 mHa |

Iteration curve, `C = 44`, from the shipped `w` (28 LM steps, 130 CG each):

```
20.0000 -> 19.9588 -> 19.9389 -> 19.9087 -> 19.8725 -> 19.8590 -> 19.8574
        -> 19.8276   (stationary, |g| -> 1e-6; floor 7.361, span bound 14.079)
```

| init | final `error_2` |
|---|---:|
| shipped `w` | **19.8276** |
| continuous-`U` fit `w` (the 16.55 solution) | **19.8276** |
| shipped + 2 % noise | **19.8276** |
| shipped + 10 % noise | **19.8276** |
| relaxed-optimum split (alternative basin) | 19.8895 |
| block-diagonal eigen start | 20.6126 |

Four unrelated starts reach the identical value: 19.8276 is the fixed-`U`
optimum of the shipped dictionary, and the shipped `w` (20.0000) is 0.87 % above
it.  There is nothing to collect at `C = 44` — and §5 shows it would not be
free even if there were.

## 3. The measured `C` curve

Two lower bounds are computed exactly and a third set of numbers is measured.

* **Rank floor** — the best rank-`K` approximation of `H` at all.  Depends only
  on `K = R*C` (`artifacts/H_spectrum.npy` and recomputed from `H`).
* **Span bound** — the frozen dictionary's own limit.  With `S = sum_r S_r`
  (1144 dimensions from the shipped words), the best PSD `M` with
  `range(M) ⊆ S` and `rank <= K` gives

  ```
  min ||M - H||^2 = ||H||^2 - sum_{j<=K} max(lam_j(H_S), 0)^2,
  lam(H_S) = eig( G^{-1/2} (P^T H P) G^{-1/2} ),   G = P^T P
  ```

  because `<H_S, H - H_S> = 0`.  Rigorous for every fit at this `U`.
* **Measured** — the converged LM fit at that `C` (3 inits each, then a long
  polish; Kaggle CPU kernel `zhuating/qcc-chem-c-axis-frozen-u` v1, COMPLETE,
  2311 s).  Per-column shape `(8,143,C)`.

The out-of-span energy is fixed by the words: **12.236 mHa** for the shipped
word set (8.165 mHa for the continuous-`U` fit), which is why the span bound is
14.08 mHa at `K = 352` even though the rank floor is 7.36.

| C | K | rank floor | span bound | measured `error_2` | excess over span | `sum_b|w|` | gate gap |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **44** | 352 | 7.361 | 14.079 | **19.8276** | 13.961 | 423.1 | −0.172 |
| **43** | 344 | 8.168 | 14.498 | **21.2264** | 15.504 | 632.1 | **+1.226** |
| **42** | 336 | 9.130 | 15.037 | **23.2501** | 17.733 | 624.5 | **+3.250** |
| 41 | 328 | 10.267 | 15.736 | 25.4950 | 20.060 | 616.7 | +5.495 |
| 40 | 320 | 11.743 | 16.718 | 27.8262 | 22.244 | 607.2 | +7.826 |
| 39 | 312 | 13.485 | 17.965 | 30.3081 | 24.410 | 599.7 | +10.308 |
| 38 | 304 | 15.543 | 19.538 | 32.9770 | 26.566 | 590.7 | +12.977 |

Read-across:

* the fit tracks **span bound + a growing excess**, never the rank floor: the
  dictionary, not the rank, is what binds at 352 columns;
* the fit's growth from `C = 44` to `C = 42` (+3.42 mHa) is 3.4× the span
  bound's own growth (+0.96): the *block structure* degrades, not just `K`;
* `C <= 39` fails a different way as well — no `W` on the Omega-target ray keeps
  `error_1 <= 20 mHa` for those `X` (see §5), so the submission stops existing
  altogether.

## 4. What the excess is, and what `C` would have to do

The span bound ignores the block structure (it lets the `K` columns live
anywhere in the 1144-dimensional `S`).  The model forces them into `R` spans,
`C` columns each.  For a *random* `K`-dimensional subspace of `S` the split
would be free (`dim(W ∩ S_r) ~ K*B/1144 = C` exactly), but the optimal subspace
is the top eigenspace of `H_S`, and it concentrates in directions that do not
decompose that way.  The price is measured on two dictionaries:

| dictionary | span bound (K=352) | best fit | excess |
|---|---:|---:|---:|
| shipped words (frozen `U`) | 14.079 | 19.8276 | **13.961** |
| continuous `U` of the 16.55 fit | 10.783 | 16.55 | **12.56** |

Two unrelated dictionaries give the same ~13 mHa excess, so it is a property of
the `(R,B,C)` block ansatz at `K ~ 352`, not of a starting point or an
optimiser.  This is also `RESULT2`'s merge result seen from the other side: the
excess is exactly the capacity that merging ranks destroys.

**What `C` would have to do to pass the 20 mHa gate** (`error_2 <= 20`,
excess required = `sqrt(400 - span^2)`):

| C | span bound | excess needed | vs the `C = 44` excess 13.961 | measured excess |
|---:|---:|---:|---:|---:|
| 43 | 14.498 | 13.66 | **−2.1 %** | 15.50 (+11 %) |
| 42 | 15.037 | 13.19 | **−5.5 %** | 17.73 (+27 %) |
| 41 | 15.736 | 12.34 | −11.6 % | 20.06 (+44 %) |
| 40 | 16.718 | 10.99 | −21.3 % | 22.24 (+59 %) |

The sign is wrong everywhere: passing requires the excess to *fall* while
capacity is removed, and the measurements show it *rising* by 1.5–2.2 mHa per
column removed.  Even discounting half of that rise as optimiser slack (the
`C < 44` basins are not `lambda_eff`-lean, §5), `C = 43` still needs 13.66 <
13.961, i.e. a strictly better fit with strictly less capacity.  **Closed.**

## 5. The second squeeze: `lambda_eff`, L1, and the shipped needle

`error_2` is not the only thing a refit must satisfy.  `lambda_eff` depends on
the weights through `lam_h2 = 0.25 sum_rc (sum_b |w_b| + |wB_rc|)^2` while the
`E_gap` floor pins `0.5 sum W^2 ~ 540`:

* shipped `w`: `sum_b |w| = 415.39`, `lam_h2 = 270.12`, `Lambda = 283.144`,
  `E_gap = 3.914898000246`, `lambda_eff = 46.921583`;
* the `C = 44` refit (`error_2 = 19.8276`): `sum_b |w| = 423.08` (+1.85 %),
  `lam_h2 = 277.12`, best feasible `W` gives `Lambda = 290.03`; even with
  `E_gap` driven onto its floor that is `lambda_eff = 47.49` — **+1.2 % cost**,
  i.e. GM −0.11 versus the shipped;
* the `C <= 43` basins are far worse: `sum_b |w| ~ 600-632`, `lam_h2 ~ 520`,
  `Lambda ~ 533` (vs 283), `lambda_eff ~ 65-66` at the measured `E_gap` and
  ~64.5 even with `E_gap` on its floor, against a break-even of 47.17
  (`C = 43`) / 47.43 (`C = 42`).

So the shipped solution trades 0.87 % of `error_2` for 1.2 % of `lambda_eff`:
it is the **`lambda_eff`-minimal** point of the family, not the `error_2`-minimal
one.  The trade is sharp — scaling the shipped `w` along its own ray:

| scale | error_2 (mHa) | error_1 (mHa) | E_gap | Lambda | lambda_eff | GM |
|---:|---:|---:|---:|---:|---:|---:|
| 0.990 | 242.5 | 15.61 | 14.899 | 288.63 | 91.53 | 22.53 |
| 1.000 | **20.00** | 13.39 | 3.921 | 283.27 | 46.97 | **28.142** |
| 1.005 | 124.5 | — | — | — | no feasible `W` | — |
| 1.020 | 493.5 | — | — | — | no feasible `W` | — |

`error_2` doubles with a 0.5 % weight change, and `error_1` leaves its 20 mHa
budget at the same time: the shipped point is a needle, not a plateau.

The `W` channel itself is *not* the bottleneck.  With
`Omega_target = A - V^T diag(lam) V` (`A = h1_thc - eta/2 S + beta1 I`, `V` the
fixed one-body words) and a linear least squares for `W`,
`error_1 = ||Omega(W) - Omega_target||_F` is reachable at **15.88 mHa** on the
shipped `X` (vs the shipped's 20.00) and **15.45 mHa** on the `C = 44` refit
(`E_gap = 4.11`).  `error_1` therefore has ~4 mHa of unused headroom; `error_2`
is what binds, and `sum_b|w|` is what forbids spending it.

One consequence worth recording: a `C = 44` refit at `error_2 = 19.83` /
`error_1 = 15.45` would be a *much safer* submission than the shipped one
(margin 0.86 % instead of 2e-9), but it costs 1.2 % of `lambda_eff`
(`Lambda` 290.0 vs 283.1) and hence **GM −0.33** (`cost 305.38 M`, GM 27.817).
It is therefore rejected: the current submission sits exactly on the gate, and
buying margin costs more than the whole `C` axis would have paid.

## 6. Cost and GM, exact `SpinFreeData_V1`, loader unchanged

`T = 2*4022 + T_h(8,143,C)` (the 15 loaders are the shipped circuits — the angle
table does not depend on `C`), `Q = qubits + J*brot = 427` for every `C` in the
legal box (`RESULT_Q` §5.1).  `lambda_eff` held at the shipped 46.921583.

| C | K | T_h | T | Q | cost (M) | GM | vs 28.15094 | break-even `lambda_eff` |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 44 | 352 | 6662 | 14706 | 427 | 294.642 | 28.15096 | 0.000 | 46.922 |
| 43 | 344 | 6584 | 14628 | 427 | 293.080 | 28.20091 | +0.050 | 47.172 |
| 42 | 336 | 6505 | 14549 | 427 | 291.497 | 28.25186 | **+0.101** | 47.428 |
| 41 | 328 | 6427 | 14471 | 427 | 289.934 | 28.30253 | +0.152 | 47.684 |
| 40 | 320 | 6348 | 14392 | 427 | 288.351 | 28.35422 | +0.203 | 47.945 |
| 38 | 304 | 6191 | 14235 | 427 | 285.206 | 28.45808 | +0.307 | 48.474 |
| 36 | 288 | 6034 | 14078 | 427 | 282.060 | 28.56348 | +0.413 | 49.015 |

The break-even column is the `lambda_eff` at which a shape merely *matches* the
shipped cost.  At `C = 42` it is 47.428 while the best a `C = 44` refit can
reach is 47.49 — and that refit fits *four more* columns per group.  A `C = 42`
candidate would have to be leaner than the shipped weights while fitting less
capacity; with the (`error_2`, L1) coupling of §5 that is not available.

## 7. What is left in the chemistry leg

| lever | size | status |
|---|---:|---|
| `C = 42..40` (this report) | +0.10 … +0.20 GM | **closed** by measurement: 21.2264 / 23.2501 mHa at `C = 43` / `42`; the excess must fall 2–21 % where it rises 11–59 % |
| `lambda_eff` 46.9216 → floor 46.786 | +0.027 GM | **closed**: the shipped weights already sit at `error_2 = 20.0`, i.e. they spend the whole error budget; a leaner `w` needs `error_2 > 20` (scale 0.99 → 242 mHa) |
| loader k2/k3 269 → 264 (`-20 T`) | +0.013 GM | open, blocked: `compile_basis.plan_one` found no plan in 900 s (`RESULT6`); a 1.5–6 h budget is untested |
| `B = 140` (rows 1196) | +0.105 GM | blocked twice: needs a re-emitted word table (new loader plan + new fit), and a re-emitted candidate carries the 11.2 mHa tax, so it needs *continuous* ≤ 16.6 mHa where `RESULT2` measured 19–20 |
| `B = 129` (rows 1108) | +0.46 GM | dead: 27.2 mHa continuous, 2.7× the gate |
| `brot` 8 → 7 | +0.18 GM | dead: the words are 8-bit; a 7-bit re-emission is accuracy-dead (`RESULT_Q` §4.2) and needs a re-emit |

The leg is at its frontier.  The only open item is +0.013 GM in the loader
planner; everything on the fit side is closed from both directions — `error_2`
cannot be pushed under the gate at `C < 44`, and it cannot be traded for
`lambda_eff` either, because it is already spent.

## 8. Verification scope / reproducibility

Run on the competition's unmodified `scoreinfra`, locally and on Kaggle:

* FCIDUMP checksum, `E_upper`, `S`, `beta1` via `check_fcidump` /
  `load_fixed_shifts`;
* the (2926, 2926) vech target rebuilt from the packaged TEI on every run;
* exact full-space `||YY^T - H||_F` for every fit (no eigenspace truncation),
  cross-checked against `evaluate_dfthc_vectors` / `evaluate_dfthc_angle_words`
  (agree to 12 digits at every `C`);
* official `error_1 / error_2 / Lambda / E_gap / lambda_eff` for the shipped npz
  and for every candidate `(w, W)`;
* exact `SpinFreeData_V1` `T_h`, `Q` per shape and the GM from `scripts/gm.py`'s
  reference constants.

Not run: kickmix, any circuit, the full `verify.py` (needs `.kmb`), any Kaggle
submission or leaderboard read.

Provenance: Kaggle CPU kernel `zhuating/qcc-chem-c-axis-frozen-u` v1,
COMPLETE, 2311 s (`kgpu.py push`), outputs `artifacts/20261118_caxis/`
(`result.json`, `w_C44.npz`, `w_C43.npz`, `w_C42.npz`, kernel log).  The
`C = 44` value reproduces the local run to 4 digits on a different machine.

Code (all in `LAMBDA_MEASURE/`, reusable): `wsolve.py` (solver),
`check_wsolve.py` (its four validation checks), `diag_c2.py` (span bound),
`multi.py` (multi-start), `wstage.py` + `pareto44.py` (`W` channel),
`cost_c2.py` (cost/GM and break-even), `kernel_driver.py` + `build_kernel.py`
(the Kaggle sweep).  `kernel_driver.py` takes `CS=44,43,...` to re-run any
subset.
