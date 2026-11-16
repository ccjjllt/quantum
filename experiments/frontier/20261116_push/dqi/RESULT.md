# DQI 890Q push — 2026-11-16

Baseline: `ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d`
(`hayatohikawa/qcc-c8-milestone-portfolio`), 890 qubits, official cost
**347,375,470,571.73334**, mean T 368,139.490, R = 1.19126046, 0 value / 0 phase errors at the
default salt (102,400 shots). All circuit loading, transformation and verification ran on Kaggle
CPU kernels; nothing was simulated locally and nothing was submitted.

## 0. Summary

| lever | status | evidence |
|---|---|---|
| Q 890 → 888/880/870/840 | **closed for this tape** | the 50 ancillas are one permanent working pool: HMR-delimited peak = 50, and `peak_without = 890` for each of the 50 taken alone (§3) |
| "borrow the carry bank for the 24 helper bits" (Q→865/864) | **fails on this tape** | the carry bank is a live accumulator (touched inside ~62–72 % of helper-window ops) **and** the 890 level is a 3.59 M-op plateau, not one site, so any single-site borrow moves Q by 0 (§3b) |
| T, exact peephole: cancel pairs | **0 available** | 0 exact `CCX` cancel pairs on 362,984 CCX (§5) |
| T, dead-write deletion (`R` target / unused-`HMR` target) | **0 available** | 0 sites; all 54,075 bits are referenced (§5) |
| T, \|0>-control removal | **0 available** | 0 sites (§5) |
| Toffoli surface overall | **saturated** | cancel / zero-control / dead-write are all zero, and only 871 of 369,010 Toffolis fail to fire (§5) |
| toolchain | **exact, validated** | a null round-trip re-pack reproduces `ccc2ab84…`, T 368,139.490 and 0/0 errors bit-for-bit (§5) |

Q is the dominant lever (1 qubit = 827 mean T = +0.0205 GM at Q=890; Q→840 at constant T is
+1.11 GM), so it got the bulk of the effort. The conclusion is that this tape is at its structural
floor, that its Toffoli surface is already scraped clean, and that the gap to the 864-qubit
frontier hypothesis is a decoder-generation change, not a patch.

**Nothing was packaged and nothing was submitted.** With 0 Toffolis and 0 qubits removable, any
re-hash of this tape only re-draws the salt (expected +0.09 % cost, §6) with no offsetting gain.

## 1. What was done

Seven Kaggle CPU kernels (`enable_gpu: false`, `enable_tpu: false`, no internet, competition data
attached, DQI from `hayatohikawa/qcc-c8-milestone-portfolio`):

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k1 | `zhuating/qcc-dqi890-liveness` | sha gate, `.kmb → .kmx`, qccscope liveness | complete; confirmed sha and 58,416,320 ops |
| k2 | `zhuating/qcc-dqi890-surgery` | qccscope inventory, retention-drop attempt | complete; `droppable = []`, `peak_without = 890` for all 50 |
| k3 | `zhuating/qcc-dqi890-kmbdiag` | first direct-`.kmb` numpy reader | crashed on a numpy `uint32 initial=-1`; the container facts were recovered and reused |
| k4 | `zhuating/qcc-dqi890-kmbsurgery` | direct `.kmb`: cancel pairs, \|0>-controls, ancilla live ranges | complete; 0 pairs, 0 zero-controls |
| k5 | `zhuating/qcc-dqi890-deadwrite` | dead-write deletion + **null round-trip control** + official verify | complete; 0 dead writes, null candidate PASS at the exact baseline |
| k6 | (`zhuating/qcc-dqi890-package`) | package + verify a submission zip, guarded at ≥300 T saved | written but never pushed: 0 T saved |
| k7 | `zhuating/qcc-dqi890-zerobank` | carry-bank vs helper-bank overlap test (§3b) | overlap complete; the 256-lane value scan was OOM-killed |

