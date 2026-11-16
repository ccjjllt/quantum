# CODE2 — the code/gauge axis on the 4,025 set is closed; what is actually left on the table

**Status: final negative, search stopped 2026-11-16 evening UTC. No candidate package, no
submission.** The 4,025 Toffoli/pass set (`marculera/dfthc-c44-build`) stands. See §0 and §9.

Date: 2026-11-16 (evening UTC). Chemistry only. **No circuit simulation was run locally**:
everything below is classical GF(2)/linear algebra on `submission.npz`, plus *reading*
`kickmix` gate counts (static, no shots). The only simulation anywhere in this note is the one
Kaggle CPU verifier run recorded in §6.

Assets used
* table + circuits: `marculera/dfthc-c44-build` (4,025 Toffoli/pass, the published best),
  local copy `…/qcc_push/marculera_ds/`, `submission.npz` sha256 `302e608c…32e2e9`.
* shipped planner/emitter: `…/qcc_push/syed_v12/src/dfthcsos_source/{compiler,plans}`,
  ported into `code2/{compiler,planner.py,minrank.py,lowbasis.py,compile_basis.py}`
  (only the path constants were edited: `ROOT`/`V18`/`sys.path`, and
  `prove_loader_branches` replaced by `None` — that module is not shipped and is the *proof*
  harness, not the planner).

## 0. Verdict

1. **The code axis (bits 0–2) is closed, measured, not argued.** Every legal code change is a
   value change of ±π/128…±π/32 on whole columns, and the table is a cancellation tuned to
   7·10⁻⁵ relative. A single legal bit-0 code flip on **one** of the 75 columns moves
   `error_1` from 20.0 mHa to **81–1028 mHa** and `error_2` from 20.0 to **62–239 mHa**
   (gates: 20 mHa). The one legal XOR-code flip tested: `error_1` 852 mHa. There is no code
   assignment at (8,143,44)/1,220 rows that survives the gates without a fresh weight refit.
2. **The π-gauge axis is closed by construction.** Exactly one single-column π-flip is an exact
   gauge on this table: **column 0** (the root of the Givens tree) — metrics bit-identical.
   Every other single-column flip destroys them (`error_1` 1,717–3,694 mHa). A π-flip adds 128
   to the word, i.e. it flips **bit 7 only**, and bit 7 is never a Toffoli output in this loader
   family (it rides on the polarisation helper, written by CX/X only). So the entire gauge
   group is *T-inert*: it cannot move a single gate.
3. **Plan axis: the 4,025 set is at the family floor for 5 of 15 loaders and the shipped
   planner cannot reach the others' shipped counts.** The cut ceiling of the 5×3-block family is
   150 = 5×30 per pass (all five 3-dim blocks have slice rank 75 on this table, measured on
   coordinate blocks *and* on 60 random 3-dim subspaces), i.e. **149 usable cuts = 188 products
   = 263 Toffolis is the floor**. Loaders 4–8 are exactly there (189 products + a 68-high cache).
   Re-running the shipped machinery on this table gives at most 145 cuts (190 products) for the
   loaders that have slack — a *tie or a loss*, never a win (table in §4).
4. **The last six loaders cannot be re-emitted with the shipped emitter at all** (§5): batches
   9, 10 and 14 have `bit7 XOR bit6` different from their predecessor, and batches 11–13 use a
   helper whose five low patterns are not independent modulo affine functions, so the shipped
   6-AND low cache does not apply. This is the concrete missing piece, not a search limit.
5. Consequently **no candidate package exists and nothing was submitted**; the 4,025 set stands.
   The one Kaggle run made here was a *negative control* and it FAILed as predicted (§6).

## 1. What the 4,025 set actually spends (exact per-loader census)

`T_loader = (#products with non-zero high support) + high_cache + low_cache`, and
`qubits = 51 + high_cache + low_cache` (11 selection + 5×8 word + the ancillas). Reading the
shipped `angle_k_*.kmb` with `kickmix` (static counts only) gives the qubit column below, and
`solve` of the two equations gives the rest. `products = (525 − Σcuts)/2`.

| k | T (official) | Q | cache | high | low | products | Σcuts | note |
|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 0 | 294 | 128 | 77 | 69 | 8 | 217 | 91 | legacy maoxin-based, windowed emitter |
| 1 | 288 | 126 | 75 | 69 | 6 | 213 | 99 | legacy maoxin-based |
| 2 | 269 | 125 | 74 | 68 | 6 | 195 | 135 | |
| 3 | 269 | 125 | 74 | 68 | 6 | 195 | 135 | |
| 4–8 | 263 | 125 | 74 | 68 | 6 | 189 | 147 | **at the floor** |
| 9 | 264 | 126 | 75 | 69 | 6 | 189 | 147 | |
| 10 | 265 | 126 | 75 | 69 | 6 | 190 | 145 | |
| 11–13 | 265 | 125 | 74 | 68 | 6 | 191 | 143 | |
| 14 | 266 | 126 | 75 | 69 | 6 | 191 | 143 | |

