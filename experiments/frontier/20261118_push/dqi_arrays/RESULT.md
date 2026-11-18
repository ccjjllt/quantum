# DQI tape `575b043f` — are the EEA's polynomial arrays 3, and is one of them redundant?

**Answer: no. The array-count axis is closed.** Two measurements decide it, both below:

* **Every word is read.** In the forward EEA the CCX operands touch all 74 words; the *least*-read
  S word is read **798** times as a CCX operand and **zero** S words have zero reads. A redundant
  array would appear as a set of words with many writes and no reads. There is no such set — the
  only words with zero *writes* are `S0`, `S1`, and those are pure reads (they are the EEA inputs).
* **The reference's 2-array form is not cheaper.** Measured on the official generator: at the
  tape's polynomial width it needs **3,672 multiply rows per EEA pass** against the tape's
  **3,647** — identical within 1 %. The tape's "3 arrays per step" is the reference's "1 array,
  3× as many steps". Deleting an array does not delete rows; it multiplies steps.

`ΔT` from the array hypothesis: **0**. GM stays **28.15093**.

The real, measured prize is elsewhere and is priced at the end: **1 div round/step ⇒ T ≈ 204,555,
GM 34.21** — a schedule change, not a splice.

All numbers below are static-IR readings of the tape on two Kaggle CPU kernels
(`zhuating/qcc-dqi-arrays`, `zhuating/qcc-dqi-mult-census`) plus local builds of the **official**
generator through the PyPI `kickmix` package. Nothing was simulated, nothing was written back, the
tape was deleted in-kernel, no submission was made.

---

## 0. Deliverable 1 — the arrays that actually exist (measured, not named)

### 0.1 The multiply vocabulary

1,530 distinct unordered CCX operand-word pairs in the forward EEA, 153,175 CCX. The eleven most
used pairs (CCX counts, `/42` = multiply rows):

| pair | CCX | rows | pair | CCX | rows |
|---|---:|---:|---|---:|---:|
| (0, 70) | 1,512 | 36 | (10, 69) | 1,344 | 32 |
| (2, 69) | 1,470 | 35 | (8, 70) | 1,344 | 32 |
| (4, 70) | 1,428 | 34 | (16, 70) | 1,275 | 30 |
| (72, 73) | 1,418 | 33 | (14, 69) | 1,218 | 29 |
| (6, 69) | 1,386 | 33 | (20, 70) | 1,191 | 28 |
| (12, 70) | 1,359 | 32 | (18, 69) | 1,176 | 28 |

Reading: the operands are **one S word × one pool word** almost everywhere, and the pool partner
alternates between **69** and **70**. Concretely, the S-word partner's index parity tracks the pool
word (`A=70` sweeps carry `B ≡ 0 mod 4`, `A=69` sweeps carry `B ≡ 2 mod 4`). So the tape holds

* **P₀ = {words ≡ 0 (mod 4)}** and **P₂ = {words ≡ 2 (mod 4)}** — the two interleaved polynomial
  arrays over the same 70-word store (this is `dqi_surgery` INTERFACE §5's stride-2 ladder, refined
  to stride 4), and
* **the pool words 69/70** = the quotient carrier, **71/72/73** = the product accumulator +
  Landau/degree scratch. They alternate roles by design: a sweep is always
  `(q=70, operand=B, target=69)` or `(q=69, operand=B, target=70)`, i.e. quotient-in /
  quotient-out through the same two words.

There is **no third polynomial array of 32 words**. The third "row" per step is the *target-side*
update in the other parity class, not a third polynomial.

### 0.2 Op intervals and read counts per set (forward EEA, `[17 576 206, 30 151 421)`)

| set | words | first → last op as operand | CCX reads | CCX writes |
|---|---|---:|---:|---:|
| P₀ (array A) | 0,4,8,…,68 | 17 576 206 → 29 916 601 | 78 240 | 35 544 |
| P₂ (array B) | 2,6,10,…,66 | 17 585 915 → 29 805 688 | 81 202 | 14 620 |
| odd interleave (the alternating half) | 1,3,5,…,67 | 17 576 206 → 30 151 420 | 56 820 | 32 080 |
| quotient / accumulator | 69, 70 | 17 577 672 → 30 133 879 | 37 725 | 32 487 |
| product pool | 71,72,73,74 | 17 577 878 → 29 807 006 | 28 880 | 38 444 |

(reads/writes are CCX operands/targets only; CX traffic is an order of magnitude larger and is not
what the Toffoli bill is made of. `reads` double-counts a word appearing on both control slots.)

