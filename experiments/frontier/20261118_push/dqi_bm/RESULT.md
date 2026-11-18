# DQI leg — feasibility of a Berlekamp–Massey decoder at ≤ 890 qubits

Line: `dqi_bm` (account `zhuating`). Question: can the frontier BM Reed–Solomon decoder
(arXiv:2610.22367, 440,000 Toffoli / 1,837 qubits) be packed into **Q ≤ 890** and brought
under **mean T ≤ 264,691**, the DQI cost that puts the shipped triple at GM 31.42723?

**Verdict: no, on both axes, and the width axis is structural, not an engineering gap.**
The BM decoder's live state at the peak of its forward pass is 840 (syndromes) + 864
(σ and τ) = **1,704 qubits before one qubit of scratch**, i.e. 1.91× our tape; at its own
floor width it would have to run at **T ≤ 100,148** to match our tape and **≤ 72,207** to
reach the 31.43 tier, while its locator alone — the cheapest published locator of any
kind — is 259,448 T. Fitting it into 890 would need σ+τ inside the syndrome array, which
is impossible because all 70 syndrome words are read again in round 70.

The line is closed with exact arithmetic below. One **measured** by-product is worth
keeping: the tape's own clean 28-round ladder runs at exactly **41.0 T per multiply
position + 109 T per round** (r² = 0.9985), i.e. *better per multiply than the published
BM*, and the tape's remaining 242,201 T of non-multiply cost is concentrated in 93 small
clusters plus one 65,774 T cluster. That is where any 890-qubit T cut has to come from —
not from BM.

All measurement ran on Kaggle CPU (`zhuating/qcc-dqi-bm-rounds`, v1–v3, COMPLETE, static
IR read only). **Nothing was simulated, nothing was verified, nothing was submitted or
pushed.** Zero kernels ran concurrently with another line.

---

## 1. Sources read

| source | what it gave |
|---|---|
| **arXiv:2610.22367v1** — Gu, Kemeny, Yelin, Lukin, *Discovering state-of-the-art quantum circuits with large language models*, 15 Oct 2026, SI I.1 "Reed–Solomon decoding for OPI" | the BM decoder: rescaled update, the σ₀δ = 1 invariant, the 19-qubit history entry, adaptive cutoffs, in-place ω, the precomputed reciprocal Ψ, and every stage count used here (140k locator, 93k scan, 44k×2 Ψ EEA, 440k / 1,837 total) |
| **arXiv:2510.10967v1** — Khattar, Shutty, Gidney, Zalcman, Yosri, Maslov, Babbush, Jordan, 13 Oct 2025 | the EEA baseline and the **2nb + O(log n)** space claim (`len(poly) + len(dialog) = 2n`), 1,885 logical qubits / 5.72e6 Toffoli, `6n` iterations / `6n²` multiplications |
| `data/competition/verifiers/dqi/dqi_reference_circuit.py` (647 lines) | the competition's EEA generator: `m = n+3 = 73` words per array × 2 arrays, `default_n_iters = 3(n+1)+9 = 222`, the four-phase `counter`, `_pre_align_reg_b`, the Chien/Forney form |
| `data/competition/verifiers/dqi/verify_submission_dqi.py` (501 lines) | the exact contract: syndromes restored bit-exactly (`reg_diff`), all ancillas back to 0, phase only, `score = R(eps)·Q²·mean T`, `Q = circuit.num_qubits` |
| `experiments/frontier/20261118_push/dqi_algo/RESULT.md` | the tape's region split (EEA fwd 153,180.1 / Chien 44,217.0 / EEA rev 169,719.2) and the 42-CCX multiply-block census |
| `experiments/frontier/20261118_push/dqi/RESULT.md` | pool census (2 persistent + 2 product words + 2 flags = 50 wires), and the truncation probe that proves the reverse pass restores the syndrome array |
| **this line's kernel** `zhuating/qcc-dqi-bm-rounds` v3 → `rounds.json` | the tape's measured per-round cost curve, per-cluster T, and the EEA working-set word census |