Σ products = 2,908, Σ cache = 1,117, total 4,025 by construction. Floor for every loader:
263 (= 188 products + 69 + 6, or 189 + 68 + 6; 262 would need 149 cuts *and* a 68-high cache at
the same time, and no perfect 149-cut state was found at all here). Remaining headroom in this
family: k9 −1, k10 −2, k11–13 −2 each, k14 −3, k2/k3 −6 each, k1 −25, k0 −31.

## 2. The code family of this table, measured per loader

A relation is a *free forced cut* for monomial `m` if the 5 output bits in that relation are
zero at every high slice h = 1…75. Census over the 11 non-linear low masks (masks 3,5,6,7,9,
10,11,12,13,14,15) and the 5 cubic masks (7,11,13,14,15):

| loader k | per-word bit-0 codes | XOR-of-five bit-1 | XOR-of-five bit-2 (cubic only) | forced cuts |
|---|--:|--:|--:|--:|
| 0, 1 | 0 | 0 | 0 | 0 |
| 2, 3 | 11/11 | 0 | 0 | 55 |
| 4–14 | 11/11 | 11/11 | 5/5 | 71 |

This reproduces the published code description exactly (bit 0 affine per word from batch 1 on,
XOR-of-five affine at bit 1 and quadratic at bit 2 from batch 3 on) and it is why k0/k1 are the
expensive loaders: their deltas carry no code at all, so their plans have no forced cuts.

## 3. Why no code change can be spent (measured)

Metrics are a function of the word table only (θ/π = word/128, decoded on `tree_edges`); baseline
`e1 19.9992 mHa, e2 19.99997 mHa, Λ 283.2165, E_gap 3.914902 (floor 3.914898),
λ_eff 46.927643`. One column out of 75, one legal code unit:

| change (one column) | e1 mHa | e2 mHa | λ_eff |
|---|--:|--:|--:|
| baseline | 19.9992 | 19.99997 | 46.9276 |
| bit 0 constant (col 0) | 1028.20 | 239.48 | 60.213 |
| bit 0 constant (col 7) | 502.90 | 118.51 | 50.677 |
| bit 0 constant (col 37) | 265.11 | 69.82 | 47.768 |
| bit 0 constant (col 74) | 81.04 | 62.12 | 46.943 |
| bit 0 on the affine form `l_0` (col 37) | 168.98 | 49.94 | 47.344 |
| XOR-of-5 bit 1 on `l_1` (batch 7) | 851.90 | 193.41 | 52.935 |
| XOR-of-5 bit 2 on `l_0 l_1` (batch 7) | 1226.18 | 245.42 | 57.079 |
| π-flip (bit 7) col 0 (**gauge**) | **19.9992** | **19.99997** | **46.9276** |
| π-flip (bit 7) col 37 | 3694.44 | 1135.35 | 74.786 |
| π-flip (bit 7) batch 0 (cols 0–4) | 6572.82 | 2676.55 | 129.274 |

All 75 single-column π-flips were scanned: **only column 0 is an exact gauge** (metrics equal to
1e-12). Column 0 is the Givens root, so its flip negates every leaf and every `uu^T` is
invariant — the textbook π-gauge. It changes nothing else: β = 8 puts the word on a 1/128 grid of
θ/π on [−1,1), so θ→θ+π is word→word+128, i.e. **bit 7**, and the loader never computes bit 7 as
a Toffoli (it is the polarisation helper: `CX`/`X` only, `emit_plan.py` lines 52–78, 126–137).
Hence the gauge is free *and* inert: it cannot buy a gate.

The conclusion is structural, not just empirical: the codes at bits 0–2 live *inside* the loaded
7 bits, they are exactly the values the metric measures, and the gates are already at
19.9992/19.99997 of 20. A code assignment that differs in even one column, in one block of 16
addresses, is a different angle table and fails.

## 4. The plan axis, measured with the shipped planner on this table

Two routes, both run per loader on the marculera words:

* **identity low basis** (`plan_screen2.py`/`plan_ident.py`): 40–60 partitions of the 15 low
  monomials into 5 triples, screened by the saturation gap (span − dim of the pair columns at the
  full annihilator), then `planner.top_down` + `planner.local_search`.
  Best: **119–141 cuts** depending on partition (k9 141, k2/k3 133, k1 85).
