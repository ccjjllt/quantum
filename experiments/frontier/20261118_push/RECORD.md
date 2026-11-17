# 2026-11-18 push — master record

Round 2 of parallel research after the 2026-11-17 deep pass. All numbers below are
measured unless marked **[model]** (pure arithmetic from the official cost code).

## 0. Starting point

Shipped triple (verified, 28.1806 local): invsqrt `563d0583` 74,560.90687 /
DQI `575b043f` 346,409,762,292.72 / chem `a73b25d2` 294,643,137.73.
LB 28.15094 (rank 156), gold 28.71339, top 31.42723.
Submission quota: 5/5 used on 2026-11-17; resets UTC 00:00 = Beijing 08:00 on 11-18.

## 1. probe791 (chem, reduced rows) — COMPLETE, negative

Kernel `qingyu1232/qcc-chem-probe791` (2026-11-17 15:15–15:51). Truncated the
shipped 1,220-row table to 791 rows and asked the emitter to plan loaders for
k=2 and k=4 with a 900 s budget each, 4–5 seeds each.

```
k2: target len 50 (hmax 49); seeds 11/7/9/8: no rank-74 basis found
k4: target len 50 (hmax 49); seeds 11/7/9/8: no rank-74 basis found
SUMMARY {"2": null, "4": null}
```

So a 791-row table cannot even be planned at rank 74 within 4 × 15 min per k.
The rows axis is closed on the *loader-planning* side as well as the accuracy
side (RESULT2: (5,143,88) is 136.76 mHa continuous, gate 20).

## 2. R=5 / R=4 shapes — closed with exact model values

Subagent result (2026-11-18 ~00:20), exact full-space objective:

| shape | rows | best continuous error_2 | exact-model Q | T_h |
|---|---:|---:|---:|---:|
| (5,143,88) | 791 | 136.76 mHa | 429 | 7,539 |
| (5,136,96) | 756 | 135.20 mHa | 430 | 7,916 |
| (4,143,128) | 648 | 176.76 mHa | 429 | 8,243 |
| (6,136,72) | 892 | 127.69 mHa | 427 | 7,433 |

The gate is 20 mHa — 6.5–6.8× away. The one shape that clears continuous 20 mHa,
(8,143,55) at 18.05, fails on quantisation (error_1 50 mHa) and lambda_eff
(63.90 vs 46.92), cost 313.8 M. Closed. Full record:
`experiments/frontier/20261117_deep/chem/R5_SHAPE/RESULT.md`.

## 3. New lever: `brot` is submission-controlled (chem) **[model]**

`verifiers/dfthcsos/verify.py` reads `brot` and `J` from the width/number of the
`word_j` registers of the submitted angle circuits, then uses `beta = brot` in
`SpinFreeData_V1`. Exact values for the shipped shape (R=8,B=143,C=44,N=76,
chi=10 fixed, J=5):

| brot | givens `2*(N-1)*(2*brot-1)` | T_h | Q_total |
|---:|---:|---:|---:|
| 8 (shipped) | 2,250 | 6,662 | 427 |
| 7 | 1,950 | 6,362 | 422 |
| 6 | 1,650 | 6,062 | 417 |
| 5 | 1,350 | 5,762 | 412 |
| 4 | 1,050 | 5,462 | 407 |

`theta/pi = word / 2**(brot-1)`. The shipped `angle_words` (1220, 75) uint8 uses
all 256 values (odd count 45,088), so 7-bit is **not** free: it needs a refit at
7-bit word quantisation that keeps `error_1, error_2 <= 0.020`, `Lambda >= 49`.
If it works: brot 8→7 is `(422/427)*(14412/14706) = 0.9685` on chem cost
(**+0.30 GM**), brot 8→6 would be 0.9307 (**+0.72 GM**) but 6-bit quantisation is
much coarser. Assigned to the chem research line.

A second free knob in the same formula: `Q_total = 84 + J*brot + max(...)`.
J=5 is shipped; smaller J lowers Q but multiplies the number of loader circuits.
Assigned to the chem line (J sweep).

## 4. Parallel research lines opened (2026-11-18 00:40 Beijing)

Brief: `experiments/frontier/20261118_push/BRIEF.md`.

