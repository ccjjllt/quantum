# DQI v13→v15 redesign — 2026-11-16 (part 2)

Goal: reach Q ≈ 864–866 at T ≈ 368 k by removing the 24-bit extra bank, per the plan (build the v12
source as a control, then alias the helper addition into the carry bank / dead syndrome registers).
Baseline to beat: `ccc2ab84…` (890 Q, 347,375,470,571.73 → GM 28.091).

## 0. Outcome

**The 24-bit extra bank is not an allocation artefact. It is the third 24-bit register that an
in-place field division provably requires, and Q = 889 is the algebraic floor of this decoder
architecture (888 with the 1-bit predicates classicalised). Q = 864–865 is unreachable from this
source at any T.** Exact blocking call site and proof: §3–§4. This matches the user's instruction to
report the blocker and stop.

The v12 control was reproduced end to end first (§2): the source builds `7cbe8ecf…` byte-exactly on
Kaggle CPU in 215 s and the unchanged official verifier scores it at 889 Q / 383,156.29 T /
360,733,280,431.94 with 0 value and 0 phase errors.

A calibration worth flagging (§6): gold 28.65386 is *equally* consistent with **Q = 890, T = 361.5 k
(−1.8 % T at unchanged Q)** as with Q = 865 at the v12 T. Given §4, the T-at-fixed-Q reading is the
only one that does not require new arithmetic.

## 1. Cost/GM reference table (exact, R = 1.19126046)

| Q | mean T | cost (1e9) | GM |
|---:|---:|---:|---:|
| 890 | 368,139 (today) | **347.38** | **28.091** |
| 890 | 361,500 (−1.8 %) | 341.11 | 28.262 |
| 890 | 356,000 (−3.3 %) | 335.92 | 28.407 |
| 880 | 368,139 | 339.61 | 28.303 |
| 870 | 368,139 | 331.94 | 28.520 |
| 866 | 368,139 | 328.89 | 28.608 |
| 865 | 368,139 | 328.13 | 28.630 |
| 864 | 368,139 | 327.38 | 28.652 |
| 865 | 383,156 (v12 T) | 341.52 | 28.251 |
| 889 | 383,156 (v12 as built) | 360.73 | 27.740 |
| 888 | 384,003 | 360.72 | 27.740 |
| 840 | 368,139 | 309.44 | 29.195 |

Two consequences that shaped the work below:

* **The v12 line cannot beat the v13 tape by fixing Q.** v12 builds at 889/383 k = 360.7e9 (27.74).
  Removing all 24 helper bits gives 865/383 k = 341.5e9 (28.25, +0.16). To merely *tie* the current
  347.4e9 the v12 line would have to reach Q ≤ 871. So a v12-based Q fix is worth +0.16 at best, and
  only if the whole 24 bits go.
* **Q = 864 at 368 k (28.652) needs the v13/v14 multiplier with the v15 allocation.** Neither half
  alone is enough.

## 2. Control build (step 1 of the plan)

`syed3000/vqcc-own-circuit-portfolio` no longer ships the source (as of 2026-11-15 12:54 it contains
only `dqi.kmb` = 486,989,273 bytes, i.e. the **890-qubit** file, `invsqrt.kmb`, and the 15 chemistry
loaders). I therefore republished the local Apache-2.0 tree as a private dataset
**`zhuating/qcc-dqi-source-v12`** (8.27 MB zip: `dqi_source/{build.sh, src/, LICENSE, NOTICE,
SHA256SUMS}`) and ran it standalone:

* kernel **`zhuating/qcc-dqi-v12build`**: locate the tree (it mounts unpacked at
  `/kaggle/input/qcc-dqi-source-v12`), copy it to `/tmp` (the mount is read-only and `build.sh` also
  needs the two pinned host files written into `src/pro1_controller_bundle/1_task/{official,
  verifiers}`), run `PY=python3.13 bash build.sh ENGINE VERIFIERS OUT`, check the SHA against
  `7cbe8ecf…`, then run the unchanged official verifier at the default salt.

**Control result (k8, PASS):**

```
[  247s] build exited 0 in 218s
BUILT dqi.kmb 7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9
[  248s] BUILT 455590024 7cbe8ecf... MATCH
[  377s] CONTROL verified 129s
CONTROL {'status': 'PASS', 'score': 360733280431.94055, 'num_qubits': 889,
         'toffoli_count': 383156.2908886719, 'value_errors': 0, 'phase_errors': 0,
         'circuit_sha256': '7cbe8ecf6f6e9743529b574f019504bb1712ce06fbb570c719ce9d9e2c914cd9'}
```

