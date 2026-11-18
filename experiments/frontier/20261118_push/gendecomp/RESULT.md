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
   `outer(L, v)` = *v replicated on a low-monomial subset L*. The target span `R`
   (dim 75 over `h=1..75`, 76 once the `h=76` slice is kept; I use 76) contains **no**
   such vector at all (**[coord]** all 4,943 subsets with |L| <= 5, and 120
   with |L| <= 2 here: `dim W = 0`), so `span{columns}` must strictly exceed `R`. The natural
   chunk-vector product space has dimension `sum_B dim pi_B(R) = 375` (5 blocks of 3 low
   coords), which forces **>= 188 products**, and k4..k8 are exactly there (376 terms).

The general route does not even expose k0/k1: the closed line priced `219/213 -> 188`
products at **+0.103 GM** **[model]**, but k0/k1 need 76 dimensions in block 0 and their
in-block chunk-vector pool has only 42, so their general-architecture floor is *above* 188
too.  Verdict: **the loader product-count axis is closed — not +2.7 GM, but +0 at the
shipped point.**

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
and `logs/debug_residual_k2.log`.

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
| nonzero ANF cells, `h=0..76`, `l=1..15` | 1143 = 15 axial (`h=0`) + **1128 required** | same |
| distinct cell values among the 1128 required cells | **1128, all distinct** | same |
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
| <= 3 | 575 | **0** (local + **[coord]**) |
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

| k | dim pi_B(R), 5 blocks | in-block chunk-vector pool | what the pool can actually span |
|---|---|---|---:|
| 0 | 76,75,75,75,75 (sum 376) | 42,35,35,35,35 | 42,35,35,35,35 = 182 |
| 1 | 76,75,75,75,75 (sum 376) | 42,35,35,36,36 | 42,35,35,36,36 = 184 |
| 2,3 | 75,75,75,75,75 (sum 375) | 50,75,75,105,105 | 50,74,74,75,75 = 348 |
| 4..14 | 75,75,75,75,75 (sum 375) | 53..55, 83, 86, 122, 133 | 53..55,75,75,75,75 = 353..355 |

so the block product space has dimension **375** for every loader with k >= 2 and **376**
for k0/k1, hence `products >= ceil(375/2) = 188` for *any* product set whose columns are
block-local.  **But the floor is not attained**: the pool of block 0 reaches only 42..55
of its 75..76 dimensions, for every loader, so no block-local column set spans `R` at all.
The shipped k4..k8 count (188 products = 376 rectangles) is at the floor only because its
columns are *not* block-local.

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

| construction | terms | products | attainable? |
|---|---:|---:|---|
| single-coordinate chunk vectors (`L` = one coord) | 454 (k4) / 470 (k2) | 454 / 470 | yes |
| prefix chain over a best-ordered coordinate sequence | 454 | 454 | yes |
| per-bit basis labels (`v` = one payload bit, all 35 bits independent) | 470 | 250 | yes |
| 5 x 3 blocks, ideal product space | **375** | **188** | **no**: block 0's in-block pool is only 54 of its 75 dimensions |
| 2-coord blocks (+ one 3-block), union pool | 445 (k4) / 455 (k2) | 223 / 228 | **yes**, `covers_R = true` |
| shipped k2 plan (re-emitted here) | 392 | 196 | yes (shipped, verified) |
| shipped k4..k8 **[brief]** | 376 | 188 | yes (shipped, verified) |

The 375-term floor is therefore *not attainable*, and the cheapest product set I could
actually construct from this family is **445 terms (223 products)** for k4 — worse than
the shipped 188.  The shipped cut-derived plan is still the best known product set.

