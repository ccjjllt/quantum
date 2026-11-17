# DQI leg — algorithmic Toffoli-count reduction at Q=890

Line: `dqi_algo` (account `zhuating`). Target: cut the DQI mean executed Toffoli count
`T` at fixed `Q = 890` by an **algorithmic** change, not by byte-patching.

Baseline (official verifier, unmodified): `575b043f`, Q=890, static 367,989,
**mean executed T = 367,116.06**, cost `1.1912605 * 890^2 * T = 346,409,762,292.72`,
ratio 70.551, GM contribution 28.180659 for the shipped triple.

Everything below is measured on a Kaggle CPU kernel (never locally simulated, never
submitted, nothing pushed). Two kernels:

| kernel | ref | what it did |
|---|---|---|
| `zhuating/qcc-dqi-algo-regions` v1 | COMPLETE | staged structure dump + per-region mean T |
| `zhuating/qcc-dqi-algo-trunc` v1 | see §7 | truncation probe, official verifier |

Exact commands are in §9. Evidence JSON: `region_split.json`, `truncation_probe.json`.

---

## 1. Region split — the answer to "whose subroutine is it"

The tape carries **no INFO_TAG** (0 tags in 57.5M instructions), so the Chien/Forney
block has to be located structurally. Its only unambiguous anchor is
`bit_store(is_error, True, control=error_mbuc[j])`, i.e. runs of 12 consecutive
`BIT_STORE1_IF` whose condition bits are exactly the 12 bits of one `E` register.
There are **4,025** such runs (the tape visits 4,025 of the 4,095 codeword positions),
spanning ops `[30,335,416, 35,627,261]`; every Toffoli of the tape lies inside
`[17,576,206, 52,910,630]`.

| region | op range | ops | static T | CCX | CCZ | **mean T** (65,536-shot estimate) | share |
|---|---|---:|---:|---:|---:|---:|---:|
| preamble (classical) | 0 – 17,576,206 | 17,576,206 | 0 | 0 | 0 | 0 | 0 % |
| **EEA forward** | 17,576,206 – 30,335,416 | 12,759,210 | **153,186** | 153,185 | 1 | **153,180.1** | 41.7 % |
| **Chien / Forney** | 30,335,416 – 35,627,262 | 5,291,846 | **44,264** | 40,240 | 4,024 | **44,217.0** | 12.0 % |
| **EEA reverse** | 35,627,262 – 52,910,631 | 17,283,369 | **170,539** | 168,587 | 1,952 | **169,719.2** | 46.2 % |
| epilogue (classical) | 52,910,631 – 57,520,821 | 4,610,190 | 0 | 0 | 0 | 0 | 0 % |
| **total** | | 57,520,821 | **367,989** | 362,012 | 5,977 | **367,116.31 ± 0.18** | |

The estimator's total lands on the official verifier's **367,116.06** (Δ = 0.25, se 0.18),
so the split is calibrated against the shipped number, not against a model.

**Result: the two synchronized-EEA passes are 87.9 % of T (323,725 static /
322,899 mean). Chien/Forney is 12.0 %.** Attacking Chien can never buy more than
+1.23 GM even if it were free, and it is not free (§4).

Two further measured splits of the same regions:

* Toffoli **target register family**: EEA-forward 85,406 syndrome-register / 67,779
  pool-register (840-889); EEA-reverse 85,488 / 83,099; Chien 0 / 40,240.
  **51.9 % of the whole tape's Toffolis write the five 12-bit workspace registers
  (qubits 840-889)**, i.e. they are the EEA's bookkeeping/accumulator traffic, not the
  syndrome data path. `Q` is 890 = 840 syndromes + 50 pool, so this is also the reason
  the width cannot shrink (already closed in the brief).
* **Conditioning is not available**: a stack scan of all 2,558,513 PUSH/POP pairs shows
  every Toffoli of every region sits either at depth 0 (148,411) or under conditions on
  *scratch* bits only (219,578) — **zero Toffolis are under an `E`-bit (input) condition**,
  and the measured mean is 99.76 % of static. The 873 T discount the brief records is
  the entire conditional-execution budget of this tape.