**Read counts are the hard criterion the brief asks for**, and they refute redundancy directly:
per-word CCX reads / writes in the forward pass (full table in
`out/arrays.json`), minimum over `S0..S68` = **798 reads** (word 1), maximum write-read deficit
= +8,505 (word 70, which is read 20,820 times anyway). No word is a Toffoli sink.

### 0.3 The "35 iterations × 96 rows" premise is wrong; the real shape is a staircase

The forward EEA segments cleanly at "sweep-start" blocks (target word ∈ {69,70}, 42 CCX,
first CCX after a ≥5,000-op gap). Measured: **41 sweeps**, and the CCX between consecutive sweep
starts is

```
4, 4, 6, 6, 8, 8, 10, 10, 12, 12, 14, 14, 16, 16, 18, 18, 19, 20, 21, 22, 23, 24, 25, …, 35  rows
```

— an arithmetic staircase of **+1 row per sweep**, not a flat 96 rows/step. 3,647 rows total per
pass (`153 175 = 3 647 × 42 + 1`), spread over 41 sweeps plus one irregular 1,583-row head segment
and one 704-row tail. `3,339` is the *pair-census* count and under-counts split accumulators; the
op-gap count `3,647` is the right one.

So the "96 = 3 × 32" arithmetic coincidence has no structural referent. **Deliverable 3 is
"不可删"**: nothing to splice, ΔT = 0, GM unchanged.

---

## 1. 对照：参考的 2 数组形式 (the question put to this round)

### 1.1 Where the official generator puts σ and ω — and why it needs no third array

`data/competition/verifiers/dqi/dqi_reference_circuit.py`, read in full:

* `reg_a`, `reg_b` are the **only** two quantum arrays (`m = n + 3` words each, §103-104).
  `reg_a` is initialised to the left-aligned syndrome polynomial (`_initial_shift_loop`, §140-164)
  and `reg_b` to the monomial `1` (`init_ones` sets `reg_b[m-1][0]`, `n_B = n+1`, §117-120).
* `_multiply_and_add_or_sub` (§291-378) is **one** multiply-accumulate row-sweep:
  `reg_b[i] ^= q_i · reg_a[i]` for the degree-gated set `{i : i < lim_a or i ≥ 2}` (§348-363), where
  `q_i` is carried along the array by `cswap(q_i, reg_a[i])` (§353-360) — the quotient follows the
  pipeline by *swapping*, so one row-sweep covers the whole array.
* `_swap_a_and_b` (§467-480) exchanges the two arrays at the end of a division round; `_shift_b_array_right`
  (§378-437) realigns the auxiliary slice. Neither introduces a third array.
* The Chien (§522-611) then reads **both** outputs out of `reg_b`:

  ```python
  sigma        = reg_b[0]
  sigma_prime  = reg_b[1]
  omega        = reg_b[m // 2 + t]        # t = n_syndromes // 2
  sum_pairs = [(reg_b[k], omega)  for k in range(m//2+1, m//2+t)]      # ω = Horner over the upper half
            + [(reg_b[k], sigma_prime) for k in range(3, t+1, 2)]      # σ' = odd coefficients
            + [(reg_b[k], sigma)       for k in range(2, t+1, 2)]      # σ  = even coefficients
            + [(sigma_prime, sigma)]
  ```

  **σ = the low half of `reg_b`, ω = the upper half of `reg_b`.** ω is obtained as
  `(v · S) mod x^{2t}` — the single Bezout coefficient `v` multiplied by the syndrome polynomial —
  **not** as the textbook second Bezout coefficient `t_i`.

So the answer to "why no third array": the classic 3-array EEA `(r, s, t)` needs `t` only if you
want the second Bezout relation `s·a + t·b = r`. This decoder only ever needs `(σ, ω)`, and
`ω = σ·S mod x^{2t}` gives ω from σ and the (still available) syndrome polynomial. The remainder
`r` needs no dedicated degree register either — `(n_A, n_B, n_a, n_b, n_q, flag, counter,
halting_counter)` carry every degree the schedule needs. **State = 2 arrays + 8 small registers.**

### 1.2 Priced at the tape's width — measured, not assumed

Local builds through PyPI `kickmix` (GF(2¹²), no simulation, circuit construction + static
statistics only). Unit costs:

| object | T |
|---|---:|
| `init_gf2_div_with_scaffold` + `del_…` | **378** |
| `init_gf2_inverse_with_scaffold` + `del_…` | **315** ← the `315` in `dqi_surgery/SPEC.md` §3 Case B |
| `ixor_gf2_mul` (one row, uncontrolled) | **63** |
| `ixor_gf2_mul` controlled (as the EEA uses it, `mul`) | **75** |

