# DQI decoder-level T probe — 2026-11-16 (part 5)

Mandate: a genuine decoder-level mean-T reduction on the **v12 source** (889 Q), target
**T ≤ 364,000** (GM 28.26) or better. Base = `7cbe8ecf…`, official mean T **383,156.29**
at Q 889, cost **360,733,280,431.94** (`RESULT2.md` §2, unchanged verifier, default salt).

Baseline to *ship* (the v13/v14 tape we already hold): `ccc2ab84…`, Q 890, mean T
368,139.49, cost 347,375,470,571.73.

## 0. Outcome

**The target is not reachable, and both mandated paths are now closed with measurements
rather than estimates.** Four results, all new:

1. **The exact stage shares of the real build** (k14: a Toffoli counter whose total
   reproduces the finished circuit's `num_toffoli_like` **exactly at 384,003** and whose
   build reproduces `7cbe8ecf…` byte-for-byte). `RESULT4.md` §1's shares were **call
   counts, not gate counts** and are wrong by up to 2×; corrected table in §1.
2. **80.9–82.4 % of all DQI T is the field-multiplication primitive** and a further
   12.6 % is AND initialisation — 93–95 % of T is rank-optimal product work. §2.
3. **Path 1 (decision machine) is closed by the machine's measurement model**, not by
   effort: the only measurement primitive is `hmr` = **X-basis measure + Z reset**, whose
   outcome is a fresh uniform random bit. A measured bit therefore cannot certify that a
   *data-arithmetic* block is the identity, so `raw_query_return_*` (592 field products)
   and `odd_full_preimage` (a 17-level elimination) cannot be skipped. Every constructible
   machine is of the form "skip a phase block whose classical mask is all-zero", worth
   `static_T / 2^bits`; the source already has all five, worth 803.0 T of the 846.71 T the
   verifier measures, and every remaining phase block is tagged by ≥ 12 bits
   (≤ 0.064 T). **Marginal decision-machine ceiling on this tape: < 1 T.** §3.
4. **Path 2 (retain/replace) was implemented, built and officially verified:**
   retaining `Norm(u)` across the consuming half-scale removes exactly 1,302 T
   (31 × 42) but needs 12 simultaneously-live helper bits → **Q 889 → 901** →
   cost **369,278,647,729.75, +2.369 % worse**. Break-even at +12 qubits needs
   ΔT ≥ 10,414 T; delivered 1,302 T. Recorded and stopped, as instructed. §4.

**Nothing was packaged and nothing was submitted.**

## 1. Exact stage shares (k14, verified total = 384,003)

Counter rule, calibrated in k11/k11b/k13 and *proved* by the total in k14:

| builder call | emitted | T |
|---|---|---:|
| `ccx(c1,c2,t)`, two qubit controls | CCX | 1 per broadcast element |
| `ccx` with a classical/constant control | `CX` (or `CX if b`) | **0** |
| `ccz(c1,c2,t)`, two qubit controls | CCZ | 1 |
| `ccz` with a classical control | `CZ … if b` | **0** |
| `cswap(b,a,a')` with a qubit `b` | CSWAP | 1 |
| `cswap` with a classical `b` | plain `SWAP` | **0** |
| `init_and(c1,c2,t)`, two qubit controls | `R` + CCX | 1 |
| `init_and` with a classical/constant control | `R` + `CX` / `R` + `X` | **0** |
| `del_and` | `HMR` + `CZ … if b` | **0** (measurement-based uncompute) |
| `cz hmr reset x z swap cx` and all `BIT_*`, `PUSH/POP_CONDITION` | — | **0** |

Verification of the rule against the finished circuit:

```
TOTAL 384003  official 384003  MATCH
components {"ccx":316409, "ccx_folded":24948, "init_and":48210, "init_and_folded":0,
            "ccz":7000, "ccz_folded":488882, "cswap":12384, "del_and_folded":48210}
opcodes    CCX 364619 CCZ 7000 CSWAP 12384 CX 31293155 CZ 538932 SWAP 378664
           HMR 71531 R 48210 X 108090 Z 46469 BIT_INVERT 15439990 BIT_STORE0 1527327
           BIT_STORE1 54936 PUSH/POP 1519774 each   (52,930,855 instructions)
SHA 7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9  MATCH
316,409 + 48,210 + 12,384 + 7,000 = 384,003
335,784 + 23,262 + 5,573            = 364,619  (tape CCX)
```