| line | account | target |
|---|---|---|
| dqi | zhuating | verify new public DQI set; product-cache finder inside condition blocks; Q<=866 feasibility |
| chem | qingyu1232 | brot 8→7 (and 6), 4,022 public loaders, J sweep |
| invsqrt | jiyujia | fresh 42Q synthesis / lower C |
| harvest | ccjjllt_check | new public components + top-team intel + papers |
| model | zhuating | full audit of submission-controlled parameters in all three verifiers |

## 4b. Packaging bug found and corrected (2026-11-18 00:55)

The "28.1806" package built by `qingyu1232/qcc-integrator-inv563d0583` v2 is **wrong**:
its `receipt.json` shows `dqi.kmb` sha `957d6733…` with **value_errors 1** on the default
salt, cost 348,246,849,661.48, GM **28.1310187** — below the current LB 28.15094.
`members_2818066.json` itself carries the wrong DQI sha; the "salt false alarm" note in
SUMMARY2 §17 was masking a manifest error.

Corrected manifest `integration/members_281806_correct.json`: same invsqrt (`563d0583`)
and same chem 18-member set, DQI replaced by `575b043f`
(sha `575b043f4fee…`, 479,128,738 B) from
`grantprater/vqcc-dqi-61c8348d-merged-closings : dqi_575b043f.kmb.xz`.
New integrator `qingyu1232/qcc-integrator-281806` v1 (expected GM 28.180659; the kernel
extracts the `.xz` and matches the sha). The LB draw for `575b043f` is already known clean
from submission 58464076, so the expected LB score is 28.18 if the salt is per-file.

## 4c. invsqrt circuit census (2026-11-18, local parse only, no simulation)

`563d0583.kmb`: 179,308 B, 44 qubits, 20,659 instructions.
Static counts: `CX 12,297 · CCX 1,518 · CZ 1,502 · HMR 1,277 · Z 1,010 · X 946 ·
PUSH/POP_CONDITION 674 each · CZ_IF 593 · Z_POW 43 · CCZ 30 · SWAP 12`.
`mean_toffolis()` = **1,454.0008 exactly** (static 1,548 -> 94 saved by classical
conditions). 33 of the 43 Z_POW are non-Clifford (T=962.256).

Pair analysis (compute/uncompute candidates): only **6 clean adjacent CCX pairs**
(same controls+target, nothing touching the target between) and 8 with only Clifford
touches between. So the CCX->HMR rewrite is **not** a large lever on this circuit —
it already uses HMR 1,277 times. The Toffoli-count lever must come from a different
arithmetic/approximation, not from uncomputation pairs.

U/tree facts for the chem tree line: `U` is (8,143,76) -> 1,144 two-body rows, every
row is a unit vector (norm 1.000000); `tree_edges` is not a chain (degrees 1..7, 44
leaves); `reconstruct_u_vectors` applies the 75 Givens rotations in `tree_edges`
order from e_0.

### 4d. Gauge freedom is NOT free for the loader line (checked 2026-11-18 01:20)

The DF-THC metric is invariant under an orthogonal `b`-gauge `U' = U G`, `W' = W G^T`,
so it looked like a free way to reshape the angle table. But the score factor is
`lambda_h2 = 1/4 sum_(rho c) (|w|_1 + |w_B|)^2` (verifier `dfthc_math.py:88-96`),
which is an **L1** functional and therefore **not** gauge-invariant. The shipped
`lambda_eff` 46.9216 is already the lambda-minimal point (floor 46.786), so a general
orthogonal gauge will raise Lambda and cost more than it can save on loaders.
Only permutation/sign gauges keep L1 exactly — those are the row-permutation lever
already handed to the loader line. Do not spend time on continuous gauges.

## 4e. Model audit results (2026-11-18 ~01:25, measured on Kaggle CPU)

* **`brot 8->7` is DEAD (measured).** On the shipped `a73b25d2` table the verifier gives
  brot=7: error_1 2047 mHa, error_2 419.5 mHa, Lambda 289.11, lambda_eff 74.94 -> FAIL;
  brot=6 worse. Re-quantisation costs ~x21 per bit on error_2 against a 20 mHa budget,
  and lambda_eff would rise ~60% anyway. `brot 8` is a floor, not a knob. My earlier
  +0.30 GM estimate is refuted.
* **`Q_total = 387 + J*brot` is exact** (J=5 -> 427); `J` changes no metric; J=14 is
  rejected (>128 angle-circuit qubits); J=5 is the optimum.
