# LOADER_R5_PORT — the 791-row planner port: what works, what it costs, what blocks it

Status: **the port is done and the emitted loader is verified correct on Kaggle.**
Best measured: **238 T per loader** (189 products + 43 high + 6 low), **99 qubits**, exact
word match on all 800 addresses, clean workspace, no phase flips
(`qingyu1232/qcc-chem-r5-loader-verify`: `toffoli-like 238`, `words match on 0..790: True`,
`workspace clean: True | phase flipped: False`). That is 1 T over the 237 budget
(T = 14,029, GM +0.45 vs +0.52). One blocking geometry item sits on the *fit* side, and
**the fit has since failed** (`RESULT3.md` §2.3): the real pipeline reaches 53.65 mHa
continuous at (5,143,75) versus a 16.7 mHa gate, so the loader is ready but unused.
No submission.

## 1. What was ported (exact surface)

`r5port.py` (in this directory) drives the shipped
`syed_v12/src/dfthcsos_source/{compiler,research/scripts}` code unchanged except for
these constants:

| item | shipped (1,220 rows) | port (791 rows) |
|---|---|---|
| rows / plan grid | 1,220 / 1,232 = 77×16 | **791 / 800 = 50×16** |
| selection bits | 11 | **10** (`range(SEL)`, `q{10+8*j+b}`, `10+8*(…)` word map, `CX q{16+8*j} q{17+8*j}`, `nextq=50`) |
| high bits / high monomial loop | 7 / `range(1,77)` | **6 / `range(1,50)`** |
| high-bit seed | `{1<<b: 4+b for b in range(7)}` | `range(HB=6)` |
| polarisation grid | `arange(1232)`, `reshape(77,16)` | `arange(800)`, `reshape(50,16)` |
| `cross_tensor` | `(1232, 77)`, 7 high Möbius levels | `(800, 50)`, 6 levels |
| `BlockPlan/coord_relations` | `hmax=77` | **`hmax=50`** (49 determined slices) |
| padding completion | 12 rows 1220…1231 | 9 rows 791…799 |
| NOUT / NDIM / low cache / 4-low split | 35 / 525 / 6 / 4 low bits | **unchanged** |

`planner.BlockPlan/greedy/top_down/local_search`, `parity_recover.candidates/
alternating_field`, `extract_matching.matching`, `transport_cuts`,
`gauge_plan_fit.complete_forced` and `emit_plan.emit` are used as shipped. `emit` is
loaded by `exec`ing its own source with the ten constants replaced, so the emitter
logic is byte-identical.

Two report-only quirks in the shipped `emit_plan` (cosmetic, not the circuit): the
report dict hardcodes `'high_cache': 69` and `'low_computes': len(computes) - 69`, so
at 791 rows they read 69 and −20; the real numbers are **43 high** and **6 low**
(`toffoli_count` and `num_qubits` in the same report are correct).

## 2. Machinery validated on the shipped plan

Re-emitting the shipped `plans/angle_k_4.json` on the shipped completed table
(`planner.complete_words(submission.angle_words)` → (1232, 75)) gives

```
k=4: products 193  high 69  low 6  toffoli 268  qubits 126
shipped angle_k_4.kmb:            268 Toffolis, 125 qubits
```

i.e. the Toffoli count matches exactly and the emitted `.kmx` has exactly 268 `CCX`
lines; qubits are 1 more than the shipped build (within the 128 cap). So the `exec`-patch
mechanism is faithful.

## 3. The 791-row plan: measured cost

Dummy table: the shipped table's **first 800 rows** (50 complete blocks — so the code
and the polarisation helper hold on every block, which the 791-row truncation alone
does not) with the last block's bit 0 forced affine for the five loaded words, so the
`REL_LSB` forced relations can be imposed. Command:

```python
# r5port.py  (sys.path -> shipped compiler/ + research/scripts)
Wc      = complete_words_r5(table)          # (800, 75) pass-through in the probe
target  = cross_tensor_r5(Wc, k=4)          # 50 slices of 15 low x 35 out
rels    = REL_LSB + [REL_P1]                # the marculera bit-0 / XOR-of-five codes
pts     = screen_parts(target, rels)[0]
bp      = BlockPlan(target, pts, rels, per_coord=True, hmax=50)
cuts    = local_search(bp, top_down(bp, …), seconds=…)   # ≥ 0 always
pairs   = extract_matching.matching({'parts': pts, 'cuts': cuts})
emit_r5({'k':4,'parts':pts,'cuts':cuts,'explicit_products':…}, Wc, 'angle_k_4.kmx')
```

Result (one loader, k=4):

```
screen_parts best slack -245        # pure-nullspace cuts alone are far from pairable
check top_down:      sum_cuts 143  dim 382  span 382  alt_rank 382  feasible True
check local_search:  sum_cuts 145  dim 380  span 380  alt_rank 380  feasible True
REPORT product_count 190  toffoli_count 239  num_qubits 99  sum_cuts 145
```

`190 = (525 − 145)/2` exactly, and `239 = 190 + 43 + 6`, so the cost algebra and the
emitter agree. **99 qubits** = 10 selection + 40 word + 49 monomial cache (29 of the
78 available workspace qubits unused).

Cost at the shape level (15 circuits, `T_heur(5,143,75) = 6,889`, `Q = 427`):

| per loader | L/pass | T | chem cost | GM | vs the 237 budget |
|---:|---:|---:|---:|---:|---|
| **238** (measured, Σcuts 147, seed 3) | 3,570 | **14,029** | 281.1 M | **28.54 (+0.45)** | +1 T |
| 239 (Σcuts 145, seeds 1/2/4) | 3,585 | 14,059 | 281.7 M | 28.52 (+0.43) | +2 T |
| 237 (Σcuts 149) | 3,555 | 13,999 | 280.5 M | 28.56 (+0.47) | target |
| 211 (Σcuts 201) | 3,165 | 13,219 | 264.9 M | 29.11 (+1.02) | projection |

Seed variance, measured over five runs of the same table (the shipped `local_search` is
**wall-clock bounded**, so the result is not reproducible run to run): Σcuts
145, 147, 145, 143→fallback, and 71 (the `forced_only` fallback when `top_down` returns
an unpairable set). A production run must therefore retry seeds and keep the best
*feasible* set; `plan_and_emit` prints `check <tag>: … feasible True/False` for exactly
that purpose.

So the measured port lands **2 T short of the T<14,000 target and 28 T short of the
211 projection** — the cut search has to find 4 more (resp. 56 more) cut dimensions.
The longer search (`time_limit=900`, second seed) is running; the first 240 s run gave
145.

### 3b. The emitted loader, verified

`qingyu1232/qcc-chem-r5-loader-verify` (Kaggle CPU, kickmix) loads
`angle_k_4.kmx` and, for every address `a` in 0…799, sets the five word registers to
batch 3 (`table[a,15:20]`), runs the circuit and compares with batch 4
(`table[a,20:25]`):

```
circuit qubits 99   toffoli-like 238
selection 10  words 5  brot 8
words match on 0..790: True
words match on all 800: True
workspace clean: True | phase flipped: False
selection preserved: True
```

So the 791-row geometry (10 selection bits, 6 high bits, `q{10+8j+b}` word map,
`CX q{16+8j} q{17+8j}`, 50 high monomials, `hmax=50`) is **correct end to end**: the
emitter, the plan algebra and the physical qubit map all check out.

## 4. Blocking geometry (the real finding)

**(a) The last block of a 791-row table has only 7 real rows** (791 = 49·16 + 7). The
bit-0-affine code costs **55 constraints per block** (5 bits × 11 nonlinear low
monomials) and the 9 unreachable rows supply only **45 degrees of freedom** (9 rows ×
5 bits). At 1,220 rows the numbers are 55 vs 60, which is why the shipped 12-row padding
completion works there and **cannot work at 791**. Consequences:

* with `rels = REL_LSB` the shipped planner asserts (`forced cut is not an
  annihilator`) on any 791-row table whose last block is not affine;
* with `rels = []` the pairability collapses (measured: `alt_rank` 246 vs `dim` 386, and
  `screen_parts` best slack −245), so no plan can be emitted at all;
* therefore **the R=5 word table must carry the code on its last 7 rows**: bit 0 of
  each of the five loaded words must be affine in the low four address bits across
  rows 784…790 (plus whatever is placed in 791…799). That is ~10 linear conditions
  (2 per coded bit) that the *fit* has to impose — this is the one item the loader
  needs from the fit side, and it should be added to the pending R=5 refinement.

**(b) `emit_plan` cannot emit k=0** (`assert k>=1, 'ANGLE_0 needs a separately
scheduled low-cache window'`); loader 0 uses `emit_k0.py` + `k0_windows.json` at
1,220 rows. At 791 rows the cap pressure is gone (99 of 128 qubits used), so k=0 should
be emittable through the generic path; that needs a one-line test (drop the assert for
the port) and a check that the loader-0 plan's low-cache window is expressible with 29
spare qubits. This is a bounded, non-blocking item.

**(c) The remaining gap is the cut search, i.e. exactly the coded-word search.** The
shipped planner's search (`screen_parts` → `top_down` → `local_search`) was tuned at 49
vs 76 slices: at 791 rows the *screen* finds no partition whose pure-nullspace cuts are
pairable (−245), and `local_search` gains only +2 Σcuts over `top_down` (143 → 145) in
240 s. The 45 % cut increase the 211 projection needs must come from a *better code*
(more relations like `REL_P1` at bit 2, or a different low-block partition), not from
more search time on the same relations — which matches the public record: the frontier's
loader moved 4,033 → 4,025 (8 Toffolis) with new codes, not new planners.

## 5. What is ready and what is needed

Ready now:

* `r5port.py`: `complete_words_r5`, `cross_tensor_r5`, `screen_parts`, `plan_and_emit`
  and the `exec`-patched `emit_r5` — all ten geometry constants done, machinery
  validated against the shipped 268-Toffoli loader;
* a measured, emittable 791-row plan at **239 T / 99 qubits** on a realistic table;
* the Kaggle single-loader check: `qingyu1232/qcc-chem-r5-loader-verify` simulates the
  emitted `angle_k_4.kmx` on all 800 addresses (word registers batch 3 → batch 4,
  workspace clean, no phase flips) — result in the kernel log.

Needed before a real build:

1. the R=5 table from the pending fit (`qingyu1232/qcc-chem-merge-shrink-full-budget`),
   with the **last-block code constraint** of §4(a) added;
2. a code search (bit 2 / XOR-of-five variants, `nrel` and `REL_P1`-style relations) to
   push Σcuts from 145 to ≥ 149 (> 237) or ≥ 201 (211 projection);
3. the loader-0 path (§4(b));
4. the official 78,080-shot verifier on the assembled 15-loader family (the unshipped
   `prove_loader_branches` is not needed — the official verifier substitutes).

## 6. Commands

```bash
# port + plan + emit one loader on the synthetic table (local, numpy only)
python experiments/frontier/20261116_push/chem/r5port.py 4 6      # nrel=6 (codes)
python experiments/frontier/20261116_push/chem/r5port.py 4 -1     # nrel=-1 (no codes)

# single-loader correctness on Kaggle CPU (kickmix, all 800 addresses)
qingyu1232/qcc-chem-r5-loader-verify      # dataset qingyu1232/qcc-chem-r5-loader-probe
```

Scope: design/port exercise. One loader emitted **and simulated correct on all 800
addresses**; the other 14 and the full official 78,080-shot family verification are not
run. The 791-row table does not exist and the fit that would produce it has now failed
(53.65 mHa continuous at (5,143,75), `RESULT3.md` §2.3), so this loader is a verified
capability, not a pending build.