Note the free foldings the builder performs and that no analysis has credited before:
**488,882 of 495,882 `ccz` emissions** are classical-bit controlled and become
`CZ … if b` (0 T); **48,210 `del_and`** emissions are `HMR` + conditioned `CZ` (0 T);
**24,948 `ccx`** emissions have a closed control and become `CX` (0 T).

### Exact per-stage partition (k14; single monotone counter, consecutive differences)

| stage | T | share |
|---|---:|---:|
| `raw_query_return_NN` — extractor inverse ladder (32 pivots) | 78,611 | **20.47 %** |
| `raw_query_prefix_NN` — extractor forward ladder (35 pivots) | 73,122 | **19.04 %** |
| `shared_seam_restored_raw_inputs` — converter closing | 56,387 | **14.68 %** |
| `odd_full_preimage` — converter preimage | 55,457 | **14.44 %** |
| `adaptive64_scan` — 4,095-position phase scan | 44,286 | **11.53 %** |
| `synthesis_return` — 34 CRT nodes | 37,230 | **9.70 %** |
| `synthesis_prefix` — 34 CRT nodes | 27,965 | **7.28 %** |
| `shared_seam_finish_return_live_inverse` | 6,077 | 1.58 % |
| `projective_finish_prefix` | 1,752 | 0.46 % |
| `odd_border_and_elimination` | 1,577 | 0.41 % |
| `shared_seam_undo_odd_full_preimage` | 1,539 | 0.40 % |
| `blocked_mask_shear`, `adaptive64_histogram`, syndrome gauge, `raw_boundary`, first-three seams, tail | **0** | 0 % |
| **total** | **384,003** | 100 % |

Rolled up by block: **extractor 151,733 (39.51 %)**, **converter 114,960 (29.94 %)**,
**synthesis 65,195 (16.98 %)**, **scan 44,286 (11.53 %)**, **projective finish 7,829
(2.04 %)** — sum 384,003. This reproduces the author's own asserted component ledger
(152,494 / 115,025 / 65,076 / 43,521 / 7,979 − 92) to within 0.5 %, independently.

### Correction to `RESULT4.md` §1

`RESULT4.md` counted `builder.ccx/ccz/cswap` **calls**. `ccx` broadcasts over `km.array`
(one call emits up to 24 gates) and 488,882 `ccz` calls are classical-controlled and cost
zero, so the published per-site T numbers are not gate counts. The worst case is
`direct_carry_arithmetic.restore_with_shared_norm` at "4,139 T/call"; it is **543 T/call**
(99 `emit_prefix` + 99 adjoint product + 108 inverse norm + 84 half scales + 84 quotient
phase + 42 second `init_norm` + 27 inverse phase; every `phase_product` on a classical mask
is 0 T). `divide_deferred` is 291 T/call, matching its ledger exactly. Correct shares:
`raw_query_return_*` 20.47 % (was 23.6 %), `odd_full_preimage` 14.44 % (was 20.2 %),
`raw_query_prefix_*` 19.04 % (was 10.7 %), converter seam 14.68 % (was 20.9 %),
synthesis 16.98 % (was 13.6 %).

## 2. Where the T is: rank-optimal products

| component | T | share |
|---|---:|---:|
| `field_tensor.accumulate_product` (every GF(2^24)/GF(2^12) product term) | ≥ 310,836 | **≥ 80.9 %** |
| `builder.ccx`, other sites (reciprocal / eliminator primitives) | ≤ 5,573 | ≤ 1.5 % |
| `init_and`, two qubit controls (AND initialisations) | 48,210 | **12.55 %** |
| `cswap`, qubit control (routing in `transpose14_core`/`_window`/tail) | 12,384 | **3.22 %** |
| `ccz`, two qubit controls (quotient/phase blocks) | 7,000 | **1.82 %** |
| **total** | **384,003** | 100 % |