**Two corrections to the brief's facts.**

1. `arXiv:2510.10967v2` **does not exist** (arXiv serves v1 only, 13 Oct 2025), and no
   version of 2510.10967 contains a BM decoder — it mentions Berlekamp–Massey only as an
   alternative it did not build, and its own contribution is the EEA. The BM circuit at
   440k/1,837 is **arXiv:2610.22367**, which *re-implements* the 2510.10967 baseline
   (5.1M Toffoli, 1,938 qubits) and beats it.
2. The brief's "5.1x worse than our tape in Q²·T" is right, but the sharper statement is
   that the BM loses **in its own metric too**: the paper's headline is a 12.2× **T·Q**
   win over *its* 2nb baseline, and our tape is 2.47× cheaper than the BM in exactly that
   T·Q metric:

| circuit | Q | mean T | Q²·T | × shipped cost | T·Q |
|---|---:|---:|---:|---:|---:|
| competition reference `sample_submission/dqi.kmb` (EEA, 2nb) | 1,893 | 5,725,108 | 2.052e13 | 70.55 | 1.084e10 |
| 2610.22367's EEA reimplementation (2nb) | 1,938 | 5,100,000 | 1.916e13 | 65.87 | 9.884e9 |
| **2610.22367's BM decoder (2nb state)** | **1,837** | **440,000** | **1.485e12** | **5.11** | **8.083e8** |
| **our tape `575b043f` (EEA, 1nb)** | **890** | **367,116** | **2.908e11** | **1.00** | **3.267e8** |

The BM paper's advance and our tape's advance are the **same axis** (width, 2nb → our
1nb) applied to each other's baseline. That is why the BM number cannot be imported.

---

## 2. What the BM decoder actually is (as published)

Per round `r = 1..70`, with `τ̃ = zτ`:

```
Δ = Σ_{i=0..min(deg σ, r−1)} σ_i S_{r−i}
(σ, τ, δ, d) ← (σ, τ̃, δ, d+1)                        if Δ = 0
             ← (σ − (Δ/δ)τ̃, σ,   Δ, −d)              if Δ ≠ 0, d ≥ 0   (replace)
             ← (σ − (Δ/δ)τ̃, τ̃,   δ, d+1)             if Δ ≠ 0, d < 0   (retain)
```

Four things make it reversible and cheap, and each has a qubit consequence:

1. **Rescaled replace branch.** Writing the replace as `τ − α⁻¹σ` instead of `σ − ατ`
   makes both branches share one arithmetic path, so no displaced template is ever
   stored. Cost: σ and τ must both be live (2 registers).
2. **δ is never stored.** The invariant σ₀δ = 1 fixes `δ = σ₀⁻¹`, so the round forms
   `Δ·σ₀` and inverts it. Cost: one GF inversion per round, one 12-bit temporary.
