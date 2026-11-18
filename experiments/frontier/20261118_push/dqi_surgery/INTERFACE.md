# DQI tape `575b043f` — EEA/Chien interface map (measured, static IR)

Two Kaggle CPU kernels (`zhuating/qcc-dqi-surgery-map`, `...-map2`) read the tape and dumped
every number below. Nothing was simulated, nothing was verified, nothing was written back; both
kernels delete the 479 MB tape before exiting.

```
kmb sha256  575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155
num_ops 57,520,821   num_qubits 890   num_bits 66,726
registers S0..S69 (12 q each, S_i = q 12i..12i+11)  +  E0..E4094 (12 b each)
pool: words 70,71,72,73 (Q840..Q887) + Q888, Q889
```

Evidence files (in `out/`): `survey.json`, `survey2.json`, `chien_trace.json`, `win_fwd_head.txt`,
`win_fwd_tail.txt`, `win_chien_head.txt`, `win_chien_tail.txt`, `win_rev_head.txt`,
`win_rev_tail.txt`, `win2_eea_last_mult.txt`, `win2_pre_chien_5k.txt`, `win2_chien_to_rev.txt`,
`win2_tape_head.txt`, `win2_tape_tail.txt`, `kernel.log`, `kernel2.log`.

---

## 0. The headline correction: the EEA does **not** end at 30,335,416

The three-way split inherited from `dqi_align` uses the Chien **anchors** (the `12 × BIT_STORE1_IF`
run that opens each Chien position). That boundary is *inside* the first Chien block, not at its
left edge. Measured:

| op | what it is |
|---|---|
| **30,151,420** | `CCX S1[0], S3[0] -> Q868` — the **last multiplication CCX of the forward EEA** |
| 30,151,421 | first op after it: `CX Q868, S7[9]` (fan-out of that product) |
| 30,151,421 … 30,335,415 | **183,995 ops, 11 Toffoli**, 183,037 `CX`, 479 `SWAP`, 272 `BIT_INVERT_IF`, 71 distinct words 0…71 |
| 30,335,009 … 30,335,027 | the 10-CCX chain + `X S57` of the *first* Chien position (tested word `S57`) |
| 30,335,415 | `BIT_STORE0 B53665` (closes that position) |
| 30,335,416 | `12 × BIT_STORE1_IF E2730[0..11]` — the first *anchor*, i.e. the **second** position |

So the true, Toffoli-meaningful boundary of the forward EEA is **30,151,421**, and the region
`[30,151,421, 30,335,416)` is a **0-Toffoli realignment sweep** (see §4). Cutting at 30,335,416
would slice through the first Chien position's conjunction, so it is not a usable splice point.

Consequence: `[17,576,206, 30,151,421)` holds **153,175 CCX** = 3,647 × 42 + 1, and the 11
Toffoli inside the sweep are one complete Chien position (10 CCX + 1 CCZ). The old region count
153,186 is 153,175 + 11, exactly as the arithmetic requires.

## 1. Condition-stack depth at every candidate cut (re-checked)

| cut | depth before | depth after | note |
|---|---:|---:|---|
| 17,576,206 (EEA start) | 0 | 0 | first op is `CCX S0[0],S1[0] -> Q840`, no shift |
| 30,151,421 (EEA Toffoli end) | 0 | 0 | **the real forward cut** |
| 30,334,7xx (align → Chien) | 0 | 0 | inside the sweep, 0 T either side |
| 30,335,416 (nominal, Chien anchor) | 0 | 0 | usable but wasteful; loses the first position |
| 35,627,262 (Chien → rev) | 0 | 0 | |
| 57,520,821 (tape end) | 0 | 0 | last op is `BIT_INVERT_IF E1365[10] ← E1365[11]` |

All six are depth 0. The depth-0 property is *not* the constraint; the constraint is which
qubits/bits are mid-flight (§3).

## 2. What the Chien block reads — the per-position template, measured

Full run-length-encoded opcode sequence of one position (from `survey2.json:template_rle`,
1,240 ops of a 2-position window, so ~620 ops per position):