* **Angle-circuit workspace is free** up to the 128-qubit cap (padding 61->128 leaves
  Q_total and score bit-identical).
* **Row order is a legal free degree of freedom, but only jointly**: permute `(w, u)`
  together inside each rho block (1211/1220 rows moved, metrics identical to 1e-14).
  Permuting words alone explodes to 27,133 mHa.
* invsqrt: 33 rotations is within 1 of the provable dyadic-ladder floor; marginal
  rotation +0.041 GM; **1 qubit = +0.213 GM** is the only real path.
* dqi: a failed shot costs 0.459%, so a rewrite saving >1,678 T may lose one shot and
  still win; `num_shots`/`log2_delta`/`(m,n,degree,r)` are CLI-only; E0..E4094 are
  never read back (49,140 free classical bits); **no Z-basis measurement exists**.
* Flagged but NOT used: the receipts suggest the grader may run without `--salt`
  (seed = circuit hash); the public DQI author says the leaderboard uses a secret salt.
  Unconfirmed, contract-sensitive, and not part of any plan here.

## 5. Submission plan

Quota resets 2026-11-18 08:00 Beijing. Submit the best verified package then and
record the public score + submission ref here and in `submissions/`.

## 4f. C axis final (2026-11-18 ~01:40, measured on Kaggle CPU)

Frozen-U joint `w` refit at each C (3 starts + polish, exact full-space objective):
C=44 19.8276 mHa (shipped is 0.87% above the C=44 frontier), C=43 21.2264 (+1.23 over
gate), C=42 23.2501 (+3.25), C=40 27.83, C=38 32.98. The structural excess rises with
each removed column, and the C<44 basins are not lambda-lean (Lambda 534 vs 283,
lambda_eff ~65 against break-even 47.2/47.4). **C axis closed.** Record:
`experiments/frontier/20261117_deep/chem/LAMBDA_MEASURE/RESULT3.md`.

## 4g. Chemistry line closed on everything except loaders (2026-11-18 ~01:40)

Chem agent (measured, official verifier): baseline rebuilt bit-identical (score
294,643,137.73, T 14,706, Q 427); **brot dead** (7-bit: error_2 0.426064, lambda_eff
72.67, cost +49.9%; a full 50,336-parameter L-BFGS refit moves it only -0.02% -> grid
problem, not optimiser); `tree_edges` provably cannot move T_h/Q (the heuristic takes
no tree); J=5 optimal; the public "4,022-Toffoli loaders" are byte-identical to ours
(sha ed6487084d30b0c7...). The shipped point sits 2.6e-10 from both error gates and
the E_gap floor. Record: `experiments/frontier/20261118_push/chem/RESULT.md`.

## 4h. Public frontier = our package; loader ceiling measured (2026-11-18 ~01:50)

* `atakanaldemir/qcc-shared-products-and-controlled-refits` reports **observed public score
  28.18070** — exactly our verified 28.180659 package (same invsqrt 563d, DQI 575b, chem
  703843d3 + the 4,022 loaders). The public frontier is therefore where we already are;
  everything above it is private work.
* The loader line's own probes give the **true cut ceiling**: at the 4-bit split the five
  3-coordinate blocks have dim 105 and rank **75** (not 30), so nullity = **150 cuts** ->
  `products_ceiling 187.5` -> `toffoli_est 256.5` per loader. The shipped best loaders
  (k4-k8) already have **149 cuts / 263 Toffoli**. Remaining realistic saving: weak
  loaders k0 (87 cuts), k1 (99), k2/k3 (137), k9-14 (143-147) up to 263 ->
  about **-80 Toffoli total = -160 T = +0.10 GM**. My earlier 375-cut / +2.7 GM estimate
  was wrong (it used rank 30 instead of 75).
* Row/tree/column permutations do **not** move the ceiling: the block ranks stay
  [75,75,75,75,75] for identity/reverse/sort/nearest-neighbour/random, and non-identity
  permutations break the emitter's `helper_low_high_ok` structure.
* The 5-low-bit split lowers the estimate to 231.5 Toffoli but has **0 form-pair
  candidates** at saturation (`probe_split_pairs`), so it is unreachable; 3-low-bit is
  worse (254).
* Consequence: the achievable stack today is invsqrt 42Q (+0.44 if a cheaper retirement
  exists), DQI cuts (+0.06 at 686 T, more only with a new pair finder), loaders (+0.10),
  chem lambda floor (+0.03) -> roughly **28.7-28.8**. The leaderboard's 29.98-31.43 tier
  must come from a fundamentally cheaper DQI decoder (a 32% mean-T cut at 890Q, or
  <=840Q), which is the only remaining large lever.