The `.kmb` container format was recovered from boristown's public `patch_dqi_ccc2ab84.py` and
re-used: `MAGIC(16)` + `"<4I9Q"`(88) + `<QQ idx,size>` chunks; `secs[1]=ops`, `[2..4]=a3,b3,t3`,
`[5,6]=a2,t2`, `[7]=a1`, `[8]=bits`, `[9]=conds`; opcode = `ops & 127`, inline condition =
`ops & 128`. Header: `h[1]=Q`, `h[3]=n_registers`, `h[4]=n_ops`, `h[5]=static_T`,
`h[6..9]=len(secs[5,7,8,9])`. This allows exact numpy editing of the 58.4 M-op tape with no
1.1 GB kmx text round-trip, and the k5 null control proves the writer is byte-exact.

Tape facts (measured, k4/k5): 58,416,320 ops; static Toffoli-like **369,010** = CCX 362,984 +
CCZ 6,026, **no CSWAP**; CX 30,326,542; CZ 534,171; SWAP 382,091; HMR 72,051; R 48,043;
X 108,396; classical bit ops 21,404,883; PUSH/POP 2,576,153 each; 54,075 classical bits;
Q = 890 with registers exactly `0..839` (70 × 12) and ancillas exactly `840..889`.
Static 369,010 vs mean 368,139.490 ⇒ only 871 Toffolis are conditional-and-not-firing.

## 2. Reusable finding: the 49 = 24+1+24 story does not transfer

`experiments/frontier/20261115_upgrade/dqi_ancilla/REPORT.md` measured the **889-qubit v12 source**
(24 carry + 1 flag + 24 transient product scratch). The shipped **890-qubit v13/v14 tape** is a
different allocation and had to be measured, not inferred. It is 4 twelve-bit words + 2 bits:

| wires | bits | role (from the define op and use mix) | ops touched | CCX targets | HMR/R | first / last op |
|---|---|---:|---:|---:|---:|---|
| 840 | 1 | accumulator, `define X(840)` (so it starts as \|1>) | 1,516,399 | 28,804 | 16 | 17,576,193 / 53,808,143 |
| 841–851 | 11 | 12-bit word loaded from 840 (`CX 840→w`) | 270 k–793 k | 10–14.8 k | 16 | 17,576,2xx / 53,804,3xx |
| 852–863 | 12 | second 12-bit word (copies of 852/853/858) | 129 k–240 k | 52–3,290 | 14 | 17,577,6xx / 53,806,6xx |
| 864–875 | 12 | AND / measure pool A | 183 k–217 k | 2.8 k–7.2 k | 1,611–9,417 | 17,577,8xx / 53,806,9xx |
| 876–887 | 12 | AND / measure pool B | 173 k–231 k | 2.8 k–8.2 k | 1,519–9,696 | 17,578,7xx / 53,806,9xx |
| 888–889 | 2 | pool / predicates | 176 k / 115 k | 2,983 / 1,960 | 1,380 / 1,137 | 17,579,1xx / 53,806,9xx |

## 3. Q: the 50 ancillas are a working pool, not scratch (measured)

Width profile (`qccscope.liveness` on the kmx conversion; cross-checked against the raw-tape
per-wire census, which shows every ancilla touched across a 36 M-op span):

```
ops        0 – 17.5 M : width 840          (extractor + first synthesis nodes)
ops     17.5 – 21.6 M : rising 840 → 890
ops     21.6 – 53.5 M : 3,591,056 ops at width 890, in 925 episodes
ops     53.5 – 58.4 M : falling to 840     (restore / uncompute tail)
width quantiles 1/5/25/50/75/95/99/100 % = 840, 840, 840, 867, 878, 890, 890, 890
```

* **`peak_without = 890` for every one of the 50 ancillas** (k2 C4): removing any single wire leaves
  the peak at 890, because the pool rotates — at each plateau op a different subset of 50 is open.