```
CX×121                                      <- tail of the previous position (Horner contraction + its inverse)
BIT_INVERT×65, BIT_STORE0, BIT_STORE1×12, POP_CONDITION
X×12                                        <- complement the tested word
(R, CCX)×10                                 <- 10-CCX conjunction   Q888 = AND_{k<=10} ~S(.)[k]
BIT_STORE0×11                               <- clear 11 scratch flags
(BIT_INVERT, POP, SWAP, BIT_INVERT×3, POP)×11   <- the 11-stage selection cascade (SWAP of 2 qubits *inside* one word)
(POP×2, CX)×12 with CCZ in the middle       <- mask contraction, phase applied here
(BIT_INVERT×3, SWAP, POP×2)×11             <- cascade, exactly reversed
(HMR, CZ)×10                                <- coherent uncompute of the conjunction, 0 Toffoli
X×12, POP, BIT_STORE0
```

Register footprint of one position (`chien_blocks.first`, window anchor−620 … anchor+620):
qubit words `{6, 10, 11, 15, 52, 54, 55, 56, 57, 59}` (all 12 bits) + pool `{72, 73, 74}`; bit
registers `E2730` (the current mask) + `E3610` (next) + the scratch flags. Per position the block
touches **exactly two S words at full width** (the tested word and one auxiliary) plus the mask
register of that position and the 13 scratch flags.

**"40 op template"**: the Toffoli-bearing core of a position is 12 `X` + 10 `(R,CCX)` + 11
`BIT_STORE0` + 1 `CCZ` = 34 declarations + 6 wrappers ≈ 40 ops; the remaining ~580 ops of the
position are `CX`/`SWAP`/`BIT_INVERT_IF` bookkeeping at 0 Toffoli.

## 3. Liveness across the cuts (±3,000-op windows)

| cut | live across | composition |
|---|---:|---|
| 17,576,206 (EEA start) | **32** | `S0[0..11]`, `S1[0..11]`, pool `Q840,842,844,845,846,848,849,851` |
| 30,335,416 (nominal fwd/Chien) | 35 | flags `B49782, B53665..B53676`; `E2730[0..11]`; pool `Q864,869,870,871,876,877,878,879,881,888` |
| 35,627,262 (Chien/rev) | 35 | flags `B49782, B53665..B53676`; `E4079[0..11]`; pool `Q864,869,870,871,876,877,878,879,881,888` |

Three facts fall out of this and they are the interface contract:

1. **The EEA's input is `S0`, `S1` and 8 pool qubits.** Nothing else. Words `S2..S69` are touched
   before op 17,576,206 and never again inside the EEA's first window — they are already in place
   (the syndrome array was loaded/aligned upstream). The first multiplication is
   `S0[0] × S1[0] -> Q840[0]`.
2. **No `S*` word is in flight across either Chien boundary.** The Chien stage is a pure *phase*
   stage at word level: at both ends the syndrome array is quiescent, and the only carried quantum
   state is **10 pool qubits** (subset of `Q864..Q889`) plus the mask registers and flags. This is
   why the Chien can be kept verbatim while both EEA passes are replaced: the S-array state it
   consumes is created entirely before the cut and destroyed entirely after it.
3. The 13 classical flags and one `E` register that straddle each boundary belong to the *first /
   last position's own* bookkeeping (the window sees ~5 positions), not to a carried interface.

## 4. The 183,995-op, 0-Toffoli stage between the EEA and the Chien

`[30,151,421, 30,335,416)`: `CX 183,037`, `SWAP 479`, `BIT_INVERT_IF 272`, `CZ_IF 10`,
`R 10`, `HMR 34`, `X 24`, `BIT_STORE0 14`, `BIT_STORE1_IF 12`, **`CCX 10` + `CCZ 1`** (the first
Chien position). So ≈183,000 `CX` of pure data movement at 0 Toffoli.