## 4i. Loader line final (loaders agent, measured, 2026-11-18 ~01:55)

* True block rank is **75**, nullity 30 -> **150 cuts**, `products >= 188` (dim 375 odd),
  `Toffoli >= 263`. The shipped k4-k8 sit exactly on that floor.
* Block partition (>=4 coords), (h,l) L=5 split, and row order are each measured closed:
  saturation has 0 form-pair candidates for the alternative partitions; L=5 has 32-CCX
  high cache but 0 pairing candidates; every non-identity row order breaks the
  `bit7^bit6` helper's low/high decomposition; block-rank proxy is 75 for all orders.
* k0/k1 are structurally stuck: per-coordinate projection ranks [35]x15 (no relations),
  so the minrank attack has nothing to exploit. k>=9 cannot be re-emitted from this
  table (word group 0's helper table differs).
* Bounded upside from pushing the weak loaders to 263: **-80 Toffoli = -160 T ->
  chem 291,437,446 / GM 28.2836 (+0.103)**.
* The decisive remaining fact: the hard product floor for ANY product architecture is
  `ceil(dim/2) = 38` products (Toffoli ~113/loader), 5x below what the cut/pairing route
  can reach. A general GF(2) product decomposition (not the cut/pairing route) is the
  only way to that floor; a new line has been opened on it.

## 4j. Tree axis closed (tree agent, measured, 2026-11-18 ~02:00)

* The exact inverse of `reconstruct_u_vectors` reproduces the shipped U to 2e-14; the
  shipped words decode with row norms 1+-2e-16.
* Free exact levers: per-(row,edge) sign branches (theta->theta+pi, still a grid point)
  and edge permutations that keep each node's child order (residual 0.0, bit-identical U
  -> the column-permutation lever). Sibling-reordering permutations are not free (0.63).
* 263 trees (chain/star/bushy/attach/Prufer/deep/heap/chain relabellings): loader floor
  total 2,687..2,805 (median 2,780, sd 24.9) -- best is +321 above the shipped.
  12 free value-preserving permutations: 2,447..2,454 (+81).
* Shipped per-loader Toffoli (kickmix metadata): [292,287,269,269,263,263,263,263,263,
  264,265,265,265,265,266], sum 4,022 -> T = 14,706 exactly.
* Planner probes: shipped table k=4/k=9 at 120 s -> max cuts 150, no perfect pairing;
  a canonical re-encoding of the same U at 420 s -> no plan. No alternative table can
  come in under 4,022.
* Prize: -80 Toffoli (all remaining loader headroom) = **+0.051 GM**; -174.5 (absolute
  ceiling) = +0.112 GM. Closed.

## 4k. invsqrt rotation retune (measured, 2026-11-18 ~02:05)

`jiyujia/qcc-invsqrt-rotlp-563d0583` retuned the 33 rotation eps to the margin boundary:
OFFICIAL PASS, score **74,560.71496** vs shipped 74,560.90687 (-0.192, 2.6e-6 relative),
toffoli 1,453.9968, t_count 2.4985, margin 31,789,809 (shipped 31,789,811). GM gain
~1e-6. The 33 rotations are the dyadic-ladder floor (model line); the only real invsqrt
lever remains Q=44->43/42 (+0.22/+0.44), which needs a cheaper retirement than the
>=132 C per pair measured earlier against an 80.7 C budget.

## 4l. invsqrt line closed (invsqrt agent, measured, 2026-11-18 ~02:10)

* Public sweep by sha256 + published official receipts: **our `563d0583` is the public floor**
  (the junmiaotiao frontier notebook ships the identical bytes); next best f2cdab0b 75,006.38,
  8b410e77 75,038.13, 0af21cb8 74,797.37.
* Toffoli at Q=44: census splits the 1,548 static into 7 regions; the conditional discount is
  fully explained (176 depth-1 + 8 depth-2 -> 1,454.0 exactly). Hash-consed product accounting:
  1,479 distinct products, only 4 ever recomputed, 35 removed by CCX, **1,277 recycled by HMR**
  -> **no paid compute->CCX-uncompute pair anywhere**. A phase-fold search found 0 sites.
  Karatsuba does not apply (table+interpolation, not a wide multiplier).