* **The reuse rule makes the conservative peak the true one.** A wire id can only be reused after
  `R`/`HMR` puts it back to |0>: `CX`/`CCX` targets XOR and therefore read the target, and the only
  non-reading writer in the tape is `X`, which itself requires |0> (that is exactly how q840 is
  opened). So the HMR-delimited peak of 50 is a real lower bound for this tape; a relabelling /
  def-use pass cannot go below it. This reproduces, one qubit worse, the earlier
  `min_qubits = 889 = Q` and `FREE_SHRINK_IF_RENUMBERED 0` results.
* **There are no retention wires to drop**: 0 of 50 ancillas have the "single AND define + `CX`
  copies only" shape (`droppable = []`, k2 D0/E2), and no ancilla is idle across a plateau episode.
* **The 890 level is not a spike**: 3.59 M ops (6.1 % of the tape) at width 890 across 925 episodes
  spanning ops 21.6 M–53.5 M, so there is no narrow window in which to park a value.

### Top 3 blocking ancillas and the minimum T cost to release each

| rank | wire | why it blocks | tape-level mechanism | minimum T cost |
|---:|---:|---|---|---:|
| 1 | **q840** | 1.52 M touches, 28,804 CCX targets, 733,686 XOR-writes, live op 17,576,193 → 53,808,143. The running accumulator that every synthesis/convert step updates. | recompute = replay the whole prefix | **not finite** |
| 2 | **q841** | 793 k touches, 14,824 CCX targets, 385,377 XOR-writes; opened by `CX 840→841` but then written independently, so it diverges from q840 | none | **not finite** |
| 3 | **q864** | 217 k touches, 7,195 CCX targets and **9,417** HMR/R: the first AND-pool wire, re-prepared ~9.4 k times | re-home each of the 7,195 products | **≥ 925 T** (one CCX per plateau episode), realistically ≥ 7,195 T — **and it does not lower Q on its own**: 25 other pool wires are equally live, so a single release moves the peak by 0 |

Practical reading: **890 = 840 + 4×12 + 2**. Reaching the 864-qubit point (840 + one 24-bit word,
the ~28.65 GM hypothesis) requires the *algorithm* to keep two working words instead of four and to
halve the AND pool. That is the v13→v15 decoder redesign, not a patch.

## 3b. The specific "borrow the carry bank for the 24 helper bits" hypothesis — tested

Hypothesis (from `after_v3/blocks/v6/THIRD_PUBLIC_CHART_GATE.md` lines 35–37, which describes the
**889-qubit v12 source**): "Peak ownership is 840+24+1 retained bits plus 24 fresh helper bits, hence
Q889"; if the 24 fresh helper bits borrow the clean 24-bit carry bank instead, Q ≈ 865/864.

Measured on the shipped 890-qubit tape (k7):

* The **carry bank is q840..q863** (24 wires; `q840` is opened by `X(840)`, i.e. it starts as |1>).
  Each is touched **90 k – 1.5 M** times and reset only **14–16 times in the whole 58.4 M-op tape**:
  they are permanent accumulators, not a bank re-prepared per site.
* The **helper bank is q864..q887** (24 wires) and it is a *pool*: 9,417 HMR/R on `q864`,
  1,519–9,696 on the others, i.e. opened and erased ~9.6 k times each.
* Overlap test — for every true use window `[write, last read]` of a helper wire, does any
  carry-bank wire get touched inside it?

