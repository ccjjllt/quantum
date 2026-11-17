# General GF(2) product decomposition of the chemistry angle-loader target

Line: "bypass the cut/pairing heuristic with a general GF(2) product decomposition".
Account `ccjjllt_check`, at most 1 kernel at a time. Date 2026-11-18.

Everything below that is not marked **[brief]** / **[coord]** is a *local pure-arithmetic
measurement* (GF(2) linear algebra on the shipped 1220x75 table, no circuit simulation, no
verifier run). **[coord]** marks numbers independently re-derived by the coordinator on a
Kaggle CPU kernel (`jiyujia/qcc-chem-span-rep`).

---

## 0. Bottom line

**The brief's `products >= ceil(dim/2) = 38` floor is not reachable — not by 5x, not by
1 product — and the general architecture lands on the *same* 188 products as the cut
architecture.** Two independent derivations now agree on 188:

1. cut architecture **[brief]**: `products = (525 - cuts)/2`, `cuts <= 149` (parity) -> 188.
2. general product architecture (this line, measured): a product's column is always
   `outer(L, v)` = *v replicated on a low-monomial subset L*. The target span `R` (dim 75)
   contains **no** such vector at all (**[coord]** all 4,943 subsets with |L| <= 5, and 120
   with |L| <= 2 here: `dim W = 0`), so `span{columns}` must strictly exceed `R`. The natural
   chunk-vector product space has dimension `sum_B dim pi_B(R) = 375` (5 blocks of 3 low
   coords), which forces **>= 188 products**, and k4..k8 are exactly there (376 terms).

The only remaining lever the general route exposes is k0/k1 (`219/213 -> 188` products,
**+0.103 GM** **[model]**), and the measured block census says it is not reachable either
(block 0 needs 76 dimensions and its in-block chunk-vector pool has 42). Verdict: **the
loader product-count axis is closed, not +2.7 GM but +0 at the shipped point.**

---

## 1. What a "product" really is (derivation, then measured)

`s['explicit_products']` has one entry `{'l1','l2','out'}` per CCX.  `emit_plan.emit`
builds each control as

```
a = XOR_{i in bits(l1)} [monomial i over the 4 low bits]  XOR  XOR_{j in bits(h1)} [monomial j over the 7 high bits]
b = same for (l2, h2)                      CCX(ap, bp, z) with z fanned out over the bits of `out`
```

so over GF(2) the product's ANF is `a*b`. Writing `L1, H1, L2, H2` for the monomial
supports, and using `x^S * x^T = x^(S|T)`:

```
a*b = L1*L2  +  L1*H2  +  H1*L2  +  H1*H2
      (low-only,  (the 2 "cells"  (high-only,
       axial/free)  rectangles)    axial/free)
```

So **one product = two rectangles `H2 x L1` and `H1 x L2` in the 76x15 ANF cell grid,
both carrying the *same* 35-bit label `out`**; the row set of each rectangle is exactly
the coordinate row-set that `emit_plan` derives from the target (`hs`), so row sets are
free. Everything else is `(l=0)`/`(h=0)` axial and is fixed for free by the final
`CX` fanouts, plus 12 free padding cells `(h=76, l>=4)`.

Verified against the shipped emitter end to end: my rectangle reconstruction of the
re-emitted k2 plan differs from `cross_tensor` on **18 cells only**, all of them axial
(15 at `h=0`, plain `l`) or padding (`h=76, l=13,14,15`) — see `logs/emit_repro_k2.log`
and `debug_residual.py`.

Consequence for counting. Two terms with the same label can share one CCX, and a single
term can be realised by one CCX, so

```
products = sum over labels v of ceil(t_v / 2)      (t_v = number of rectangles with label v)
```

The shipped k2 plan is 196 products = 392 rectangles with 196 labels, each used twice.

## 2. Measured: the target has no structure to exploit

`probe_anf.py`, `probe_rank.py`, `logs/*.log` (k0..k4 spot-checked, all identical):