Build environment: CPython 3.13, numpy from the Kaggle image, 215 s wall, peak RSS 1.04 GB,
`python3.13 -B build_v7.py`. The published 360.73e9 reproduces to the digit. Every claim in §3–§5 is
read from the pinned source text with `file:line` citations, so the analysis does not depend on the
build — but the build proves the source I read is the source that produced the circuit.

## 3. The five helper sites, with the reason each needs its bits

| site | file:line | what the bits are | removable? |
|---|---|---|---|
| **A** extractor forward | `after_c5/extractor_width/direct_carry_arithmetic.py:37` (`_adjoint_consume`) | destination of the **in-place multiply `target ← conj(source)·target`** | **no** |
| **B** extractor return | `after_c5/arithmetic_t/gf24_nested_norm.py:263–272` (`emit_prefix`) and `:295–305` (`emit_closing`) | same in-place unit product | **no** |
| **C** third pivot | `after_v3/blocks/v5/inverse_retained_norm_deferred.py:80,87` (`_inverse_with_bank`) | in-place `source ← source·inverse_norm` in two 12-bit halves, **plus** a 24-bit caller-owned clean bank (the function refuses to run without it: *"source and clean storage bank must be disjoint"*, `:52`) | **no** |
| **D** CRT synthesis | `night_c27/synthesis/fused_crt_synthesis.py:111` (`emit_prefix`) | the two extra coefficient slots of an in-place linear map: `out = N + T`, `N` supplies `r` 12-bit words, the trinomial multiply needs `r+2` | **partly** — 12 of the 24 can take the *idle* `carry[12:]` (idle during synthesis, needed again only as `gauge_other`, `integrated_pipeline.py:218`) |
| **E** converter / outer | `after_c5/converter_width/local_flag_defer/local_flag_window.py:29,50,71` + `work/round2/milestone152/source/monic_forney.py:47` (+ `gauge_park_lender.py:36–43`) | converter working word + per-step flag | no |

The author states the plateau himself, `after_v3/blocks/v6/third_pivot_chart.py:99–100`:

> "At most 25 new quantum wires are live, including this new predicate; the production caller has 864
> retained wires at entry, hence Q889."

## 4. Why site A cannot be fixed — the hard blocker

```python
# after_c5/extractor_width/direct_carry_arithmetic.py:35
def _adjoint_consume(builder, source, target, delta):
    """target <- conjugate(source)*target, 99T; return its exact old mask."""
    temporary = builder.alloc_qubits(24)          # <-- the 24 bits
    builder.cx(source[12:], source[:12])
    A.product(builder, source, target, temporary, delta)   # temporary = source*target
    builder.cx(source[12:], source[:12])
    builder.swap(target, temporary)               # target <- product, temporary <- old target
    mask = builder.alloc_bits(24)
    builder.hmr(temporary, mask)                  # old target -> classical phase debt
    builder.free(temporary)
    return mask
```

Caller — the extractor slot loop, `after_v3/blocks/v6/first3_retained_norm_adapter.py:88–90`:

```python
divisions[i] = Arithmetic.divide_deferred(builder, current, carry)   # source = head, target = carry
builder.swap(current, carry)                                        # current <- v/u, carry <- u
```

so `source = words[i]` (a 24-bit view of two syndrome registers) and `target = carry` (the running
remainder). **Both are variable (superposed) 24-bit registers and the result must land in `target`.**

1. A general in-place multiply `t ← s·t` with both operands live cannot be done in `|t|` bits: every
   output bit depends on both operands, so no bit of `t` may be overwritten before all 24 output bits
   exist. A third 24-bit register is a lower bound.
2. 12 bits is not enough either. In the tower split `t=(t_lo,t_hi)`, `s=(s_lo,s_hi)`:
   `p_lo = t_lo s_lo ⊕ λ·t_hi s_hi`, `p_hi = t_lo s_hi ⊕ t_hi s_lo ⊕ t_hi s_hi` — both halves of `t`
   are needed by **both** output halves, so one 12-bit accumulator cannot hold one half while the
   other is finished. (The *next* step, `_consume_halves`, gets away with 12 bits only because its
   second operand is a **scalar** in the base field: multiplication by `1/Norm(u)` is 12 independent
   linear maps, not a field multiply. That is the whole trick of this decoder and it is already
   applied.)
