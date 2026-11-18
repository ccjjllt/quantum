# DQI: standalone rebuild of `_initial_shift_loop` (reference side)

Kaggle CPU kernel: `zhuating/qcc-dqi-refshift` (v6, `enable_gpu=false`, `enable_tpu=false`).
Static IR build only — nothing simulated, no official verifier run, no submission.
Kernel wall time 9.8 s; the 479 MB tape was decompressed and read in the same kernel
and deleted before exit (`files left ['reference_shift.json']`).

Question: are the two big Toffoli clusters of tape `575b043f` the reference
`_initial_shift_loop`?

## What was built

| item | value |
|---|---|
| reference generator | `verifiers/dqi/dqi_reference_circuit.py`, copied out of the competition mount (original untouched) |
| source sha256 | `2b8e1b80a806157c333a7e308eaf2499ee09de499efbc05875202c327959959e` (identical to the repo copy) |
| `_initial_shift_loop` | lines 140–164, called exactly as on lines 123 / 131 |
| kickmix | `0.1`, from `competition/kickmix/kickmix.so` |
| parameters | `n_syndromes=70`, `degree=12`, `m=73`, `logm = m.bit_length()+1 = 8` |
| registers | `reg_a = [alloc(12)x3] + S0..S69`, `n_A = alloc(8)`; the 3 scratch words are global words **A70/A71/A72**, so `reg_a[3+i] = S{i}` |
| preamble | `x([reg_a[0][0], n_A[0]])`, `gf2_iadd(70, n_A)` → 5 `X`, 0 Toffoli |