* **rank-74 low basis** (`plan_basis.py` = the author's own `compile_basis.plan_one` with
  `minrank.find_basis` + `lowbasis.transform_target`): `full` = 31 per block. Best perfect
  states: **145 cuts (190 products)** for k9, k10, k12, k14; k2/k3 133 (196 products);
  k11/k13 seed 7 found no perfect pairing on the descent path.

Against the census of §1 that is a **tie or a loss for every emittable loader**:

| loader | shipped products | my best products | my T = products+75 | shipped T | Δ |
|---|--:|--:|--:|--:|--:|
| 2 | 195 | 196 | 271 | 269 | +2 |
| 3 | 195 | 196 | 271 | 269 | +2 |
| 9 | 189 | 190 | 265 | 264 | +1 |
| 10 | 190 | 190 | 265 | 265 | 0 |
| 12 | 191 | 190 | 265 | 265 | 0 |
| 14 | 191 | 190 | 265 | 266 | −1 but not emittable (§5) |
| 4–8 | 189 (+68 cache) | ≥189 | ≥264 | 263 | ≥ +1 |

`climb_cuts.py` (600 s of swap search from the 145-cut perfect state of k12) found no move at
all: 145 is a local optimum of that search. The shipped 147-cut states of k4–9 are not reachable
from the states this code finds.

An exact check of those four 145-cut plans (`basis_plan_k{9,10,12,14}.json`) also rules out the
cache route as a rescue: every one of them has 190 non-trivial products, **zero** low-only
products, and needs **all 69** high monomials of weight ≥ 2 (nothing is missing, so no 68-high
cache is available for them):

```
k9  190 pairs, 190 non-trivial, needed high monomials of weight>=2: 69   -> T 265 (shipped 264)
k10 190 pairs, 190 non-trivial, 69                                        -> T 265 (shipped 265)
k12 190 pairs, 190 non-trivial, 69                                        -> T 265 (shipped 265)
k14 190 pairs, 190 non-trivial, 69                                        -> T 265 (shipped 266)
```

**Do not read the 190-product results as a 3-gate win.** The shipped k9/k10/k14 already have
189/190/191 products (a *cache* of 75, not 68); their T is 264/265/266. 190 products is a tie at
best, and the only one-gate win it contains is k14 — which the shipped emitter cannot build (§5a).
The 4-gate expectation (`T −24`) would need four loaders at 189 products *and* a 68-high cache,
i.e. 147 cuts on four loaders — not reached by any run here.

## 5. The two hard blockers (exact, reproducible)