3. **Δ is erased by MBU.** A replace round leaves σ₀ = Δ⁻¹, so the reverse pass recovers
   Δ from σ; only a **retain** round needs Δ saved. One stack entry = **19 qubits**
   (12-bit Δ + flags); the worst case would be 35 entries = 665 qubits, per-round history
   840 qubits (the paper's 2,677-qubit variant). Typical failure from a one-entry stack
   plus cutoff overrun: **1.4e-4** over 400M samples (7 wrong signs in 100,000 circuit
   tests) — comfortably inside the verifier's `eps_plus < 1/16`.
4. **Adaptive cutoffs.** Round `r` updates only the prefix `σ_0..σ_k` with `k` a
   *compile-time* constant chosen by classically simulating BM on the DQI distribution
   (typical degree ≈ r/2, so the peak is 35 ≈ `l`). This is the source of BM's cheap
   control: no runtime degree register, no unary iteration over degrees.

The evaluator is built **in place**: `ω_i = S_{i+1} + Σ_{j=1..i} σ_j S_{i−j+1}` is
triangular, so `σ·S mod z^35` overwrites `S_1..S_35`, and the last 35 syndrome words are
zero on a correct decode and become workspace. The scan needs `Ψ = (σ′)⁻¹ mod σ`, computed
by an EEA on the half-degree pair `(E, O)` (deg ≤ 17, because squaring is linear in char 2),
which also lives in the zeroed syndrome words.

---

## 3. Q: the packing question, and why 890 is impossible

### 3.1 The measured fact about our tape

Kernel `qcc-dqi-bm-rounds` v3, forward EEA region `[17,576,206, 30,335,416)` of
`575b043f` (sha256 `575b043f4fee…`, 57,520,821 ops):

```
forward EEA multiply blocks:  1,542 blocks of 42 CCX
12-bit word indices used as multiply TARGETS: 2 .. 73   (72 words = 864 qubits)
                                              word "74" = the two flag qubits 888-889
words 0 and 1:                                never a multiply target
```

(Correction, 2026-11-18: the `2..73` set is the *target* set. The union over controls and
targets is `0..73`, i.e. the whole 888-qubit register file — words 0 and 1 are controls of
the EEA's opening division `CCX(0, 12, 840)` at op 17,576,206, measured by the `dqi_align`
line. The conclusion is unaffected and slightly strengthened: the EEA touches every 12-bit
word of the tape and no word outside it.)

So the EEA's entire arithmetic working set is **one 70-word polynomial array plus the four
12-bit pool words = 74 words = 888 qubits**, and there is no second 70-word array anywhere
in the circuit. The 1nb packing is a measured
property of the tape, not an inference, and it is *better* than the `2nb + O(log n)` that
2510.10967 proves as the theoretical minimum for its own architecture. Why it is available
to the EEA at all [arith]: the Bezout pair satisfies `deg r_i + deg t_i ≤ 69` (the final
pair is `deg σ = 35`, `deg ω = 34`), so the remainder ladder and the coefficient ladder
share one 70-word array — and, decisively, the array being shared *is the input array*, so
the syndromes are consumed rather than preserved. Our tape pays for that in T: its reverse
pass is **16,539 T more expensive than its forward pass** (169,719 vs 153,180) — it
re-derives the quotient stream instead of storing it, which is exactly the 2nb → 1nb trade.
(The dqi line's truncation probe confirms the same thing from the other side: deleting the
smallest trailing chunk fails on 102,400/102,400 shots because the syndrome registers are
never restored — they *are* the EEA array.)

### 3.2 The BM live set

Round `r` reads `S_{r−i}` for `i ≤ min(deg σ, r−1) ≤ 35`, so `S_j` is read at every round
in `[j, min(j+35, 70)]`. **`S_35` is read at round 70**, and every syndrome word is
required by the verifier's `reg_diff` check at the end. So:

* no syndrome word is dead before the last round → none can be used as workspace;
* `σ` and `τ` are two *independent* degree-≤35 polynomials whose degrees are **not**
  bounded by a common budget (both reach 35 near the end), so 2 × 36 words are live;
* nothing here is an implementation choice — it is the recurrence of §2, items 1–2.

```
  70 words = 840 qubits   syndromes S_1..S_70 (read to round 70, must be restored)
  36 words = 432 qubits   locator sigma (deg <= 35)
  36 words = 432 qubits   template tau (deg <= 35)
 142 words = 1704 qubits   <-- floor, before Delta (12), stack (19), counter, scan temps
```

The published circuit is 1,837 Q = 1,704 + 19 (stack) + ~114 (Δ, d, scan temporaries),
and its no-reuse variant is 2,677 = 1,837 + 840. So **the published 1,837 is already within
7.8 % of the BM floor**; there is no 890-qubit BM to find by better engineering.

The contrast is exact and worth stating once: the **EEA consumes its input** (the syndrome
array is overwritten by the (σ, ω) pair, which is 35 + 35 = 70 words — the Bezout degree
sum fits in one array), so its working set is 70 words + O(1). **BM reads its input
throughout**, so its working set is 70 + 72 words. 1nb is available to the EEA and not to
BM.

Width cost of the gap: `(1704/890)² = 3.67`, `(1837/890)² = 4.26`.

### 3.3 What width does to the requirement

`T_be(Q) = 367,116 · (890/Q)²` is the T a wider decoder must beat to be worth shipping:

| Q | 890 | 950 | 1,000 | 1,100 | 1,704 (BM floor) | 1,837 (published BM) |
|---|---:|---:|---:|---:|---:|---:|
| T must be ≤ | 367,116 | 322,208 | 290,793 | 240,324 | **100,148** | **86,172** |
| T for GM 31.42723 | 264,691 | 232,298 | 209,612 | 173,233 | **72,207** | **62,130** |

At its own floor the BM would have to be **3.67× cheaper than the tape** to break even,
and **5.08× cheaper** to reach the tier — while its locator alone is 259,448 T (below).

---

## 4. T: stage table and the two hybrids

Published BM stage counts (`[paper]`) against the measured tape (`[tape]`):

| stage | BM (1,837 Q) | tape `575b043f` (890 Q) | BM/tape |
|---|---:|---:|---:|
| locator solve, forward (70 BM rounds) | **140,000** | 153,180 | 0.91× |
| locator solve, reverse | **119,448** *(implied: 440,000 − the four listed stages)* | 169,719 | 0.70× |
| phase scan (Chien / Forney) | 92,552 *(4,024 × 23 T/pos)* | **44,217** *(4,025 × 11.0 T/pos)* | 2.09× |
| Ψ = (σ′)⁻¹ mod σ, EEA forward | 44,000 | — | — |
| Ψ EEA, reverse | 44,000 | — | — |
| in-place evaluator ω = σS mod z³⁵ | not listed *(630 multiplies ≈ 26,460 T if it is not inside the 140k)* | — | — |
| **total** | **440,000** | **367,116** | **1.20×** |

Per-stage reading:

* **Locator: BM wins 63,451 T (19.7 %).** 140,000 + 119,448 = 259,448 vs 153,180 +
  169,719 = 322,899. BM's reverse is *cheaper* than its forward because Δ is re-derived
  from σ₀ — the mirror image of our tape's reverse, which is 16,539 T *more* expensive
  because the quotients are re-derived.
* **Scan: the tape wins 48,335 T (2.1×).** Our Chien costs 11.0 T/position (10-bit
  measured AND + 1 CCZ per position) against the published BM's 23 (11-Toffoli zero test
  + 12 Toffolis for the trace products). This asset is *composable* — it only needs σ, ω
  and the mask, so it can front-end either locator.
