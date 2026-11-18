# DQI — normalized divstep EEA generator: status after the verification round (2026-11-18)

Line `dqi_gen` (account `zhuating`). Goal: a DQI decoder generator at least 1.6x cheaper than the
official reference generator, verified end-to-end by the unmodified official verifier.

**Bottom line: the EEA is finished and validated, the register contract is verified by the official
verifier, the phase contract is not met.** Official verifier, 25,600 shots, `(m,n,b) = (15,6,4)`:

| circuit | Q | static T | value_errors | phase_errors | verdict |
|---|---:|---:|---:|---:|---|
| official reference generator | 140 | 33,258 | 0 / 25,600 | 0 / 25,600 | **PASS**, score 936,905,204.03 |
| `dqi_fast.py` (this line) | 213 | 8,068 | **0 / 25,600** | 12,852 / 25,600 | FAIL, eps_plus = 0.543 |

So: 4.1x fewer Toffolis, every register restored, **but 50.2 % of shots get the wrong global phase**.
The phase damage is localised and explained in §4; it is not a rotation-, carry- or EEA-depth problem.
Nothing is submitted, no score is claimed.

---

## 0. The parameter sets in the brief are not admissible

`verifiers/dqi/verify_submission_dqi.py::_validate_inputs` requires `2 <= n < m <= 2**degree - 1`:

| requested | admissible? | why |
|---|---|---|
| `m=63, n=6, degree=4` | **no** | needs `m <= 15` |
| `m=511, n=10, degree=8` | **no** | needs `m <= 255` |
| `m=63, n=6, degree=6`, `m=255, n=10, degree=8`, `m=4095, n=70, degree=12` | yes | used here |

The verifier refuses to start at `(63,6,4)`, so that run cannot be evidence for anything.

## 1. Reference baseline (official generator imported unmodified)

| (m,n,b) | Q | static T | EEA (fwd+rev) | Chien/Forney | rest | source |
|---|---:|---:|---:|---:|---:|---|
| (15,6,4) | 140 | **33,258** | 32,436 (97.5 %) | 562 | 260 | local build |
| (63,6,6) | 180 | **55,879** | 50,268 (90 %) | 5,271 | 340 | local build |
| (255,10,8) | 296 | **146,564** | 111,444 (76 %) | 34,076 | 1,044 | kernel |
| (511,10,9) | 328 | **220,888** | 139,552 (63 %) | 80,184 | 1,152 | local build |

Official verifier reading at `(15,6,4)` (kernel `zhuating/qcc-dqi-gen-probe` v6, 25,600 shots, 2 workers):

```json
{"status": "PASS", "score": 936905204.0327171, "value_errors": 0, "phase_errors": 0,
 "toffoli_count": 33229.737890625, "num_qubits": 140, "verified_shots": 25600,
 "effective_error_rate": 0.0034597371721321658, "empirical_error_rate": 0.0}
```

The reference runs `n_iters = 3(n+1)+9` synchronized EEA iterations (30 at n=6, 222 at n=70), each
sweeping all `m = n+3` slots: that is why the EEA is 97.5 % of its T at small `n`.
Chien/Forney costs 37 T/position at b=4 and 157 T/position at b=9, of which
`init_gf2_inverse_with_scaffold` is 18 T / 129 T (the 315 T in the brief is the b=12 value).

## 2. The normalized divstep EEA (validated)

`work/twin.py` implements the recurrence in `dqi_fast.py::_divstep_eea` classically; it is compared
against a textbook monic full-quotient EEA decoder on random instances for `(15,6,4)`, `(63,6,63)`
and `(255,10,8)`, 4000 each, error weight uniform in `0..t`: **0 failures**.

One step cancels exactly one leading coefficient with the scalar quotient `c = lc(A)/lc(B)` and
monomial shift `k = deg A - deg B`; `k` costs nothing because the slot layout is relative
(`slot j` = coefficient of `x**(p+1-j)`), so the subtraction is slot-aligned and lowering a degree
counter is a cyclic rotation of qubit ids (0 Toffoli). Slot 0 is permanently dead (a coefficient
above the degree), so the value that wraps is always 0. `lc(B) = 0` is repaired by one slot shift;
the two lattice rows are exchanged when `deg A < deg B`.

Steps actually used (max over the trials), against the reference's `3(n+1)+9`:

| n | subs | shifts | swaps | **steps** | emitted `n_iter` | reference iterations |
|---|---:|---:|---:|---:|---:|---:|
| 6 | 7 | 3 | 4 | **8** | 15 | 30 |
| 10 | 11 | 5 | 6 | **12** | 23 | 42 |