Both directions were built, plus a `logm=7` variant (the brief's assumption) for sensitivity.
Nothing is freed, so the stream is exactly `preamble + loop`.

Qubit layout (from `vqcc_ir` register ids): `S0..S69` = 0..839, `A70..A72` = 840..875,
`nA` = 876..883, the per-step `ctrl` ancilla = 884. `builder.mark()` emits `@enter/@exit`
INFO_TAG instructions, so the 69 `shift_step` boundaries are exact.

## Reference numbers (loop only, tags excluded)

| | forward | adjoint |
|---|---|---|
| ops (physics) | **43,919** | **42,815** |
| ops incl. INFO_TAG | 46,265 | 45,023 |
| `CSWAP` | **28,980** | **28,980** |
| `CCX` | **1,932** | **1,932** |
| `CX` (native, unconditional) | 586 | 586 |
| `SWAP` | 0 | 0 |
| `CCZ` | 0 | 0 |
| `HMR` | 1,794 | 1,794 |
| `R` | 1,794 | 1,794 |
| `CZ` / `CZ_IF` | 828 / 828 | 828 / 828 |
| `X` | 4,831 | 3,727 |
| `Z` / `Z_IF` | 276 / 69 | 276 / 69 |
| `PUSH_CONDITION` / `POP_CONDITION` | 897 / 897 | 897 / 897 |
| `NEG` | 207 | 207 |
| `toffoli_like` | **30,912** | **30,912** |
| T if every CSWAP→`CX+CCX+CX` (tape idiom) | **30,912** | **30,912** |
| ops if every CSWAP is expanded (tape idiom) | 101,879 | 100,775 |

`logm=7` variant (forward): `CCX` 1,794, `CSWAP` 28,980, T **30,774** (138 T cheaper —
the 8-bit `flip_if_less_than` loses one comparison stage). The official build uses 8 bits.

### Per-`shift_step` structure (exact, from the mark tags; `steps_consistent=true` for both)

`lane_len L = 70 − step`, and each step emits **`CSWAP = 12·(L−1)`** — one lane rotation
per bit index — plus a fixed non-CSWAP overhead of **203–237 ops**:

```
ops(step) = 12*(70-step-1)
          + [28 CCX, 8-9 CX, 26 HMR, 26 R, 12 CZ, 12 CZ_IF, 13 PUSH, 13 POP,
             1 Z_IF, 2-7 Z, 1-6 NEG, 61-74 X (forward) / 45-58 X (adjoint)]
```

so `sum_step CSWAP = 12·Σ(L−1) = 12·2415 = 28,980` and `sum_step ops = 43,919`.
Only `CSWAP`, `X`, `Z`, `NEG` vary between steps; `CCX = 28`, `HMR = R = 26`,
`CZ = CZ_IF = 12`, `CX ∈ {8,9}` are step-independent (the `flip_if_less_than` constant
`n − step` and the `isub` constant change the NOT/measurement pattern).

| step | lane | ops | CSWAP | CCX | CX | HMR | first CSWAP |
|---|---|---|---|---|---|---|---|
| 0 | 70 | 1,045 | 828 | 28 | 8 | 26 | `ctrl, S69.0, S0.0` |
| 1 | 69 | 1,032 | 816 | 28 | 9 | 26 | `ctrl, S69.0, S1.0` |
| 2 | 68 | 1,014 | 804 | 28 | 8 | 26 | `ctrl, S69.0, S2.0` |
| … | | | | | | | |
| 67 | 3 | 239 | 24 | 28 | 9 | 26 | `ctrl, S69.0, S67.0` |
| 68 | 2 | 215 | 12 | 28 | 8 | 26 | `ctrl, S69.0, S68.0` |

Adjoint runs the same steps in reverse (step 68 → step 0), same CSWAP total.

**Structure detail that matters for the tape comparison.** The 828 CSWAPs of step 0 are
*not* 69 groups of 12; they are **12 lane rotations of 69 swaps each**, ordered by bit
index (measured `cswap_per_bit = {0:69, 1:69, …, 11:69}`, and the swap operands span words
`S0..S69`). The first 69 CSWAPs are all bit 0 — `(ctrl, S69.0, S0.0)`, `(ctrl, S68.0, S1.0)`,
…, `(ctrl, S35.0, S34.0)` then the second mirror — because each lane rotation is the classic
mirror+mirror cyclic rotate (`reverse(lane)` then `reverse(lane[0:L−1])`), 69 swaps for a
70-word lane. Step 1 is 68 swaps per bit over `S1..S69`, step 68 is 1 swap per bit between
`S68` and `S69` (`cswap_per_bit = {0:1,…,11:1}`).
The zero-fill comes from the wrap: `ctrl = [top word == 0]`, so the word that wraps to the
bottom of the shrinking window is always a zero.

## Tape comparison (same kernel, tape sha `575b043f…`, 890 qubits, 57,520,821 ops, 367,989 static T)

| | tape fwd cluster | tape rev cluster | reference fwd loop |
|---|---|---|---|
| span | [19,508,954, 21,385,877) | [46,230,185, 52,842,219) | — |
| width | 1,876,923 | 6,612,034 | 43,919 (101,879 if CSWAP expanded) |
| `CCX` | 29,543 | 64,050 | 1,932 |
| `CCZ` | 0 | 1,724 | 0 |
| `toffoli_like` | 29,543 | 65,774 | 30,912 |
| `CX` | 1,826,827 | 4,326,547 | 586 |
| `SWAP` | 8,397 | 162,848 | 0 |
| `CSWAP` | **0** | **0** | 28,980 |
| `CX+CCX+CX` Fredkin triples | **0** | **0** | n/a (CSWAP opcode) |
| CCX with CX on both sides, wrong pair | 29,165 | 63,133 | — |
| `HMR` | 1,600 | 4,818 | 1,794 |

The "Fredkin triple" test is exact: a `CCX(c,t1,t2)` whose predecessor and successor are
both `CX` on the same unordered pair `{t1,t2}` (both decomposition conventions accepted).
Result: **0 triples in both clusters**, i.e. the tape never emits a `CX+CCX+CX` swap
anywhere in the two big clusters. The tape does use real `SWAP` ops (8,397 / 162,848),
which the reference loop never emits.

### Answers

**1. Reference forward-shift T, and the distance to 29,543.**
T = `CCX 1,932 + CSWAP 28,980` = **30,912** (each CSWAP = 1 Toffoli-like in the tape idiom).
The tape's fwd cluster is 29,543, i.e. **1,369 T below the reference (−4.4 %)**. So the
*magnitudes* are close, and that is the whole coincidence: 93.8 % of the reference's T is
one CSWAP per lane step, whereas the tape's T sits inside 1.83 M CX. A T-count match at the
5 % level is not evidence of identity — the op budget is off by 18–31×.

**2. Is the reference's idiom `CX+CCX+CX`? No.** The reference emits `CSWAP` as a single
opcode (28,980 of them, `SWAP` = `CCZ` = 0). Expanding it the way the tape expands
controlled swaps (`CX+CCX+CX`) would give 57,960 extra CX and 101,879 ops; the tape
clusters contain neither the opcode nor the expansion. Per-step relation to array length:
`CSWAP = 12·(L−1)` with `L = 70 − step`, i.e. linear in the lane length, and the step's
total is that plus a constant ~203–237 non-CSWAP ops.

**3. Can 1,826,827 CX be explained by 28,980 CSWAPs? No.** 28,980 CSWAPs need 57,960 CX.
The cluster has **1,826,827 CX = 31.5×** that, and 1,876,923 ops = 18.4× the reference's
expanded 101,879. In the other direction the CCX budget is already spent: 28,980 of the
cluster's 29,543 CCX would be CSWAP middles, leaving 563 CCX for the zero tests and
comparisons that cost the reference 1,932 CCX. Also `HMR` = 1,600 vs 1,794 with a
completely different per-step profile (reference: 26 `HMR` + 26 `R` per step, 828 `CZ_IF`
total; tape head: 161 `HMR`, 989 `CZ_IF`, 152 `BIT_INVERT_IF` in 20,000 ops).

**Verdict: neither cluster is `_initial_shift_loop`** (nor any CSWAP/rotate form of it).
The reference loop is a 28,980-CSWAP permutation of 70 syndrome words; the tape's clusters
are dominated by CX fan-out out of one scratch bit (head of the fwd cluster: `CCX(504,516,868)`
— controls in syndrome words 42/43, target bit 4 of scratch word 72 — followed by ≈7 `CX`
from 868 into the other bits of word 72 and bit 11 of word 73: an AND-then-XOR accumulate
shape, not a word swap).

## Bucket barrel-shifter replacement (T upper bound)

Same function: `k` = number of leading zero words of the 70-word window `S0..S69`; one
barrel rotate up by `k` with zero fill of the low `k` positions, `n_A −= k`. This is exact:
a step rotates only while the top word is zero, so `k` is the leading-zero count and the
composite of the shrinking-window rotations equals one rotate of the full window by `k`
(the wrapped word is always a zero).

| component | count | T (1 CCX per CSWAP, tape idiom) |
|---|---|---|
| barrel: `ceil(log2 70) = 7` levels × 70 words × 12 bits | 5,880 CSWAP | 5,880 |
| leading-zero test: 70 × 11 CCX (12-bit zero test) | 770 CCX | 770 |
| … uncompute of the zero flags | 770 CCX | 770 |
| priority encoder (unary → 7-bit `k`), 70 × 7 | 490 CCX | 490 |
| `n_A −= k` (8-bit minus 7-bit, loose) | 30 CCX | 30 |
| **total** | | **7,940** |

≈ 20,220 ops in the tape's 3-op CSWAP idiom. Savings: **−21,603 T (−73.1 %)** against the
tape fwd cluster's 29,543, and **−22,972 T (−74.3 %)** against the reference loop's 30,912.
With native CSWAP the barrel's 5,880 swap levels are still 5,880 Toffoli-like, so the bound
is 7,940 either way; the only soft term is the 30-CCX `n_A` subtract.

For scale, in our own generator both shift passes cost 2 × 30,912 = **61,824 T (16.8 % of the
tape's 367,989 static T)**; the barrel version of both passes would cost 2 × 7,940 = 15,880 T,
a saving of **45,944 T per circuit (12.5 % of the tape's static T)**. The two tape clusters
together are 95,317 T (25.9 %), so if an alignment of this shape is what they implement, the
barrel bound is the target to rewrite it against.

## Verification scope

* Computed from a real build in the Kaggle CPU kernel and a static read of the emitted
  `.kmb` with the competition's `vqcc_ir.py`; `steps_consistent=true` on the forward and
  adjoint builds (per-step CSWAP/CCX/ops sums equal the whole-loop census; per-step
  `CSWAP == 12·(lane_len−1)`).
* Tape figures are the cluster censuses measured in the same run and agree with the
  earlier line (`T 29,543` / `65,774`, `CX 1,826,827` / `4,326,547`, `SWAP 8,397` / `162,848`).
* No simulation, no verifier, no leaderboard run. The barrel figure is a cost bound on
  paper, not a built circuit — it has not been verified or emitted.

## Files

| file | contents |
|---|---|
| `reference_shift.json` | full result (541 KB): sources, params, forward/adjoint/logm7 censuses, the 3,000-op symbolic heads (`name, cond, q0, q1, q2` + name table + label map), all 69 per-step records (incl. `cswap_per_bit` and the full per-step census), tape cluster censuses + 300-op tape head, comparison, barrel bound |
| `k_shift/main.py` | the kernel (v6) |
| `k_shift/kernel-metadata.json` | CPU-only metadata (`zhuating/qcc-dqi-refshift`) |
| `out/qcc-dqi-refshift.log` | kernel log |
| `out/reference_shift.json` | kernel output (identical, sha `47cb7440dbf9a6d720af…`) |