* Rotations: worst x=231, ratio 0.99956056, margin 31,789,811 units (0.044% of tol); dropping
  the smallest rotation and retuning fails at 1.2495; the verifier's own objective (absolute
  margin) returns lambda=1.0 -> shipped angle set is locally optimal. The 240.56 C rotation
  block is a floor.
* Width: 42Q needs Toffoli <= 1,534.69 (+80.69); observed frontier slope 13.4 Toffoli/wire,
  42Q needs 40.3/wire. Syed's 46Q circuit (1,480.8 Toffoli) would win at 42 wires but is pinned
  at 46 by 485 one-wire spikes.
* New official receipt: shipped file, 1 shot/x PASS, score **74,560.71496**, toffoli 1,453.9968.
* Verdict: **invsqrt is finished at 74,560.9**; only a generator-level rewrite could move it.

## 4m. DQI candidate + region split (measured, 2026-11-18 ~02:10)

* Candidate `dqi_cond.kmb` (condition-block finder output, `zhuating/qcc-dqi-condfind-1118`):
  default salt **PASS 346,406,882,459.21** (toffoli 367,113.005, Q 890, 0/0 errors) vs
  shipped 346,409,762,292.72 -> only **-2,879,833 (-3.05 T)**; the two fresh salts each lose
  1 value error (cost 348.0e9). Negligible gain and worse salt robustness: **do not ship**.
* Static region split of `575b043f` (57,520,821 ops): A (ops 0..30,335,416) 153,186 Toffoli;
  B = Chien region (30,335,416..35,627,262, j=7..4094) **44,264 Toffoli (12.0%)**;
  C (35,627,262..end) 170,539 Toffoli. So the Chien search is only 12% of T: **the EEA
  regions A+C (88%) dominate**, and a 28% T cut must come from the EEA, not the Chien search.
  GF-mult block census shows many uniform 42-CCX blocks in A (1,542 blocks of 42).

## 4n. DQI region split details (measured, `region_split.json`)

| region | ops | Toffoli | CCX | CCZ | dynamics mean | mult blocks >=12 | target mix |
|---|---:|---:|---:|---:|---:|---:|---|
| A (forward EEA) | 30.3M | 153,186 | 153,185 | 1 | 153,180.1 | 2,702 (1,542 of size 42) | syndrome 85,406 / pool 67,779 |
| B (Chien/Forney) | 5.29M | 44,264 | 40,240 | 4,024 | 44,217.0 | 0 | pool 40,240 |
| C (reverse EEA) | 21.9M | 170,539 | 168,587 | 1,952 | 169,719.2 | 2,602 (1,526 of size 42) | syndrome 85,488 / pool 83,099 |

Dynamic mean 367,116.3 vs static 367,989: every block fires (no gating surplus). The 42-CCX
blocks are GF(2^12) multipliers: A ~2,702 mult-blocks, C ~2,602. The reference generator's
`default_n_iters(n) = 3(n+1)+9 = 222` is a loose bound; if the tape's per-pass iteration count
is smaller (order 37-50) it may or may not carry surplus. The truncation test (delete last k
forward + first k reverse iterations, verify 3 salts) is with the dqi_algo line.

## 4o. DQI tape axes closed (dqi agent, measured, 2026-11-18 ~02:15)

* All five public DQI files verified at 3 salts, phase_errors 0 everywhere:
  61c8348d 348,004,440,260.46 (loses a shot on ALL 3 salts), **575b043f 346,409,762,292.72
  (0/1/0)**, 66b4f18b 347,128,304,010.81, ccc2ab84 347,375,470,571.73, d54d3387
  347,340,788,307.83. Our file is the best; it is 4 static Toffolis below 61c8348d and
  also more salt-robust.
