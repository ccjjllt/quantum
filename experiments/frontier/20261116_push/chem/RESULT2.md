# Addendum: the R=5 / R=6 shape gate (rows 791 / 934)

Date: 2026-11-16 (second session). Scope: chemistry only, the `(5,143,75)` and
`(6,143,64)` shapes proposed by frontier intel. CPU-only; all circuit work on
Kaggle would be required but **no circuit was built and no verification run was
needed, because the gate fails before the loader stage**. No submission.
`RESULT.md` (the R=8 decomposition and the loader/heuristic block) stands unchanged.

## 0. Answer in one paragraph

The T side of the projection is real and I confirm it exactly: with `Q = 427`
unchanged and `T_heur = 6,889` / `6,976`, a loaders-per-pass figure of 3,165 / 3,120
gives `T = 13,219` (`GM 29.111`, chem cost 264.85 M) — i.e. the loader budget is
comfortable (**per-loader ≤ 237 is needed for T < 14,000; the row-scaling projection
is 174–211**). The **precision gate fails**, and it fails for a reason that is now
measured rather than assumed. Two walls bound this shape family: the rank floor
`floor(K)` (`K = R*C`) and the **projector budget per copy `B/C`**, which sets how
far a fit can get above that floor, `rho = e2_fit/floor`. Measured: `rho = 1.93` at
`B/C = 3.25` (the shipped shape), 2.69 at 2.93, 5.33 at 1.93, 7.54 at 1.58 — i.e.
`rho ≈ 1.93·(3.25/(B/C))^1.95`. The shipped 143-projector spans are also measured to
be **exactly saturated** (pruning 143 → 120 projectors leaves 85–166 mHa per group),
so no spare capacity exists to carry more copies per group. Feeding the two walls
with the proposals' own numbers: **(5,143,75)** has `floor = 5.56` and `B/C = 1.91`
→ needs `rho ≤ 2.99`, gets ≈5.4 → **e2 ≈ 30 mHa against a 16.6 mHa gate**;
**(6,143,64)** needs `rho ≤ 3.20`, gets ≈4.0 → **e2 ≈ 20 mHa against 15.9**. Both
fail, and holding `B/C = 3.25` the minimum viable rows is ~1,215 — which is exactly
the shipped shape. The projection's T (12.1–13.2 k) is real but unreachable.

## 1. Exact T / Q of the proposed shapes (official `SpinFreeData_V1`, no estimation)

Computed with `scoreinfra/costs_prepare.py`; `J = 5` and `brot = 8` unchanged, so
`J*brot = 40` and the angle temp stays 77.

| shape | rows | selection bits | T_heur | outer | inner | Givens | Q_total | T at 211/loader | T at 174/loader |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (8,143,44) shipped | 1,220 | 11 | 6,662 | 317 | 4,095 | 2,250 | **427** | 14,712 (measured) | — |
| **(5,143,75)** | **791** | **10** | **6,889** | 325 | 4,314 | 2,250 | **427** | **13,219** | 12,109 |
| **(6,143,64)** | **934** | **10** | **6,976** | 327 | 4,399 | 2,250 | **427** | **13,216** | 12,125 |

* `Q` is **unchanged at 427** for both (persistent 84 + `J*brot` 40 + temp 303). The
  whole gain would be T.
* `T < 14,000` needs `L/pass ≤ 3,556` → **per-loader ≤ 237** for (5,143,75) and
  `≤ 234` for (6,143,64). The requested 211 (and my row-scaled 174) both clear it.
* The ANGLE cap is *looser*, not tighter: 10 selection + 40 word = 50 persistent →
  **78 workspace** (vs 77 now).
* `T = 13,219` ⇒ chem cost `46.9216·T·427` = **264.85 M** (−10.15 %) ⇒ GM **29.111**
  from the current 28.0909; `T = 13,186` ⇒ 264.19 M, GM 29.135. Equal to the repo
  projection.

## 2. The gate arithmetic

At 1,220 rows the shipped 8-bit table is at `error_2 = 19.99997 mHa` with a
continuous floor of 14.2–14.8 mHa, i.e. the 8-bit rounding penalty is
`p = sqrt(20² − 14.5²) ≈ 13.8 mHa` in quadrature. At 791 rows there are 59,325
angles instead of 91,500, so `p ≈ 13.8·sqrt(791/1220) ≈ 11.0 mHa` and