* **Ψ: BM pays 88,000 T the tape does not pay at all.**

Best hybrid (BM locator + our scan) = 259,448 + 44,217 = **303,665 T**; with the
evaluator priced = **330,125 T**:

| hybrid | T | vs target 264,691 | vs tape 367,116 | widest Q that still beats the tape |
|---|---:|---:|---:|---:|
| A: BM locator + tape scan | 303,665 | 1.147× | 0.827× | **979** |
| B: A + evaluator (630 × 42 T) | 330,125 | 1.247× | 0.899× | **939** |
| C: published BM circuit | 440,000 | 1.662× | 1.199× | **813** |

**The decisive number is the last column.** Even the most favourable hybrid — a locator
that is 20 % cheaper than ours plus *our* best scan — only pays if the circuit is at most
**979 qubits wide**. The BM's live state is **1,704**. It would have to be 1.74× narrower
than its own floor.

Multiply-count bookkeeping, for completeness (`[arith]`): with the paper's typical degree
`L_r ≈ r/2`, a BM forward pass needs `2·Σ_{r=1..70} min(⌊r/2⌋,35) = **2,450**` field
multiplies versus the tape's 1,542 — BM does **1.59× more** arithmetic and wins only
because each costs 57 T instead of the tape's blended 99 T. (That blend is misleading:
§5.1 measures the tape's clean ladder at **45.1 T/multiply**, i.e. below the BM's 57.1 —
the BM's per-multiply advantage is not real in the tape's good rounds.) Its arithmetic
floor is `2 × 2,450 × 42 = 205,800 T` for both passes, so A's 303,665 is only 1.48× its own
floor and **the BM has no headroom left**: the absolute floor of the BM+Chien hybrid,
`205,800 + 44,217 = 250,017 T`, is still only 5.5 % below the 264,691 target with *every*
control gate free.