```
k7 B3 (truncated at w872 when the kernel hit the memory ceiling)
wire  windows  window ops  windows with carry touch  frac   window ops with carry touch
864   24,082   7,269,457   1,964                     8.2 %  4,523,936  (62 %)
865   15,271   6,327,603   1,609                    10.5 %  4,576,621  (72 %)
866   15,125   5,984,625   1,646                    10.9 %  4,279,456  (72 %)
867   16,043   6,373,134   1,489                     9.3 %  4,565,892  (72 %)
868   15,480   5,914,076   1,934                    12.5 %  4,149,584  (70 %)
869   21,968   7,950,069   1,822                     8.3 %  5,476,783  (69 %)
870   22,973   7,533,041   1,921                     8.4 %  5,085,168  (68 %)
871   23,653   6,874,802   1,832                     7.8 %  4,548,340  (66 %)
872   15,240   5,725,852   2,008                    13.2 %  3,960,650  (69 %)
```

**Verdict: the borrow fails on this tape, for two independent reasons.**

1. *Value conflict.* 8–13 % of the helper use windows contain a carry-bank touch, and those windows
   carry 62–72 % of all helper-window ops. The carry bank is a live accumulator there, so it is
   neither clean nor free; a rename would corrupt the decoder state.
2. *Wrong shape of the peak* (decisive). In the v12 design 889 is a narrow spike at one site (one
   24-bit conditional head addition), which is why a single-site borrow could work there. On this
   tape the width is 890 for **3,591,056 ops across 925 episodes spanning ops 21.6 M–53.5 M** — the
   whole second half. The 24 helper wires are simultaneously live with the 24 carry wires for 6 %
   of the entire tape, so a single-site borrow moves Q by exactly 0 — the same way each of the
   "five witnesses" in the 889 analysis moved Q by 0.

The blocking site in tape terms is not one call site: it is every helper window containing a carry
touch (≈2 k per helper wire, ≈45 k in total). The first concrete blocker is **q840**: initialised to
|1> at op 17,576,193 and XOR-written 733,686 times afterwards, so it can never serve as a clean
0-bit of a borrowed bank.

Caveat: the value-level half of k7 (a 256-lane scan that would have measured how many ancillas hold
0 on all sampled lanes at the plateau, and the resulting "semistatic" width) did not run — the
kernel was OOM-killed after the overlap stage. The verdict above therefore rests on static tape
structure (touch windows, reset counts, initialisation), which is sufficient for reason 2 alone.

## 4. What Q=864 would actually require

The four 12-bit words are (i) a running accumulator, (ii) its shadow/copy, (iii)+(iv) two AND/MBU
pools with ~9.6 k re-preparations each. A two-word design must fuse (i)+(ii) into an in-place
accumulate that never needs a shadow, and halve the pool by serialising the rank-42 products. Both
are decoder-level rewrites with phase re-derivation. There is no tape-level schedule that reaches
them, because at the plateau every wire sits inside a live interval that the |0>-reuse rule cannot
break — and the peak is 6 % of the tape long, so there is no single site to attack.

## 5. T axis: exact peephole results

Method: full per-wire write-version tracking over the tape plus a 63.9 M-entry sorted `(wire, op)`
touch index, so every rule below is decided exactly (no simulation sampling).

| rule | condition | sites | T saved |
|---|---|---:|---:|
| exact cancel pair | `CCX(a,b→t)` twice, `a`,`b`,`t` versions unchanged, no read of `t` between | **0** | 0 |
| \|0>-control | `CCX/CCZ` with an unconditional control whose last write is `R`/`HMR` | **0** | 0 |
| dead write → `R` | `CCX/CCZ` into `t`, next touch of `t` is an unconditional `R` (no measurement) | **0** | 0 |
| dead write → unused `HMR` | same, next touch an `HMR` whose bit is never referenced | **0** | 0 |
| bits | every one of the 54,075 classical bits is referenced by some condition | — | — |

Measured (k5):

```
A3  Q 890  n 58416320  staticT 369010  nbits 54075
A5  bits referenced by conditions 54075
B0  touch index 63,868,953 (wire, op) pairs
B1  dead to R            0
B2  dead to unused HMR   0
B3  total T saving       0
C1  CAND_0_null bytes 486988897 ops 58416320 deleted 0 staticT 369010
D   CAND_0_null 147s Q 890 T 368139.490 score 347375470571.733 err 0/0
    sha ccc2ab84ed713901 dscore +0.000 (+0.000000%)
```

