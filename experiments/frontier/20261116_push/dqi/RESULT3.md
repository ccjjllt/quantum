# DQI T-axis push — 2026-11-16 (part 3)

Mandate: keep the 24-bit temporary (Q unchanged), cut mean T instead. Base = v12 source
(889 Q, T = 383,156.29 verified). Targets: T ≤ 361.5 k (GM 28.26) or ≤ 356 k (GM 28.41).

## 0. Outcome

**The v12 line cannot pay for itself at any achievable T, and the proposed v15 scheduling levers are
T-neutral by construction.** Concretely:

1. **A v12-derived 889-Q circuit needs a −3.71 % T cut just to *tie* today's shipped circuit**
   (889 Q ties 347.375e9 only at T ≤ 368,940, vs 383,156 measured). A 1 % cut leaves it 2.7 % *worse*
   than the 890-Q tape we already ship. So "any T reduction ≥ 1 % is valuable" is true only on the
   890-Q tape, not on v12.
2. **The v12 tape's Toffoli surface is saturated in exactly the same four classes that are saturated
   on the 890-Q tape** (§2, measured: 0 / 0 / 0 / 0 on 384,003 Toffoli-likes). The T that remains is
   the arithmetic itself. The shipped circuit's 4 % T edge over v12 is explained completely by the
   v13 line having **no conditional SWAPs at all** (v12 has 12,384 CSWAP; shipped has 0) — that work
   is already banked.
3. **The three suggested v15 changes do not reduce Toffoli count** (§3): serialising the rank-42
   products does not change the number of ANDs (42 per GF(2^12) product either way), the
   accumulator+shadow fusion is a *qubit* move (and it is exactly the in-place-division blocker from
   `RESULT2.md` §4), and the products themselves are already at proven-optimal rank.
4. Therefore there is no T ≤ 361.5 k candidate to package, and **nothing was submitted**.

## 1. The T budget, made explicit

Cost = R·Q²·T, R = 1.19126046. The shipped circuit is Q = 890, T = 368,139.49 → 347.375e9 (GM 28.091).

| target | GM | cost needed | T needed at Q=890 | T needed at Q=889 |
|---|---|---:|---:|---:|
| tie today | 28.091 | 347.375e9 | 368,139 (0 %) | 368,940 (−3.71 %) |
| 28.26 | +0.17 | 341.11e9 | 361,500 (−1.80 %) | 362,290 (−5.45 %) |
| 28.41 | +0.32 | 335.92e9 | 356,000 (−3.29 %) | 356,780 (−6.88 %) |
| 28.65 (gold) | +0.56 | 327.4e9 | 347,000 (−5.7 %) | 347,760 (−9.2 %) |

So the whole T programme has to happen **on the 890-qubit tape**; porting anything into the v12 source
starts 3.71 % in the hole. And on the 890 tape the four sound peephole classes are measurably empty
(`RESULT.md` §5: 0 cancel pairs, 0 \|0>-controls, 0 dead writes to `R`, 0 dead writes to unused `HMR`,
all 54,075 bits referenced), with a **null round-trip control that reproduces `ccc2ab84…`, T
368,139.490 and 0/0 errors bit-for-bit**, so those zeros are exact, not sampling artefacts.

## 2. The v12 tape, measured (k9)

`zhuating/qcc-dqi-v12tscan`: build the pinned source → `7cbe8ecf…` → unpack the `.kmb` → run the same
exact scans (per-wire write-version tracking + a sorted 63 M-pair `(wire, op)` touch index) → verify
anything that survives.

```
BUILD 0  455,590,024  7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9
A3  Q 889  n 52,930,855  staticT 384,003  nbits 53,911
A4  opcodes {0x1: 3,039,548 (PUSH/POP), 0x10: 46,469, 0x11: 108,090, 0x12: 48,210,
             0x20: 538,932 (CZ), 0x21: 31,293,155 (CX), 0x22: 378,664 (SWAP),
             0x30: 7,000 (CCZ), 0x31: 364,619 (CCX), 0x32: 12,384 (CSWAP),
             0x40: 1,527,327, 0x41: 54,936, 0x42: 15,439,990 (bit ops), 0x50: 71,531 (HMR)}
B0  touch index 65,847,811 (wire, op) pairs
C0  exact cancel pairs                 0
C1  degenerate-operand Toffolis        0
C2  |0>-control Toffolis               0
C3  dead to R 0 / dead to unused HMR   0
C4  total sound deletions 0  -> T stays 384,003
C5  needed to tie the 890 tape: T <= 368,940, i.e. a 15,063 T cut
D0  no candidate: the v12 T surface is saturated too
```

So the v12 tape is saturated in **the same four classes** as the shipped tape, decided exactly (full
write-version tracking, no simulation sampling).

### 2.1 Where the shipped circuit's 4 % T edge over v12 actually comes from

The two tapes differ by exactly 15 k Toffoli-likes, and the difference is one opcode:

| opcode | v12 (889 Q) | shipped (890 Q) | Δ |
|---|---:|---:|---:|
| CCX (0x31) | 364,619 | 362,984 | −1,635 |
| CCZ (0x30) | 7,000 | 6,026 | −974 |
| **CSWAP (0x32)** | **12,384** | **0** | **−12,384** |
| static T | 384,003 | 369,010 | −14,993 |