---

## 5. Measurement: where the tape's 367k actually is

`zhuating/qcc-dqi-bm-rounds` v1–v3, static read of `575b043f` (no simulation). Method:
anchor each EEA division round on its 42-CCX field-multiply blocks (maximal same-triple
runs, gap ≤ 80), cluster them with a 6,000-op gap, attribute `[first multiply of round i,
first multiply of round i+1)` to round `i`.

### 5.1 The clean ladder is *already* at the arithmetic floor

The forward pass contains 28 consecutive rounds with a strictly `+1` growing window
`w = 3..30`. Their cost is an exact affine function of `w`:

```
T(w) = 41.0 · w + 109.3       28 rounds, r² = 0.9985,  ΣT = 22,001
T(4) = 252 = 42·4 + 84         T(30) = 1,344 = 42·30 + 84      (odd w: +35)
```

**One extra window position costs 41 T — exactly its own 42-CCX multiply and nothing
else.** So on this axis the tape is not paying per-position control at all, and a
statically widened ("unconditional sweep") schedule can only add ANDs: widening those 28
rounds to 68 positions would add 59,122 T and remove nothing. I tested that idea and the
measurement rejects it. Note also that 45.1 T/multiply (the `w = 17..30` bucket) is
**below the published BM's 57.1 T/multiply**: BM's "cheap control" advantage does not
exist in the tape's ladder.

### 5.2 The cost is not in the multiplies but in 93 small clusters and one big one

| pass | bucket | clusters | T | multiplies | T/mult | share of tape |
|---|---|---:|---:|---:|---:|---:|
| forward | `w = 1` | 67 | 25,064 | 67 | **374** | 6.8 % |
| forward | `w = 2` | 11 | 12,294 | 22 | **559** | 3.3 % |
| forward | `w = 3` | 13 | 32,264 | 39 | **827** | 8.8 % |
| forward | `w = 4..16` | 77 | 50,178 | 727 | 69.0 | 13.6 % |
| forward | `w = 17..30` | 16 | 17,052 | 378 | 45.1 | 4.6 % |
| forward | `w ≥ 31` | 5 | 16,334 | 309 | 52.9 | 4.4 % |
| reverse | `w ≤ 3` | 88 | 13,646 | 126 | 108 | 3.7 % |
| reverse | `w = 4..16` | 76 | 52,289 | 713 | 73.3 | 14.2 % |
| reverse | `w = 17..30` | 18 | 22,348 | 412 | 54.2 | 6.1 % |
| reverse | `w ≥ 31` | 5 | **76,714** | 275 | **279** | 20.8 % |

