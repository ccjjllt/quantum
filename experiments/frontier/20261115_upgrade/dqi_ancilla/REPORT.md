# DQI ancilla audit — where the 49 non-syndrome qubits are, and whether any can go

Date: 2026-11-15. Read-only source analysis. **No circuit was built, no simulation was run,
no Kaggle job was started, no file outside this directory was touched.**

Source read: `/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_upgrade_src/dqi/dqi_source`
(the second copy at `…/dqi_src/dqi_source` is byte-identical — `diff -rq` returns empty).
All `path:line` below are relative to that tree. Reference algorithm read from
`/Users/zhaohuaxiang/ccjjllt/quantum/data/competition/verifiers/dqi/dqi_reference_circuit.py`.

---

## 0. TL;DR

1. The 49 ancillas are **24 + 1 + 24**, exactly:
   * **24** = the working carry word pair (`carry`), allocated once at
     `after_c5/integration_v3/integrated_pipeline.py:163`, live from there to `:202`;
   * **1** = the gauge-chart sentinel flag (`rolling_tail.py:226`), live `:167 → :198`;
   * **24** = one **transient** GF(2^24) scratch word pair. It appears at **five different call
     sites**, never two at once, always freed before return.
2. Every one of those five sites independently peaks at **864 + 1 + 24 = 889**.
   Q is a max over the whole tape, so **no single-site patch can move Q**. A one-qubit win
   requires fixed-point surgery on *all* of the flag sites, not one.
3. Verdict: **no cheap qubit.** The only plausible route from 889 to 888 is to convert the
   three 1-bit *predicates* (tail flag, third-chart predicate, gauge sentinel) into classical
   controls. ΔT for that is **not derivable from source reading**; the structural minimum is
   0 T, the pessimistic bound is a few hundred T, and the break-even is +863 mean T.
   Best case +0.0205 GM points; realistic ±0.010. Q=887 (or lower) requires shrinking the
   24-bit scratch to 23 bits at five sites — a new arithmetic identity, not a patch.

---

## 1. What the decoder must compute (contract recap)

`data/competition/verifiers/dqi/dqi_reference_circuit.py:73-138` fixes the interface: 70
syndrome registers `S0..S69` of width 12 (`:621`) and 4095 classical `E0..E4094` (`:622`).
The reference build allocates `reg_a[:3]` (36) + `reg_b` (73×12 = 876) + 5 range registers
(`logm = m.bit_length()+1 = 8` each ⇒ 40) + flag (1) + counter (2) + halting counter (8) = **963
ancillas on top of 840**, i.e. Q = 1803 (`:103-114`). Our generator is at 49.

The body is the same three-stage Reed–Solomon MBUC pipeline: forward synchronized EEA
(`_synchronized_eea`, `:124`), Chien/Forney phase kickback (`:126`), reverse EEA (`:128`).
Our production source replaces the generic EEA by a direct-carry polynomial EEA over the
*same* 840 syndrome wires (the 35 "heads" are 24-bit views of `S_{2i}‖S_{2i+1}` —
`integrated_pipeline.py:162`), plus one 24-bit carry word and one 24-bit transient.

So the *algorithm* needs, at steady state, exactly one extra 24-bit word beyond the 840
syndrome wires. Everything else is transient.

---

## 2. The ancilla budget

`Q = 889` and `Q = 840 + 49`. The 49 decomposes as:

| # | object | width | allocated at | live range | measured + released? |
|---|---|---:|---|---|---|
| 1 | `carry` (working word pair; `N[0]` / `gauge_other`) | **24** | `after_c5/integration_v3/integrated_pipeline.py:163` | `:163` (after `Public.emit`) → `builder.free(carry)` at `:202`; restored by `x(carry[0])` at `:201` | never measured; **freed**, `build_v7.py:53` asserts `num_allocated_qubits == 840` afterwards |
| 2 | gauge sentinel (`GaugeRecord.flag`) | **1** | `night_c27/controller/rolling_tail.py:226` (`gauge_prefix`) | `integrated_pipeline.py:167` → `:198` (`Tail.gauge_return`) | HMR'd by `erase_zero_flag` (`rolling_tail.py:234`) then freed (`:235`) |
| 3 | transient GF(2^24) scratch | **24** | five sites, see §3 | microseconds of tape each; never two at once | HMR'd into a classical mask, always freed |