| quantity | k4 | k2 |
|---|---|---|
| nonzero ANF cells `(h in 1..76, l in 1..15)` | 1143 | 1143 |
| distinct cell values | 1143 (**all distinct**) | 1143 |
| rank of the 76 slice vectors in GF(2)^525 | 76 (75 for `h=1..75`) | same |
| rank of all cell values in GF(2)^35 | 35 | 35 |
| per-row rank (15 cells per row) | 15 for all 75 rows, 3 at h=76 | same |
| per-low-coord column ranks | `[35,35,29,35,29,29,28,35,29,29,28,29,28,28,28]`, sum **454** | `[35,35,30,35,30,30,30,35,30,30,30,30,30,30,30]`, sum **470** |
| rank of every pairwise column difference `Y_l ^ Y_l'` | 28..35 (mean 31.8) | — |

All cell values distinct kills the "pair equal values" idea outright (`equal_value_pairs
= 0` for every loader), and the pairwise-difference ranks show the 15 low-coordinate
columns are mutually generic, so no "common part" or prefix-chain scheme can share work
across coordinates: the measured prefix-chain cost equals the plain sum of column ranks
(454 for k4).

## 3. Measured: the reported 38-product floor is a phantom

The brief's bound is `2*products >= rank(target) = 75`.  That counts *arbitrary* columns
of `R`. But every column is `outer(L, v)`: `v` on the low set `L`, zero elsewhere — a
"chunk vector".  Measured census of chunk vectors inside `R`:

| |L| range | subsets | chunk vectors found in R |
|---|---:|---:|
| <= 1 | 15 | **0** |
| <= 2 | 120 | **0** |
| <= 3 | 575 | **0** **[coord]** |
| <= 4 | 1940 | **0** **[coord]** |
| <= 5 | 4943 | **0** **[coord]** |

(`probe_span_rep.py`, `logs/probe_span_rep_k4.log`; coordinator's kernel reproduces it for
k=4 and k=2.)  Since `target[h]` is by construction a subset sum of the columns, `R` is
inside `span{columns}`; with no chunk vector in `R` the span must be **strictly larger**
than `R`, so `products >= 38` is not merely loose, it is unattainable by a wide margin.

## 4. Measured: what the architecture can actually do

`probe_block3.py` / `logs/block3_all.json`, `logs/census_b4_b5.json`.  For a block `B` of
low coordinates, `pi_B(R)` is the projection of the slice space; a chunk vector with
`L <= B` can live inside `pi_B(R)` and then serves that block exactly.  Census:

| k | dim pi_B(R) for the 5 blocks | chunk-vector pool per block | greedy spanning set |
|---|---|---|---:|
| 0 | 76,75,75,75,75 | 42,35,35,35,35 | **376 terms** |
| 1 | 76,75,75,75,75 | 42,35,35,36,36 | **376 terms** |
| 2,3 | 75,75,75,75,75 | 50,75,75,105,105 | **375 terms** |
| 4..14 | 75,75,75,75,75 | 53..55, 83, 86, 122, 133 | **375 terms** |

so the block product space has dimension **375** for every loader with k >= 2 and **376**
for k0/k1, hence `products >= ceil(375/2) = 188` for *any* product set whose columns are
block-local.  The shipped k4..k8 count (188 products = 376 rectangles) is exactly this
floor; the shipped k2 (194) is 3 above it.

Larger blocks are not an option — the census is empty:

| block size | dim pi_B(R) | pool |
|---|---:|---:|
| 4 | 76,75,75 | **1, 0, 0** |
| 5 | 76,75,75 | **0, 0, 0** |
| 7 | 76,75 | **0, 0** |

i.e. a chunk vector `outer(L,v)` with `|L| >= 4` inside the target's own projection
essentially never exists (the codimension is far too large), so no coarser partition can
buy terms.

Other constructions measured, all worse than 375 terms:

| construction | terms | products |
|---|---:|---:|
| single-coordinate chunk vectors (`L` = one coord) | 454 (k4) / 470 (k2) | 454 / 470 |
| prefix chain over a best-ordered coordinate sequence | 454 | 454 |
| per-bit basis labels (`v` = one payload bit, all 35 bits independent) | 470 | 250 |
| 5 x 3 blocks (this line) | **375** | **188** |
| shipped k2 plan (re-emitted here) | 392 | 196 |
| shipped k4..k8 **[brief]** | 376 | 188 |

## 5. The floor that is left, and why it does not help

Generic counting over the whole architecture (each chunk vector carries `15 + 35 = 50`
free bits; `R` is a 75-dim subspace of a 525-dim space):

```
50*M + 75*(M - 75) >= 75*450   =>   M >= 315 rectangles   =>   products >= 158
```