Word profile in 20k-op bins shows a monotone *sweep*: the "hot" words walk
`{2,3,6,10,11,14,15} → {18,22,26,30,34} → {38,42,46,50,54} → {54,58,62,67,68,70} → {8,9,12,13,…,65}
→ {6,10,11,…,64} → all 71 words`, and by the last bins **all of words 0…71 are touched**. That is
the signature of the reference's `_initial_shift_loop`: 69 steps, each rotating one 12-bit **lane**
(`basis vector` across words) left by one word over a suffix of the array, with a zero-test gate.
Cost: 0 Toffoli (a lane rotate is `CX`/`SWAP` only), ~2.1 × 12 × Σ(70−s) `CX`.

**It is a realignment, and it is the only stage between the two objects.** For the surgery this is
good news: the new EEA does **not** have to emit the Chien's layout directly — it only has to emit
the layout the sweep expects. And since the sweep is 0 T, deleting it buys nothing: keep it.

## 5. Chien trace — all 4,024 positions (`chien_trace.json`)

Per position `n`: the anchor op, the mask register index `j`, the tested word (`x_word`, from the
`12 × X` run), the `CCZ` words, the first `SWAP` qubit pairs, op counts.

| quantity | measured |
|---|---|
| positions | 4,024 anchors inside `[30,335,416, 35,627,261)`; a 4,025th position straddles the left edge (its 10-CCX chain is at 30,335,009…30,335,027 and its tested word is `S56`) |
| `j` values | 4,024 **distinct**, range 7 … 4,094 (`j` is the position index, visited in a permuted MBUC order) |
| tested word | **32 distinct values**: `{8+4k, 9+4k : k=0..14}` ∪ `{69, 71}` |
| is the tested word a function of `j`? | **yes, no exceptions** (`n_j_with_multi_xword = 0`) |
| Δ(tested word) between consecutive positions, mod 70 | `+1`: 1,886, `−1`: 1,762, `+2`: 125, `−2`: 125, `−5`: 125 |
| linear fits | `word = (13 + 35·n) mod 70`: 252/4,024 hits; `word = (13 + 35·j) mod 70`: 134/4,024 — **not linear** |

Reading:

* The Chien **does not rotate the σ array as a whole**: within a position the 22 `SWAP`s form a
  cascade (`S.̲[0] ↔ S.̲[k]`, k=1..11) that is emitted *and* reversed inside the same position
  (§2). Δword ≈ ±1 between positions is a *compile-time* choice of which word to test, and it is a
  function of `j` alone.
* The tested words come in **pairs two apart, four apart across pairs**: (8,9), (12,13), …,
  (64,65). Combined with the EEA's own structure — the very first multiplication is
  `word 0 × word 1`, and the multiply-control ladder is `0,2,4,…,44` (stride 2) with a second
  ladder `46,50,54,58,62` (stride 4) — this is consistent with **the 70-word array being two
  interleaved 35-word polynomials**, i.e. `a_k = word 2k`, `b_k = word 2k+1`. Under that reading
  `{8,9} = (a_4, b_4)`, `{12,13} = (a_6, b_6)`, … so the Chien walks the array in steps of *two
  coefficients*, testing one and phasing against the other.
* `69` and `71` are the two singletons: word 69 = `b_34` (last word of the interleaved b) and
  word 71 = pool word 71, i.e. the boundary cases of the same walk.

**TODO-1 (not measured, 1 kernel pass):** which coefficient index each word holds (left- vs
right-aligned, i.e. is `word 0` the *leading* or the *constant* coefficient) and which word carries
ω. Both are decided by one dump: the first three multiplication blocks of the forward EEA with
their `CX` fan-out resolved (which output bit is written by which `γ_l` term). The evidence above
fixes the *pairing* and the *traversal*, not the orientation.

## 6. Region opcode censuses (why "fixed schedule" is right)

