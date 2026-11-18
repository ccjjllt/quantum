# DQI align line — the two big Toffoli spans are multiply streams, not an alignment

Date 2026-11-18. Line `dqi_align`, account `zhuating`. This line was opened on the
hypothesis that the two largest Toffoli clusters of tape `575b043f` are the forward and
reverse of the **initial syndrome alignment** and could be replaced by a leading-zero
counter + barrel shifter (estimated +2.9 GM).

**Verdict: refuted. Both spans are ordinary EEA field-arithmetic streams, and there is
zero block-level redundancy in either of them.** The barrel-shifter route is closed, the
+2.9 GM is not available, and the 95,317 T is 2,243 multiply groups at the tape's own
multiplier cost — not waste.

All measurement is on Kaggle CPU kernels, **static IR read only**: five kernels of this
line (`qcc-dqi-align-dump`, `-names`, `-regmap`, `-blocks` v1/v2), each COMPLETE, each
deleting the 479 MB decompressed tape before exit. **No simulation, no verifier, no
candidate, no submission, no git push.** Raw JSON in `out/`.

---

## 0. Answers to the four questions asked

| # | question | answer |
|---|---|---|
| 1 | Is `q // 12` a valid word model? | **Yes**, and it was independently confirmed two ways (§1) |
| 2 | Are the two spans the initial alignment? | **No.** Three independent refutations (§2) |
| A | Block-level redundancy inside the spans? | **None.** 342/342, 626/626, 140/140 distinct content; `T_deletable = 0` (§3) |
| B | What is the `(6,46,70)/(7,46,48)/(10,46,70)/(11,46,48)` period-4 pattern? | One **identical 130-CCX gadget (24+34+36+36) broadcast over 10 operand words**, with a fixed second operand (S46) and a shared target pair (pool word 70, S48) — a shared-multiplier accumulation, not ten independent multiplies (§4) |

---

## 1. The word model: `q // 12` == the syndrome register index

The `.kmb` carries its own register table. Two notes before the numbers:

* `c.registers` stores **tagged** ids (`id >> 31 == 1`); masking with `0x7FFFFFFF` recovers
  the physical qubit. Measured `id_tag_high_bit = 1`.
* my first labelling pass read the table unmasked and additionally let the 4,095 classical
  `E*` registers shadow the 70 `S*` registers in the reverse map, so the *names* in
  `out/regmap.json` (`ctrl_top[].reg`) are wrong. The **qubit numbers in that file are
  correct** and every conclusion below uses qubit numbers / `q // 12` only. Recorded here
  so nobody reuses the name column.

Measured (`out/regmap.json → checks`):

```
n_S_registers              70
S_widths                   [12]            every S register is 12 qubits
S0_ids                     0..11
S1_ids                     12..23
S69_ids                    828..839
S_all_contiguous           true
S_starts_step              12
is_word12_equals_register  true
```

So `S_i = qubits 12i..12i+11`, `word = q//12` **is** the syndrome index, words 70..73 are
the pool and word 74 is the two flag qubits 888-889. Independent corroboration: every
42-CCX multiply group in both spans shares one word triple to 42.9 (fwd) / 41.2 (rev) CCX
per triple — a 12-bit-aligned decomposition would not produce that constant.

---

## 2. The two spans are not the initial alignment — three refutations

Forward span `[19,508,954, 21,385,877)` = 1,876,923 ops, **29,543 T** (all CCX, 0 CCZ).
Reverse span `[46,230,185, 52,842,219)` = 6,612,034 ops, **65,774 T** (64,050 CCX + 1,724 CCZ).

**R1 — CX:CCX is 61.8 and 65.8; a controlled-swap stream is 2.0.**
A controlled bit swap written as `CX(e,b); CCX(a,b,e); CX(e,b)` emits exactly 2 CX per
CCX. Measured: 1,826,827 CX / 29,543 CCX = **61.8** (fwd) and 4,326,547 / 64,050 =
**67.5** (rev). At most 3.2 % of the CX traffic could belong to controlled swaps; the rest
is the multiply scaffold (~30–60 CX per AND, as the dqi_algo line measured).

**R2 — not one Fredkin neighbourhood exists.** For every CCX at op `p` with operands
`(a,b,e)` I tested whether `p-1` and `p+1` are CX gates on the pair `(e,b)` (all four
orderings). Result:

| span | CCX | both-sides hits | one-side hits |
|---|---:|---:|---:|
| span_fwd | 29,542 | **0** | **0** |
| span_rev | 64,049 | **0** | **0** |
| cluster132 | 5,895 | 48 (0.8 %) | 48 |

An alignment built from controlled swaps would fire this on ~100 % of its CCX.

**R3 — the control structure is not 69 steps.** An initial-shift step `s` has one control
serving 12·(67−s) swaps over *contiguous* register pairs. Measured instead: **448 distinct
control qubits** in span_fwd (531 in span_rev), the busiest serving 609 (1,439) CCX over
**75 (491) distinct target pairs** spread across 1.8 M (6.5 M) ops. Bit `q0 = 840`
(pool word 70 bit 0) is a control in 609 different multiplies — an operand bit reused by
an AND network, not a step flag.