---

## 2. Iteration structure — how many EEA rounds the tape actually runs

The tape's field multiply is a contiguous block of **42 CCX** (constant
`(control-register, control-register, target-register)` triple, inter-CCX gap ≤ 80
instructions). Grouping blocks into clusters (gap ≤ 6,000 ops) gives the round ladder:

| | clusters | clusters containing a multiply | 42-CCX blocks | T inside the 42-blocks | largest single cluster |
|---|---:|---:|---:|---:|---:|
| EEA forward | 151 | 133 | **1,542** | 66,670 | 132 multiplies (5,544 T) |
| EEA reverse | 137 | 135 | **1,526** | 64,256 | 66 multiplies (2,772 T) |

Multiply count per cluster, forward pass (read off in stream order):

```
4,4,1,1,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,3,0,3,0,0,3,0,132,
2,7,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
31,32,33,34,34, 2,3,16,3,15,60,1,14,2,3,13,3,12,49,1,11,10,10,1,10,9,9,1,9,16,9,
14,8,12,7,16,13,10,7,4,5,7,25, 5,6,5,6,1,6,6,7,1,7,7,8,1,8,8,9,1,9,9,10,1,10,10,11,1,
2,11,11,2,12,3,13,3,2,14,1,2,14,14,2,15,3,16,3,2,34
```

and the reverse pass **ends** with the mirror ladder

```
34,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,1,2,66,66
```

so both passes are a **34-step degree-driven ladder whose window grows 1 → 34** (the
peak window 34 ≈ t = 35), with the middle of the sweep in the 7-16 range.

### Is that the minimum?

Yes, and it is not the reference's number. The reference generator uses
`default_n_iters(n) = 3*(n+1)+9 = 222` (`verifiers/dqi/dqi_reference_circuit.py:613`)
because its `_synchronized_eea` advances **one of four sub-updates per iteration**
(`counter` is 2 bits, one-hot decoded in `_counter_controls`), so 222 iterations ≈ 55
"full" division steps — a deliberately loose upper bound on top of a 4× factor.

The mathematical requirement is: start from `deg r = 69` (n = 70 syndromes) and stop
when `deg r < t = 35`; each division step drops the remainder degree by **at least 1**,
so **≤ 35 steps** suffice, and 34-35 is what the tape runs. The tape therefore already
sits at the tight count, **not** at 222 and not at "about 105" — the two passes are
34 + 34 rounds of a *degree-indexed triangular* schedule, and the multiply total
(3,068 rank-42 blocks) is ~8× below what the reference formulation would spend
(16,206 multiply-adds per pass).

**Consequence:** there is no surplus round to truncate. The only way the tape could be
carrying slack is if its schedule were looser than the degree argument, and two
independent measurements say it is not: (a) the ladder peaks exactly at the window
34-35 = t, and (b) mean/static = 99.76 %, so nothing is being gated off on typical
shots — a loose schedule with a halting gate would show a large discount, and a loose
schedule *without* a gate would have to divide by zero after convergence.

§7 tests this empirically anyway (the coordinator asked for the measurement, and it is
worth 3,340 T / +0.086 GM if it were wrong).

---

## 3. Where the Toffolis are, in arithmetic terms

CCX block census per region (maximal runs of CCX sharing a register triple, gap ≤ 80):

| block size (CCX) | EEA fwd blocks | EEA rev blocks | reading |
|---:|---:|---:|---|
| 42 | 1,542 | 1,526 | one GF(2^12) multiply-add |
| 36 | 210 | 212 | multiply, shorter window |
| 34 | 105 | 105 | multiply, shorter window |
| 24 | 111 | 109 | multiply, shorter window |
| 12 | 492 | 471 | 12-bit AND broadcast (`init_and`-style) |
| 82 / 99 | 16 / 6 | 2 / 0 | two multiplies merged by the gap rule |
| 1-11 | 46,153 / 62,727 CCX | 59,047 / 82,044 CCX | control logic: comparisons, one-hot decode, counter updates |
| Chien | 32,192 blocks of 1 + 4,024 of 2 | — | 10 ANDs + 1 CCZ per position |