```
continuous gate = sqrt(20² − p²) = sqrt(400 − 121) ≈ 16.7 mHa   (791 rows)
                                                    ≈ 14.6 mHa   (1,220 rows)
```

So (5,143,75) must reach **≤ 16.7 mHa continuous** (and ideally ≤ 14.5 to have any
margin under the gate, since the frontier already spends its whole budget).

## 3. New exact result: the rank floor is *not* the blocker

The verifier's `error_2` is `||Σ_rc X_rc ⊗ X_rc − tei − shifts||_F` with
`X_rc = Σ_b w_rcb u_b u_bᵀ` symmetric. Writing `y = √weight·vech(X)` on the 2,926
pairs `p ≤ q` turns it into

```
error_2² = || Y Yᵀ − H ||_F² ,   H = W^½ M W^½  (2926 × 2926),
```

so with `K = R·C` terms the *best possible continuous* `error_2` is the eigenvalue
tail of `H`. This reproduces the verifier exactly on the shipped table
(`19.99997 mHa`, verified below), so the floors are hard:

| K | 235 | 264 | 282 | 300 | 320 | 352 | 375 | 384 | 400 | 450 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| floor (mHa) | 45.34 | 29.94 | 22.60 | 16.70 | 11.74 | **7.36** | **5.56** | **4.98** | 4.13 | 2.30 |

Consequences:

* **`K ≤ 282` is provably dead** (floor 22.6 > 20 mHa even with a perfect fit). That
  kills every "reduce R and keep C" shape, including (5,143,44)-type ideas.
* The two proposals have `K = 375 / 384` and floors **5.56 / 4.98 mHa — better than
  the shipped 7.36**. So the projections are not expressiveness-limited; the shipped
  shape itself only realises `14.2/7.36 = 1.9×` its floor.

## 4. What actually binds: projectors per copy, and it is saturated

Each group's `C` matrices must live in a `B`-dimensional span of rank-1 projectors
`u_b u_bᵀ` (`X = U D Uᵀ` with the same `U` for the whole group). The ratio
`B/C` is therefore the real currency, and the shipped point sits at its edge.
Measured on the shipped table (`projector_need.py`, each group, weights refit):

| group | k=20 | k=40 | k=60 | k=80 | k=100 | k=120 | **k=143** |
|---|---:|---:|---:|---:|---:|---:|---:|
| residual (mHa), groups 0–7 | 1372–1577 | 857–1266 | 523–877 | 345–499 | 210–291 | 86–166 | **0.000** |
| projectors per copy | — | — | — | — | 2.3 | **2.7** | **3.25** |

*At `k = 143` the reconstruction is exact (0.000 mHa), which validates the solver;*
removing 23 of 143 projectors (2.7 per copy) already costs 86–166 mHa **per group**.
So the shipped 44-copy groups use all 143 directions essentially, and the family has
**zero spare projector capacity**.

Measured fits along the same axis (repo records, full-U L-BFGS/Adam runs):

| shape | K | B/C | floor | measured continuous e2 | verdict |
|---|---:|---:|---:|---:|---|
| (8,143,44) shipped | 352 | **3.25** | 7.36 | **14.20** | passes (20.000 quantized) |
| (6,143,64) proposal | 384 | **2.23** | 4.98 | not measured | predicted 20.0 (gate 15.9) |
| (5,143,75) proposal | 375 | **1.91** | 5.56 | not measured | predicted 30.2 (gate 16.6) |
| (5,135,70) measured | 350 | 1.93 | 7.55 | **40.24** | fails (2.4× gate) |
| (4,131,83) measured | 332 | 1.58 | 9.69 | **73.07** | fails |

The proposals have `B/C` inside the measured failed region and only +7 % more terms
than `(5,135,70)`. The `B` axis shows the same mechanism in miniature: `B = 129`
(rows 1,108, `B/C = 2.93`, loader −554 T) was measured at **19.83 mHa continuous**,
already past the 14.6 mHa gate for 1,220 rows.

## 4b. The two walls, and the Pareto corner (this is why the frontier is stuck)

Two measured quantities describe every shape in this family:

* **rank wall** — the rank floor `floor(K)` above: the fit can never be below it;
* **projector wall** — the fit quality in units of its floor, `rho = e2_fit / floor(K)`,
  which depends only on the projector budget per copy `B/C`. Measured points:

| shape | B/C | floor | measured continuous e2 | rho |
|---|---:|---:|---:|---:|
| (8,143,44) | 3.25 | 7.36 | 14.20 | **1.93** |
| (8,129,44) | 2.93 | 7.36 | 19.83 | **2.69** |
| (5,135,70) | 1.93 | 7.55 | 40.24 | **5.33** |
| (4,131,83) | 1.58 | 9.69 | 73.07 | **7.54** |

`rho` follows `rho ≈ 1.93 · (3.25/(B/C))^1.95` to within 15 % on all four points (back-
tested: 2.36 vs 2.69 at B/C 2.93; 7.85 vs 7.54 at 1.58). With `rows = 76 + R·B`,
`K = R·C` and `B/C ≤ 3.25` (the measured projector limit), this closes the whole family:

| shape | rows | K | B/C | floor | gate (rows) | rho needed | rho predicted | e2 predicted | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| (9,143,44) | 1363 | 396 | 3.25 | 4.32 | 13.68 | 3.17 | 1.93 | 8.3 | passes but T 16,088 |
| **(8,143,44)** | **1220** | **352** | **3.25** | **7.36** | **14.48** | **1.97** | **1.93** | **14.2** | **passes — the corner** |
| (7,143,46) | 1077 | 322 | 3.11 | 11.33 | 15.23 | 1.34 | 2.1 | 23.8 | fails |
| (7,143,44) | 1077 | 308 | 3.25 | 14.48 | 15.23 | 1.05 | 1.93 | 27.9 | fails |
| (6,143,52) | 934 | 312 | 2.75 | 13.48 | 15.94 | 1.18 | 2.65 | 35.7 | fails |
| **(6,143,64)** | **934** | **384** | **2.23** | **4.98** | **15.94** | **3.20** | **4.02** | **20.0** | **fails (26 % over)** |
| **(5,143,75)** | **791** | **375** | **1.91** | **5.56** | **16.63** | **2.99** | **5.44** | **30.2** | **fails (82 % over)** |

Two consequences worth stating precisely:

1. **Rows below ~1,215 cannot pass.** Holding `B/C = 3.25`, the minimum-viable-rows
   curve is 1080 → 27.9, 1120 → 22.3, 1160 → 18.4, 1200 → 15.6, **1220 → 14.2 (gate
   14.48)**. So the shipped `(8,143,44)` sits exactly on the Pareto corner of the two
   walls — which is precisely why the public chemistry T has not moved off 14,712.
2. **The `(7,143,*)` family** (which the intel did not consider: same `B/C = 3.25`,
   rows 1,077, T 13,336, GM 29.03) is the *cleanest* test of the rank wall alone: it
   needs `rho ≤ 1.05`, i.e. a fit within 5 % of the theoretical optimum, where the
   family achieves 1.93. It is dead on the rank wall, with no projector argument
   needed.

## 5. Attempted fit for the exact shapes (and its honest scope)

I implemented the exact objective in the 2,926-dim space with analytic gradients in
`w` and `u` (`fit_shape.py`) and ran it on the known-good `(8,143,44)` as a
calibration: it reaches **360 mHa**, i.e. **25× worse than the real 14.2 mHa**. The
protocol (spectral init + a few alternating L-BFGS rounds) is therefore not a
competitive fitter, and I do **not** report a new measured number for `(5,143,75)`
or `(6,143,64)` from it. This is a known limitation, recorded so the number is not
mistaken for a shape property.

What can be said without a competitive fitter: at `B/C ≈ 2` the *only* measured
point is 40.24 mHa, the shape's floor is not the problem, and the projector spans
are saturated — so the burden of proof is on anyone claiming ≤ 16.7 mHa at
`B/C ≈ 1.9–2.2`.

## 6. Loader side: not the blocker, but a from-scratch build

* rows 791 → **10 selection qubits** (all public plans are 11-bit / 1,220-row), so
  the loader would be a new design, not a rescale of the published ones.
* Budget: ≤ 237 Toffoli per circuit for `T < 14,000`. Row-scaled from the shipped
  268/1,220-row loader (cache 43–49 + low 6 + products 193·791/1220 ≈ 125) gives
  **174**, and the repo's pair-cache projection gives **211**. Both fit, with the
  78-qubit workspace and the same 69→43 high-monomial cache logic.