The emitted circuit was compared **state-for-state** with the twin after every step
(`n_iter = 1..9`, `(15,6,4)`): exact match of all four arrays and both degree counters, and the final
`(omega, sigma)` yields exactly the twin's per-position Forney values (`ej = {3: 5}` for a single
error at position 3 with value 5). Chien/Forney costs 0 Toffoli for the evaluations (Horner with
classical constant multiplies = Clifford), b T for the zero test, and one b=4 division (27 T) per
position — there is no per-position `init_gf2_inverse_with_scaffold` (18 T at b=4, 315 T at b=12).

## 3. Measured cost of the current generator, and why Q² matters

| (m,n,b) | Q | static T | T vs ref | Q² vs ref | net cost |
|---|---:|---:|---:|---:|---:|
| (15,6,4) | 213 | 8,068 | 4.12x cheaper | 2.31x worse | 0.56 → 1.78x cheaper |
| (63,6,6) | 317 | 23,742 | 2.35x cheaper | 3.10x worse | 1.32 → **worse** |
| (255,10,8) | 587 | 105,602 | 1.39x cheaper | 3.93x worse | 2.83 → **worse** |

All three figures are the same generator as measured in the kernel (`probe_results.json`, `static`).
The layout uses 4 full-size arrays (polynomial + cofactor, `2*(n+2)` words each), which is what
inflates Q; the reference packs `sigma`/`omega` into the remainder array and stays at
`2*Q_syndrome + ~50`. Consequence: **a T win alone is not enough at small n** — Q² must be held.

## 4. Why there is no PASS: the phase path, measured and localised

Local and kernel evidence agree: `value_errors = 0` (all syndromes restored, every ancilla back to
|0>, including after discarding the whole decoder workspace), `phase_errors ≈ 50 %`.

Minimal circuits with definite computational-basis inputs and the phase read through
`read_phase_flipped_across_shots` (16 shots each):

| gadget, as used | phase flips / 16 |
|---|---|
| `flip_if_equal(reg, 0, f)` with `reg ≠ 0` | **7** |
| `flip_if_equal(reg, 0, f)` with `reg = 0` | 0 |
| `flip_if_less_than(a, 3, f)`, `a = 1` (true) | **12** |
| `flip_if_less_than(a, 3, f)`, `a = 6` (false) | 0 |
| `flip_if_less_than(a, b, f)` two registers, true | **4** |
| `flip_if_greater_than(p, 2, f)`, true | **4** |
| `init_gf2_div(x,y)` then `reset` of the target, `(5,3)` | **12** |
| `init_gf2_div(x,y)` then `del_gf2_div(x,y,target)` | **0** |
| `init_gf2_div_with_scaffold` + `del_..._with_scaffold`, operand changed in between | random |
| `init_and` + `reset` of the target | 0 |
| plain `R` (reset) of a definite basis qubit | 0 |

**Rule that follows (this answers the "T halves for free" question):** every kickmix gadget whose
result is a *qubit flag* (`flip_if_equal`, `flip_if_less_than`, `flip_if_greater_than`,
`init_gf2_div`, `*_with_scaffold`) is measurement-based, and it leaks a phase that depends on its
internal `HMR` outcomes unless the **matching uncompute gadget is applied with unchanged operands**
(`del_*`, or the same `flip_if_*` again). `reset`ting such a flag — the cheap way to reuse it next
step — is exactly what leaks. Hence:

* the phase damage is **not** caused by discarding the workspace (plain `R` on data qubits is
  phase-clean, and the 25,600-shot run has `value_errors = 0` with the workspace discarded);
* it **is** caused by resetting the per-step decision flags, which are gadget outputs
  (`sw`, `zb`, `run` in `_divstep_eea`);
* therefore the 2x saving from "no reverse EEA" is **not available**: the flags must be uncomputed
  by their own gadgets, which requires the operands to be restored first — i.e. the reference's
  adjoint-pass discipline. I do not claim any T halving.

Concretely (measured on a single-gadget circuit): a comparison costs 4-5 T, and it must be paid
**twice** (compute + uncompute) once the operands are restored. In the EEA that is
`2 * 3 comparisons + 2 * 2 ANDs` per step, ≈ 30-40 T per step at b=4 — affordable; the price is the
reverse pass over the arrays (~2x T), not the flags.

The other two hazards, both hit in the first version:

* `init_gf2_div` is **not** standalone: it must be paired with `del_gf2_div` on the *same* operands;
  my first version divided by `RA[1]` and then modified `RA[1]` in the same step (random phases).
* `flip_if_greater_than` is not usable as a data-dependent predicate at all; `flip_if_less_than`
  plus one `X` gives the same test cleanly.

## 5. Does the divstep scale? Per-step structure versus the shipped tape

Shipped tape `575b043f` (n=70, b=12), from `zhuating/qcc-dqi-mult-census`:
3,339 multiply blocks in the forward EEA, 3,682 in the reverse, 35 steps per pass, i.e.
**~96 word-multiplies per step = 3 polynomial arrays x ~32 words**.