(cluster accounting covers 318,183 of the two passes' 323,725 static T, 98.3 %.)

Two clusters alone hold **95,317 T = 25.9 % of the whole tape**:

* forward `op 19,508,954`: 3 multiply blocks, **29,543 T**, of which 20,723 sit in CCX
  blocks of size < 12;
* reverse `op 46,230,185`: 66 multiply blocks (2,772 CCX in 42-blocks), **65,774 T**, of
  which 46,966 sit in CCX blocks of size < 12.

The whole target cut is 102,425 T, and those two clusters hold **93.1 % of it**
(102,425 / 95,317 = 1.075). **Identifying and re-scheduling those two clusters is the only
890-qubit T lead this study found**, and it is a tape-generation problem (the fused tape
carries no tags; dqi_algo §5 already showed an in-place block rewrite is a byte-level
operation), not a BM problem.

> **Follow-up, 2026-11-18 — this lead is closed.** The `dqi_align` line measured both spans
> at the gate level: they are **EEA multiply streams, not an alignment**. `span_fwd` is
> 1.88 M ops at a *flat* 15.7 T per 1 k ops (slope +0.01 T/segment, r² = 0.0002), with
> 61.8 CX per CCX and **zero** Fredkin neighbourhoods; `span_rev` is 65.8 CX per CCX with
> 448/531 distinct control qubits each serving up to 171/491 distinct target pairs. There is
> also **zero block-level redundancy** (342/342 and 626/626 blocks have unique bit-level
> wiring, `T_deletable = 0`). So the 95,317 T is 2,243 multiply groups at the tape's own
> multiplier cost, spread uniformly through the arithmetic, and cannot be re-scheduled:
> a 26 % T cut needs a cheaper *multiplier*, which is the `dqi_mult` rank axis.
> See `experiments/frontier/20261118_push/dqi_align/RESULT.md`.

Whole-tape arithmetic for scale: 3,068 multiply blocks × 42 ANDs = **128,856 T (35.0 %)**;
at the measured 41.0 T/multiply the floor is 125,788 T; the tape spends **242,201 T
(65.8 %) on everything else**, of which 95,317 T is the two clusters above.

---

## 6. Pricing, so the size of the miss is unambiguous

Base: invsqrt 74,560.90687 / dqi 346,409,762,292.72 / chem 294,643,137.73 → GM 28.180659.
DQI target for GM 31.42723: cost ≤ 249,761,368,080, i.e. **T ≤ 264,691 at Q = 890**
(the brief's 249.6e9 / 264,600 confirmed) or **T ≤ 297,139 at Q = 840**.

| candidate | Q | T | dqi cost | × shipped | GM (other two legs held) |
|---|---:|---:|---:|---:|---:|
| shipped tape `575b043f` | 890 | 367,116 | 3.464e11 | 1.000 | 28.1807 |
| BM + tape scan (hybrid A) at its Q floor | 1,704 | 303,665 | 1.050e12 | 3.032 | 19.4701 |
| hybrid B at its Q floor | 1,704 | 330,125 | 1.142e12 | 3.296 | 18.9353 |
| published BM circuit | 1,837 | 440,000 | 1.769e12 | 5.106 | 16.3652 |
| hybrid A *if* it were 890 Q (it cannot be) | 890 | 303,665 | 2.865e11 | 0.827 | 30.0207 |
| the 890-Q target | 890 | 264,691 | 2.498e11 | 0.721 | 31.4272 |

Hybrid A at its real width is **3.03× worse than the shipped tape, −8.71 GM**. And note
what the "if it were 890 Q" row says: even with a *free* width for the BM state, A buys
**+1.84 GM (28.18 → 30.02)** — it would enter the bottom of the 29.98–31.43 tier but stop
there, because 303,665 T is still 14.7 % above the target. The tier's top needs both the
BM's T **and** the tape's width, and no construction has both.

---

## 7. Verdict

1. **Q (structural, closes the line).** BM's forward pass needs
   `840 (syndromes, all live to round 70) + 864 (σ, τ) = 1,704 Q` before scratch; the
   published circuit is 1,837. Packing into ≤ 890 requires putting σ and τ inside the
   syndrome array, which is impossible for any BM-shaped recurrence because `S_35` is
   read in round 70. `(1704/890)² = 3.67` is a permanent tax: at its own floor the BM
   must be 3.6× cheaper in T merely to tie.
2. **T (also closes, independently).** Published 440,000; best hybrid 303,665;
   absolute floor of that hybrid with all control free 250,017; target 264,691. The
   locator *alone* (259,448) exceeds the entire 31.43 budget at 1,704 Q (72,207).
   Even a hypothetically 890-qubit BM would land at GM 30.02 (+1.84), not 31.43.
3. **Both axes fail, and neither failure is marginal.** Which stage breaks the budget:
   the **locator solve** (259,448 T, and it is what forces 1,704 qubits), then the
   **Ψ EEA** (88,000 T with no counterpart in our tape).
4. **Do not build it.** A prototype at ≤ 890 Q cannot exist; a prototype at 1,704 Q would
   be a faithful reproduction of a circuit we already know is 3.03× worse. This is a
   feasibility study and the honest result is the arithmetic above.
5. **What survives and should be handed on:** (a) our 11.0 T/position scan beats the
   published 23 by 2.1× and is composable; (b) the tape's clean ladder already runs at
   41.0 T/multiply with 109 T/round, so the multiply axis is at its floor; (c) **25.9 % of
   the tape's T sits in two clusters** (`op 19,508,954` forward, 29,543 T; `op 46,230,185`
   reverse, 65,774 T) — **subsequently identified by the `dqi_align` line as uniformly
   spread multiply streams with zero block-level redundancy, so this is not a lever** (§5.2
   follow-up box).

---

## 8. Scope, honestly stated

* **Measured on Kaggle CPU:** one kernel, `zhuating/qcc-dqi-bm-rounds`, 3 versions, all
  COMPLETE (v1 12 s, v2 30 s, v3 40 s of work). It only *reads* the instruction stream of
  `575b043f` (sha256 `575b043f4fee91a0…`, 479,128,738 B, 57,520,821 ops, Q 890, static T
  367,989) and counts Toffoli positions per round. Raw output: `rounds.json` (this
  directory).
* **Not done:** no circuit was built, no BM decoder was compiled, no simulation and no
  official verification was run, because the estimate closes the line before a prototype
  is worth building. No submission, no dataset, no git push. Zero kernels run in parallel
  with another line.
* **Not verified:** the identification of the two 95k clusters' *function* (candidate:
  the initial-shift align/unalign of `_initial_shift_loop`, which is a data-dependent lane
  rotation in the reference generator). The census gives their op ranges and block
  composition; naming them needs a separate pass. Everything in §5.2 is a count, not an
  interpretation.