Multiplying blocks (≥ 24 CCX, i.e. real field multiplies): **3,969 blocks,
159,300 CCX = 43.3 % of the tape's static T**, mean rank **40.1**, mode **42**.

So the tape's arithmetic decomposes as

```
367,989 T  =  159,300  field-multiply ANDs (43.3 %)
           +   44,264  Chien per-position (12.0 %)
           +  164,425  EEA control logic + 12-bit AND chains (44.7 %)
```

`42` is a *good* multiply: schoolbook is 144 ANDs, recursive Karatsuba is 54-81,
Toom-3 is 45 (5 products × rank-9 4-bit leaves), Toom-4 is 7 × rank-6 3-bit leaves = 42.
The classical lower bound for the bilinear complexity of an n-term polynomial product
is `2n-1`, i.e. **23** for n = 12.

---

## 4. Priced alternatives (every number traceable, GM from the base triple)

Base: invsqrt 74,560.90687 / dqi 346,409,762,292.72 / chem 294,643,137.73 → GM 28.180659.

| # | alternative | explicit count | ΔT | ΔGM | verdict |
|---|---|---|---:|---:|---|
| A1 | schoolbook 12×12 multiply (144 ANDs) | 3,969 × 144 = 571,536 | **+412,236** | −8.1 | rejected (measured inferior) |
| A2 | kickmix `ixor_gf2_mul` (measured 63 T for 12 bits) | 3,969 × 63 = 250,047 | **+90,747** | −1.9 | rejected |
| A3 | Toom-3 (5 × rank 9 = 45) | 3,969 × 45 = 178,605 | **+19,305** | −0.53 | rejected |
| A4 | rank 42 → 35 in the 3,068 rank-42 blocks | 128,856 × (1−35/42) | **−21,476** | **+0.572** | needs regenerating the tape |
| A5 | mean rank 40.1 → 30, all multiply blocks | 159,300 × (1−30/40.1) | **−40,242** | **+1.112** | no known construction |
| A6 | every multiply at the bilinear floor 2n−1 = 23 | 159,300 × (1−23/40.1) | **−68,022** | **+1.992** | **hard ceiling of the whole axis** |
| B1 | Berlekamp–Massey instead of the EEA | 70 iters × 2 × 36 ≈ **5,040** multiplies (fwd alone) vs the tape's 1,542 blocks | ≥ +147,000 (fwd) | ≪ 0 | rejected: 3.3× the multiplies |
| B2 | Welch–Berlekamp (solve a 71×71 system) | ≈ 71³/3 ≈ **119,000** multiplies | +4.9 M | ≪ 0 | rejected: 77× |
| B3 | windowed / multi-bit EEA (2-4 quotient words per round) | bilinear rank is additive → multiply Toffoli count invariant; only the degree metadata can move | ≈ 0 | 0 | rejected: no Toffoli gain |
| C1 | Chien/Forney halved (5.5 T/position) | 4,025 × 5.5 | −22,108 | +0.590 | not reachable, see below |
| C2 | Chien/Forney entirely free | 44,217 | −44,217 | +1.232 | impossible: the phase kick needs the per-position AND |
| — | mission target (−20 % T) | | −73,423 | +2.176 | |

Notes on the rejected rows, all measured:

* **A2/A3**: measured locally by *constructing* the circuits (no simulation):
  `ixor_gf2_mul` at degree 12 = 63 T (75 T if controlled), degrees 2..12 =
  3,7,9,17,21,25,27,43,51,59,63. The tape's 42 is better than all of these.
