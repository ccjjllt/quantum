# invsqrt RESULT4: bounded Q=42 slot test — are the dead wires |0>?

Work in `experiments/frontier/20261116_push/invsqrt/`.
Kernel `jiyujia/qcc-v12-q42-slot-test` (Kaggle CPU, Python 3.13.18, numpy 2.1.3, competition
`kickmix.so`).  Source pin `invsqrt_source_zip` sha256 `7d9801ae…8254`; cap-17 first-loader
certificate (78 Toffolis, `work_peak 17`, search `v8_first_cap17_s0`).

## 0. Verdict

**The hypothesis is refuted.  None of the dead wires at the peak cuts is identically |0>.**
110 slots were tested over the **full domain (all 3,133,452 official inputs)**; every one is a real
non-constant function of x, with roughly half the inputs mapping it to 1 (`ones ≈ 1.56M/3.13M`) or
the familiar rare-flag distribution (`838,860 / 246,723 / 16,320`).  The **first failing input is
x = 1** for most slots (x = 3, 4, 5, 6, 11, 64 for the rest).

Therefore a dead wire cannot be freed with a free CX: it has to be *zeroed by a genuine identity*
`V = XOR(other live wires)` at that cut.  The 13-slot Q=42 plan cannot be paid for out of "free
zeroing", and the invsqrt width line closes here.

## 1. What was measured

Build: cap-17 first loader certificate, `tools/build_variant.py --Q 46`, all 13 shipped patches
(raw emission, 35,833 ops, 46 qubits).  Profile recomputed on that text:

```
peak occupied 46      peak live 41          (unchanged from RESULT2/RESULT3)
```

Peak-46 runs and their enclosing generator stages (`cuts` names, `instruction_cut`):

| stage | ops at 46 | runs | span |
|---|---:|---:|---|
| `raw_root_restored_with_paid_R` | 6,374 | 1 | [26427, 32800] |
| `divider_return` | 3,309 | 2 | [18268, 21581] |
| `coefficient_retired_for_divider` | 1,293 | 193 | [7188, 17364] |
| `seed_ready` | 444 | 83 | [6027, 6973] |
| `A_restored` | 378 | 1 | [25947, 26324] |
| `inverse_product_data` | 213 | 19 | [22147, 24147] |
| `first_table` / `second_a6_retired` | 117 / 117 | 17 / 17 | — |
| `coefficient_sources_restored` | 54 | 6 | [24562, 24999] |
| `first_coefficient` / `second_coefficient` | 9 / 9 | 1 / 1 | — |

**Slot definition** (exactly the question asked): at each stage's longest peak run `[a,b]`, the
*dirty-and-dead* set is `occ(i) & ~live(i)` intersected over **every** op of the run — i.e. wires
that are allocated but whose value is never read anywhere inside the run.  The first 10 (by wire
index) of each set were tested — 110 slots in total, covering the five blocking blocks named in
`RESULT3.md`.

## 2. Result per stage (full domain, seed 1)

```
stage                                slots tested   dead pool   identically 0
raw_root_restored_with_paid_R        10             14          0
divider_return                       10             15          0
coefficient_retired_for_divider      10             18          0     (product forward + divider)
seed_ready                           10             18          0
A_restored                           10             14          0
inverse_product_data                 10             20          0
first_table                          10             19          0
second_a6_retired                    10             26          0
coefficient_sources_restored         10             10          0
first_coefficient                    10             18          0     (coefficient_forward)
second_coefficient                   10             18          0
                                     ---            ---         ---
                                     110                        0
```

Representative rows (ones out of 3,133,452; first failing input = smallest x with the wire = 1):

```
first_coefficient (the first Q=42 blocker)
    q9  1,566,520  x=1     q10 1,566,181  x=5     q11 1,565,900  x=3
    q13 1,564,302  x=6     q18 1,552,633  x=2     q22   838,860  x=4
    q23   246,723  x=1     q24    16,320  x=64    q28 1,571,076  x=1   q30 1,565,218  x=1

coefficient_retired_for_divider (product forward / divider)
    q0 1,567,321 x=1   q1 1,566,515 x=1   q2 1,567,391 x=1   q3 1,566,653 x=1
    q4 1,566,910 x=1   q11 1,565,900 x=3  q13 1,564,302 x=6  q21 1,565,420 x=1
    q26 1,565,469 x=11 q27 1,565,749 x=5

divider_return
    q0..q6, q14, q21, q30: all ≈1.56M ones, first failing x = 1 (q14 x=3)
```

The three rare counts are the exponent-code flags and they are **bit-identical to the ones measured
on the shipped 44Q file** (`q22` 838,860 / `q23` 246,723 / `q24` 16,320 of 3,133,452 — see
`RESULT.md` §6.3).  So the v12 body and `f2cdab0b` share the same flag semantics, and the same
"rare but not zero" trap applies: a sampled probe reads them as dead, the full domain does not.

Note on the `ones_seed2` column in `evidence/slot_test.json`: seed 2 was run **only for slots that
came out zero**, and there were none, so that column is an artefact and reads 0.  The single-seed
full-domain count is the measurement.

## 3. Why this closes the line

* Freeing a wire requires it to be `|0>` (the emitter's `init_and` convention is HMR + CX/CX/CCX on
  a clean wire; an HMR of a nonzero basis value leaves an uncorrectable random phase `(-1)^{V·r}`).
* **0 of 110** dead slots qualify, over the full input domain, at every peak stage — including
  exactly the wires at the five blocking blocks of `RESULT3.md`.
* Hence each of the 13 Q=42 slots needs a real identity, and `RESULT3.md` §5 shows the identity
  library (`hret_s15k7a_s15.json`, `v9_form_e2.json`, `w2core_e2.py`) is fully spent at those sites,
  with `tools/minand_sat.py` unpublished.  The cap-17 search recovery (~20 T-eq) addresses the
  Toffoli budget, not the 13 slots.

## 4. Verification scope

* **Measured**: 110 slot values over all 3,133,452 official inputs with the competition simulator
  (prefix simulation at each block's peak run, batches of 65,536).  Static live/dirty profile on the
  raw emitted text (35,833 ops).  Cap-17 loader certificate produced by the tree's own search.
* **Not run**: no Q≤42 circuit exists, so the official `verify_submission_invsqrt.py` was **not**
  run for any new candidate.  Nothing submitted.
* **Already on record** (from `RESULT3.md`): the cap-17-loader 46Q body passes the exact full-domain
  prover (`PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`, 3,133,452 inputs,
  1,309 HMR variables, circuit `6646f5e0…01d1`).

## 5. Final state of the invsqrt task

| item | value | status |
|---|---|---|
| shipped best | `f2cdab0b` 44Q, 75,006.38 | full-shot official PASS (default salt), `RESULT.md` |
| Q=44 floor of that file | 5,790 ops need all 44 wires | proven, `RESULT.md` §4 |
| v12 42Q attempt | 13 wire-slots, all nonzero on the full domain | **refuted**, this file |
| cap-17 loader certificate | 80 Toffolis, work_peak 17, exact proof | **verified**, `RESULT3.md` §2 |

**invsqrt is closed.**  `RESULT.md`, `RESULT2.md`, `RESULT3.md`, `RESULT4.md` and the kernels listed
in them carry the full evidence; no further compute on this task.