* **Imported numbers are the papers'**: 140,000 / 93,000 / 44,000 / 440,000 / 1,837 /
  19 qubits / 2,677 / 1.4e-4 / 2510.10967's 2nb claim and 5.72e6 / 1,885. The BM
  locator's *reverse* 119,448 is arithmetic implied by the published total, and the
  multiply count 2,450 is my derivation from the published typical-degree curve, not a
  published number — both are flagged where used.

## 9. Files and exact commands

```
experiments/frontier/20261118_push/dqi_bm/
  RESULT.md                        this file
  rounds.json                      kernel v3 output (per-cluster T, fits, word census)
  model.py                         pure-arithmetic model; §4, §5.2, §6, §7 all regenerate
  k_rounds/main.py                 the static-IR kernel (v3)
  k_rounds/kernel-metadata.json
```

```bash
# the measurement kernel (CPU, private, no GPU/TPU)
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_bm/k_rounds \
      --slug qcc-dqi-bm-rounds --account zhuating --competition \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_bm/k_rounds \
      --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-bm-rounds --account zhuating

# fetch ONLY the small JSON (the kernel's working dir also holds the 479 MB .kmb)
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_zhuating) KAGGLE_CONFIG_DIR=~/.kaggle \
  python -c "from kaggle.api.kaggle_api_extended import KaggleApi as A; a=A(); a.authenticate(); \
  a.kernels_output('zhuating/qcc-dqi-bm-rounds','/tmp/bmrounds3',file_pattern=r'rounds\\.json',force=True)"

# all the arithmetic in this report (local, pure arithmetic, no simulation)
python3 experiments/frontier/20261118_push/dqi_bm/model.py
```
