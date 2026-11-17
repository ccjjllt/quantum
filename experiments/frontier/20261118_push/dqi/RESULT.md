# DQI cost reduction — public-candidate audit, inside-condition-block pair finder, Q-axis census

Date 2026-11-18. Line: DQI. Account `zhuating`. Target to beat:
**DQI cost 346,409,762,292.72** (`575b043f`, Q 890, mean executed T 367,116.06, static 367,989).
All circuits ran on Kaggle CPU kernels (`enable_gpu=false`, `enable_tpu=false`, private).
**Nothing was simulated locally, nothing was submitted, nothing was published.**

## 0. Verdict

| axis | verdict | decisive measured number |
|---|---|---|
| **1. public candidates** | re-measured | `575b043f` is **exactly 4 static Toffoli-likes** below `61c8348d` (367,989 vs 367,993) and 3.95 T lower on mean T — **confirmed**, all 5 files PASS on 3 salts |
| **2. retention pairs inside condition blocks** (their open item #3) | **closed** | a finder was built and run over all **362,012** CCX: **4,184** retention pairs, 206 of them inside blocks, **44** with a clean wire, **3** servable → **−3 T = −0.0008 % of cost = +0.00008 GM** |
| **2b. free Toffolis** (void / zero / held, now also inside blocks) | **closed** | **0** of 362,012 CCX need no Toffoli (depth 0: 317,590, depth 1: 43,871, depth 2: 551) |
| **2c. plain cancels** | **closed** | **0** pairs `CCX(a,b,t)` … `CCX(a,b,t)` with a, b, t and every condition bit untouched in between |
| **2d. buy retentions with extra wires** | **closed** | measured curve: 1 wire buys **180** retentions against an **825 T** break-even; 14 wires buy **2,366** against **11,556 T** → **+2.5 % cost** |
| **3. Q below 890** | **closed** | the 50 pool wires absorb **51.94 %** of the tape's Toffolis; 26 are persistent 12-bit EEA words + 2 flags and **24 are the product pool** (0.8–1.7 Toffoli writes per reset-window, 116,894 Toffoli writes over 108,841 windows). 866 Q allows 26 pool wires → zero product pool, and its break-even T budget is **+20,630 T** against a **≥116,894 T** rebuild floor (5.7× over) |

**Net: the best cheaper circuit this work produced is 3 Toffoli-likes cheaper
(367,989 → 367,986 at Q 890) and it passes the unmodified verifier at the default salt
with 0/0 errors. That is +0.00008 GM on a clean draw and −0.0429 GM on a lost shot, and
it lost a shot at 2 of the 3 salts measured. It is far below both the +1,678 T
single-lost-shot price and the ~550 T EV break-even, so it must NOT be shipped.** The
DQI T axis on this tape generation is exhausted; the only remaining object is a new
decoder generation (Q and the algorithm), which this line did not attempt.

## 1. The five public candidates, unmodified official verifier, 3 salts

Kernel `zhuating/qcc-dqi-verify-sweep-1118` (CPU, competition data +
dataset `grantprater/vqcc-dqi-61c8348d-merged-closings`). Each file was decompressed
(xz → `/kaggle/working`, one at a time, deleted after) and run as
`python verifiers/dqi/verify_submission_dqi.py FILE [--salt S]` with
`PYTHONPATH=<comp>/kickmix:<comp>/verifiers`. Salts: `<default>`, `dqi-push-18x`,
`dqi-push-18y`. Every run `rc=0` and `status=PASS`; `phase_errors = 0` in all 15 runs.
Raw: `evidence/verify_public_5x3salts.json`.

| file | sha256 (verifier's own `circuit_sha256`) | Q | static T | mean T (`<default>`) | cost `<default>` | cost `…18x` | cost `…18y` |
|---|---|---:|---:|---:|---:|---:|---:|
| `dqi.kmb` (= `61c8348d`) | `61c8348d6e85bb02…` | 890 | 367,993 | 367,120.0042 | **348,004,440,260.46** (1 lost shot) | 348,004,530,341.68 (1) | 348,004,557,131.84 (1) |
| `dqi_575b043f.kmb.xz` | `575b043f4fee91a0…` | 890 | **367,989** | **367,116.0572** | **346,409,762,292.72** (0) | 348,000,716,409.72 (1) | 346,409,870,078.45 (0) |
| `dqi_66b4f18b.kmb.xz` | `66b4f18b85273bdc…` | 890 | 368,750 | 367,877.5490 | 347,128,304,010.81 (0) | 347,128,434,511.07 (0) | 347,128,135,702.15 (0) |
| `dqi_ccc2ab84.kmb.xz` | `ccc2ab84ed713901…` | 890 | 369,010 | 368,139.4897 | 347,375,470,571.73 (0) | 347,375,716,598.17 (0) | 347,375,823,619.07 (0) |
| `dqi_d54d3387.kmb.xz` | `d54d338753757cf0…` | 890 | 368,973 | 368,102.7344 | 347,340,788,307.83 (0) | 347,340,705,227.02 (0) | 347,340,509,126.47 (0) |

Facts worth having on record:

* **`575b043f` is 4 static Toffoli-likes better than `61c8348d` (confirmed)** — 367,989
  vs 367,993 — and 3.95 T lower on mean executed T (367,116.057 vs 367,120.004) at the
  same Q 890 and the same `num_ops` family. The README's 346,409,762,293 reproduces to
  the unit (346,409,762,292.72 at the default salt); its second clean draw
  (346,409,819,618) is a different salt with a slightly different mean T — ours is
  346,409,870,078.45 at `dqi-push-18y`, 1.5e-7 apart — i.e. pure draw noise.
* **`61c8348d` is not 346.41e9 in practice on any salt measured.** Its README quotes a
  clean-draw 346,413,287,873; all three of our salts lose one shot → **348.00e9 every
  time**, i.e. 0.46 % worse than the shipped `575b043f`. Its 0/0 salt has not appeared
  in 3 draws, while `575b043f` got 2 clean draws in 3. That is the whole reason the
  public swap to `575b043f` was worth more than its 4 Toffolis.
* `dqi_66b4f18b` (Balram's cheaper-closing input) is **+761 static T** over `575b043f`;
  `dqi_d54d3387` is +984; `dqi_ccc2ab84` is +1,021. The merged `61c8348d` really did take
  the best of both, and `575b043f` took the four extra closings on top.
* For the record the sweep also verified the organisers' own reference
  `sample_submission/dqi.kmb`: Q **1,893**, static T 5,725,461, mean T 5,725,108.4,
  cost exactly `24439463583672.93` = the competition REFERENCE, 3/3 salts PASS 0/0.

## 2. A finder for retention pairs inside condition blocks (their open item #3)

`qc.passes.measure_out.find(retain=True)` pairs only `depth == 0 and own is None` CCX
gates, so every product computed twice inside a `PUSH_CONDITION` block is invisible to
it. The shipped prover `vqcc_pair_window.py --prove` **does** handle such pairs (both
gates in one block instance); it just has no finder. I wrote one
(`k_find/main.py`, class `Finder`) and ran it on `575b043f`:

* one streaming pass in the shipped 64-bit symbol algebra
  (`qc.passes.measure_out.step_symbols` with `condsym`, the same keying the shipped
  `--retain` uses);
* a pair is keyed by **(block-instance path, own `_IF` bit, the two controls' sorted
  symbols)** and requires that no condition bit of the enclosing blocks is rewritten in
  between (measured: **0** such rejections);
* a wire serves the pair when it holds 0 whenever the first gate runs and nothing touches
  it over the span — its last touch is an `R`/`HMR` whose block path is a **prefix** of
  the gate's (so that reset surely ran) — the sufficient half of `pair_window.wire_free`;
* every candidate is then handed to the **shipped** prover,
  `pair_window.prove(span, Q, cap=4e6, abstract=True)`, and only proven pairs whose wire
  also passes the exact `pair_window.wire_free` are applied with the **shipped**
  `measure_out.apply(..., allow_open=True)`.

### 2.1 Measured (kernel `zhuating/qcc-dqi-condfind-1118`, 2m12s of work)

Tape `575b043f`: 479,128,738 B, sha `575b043f4fee91a0…`, 57,520,821 ops, Q 890,
66,726 bits, static T 367,989.

```
depth census : toffoli_like 367,989 | CCX 362,012
               CCX at depth 0 317,590 (= every depth-0 Toffoli-like)
               CCX at depth>0  44,422  (depth 1: 43,871, depth 2: 551), max depth 2
               2,558,513 PUSH blocks; 18,552,812 gates carry a per-gate _IF bit
scan         : ccx_total 362,012 | ccx_keyable 362,012
               pairs with a clean wire          44   (all at depth 1)
               pairs with no clean wire      4,140   (162 of them conditioned)
               pairs whose condition bit is rewritten between   0
               plain cancels                     0
               CCX with a control at the constant 0   0
proof        : 3 proven by the shipped prover, 0 not proven, 0 undecided,
               0 rejected by wire_free    (only 3 of the 44 are mutually disjoint:
               their spans are 19,903/19,903/19,904 instructions, all in ops 48.5M–52.3M,
               and one wire, W880, serves all three)
apply        : static T 367,989 -> 367,986 (-3), Q 890 unchanged,
               bits 66,726 -> 66,729, ops 57,520,821 -> 57,520,830
               sha256 327b07519606f7e7c7765eca1194b0691b0b0c7b59382c1db4f60bd8d061c61f
```

Cross-check that the finder is right: on the unconditioned population it finds exactly
**3,978** pairs, which is **exactly** what the shipped
`measure_out.py count 575b043f --retain` reported on 2026-11-17, and like that run
**none** of them has a clean wire. The 44+4,140 = 4,184 = 3,978 unconditioned + 206
conditioned. So the conditioned class is genuinely new work (206 pairs, 44 servable)
and it is worth **3 Toffolis**.

### 2.2 The free-Toffoli classes, now also inside blocks (kernel `zhuating/qcc-dqi-free-1118`)

The shipped `free_gates` tests three no-Toffoli classes on unconditioned gates only
(0 found in 317,590). Re-tested on **all 362,012** CCX in the same symbol algebra, with a
symbol→wire count so `held` is O(1):

```
ccx@0 317,590   ccx@1 43,871   ccx@2 551
free_void 0     free_zero 0    free_held 0    free_dead_condition 0
```

**No CCX anywhere in the tape can be removed for free** — not by a zero control, not by
a target that already holds the product, not by another wire already holding it, not by
a block whose condition is the constant 0. Raw: `evidence/free_and_extra_wire.json`.

### 2.3 Retention pairs by number of clean wires, and the price of a wire

```
clean wires over the span:  0 -> 4,140 pairs      1 -> 44 pairs      >=2 -> 0 pairs
```

Adding k clean wires (measured with a greedy joint assignment, spans served disjointly;
`cost ratio = ((890+k)/890)^2 * (367116.057 - served)/367116.057`):

| +wires k | retentions served | T that k wires must buy to break even | cost ratio | GM |
|---:|---:|---:|---:|---:|
| 0 | 3 | 0 | 0.999992 (−0.001 %) | 28.151009 |
| 1 | 180 | 825 | 1.001757 (+0.176 %) | 28.134464 |
| 2 | 357 | 1,651 | 1.003523 (+0.352 %) | 28.117955 |
| 4 | 711 | 3,302 | 1.007055 (+0.705 %) | 28.085042 |
| 8 | 1,419 | 6,603 | 1.014123 (+1.412 %) | 28.019639 |
| **14** | **2,366** | **11,556** | **1.025059 (+2.506 %)** | **27.919641** |
| 16 | 2,470 | 13,206 | 1.029306 (+2.931 %) | 27.881188 |
| 24 | 2,872 | 19,810 | 1.046409 (+4.641 %) | 27.728452 |

So **the 686 Toffoli-likes the public README lists as "waiting for a second helper
wire" are not buyable at any k**: one wire buys ~180 retentions, break-even is 825, and
the marginal wire buys less as k grows (the 686 would need +14 wires = +2.5 % cost). The
same holds for the 866 Q move, whose whole budget for 26 extra wires is 20,630 T
(793 T/wire). This closes open item #1 quantitatively rather than by opinion.

## 3. Can Q go below 890?

Kernel `zhuating/qcc-dqi-poolcensus-1118`, per-wire census of wires 840–889 on
`575b043f` (raw: `evidence/pool_census_575b043f.json`). It reproduces the earlier
`61c8348d` table to the digit: **191,118** Toffoli writes into the pool, against the
earlier **191,122** — exactly the 4 Toffoli-likes `575b043f` cut. Every `R` and all but
116 of the `HMR` in the tape land on these 50 wires (119,917 of 120,033 resets).

| group | wires | resets | windows | Toffoli writes | role |
|---|---:|---:|---:|---:|---|
| 840–851 | 12 | 192 | 204 | 58,650 | persistent 12-bit word #1: 15–17 value lifetimes over the whole tape (first touch op 17.58 M, last 52.91 M), rewritten by Toffolis in place |
| 852–863 | 12 | 168 | 180 | 6,684 | persistent 12-bit word #2: same 15 lifetimes, built almost entirely by **CX** accumulation (~1.17 M CX writes) |
| 864–875 | 12 | 51,130 | 51,134 | 57,700 | **product pool**: 0.8–1.7 Toffoli writes per reset-window |
| 876–887 | 12 | 57,695 | 57,707 | 59,194 | **product pool**: same |
| 888–889 | 2 | 10,732 | 10,734 | 8,890 | measured flags |
| **total** | **50** | **119,917** | **119,959** | **191,118** | **51.94 % of the tape's 367,989 Toffolis** |

So the 50 pool wires are **26 word/flag wires + 24 product-pool wires**, and the pool is
where half of the Toffoli cost happens. A 2nb+2-style workspace for the published
out-of-place formulation is 2·70·12+2 = **1,682 Q** — 3.57× our Q² — so the only
in-place target is ≤ 866 Q = 840 + 26, which leaves **zero** product-pool wires while
116,894 Toffoli writes over 108,841 windows need a home. Arithmetic on the official
formula: at Q 866 the T budget is +20,630 T (T may grow at most 5.6 %) and at Q 889 it is
+826 T, while the cheapest single wire to shed (`q889`) already costs 1,831 T to rebuild
with one AND per value lifetime. **Q is closed: 890 is the floor of this generation.**

## 4. What the 3-Toffoli candidate actually scores

Kernel `zhuating/qcc-dqi-verify-cand-1118`, unmodified official verifier on
`dqi_cond.kmb` (sha256 `327b07519606f7e7…`), 3 salts, raw
`evidence/verify_candidate_dqi_cond_3salts.json`:

| salt | status | value err | phase err | mean T | Q | cost |
|---|---|---:|---:|---:|---:|---:|
| `<default>` | PASS | **0** | 0 | 367,113.0052 | 890 | **346,406,882,459.21** |
| `dqi-push-18x` | PASS | 1 | 0 | 367,113.1040 | 890 | 347,997,899,332.77 |
| `dqi-push-18y` | PASS | 1 | 0 | 367,113.1722 | 890 | 347,997,963,993.88 |

`R·Q²·T` reproduces all three to the unit. Deltas against the shipped `575b043f`
(`scripts/gm.py`, the shipped invsqrt/chem held):

```
clean draw   : cost 346,406,882,459.21  (-2,879,833.51, -0.00083 %)  GM 28.15101005  (+0.00007801)
1 lost shot  : cost 347,997,899,332.77  (+1,588,137,040, +0.4584 %)  GM 28.10804316  (-0.04288888)
```

The parent loses a shot on 1 of its 3 salts; this candidate loses one on 2 of 3. With
+1,678 T as the price of one lost shot and ~550 T the EV break-even, a 3 T cut cannot be
shipped at any draw. **Recommendation: keep `575b043f`.** The candidate and its verifier
JSON are kept here only as evidence that the machinery is correct end to end.

## 5. Files

Small reports (in `experiments/frontier/20261118_push/dqi/evidence/`):

| file | what |
|---|---|
| `verify_public_5x3salts.json` | the 5 public candidates × 3 salts, full verifier JSON |
| `verify_candidate_dqi_cond_3salts.json` | `dqi_cond.kmb` × 3 salts, full verifier JSON |
| `cond_pairs_summary.json`, `prove_result.json`, `assign_cond.json`, `cancels.json`, `candidate.json` | the finder's counts, the 3 proven pairs, the rewrite, the candidate's sha |
| `free_and_extra_wire.json` | the void/zero/held counts and the extra-wire curve |
| `pool_census_575b043f.json` | per-wire census of wires 840–889 |
| `pool_census_k_find_BUGGY_superseded.json` | kept for honesty: the first pool census in the `k_find` kernel mapped an operand array's index to the op index directly, so resets/windows/toffoli-writes were misattributed (6,573 resets instead of 119,917). Its **touch** counts are right; every other column is superseded by `pool_census_575b043f.json`. |

Large files (git-ignored `artifacts/`, 457 MB):

| path | sha256 |
|---|---|
| `artifacts/20261118_push_dqi/out_condfind/dqi_cond.kmb` (479,128,819 B) | `327b07519606f7e7c7765eca1194b0691b0b0c7b59382c1db4f60bd8d061c61f` |

Kernels (all CPU, private): `zhuating/qcc-dqi-verify-sweep-1118`,
`zhuating/qcc-dqi-condfind-1118`, `zhuating/qcc-dqi-free-1118`,
`zhuating/qcc-dqi-poolcensus-1118`, `zhuating/qcc-dqi-verify-cand-1118`.
Sources under `experiments/frontier/20261118_push/dqi/k_*/main.py`
(`k_find/main.py` also carries the finder class, delimited by `# ---8<--- condfind`
markers, because a Kaggle script kernel uploads only `code_file`).

## 6. Exact commands

```bash
# push a kernel (CPU-only metadata written by the helper)
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi/k_verify \
    --slug qcc-dqi-verify-sweep-1118 --account zhuating --competition \
    --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py push --dir ... --account zhuating
python scripts/kgpu.py fetch --kernel zhuating/qcc-dqi-verify-sweep-1118 \
    --account zhuating --out artifacts/20261118_push_dqi/out_verify

# the finder / free-class / pool-census / candidate-verifier kernels
python scripts/kgpu.py new  --dir .../k_find    --slug qcc-dqi-condfind-1118 \
    --account zhuating --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py new  --dir .../k_free    --slug qcc-dqi-free-1118      --account zhuating \
    --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py new  --dir .../k_pool    --slug qcc-dqi-poolcensus-1118 --account zhuating \
    --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py new  --dir .../k_verify2 --slug qcc-dqi-verify-cand-1118 --account zhuating \
    --competition --kernel zhuating/qcc-dqi-condfind-1118

# the GM arithmetic (local, pure arithmetic)
python3 scripts/gm.py dqi=346406882459.21216 invsqrt=74797.36535717871 chem=294643137.73
```

Inside the kernels the verifier is invoked exactly as the brief specifies
(`PYTHONPATH=<comp>/kickmix:<comp>/verifiers`, `cwd=<comp>/verifiers`,
`python verifiers/dqi/verify_submission_dqi.py FILE [--salt S]`), and the tool package is
laid out the way the dataset README requires (`qc/ir.py`, `qc/bitsim.py`,
`qc/passes/measure_out.py`, `analysis/dqi/pair_window.py`, empty `__init__.py`).

## 7. Verification scope, stated honestly

* **What passed the official verifier:** all 5 public DQI files at `<default>`,
  `dqi-push-18x`, `dqi-push-18y` (15 runs, `rc=0`, `status=PASS`, `phase_errors=0`);
  and `dqi_cond.kmb` at the same 3 salts (`status=PASS`, 0/0 at `<default>`, 1 value
  error per fresh salt). No other circuit was verified.
* **Not done / not claimed:** no Kaggle submission, no dataset, no git push; no local
  simulation of any candidate; no new decoder generation; no value-level
  (simulated) redundancy search between wires — the 64-bit symbol algebra proves
  equality but never inequality, so a pair whose wires were never given the same symbol
  would be missed. That is the same convention as the shipped tools.
* **The one mechanism left unexamined on this tape, named so nobody mistakes it for
  closed:** *reordering* two duplicate computations into one span (the second half of the
  public README's open item #1, "or for an order that brings the two computations
  together"). I did not attempt it. What can be said without measuring: if the second
  `CCX(a,b,t2)` is moved next to the first, it becomes `CX(t1,t2)` and needs no wire —
  but then `t2` must stay live from there to its own reader, which is exactly the same
  "a wire must be clean over the span" requirement, now on `t2` instead of on a scratch
  wire. So a reordering does not escape the 4,140 no-wire pairs unless a *different*
  wire is clean over a *shorter* span; that is an argument, not a measurement, and it is
  the only place a >550 T cut could still be hiding in this tape.
* **Known limits of the numbers here.** (a) The wire table in §3 is this tape's; the
  earlier 61c8348d table agrees on every total (191,122 vs 191,118 Toffoli writes) so I
  treat it as reproduced rather than independently closed. (b) The `extra_wire_curve`
  assumes the served gates execute on every shot; they sit inside blocks, so the true
  saving is smaller, which only strengthens the negative result. (c) Draw outcomes are
  per-circuit (a new file is a new SHA → a new draw): `575b043f` 0/1/0 errors on the 3
  salts, `dqi_cond` 0/1/1, `61c8348d` 1/1/1.