* So the loader would deliver `T ≈ 12.1–13.2 k` and GM +0.5…+1.0 **if** the table
  existed. It does not.

## 7. Verdict and the exact blocking site

**CLOSED: `(5,143,75)` and `(6,143,64)` fail the quantization gate, and the failure is
structural — two independent walls, both measured.**

* the rank floor is *better* than the shipped shape (5.56 / 4.98 vs 7.36 mHa), so
  "more terms" is not the issue; but the *fit* must land within `rho = 2.99 / 3.20` of
  that floor, i.e. ~65 % worse relative quality than the family achieves at its own
  best point (1.93);
* at the `B/C` those shapes require (1.91 / 2.23) the measured `rho` is 5.3 / ~4.0
  (power law `1.93·(3.25/(B/C))^1.95`), giving predicted continuous e2 of **30.2 /
  20.0 mHa** against gates of **16.6 / 15.9** — predicted quantized ≈ 32 / 26 mHa,
  i.e. outside the 20 mHa gate;
* the two *measured* points in that region (`(5,135,70)` 40.24 mHa at B/C 1.93,
  `(4,131,83)` 73.07 at 1.58) confirm the trend; the proposals add only +7 % of terms
  over `(5,135,70)` and cannot recover a 2.4× deficit;
* `K ≤ 282` shapes are provably impossible (floor 22.6 mHa > 20);
* rows below ~1,215 cannot pass at `B/C = 3.25`, so the T projection (12.1–13.2 k)
  would require a shape that the precision does not allow;
* the loader and the ANGLE cap are *not* binding (per-loader ≤ 237 needed vs 174–211
  projected; 78 workspace available, one more than now).

**What would overturn this** (one experiment, no new theory): a fit at
`(5,143,75)` or `(6,143,64)` — from the merged `(8,143,44)` structure, long
L-BFGS/Adam schedule, weights and vectors free — that reports **continuous
`error_2 ≤ 16.7 mHa`** (i.e. `rho ≤ 3.0`). If it lands at 20–30 mHa, as the measured
`rho` curve predicts, the line is dead and the row-reduction avenue for chemistry is
exhausted for good: `rows = 76 + R·B`, every reduction of `R` or `B` raises `rho`
and/or the floor, and the shipped `(8,143,44)` is the only point that clears both.

**On the leader inference** (`DQI 840 + chem T≈13,186`): `T ≈ 13.19 k` is exactly
what a 791-row loader would produce, which is why the inference looks attractive,
but the same arithmetic is reachable from a *different* composition (better
invsqrt/DQI at the shipped 14,712 chemistry T), and no measured `B/C ≈ 2` fit
supports the chemistry reading. Treat it as unverified.

## 8. Artifacts, files, verification scope

* `rank_floor.py` — builds `H` (2,926²) from the packaged FCIDUMP + fixed `S`,
  reports the rank-K floors, and **reproduces the official `error_2` on the shipped
  table exactly** (`19.99997 mHa` vs verifier `19.99997`).
* `projector_need.py` — prune-and-refit projector curve on the shipped groups
  (§4); validates exactness at `k = 143`.
* `fit_shape.py` — exact-objective fitter (calibration 360 mHa on `(8,143,44)`,
  i.e. non-competitive; see §5).
* `group_gate.py` — earlier per-mode group construction, superseded (§5); kept for
  the record.
* No candidate package, no official verifier run in this session (nothing to run).
  The verified baseline of `RESULT.md` is unchanged: `T = 14,712`, `Q = 427`,
  `lambda_eff = 46.927643`, cost **294,800,582.44** (PASS at 3 salts), and the refit
  weights give 294,762,697.44 metrics-only.
* Scope: everything here is classical linear algebra on the reference integrals and
  on the shipped `submission.npz`; no simulation was needed and no Kaggle submission
  was made. The `(5,143,75)` / `(6,143,64)` numbers are therefore **gate evidence**,
  not a candidate cost.

## 9. Recommendation

Do not build the 10-bit loader. Close the R=5/6 line unless someone produces the
≤ 16.7 mHa fit above; the projected T (12.1–13.2 k) is real but unreachable because
the table cannot be fit at that projector budget. Chemistry remains frozen at
294.7–294.8 M (T = 14,712), and the remaining chemical headroom is still the
`lambda_eff` floor (+0.086 GM at most).