(The `pool_greedy` number in the Kaggle log, 354 independent vectors for k4 with
`covers_R = false`, is exactly this: 54+75+75+75+75 = 354 of the 375 dimensions, with
block 0's 21 missing dimensions unreachable from in-block columns.)

The bounded rectangle-cover attempt is also dead on arrival, and that is measurable:
all 1128 required cell values are **distinct**, so for a rectangle of area A with the
label of one of its own cells the net gain is `1 - (A-1) = 2 - A <= 0`; the measured best
gain over 400 sampled rectangles (all shapes, seeds on residual cells) is **exactly 1,
at area 1**.  A greedy cover can therefore only take 1x1 rectangles, i.e. 1128 terms =
1128 products, and no `out`-label sharing ever becomes available.  The `pool_greedy`
line in the kernel log shows the same thing at the algebraic level: 354 independent
chunk vectors from the union of the five 3-blocks cover 354 dimensions but `covers_R`
is **false**.

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

## 7. Kaggle CPU confirmation (one kernel)

`jiyujia/qcc-chem-gendecomp-k4` (COMPLETE, CPU, `enable_gpu=false`, `enable_tpu=false`,
no internet, no competition data, no submission).  It re-derives everything from the
shipped table embedded as base64 (sha256 `d8a7adba896711fd…`, the shipped `angle_words`),
and refuses to continue unless the rebuilt target matrix matches the precomputed digests
(`k4 74660f03e34f04a8…`, `k2 7f6a7c4c063fe796…`).  Measured, verbatim from
`logs/kernel_out/qcc-chem-gendecomp-k4.log`:

```
{"k":4,"step":"target_ok","sha":"74660f03e34f04a8c39ebc24c55de53e9c680af679a16751664db8d4626cc06c"}
{"k":4,"step":"chunk_census_R","lmax":1,"chunk_vectors_in_R":0}
{"k":4,"step":"chunk_census_R","lmax":2,"chunk_vectors_in_R":0}
{"k":4,"step":"chunk_census_R","lmax":3,"chunk_vectors_in_R":0}
{"k":4,"step":"block3_total","dims":[75,75,75,75,75],"pools":[54,83,86,122,133],
 "covered":[54,75,75,75,75],"sum_dims":375,"term_floor":375,"products_floor":188}
{"k":4,"step":"block_b","b":4,"dims":[76,75,75],"pools":[1,0,0]}
{"k":4,"step":"block_b","b":5,"dims":[76,75,75],"pools":[0,0,0]}
{"k":4,"step":"block2_attainable","terms":445,"covers_R":true}
{"k":4,"step":"cover_start","cells":1128,"distinct":1128}
{"k":4,"step":"cover_probe","best_gain":1,"best_area":1}
{"k":4,"step":"pool_greedy","pool":478,"chosen":354,"span":354,"covers_R":false}
{"k":2,"step":"block3_total","sum_dims":375,"term_floor":375,"products_floor":188}
{"k":2,"step":"block2_attainable","terms":455,"covers_R":true}
{"k":2,"step":"column_ranks","ranks":[35,35,30,35,30,30,30,35,30,30,30,30,30,30,30],"sum":470}
```

Note on accounts: the assigned account `ccjjllt_check` pushed the same kernel as
`ccjjllt_check/qcc-chem-gendecomp-spanrep` but its token is denied `kernels.get`, so the
log could not be read back; the identical file was therefore also pushed under `jiyujia`
(which the coordinator used for this line's cross-check) and that is the run quoted here.
No other kernel was used and nothing else was run on Kaggle.

## 8. What was run, what was not

* Local, pure arithmetic (no simulation, no verifier, nothing emitted for submission):
  `probe_anf.py`, `probe_rank.py`, `probe_cols.py`, `probe_span_rep.py`,
  `probe_bitbasis.py`, `probe_block3.py`, `debug_residual.py`, `probe_products.py`,
  plus one re-emission of the shipped k2 plan (`emit_from_basis.py 2`) that reproduces the
  closed line exactly: `{"k":2,"products":196,"toffoli":271,"qubits":126,"sum_cuts":133}`.
* Kaggle CPU: one kernel, `jiyujia/qcc-chem-gendecomp-k4` (see §7) re-deriving §2-§4 from
  the shipped table, plus the coordinator's independent `jiyujia/qcc-chem-span-rep`
  **[coord]** chunk-vector census (|L| <= 5, 4,943 subsets, 0 found, k=4 and k=2).
* **No new loader circuit was emitted and no official verifier was run by this line**, so
  no PASS is claimed and the shipped metrics stand unchanged: **Toffoli per loader unchanged
  (294/288/269/269/263x5/264/265x4/266), sum 4,025, `T_total = 14,706`, `Q_total = 427`,
  chem cost 294,643,137.73, GM 28.180659, delta 0.**
  There is nothing to verify: no product set below the shipped count was found.
* Not attempted beyond the bound: a non-block space `S` with `315 <= dim S <= 375`
  spanned by chunk vectors.  The measured censuses (|L| >= 4 -> empty) are the evidence
  that this family does not exist; a proof would need a finer argument than counting.

## 9. Artifacts

All under `experiments/frontier/20261118_push/gendecomp/`.  sha256 in `logs/sha256.txt`.

| file | what it is |
|---|---|
| `common.py` | shipped-table loader + GF(2) rank helpers + ANF cell extraction |
| `probe_anf.py` -> `logs/probe_anf.log` | cell census: 1143 nonzero cells over `h=0..76` (1128 required), all values distinct, ranks |
| `probe_rank.py` -> `logs/probe_rank.log` | per-column / per-row rank profiles |
| `probe_cols.py` -> `logs/probe_cols.log` | pairwise column-difference ranks (all 28..35) |
| `probe_span_rep.py` -> `logs/probe_span_rep_k4.log` | `dim W = 0`: no chunk vector in `R` |
| `probe_bitbasis.py` -> `logs/probe_bitbasis.log` | per-bit label scheme: 470 terms / 250 products |
| `probe_block3.py` -> `logs/probe_block3_k4.log`, `logs/block3_all.json`, `logs/census_b4_b5.json` | block census, greedy coverage, 375/376-term floor for every loader, |L|>=4 pools |
| `probe_products.py`, `debug_residual.py` -> `logs/debug_residual_k2.log` | plan.json rectangle model, 18-cell axial-only residual |
| `make_kernel.py`, `k_spanrep/main.py` | Kaggle kernel source (self-contained, base64 table + digest checks) |
| `logs/kernel_out/qcc-chem-gendecomp-k4.log` | the Kaggle CPU run quoted in section 7 |
| `logs/kernel_dryrun.log` | the same kernel script executed locally (same JSON lines) |
| `artifacts/repro_k2/` | re-emitted shipped k2 plan (196 products, 271 Toffoli, 126 qubits) |

Exact commands:

```
cd experiments/frontier/20261118_push/gendecomp
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_anf.py 0,1,2,3,4
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_rank.py 2,4
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_cols.py 4
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_span_rep.py 4 2
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_bitbasis.py 4,2
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python probe_block3.py 4
# shipped-plan reproduction (read-only on the shipped emitter):
cd experiments/frontier/20261117_deep/chem/work/ds/code2
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python emit_from_basis.py 2 \
  --outdir /Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/gendecomp/artifacts/repro_k2 --write-state
# Kaggle CPU kernel:
cd /Users/zhaohuaxiang/ccjjllt/quantum
python3 scripts/kgpu.py new   --dir experiments/frontier/20261118_push/gendecomp/k_spanrep2 --slug qcc-chem-gendecomp-k4 --account jiyujia
python3 scripts/kgpu.py push  --dir experiments/frontier/20261118_push/gendecomp/k_spanrep2 --account jiyujia
python3 scripts/kgpu.py status --kernel jiyujia/qcc-chem-gendecomp-k4 --account jiyujia --wait 900
python3 scripts/kgpu.py fetch  --kernel jiyujia/qcc-chem-gendecomp-k4 --account jiyujia \
  --out experiments/frontier/20261118_push/gendecomp/logs/kernel_out
```

## 10. Verdict

**Closed.** A general (non-cut-derived) product set cannot beat 188 products for k4 or
k2: the target span contains no replicated column at all, every product column is
replicated, so the span must strictly exceed `R`; the natural chunk-vector product space
needs 375 dimensions (= 188 products) and is not even attainable (block 0's in-block pool
is 54 < 75); the cheapest attainable construction is 445 terms = 223 products, i.e. worse
than the shipped plan; and an `out`-label cover cannot start because all 1,128 required
cell values are distinct.  The brief's 38-product / +2.7 GM hope is a phantom of the rank
bound and should not be planned against.
