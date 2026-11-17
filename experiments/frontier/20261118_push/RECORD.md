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