Corroborating: the forward span's T profile is **flat** — 200 segments of 9,384 ops give
slope **+0.01 T/segment, r² = 0.0002**, head 183 vs tail 208 T. A shrinking shift decays;
this does not. (The `[21.6M, 26.3M)` band does decay, 279 → 104 T per 470 k ops, but the
fit is poor (r² = 0.15) and 6 of its last 10 segments are exactly 0 — that band is the EEA
sweep ladder, and it lies *after* span_fwd.)

Also refuted at the architectural level: the tape has **no initial alignment at all**. The
first operations of the forward region (op 17,576,206) are `CCX(0, 12, 840)` — word 0 ×
word 1 into the pool — followed immediately by its Karatsuba scaffold, i.e. the EEA starts
with a **division**. The reference's `_initial_shift_loop` exists only because that
generator pads its array to `m = n + 3 = 73`; the tape's array is exactly 70 = n, so there
is nothing to left-align.

---

## 3. A — block-level redundancy: **none**

Method. Both spans were cut into maximal runs of CCX sharing the same `(wa, wb, wt)` word
triple with inter-op gap ≤ 80 and size ≥ 8 (the census rule used by the dqi_algo line, so
the block boundaries are the established ones). Each block's **content** is
`(wa, wb, wt, n, sorted (a_bit, b_bit, t_bit) triples)` and is hashed with blake2b-96.

Result:

| span | blocks | distinct content | duplicate groups | duplicate pairs | T in duplicate blocks | **T deletable** |
|---|---:|---:|---:|---:|---:|---:|
| span_fwd | 342 | **342** | **0** | 0 | 0 | **0** |
| span_rev | 626 | **626** | **0** | 0 | 0 | **0** |
| cluster132 | 140 | **140** | **0** | 0 | 0 | **0** |

**There is no block-level redundancy in either span: every multiply block has a unique
bit-level wiring, so no second copy is an identity and nothing can be deleted.** The same
holds for the 140-block dot-product cluster. (This is consistent with the dqi line's
independent result of 0 plain cancels and 0 free Toffolis over all 362,012 CCX.)

Block-size histogram, which is what identifies the real arithmetic unit:

| size (CCX) | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15/16 | 17 | 18 | 19 | 22 | 23 | **24** | 31 | **34** | **36** | 42 | 82 | 99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| span_fwd | 18 | 12 | 6 | 13 | 15 | 6 | 3 | 4 | 10 | 2 | 2 | 2 | 1 | **60** | 4 | **60** | **120** | 3 | – | 1 |
| span_rev | 58 | 10 | 13 | 22 | 18 | – | 3 | 4 | 4 | 6 | – | – | – | **105** | – | **105** | **210** | 66 | 2 | – |

The 24 / 34 / 36 counts are in an exact **1 : 1 : 2** ratio in both spans (60/60/120 and
105/105/210). Grouped as `24 + 34 + 36 + 36 = 130`, that is **one two-word-product gadget
of 130 CCX**, not three separate multiplies. It is the dominant unit in both spans:
60 units = 7,800 T (26.4 % of span_fwd) and 105 units = 13,650 T (20.8 % of span_rev), i.e.
**21,450 T = 5.8 % of the whole tape** in this one gadget family.

---

## 4. B — the period-4 pattern is a broadcast shared-multiplier accumulation

The 200-block window is in `out/blocks.json → pattern_span_fwd` with **complete** bit
triples. The word-triple sequence is rigid:

```
(6,46,70) 24  (6,46,70) 34   (7,46,48) 36  (7,46,48) 36     (8,46,71) 8
(10,46,70) 24 (10,46,70) 34  (11,46,48) 36 (11,46,48) 36
(14,46,70) 24 (14,46,70) 34  (15,46,48) 36 (15,46,48) 36
...
(42,46,70) 24 (42,46,70) 34  (43,46,48) 36 (43,46,48) 36
```

i.e. ten operand pairs `S_{4k+2}, S_{4k+3}` (k = 1..10), each multiplied by the **same**
second operand `S46`, low half into **pool word 70** and high half into **S48**.

The decisive measurement is the `(a_bit, b_bit)` multiset hash per block
(`out/blocks.json → family_wb46`): the ten `n = 24` members share **one** hash
(`5db9436bd32a4bec`), the ten `n = 34` members share **one** hash (`490f390ff58a78aa`), and
the two `n = 36` families share one hash each (`24815a1e356a1f1a`, `1f11fcbc1c48bddc`).
So:

**the same 130-CCX AND pattern is applied ten times, changing only which operand word is
fed in, and all ten products accumulate into the same two target words.**

That is a **shared-multiplier accumulation** — a convolution row / linear combination
`T = Σ_k S46 · S_{4k+2,4k+3}` — with all ten products landing in the **same two target
words**, pool word 70 and S48, which is consistent with one two-word (24-bit) accumulator
split across them (the split itself is an inference from the target pair; the ten-fold
shared wiring and the shared targets are measured). It is not ten independent multiplies,
and it is not a radix-4 butterfly (a butterfly needs ten *distinct* wirings and separate
targets).

