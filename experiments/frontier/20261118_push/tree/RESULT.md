# tree_edges axis — CLOSED (no win)

Line: choose a better `tree_edges` so the 15 ANGLE loaders get cheaper.
Account: `jiyujia`. **Zero Kaggle kernels were pushed** for this line — every
measurement below is either the official verifier code read as pure numpy
(small arithmetic), the chem planner's GF(2) algebra, or `kickmix` metadata
parsing of the shipped `.kmb` files. Nothing was simulated, nothing submitted,
nothing to cancel on the account.

Verdict: **no tree, edge order or sign representative beats the shipped table.**
Every legal alternative I could construct is *worse* in the loader floor by
+81 … +439 products (Σ over 15 loaders), so the axis is closed with the
distribution below rather than with an opinion.

---

## 1. What is actually free (verified)

`verifiers/dfthcsos/scoreinfra/dfthc_math.py:reconstruct_u_vectors` applies the
75 ordered Givens rotations to `e_0`. Reading `verify.py`:

* `tree_edges` comes from the submitted `submission.npz` (`load_tree_edges`).
* The submitted `U` is used **only** for `np.shape(params["U"])[-1] == ORBITALS`
  (`load_inputs`/`native_inputs` build everything from `W`, `H2_I`, the baseline
  `Hsym_lower`/`H1_I` and the words). So Λ and the energy are functions of the
  **word table only**, not of `tree_edges` and not of the npz `U` values.
* The heuristic cost model (`SpinFreeData_V1`) never sees the tree; only
  `angles_toffoli` (= per-shot mean over `U_T`/`U_T^†`, i.e. `2 * Σ loader`)
  moves. Q is untouched: the shipped loaders are at 128 qubits and
  `angles_temporary = 77 < outer/inner temporary`, so Q = 427 is inert.

Three re-encodings keep `decode(words)` fixed and therefore cannot move
error_1 / error_2 / Λ / λ_eff:

| lever | residual `‖decode−V‖_F` | note |
|---|---:|---|
| exact inverse (reverse-order Givens sweep) | 2.0e-14 | `common.encode`; `decode(encode(V))−V` max abs 6.7e-16 |
| per-(row,edge) sign branch (θ → θ+π, exact grid point) | 2.1e-14 | `signrules.encode_rule` |
| edge permutation that keeps every node's child order | **0.0** | `perms.value_preserving_extension` — bit-identical decode |

The last one is the coordinator's column-permutation lever, and it is real: the
15 batches `words[:,5k:5k+5]` change while the U is bit-identical. (A permutation
that also reorders siblings does *not* preserve U: measured residual 0.63 — the
rotation sees different amplitudes, so "permute the edges" is only free inside
the value-preserving class.)