**The null candidate is the decisive toolchain result**: unpacking and re-packing the tape with the
new numpy `.kmb` writer reproduces `sha256 = ccc2ab84ed713901…`, mean T 368,139.490, score
347,375,470,571.733 and 0/0 errors — bit-for-bit the baseline. Every rule above is therefore applied
on a proven-exact basis. All four rules fire zero times: **this tape's Toffoli surface is fully
saturated**. There is no 4-Toffoli peephole left, let alone 300.

## 6. What this means for the score

* A DQI circuit change changes the `.kmb` SHA-256, hence the seed, hence the draw
  (`_initial_seed(circuit_hash, salt)`). The realised 28.09090 package is one draw; the manifest's
  48-draw expectation for the sibling family was +0.2048 % over its zero-failure cost. A candidate
  must cut cost by **≳0.09 %** (≈320 T) before re-drawing is even break-even.
* With 0 T and 0 Q available, **no DQI candidate from this tape clears that bar**, so k6 (guarded at
  `MIN_T = 300`) was never run and no zip was produced.
* The 143-team 28.09486 tie cannot be broken from the DQI side by peephole work: a 4-Toffoli saving
  would be +0.0000019 GM *if the salt did not change*, but it does.

## 7. Negative results worth keeping

1. **No relabelling win on this tape**: the |0>-reuse rule makes the HMR-delimited peak the true
   minimum.
2. **No retention wires at the peak** (the 889-family artefact) — 0 of 50 ancillas have the shape.
3. **`peak_without = 890` for all 50 ancillas**: the "five witnesses" plateau of the 889 analysis is
   now 50 witnesses.
4. **The 890 level is broad** (3.59 M ops, 925 episodes), so "park a value across the peak" has no
   window, and neither does a single-site borrow (§3b).
5. **`q864` is not a transient scratch** (9,417 HMR/R, 108,178 writes over 217 k ops): the public
   HW-27 rule converted only 8 sites because every other `CCX→864` has an intervening use.
6. **No CSWAP at all**, so there is no CSWAP→CX/CCX axis.
7. **`Z_POW` = 0**, so there is no rotation budget to trade.
8. **Only 871 of 369,010 Toffolis fail to fire**, so "make more gates conditional" has essentially
   no headroom on the existing bits.
9. **`q840` starts as |1>** (`X(840)`), so the "clean 24-bit carry bank" premise of the
   864-qubit hypothesis is false for this tape at the very first bit.

## 8. Honest verification scope

* Every score quoted is the **unchanged official verifier**
  (`verifiers/dqi/verify_submission_dqi.py`, `ProblemSpecDQI.benchmark_instance()`, salt `''`,
  102,400 shots, batch 256, 4 workers) executed on a Kaggle CPU kernel against the candidate `.kmb`.
  The only full-verifier run in this work is the k5 null candidate (PASS, 0/0, exact baseline
  score) — no *modified* candidate reached the verifier because no sound modification was found.
* Static counts (Q, 369,010 static Toffoli-like, opcode census, per-wire touch counts, HMR counts,
  version-tracked peephole decisions) are read directly from the tape.
* Width/liveness numbers are from `qccscope.liveness` (a conservative, HMR-delimited model) on the
  kmx conversion of the same bytes, cross-checked against the raw-tape per-wire census. Per-version
  def-use liveness was **not** separately re-implemented; §3 argues it cannot beat the conservative
  model for this tape because of the |0>-reuse rule.
* The 256-lane value scan did not complete (OOM in k7), so no "semistatic width" number is claimed.
* No candidate was submitted to Kaggle; no leaderboard number was produced by this work.
* The 864-qubit / 28.65 GM identification is a **hypothesis supplied by frontier intel**, not
  something measured here.