i.e. **the v13/v14 line's entire T advantage is that it contains no conditional SWAPs.** A Fredkin is
`CX(b,c); CCX(a,c,b); CX(b,c)` = 1 Toffoli-like either way, so *converting* a CSWAP does not save T —
the v13 design had to **eliminate the conditional swaps structurally** (its swaps are unconditional
378 k `0x22` SWAPs plus classically-conditioned CX). That work is already in the circuit we ship.
Applying it hypothetically to v12 would give 371,619 T at 889 Q = 349.2e9, still worse than the
347.375e9 we already have.

## 3. Why the three v15 levers are T-neutral

**(a) Serialising the rank-42 products.** A GF(2^12) product in this design is
`⊕_{t=1..42} c_t·(L_t(a) ∧ M_t(b))`: 42 ANDs into fresh wires, each AND = 1 CCX, then the 42
constant multiples are pure CX fan-out. The AND wires are erased by measurement (MBU), which costs
**0** Toffoli-like gates. So a product is exactly **42 T** and that number is a function of the rank,
not of the schedule. Serialising the terms (fewer live AND wires) changes the number of *CX* gates and
the live-wire count; it cannot change 42. The measured value in this family is 42-T per `mul_xor0`
(3,406 occurrences = 143,052 T in the sibling decomposition) and 99-T per `mul24` (390 occurrences =
38,610 T) — i.e. the multipliers are **already** at the AND-count floor.

**(b) Fused accumulator + shadow.** This is the `v ← v/u` in-place multiply of `RESULT2.md` §4. It
saves 24 *qubits*, not Toffolis: the same 99-T cofactor product and the same 84-T scalar product must
be executed either way. It is also the object that provably needs the third 24-bit register.

**(c) Two working words.** In this decoder, "two words" *is* the pair (head, carry) that
`divide_deferred` consumes; the third register is the product destination. So (c) reduces to (b).

**(d) The rank itself.** `rank(GF(2^3)) = 6` and `rank(GF(2^4)) = 9` are proven optimal (complete
enumeration, 2,869,685 candidates, 0 solutions — `experiments/.../20261112_mulrank`), giving 42 = 7×6
and 99 = 11×9. Lowering 42 or 99 is an open problem in bilinear complexity, not an engineering change.

Where the remaining T actually sits (sibling decomposition, measured): extract 59.2 k, synthesis
31.6 k, convert 60.7 k, scan 44.3 k, unconvert 62.5 k, unsynthesis 40.4 k, unextract 96.9 k. The
uncompute half is 50.5 %, and it is the half that MBU would attack — but MBU applies only where the
AND target is untouched between compute and uncompute, and that class is empty on both tapes (the
public `cmerge` + `8×HW-27` pass already harvested the 8 sites that existed on the 890 tape, and the
v12 tape shows the same zeros in §2). Everything else is genuinely load-bearing phase arithmetic: the
uncompute restores values that the phase repayment later reads.

## 4. What a real T win would require

Given (a)–(d), a ≥1 % T cut means one of:

1. **A cheaper decoder structure** — fewer multiplications per syndrome pass (the extractor does
   ~67 divisions each way, each costing one 99-T cofactor product + two 42-T scalar products + a
   191-T inverse-norm pair). Halving the number of divisions, or replacing the EEA by a
   retain/replace Berlekamp–Massey form (fewer field inversions), is the only ≥ 5 % lever. The
   published BM decoders are far more expensive overall (arXiv:2610.22367's discovered circuit:
   442,397 T at 1,837 Q), so this is not a safe bet.
2. **More conditional Toffolis.** Static 369,010 vs mean 368,139 ⇒ only 871 Toffolis fail to fire.
   Raising that requires a decision machine over measured bits that provably implies a gate is a
   no-op — the previously measured ceiling for the sibling family was 14.2 % of T with a
   "n−1 zero-test" lower bound that was never constructed.
3. **Rank improvements** below 42 / 99 — open mathematics.

None of these is available in this session, and each is the same class of work as the Q redesign.

## 5. Receipts

| kernel | ref | purpose |
|---|---|---|
| k9 | `zhuating/qcc-dqi-v12tscan` | build v12, exact T-surface scan, verify if anything survives | **complete**: 0 deletions in all four classes (§2) |
| k8 | `zhuating/qcc-dqi-v12build` | v12 build gate: `7cbe8ecf…` MATCH, verifier PASS 889 Q / 383,156.29 T / 360.733e9 / 0-0 |
| (dataset) | `zhuating/qcc-dqi-source-v12` | private Apache-2.0 copy of the v12 source tree |

## 6. Verdict

No T candidate exists on either tape inside the sound peephole classes, the v12 line starts 3.7 %
behind and its levers are T-neutral, and every remaining ≥ 1 % T idea is the same decoder-level
rewrite that the Q axis needs. **DQI is closed for this competition window at 890 Q / 368,139 T /
347.375e9 unless a new decoder generation appears.** No submission was made.