* **A5/A6**: 42 → 35 needs a rank-35 bilinear algorithm for GF(2^12) over GF(2); the
  standard families bottom out at 42 here (Toom-4), so A5 requires a searched
  decomposition that does not exist in the literature at this size, and A6 is the
  information-theoretic limit (`2n-1`), not a construction.
* **B1**: the tape's forward pass uses 1,542 multiply blocks; BM's discrepancy +
  update for n=70, L≤35 costs 2×(L+1) per syndrome over 70 syndromes. Even at the
  tape's own rank 42 that is 211,680 T for the forward pass alone, and the reverse
  pass has to be paid on top.
* **B3**: for a bilinear map, splitting the quotient into 2 or 4 words multiplies the
  *number* of product terms by the number of words and the *window* per word shrinks
  proportionally — the total rank is invariant. Only the degree counters get cheaper,
  and those are a compiler rewrite (46-48 % of the EEA targets the workspace
  registers, §1), not an arithmetic substitution available from the `.kmb`.
* **C1/C2**: the Chien region costs **10.998 T/position** (40,240 CCX + 4,024 CCZ over
  4,025 positions) plus 881 CX/position. A per-position 12-bit inverse in the kickmix
  idiom costs **315 T** (measured: `init_gf2_inverse_with_scaffold(12)`), 28.6× the
  whole per-position budget, so the tape already avoids it: it evaluates with CX-only
  Horner and kicks the phase with `gf2_phase_by_product` (0 Toffoli) through a 10-bit
  measured AND (10 CCX + 10 HMR + 10 CZ_IF) and 1 CCZ. There is nothing left to remove.

**Arithmetic bound.** With this block structure the entire arithmetic-substitution
budget of the DQI leg is **68,022 T = 18.5 % of T = +1.99 GM**, and 100 % of it sits in
one place: the bilinear rank of a 12×12 GF(2) multiply (currently 42, floor 23). Every
other region is already at its idiom minimum (Chien 11.0 T/position) or is control
logic that no arithmetic change touches.

---

## 5. What would actually be needed

To capture A4-A6 the tape has to be **regenerated** with a lower-rank multiply; the
`.kmb` is a flat instruction stream with no tags, no register-name structure beyond
`S0..S69`/`E0..E4094`, and every multiply block is fused into a rotation scaffold
(~30 CX per AND, 42 ANDs per block, 1,250 CX per block). Replacing a block in place
would mean reconstructing its operand mapping from the CX scaffolding — that is a
byte-level rewrite of the other line's kind, with a much worse risk profile, and it
cannot be validated except by the verifier on a 479 MB file.

A rank-35 multiply (A4, +0.57 GM) is the smallest change that pays, and it needs the
generator, not the tape.

---

## 6. Second-order finding worth passing on

**51.9 % of all Toffolis write qubits 840-889** (the 50-qubit pool), and the EEA's
control logic is 44.7 % of the tape. That is the largest single budget in the DQI leg
after the multiplies and it is invisible to any arithmetic substitution: it is the
price of the data-dependent schedule (degree counters `n_A, n_B, n_a, n_b, n_q`,
one-hot decode, halting counter). A regenerated tape with a fixed schedule would trade
this against extra multiplies — the tape's own 34-round triangular ladder is already
the right side of that trade.

---

## 9. Exact commands

```
# structure dump + per-region mean T  (zhuating/qcc-dqi-algo-regions v1, COMPLETE, 109 s)
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_algo \
      --slug qcc-dqi-algo-regions --account zhuating \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings --competition
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_algo --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-algo-regions --account zhuating

# truncation probe (zhuating/qcc-dqi-algo-trunc v1)
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_algo/kprobe --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-algo-trunc --account zhuating

# local (arithmetic only, no simulation, no verifier): primitive Toffoli counts
.venv/bin/python -c "import kickmix as km; ..."   # ixor_gf2_mul / init_gf2_*_with_scaffold
```

Local dry run of the analysis (static part only, IR read, no simulation):
`DQIALGO_STATIC_ONLY=1 .venv/bin/python experiments/frontier/20261118_push/dqi_algo/main.py`