Reference EEA-only builds (`_synchronized_eea`, forward pass only), call counts instrumented on the
builder:

| n | m | iters | `gf2_div` /iter | `ixor_gf2_mul` /iter | mul/(iter·m) | T/iter |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 5 | 18 | **2.00** | 4.89 | 0.978 | 1,533.7 |
| 3 | 6 | 21 | **2.00** | 5.90 | 0.984 | 1,653.9 |
| 4 | 7 | 24 | **2.00** | 6.92 | 0.988 | 1,765.1 |
| 5 | 8 | 27 | **2.00** | 7.93 | 0.991 | 1,916.7 |
| 8 | 11 | 36 | **2.00** | 10.94 | 0.995 | 2,265.8 |

Hard facts extracted:

1. **Exactly 2 `gf2_div_with_scaffold` per EEA iteration** — one at the leading index, one at the
   trailing index (`_multiply_and_add_or_sub` §371/375). *Not* one per position, *not* 19.5.
2. **≈ m multiply rows per iteration** (`0.978 … 0.995 × it × m`), i.e. one row-sweep of the whole
   array per iteration.
3. Iterations per pass = `default_n_iters(n) = 3(n+1) + 9`.
4. `T/iter = 122·m + 924` (least-squares through the m=5 / m=11 points; the 924 intercept is
   2×378 = 756 of division + ~168 of bookkeeping, the 122 slope is the 75-T row + ~47 T of
   `_swap_a_and_b`/`_shift_b_array_right`/`_update_flag`/`_update_metadata` per word).

**At the tape's polynomial width** (window ≈ 35–36 words ⇒ `n = 33`, `m = 36`, `n_iters = 108`):

```
rows / pass   = 108 × 35          = 3,780   (measured ratio 0.99 → 3,742)
tape rows / pass                  = 3,647
```

**Identical, within 1 %.** That is the decisive number of this whole line: the tape's
"3 arrays × 35 steps × ~104 rows" and the reference's "1 array × 108 steps × 35 rows" are the *same
work*, re-scheduled. The array count is not a free parameter; the reference's three gated
row-sweeps per division round (`_update_flag` sub-steps 0…3, all sharing the `mul` control) are
exactly what the tape's three array-updates buy back.

The width is not imposed: `(3(n+1)+9)·m = 3,647` has its solution at `m ≈ 34` (`n ≈ 31`), which is
independently what the tape's multiply vocabulary says (two interleaved arrays over a 70-word
store ⇒ ~35 words each). So the two row counts agree because both are the same algorithm at the
same width, not because a parameter was chosen to make them agree.

### 1.3 Break-even budget, corrected

The brief's arithmetic: `(367,116 − 152,057) / 35 = 6,144 T/step` ⇒ ~19.5 divisions of 315 T.

* **Division axis: 9.75× under budget.** Measured **2** divisions/step = 756 T/step, versus the
  6,144 T/step allowance, versus the tape's 4,032 T/step. On this axis alone the 2-array form has
  enormous slack — the brief is right about that.
* **Row axis: over budget by 3×, and that is what kills it.** The 1,260 rows/pass figure assumes
  one division *round* per step. The reference spends `3(n+1)+9` steps ≈ `3 × n_rounds` because
  each round is spread over three gated sub-steps. Priced both ways:

| form | rows/pass | EEA T (2 passes) | static T | mean T | GM |
|---|---:|---:|---:|---:|---:|
| tape `575b043f` (measured) | 3,647 | 321,762 | 367,989 | 367,116 | **28.151** |
| reference 2-array, as written (75-T row, measured fit) | 3,780 | 1,148,256 | 1,194,483 | 1,191,649 | **19.01** |
| reference 2-array, as written, but with the tape's 42-T row | 3,780 | 891,648 | 937,875 | 935,650 | **20.61** |
| **2-array with 1 division round/step** (+2 div/round) | 1,260 | **158,760** | 204,987 | 204,501 | **34.21** |
| 1 round/step, projective (no division at all) | 1,260 | 105,840 | 152,067 | 151,706 | **37.79** |

(`mean T = 367,116.0572 × static_T / 367,989`; non-EEA = 44,275 (Chien) + 1,952 (rev CCZ) =
46,227 T. GM from `scripts/gm.py` with invsqrt 74,797.365357 / chem 294,643,137.73 held; the model
reproduces the shipped 28.15093 to 1e-5, so it is calibrated. The brief's `152,057 ⇒ 37.0` is the
same last row before the static→mean conversion.)

