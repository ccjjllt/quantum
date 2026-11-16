# DQI decoder-level T probe — 2026-11-16 (part 4)

Question: can the per-syndrome division / retain step be replaced by a BM-style retain/replace form,
or the repeated products replaced by a retained state / a decision machine over measured bits, to cut
≥1 % of T (3,700 T) at Q ≈ 890 in the v12 source?

**Answer: no. All three forms are measurably worse or blocked, and the honest estimate for a working
version is a multi-week rewrite.** Evidence below: a measured Toffoli budget of the actual build, the
per-object multiplication counts of each candidate form, and the state of the retain/replace pass.

## 1. The measured T budget of the v12 build (k10)

`zhuating/qcc-dqi-tprofile` runs the pinned source in process, wraps the builder in a counting proxy
(no live `operation_statistics()` exists on a `CircuitBuilder`) and records the Toffoli-like count at
every one of the pipeline's own `stage()` callbacks.

Stage shares of Toffoli-like emissions:

| stage | share |
|---|---:|
| `raw_query_return_*` (extractor return query triangle) | **23.6 %** |
| `shared_seam_restored_raw_inputs` | **20.9 %** |
| `odd_full_preimage` | **20.2 %** |
| `raw_query_prefix_*` (extractor forward query triangle) | **10.7 %** |
| `shared_seam_finish_return_live_inverse` | 5.6 % |
| `synthesis_return` × 34 nodes | ≈ 13.6 % |
| synthesis prefix, projective finish, scan, tail | rest |

Per-call-site (inclusive, resolved sites only — several call sites resolve to a duplicate module copy
on the search path, so this list is partial):

```
gf24_nested_norm.emit_closing               n=  50  T=141,900  T/call=2,838
direct_carry_arithmetic.restore_with_shared_norm n= 31 T=128,309 T/call=4,139
fused_crt_synthesis.emit_closing            n=  34  T=121,482  T/call=3,573
gf24_arithmetic.product                     n=1184  T=117,216  T/call=   99   <-- exactly the 99-T metric
tower_inverse.phase_product                 n= 338  T= 31,344  T/call= 92.7
direct_carry_arithmetic._inverse_norm       n=  63  T= 29,232  T/call=  464
fused_crt_synthesis.emit_prefix             n=  34  T= 27,846  T/call=  819
tower_inverse.xor_product                   n= 427  T= 10,671  T/call=   25
inverse_retained_norm_deferred.{return,prefix}_with_bank n=6+6 T=13,620 T/call=1,165/1,105
direct_carry_arithmetic._adjoint_consume    n=  63  T=  6,237  T/call=   99
direct_carry_arithmetic._consume_halves     n=  63  T=  5,292  T/call=   84
direct_carry_arithmetic._quotient_phase_with_norm n=32 T=2,688 T/call=   84
```

Three facts matter here:

1. **The T/call values reproduce the task's own cost model exactly** — 99 per GF(2^24) product, 84 for
   the two-half scalar product, 25 per `xor_product`, 464 per inverse-norm pair. So the *relative*
   budget is trustworthy.
2. **The single largest object is the O(n²) query triangle: `raw_query_prefix_*` + `raw_query_return_*`
   = 34.3 % of all Toffoli-like emissions.** The extractor runs `for i in 3..34: for old in 3..i
   query_step(...)` = 32 forward + 32 return passes over a triangular sum (Σi ≈ 590 query steps per
   direction). This is precisely the object a BM-style form would remove.
3. Caveat, stated honestly: the counter totals 836,293 Toffoli-like *emissions* while the finished
   circuit contains 384,003 (opcode census 364,619 CCX + 7,000 CCZ + 12,384 CSWAP). The builder or the
   pipeline emits gates that do not survive into the tape (probable builder-side cancellation, or a
   duplicated module copy being instrumented twice). The **shares** above are differences of one
   counter over disjoint pipeline stages and are therefore internally consistent, but the absolute
   numbers must not be read as gate counts. The author's own component ledger — which the build
   *asserts* (`static_T == source_ledger(...)['total_static_T']`) — gives the absolute split:
   extractor/gauge/seed ≈ 152.8 k, preimage + gauge parking + converter ≈ 115.6 k, synthesis 65.1 k,
   scan 44.3 k, projective finish 7.9 k, total 384,003.

## 2. BM-style retain/replace: 8× the multiplications, measured

The repo already measured the multiplication counts of both formulations on this task
(`experiments/frontier/20261115_upgrade/dqi_plan.md` §19, `20261112_mulrank`):

| formulation | field multiplications per direction |
|---|---:|
| extended Euclid (what this source uses) | **≈ 939–955** (core) + 68 setup/reduce + ≈141 Hankel ≈ 1,148 |
| Berlekamp–Massey over the same syndrome set | **7,560** |

