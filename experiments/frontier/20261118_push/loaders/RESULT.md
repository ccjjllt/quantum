# Loader line, 2026-11-18 push — the chemistry angle-loader product count

Line: "a fundamentally cheaper chemistry angle loader". Account `ccjjllt_check`.
No Kaggle kernel was run by this line (see §8); everything below that is not marked
**[brief]** or **[model]** is a *local pure-arithmetic measurement* (GF(2) rank algebra and
the emitter's own 1232-row algebraic table check — no circuit simulation).

---

## 0. Bottom line

**The premise in `BRIEF.md` §"chem loader cuts" is arithmetically wrong, and the axis is
already at its ceiling.** The brief's *"algebraic bound 375 cuts -> 75 products -> 150
Toffoli per loader (2,250 total)"* comes from reading the per-block **nullity (30)** as if it
were the **rank**. Measured (all 15 loaders, three independent low bases each):

```
per-block matrix = 75 slices x 105 bits (3 low coords x 35 payload bits)
block rank       = 75  (identity low basis, and every random invertible basis)
block rank       = 74  (the stored minrank low basis of k2, k9, k10, k12, k14)
```

so the block-local cut space is `5 x (105-75) = 150` cuts (generic basis) or
`5 x (105-74) = 155` cuts (stored minrank basis) — **not 375**. Hence

```
products = (525 - cuts)/2  >=  188   (cuts <= 149 after the parity constraint)
Toffoli  = products + 75   >=  263        <-- the shipped k4..k8 value, exactly
```

The shipped best loaders (k4..k8, 263 Toffoli = 188 products + 75 computes = 149 cuts) sit
**exactly on the algebraic floor** of this architecture, not 1.45 GM away from it. The
invalidated hope was worth +2.72 GM (`loaders 2,250 -> GM 30.899`), so this correction matters
for planning: there is no large prize on this axis.

Realistic remaining headroom, measured: **80 Toffoli total = +0.103 GM** (§6), and even that
requires beating two searches that already failed.

---

## 1. Cost arithmetic reproduced (measured)

Command (`BUILD` in `emit_from_basis.py` already points at a directory holding
`submission.npz`, sha256 of `angle_words` `33e671e4a00ae869…` = the shipped table):

```
cd experiments/frontier/20261117_deep/chem/work/ds/code2
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python emit_from_basis.py 2 --outdir <tmp>
{"k": 2, "products": 196, "toffoli": 271, "qubits": 126, "shipped": 269, "delta": 2, "sum_cuts": 133}
```

* `Toffoli = products + 75` confirmed, with `75 = 69 high-cache CCX + 6 low-cache CCX`
  (the emitter report prints `high_cache: 69`; `num_qubits 126 = 11 + 40 + 69 + 6`).
* `products = (525 - sum_cuts)/2`: `(525-133)/2 = 196` ✓.
* The low-cache cost is *not* constant across loaders: the `calib_emit.json` k0 path reports
  `low_computes 11, num_qubits 128` (non-pure helper path). The shipped-per-loader cut counts
  in §2 assume 75 computes, which is what the relation `263 = 188 + 75` gives and what my own
  k2 emission reproduces; treat k0's 87 cuts as derived, not directly re-emitted.
* `emit_from_basis.py k>=9` fails on this table (`AssertionError` in `emit_plan.py:57`: the
  helper table `bit7^bit6` of word group 0 differs from groups 9..14), so the local emit path
  covers k=1..8 only. This is a property of the shipped table, not of the plans.

## 2. Measured per-loader state (Toffoli **[brief]**, cuts/products derived)

`computes = 75`, `cuts = 525 - 2*(Toffoli-75)`:

| k | 0 | 1 | 2 | 3 | 4-8 | 9 | 10-13 | 14 | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shipped Toffoli | 294 | 288 | 269 | 269 | 263 | 264 | 265 | 266 | **4,025** |
| ⇒ products | 219 | 213 | 194 | 194 | 188 | 189 | 190 | 191 | 2,840 |
| ⇒ cuts | 87 | 99 | 137 | 137 | **149** | 147 | 145 | 143 | 2,075 |
| measured ceiling (identity basis) | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 2,250 |
| measured ceiling (stored minrank basis) | — | — | 155 | n/a | n/a | 155 | 155 | 155 | — |

Log: `logs/probe_blocks.log` (identity / stored-plan / 3 random bases × 15 loaders).

Parity detail that matters: with a 150-cut ceiling `dim = 525-150 = 375` is **odd**, and
`dim = 2·products` must be even, so at most **149** cuts are usable ⇒ **188 products ⇒ 263
Toffoli**. k4..k8 are therefore *exactly* at the floor; the only way below is a low basis with
block rank 74 for that loader (155 cuts ⇒ dim 370 ⇒ 185 products ⇒ 260 Toffoli, −3).

## 3. Why a coarser block partition cannot buy the missing cuts (measured)

`products = Σ_p rank_p / 2`; a partition into larger blocks raises the nominal cut ceiling
(`blockdim − rank_p`), e.g. 2 blocks of 7+8 coords ⇒ 375 nominal cuts ⇒ 75 products. Measured
at **full saturation** (`logs/probe_parts_k4.log`, k=4, identity basis), counting the
`(block,form)×(block,form)` pairs whose joint constraint space still leaves an output vector
`v` — i.e. whether any product can exist at all:

| partition | block ranks | cuts at saturation | dim (=2·products) | nominal products | form-pairs with a candidate |
|---|---|---:|---:|---:|---:|
| **5 × 3 coords (shipped)** | 75,75,75,75,75 | 150 | 375 | 187.5 | **222** |
| 4+4+4+3 | 75,75,75,75 | 225 | 300 | 150.0 | **0** |
| 3 × 5 | 75,75,75 | 300 | 225 | 112.5 | **0** |
| 2 (7+8) | 75,75 | 375 | 150 | 75.0 | **0** |

So the "375 cuts" ceiling is not merely loose — it is **unreachable**: with blocks of ≥4 low
coordinates the cut constraints saturate the 35-bit output space for every form and *no product
pairing candidate exists at all*. Blocks of 3 coordinates are the only workable partition, and
that is the shipped design. (The 5×3 alternating-rank witness at saturation is 298/375 in a
sampled pool, which is why the descent has to drop a few cuts from 155 to 149 — consistent with
everything the previous session observed.)

## 4. The (h,l) address split (measured, closed)

`logs/probe_split_k4.log`, `logs/probe_split_pairs.log` (generalised `complete_words` /
`cross_tensor`, verified against the shipped 4-bit code path):

| split L | M | nh | determined slices | low coords | high-cache CCX | block ranks | cuts at saturation | products ceiling | form-pairs with a candidate |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 3 | 8 | 153 | 152 | 7 | **144** | 99,93,28 | 25 | 110.0 | 63 |
| **4 (shipped)** | 16 | 77 | 76 | 15 | **69** | 75×5 | 150 | 187.5 | **222** |
| 5 | 32 | 39 | 38 | 31 | **32** | 38,37×9,28 | 686 | 199.5 | **0** |

* L=5's attractive 32-CCX high cache is worthless: **0** pairing candidates at saturation, so
  its 231.5 (+ low-cache) estimate is *not* reachable.
* L=3 pays 144 high-cache CCX (saves 25 low compute) and its ceiling is 110 products ⇒
  ≥ 254 Toffoli before the low cache — worse than 263, and only 63 candidates.
* The split axis therefore cannot beat the 4-bit split. (These are ceiling numbers; the
  low-cache cost for L=5's 31 low monomials is an **estimate** ~26 CCX, never emitted.)

## 5. Row order of the table (measured, blocked at the emitter)

`logs/probe_perm.log`. Metric legality of row permutations is established by the parameter
audit line; this is the **emitter** side. The shipped loaders get 5 *free* low monomials from
the word helper `bit7^bit6`, whose table must decompose as `low[l] ^ high[h]`
(`emit_plan.separate_helpers` asserts it). Measured on the completed 1232-row table:

| permutation | rows moved | helper low⊕high OK | block ranks k4 / k2 |
|---|---:|---|---|
| identity | 0 | **true** | 75×5 / 75×5 |
| reverse two-body rows | 1,144 | false | 75×5 / 75×5 |
| sort two-body rows by word (per rho) | 1,132 | false | 75×5 / 75×5 |
| nearest-neighbour (Gray/TSP-like) per rho | 1,114 | false | 75×5 / 75×5 |
| random two-body | 1,143 | false | 75×5 / 75×5 |
| sort one-body rows 0..75 by word | 76 | false | 75×5 / 75×5 |
| random one-body rows | 76 | false | 75×5 / 75×5 |
| global 16-aligned low relabeling | 914 | false (only rows 1219,1223,1227,1231) | 75×5 / 75×5 |

Two independent reasons this axis cannot be priced or exploited cheaply:

1. **No signal on the cheap proxy**: the block-rank proxy is saturated at the maximum 75 for
   every ordering, so the product count can only be obtained by a full planner run per
   (ordering, loader) — the previous session measured 2,321 s for one loader on k2.
2. **Emitter blocker**: every non-identity permutation examined breaks the helper
   separability that supplies the low cache. Metric-legal permutations act inside 143-row rho
   blocks, which are not 16-aligned with the low groups (`76 = 4·16+12`), so they always
   scramble the low/high grid. A candidate would first need a rebuilt low cache (no helper
   trick: ~11 rather than 6 CCX) before it could even be emitted.

## 6. Bound on the remaining upside (proven vs model)

Proven ceilings for the shipped architecture (measured ranks):
`products >= 188` (generic basis, parity included) / `products >= 185` (needs block rank 74).
Hence `Toffoli >= 263` / `>= 260` per loader.

**[model]** (pure arithmetic: `T = 2·ΣToffoli + 6,662 − 6`, calibrated so the shipped point
reproduces `T = 14,706`, `chem = 294,643,137.73`, `GM = 28.180659` exactly):

| scenario | Σ loader Toffoli | T_total | chem cost | GM | ΔGM vs shipped |
|---|---:|---:|---:|---:|---:|
| shipped | 4,025 | 14,706 | 294,643,137.73 | 28.180659 | — |
| **weak loaders pushed to 263** (k0,k1,k2,k3,k9..k14) | 3,945 | 14,546 | 291,437,446.04 | 28.283608 | **+0.10295** |
| all 15 at 260 (needs a rank-74 basis for every loader) | 3,900 | 14,456 | 289,634,244.46 | 28.342183 | +0.16152 |
| brief's invalidated target (all 15 at 150) | 2,250 | 11,156 | 223,516,853.29 | 30.899148 | +2.718 |

The first row of the delta table is the *only* remaining loader-axis prize and it needs
k0/k1 pushed from 87/99 to 149 cuts, which the prior session could not do (5 seeds each, no
rank-74 basis found). A structural explanation for why k0/k1 are different, measured here:
per-coordinate projection ranks of their target are `[35]*15` (no relations at all, so the
minrank/`find_third` attack has nothing to find), versus
`[35,35,29,35,29,29,28,35,29,29,28,29,28,28,28]` for k≥4 (whose 5 helper relations are exactly
what the attack exploits). So k0/k1's gap is structural, not a search-budget shortfall.

## 7. What is proven, what is estimated

**Proven (local GF(2) algebra, deterministic):**
* `products = (525 − cuts)/2` and `Toffoli = products + 75` (reproduced end to end for k2:
  271 = 196 + 75, 126 qubits ≤ 128).
* Block ranks 75 (identity/random bases) and 74 (stored minrank bases) for every loader
  examined; block dim 105 ⇒ cut ceiling 150/155, **not 375**.
* Parity ⇒ 188 products / 263 Toffoli is the floor for a generic basis; 185/260 needs rank 74.
* With blocks of ≥4 low coordinates, or with the L=5 or L=3 split, the pairing candidate set at
  saturation is empty/insufficient (counted exactly, §3/§4).
* Every examined non-identity row permutation breaks the helper low⊕high decomposition.
* `rank(target) = 75` for all 15 loaders, so `products >= 38` for *any* product architecture —
  the machinery's 188 is 5× that floor, but §3/§4 show the cut/pairing route cannot approach it.

**Estimated / not measured here:**
* k0's cut count (87) is derived from 294 under `computes = 75`; its own emission uses
  `low_computes = 11` in `calib_emit.json`, i.e. a different low-cache path.
* All GM deltas (pure arithmetic on the official cost formula; nothing re-verified).
* The low-cache CCX count for the L=3/L=5 splits (never emitted).
* Any product count under a row permutation (no planner run was spent, by design).
* No new loader circuit was emitted, so **no PASS is claimed for this line**.

## 8. Status / what was not run

* **No Kaggle kernel was started by this line** (the coordinator closed the axis before a
  candidate existed; no circuit was produced to verify). All circuits in the numbers above are
  the already-verified shipped ones from `BRIEF.md`.
* No new plan, no `.kmx`/`.kmb`, no submission change, no git push.
* Verdict: **the 263 floor cannot be beaten by the cut/block architecture**, and the three
  remaining structural knobs (block partition, (h,l) split, row order) are each closed with the
  measurements above. The loader axis is worth at most **+0.10 GM** and probably less.

## 9. Artifacts

All under `experiments/frontier/20261118_push/loaders/`. sha256 in `logs/sha256.txt`.

| file | what it is |
|---|---|
| `common.py` | shared loaders: shipped-table path, GF(2) rank helpers, code2 import shim |
| `probe_blocks.py` → `logs/probe_blocks.log` | per-block rank 75/74 for all 15 loaders, 3 bases each |
| `probe_parts.py` → `logs/probe_parts_k4.log` | pairing candidates at saturation vs block partition |
| `probe_split.py` → `logs/probe_split_k4.log` | L=3/4/5 split: nh, high cache, ranks, cut ceiling |
| `probe_split_pairs.py` → `logs/probe_split_pairs.log` | candidate availability per split (L=5 → 0) |
| `probe_perm.py` → `logs/probe_perm.log` | row-permutation legality for the emitter, block-rank proxy |
| `probe_rows.py` | row-sparsity probe (K(V)=Σ dim row_i(S)) — exploratory, not used in a claim |
| `logs/emit_repro_k2.log` | `emit_from_basis.py 2` reproduction: 196 products + 75 = 271, 126 qubits |
| `logs/sha256.txt` | sha256 of every script and log above |