(`field_tensor.py:159` is the only `ccx` in `accumulate_product`; k11b measured 335,784
emissions there, of which 24,948 can fold to `CX` when a parity pivot is closed, so the
surviving product terms are 310,836–316,409.)

Product counts, structurally exact from the source:

* extractor ladder: `Σ_{i=3}^{34} i = 592` products in the forward sweep and 592 in the
  return sweep = **1,184 × 99 = 117,216 T (30.5 % of all T, 77 % of the extractor block)**.
  The ladder is a Möbius/continuant evaluation `n_j = (n_{j−2} ⊕ h_{j−1} n_{j−1})/c_{j−1}`
  at node α_i, and the return step is its exact inverse; each is `i` variable×variable
  GF(2^24) products, i.e. optimal for the generic continuant, and the two are irreducible
  as a pair.
* synthesis: `Σ_{r=1}^{34}(r+2)·42 = 27,846 T` in the prefixes and `Σ_{r=1}^{34} r·42 =
  24,990 T` in the returns, plus `34 × 363 = 12,342 T` for the paired 24-bit closings.
  Both sums are forced by the CRT/Forney representation size growing by one word per node.
* `divide_deferred` 291 T = 99 (cofactor product) + 42 (`init_norm`) + 66
  (`inverse_twelve`) + 84 (two half scales). `restore_with_shared_norm` 543 T. Both at
  their floor: dividing by `u` costs one 24-bit product plus two 12-bit scalar products
  (`1/Norm(u)` acts as a base-field scalar), and no cheaper decomposition exists — the
  alternative "compute `1/u` once, use it twice" is 381 T versus the 366 T actually used
  for two divisions in the return.

So a −19,156 T (−5.00 %) cut needs to delete ~194 24-bit products or ~456 12-bit products,
and there is no duplicated, dead or removable product in the tape (all four sound peephole
classes are empty; `RESULT.md` §5, `RESULT3.md` §2 with a bit-exact null control).

## 3. Path 1 — decision machine over measured bits: closed by the measurement model

The source's decision machines are all of one shape:
`active = [classical mask ≠ 0]; push_condition(active); <phase block>; pop_condition()`
(`zero_mask_scan.point_cell` for the 4,095-position scan, `last_return_child_norm_guard`,
`scalar_inverse_six`, the `paired_dual62` gates, `converter_zero_predicate`,
`tail_or_gauge_fresh_zero_phase`, `direct_carry84_selected_target_parities`). Their exact
expected discount, from the source's own `v7_events.snapshot` (which `build_v7` asserts
reproduces the official measured mean to the digit — 384,003 − 846.71 = 383,156.29):

```
paired_dual62_exclusive_overlap   27 T × 18 / 2^0   = 486.000
tail_or_gauge_fresh_zero_phase    22 T × 21 / 2^1   = 231.000
tail_or_gauge_fresh_zero_phase    10 T ×  1 / 2^1   =   5.000
converter_zero_predicate          10 T × 16 / 2^1   =  80.000
scalar_inverse_six                 4 T ×  7 / 2^6   =   0.4375
last_return_child_norm_guard      15 T ×  1 / 2^6   =   0.2344
converter_inverse_phase27         27 T × 18 / 2^12  =   0.1187
direct_carry84_selected_target_parities 84 T × 32 / 2^24 ≈ 0.0002
                                              total = 802.79 T
```

Measured mean discount is 384,003 − 383,156.29 = **846.71 T**; the remaining 43.9 T is the
certified correlated occupancy of the adaptive scan (`exact_occupancy.certificate_values`).
**So 94.8 % of the achievable decision-machine value is already banked.**

Why no new machine can be built:

1. `hmr` is documented and implemented as **"X-basis measurement and Z-basis reset"**. Its
   outcome is a fresh uniform random bit (which is exactly why every fresh-mask discount is
   `t/2^bits` and why that model reproduces the official mean to the digit). There is **no
   Z-basis measurement** and no way to write a computational-basis value into a classical
   bit. So a measured bit carries no information about a data value.