Two structural facts that bound how it can be replaced:

* `t_bit ≠ (a_bit + b_bit) mod 12` for the sampled triples, so the target is not a plain
  schoolbook convolution index; the block is a *transformed* accumulation.
* within one block the same `(a_bit, b_bit, t_bit)` triple recurs up to 5 times (e.g.
  `(0,0,0)` five times in the `n = 24` member). Those are not adjacent, and the dqi line
  measured 0 plain cancels tape-wide, so each recurrence is consumed by an intervening
  read/reset — the gadget reuses a computed AND rather than recomputing it.

**Consequence for the `dqi_mult` line** (stated as a lead, not a claim): the unit to
replace is **one 130-CCX gadget with interface `(operand word a, S46, target 70, target
48)`**, replicated 10× in span_fwd and mirrored in span_rev, not a 42-CCX block. Its
cost — 130 CCX for a two-word product, against the 42-AND bilinear optimum for a 12-bit
product — is 3.1× the arithmetic floor, which is where any real saving would have to come
from, and it is invisible to the "42-CCX block" bookkeeping the earlier lines used.

---

## 5. Why the +2.9 GM was wrong (my error, corrected)

If 95,317 T vanished, `T = 367,116 → 271,799` (−25.96 %) and GM would be
`28.1807 × (1/0.7404)^(1/3) = 31.15` (+2.97). That arithmetic is right, and my earlier
"+0.6 GM" note was wrong.

But the 95,317 T is not removable: it is **2,243 multiply groups** (689 CCX word-triples ×
42.9 CCX in span_fwd, 1,554 × 41.2 in span_rev) plus 1,724 CCZ, at the tape's own
multiplier cost. Nothing in it is duplicated (§3), none of it is a rotation (§2), and the
only way to lower it is a cheaper multiplier — which is `dqi_mult`'s axis (rank 42 → ≤ 35),
not a width or alignment rewrite.

For the record, the correct sensitivities: a 10 % T cut = +0.9 GM, 16 % = +1.5 GM,
26 % = +2.97 GM.

---

## 6. Scope

* **Measured on Kaggle CPU:** five kernels of this line, all COMPLETE, static IR read of
  `575b043f` (sha256 `575b043f4fee91a0…`, 479,128,738 B, 57,520,821 ops, Q 890, static T
  367,989 — reproduced exactly by every run). Each kernel deletes the decompressed tape
  before exit so the output fetch returns only JSON.
* **Not done:** no circuit was built, no candidate `.kmb` was patched, **no verifier was
  run**, nothing was submitted or pushed. The barrel-shifter plan was cancelled by the
  measurement before any gate-count work started.
* **Not verified:** the *name* of the 130-CCX gadget (candidates: shared-multiplier
  convolution row; transformed two-word accumulation). The wiring evidence establishes the
  ten-fold broadcast and the two-word accumulator; naming the algorithm needs the
  generator, not the tape.
* **Known artifact, corrected:** `out/regmap.json`'s `ctrl_top[].reg` / `.bit` columns are
  wrong (unmasked register table + `E*` shadowing). All conclusions use raw qubit ids.

## 7. Files and commands

```
experiments/frontier/20261118_push/dqi_align/
  RESULT.md                  this file
  out/align.json             kernel 1: op code census, 10k-op profiles, span gate mixes,
                             42-CCX word-triple census, segments
  out/registers.json         kernel 3: the register table + the S_i contiguity checks
  out/regmap.json            kernel 3: Fredkin-neighbourhood test, per-control clusters
  out/blocks.json            kernel 4 v2: block decomposition, dedup verdict, the full
                             200-block period-4 window with complete bit triples,
                             family_wb46 with the (a_bit,b_bit) multiset hashes
  out/units.json             kernel 2: +-120-op repeated-unit clustering (top coverage 0.3 %)
  out/word_hist.json         kernel 2: target-word / control-word-pair histograms
  out/decay_fit.json         kernel 2: 200-segment T/CX/CCX/SWAP profiles + linear fits
  out/windows3.json          kernel 3: 3 x 20,000-op windows, register-labelled
  k_align/, k_names/, k_regmap/, k_blocks/   kernel sources + metadata
```

`out/windows3.json` was not fetched to this directory (the file is regenerable from
`k_regmap/main.py` in ~15 s of kernel time); `out/blocks.json → pattern_span_fwd` carries
the same information for the period-4 family, with complete bit triples.

```bash
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_align/k_blocks \
      --slug qcc-dqi-align-blocks --account zhuating --competition \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_align/k_blocks \
      --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-align-blocks --account zhuating

# fetch only the small JSON (the kernel deletes the 479 MB tape before exit anyway)
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_zhuating) KAGGLE_CONFIG_DIR=~/.kaggle \
  python -c "from kaggle.api.kaggle_api_extended import KaggleApi as A; a=A(); a.authenticate(); \
  a.kernels_output('zhuating/qcc-dqi-align-blocks','/tmp/blk2',file_pattern=r'blocks\\.json',force=True)"
```