This generator at n=70: **4 arrays x 72 words = 288 word-multiplies per step**, `n_iter = 2n+3 = 143`
steps per pass (~71 doing real work). => **~41,000 word-multiplies per pass against ~3,339**: 12x
more multiply traffic, i.e. ~1.7-2.6M T at 42-63 T per multiply. As implemented, the normalized
divstep is **much worse** than the shipped circuit at `(4095,70,12)`; it only wins against the
*reference generator*, and only in T.

Required before the 253k-265k projection can be believed (none of it verified):

1. **active-window multiply** instead of full width (average ~35 words, not 72) → 2x;
2. **two arrays per step** (`A` and its cofactor `U`; `B`, `V` are read-only inside a division
   round) → 2x;
3. **~n+1 steps** instead of `2n+3`;
4. **no division per step**: keep `1/lc(B)` in a register refreshed once per round (378 T at b=12
   per step is 54k T/pass on its own);
5. **Chien/Forney at ~11 T/position** (the shipped `CCZ` mask contraction) instead of ~40 T at b=12;
6. **Q ≈ 840-890** by packing `sigma`/`omega` into the remainder slots (`Q = 3400` would lose more
   than the T win buys, as the b=8 row in §3 shows).

With 1-3 a single pass lands near 120-130k T, i.e. ~250k with a reverse pass. That is the only route
to 253k I can defend today, and it is unverified.

## 6. Files and commands

```
dqi_fast.py           generator (normalized divstep EEA + Chien/Forney; phase path broken, see 4)
work/twin.py          validated classical twin of the recurrence + textbook EEA cross-check
work/check_local.py   16-shot contract check using the verifier's own sampling/validation helpers
work/measure.py       reference region split (EEA / Chien / rest) by rebuild-diff
kprobe/main.py        Kaggle CPU probe (static counts + official verifier, 25,600 shots)
kprobe_out/           fetched kernel output, incl. probe_results.json and the kernel log
probe_results.json    copy of the measured JSON (see 7)
../../../../artifacts/dqi_gen/fast_15_6_4.kmb   candidate circuit (860 KB)
../../../../artifacts/dqi_gen/ref_15_6_4.kmb    reference circuit, same parameters (2.9 MB)
```

```
.venv/bin/python experiments/frontier/20261118_push/dqi_gen/work/measure.py
.venv/bin/python experiments/frontier/20261118_push/dqi_gen/work/check_local.py
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_gen/kprobe --account zhuating
python scripts/kgpu.py fetch --kernel zhuating/qcc-dqi-gen-probe --account zhuating --out ...
```

## 7. Official verifier readings at (15,6,4), 25,600 shots, unmodified verifier

Reference (baseline):

```json
{"status": "PASS", "score": 936905204.0327171, "m": 15, "n": 6, "degree": 4, "r": 6,
 "verified_shots": 25600, "value_errors": 0, "phase_errors": 0,
 "empirical_error_rate": 0.0, "effective_error_rate": 0.0034597371721321658,
 "toffoli_count": 33229.737890625, "max_toffoli_count": 33258, "num_qubits": 140,
 "num_bits": 66,
 "circuit_sha256": "a3c66b8f0be94cb423f79fe74ce025fe8b0f8d8ad192baf713dea28acacd2258"}
```

`dqi_fast.py` candidate:

```json
{"status": "FAIL",
 "error": "Effective error rate 0.5428 >= 1/16 at log2_delta=-128.0 (empirical=0.5020,
           value_errors=0/25600, phase_errors=12852/25600)"}
```

`(63,6,6)` candidate (same defect, same rate):

```json
{"status": "FAIL",
 "error": "Effective error rate 0.5404 >= 1/16 at log2_delta=-128.0 (empirical=0.4996,
           value_errors=0/25600, phase_errors=12790/25600)"}
```

Interpretation: the value half of the contract is **proven end-to-end by the official verifier**
(0/25,600 at two parameter sets, with the workspace discarded by resets). The phase half fails at
~50 %, which matches "one 1-bit decision per step is left in a random phase" — the flags are reset
instead of being uncomputed by the gadget that computed them.

## 8. Honest status and next concrete step

* normalized divstep EEA: **done**, classically exact on 12,000 instances, 8-12 steps at n=6..10.
* register contract: **verified by the official verifier**, 0 value errors over 25,600 shots.
* phase contract: **not met**, root cause localised to resetting gadget-produced flags.
* next step (small, well-defined): keep the 3 per-step flags in per-step qubits (3 x `n_iter` extra
  qubits, or the copy-and-uncompute pattern) and add the reverse EEA pass; then re-run the verifier at
  `(15,6,4)`. Expected: T doubles to ~16k, Q rises to ~230-260, which at `(15,6,4)` is **not** better
  than the reference's 33.2k at Q=140 — the tiny-parameter deliverable therefore also needs the Q
  reduction of §5.6, not just the phase fix.
* no submission, `submissions/` untouched, `data/competition/` untouched, verifier never modified.