That is 24 + 1 + 24 = **49**, and it does sum. There is no unexplained residue, no
"compiler bookkeeping" qubit, and no qubit that survives to the end (`build_v7.py:53-54`).

Two supporting facts about the accounting:

* `num_allocated_qubits` counts `create_quantum_register` qubits as well — `set_max_qubits`
  docstring (local kickmix 0.1: *"This includes both qubits returned by `alloc_qubits` and by
  `create_quantum_register`"*). Hence the pipeline checks `== 840` at the end and `== 865`
  mid-prefix (`check_key_boundary.py:50`).
* `Circuit.num_qubits` is the **high-water mark of the id space**, which with kickmix's LIFO
  free list equals the peak simultaneous allocation. I verified this locally with a 13-line
  builder script (no simulation): register 12 + `alloc_qubits(3)` ⇒ `num_allocated = 15`;
  `free` + `alloc_qubits(2)` ⇒ `num_allocated = 14` but `finish_circuit().num_qubits = 15`,
  and the re-allocation returned ids `[14, 13]` (LIFO). This matches the shipped-file audit
  quoted in `dqi_plan.md` §8 (`distinct_indices_used 889, min 0, max 888, UNUSED_IN_0..Q-1 0`),
  which rules out any id gap.

**A discrepancy to record, not to hide.** `build_v7.py:62` asserts `static_T == 384003` and
`v7_pipeline.py` README says "384003 static T, Q889, mean ≈383156.20". The *shipped* file
`821bf8d1…b672a3` has `static_toffoli_like = 383414`, `mean T = 383008.383203125`
(`dqi_plan.md` §3.2, measured). So this source tree is ~589 static T **newer** than the
submitted tape (it is the v7/adaptive64 variant). Width is unaffected — both are Q=889 — but
any ΔT prediction must be compared against 383,008 mean, not 383,156.

---

## 3. The peak is a plateau: five independent witnesses at exactly 889

This is the central finding, and it is what kills the one-qubit plan.

| site | where | live data | + predicate | + scratch | = Q | measured evidence |
|---|---|---|---:|---:|---:|---|
| **A** extractor forward | `direct_carry_first2.py:72` → `direct_carry_arithmetic.py:37` | 840 + 24 | 1 | 24 | 889 | `check_extractor_width.py:98,114` (`front.num_qubits == 889`, `num_allocated == 864`) |
| **B** extractor return | `first3_retained_norm_adapter.py:114` → `direct_carry_arithmetic.py:120` → `gf24_nested_norm.py:269` | 840 + 24 | 1 | 24 | 889 | same tape as A |
| **C** third-chart return | `third_pivot_chart.py:93-130` | 840 + 24 | 1 (`:115`) | 24 (`inverse_retained_norm_deferred.py:80,87`) | 889 | `third_pivot_chart.py:99-100` *"At most 25 new quantum wires are live, including this new predicate; the production caller has 864 retained wires at entry, hence Q889"*; `check_third_pivot_chart.py:25,183` |
| **D** CRT synthesis, 34 nodes forward + 34 return | `fused_crt_synthesis.py:111`; return via `gf24_nested_norm.py:305` | 840 + 24 | 1 (gauge sentinel) | 24 | 889 | `check_key_boundary.py:62` — a circuit containing **only `emit_key_prefix`** already reports `num_qubits == 889` |
| **E** converter/outer frame | `local_flag_window.py:29,50,71` + `monic_forney.py:47` | 840 + 24 | 1 step flag (+ parked gauge) | 24 (one of them the loaned gauge wire, `gauge_park_lender.py:36-43`) | 889 | `check_local_flags.py:40,113` (`RETAINED = 865`, `prefix.num_qubits == 889`) |

Consequences, all of them unwelcome:

* The public note in `dqi_plan.md` §3.2 ("the peak 889 adds a second 24-bit working word and
  one flag **in the converter/scan stage**") has the right *count* and the wrong *location*.
  `check_key_boundary.py:62` proves 889 is already reached inside `emit_key_prefix`, i.e.
  in the extractor/synthesis, before the converter is emitted at all. The converter is a
  fifth witness, not the first.
* `night_c27/build_candidate.py:74` asserts `circuit.num_qubits == 890` for the pre-`rolling_tail_early`
  build. `rolling_tail_early.py:1-14` documents the change that removed that wire
  (*"The former clean spare is allocated only around the two-flag predicate/swap boundary,
  never across arithmetic"*, `arithmetic_flag_wires=1`, `modeled_raw_peak_Q_for_864_data=889`
  at `:132`). **The 890→889 step was already taken by exactly the kind of surgery proposed
  below, and the author has documented the template.**
* Therefore a patch that relieves A alone, or B alone, or C alone, or D alone, or E alone,
  changes `num_qubits` by **zero**. That is not an estimate; it is what "max" means, given
  five witnesses all sitting on the boundary.

Environment for the record: the capped build `after_c5/integration/runs/engineering64/build/build.json`
never shows a *stage callback* above 877, yet reports Q=889 — the `stage=` hook samples only
~130 coarse boundaries (`integrated_pipeline.py:177,191`), so a 24-wide transient inside a
stage is invisible to it. Any per-stage instrumentation must wrap `Builder.alloc_qubits`
(§6.3), not the `stage` callback.

---

## 4. Candidate list, ranked

"ΔT" below is the change in **mean** Toffoli-like gates. Break-even from
Q=889/T=383,008 is `ΔT ≤ 383,008·((889/888)²−1) = **+863.1**` (exact: 383,871.12 − 383,008).
The task brief quotes +858 and the older note quotes 862.2; both use slightly different T
anchors. The number I use throughout is **+863** mean T.

| rank | candidate | qubits saved *in isolation* | ΔT (structural) | patch effort | verdict |
|---:|---|---:|---|---|---|
| — | **D-park**: HMR the gauge sentinel after `gauge_prefix`, re-prepare before the converter | D: 889→877 | 0 (HMR + `x` from mask; Clifford only) | small, 2 functions | **worthless alone** (A,B,C,E still 889) |
| — | **E-park**: park the converter's per-step flag during `Step.header` | E: 889→888 | 0 (same trick, `Step.release` at `local_flag_window.py:35-37` already exists) | small | **worthless alone** |
| 3 | **A/B-park**: park the extractor's tail flag across `divide_deferred` / `restore_with_shared_norm` | A,B: 889→888 | 0 … +560 (`toggle_zero` on 12 bits = 11 T, 2 cswaps = 6 T, ×40 slot ends) | medium, touches `rolling_tail_early` invariant | **worthless alone** |
| 2 | **C-park**: park the third-chart predicate during the two `inverse_return_with_bank` calls | C: 889→888 | 0 … +40 | small, one function | **worthless alone** |
| 1 | **All of D+E+A/B+C together** | **889 → 888** | 0 … +600 | large, 3 modules + 2 invariants | the *only* route to +1 qubit |
| — | shrink the 24-bit scratch to 23 bits | 889 → 888 at every site | unknown, large | research | not a patch |
| — | remove `carry` (24) or `gauge_other` | 889 → 865 | ≥ 100k (recompute a 24-bit word at every use) | rewrite | already closed in `dqi_plan.md` §3.2 |

Notes on the ranking:

* Ranks 3/2/D/E are ordered by *mechanicalness*, and none of them is worth building alone.
  I list them because they are the pieces of the only composition that works.
* The composition is *not* "keep removing flags until Q drops": each flag family is a
  different object living in a different span (tail: `:41-83`; third chart: `:115-124`;
  gauge: `:226-235`; converter step: `:29-37`). All four spans tripping 889 must fall.
* After 888, the next step (887) needs the 24-bit scratch at every site to become 23 bits.
  There is no 1-bit of slack anywhere in it: it is the output word of a GF(2^24) product
  (`direct_carry_arithmetic.py:37`, `gf24_nested_norm.py:269,305`) or the two top
  coefficients of `q_i·N + P·D` (`fused_crt_synthesis.py:111-129`, where `temporary` is
  literally the vector slots `r` and `r+1` of the in-place linear map, see
  `prefix_rows` at `:49-58`). Neither can be 23 bits without a new algorithm.

### Why the "obvious" cheap wins are not wins

* *"The synthesis `temporary` is idle most of the time — just free it."* It is already freed
  (`fused_crt_synthesis.py:129`), and the `carry` high half that is idle during synthesis
  (`integrated_pipeline.py:170` only keeps `carry[:12]` in `D`) still has to survive to
  `outer.emit_prefix(..., gauge_other=key['carry'][12:])` at `:218`. Parking it costs 0 T and
  only moves witness D.
* *"One syndrome word is dead at the peak."* No: all 35 heads live in `N`,`D`,`P` and are
  uncomputed at `integrated_pipeline.py:203`. The audit's `min_qubits = 889` (interval
  colouring) and `UNUSED 0` agree.
* *"Borrow a wire from the `E` registers."* They are classical (`:622`); Q counts quantum only.
* *"`max_qubits` is just a cap — lower it."* `set_max_qubits` raises on over-allocation
  (docstring); `build_v7.py:38` sets 889 and `:59` asserts 889. Lowering it to 888 makes the
  build fail, it does not shrink the tape.

---

## 5. Verdict

**No. There is no candidate whose ΔT is *provably* under the break-even, because there is no
candidate that removes a qubit at all in isolation.**

* Cheap, provable, zero-T changes exist (`D-park`, `E-park`), but each is worth **0 qubits**:
  the peak has five independent witnesses all at 889, and Q is their max.
* The only composition that yields 888 is the three-flag surgery (§4 rank 1). Its ΔT is
  **not derivable from source reading** — the structural floor is 0 T (all three parks are
  HMR + basis re-preparation + classically-conditioned gates, i.e. no Toffoli), and the
  pessimistic ceiling is ≈ +600 T, which still clears +863.
* Plausible removal: **1 qubit**, not 12 and not 49. Expected gain **+0.0205 GM points** at
  ΔT = 0, **+0.0062** at ΔT = 600, **0** at ΔT = 863.
* Q=887 is not reachable by patch: it needs the 24-bit product scratch at five sites to
  become 23 bits.
* Against the public precedent at Q=877 (`T ≈ 485,272`): irrelevant here. Copying that
  decoder's 12-qubit saving onto our T would need `T ≤ 393,561` (ΔT ≤ +10,553), i.e. it is
  a different algorithm, not a graft.

Recommendation: **do not spend a Kaggle run on a single-site park.** Either do the three-flag
change as one unit and measure it, or leave Q at 889. The expected value of the partial work
is exactly zero.

---

## 6. The most promising patch, specified for someone else to implement

Because no single edit moves Q, the "single most promising patch" is the **smallest set that
does**: classicalise the three 1-bit predicates. Below is the first and highest-leverage
member (`D-park` + `E-park` share one object, the gauge sentinel), plus the exact test plan
that makes the plateau observable. If only one thing is implemented, implement this one — it
is 0 T by construction, it retires two of the five witnesses, and it is the prerequisite for
`A/B` and `C`.

### 6.1 The invariant

> The gauge sentinel is only ever *read as a control*: `builder.cswap(record.flag, …)`
> (`rolling_tail.py:228`, `:233`; `gauge_park_lender.py:98,114`) and
> `Outer.emit_prefix(..., gauge_flag=key['gauge'].flag)` (`integrated_pipeline.py:218`).
> Therefore it may be measured into a classical bit at the end of `gauge_prefix` and the
> wire returned to the pool; every later use becomes *classically conditioned* on that bit.
> The contract `f=1 ⇒ mu=0` (`gauge_park_lender.py:5-8`) is preserved because the measurement
> is in the computational basis of a predicate that was XORed into a clean `|0>` wire.

### 6.2 The edit

1. `night_c27/controller/rolling_tail.py:218-229` — `gauge_prefix`: after
   `builder.cswap(flag[0], carry[:12], carry[12:])`, add
   `mask = builder.alloc_bits(1); builder.hmr(_array([flag[0]]), mask); builder.free(_array([flag[0]]))`
   and return `GaugeRecord(mask)` (the dataclass field keeps the name `flag`).
2. `rolling_tail.py:232-235` — `gauge_return`: replace `builder.cswap(record.flag, …)` with
   the same cswap under a classical condition (`builder.cswap` with a `km.b` control, or, if
   kickmix rejects a classical control, three `builder.cx(..., control=record.flag)`);
   `erase_zero_flag` is no longer needed because there is no coherent wire left; drop it.
3. `after_c5/integration_v3/integrated_pipeline.py:167` — unchanged (the record is opaque).
4. `after_c5/converter_width/gauge_park_lender.py:22-43` — `GaugeLender.__init__` takes the
   classical mask instead of a wire; `alloc_qubits` **always** delegates to the builder
   (there is no wire to lend), `free` drops the loan bookkeeping, `GaugeCarrier.park/unpark`
   (`:93-117`) keep their `toggle_zero`/`cz`/`cswap` sequence but with a classical control.
   Note this *removes* the loan, so E's peak becomes `864 + step flag + 24 real = 889`
   **unless** the step flag is also classicalised (`local_flag_window.py:29`); do both.
5. `after_v3/blocks/v6/third_pivot_chart.py:115` (`flag`) and
   `after_c5/extractor_width/rolling_tail_early.py:41,53` (`self.current`) — same treatment.
   These are the C and A/B witnesses. `zero_xor` (`rolling_tail.py:34-54`) already ends in a
   single `ccx`/`init_and`; replace its target with a fresh wire + `hmr` + `free`, and its
   consumer `cswap`s become classical-conditioned.

### 6.3 How to see the plateau before and after (cheap, no full build)

Wrap the builder in a 12-line proxy that records `num_allocated_qubits` inside `alloc_qubits`
and `free`, plus a stack label, then run only:

* `after_c5/extractor_width/check_extractor_width.py` — must print
  `front.num_qubits == 889` now (`:114`) and **888** after `A/B-park`, while
  `b.num_allocated_qubits == 864` (`:149`) is unchanged;
* `after_v3/blocks/v6/check_third_pivot_chart.py` — `circuit.num_qubits == 889` now (`:183`),
  **888** after `C-park`, `RETAINED = 864` (`:25`) unchanged;
* `after_c5/converter_width/local_flag_defer/check_local_flags.py` — 889 now (`:113`),
  **888** after the E change, `RETAINED = 865` (`:40`) unchanged;
* the full build only at the end: `build_v7.py` asserts `circuit.num_qubits == 889` at `:59`
  and `static_T == 384003` at `:62`; both must be edited to the measured values, and
  `v7_pipeline.runtime_bindings()['maximum_Q_source_model']` (`:155`) updated.

The proxy is the only way to see *which* site is the current maximum; the `stage=` callback
is too coarse (see the engineering64 log, §3).

### 6.4 Sanity checks that the contract still holds

1. `Pipeline.assert_bindings()` (`v7_pipeline.py:83`) must still pass — it pins every module
   identity, including `P.Tail is First3.Tail`.
2. `emit_key_prefix` / `emit_key_closing` invariants: `check_key_boundary.py:49`
   (`len(boundary) == 865`), `:50` (`num_allocated == 865`), `:70` (`== 840` after closing).
3. `builder.num_allocated_qubits == 840` and `Z_POW == 0` at the end (`build_v7.py:53,59`).
4. The **behavioural** gate is the existing component simulators, which compare against
   independent classical oracles, not against the previous tape:
   `check_extractor_width.py:191-211` (masks + expected phase), `check_third_pivot_chart.py:194+`,
   `check_local_flags.py` (256 frozen fixtures, `FIXTURE_SHA` at `:39`).
   A classical-control rewrite is exactly the kind of change these catch: a mis-ordered
   `cz` payment shows up as a wrong phase on the probe shots.
5. Only then a full build + `verify_submission_dqi.py` on the default salt, then 16 salts.

### 6.5 Pass/fail

PASS: `Q == 888` on a real tape, `0` value / `0` phase errors on default + 16 salts,
`T_mean − 383,008 ≤ 863`, and (optionally) `≤ 600` for ≥ +0.0062 GM.
FAIL: any site still at 889 (Q unchanged → abandon), or any salt that fails an input the
`821bf8d1` baseline passes on the same seed.

---

## 7. Exact arithmetic used

```
cost ∝ Q² · T          (R is at the 1.19 floor for a 0-error tape)
Q = 889, T = 383,008.383203125
k=1 : (889/888)² = 790321/788544 = 1.00225352  →  T_max = 383,871.12  (ΔT_budget = +863.12)
k=2 : (889/887)² = 1.00451467                  →  T_max = 384,737.15  (+1,729.15)
k=12: (889/877)² = 790321/769129 = 1.02755325  →  T_max = 393,561.11  (+10,553.11)
k=49: (889/840)² = 1.12006944                  →  T_max = 428,995.56  (+45,987.56)
```
GM sensitivity: one qubit at 889 changes the DQI cost by −0.2251 %, i.e.
`27.31 × ln(1.0022535)/3 = +0.0205` points (matches `headroom.md` §1 and `dqi_plan.md` §5).

---

## 8. Scope of verification

| claim | how it was established |
|---|---|
| 49 = 24 + 1 + 24 | source read of the five allocation sites + `build_v7.py:53` (`== 840` at end) |
| five witnesses at 889 | four in-repo assertions (`check_extractor_width.py:114`, `check_key_boundary.py:62`, `check_third_pivot_chart.py:183`, `check_local_flags.py:113`) + `third_pivot_chart.py:99-100` docstring for site C |
| `num_qubits` = peak live | 13-line local kickmix builder test (no simulation); consistent with `dqi_plan.md` §8 shipped-file audit |
| 890 → 889 history | `night_c27/build_candidate.py:74` vs `build_v7.py:59`, and `rolling_tail_early.py:1-14,132` |
| the 24-bit scratch cannot be 23 | `fused_crt_synthesis.py:49-58,111-129`; `gf24_nested_norm.py:269,305`; `direct_carry_arithmetic.py:35-45` |
| ΔT of the park patches | **not measured.** Structural reasoning only (HMR + Cliffords + classically conditioned CCX). This is the one open number. |

Not verified: no `.kmb` was built, no `verify_submission_dqi.py` was run, no simulator was
invoked, no Kaggle job was created. Everything above is static analysis plus one trivial
13-line builder experiment.

## 9. Open questions worth one cheap experiment each

1. Does kickmix accept a **classical** control on `cswap` / `ccx` (`km.b` in the `control=`
   slot)? If yes, `D-park` is genuinely 0 T and ranks 1/2/3 collapse into one edit family.
   If no, each classical condition costs 3 classically-conditioned `cx`, still 0 T, but the
   code churn triples. A 20-line script answers it.
2. What is the *true* per-site peak? A builder proxy (§6.3) over the existing component
   checkers answers it in minutes, per component, with no full build.
3. Is there a 12-bit (not 24-bit) formulation of `Synthesis.emit_prefix`? `prefix_rows`
   (`fused_crt_synthesis.py:49-58`) is a trinomial multiply; the two new coefficients are the
   only reason `temporary` is 24 wide. If the product could be accumulated into `P` with a
   1-word rotate (the `x^2+x+kappa` structure), the scratch would be 12 and Q would drop to
   877 at D — but the peak would then be set by A/B/C/E at 889, so it is only interesting
   **after** the flags are gone.