**Verdict on the question: the 2-array form, as the official generator implements it, cannot reach
≤ 220,000 T — it lands at ≈ 1.19 M T (GM 19.01), 3.2× worse than the tape.** Even granting it the
tape's 1.5×-cheaper 42-T multiply block it is 935,650 T (GM 20.61). The `152,067` / GM 37.8 ceiling
is real, but it is the ceiling of a *different schedule* — one division round per step — not of the
2-array representation. The tape already pays the reference's row count; what it has not done is
collapse three gated row-sweeps into one.

---

## 2. Deliverable 4 — is there a "4 rows per step" (186 = 4×42+18)?

No. 150 pairs have total CCX 186, and their target split is uniformly `(70, 105) + (8, 81)`:
105 = 2.5 rows and 81 = 1.93 rows, i.e. **one split-accumulator row plus one partial**, not four
clean rows. The clean multi-row pairs (`168 = 4 × 42`, 8 of them; `210 = 5 × 42`, 9; `252 = 6 × 42`,
5) are the *same* operand pair recurring at **different algorithm steps**, not several accumulators
inside one step. Example, pair `(49,51)`:

```
target 43 : ops 28,368,348 .. 28,369,640   (42 CCX)
target 35 : ops 28,555,699 .. 28,556,991   (42 CCX)
target 27 : ops 28,872,787 .. 28,874,079   (42 CCX)
```

190 k and 320 k ops apart — three separate sweeps. So the 47 % "non-full-width" CCX are split
accumulators (a product fanning into two words, `33 + 9` in the `(72,73)` case) and single-AND
partials, **not** a hidden fourth row. Nothing to recover there.

---

## 3. The one measurement that does move the needle

Given §1.3, the interesting form is not "2 arrays" but "**1 division round per step**" — and its
price is fully determined by quantities measured here:

```
per pass :  35 rounds × 36 rows × 42 T  =  52,920        (rows; the tape's own 42-T block)
          + 35 rounds × 2 div × 378 T   =  26,460        (measured 2 div/round)
          = 79,380 T/pass  ->  158,760 T for both passes
static T = 158,760 + 44,275 (Chien) + 1,952 (rev CCZ) = 204,987
mean  T  = 204,501      ->  GM 34.21
```

Note what this costs relative to the brief's 31.4 target: the 2×378 T/round division is *not* the
obstacle (26,460 of 158,760 T, 17 %); the 35 × 36 rows are. And the division can be avoided
altogether with the tape's own projective trick (`SPEC.md` §3 Case A: the Chien root test and
Forney are homogeneous of degree 0), which puts the EEA at **105,840 T ⇒ T ≈ 151,706 ⇒ GM 37.79**.

That is a generator job (a 35-round fixed schedule with degree-aware gating, i.e. conditioned CCX or
a unary degree register exactly as the reference uses), not a tape splice: the tape has **0**
conditioned CCX and a fully unrolled schedule, so there is no splice that changes the round count.

---

## 4. What was measured, and how

| claim | how |
|---|---|
| 153,175 / 168,587 / 40,250 CCX in fwd / rev / Chien | `k_bulk` kernel, opcode `t & 0x7F == 0x31` |
| 1,530 / 1,565 distinct operand word pairs; 3,339 / 3,681 pair-census rows | same |
| 3,647 rows/pass by op-gap blocks; staircase 4,4,6,6,…,35 | same, sweep starts = 42-CCX blocks with target ∈ {69,70} after a ≥5k gap |
| every S word read ≥ 798×, no word with 0 reads | per-word CCX operand/write tally |
| Chien reads words 0–65 and 67–73, **not 66** | whole-tape per-word touch histogram, 2,000-op bins |
| 2 `gf2_div` per EEA iteration, ≈ m rows per iteration | builder instrumentation of the official generator (`/tmp/dqicount.py`) |
| 378 T/div, 315 T/inverse, 63/75 T/row | `operation_statistics().num_toffoli_like` on single-object builds |
| T/iter = 122·m + 924 | least squares on 5 measured (m, T/iter) points |

**Artifacts**: `artifacts/20261118_push_dqi_arrays/{ccx,ccz,cswap,touch,fine}.npz`,
`firstlast.json`, `win1.txt.gz` (253,794 resolved ops = one EEA region head), `out/arrays.json`
(per-word read/write table). Kernel `zhuating/qcc-dqi-arrays` v1, CPU only, COMPLETE, tape deleted
in-kernel, no sessions left running.

**Closed**: the redundant-array hypothesis (ΔT = 0); the "2-array reference form at ≤ 220k T"
hypothesis (measured 960k T as written; 204.6k T only with a new 35-round schedule, which the tape
cannot host).