2. A data-moving block (a ladder of field products, a 17-level elimination, a `cswap`
   route) is the identity only when its *value* predicate is zero. No measured bit can
   certify that → `raw_query_return_*` (20.47 %) and `odd_full_preimage` (14.44 %) are not
   skippable by any measured flag, whatever predicate is designed.
3. A gated block is sound only when its action is a polynomial in the mask that vanishes at
   mask = 0 — i.e. a phase repayment. Gating is then worth `static_T / 2^bits`. Every
   remaining phase block in the tape is tagged by a **≥ 12-bit** HMR mask
   (`phase_product` 24-bit, `phase_affine_quotient` 24-bit, `_quotient_phase_with_norm`
   24-bit, `erase_norm` / `Narrow.phase_quotients12` 12-bit), so the marginal gain is at
   most `264 / 4096 = 0.064 T` per block — **< 1 T over the whole tape**.
4. The tape already contains 538,932 `CZ … if b` instructions: everywhere a classical
   control existed, the builder has already folded the gate to zero T. There is no latent
   classical conditioning left to exploit.

**The previously quoted "14.2 % of T (57,119 T) decision-machine ceiling" is therefore not
constructible on this architecture: it required value-conditional branches, and the machine
has no value measurement.**

## 4. Path 2 — retain/replace, implemented and measured

`direct_carry_arithmetic.restore_with_shared_norm` builds `Norm(u)` twice: once inside
`_inverse_norm` (line 124, then inverted in place) and once again at line 155 for the
inversion's own phase block, because the in-place inversion destroys the norm. Candidate:
copy the norm into a 12-bit retained register before the inversion and use the retained copy
for the trailing block. That removes exactly one 42-T `init_norm` per call, 31 calls.

Kernel `zhuating/qcc-dqi-v12retain` (build + unchanged official verifier, 102,400 shots):

```
Q 901   static_T 382701  (delta vs 384003: -1302, exactly 31 x 42)
opcodes CCX 363317 (was 364619)  CCZ 7000  CSWAP 12384   [all other opcodes unchanged]
SHA a113e3402aac3162439c389462b950d9a640589c994833e2ff86e0259bbc6d18  455,194,495 bytes

VERIFY salt=''            Q 901  T 381854.4763  score 369278647729.746  err 0/0  +2.368888%
VERIFY salt='dqi-salt-2'  Q 901  T 381854.1535  score 370974299201.836  err 1/0  +2.838945%
VERIFY salt='dqi-salt-3'  Q 901  T 381854.1450  score 369278327303.993  err 0/0  +2.368799%
```

Baseline for comparison: Q 889, T 383,156.29, score 360,733,280,431.94, 0/0.

**Verdict: worse, by construction.** The retained register makes the peak 864 + 36 helpers
+ 1 flag = 901. Break-even arithmetic at Q 889:

| change | ΔT | ΔQ | Δcost |
|---|---:|---:|---:|
| one qubit at Q 889 | 862 T | +1 | 0 % |
| this candidate | −1,302 T | +12 | **+2.369 %** |
| break-even at +12 Q | −10,414 T | +12 | 0 % |
| whole retention family (31 returns + 34 synthesis pair-closings) | −2,730 T | +12 | +1.99 % |

The entire retain/replace family is 3.8× short of paying for its own 12 qubits. No
zero-qubit version exists: `Norm(u)` and `1/Norm(u)` must be live simultaneously while the
consuming half-scale runs (which itself needs a 12-bit scratch), and every reordering that
avoids the copy destroys one of the two.

The one value error at `dqi-salt-2` is reported as measured. The change alters only *when*
`Norm(u)` is computed — never a value — and the candidate is 0/0 at the other two salts, so
this reads as a shot-noise/tolerance event rather than a correctness failure; it does not
affect the decision, since the candidate loses on cost.

## 5. Why 364,000 is out of reach here

| route | needed | delivery |
|---|---|---:|
| v12 (Q 889) → target T 364,000 | −19,156 T (−5.00 %) | −1,302 T (§4) |
| v12 → merely tie today's shipped tape (Q 889) | −14,216 T (−3.71 %) | −1,302 T |
| shipped tape (Q 890) → target T 364,000 | −4,139 T (−1.12 %) | not reachable from v12 at all |