**(a) The helper convention changes at batch 9.** This loader family reconstructs bit 7 from
`helper = bit7 XOR bit6`, which must therefore be the *same* function for a batch and its
predecessor (the loader then only loads the delta's low 7 bits and gets bit 7 for free). Measured
on the shipped table:

```
helper(batch k) == helper(batch k-1):   k = 1..8  yes (0 differing rows)
                                        k = 9     305 differing rows
                                        k = 10    304
                                        k = 11..13 yes (0)
                                        k = 14    304
```

`emit_plan.emit` asserts the stronger form (both equal batch 0's table, lines 54–57), and the
6-AND low cache (`low_helper_cache.synthesize`) asserts the five low helper patterns are
independent modulo affine functions — which also fails for batch 11's table:

```
AssertionError: Five helpers must be independent modulo affine functions for six ANDs
```

So loaders 9, 10, 14 are **not expressible** by the shipped emitter (a nonzero delta-helper would
have to be loaded inside the loader, and the low cache has to be rebuilt from the right table),
and 11–13 can be forced through only by masking batch 0 with batch 11 (a tie anyway). Whatever
marculera used for the last six loaders is a different emitter; it is not in this tree.

**(b) `angle_k_0` needs its window schedule.** `emit_k0.emit` requires `state['windows']`, a
literal physical schedule (`compiler/k0_windows.json` is one instance: 22 entries with
`product`, `qubit`, `controls`, `active` bound to the shipped product set). The generator that
builds that schedule for a *new* product set is not shipped either, so k0's 31-gate headroom is
out of reach even though its plan is cheap to find.

Also confirmed: the syed_v12 `plans/` belong to a **different table** (U, W, H2_I, tree_edges and
90,481 of 91,500 words all differ from the marculera build), so they cannot be transplanted.

## 6. Verification actually run (and only this)

Kaggle CPU kernel `zhuating/qcc-chem-code2-mix-verify` (private, no internet,
`enable_gpu: false`), dataset `zhuating/qcc-chem-code2-mix-c44`, unchanged official
`dfthcsos/verify.py`, default salt, 78,080 shots, on a 15-loader package built from **marculera's
`submission.npz` + 11 shipped `.kmb` + 4 circuits emitted locally from the syed plans**:

```
FAIL  AssertionError: error_1 = 61130.5490 mHa > 20 mHa; error_2 = 11659.1079 mHa > 20 mHa
```

That was the intended negative control: those four plans were built for another word table, so
the loaders load the wrong words. It proves (i) the mixed-package route itself is accepted by the
verifier's register/word machinery — it reached the metrics stage — and (ii) nothing can be
transplanted across tables. It is **not** a candidate and it is not submitted.

No other verification was run, because no candidate beat 4,025.

## 7. What would actually be needed for ≤4,023

1. **The last six loaders' emitter** (the delta-helper load + the low-cache rebuild). That alone
   unlocks k14 = 265 (−1) with the 145-cut plan already in `basis_plan_k14.json`, and k10/k12
   ties. Still not ≤4,023.
2. **147 cuts on k11 + k12 + k13** (189 products + 68 high + 6 = 264 each, −3 total). Needs a
   stronger matroid-parity search than `descend_smart`/`local_search` reach here (`rank_climb`
   at fixed count cannot add cuts; the swap search stalls at 145).
3. **The high-subspace cache generator** (`high_cache_plan`): it is worth exactly 1 gate on every
   loader whose products do not need one of the 69 high monomials, and it is what separates 263
   from 264 on k4–8 and k11–13.
4. **k0/k1**: the windowed k0 schedule generator, and for k1 a loader family that handles a
   delta with no code at all (the 5×3-block planner returns 85 cuts there versus the shipped 99).

## 8. Files (this directory)

| file | what it does |
|---|---|
| `calib_emit.py` | re-emits the syed plans locally (calibration: 4,074 vs the shipped 4,025 — different table) |
| `code_probe.py`, `code_probe.json` | the code/gauge metric probe of §3 |
| `code_census.py` | the per-loader code census of §2 |
| `rank_census.py` | block-rank census: 75 in every 3-dim block, coordinate or random |
| `plan_loaders.py`, `plan_screen.py`, `plan_screen2.py`, `plan_ident.py` | identity-basis partition/descent searches (§4 first bullet) |
| `plan_basis.py`, `compile_basis.py`, `minrank.py`, `lowbasis.py` | the author's rank-74 pipeline ported to this table (§4 second bullet) |
| `climb_cuts.py` | fixed-count-cut swap search from a perfect state |
| `emit_from_basis.py` | plan JSON → literal plan → `.kmx` (the `emit_plan` path, without the unshipped proof) |
| `make_mix.py`, `ds_mix/`, `k_mix/` | the §6 negative-control package, dataset and kernel |
| `basis_plan_k*.json`, `screen_plan_k*.json`, `ident_k1_*.json` | every plan state found, with cuts, low-basis rows, padding solution |

Reproduction of the decisive measurement (no simulation, ~10 s):

```bash
cd experiments/frontier/20261116_push/chem/code2
uv run python code_probe.py      # §3 table
uv run python code_census.py     # §2 table
```

## 9. Final status (stop record)

The search was stopped here on instruction. State at stop:

* **k9, k10, k12, k14** each have a stored perfect plan at `Σcuts = 145` (190 products, all
  non-trivial, all 69 high monomials needed). Against the shipped census of §1 that is
  k9 +1 (264), k10 ±0 (265), k12 ±0 (265), k14 −1 (266 → 265). **Only k14 is a win, and only by
  one Toffoli, and it is not emittable** (delta helper ≠ 0, plus the low-cache independence
  failure of §5a). So the group is worth 0 verified gates.
* **k2, k3** best plans are 196 products = 271, i.e. +2 each: dropped.
* **k11, k13** found no perfect pairing on the descent path (seeds 7–9): no plan.
* **k1** was the last open case (shipped 99 cuts / 213 products, the legacy maoxin loader). The
  identity-basis search reached only 85 cuts; the rank-74 basis search found no rank-74 basis in
  seed 7 and was still running when the search was stopped — it produced **no plan file**
  (`basis_plan_k1.json` does not exist). Treat k1 as unresolved-but-unpromising, not as a win.
* **k0** and the last six loaders remain blocked by §5a/§5b regardless of any further search.
* No Kaggle verification other than the §6 negative control was run, because nothing beat 4,025.

Consequence: **the code/gauge axis and the plan axis both yield zero gates at (8,143,44)/1,220
rows with the shipped emitter.** A future attempt needs the missing emitter pieces of §5 (the
delta-helper load and the per-batch low cache, then the 68-high cache generator), not more
searching of the same plan space.