So the theoretical floor is ~158 products and the shipped point is at 188, i.e. **at most
~16 % (about +0.5 GM) is even conceivable on this axis**, and only with a space
`R <= S`, `dim S in [315, 375]`, spanned by chunk vectors.  I could not construct one:
`S` must contain 315..375 chunk vectors, and the only family of spaces where the chunk
census is large is the product-of-3-blocks space (dim 375) — see the empty censuses above
for every coarser block.  `probe_span_rep` shows `R` itself contains none.

The one quantitative consequence to record: **k4..k8 are already at 188 and cannot move**;
k0/k1 would need block 0's 76 dimensions covered, and their in-block pool has only 42
chunk vectors, so their general-architecture floor is *above* 188 — the "+0.103 GM for
weak loaders" **[model]** in `loaders/RESULT.md` is therefore not reachable by this route
either.

## 6. Cost arithmetic (pure arithmetic, official formula)

`T_total = 2*sum(loader Toffoli) + 6656`, `Q_total = 427`, `lambda_eff = 46.921716817`,
calibrated so the shipped point reproduces `T = 14,706`, `chem = 294,643,137.73`,
`GM = 28.180659` exactly (same calibration as `loaders/RESULT.md`):

| scenario | sum loader Toffoli | T_total | chem cost | GM | dGM |
|---|---:|---:|---:|---:|---:|
| shipped **[brief]** | 4,025 | 14,706 | 294,643,137.73 | 28.180659 | — |
| all 15 at 263 (188 products + 75) | 3,945 | 14,546 | 291,437,446.04 | 28.283608 | **+0.10295** |
| all 15 at 150 (the brief's invalidated target) | 2,250 | 11,156 | 223,516,853.29 | 30.899148 | +2.718 |
| all 15 loaders with **zero** products + 75 computes (impossible upper bound) | 1,125 | 8,906 | 178,436,813.86 | 33.308503 | +1.12784 |

The shipped point is unchanged: **delta 0 Toffoli, +0.00000 GM**.

## 7. What was run, what was not

* Local, pure arithmetic (no simulation, no verifier, nothing emitted for submission):
  `probe_anf.py`, `probe_rank.py`, `probe_cols.py`, `probe_span_rep.py`,
  `probe_bitbasis.py`, `probe_block3.py`, `debug_residual.py`, `probe_products.py`,
  plus one re-emission of the shipped k2 plan (`emit_from_basis.py 2`) that reproduces the
  closed line exactly: `{"k":2,"products":196,"toffoli":271,"qubits":126,"sum_cuts":133}`.
* Kaggle CPU: one kernel, `jiyujia/qcc-chem-span-rep` **[coord]**, which re-derived the
  chunk-vector nullspace census from the official table on Kaggle CPU for k=4 and k=2.
* **No new loader circuit was emitted and no official verifier was run by this line**, so
  no PASS is claimed.  There is nothing to verify: the search found no product count below
  the shipped one.
* Not attempted beyond the bound: a non-block space `S` with `315 <= dim S <= 375`
  spanned by chunk vectors.  The measured censuses (|L| >= 4 -> empty) are the evidence
  that this family does not exist; a proof would need a finer argument than counting.

## 8. Artifacts

All under `experiments/frontier/20261118_push/gendecomp/`.  sha256 in `logs/sha256.txt`.

| file | what it is |
|---|---|
| `common.py` | shipped-table loader + GF(2) rank helpers + ANF cell extraction |
| `probe_anf.py` -> `logs/probe_anf.log` | cell census: 1143 cells, all values distinct, ranks |
| `probe_rank.py` -> `logs/probe_rank.log` | per-column / per-row rank profiles |
| `probe_cols.py` -> `logs/probe_cols.log` | pairwise column-difference ranks (all 28..35) |
| `probe_span_rep.py` -> `logs/probe_span_rep_k4.log` | `dim W = 0`: no chunk vector in `R` |
| `probe_bitbasis.py` -> `logs/probe_bitbasis.log` | per-bit label scheme: 470 terms / 250 products |
| `probe_block3.py` -> `logs/block3_all.json`, `logs/census_b4_b5.json` | block census + greedy spanning sets: 375/376-term floor |
| `probe_products.py`, `debug_residual.py` | plan.json rectangle model, 18-cell axial-only residual |
| `artifacts/repro_k2/` | re-emitted shipped k2 plan (196 products, 271 Toffoli, 126 qubits) |