`RESULT3.md` §1 already showed the v12 line starts 3.71 % behind the shipped tape, so every
T result here has to recover a deficit before it can score. The numbers above now close both
mandated axes with evidence: 93–95 % of T is rank-optimal field product + AND work
(§2), the T surface is saturated (§`RESULT.md` §5, `RESULT3.md` §2), the decision-machine
axis is exhausted by the measurement model (§3), and retention loses to qubit cost (§4).

The only remaining ≥ 1 % levers are structural and belong to a new decoder generation:
`out-of-place` division (Q 864, `RESULT2.md` §4–5), the v13 conditional-CSWAP-free routing
(v12 carries 12,384 CSWAP = 3.22 % that v13/v14 already eliminated, `RESULT3.md` §2.1), or
fewer products per syndrome pass.

## 6. Receipts

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k11 | `zhuating/qcc-dqi-v12stage` | first exact-counter attempt (broadcast-aware) | counter 946,043 vs official 384,003 → **rule wrong**, no output (§1) |
| k11b | `zhuating/qcc-dqi-v12attrib` | per-call-site emission attribution | found `ccz`-with-classical-control, `del_and`, `cswap`-with-bit and `init_and`-with-constant are **0 T**; located `field_tensor.accumulate_product` as the dominant site |
| k13 | `zhuating/qcc-dqi-v12stage2` | exact rule, first try | 457,161 vs 384,003 → `init_and` never folds, `ccx` folds 24,948 |
| **k14** | **`zhuating/qcc-dqi-v12stage3`** | **final exact partition** | **384,003 == official, sha `7cbe8ecf…` MATCH**, full stage table (§1) |
| **k12** | **`zhuating/qcc-dqi-v12retain`** | **path-2 candidate: build + 3-salt official verify** | **Q 901, T −1,302, cost +2.369 %, 0/0, 1/0, 0/0** (§4) |
| control | `zhuating/qcc-dqi-v12build` | v12 as published (`RESULT2.md` §2) | 889 Q / 383,156.29 T / 360.733e9 / 0-0 |

All runs were Kaggle CPU kernels (`enable_gpu: false`, no internet, competition data
attached, DQI source from the private dataset `zhuating/qcc-dqi-source-v12`); nothing was
simulated locally and nothing was submitted.

## 7. Verification scope, stated honestly

* Every score quoted is the **unchanged official verifier**
  (`verifiers/dqi/verify_submission_dqi.py`, `ProblemSpecDQI.benchmark_instance()`,
  102,400 shots, batch 256, 4 workers) run on a Kaggle CPU kernel against the candidate
  `.kmb`.
* The stage and component tables are **measured**, not modelled: the counter total equals
  the finished circuit's `CCX+CCZ+CSWAP` exactly (384,003) and the instrumented build
  reproduces the published `7cbe8ecf…` SHA-256 byte-for-byte, so the instrument changes
  nothing.
* The per-call-site split of the CCX total between `accumulate_product` and the other
  primitives is bounded (310,836–316,409) rather than exact, because 24,948 emissions fold
  to `CX` and the attribution run did not separate them per site. The four-way
  `ccx/init_and/cswap/ccz` split **is** exact.
* The 1,184-product extractor ladder and the synthesis product sums are derived from the
  source (`Σ_{i=3}^{34} i = 592` each way; `Σ(r+2)·42` and `Σ r·42`), and they agree with
  the measured stage totals to 0.5 %. The **measured** stage table in §1 is the primary
  evidence; the derivations explain it.
* The 846.71 T measured discount and its 802.79 T event-accounting are the source's own
  `v7_events.snapshot` model, corroborated by the official measured mean; the residual
  43.9 T is the certified correlated scan occupancy.
* No candidate was submitted to Kaggle; no leaderboard number was produced by this work.
  The "gold 28.65386 needs 327.4e9" calibration is inherited from `RESULT2.md` §6 and is a
  frontier hypothesis, not measured here.