3. Measured live set at site A: `840 (heads) + 24 (carry) + 1 (tail flag) = 865`, so
   `alloc_qubits(24)` lands on **889**. This is not an inference — it is the overflow dump of a real
   `set_max_qubits(888)` build (recorded in `experiments/frontier/20261115_upgrade/dqi_plan.md` §19):

   ```
   OVERFLOW at .../direct_carry_arithmetic.py:37  requested 24  allocated 865
     live 24 from .../after_c5/integration_v3/integrated_pipeline.py:163
     live  1 from .../after_c5/converter_width/tail_phase_defer/rolling_tail_deferred.py:57
   ```

   There is no free 24-bit word to borrow: `carry` is the operand, the heads are the data, the flag
   is one bit.
4. The "borrow the carry bank" form fails for a second, independent reason measured on the tape: in
   the 890-qubit tape the 24 carry bits are touched inside 62–72 % of the helper-window ops (see
   `RESULT.md` §3b), i.e. they are never idle while a helper is live.
5. Classicalising the flag (`push_condition`, previously measured at ΔT = −24) gives **888**, not 865.

**So the entire distance from 889 to 865 is one object: the cofactor register of
`v ← v/u`.** Every other saving is ≤ 1 qubit.

## 5. The only design that reaches ~865 (and why it is not a patch)

Move the division out of place:

```
today :  carry  ← carry / head_i                        (in-place; needs +24)
target :  head_{i-1}  ^=  q_i * head_i                  (disjoint target; needs +0)
          with q_i a 24-bit quotient word living in `carry`
```

The accumulate target is then a syndrome head that `q_i` and `head_i` do not touch, so no helper
exists and the allocation becomes **840 + 24 (quotient) + 0 = 864** (865 if the predicate stays
quantum). This is exactly the `N, D = D, N+P` structure the v12 code already uses for the 34
synthesis nodes (`integrated_pipeline.py:170–176`, `N`/`D` are lists of head views); the extractor is
the only remaining stage that is not in that form, because `divide_deferred` fuses three things —
the cofactor multiply, the scalar inverse-norm multiply, and the adjoint mask for phase repayment.

Cost of the change: re-derive the extractor's arithmetic and **all of its phase repayment**
(`restore_with_shared_norm`, the `DivisionRecord` masks, `rolling_tail_early.py`'s slot/return
protocol) in the multiply-accumulate form. That is the v15 arithmetic — weeks, not hours — and the
realistic outcome at v12's T is 341.5e9 (28.25); at v13's T it would be 328.1e9 (28.63).

## 6. Calibration: the gold point does not require Q = 864

| hypothesis | cost (1e9) | GM |
|---|---:|---:|
| Q = 864, T = 368,139 | 327.38 | 28.652 |
| Q = 865, T = 368,139 | 328.13 | 28.630 |
| Q = 890, T = 361,500 (−1.8 % T) | 341.11 | 28.262 |
| Q = 890, T = 356,000 (−3.3 % T) | 335.92 | 28.407 |
| Q = 880, T = 368,139 | 339.61 | 28.303 |

Gold 28.65386 needs a cost of 327.4e9. **A 1.8 % Toffoli cut at Q = 890 gets most of the way
(28.26); a 3.3 % cut passes 28.4.** Since §4 shows the Q axis is closed, the T axis at fixed Q is the
only remaining route to the frontier — and it is a much smaller ask than a new arithmetic
(uncompute is 50.5 % of T in the sibling decomposition, and the public MBU/cmerge pass only
converted 8 sites).

## 7. Receipts

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k8 | `zhuating/qcc-dqi-v12build` | reproduce `7cbe8ecf` from the v12 source on Kaggle CPU + official verify | **PASS**: sha MATCH, Q 889, T 383,156.29, 360.733e9, 0/0 (§2) |
| — | `zhuating/qcc-dqi-source-v12` | private Apache-2.0 dataset with the v12 source tree | ready, 8.27 MB |

## 8. Verdict

Stop pursuing Q < 888 on the v12 lineage. `direct_carry_arithmetic.py:35–43` (`_adjoint_consume`,
called from `first3_retained_norm_adapter.py:88`) is the hard blocker: the in-place cofactor multiply
`target ← conj(source)·target` needs a third 24-bit register, 24 bits is a lower bound, 12 bits is
provably insufficient, and the live set at that point is already 840 + 24 + 1. The 890-qubit tape is
likewise at its floor with 4×12 + 2 ancillas, all simultaneously live. **Both DQI lineages are at
their architectural minimum; the remaining frontier gap is T, not Q.**