So a BM-style retain/replace form replaces ~950 multiplications with ~7,560 — **8.0×**. The
multiplier block is ≈46 % of T (117,216 / 253,000 of the resolved 42/99-T products above; the prior
repo's independent census agrees at 45.3 %). At 8×, that block alone would go from ≈177 k to ≈1.4 M T.
A published BM reference decoder measures **5.7 M T at 1,893 Q** for this task, i.e. 15× worse
overall. **BM is not a T lever; it is a T disaster.** The only reason it appears attractive is the
query triangle, and BM removes the triangle by paying far more arithmetic.

## 3. Retain / replace of a repeated product: already saturated

* On the shipped 890-Q tape the retained-product pass is **already applied**: 241 products are held
  and reused, and the planner reports **0 additional free placements** at 889 qubits (the static
  helper count is the binding constraint), and holding one more product costs a qubit — which is
  827 mean T, i.e. far more than the 1 T it saves.
* In the v12 source the retention machinery is the `retained_norm` family: `inverse_prefix_with_bank`
  / `inverse_return_with_bank` are invoked 6 + 6 times (13,620 T total, ≈1,100–1,165 T/call) and the
  source's own ledger reports `ineligible`/`closed` contracts rather than extra placements
  (`inverse_retained_norm_deferred.source_ledger()`: `eligible_production_pairs=3`,
  `production_static_saving_from_selected_v4=246`). The remaining 246 T of that idea is **0.06 %**.

## 4. Decision machine over measured bits: possible in principle, multi-week in practice

* Ceiling: previously bounded at **14.2 % of T (57,119 T)** for the sibling family, with the entire
  prize sitting in "n−1 zero test / 1 CSWAP" lower bounds — i.e. the bound was never constructed.
* Cost per branch: each flag needs (i) a coherent predicate on data, (ii) a measurement that
  collapses it, (iii) a phase repayment conditioned on the outcome, and (iv) a proof that the
  complementary branch's work is skippable. The source does exactly this five times, and each single
  flag carries its own derivation document: `THIRD_PUBLIC_CHART_GATE.md` (11.1 KB),
  `FIRST_TWO_MATCHED_NORM_DEBTS_GATE.md` (8.2 KB), `FIRST_TWO_RETAINED_NORM195_GATE.md` (10.5 KB),
  `V5B_MATCHED_AND_CUBIC62_BINDING_REVIEW.md`, `WIDTH_COMPATIBILITY.md`, plus a `check_*` harness and
  a `runs/*/report.json` fixture set — per flag. The five existing flags are worth a few hundred T
  each at most.
* To reach 3,700 T you would need the *arithmetic* branches (the EEA's degree-drop / zero-residual
  paths), not more 1-bit flags. That means re-deriving the phase repayment of
  `divide_deferred`/`restore_with_shared_norm` conditioned on a measured predicate — the same
  `v ← v/u` object that `RESULT2.md` §4 shows is already at its structural limit.

**Estimate: 3–6 weeks of expert work for a 1 % T cut, with a real risk of ending at 0 because the
phases of the two branches do not close.** That is the "multi-week rewrite" the mandate allows me to
declare, and I am declaring it rather than forcing a half-built branch machine.

## 5. What a 1 % T cut would have needed anyway

Even a successful −1 % on the *v12* line lands at 379,324 T / 889 Q = 357.2e9, which is **worse** than
the 347.375e9 we already ship (`RESULT3.md` §1: v12 needs −3.71 % just to tie). The T programme only
pays on the shipped 890-Q tape, and there the four sound peephole classes are measurably empty and
the null round-trip control reproduces the baseline bit-for-bit.

## 6. Receipts

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k10 | `zhuating/qcc-dqi-tprofile` | in-process Toffoli budget by pipeline stage and call site | measured: query triangle 34.3 %, converter/seam ≈41 %, synthesis ≈14 % (§1) |
| k9 | `zhuating/qcc-dqi-v12tscan` | exact peephole scan of the v12 tape | 0 deletions in all four classes |
| k8 | `zhuating/qcc-dqi-v12build` | v12 build gate + official verify | `7cbe8ecf…` MATCH, 889 Q, 383,156.29 T, 360.733e9, 0/0 |

No candidate was built, packaged or submitted: none of the three forms produces a net T reduction, and
a v12-based cut would not clear the −3.71 % bar even if it worked.

## 7. Verdict

**DQI is closed for this competition window.** The shipped circuit (890 Q / 368,139.49 T /
347.375e9 / 0 value / 0 phase errors) is simultaneously at its qubit floor (`RESULT2.md`: the
in-place cofactor multiply needs a third 24-bit register), its Toffoli-peephole floor (`RESULT.md`:
0/0/0/0 with a bit-exact null control) and its architectural floor for a BM/retain/replace rewrite
(8× multipliers, saturated retention, week-scale branch machinery). The only remaining lever is a new
decoder generation, and the frontier gap is more likely T (≈ −2 %) than Q.