| op | fwd EEA `[17,576,206, 30,335,416)` | Chien `[30,335,416, 35,627,261)` | rev EEA `[35,627,262, 57,520,821)` |
|---|---:|---:|---:|
| `CCX` | 153,185 (0 conditioned) | 40,240 (0) | 168,587 (0) |
| `CCZ` | 1 | 4,024 | 1,952 |
| `CX` | 12,363,511 (60 cond) | 3,546,384 (0) | 13,857,595 (18,120) |
| `SWAP` | 58,470 (0) | 88,528 (0) | 226,522 (0) |
| `CZ` | 147,156 (147,153 `_IF`) | 40,240 (all `_IF`) | 338,927 (337,960 `_IF`) |
| `HMR` | 13,042 | 40,240 | 18,712 |
| `Z` | 11,594 (11,591 `_IF`) | 0 | 27,610 (27,439 `_IF`) |
| `BIT_INVERT` | 3,527 (all `_IF`) | 924,565 (all `_IF`) | **6,441,970 (all `_IF`)** |
| `BIT_STORE0` | 619 | 52,312 | 166,451 |
| `BIT_STORE1` | 18 (all `_IF`) | 48,288 (all `_IF`) | 2,207 (2,183 `_IF`) |
| `POP_CONDITION` | 216 | 370,208 | 631,274 |

Two conclusions that matter for the spec:

* **The forward EEA's Toffoli stream is unconditioned** — 153,185 `CCX` with zero condition bits,
  and 153,175 of them = 3,647 complete 42-CCX multiplications. There is no data-dependent branch in
  the arithmetic: the schedule is fixed and the quotient rows are *unrolled*. A 69-step divstep with
  a fixed schedule is therefore the *same class* of object and needs no counter.
* **The reverse EEA is not the op-level adjoint of the forward one**: 6,441,970 `BIT_INVERT_IF` and
  166,451 `BIT_STORE0` appear only on the way back, and `SWAP` is 3.9× the forward count. The two
  passes are two different *implementations* of mutually inverse maps. Consequence for the surgery:
  "new reverse = forward's exact adjoint" is still legitimate (the composite must be the identity),
  but a T-count symmetry argument cannot be used as a correctness check, and the reverse pass will
  have a very different op census from the tape's.

## 7. The multiplication block, at the boundary

`win2_eea_last_mult.txt` (ops 30,151,020…30,151,420) shows the last EEA block directly:

```
30151043  CX Q868,Q884 ... CX Q868,Q876          <- fan-out of the product into 13 pool qubits
30151056  CX Q868,S7[0], S7[1], S7[5], S7[6], S7[7]   <- ... and into S7
30151420  CCX S1[0], S3[0], Q868                 <- the rank-1 term, one scratch qubit
30151421  CX Q868,S7[9], S7[7], S7[5], S7[1], ... (the inverse fan-out)
```

So the final write targets of the forward EEA are **pool word 72 (`Q864..Q875`), 73, 74 and
`S7`**, i.e. the last block accumulates into a pool word and folds `S7`. The `42` terms of a block
are 42 `CCX` onto one scratch qubit reused in a running XOR chain (already established in
`dqi_block/RESULT.md`); the block operand ladder is stride-2 words, confirming the interleaved
`a/b` reading of §5.

## 8. What is proven and what is not

**Proven from the tape (static IR, no simulation):**
cut depths 0 at all six candidates; the real EEA/Chien boundary at 30,151,421; the 0-Toffoli
183,995-op realignment sweep and its word footprint; the per-position Chien template and its
register footprint; the tested-word function of `j` and its 32 values; Δword = ±1 in 90.7 % of
consecutive positions; zero conditioned `CCX` in the forward EEA; the forward/reverse op-census
asymmetry; the last EEA block's write targets; the interleaved stride-2 operand ladder.

**Not proven (TODO):** coefficient orientation and left/right alignment (§5 TODO-1); which word
holds ω; whether the "pairs" are `(a_k, b_k)` or `(σ_k, σ_{k+1})`.

None of the TODO items can change the *splice points* or the *T budget*, and all of them are
caught by the protocol in `VERIFY.md` (a wrong layout gives `value_errors > 0` on the first salt).