* Inside-condition-block pair finder (their open item #3) built: 44,422 conditioned CCX,
  4,184 retention pairs, 206 conditioned, 44 with a clean wire, **3 servable** ->
  367,989 -> 367,986 static. The candidate passes 0/0 at the default salt but loses a shot
  at 2 of 3 salts -> +0.000078 GM clean vs -0.0429 GM on a lost shot. **Reject; keep 575b043f.**
* Free Toffolis (void/zero/held/dead-condition incl. all 44,422 conditioned CCX): **0**;
  plain cancels: **0**. Extra-wire curve: 1 wire buys 180 retentions vs an 825 T break-even;
  14 wires buy 2,366 vs 11,556 -> +2.5% cost. Unaffordable at every k.
* Q axis: 51.94% of all Toffolis are written into the 50 pool wires; 26 persistent 12-bit EEA
  words + 2 flags + 24 product-pool wires. 866Q leaves zero product pool with a rebuild
  floor >=116,894 T vs a +20,630 T break-even. Closed.

## 4p. The general-decomposition KEY EXPERIMENT (gendecomp, in flight 02:05)

The loader's 525-bit slice space contains the target span R (dim 75). A product of the
emitter's form contributes `outer(L, v)` = the 35-bit value `v` placed on every low coordinate
in L. **If R has a basis of such replicated vectors, the loader needs only ~dim R = 75 products
(Toffoli ~150) instead of 188**, i.e. -113 Toffoli/loader -> -1,695 total -> -3,390 T ->
chem ~215M -> **GM ~29.8 (+1.6)**. The experiment computes, for every low-coordinate subset L
with |L| <= LMAX, the exact subspace V_L = {v : outer(L,v) in R}, accumulates W = span of all
replicated vectors, and reports dim W vs dim R. `probe_span_rep.py` is that computation; a
dim W = 75 result would open the general decomposition, a small dim W closes it.

## 4q. DQI algorithmic axis: EEA is tight; the only arithmetic lever is the multiplier rank

dqi_algo RESULT.md (measured):
* Region split calibrated to the official 367,116.06: EEA fwd 153,180 / Chien 44,217 /
  EEA rev 169,719. **EEA = 87.9%**, Chien 12.0%.
* The tape runs **34-35 division rounds per pass** (degree argument: deg 69 -> <35, at least
  one degree per round). The reference's `default_n_iters = 222` is `3(n+1)+9` on a 4-phase
  counter, i.e. ~55 full steps -- the tape is already tight. **No surplus iterations to
  truncate**; mean/static 99.76% confirms nothing is gated off.
* Arithmetic census: 3,969 real multiply blocks (159,300 CCX = 43.3% of T), mean rank 40.1,
  mode 42 (Toom-4). Control logic + 12-bit AND chains = 164,425 (44.7%); Chien 11.0 T/position
  (already at its idiom minimum; a per-position inverse would cost 315 T).
* **The entire arithmetic-substitution budget of the DQI leg is 68,022 T = 18.5% = +1.99 GM**,
  all of it in the bilinear rank of the 12x12 GF(2) multiply (42 -> floor 23). A rank-35
  multiply would be +0.57 GM but needs regeneration (no rank-35 construction known at this
  size; the tape has no tags and every multiply is fused into a ~1,250-CX rotation scaffold).
* Rejected: schoolbook (+412k T), kickmix ixor_gf2_mul (+91k), Toom-3 (+19k), Berlekamp-Massey
  (3.3x multiplies), Welch-Berlekamp (77x), windowed EEA (bilinear rank additive).

## 4r. General-decomposition key experiment: NEGATIVE (measured, jiyujia/qcc-chem-span-rep)

The decisive test: is the 75-dim target span R spanned by "replicated" vectors
`outer(L, v)` (v placed on every low coordinate in L, i.e. a product with the full h-mask)?
Measured on the shipped table, k=4 and k=2:

```
dim R = 75
|L|<=1  15 subsets   nullspace dim 0   dim W = 0
|L|<=2 120 subsets   nullspace dim 0   dim W = 0
|L|<=3 575 subsets   nullspace dim 0   dim W = 0
|L|<=4 1940 subsets  nullspace dim 0   dim W = 0
|L|<=5 4943 subsets  nullspace dim 0   dim W = 0
```

**dim W = 0**: there is no nonzero v with outer(L,v) in R for any L up to size 5. The
"only ~75 products" shortcut is dead. The cut/pairing products (188) use partial h-masks
(h1/h2 rectangles), which is a genuinely harder combinatorial problem; the hard floor
`products >= 38` is not reachable by the replicated-vector construction. The loader axis
stays at 150 cuts / 188 products / 263 Toffoli per loader, with the bounded +0.05..0.11 GM
headroom from the weak loaders.

## 4s. Frontier literature (web, 2026-11-18 02:25)

* **arXiv:2610.22367 / Anthropic (Oct 2026)**: an LLM-discovered Reed-Solomon decoder using
  **Berlekamp-Massey** instead of EEA: 440,000 Toffoli at 1,837 peak qubits vs the EEA baseline
  5.1M at 1,938. In this competition's score (`Q^2 * T`) that is **5.1x WORSE than our tape**
  (890^2*367,116 = 2.91e11 vs 1837^2*440,000 = 1.49e12), because Q^2 dominates. But the
  paper's locator-solve numbers (BM ~140k Toffoli vs synchronized EEA ~1.9M) confirm that a
  BM decoder *narrow enough* would beat our EEA; ours is already 890Q/367k T, so a BM decoder
  would need <= ~890Q and <= ~367k T to matter. Not buildable from our tape; recorded as the
  frontier direction.
* **arXiv:2602.15285 (Oct 2026)**: "Tensor Decomposition for Non-Clifford Gate Minimization" --
  algebraic minimisation of the CCZ/Toffoli count in CNOT+CCZ phase circuits via tensor
  decomposition over F2. This is the right tool for both open lines: the DQI's rank-42
  GF(2^12) multiply block (floor 23) and the chem loader product cover (188 today).
* **arXiv:2510.10967 (Khattar et al.)**: the competition's reference decoder is 1,893Q /
  5,725,108 mean T (verified by us on `sample_submission/dqi.kmb`); our tape is 2.1x narrower
  and 15.6x cheaper in T.

## 4t. Block-architecture probe (gendecomp, in flight 02:24)

The full-h replicated-vector test (dim W=0) does not close the shipped *block* architecture,
because a product with a partial h-mask contributes to the projection of R onto a 3-low-coordinate
block without being in R globally. `probe_block3.py` therefore computes, per 3-coordinate block B:
`V_L = {v : e_L (x) v in pi_B(R)}` for every nonempty L in the block (7 subsets), the pool of
chunk-vectors inside pi_B(R), and a greedy spanning set. The total term count over the 5 blocks
is the architecture's product count; 188 is the shipped cut/pairing count, and anything below
188 with an emitted plan would be a chem win (75 terms -> Toffoli ~150/loader -> chem ~215M ->
+2.4 GM). This is the decisive remaining measurement for the loader axis.

## 4u. Block-architecture probe: NEGATIVE (measured, jiyujia/qcc-chem-block3 + gendecomp)

Two independent computations agree. Per 3-low-coordinate block, `dim pi_B(R) = 75` and the
minimum number of chunk vectors `e_L (x) v` spanning it is:

| k | block 0 | block 1 | block 2 | block 3 | block 4 | total terms |
|---|---:|---:|---:|---:|---:|---:|
| 4 | 54 | 75 | 75 | 75 | 75 | **354** |
| 2 | 50 | 74 | 74 | 75 | 75 | **348** |
| agent (all k) | 42-55 | 35-75 | 35-75 | 35-75 | 35-75 | **375-376** |

So the block-restricted chunk-vector architecture needs **348-376 terms**, far worse than the
shipped cut/pairing's **188 products**. The shipped products pair *across* the five blocks
(l1/l2 masks span all 15 low coordinates), which the per-block decomposition cannot see.
**The loader axis is closed at 188** (the 150-cut / 188-product floor), and the only remaining
headroom is the weak loaders' +0.05..0.11 GM.

## 4v. DQI iteration axis: truncation probe FAILS (measured with base control)

`zhuating/qcc-dqi-algo-trunc2` (COMPLETE): cut the unmodified tape at depth-0 boundaries
(round-trip reproduces `575b043f` byte-exactly), then truncate.

| candidate | T | verifier |
|---|---:|---|
| control `575b043f` | 367,116.057 | **PASS**, 0/102,400 value errors, 0 phase |
| `P1` = last forward multiply cluster + wrap (-3,340 T, sha 35e4a7c6…) | 363,776 | **FAIL, value_errors 102,400/102,400** |

Every shot wrong => the trailing chunk is not identity => no k>=1 truncation can pass.
Both EEA passes run ~34 degree-driven rounds (forward +1 ladder 4->34; reverse ends with
the mirror ladder 34,34,33..,3), which is the minimum (degree 69 -> <35, >=1 per step).
**Iteration axis closed.** The only remaining DQI lever is the 12x12 GF(2) multiply rank
(42 -> 23, +1.99 GM ceiling), which needs the generator or a successful in-place patch
(`dqi_mult` line, running).