Sanity of the shipped table itself: row norms 1 ± 2.2e-16, and its decoded
two-body rows equal the npz `U` up to row signs (|overlap| = 1.000 for all 1144
rows, unique argmax; 286/1144 rows are sign-flipped, which is immaterial because
`X = Σ w u uᵀ` and `error_1`'s |overlap| matching are sign-blind).

## 2. The cheap proxy, and how it compares to the true ceiling

`work/proxy.py` computes, per loader, (a) the per-coordinate forced-cut count and
(b) the nullspace dimension of the 75 determined high slices inside each of the
five 3-coordinate blocks, then

```
ceil_products_k = (525 − Σ_blocks (forced + nullspace)) / 2
```

This is a hard floor on the loader's product count (products = (525−cuts)/2).

Measured on the shipped words: the 75-slice block ranks are exactly
`[75,75,75,75,75]`, so the nullspace term is exactly `[30,30,30,30,30]` = 150
cuts — identical to the loader line's independent measurement of the structural
ceiling `[75,75,75,75,75]` → 150 cuts → 187.5 products → ≈256.5 Toffoli.
The extra `forced` per-coordinate cuts are what put the shipped's own floor
*below* that (152 products for 11 loaders).

Shipped table floors: `[187,187,160,160,152×11]`, Σ = **2366**.

## 3. Measured per-loader numbers (shipped, exact)

`kickmix.Circuit.from_file(...).operation_statistics().num_toffoli_like` on the
15 shipped `.kmb` (metadata read, no simulation), sha256 of the package listed
below:

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | Σ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Toffoli | 292 | 287 | 269 | 269 | 263 | 263 | 263 | 263 | 263 | 264 | 265 | 265 | 265 | 265 | 266 | **4022** |
| products | 212 | 212 | 194 | 194 | 188 | 188 | 188 | 188 | 188 | 189 | 190 | 190 | 190 | 190 | 191 | 2892 |
| floor | 187 | 187 | 160 | 160 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 2366 |
| achieved − floor | 25 | 25 | 34 | 34 | 36 | 36 | 36 | 36 | 36 | 37 | 38 | 38 | 38 | 38 | 39 | |

`toffoli = products + 80` (k=0) or `+75` (k≥1); Σ = 4022 and
`T = 2·4022 + 6662 = 14706`, which reproduces the shipped `toffoli_count` exactly.
So the *achieved-minus-floor* gap (25–39 products) is the only headroom left, and
it is the plan search (the loader-cuts axis), not the tree.

## 4. Tree / order / sign search (measured)

Objective: `Σ_k ceil_products` (lower is better). One evaluation = 0.11 s, so
thousands of candidates were priced; only the exact emitter run on the shipped
table was expensive (and was not needed — see §5).

**(a) 263 trees**, canonical encoder, same decoded U (`sweep_big.json`) —
`floor_total` min/median/max:

| family | n | min | median | max |
|---|---:|---:|---:|---:|
| bushy (attach to early vertex) | 50 | **2687** | 2728.5 | 2762 |
| attach (uniform parent) | 50 | 2732 | 2760.0 | 2784 |
| prufer (uniform random tree) | 50 | 2758 | 2781.0 | 2800 |
| deep (catenary-ish) | 50 | 2772 | 2790.5 | 2805 |
| heap relabelling (random orbital permutation) | 40 | 2779 | 2782.0 | 2787 |
| chain relabelling | 20 | 2779 | 2790.0 | 2796 |
| chain (identity order) | 1 | 2764 | — | — |
| star (identity order) | 1 | 2777 | — | — |
| **shipped tree, canonical encoder (control)** | 1 | 2746 | — | — |
| **shipped tree + shipped words (reference)** | 1 | **2366** | — | — |

all 263: mean 2769.6, sd 24.9, min 2687, max 2805. **Every tree is ≥ +321 above
the shipped table.**

**(b) Free value-preserving edge permutations of the shipped table**
(`perm_search.json`, `perm_greedy.py`) — decode bit-identical (residual 0.0):

* 12 random permutations: floors 2447–2454.
* greedy loader-by-loader choice of the 5-column batches (25 candidates per
  stage, 2 restarts): floor **2447**, per-k `[176,176,165,160,165,165,160×9]`.
* the shipped order: **2366**, per-k `[187,187,160,160,152×11]`.

So randomising the batches costs +81 and an explicitly greedy batch choice also
lands at +81: the shipped BFS order is better than anything I could reach.

**(c) Sign representatives** (`conventions.py`, `climb_signs.json`): canonical
'pos' 2746, 'cos_pos' 2787, random per-row/per-edge sign patterns 2738–2747,
hill climb from a bad start converged to 2738. The trainer's own representative
(2366) beats all of them. Recovering that representative from the words failed
(the per-edge sign disagrees across rows at ~50 %), and 29 % of its entries differ
from the canonical encoding by even offsets ±2…±16 in the last-significant
angles — i.e. the shipped table is not a naive quantisation, it carries a word
refinement that the loaders benefit from.

## 5. Planner probes (why no emission was attempted)

Local GF(2) planner (`plan1.py`, `code2/plan_loaders.try_plan`: BlockPlan +
descend_smart + padding solve; no circuit built):

* shipped table, k=9 and k=4, 120 s budget: `max cuts 150 -> no perfect pairing`
  (the shipped plans need ≈600 s + local search to reach 147 cuts / 188 products).
* canonical re-encoding of the same U, k=4, 420 s budget: **no plan found**
  (log: `canon_control.log`), against the shipped table's measured 188 products.

Since (i) every alternative table has a floor +81 or more above the shipped's and
(ii) the planner already cannot reach the shipped floor at a comparable budget,
an emitted alternative could not come in under 4022. No loader was emitted and no
verifier run was spent.

## 6. Size of the prize (scripts/gm.py, pure arithmetic)

`python3 scripts/gm.py --current` → GM 28.150932 (chem 294,643,137.73 =
46.9217168 · 14706 · 427). Chem cost is linear in T, so a loader saving of
Δ Toffoli changes GM by `(T/(T+Δ))^(1/3)`:

| loader saving | T | GM | ΔGM |
|---:|---:|---:|---:|
| −50 Toffoli | 14656 | 28.182909 | +0.032 |
| −80 (the whole remaining loader headroom) | 14626 | 28.202165 | +0.051 |
| −174.5 (absolute structural ceiling, every loader at 187.5 products) | 14531.5 | 28.263166 | +0.112 |

So the *entire* loader axis is worth at most ≈ +0.11 GM, and the tree axis
cannot deliver even that: the shipped table already sits 81–439 products below
every tree/order/sign alternative I could construct, and its achieved counts
(188–191 for 11 loaders) are 0.5–3 products off the 187.5 structural ceiling.

**Closed.** The measurable loader headroom is the plan search (achieved − floor =
25–39 products/loader), which belongs to the loader-cuts line, not to
`tree_edges`. `helper_low_high_ok` also breaks under non-identity row
permutations (loader line's finding), so even the residual is not reachable by
reordering rows.

## 7. Reproduce

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum
PY=.venv/bin/python; W=experiments/frontier/20261118_push/tree/work

# 0. the shipped package used as the source of truth (a73b25d2)
shasum -a 256 $W/build/submission.npz        # a73b25d27caec65d…
$PY $W/sanity.py                            # decode/shape/norm sanity
$PY $W/sanity2.py                           # npz U == decode(words) up to row signs

# 1. exact inverse + sign branches + value-preserving permutations
$PY $W/signrules.py                         # sign conventions, residuals
$PY $W/perms.py 21 12                       # 12 free permutations, residual 0.0

# 2. loader floor proxy
$PY $W/proxy.py                             # shipped floors [187,187,160,160,152x11]
$PY $W/conventions.py                       # conventions vs shipped
$PY $W/sweep_big.py                         # 263 trees (sweep_big.json)
$PY $W/perm_greedy.py 5 25 2                # greedy batch order -> 2447

# 3. shipped per-loader Toffoli (metadata only)
$PY -c "import kickmix as km,glob;fs=sorted(glob.glob('artifacts/20261118_inv_sweep/ds/junmiaotiao_qcc-frontier-20261117r/dfthcsos/angle_k_*.kmb'),key=lambda p:int(p.split('_k_')[1].split('.')[0]));print([km.Circuit.from_file(f).operation_statistics().num_toffoli_like for f in fs])"

# 4. planner probes (local GF(2), ~2 min each)
$PY $W/plan1.py 9,4 120
$PY $W/canon_control.py 420 4

# 5. GM arithmetic
$PY scripts/gm.py --current
```

## 8. Artifacts

All under `experiments/frontier/20261118_push/tree/work/`; `SHA256.txt` holds:

| file | sha256 | what |
|---|---|---|
| `build/submission.npz` | `a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3` | shipped chem npz (source of U/tree/words) |
| `sweep_big.json` | `643fd5687142370b8da4d7910581f0e225290e21a9eafbeae2a6858fec53c8ba` | 263-tree floor distribution |
| `sweep0.json` | `ed37b15773e7e461b42af7958a66dfca5bccc7bdca45e34fc84e579116ba8d75` | first 16 tree/order variants |
| `perm_search.json` | `000a92ea7626037260961a2e78bdf96995b5ca5b9343900e4e5d268f49c5c42e` | 12 free permutations |
| `perm_greedy.json` | `336fc6773ae81efb5f991eeae6f2ea867d4432842ab2fca0b99d77d20e2198e8` | greedy batch order, floor 2447 |
| `perm_greedy_order.npy` | `e7a7f07865ca8313ff53ebf74bb95bdb98bae29fcb68818921760ceaafde32c2` | that 75-edge order |
| `climb_signs.json` | `88f61c4c717780061518f57dbac0762a5bf292a90da3ba5f9631c93f2971c635` | sign hill-climb table + signs |
| `ship_signs.npy` | `df6c8fe2548a263083315bb995d1b35194469df514b8223a5a3fe1e6aaccf1b8` | recovered shipped sign branches |
| `proxy.py` | `8944c6aaf4c4577e4ff4303e68ece4d83b97b3c69657e6be64eb1b9ceb22d628` | loader-floor proxy |
| `common.py` | `14b20de6f9b192e582dacf18701f22ea6cfbb6916e82fc850686006411ae17ed` | decode / exact inverse / tree validity |
| `signrules.py` | `84f5cb05ea1d86f2668e9612fd84afa505285c622da15f983928fafd21e1f961` | per-(row,edge) sign encoders |
| `perms.py` | `e49581d1c0d28565e4e8518b6ebd753ed0db1ecbb19b6e53fda90a38fb8b29ab` | value-preserving permutations |
| `perm_greedy.py` | `0dfb29100fd3527f6751bb449415b1e5b05ba49a445c07cda5a1025117032f97` | greedy batch order |
| `plan1.py` | `d5097cda453356de9885d52b9030a0ed9a5e3776fe5612a2f2b8069a73d8f9ab` | local GF(2) planner probe |
| `conventions.py` | `d628697ac79e4847be79bec6df8acbac846ec2f40abb464c74acb40e4bbbac06` | sign-convention comparison |
| `sweep_big.py` | `f3bd19e1604b0dc3d0b9d28b837fe5ddbfbc28d65453beca787971c2e5e49113` | 263-tree sweep driver |

`work/code2/` is a private copy of `experiments/frontier/20261117_deep/chem/work/ds/code2/`
(the other line's directory was never written to). No shippable npz/loaders
directory is left because no tree won.

## 9. Caveats

* The floor proxy is a *lower bound*; the achieved counts are 25–39 above it.
  The verdict does not rest on the proxy alone: the free-permutation results are
  exact (bit-identical U), and the two planner probes show the search cannot
  reproduce even the shipped floor at a comparable budget.
* `ceil_products` uses `(525 − Σcuts)/2` with integer division; odd cut totals are
  excluded, so floors are ±0.5 products.
* Not measured here: an actual emitted + officially verified alternative package.
  It would require ≈10 min/loader of planner time and, on the floor evidence,
  cannot beat 4022.
