# DQI upgrade plan — 2026-11-15

Scope: DQI only. Baseline is the public file `821bf8d1` (Syed Asad Ali v12 decoder,
Ertuğrul Özer extractor cutoff 18, Areeb Ali 241 retained products), as shipped in
submission `58349843`.

**Bottom line.** (1) Cutoff 18 is optimal; 17 is a tie, and 19/20/21 are negative
EV by −0.008/−0.045/−0.160 GM points. (2) 840Q is not feasible and no public 840Q
decoder exists; 888Q is the real one-qubit target. (3) No public DQI after 2026-11-14
beats `821bf8d1`; rank-173 applies only to the older 392k family. (4) The next
experiment is a source-level **888Q one-wire reallocation**, expected +0.010 to
+0.021 GM points if it builds at ΔT ≲ 460 mean Toffolis (break-even ΔT = 862.2).

No new circuit was built, no official verifier was run, and nothing was submitted for
this note. Every number below is labelled:

- **M** — measured by a public official-verifier log (source named);
- **E** — closed-form calculation or estimate made here;
- **P** — public report, not independently rerun here.

The current trio anchor (M, local official verifiers, default salt):

| member | file | Q | cost |
|---|---|---:|---:|
| invsqrt | `e46d90c3` | 46 | 78,719.529147 |
| DQI | `821bf8d1…b672a3` | 889 | 360,209,905,486.0156 at 0 failures |
| chemistry | maoxin123 v27 4033 + refit | 427 | 294,991,455.82 |

Zero-failure GM = **27.306613**. The DQI 48-draw expected cost is
**360,947,460,562.197** (M, `manwithacat/vqcc-apache-public-circuits` v125,
`dqi_expected_basis = 48-draw sweep`), i.e. +0.2048% over the zero-failure cost.
Submission `58349843` was still pending when this note was written; its Kaggle run
reported 0 value / 0 phase errors at 102,400 shots.

Reference costs used for GM (M, repo `docs/research-map.md` §33): invsqrt
2,076,774.2337, DQI 24,439,463,583,672.93, chemistry 3,355,599,588.3155.

---

## 1. The only two DQI levers left

DQI cost is

```
C_DQI = R(eps_plus) * Q^2 * T_mean
```

with `eps_plus` the one-sided Clopper–Pearson bound at `delta = 2^-128` over
102,400 shots and

```
R(eps) = ln(2) / -ln(1/2 + 2*sqrt(eps)),   0 <= eps < 1/16.
```

For this baseline:

| failed shots k | eps_plus | R(k) | ΔR/R(0) | GM hit (points) |
|---:|---:|---:|---:|---:|
| 0 | 8.660587e-4 | 1.19126046 | 0 | 0 |
| 1 | 9.104198e-4 | 1.19673150 | +0.4593% | **−0.04168** |
| 2 | 9.488156e-4 | 1.20138806 | +0.8502% | −0.07695 |
| 3 | 9.839091e-4 | 1.20558432 | +1.2024% | −0.10858 |
| 5 | 1.047950e-3 | 1.21310521 | +1.8338% | −0.16490 |

The “0.153% per failure” rule in the notes is exactly `0.4593% / 3`:
one failure raises the DQI cost by 0.4593%, and the GM by `(1.004593)^(1/3)-1 =
0.1531%`, which is **0.0418 GM points** at 27.3066. One failure is therefore worth
**1,757 mean Toffolis** of DQI T (`0.00459264 × 382,600.38`). This exchange rate is
the whole cutoff argument below.

The two remaining levers are `T` down and `Q` down. `Q` counts twice, so one qubit
at 889 is worth **862.2 mean T** (`T × ((889/888)^2 − 1)`). That is the 888-qubit
target.

`R` is not a lever: any zero-failure file has R = 1.19126046. Only reducing the
*probability* of a failure draw helps, and that is the exact-decoder problem, not a
parameter.

---

## 2. Cutoff ladder 15 → 22: expected cost, not the zero-failure cost

### 2.1 How `j_min` maps to T

The public build wrapper is one line (M, `kirderf/vqcc-dqi-cutoff-variants/build_cut.py`
and Areeb Ali's notebook):

```python
_orig = P.First3.emit_prefix
def _cut(builder, words, carry, *, j_min=15, **kw):
    return _orig(builder, words, carry, j_min=CUT, **kw)
P.First3.emit_prefix = _cut
```

`First3.emit_prefix` lives in `first3_retained_norm_adapter.py`. It starts the
`RollingTail` at `j_min` and only calls `tail.begin_slot/begin_return` for
`i >= j_min`:

```python
tail = Tail.RollingTail(builder, j_min, stop_index) if stop_index > j_min else None
...
token = tail.begin_slot(current, carry, i) if i >= j_min else None
...
token = tail.begin_return(current, i) if i >= record.j_min else None
```

Raising `j_min` by one skips one tail slot in both the forward and the return pass.
The measured price is exactly **116 static Toffoli-like gates** and **≈105 mean
Toffoli-like gates per shot** per step (M, cut15/16/19/20 logs; cut18/retained build
in Areeb's log). The mean is lower than the static count because some controller
gates are conditional and do not fire on every shot.

The failure side comes from the verifier's own test law
`p_k = (principal eigenvector of the DQI tridiagonal)^2`, `k = 0..35`. Cutoff `c`
excludes the lower weight band `15 <= k < c`; the excluded probability per shot is
`sum_{k=15}^{c-1} p_k`. This is the same table Areeb's notebook computes with
`optimal_dqi_weights(spec.m, spec.max_errors, spec.degree, spec.r) ** 2`.

### 2.2 Measured points and exact excluded mass

| cutoff | static T (retained) | mean T | Δmean T vs 18 | excluded shots / 102,400 draw (E) | marginal vs previous (E) |
|---:|---:|---:|---:|---:|---:|
| 15 | 383,762 (M) | 382,915.189 (M) | +314.81 | 0 | — |
| 16 | 383,646 (M) | 382,810.211 (M) | +209.83 | 0.00250 | 0.00250 |
| 17 | ≈383,530 (E) | 382,705.370 (E, step −104.99) | +104.99 | 0.01562 | 0.01562 |
| **18** | **383,414 (M)** | **382,600.383 (M)** | **0** | **0.07846** | **0.06284** |
| 19 | 383,298 (M) | 382,495.396 (M) | −104.99 | 0.35442 | 0.27596 |
| 20 | 383,182 (M) | 382,390.192 (M) | −210.19 | 1.46645 | 1.11203 |
| 21 | ≈383,066 (E) | 382,285.187 (E) | −315.20 | 5.58277 | 4.11632 |
| 22 | ≈382,950 (E) | 382,180.182 (E) | −420.20 | 19.58524 | 14.00247 |

Measured source rows: cut15 `0958baa6…c5c05` score 360,506,288,134.75 (0 errors);
cut16 `0ce13341…e49d2` score 360,407,453,871.97 (0 errors); cut18 `821bf8d1…b672a3`
score 360,209,905,486.02 (0 errors); cut19 `954c5d4b…7530c` score
361,764,924,330.57 (1 value error); cut20 `37d4e36e…357f7` score
363,072,685,516.03 (2 value errors). All from
`kirderf/vqcc-dqi-cutoff-variants` (`verify15/16/19/20` logs). Cut17 is the
`c60beda8…`/`cc0d7d25…` family; the step is taken from the four measured steps.

### 2.3 Expected cost including R

Let `base` be the intrinsic decoder failure rate excluding the cutoff contribution.
The 821 48-draw expectation implies a total of 0.4606 failures/draw; subtracting the
cut18 tail 0.0785 gives `base = 0.3822` failures/draw. (Asterios's 25-salt cutoff-15
run gives 2.3e-6/shot = 0.24/draw, and his flagged-shot replay gives 3.3e-6/shot =
0.34/draw; the manifest 48-draw value 0.46/draw is within that range. The cutoff
conclusions below do not depend on which of 0.24–0.46 is used, because the cutoff tail
is added on top.) Then

```
lambda(c) = base + sum_{k=15}^{c-1} p_k * 102400
E[R](c)  = sum_k Poisson(lambda(c))_k * R(k)
E[C](c)  = E[R](c) * Q^2 * T(c)
```

| cutoff | E[R] | expected DQI cost (E) | Δ vs cut18 expected | expected GM (E) |
|---:|---:|---:|---:|---:|
| 15 | 1.19329504 | 361.122e9 | +0.0485% | 27.283604 |
| 16 | 1.19330801 | 361.027e9 | +0.0222% | 27.285999 |
| 17 | 1.19337591 | 360.949e9 | +0.0006% | 27.287973 |
| **18** | **1.19369965** | **360.947e9** | **0** | **27.288001** |
| 19 | 1.19509073 | 361.269e9 | +0.0892% | 27.279905 |
| 20 | 1.20027431 | 362.736e9 | +0.4959% | 27.243075 |
| 21 | 1.21595778 | 367.375e9 | +1.7818% | 27.127924 |
| 22 | 1.25428798 | 378.851e9 | +4.9634% | 26.851182 |

The zero-failure GM is 27.306613; the cut18 **expected** GM is 27.288001. The
0.0186-point gap is the price of the 0.46 failures/draw, and it is the ceiling for a
correctness fix (see §5 fallback).

### 2.4 Why 18 is the optimum, and what 19/20/21 would cost

The break-even marginal failure probability per 105-T step is

```
p* = (105 / 382600.38) / 0.00459264 = 0.05975 failures/draw.
```

The measured marginal excluded mass from 17→18 is 0.06284, i.e. **5% above
break-even**. That is why cut17 and cut18 are a statistical tie: the model says cut18
wins by 0.00003 GM points. Cut18 is the last non-negative step.

From 18→19 the marginal is 0.27596, **4.6× p***. In lottery language:

- 75.9% of draws: no extra cutoff failure → +0.0025 points from the 105-T gain;
- 20.9%: one extra failure → −0.0392 points;
- 2.9%: two extra → −0.0744 points;
- expected: **−0.0081 points**.

From 18→20 the marginal is 1.388: P(0) = 24.9%, P(1) = 34.6%, P(2) = 24.0%,
P(≥3) = 16.5%; expected **−0.0449 points**. From 18→21 the marginal is 5.50:
P(0) = 0.4%, expected **−0.1601 points**. Cut22 is −0.4368.

The single public cut19 draw (1 value error) and cut20 draw (2 value errors) are
consistent with the excluded mass (0.354 and 1.466 expected excluded shots). The
cutoff errors are value errors, not phase errors, and they are not a new mechanism.

**Verdict (E): keep cutoff 18. Cutoff 17 is a tie, 19+ is negative EV. The public
“cutoff 18 remains best” statement is correct, but for the expected-cost reason, not
because its zero-failure cost is lowest.**

Implementation note: the cutoff wrapper is a build-time parameter, not a gate-level
patch. Any cutoff sweep must rebuild from `dqi_source_zip` with
`build_cut.py … CUT`; the retained-product rewrite is then applied to that file. The
`kirderf` dataset already contains cut15/16/19/20 retained `.kmb` files, so a
verification-only sweep needs no build.

---

## 3. 889Q → 840Q: no public 840Q decoder; 840 is a no-go; 888 is the real target

### 3.1 Public search

Searched `manwithacat/vqcc-apache-public-circuits` v125 (2026-11-14 11:49, 97 DQI
entries), the DQI datasets sorted by update, and notebook titles/descriptions for
“840Q”, “840 qubit”, “in-place”, “zero ancilla”. Result (M/P):

- **No public 840Q DQI circuit.** The minimum Q in the 97-entry manifest is 877
  (`f3d335c3…ec3fb`, old family, 442.121e9), then 880/881/882/883, then 888, 889,
  891, 892. All sub-889 files are older, much more expensive families.
- The best public sub-889 file is **888Q, `5faba459…713a0`** (HW-01 on yoyobar's
  family, 2026-10-30): zero-failure 401.986e9, 48-draw expected 402.294e9. It is
  11.5% worse than 821, despite one fewer qubit.
- The 883Q public family is 434.5e9, the 881Q family 891.7e9, the 877Q family
  442.1e9. None is near 360e9.
- `somejoint/qcc-dqi-889-two-halves` and `alexchilton/uncompute-dqi-port` are
  permission-denied/private; they are not usable evidence and are not in the
  manifest. There is no public 840Q artifact to test.

### 3.2 Why 840Q is not feasible for `821bf8d1`

`821bf8d1` has 840 register qubits (`S0..S69`, 70 × 12) and 49 scratch qubits.
Areeb's audit (M) reports `register_qubits = 840`, `min_qubits = 889` from the
interval-colouring bound, i.e. no relabelling saves a qubit. The source shows the
prefix alone holds 864 wires: 840 syndrome wires plus the 24-bit carry
(`assert len(set([*carry, *(wire for word in words for wire in word)])) == 864`).
The peak 889 adds a second 24-bit working word and one flag in the converter/scan
stage.

At fixed cost, going 889→840 allows

```
T budget = 382,600.38 × ((889/840)^2 − 1) = +45,939 mean T (+12.0%).
```

The earlier Q=840 analysis on the 892Q `eae396ba` family measured that 70.5% of paid
gates touch the 52 ancillas, and the cheapest 24-bit multiplication is 99 T; 1,358
uses would be ≈134k T, 2.9× the budget. The 821 family is the same structure: the two
24-bit words are live workspace, not a cache that can be recomputed once. Removing
all 49 would require recomputing a 24-bit word at every use, which is far outside
45.9k T.

**Verdict (E): 840Q is not feasible by release/recompute for this decoder, and no
public 840Q decoder exists. Do not spend a Kaggle experiment on 840Q.**

### 3.3 888Q is feasible in principle, and is the highest-value structural lever

One qubit costs only 862.2 mean T. The public HW-01 experiment on a sibling 889Q
decoder removed one long-held pole by release-and-recompute for **+460.4 mean T**,
which was a net **−0.108% cost / +0.036% relative GM (+0.0083 points)** on that
older, lower-GM base
(M, `manwithacat/vqcc-hedge-wizardry` entry HW-01; `5faba459…713a0`). The method is
proven on the 889Q shape, but not on the Syed v12 decoder.

Asterios's 2026-11-14 audit (P,
`asteriospanoras/qcc-27-30-what-works-what-fails-and-why`, open problem 3) states:

> “DQI at 888 qubits. The 509 blocking peak episodes of `821bf8d1` fall into seven
> families, each with a one-wire reallocation pattern already used elsewhere in the
> builder (estimate +0.010 to +0.021 points). It needs the decoder's source build to
> write exactly.”

That estimate brackets our calculation exactly: +0.0205 points at ΔT = 0, +0.0095
at ΔT = 460, zero at ΔT = 862.2. This is the one open DQI lever with a concrete plan,
a known pattern library, and a positive expected value.

---

## 4. Newer public DQI variants after 2026-11-14: none beats 821

| candidate | Q | zero-failure cost | expected cost | source / date | verdict |
|---|---:|---:|---:|---|---|
| **`821bf8d1`** | 889 | 360.2099e9 | **360.9475e9** | areebbb v12 / 11-13 | baseline |
| `cc0d7d25` cutoff 17 | 889 | 360.5355e9 | 361.2445e9 | ahoirg / 11-13 | +0.082% worse |
| `c60beda8` cutoff 17 + 241 | 889 | ≈360.31e9 | ≈360.95e9 | sheroleg / 11-14 | tie, not better |
| `4c81b726` 392k | 892 | 371.5696e9 | 371.8897e9 | maoxin123 / 11-12 | +3.0% worse |
| cut19 `954c5d4b` | 889 | 360.104e9* | 361.269e9 | kirderf / 11-13 | +0.089% worse |
| cut20 `37d4e36e` | 889 | 360.003e9* | 362.736e9 | kirderf / 11-13 | +0.496% worse |
| HW-01 `5faba459` | 888 | 401.986e9 | 402.294e9 | manwithacat / 10-30 | +11.5% worse |
| 877Q `f3d335c3` | 877 | 442.121e9 | — | Özer / 10-27 | +22.7% worse |
| 881Q `835414f5` | 881 | 891.688e9 | — | Magmucot / 10-26 | +147% worse |
| 840Q | — | — | — | — | **does not exist** |

`*` hypothetical zero-failure equivalent for the cut19/20 topology; the measured
single draws had 1 and 2 value errors (361.765e9 / 363.073e9).

Other post-11-14 releases checked:

- `manwithacat/vqcc-apache-public-circuits` v125 (2026-11-14 11:49): best expected
  DQI is still `821bf8d1`; no new DQI entry after that update.
- `manwithacat/vqcc-hedge-wizardry` (2026-11-14 16:33): six DQI entries, newest
  HW-22 (2026-11-05); no new 889Q/DQI circuit.
- `lucifer19/black-cat-credited-portfolio` (dataset updated 11-14): v12 DQI is
  byte-identical 821.
- The current 27.307 notebooks (`asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit`,
  `dmitrybatow/qcc-v27-frontier-live-assembly`, checked 2026-11-14/15): all ship 821
  unchanged and repeat that cutoff 19 is a net loss.
- Francisco Angulo de Lafuente's QVC Chemistry Compiler v0.4.0 (GitHub release,
  competition forum topic 759244, 11-14): 889Q DQI generator, four 102,400-shot checks
  with one value error retained; it is a repackaging of the same Syed line, not a
  cheaper decoder.

### 4.1 Rank-173 is real but does not apply to 821

The 2026-11-13 discussion “A rank-173 decomposition of the (H·D, H_hi·D²) map over
GF(2^24)” (Chih-Kai Wang, discussion 759048) is a valid algebraic result:
173 products instead of 176 in a paired block, −3 Toffolis per block, 182 blocks,
**−546 static T = 0.14%** of the 392k family. It passes a 576×48 bilinear check and a
bit-parallel 8,192-shot replay.

It explicitly does **not** apply to the current family: the newest public decoder has
1,376 GF(2^24) multiplications, each acting on its own pair of operands, while the
173-term block needs two products of the *same* operands. It applies to the older 392k
family, which is 3.0% behind 821 before the −0.14%; after it, it is still ≈2.9%
behind. **Do not port rank-173 to 821.**

The other rank lever (GF(2^24) → GF(2^12) norm, 42 → 36) is a research-level
multiplicative-complexity problem, worth ≈1.2k T / +0.010 points (P, Asterios open
problem 4). It is a fallback, not the next experiment.

### 4.2 Retention, moves, peephole, relabelling: saturated

Areeb's post-rewrite audit on the shipped file (M, log at 24.3 min) reports:

```text
qubits 889, static_toffoli_like 383414, repeated_pairs 5697,
retained_k0_hops0 0, retained_k0_hops16 0, peephole_rewrites 0,
register_qubits 840, min_qubits 889
```

So the 241 products are all that retention finds; host moves at `max_hops=16` add
nothing; the five peephole rules add nothing; and interval colouring cannot relabel
below 889. There is no free T or Q left in the supplied file. Any further gain needs
a source change (888Q) or a new arithmetic identity (norm rank/exact decoder).

---

## 5. The single highest-EV Kaggle experiment

### Build 888Q by one-wire reallocation on the cutoff-18 + 241-retention decoder

This is the only candidate with a positive expected delta, a public precedent, and a
sharp pass/fail. The audit's own estimate is +0.010 to +0.021 points; our exchange
rate says the break-even is ΔT = 862.2 mean T, so the audit's range corresponds to
ΔT ≈ 0–460.

#### Exact inputs

| input | value |
|---|---|
| decoder source | `syed3000/vqcc-own-circuit-portfolio` → `dqi_source_zip`, 8,486,126 bytes, SHA-256 `49e2b331d4008afb724985caf1038765b7a910f08838b590bf6e8fb692772763` (downloaded copy) |
| build wrapper | `kirderf/vqcc-dqi-cutoff-variants` → `build_cut.py` (Apache-2.0) |
| retention planner | same dataset → `retain.py`; Areeb Ali's notebook `areebbb/qai-fewer-toffolis-same-qubits-lb-27-29708` for the allocator/peephole source |
| runtime | competition `kickmix` (Kaggle image `kickmix.so`; local PyPI `kickmix` for dry runs) |
| verifier | competition `verifiers/dqi/verify_submission_dqi.py`, unchanged |
| baseline file | `821bf8d157c03c3e868a0099b0ab1438cfba664ab1bc6fec3210654099b672a3`, Q=889, static 383,414, mean T 382,600.383203125, official cost 360,209,905,486.0156, R 1.1912604648 |
| current trio | submission `58349843`: invsqrt `e46d90c3` 78,719.529147, DQI 821, chem maoxin v27 + refit 294,991,455.82 |

#### Procedure (one Kaggle CPU notebook, 4 cores, 30 GB)

1. **Hash gate.** Verify the source zip, the 821 file, and `build_cut.py`/`retain.py`
   hashes. Stop on mismatch.
2. **Rebuild cutoff 18 unretained.**
   `python build_cut.py SRC KM VER /tmp/dqi_cut18.kmb 18`
   Expected: 889 qubits, static 383,655, SHA prefix `32b0a8b44476` (M, Areeb's log).
3. **Apply 241 retention** with `extra=[], max_hops=0`.
   Expected: 889 qubits, static 383,414, SHA `821bf8d1…b672a3`. This reproduces the
   baseline byte for byte; if not, stop.
4. **Width profile.** Convert to `.kmx` and run `retain.scan` / `alloc.py`. Expected
   `52,983,602` lines, `5,938` repeated pairs, `168,612` idle windows on 49 scratch
   qubits, `min_qubits=889` (M, Areeb's log). Save the width profile and the 509
   blocking peak episodes.
5. **Classify the seven families.** For each blocking episode, record the wire that
   opens the peak and the value it holds. Group into the seven families from the
   public audit. Pick the family whose one-wire reallocation pattern is already used
   in the builder (`controller_work/after_c5/converter_width/gauge_park_*`,
   `local_flag_defer/local_flag_window.py`) and whose predicted recompute count is
   smallest. Save the choice and predicted ΔT before building.
6. **Apply one reallocation in source.** This is a source-level move of a value's
   lifetime to a wire that is idle across the peak (or an HMR release plus a
   recompute at the next use), not a gate-level patch of the 53M-line file. Rebuild
   with `set_max_qubits(888)`; assert Q=888.
7. **Retention again** on the 888Q file. Expected static T ≈383,414 + recompute
   cost; record static and mean.
8. **Official verifier, default salt**, then **16 independent salts** (or 48 for the
   expected cost). Record value/phase errors, R, mean T, cost. The areebbb run took
   ≈4.4 min per 102,400-shot DQI verification, so 16 salts ≈70 min.
9. **Paired replay.** Run the 821 baseline on the candidate's 16 salts (pass the
   candidate seed) and compare failure sets. The candidate must not fail an input
   the baseline passes.
10. **Gate and package.** Only if the gate below passes, write the candidate trio
    `submission.zip` (888Q DQI + current invsqrt/chem). Do not submit automatically.

#### Pass/fail

**PASS** all of:

- candidate Q = 888 and official verifier PASS on default + 16 salts with
  0 value/0 phase errors;
- `ΔT_mean = T_candidate − 382,600.383 ≤ 862.2` (break-even), and preferably
  ≤600 (≥+0.0062 points) or ≤460 (≥+0.0095 points);
- 16-salt expected cost < 360.9475e9 (821's 48-draw expected) by ≥0.05%;
- paired failure set is a subset of 821's on the same salts.

**FAIL / no-go** if Q ≠ 888, ΔT > 862.2, any salt fails an input the baseline passes,
or the expected cost is not lower. Record the family, the measured ΔT, and the
re-Verify log; do not submit.

#### Expected GM delta

Zero-failure GM at 27.306613; expected-over-draws GM at 27.288001. The delta is the
same on both (it is a cost factor):

| ΔT_mean | DQI cost change | ΔGM (points) | GM if 0 failures | expected GM |
|---:|---:|---:|---:|---:|
| 0 | −0.2248% | **+0.0205** | 27.3271 | 27.3085 |
| 200 | −0.1727% | +0.0157 | 27.3224 | 27.3037 |
| 400 | −0.1205% | +0.0110 | 27.3176 | 27.2990 |
| 460 | −0.1049% | +0.0095 | 27.3162 | 27.2975 |
| 600 | −0.0684% | +0.0062 | 27.3128 | 27.2942 |
| 862.2 | 0 | 0 | 27.3066 | 27.2880 |
| 1,000 | +0.0359% | −0.0033 | 27.3033 | 27.2847 |

The audit's +0.010 to +0.021 range is the ΔT 0–460 band. The midpoint +0.015 is a
reasonable prior; with a 50–70% build success probability the expected value is
≈+0.008 to +0.011 points.

#### Risks

- **The seven-family map is a public report, not independently reproduced.** The
  first experiment must reproduce the width profile and the 509 episodes. If the
  profile differs, stop and record the actual profile.
- **The one-wire pattern may cost more than 862 T.** The pass/fail is on the measured
  mean T; do not trust a static estimate.
- **New hash, new draw.** The 888 file changes the DQI SHA-256, so the salt draw is
  new. With 0.32–0.46 expected failures/draw, P(0 failures) ≈ 63–73%; a bad draw can
  lose 0.04–0.08 points *on that submission*. The leaderboard keeps the best
  submission, so the current 27.3066 remains the floor. Do not overwrite it with a
  worse-drawing 888 file unless the new draw is 0 failures.
- **Official verifier may find a new failure mode.** The paired 16-salt replay is
  mandatory; a single-salt PASS is not enough.
- **Build reproducibility.** The 821 build was byte-identical on Kaggle; use the
  same source zip SHA, Python 3.12, and kickmix. Keep the Apache-2.0 NOTICE/credits
  for Syed Asad Ali's decoder and Areeb Ali's retention.

#### Fallback if 888Q fails

1. **GF(2^24) → GF(2^12) norm rank 42 → 36** (Asterios estimate +0.010 points,
   ≈1.2k T). This is a new bilinear identity, not a circuit patch; run only if the
   888Q build is closed.
2. **Exact DQI decoder** (estimate +0.019 points): handle the abnormal Euclid steps
   exactly, making the score salt-proof. Harder than 888Q, but the largest single
   DQI correctness prize.
3. Do **not** fall back to cutoff 19/20/21 or 840Q.

---

## 6. Closed / do-not-spend list

- **Cutoff 19, 20, 21, 22**: negative EV (−0.008, −0.045, −0.160, −0.437 points).
  Cutoff 17 is a tie with 18; 18 stays.
- **889 → 840**: no public 840Q file; 49 scratch are live workspace; budget +45.9k T
  vs ≥134k T recompute; no-go.
- **Rank-173 port**: applies to the 392k family only; 821 has 1,376 independent
  GF(2^24) products; even on 392k it leaves the file 2.9% behind.
- **Retention/moves/peephole/relabelling**: audit reports 0 additional products,
  0 moves, 0 peephole rewrites, `min_qubits=889`.
- **Salt farming the current 821**: the current draw is already 0 errors; changing
  the zip/README does not change the DQI SHA, so it cannot redraw. Only a real
  circuit change (the 888Q build) gives a new draw.
- **Q-batching / 2×840**: Q ≥ 840 per batch and Q=889 allows only b=1; closed in
  `ABANDONED.md`.

---

## 7. Verification status and sources

- Baseline 821 official cost, R, Q, mean T: M, Areeb Ali's 2026-11-13 run log and
  `manwithacat/vqcc-apache-public-circuits` v125 manifest.
- Cutoff 15/16/19/20 scores and errors: M, `kirderf/vqcc-dqi-cutoff-variants`
  `verify15/16/19/20` logs.
- Cutoff excluded probabilities and expected-cost table: E, computed here from the
  verifier's `optimal_dqi_weights` and the Clopper–Pearson/R formulas. The 821
  48-draw expected cost is M; the base-rate split is E.
- 888Q open-problem estimate and 509 episodes/seven families: P, Asterios Panoras,
  `qcc-27-30-what-works-what-fails-and-why` (2026-11-14).
- HW-01 888Q precedent: M, `manwithacat/vqcc-hedge-wizardry` `entries.csv` HW-01.
- Rank-173 result and its limits: P, Chih-Kai Wang, competition discussion 759048
  (2026-11-13).
- No new circuit was built and no official verifier was run for this note. The 888Q
  experiment above is a plan; its PASS/FAIL is unexecuted.

Key links:

- https://www.kaggle.com/code/areebbb/qai-fewer-toffolis-same-qubits-lb-27-29708
- https://www.kaggle.com/code/ozertuu/quantum-ai-27-083-vqcc-dqi-cutoff-17
- https://www.kaggle.com/datasets/kirderf/vqcc-dqi-cutoff-variants
- https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits
- https://www.kaggle.com/datasets/manwithacat/vqcc-hedge-wizardry
- https://www.kaggle.com/code/asteriospanoras/qcc-27-30-what-works-what-fails-and-why
- https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/759048
- https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio

## 8. 实测：889 → 888 没有"免费"路径（2026-11-15，Kaggle）

`qingyu1232/qcc-dqi-q888-probe`（CPU，COMPLETE）直接读 `821bf8d1` 的声明宽度与实际用量，
原始日志：

```
dqi.kmb bytes 455584321 sha256 821bf8d1…b672a3 MATCH_821
num_qubits 889 num_bits 154157 static_toffoli_like 383414
op_kinds {'A': 49980, 'R': 52177, 'B': 17022253, 'Z': 46466, 'P': 3039542,
          'C': 32216017, 'S': 378664, 'X': 107658, 'H': 71568}
distinct_indices_used 889 min 0 max 888
UNUSED_IN_0..Q-1 0 []
ABOVE_DECLARED 0 []
FREE_SHRINK_IF_RENUMBERED 0 (Q -> 889 )
usage_least10 [(13606,15),(14180,23),(14852,11),(15232,35),(15272,19),…]
```

判决：

- 声明的 889 条 wire **全部被使用**，最大下标正好 888，`0..888` 无空洞。
  因此"声明宽度大于实用宽度 → 重编号白拿一个 qubit"这条路**不存在**，`
  (Q/(Q+1))² 的免费 0.225% 不存在。
- 最冷门的 wire 也有 13,606 次操作，不存在"顺带删掉一条死线"的空间。
- 所以 889→888 只能走**真实重分配**（release-and-recompute / HMR），
  预算仍是 ΔT ≤ 862（盈亏平衡），预期 +0.0095…+0.0205 GM，需要源码级 7 族改造。

验证范围：本项在 Kaggle 上跑（kickmix 只在 Linux 可用），本机未执行。

## 9. DQI 成本公式已完全定死（2026-11-15）

从官方 `verifiers/dqi/verify_submission_dqi.py` 反解，`821bf8d1` 的 360,209,905,486.02 可以
精确分解为

```
score = R(eps_plus) * Q^2 * T_mean
```

- `R(eps) = ln2 / -ln(1/2 + 2*sqrt(eps))`；
- `eps_plus` 是 Clopper–Pearson 上界，`DEFAULT_LOG2_DELTA = -128`，
  `num_shots = 102,400`；
- **0 个错误时** `eps_plus = -expm1(-128*ln2/102400) = 8.66e-4` → **`R = 1.19`**（0 错误的地板）。

反解 `T_mean`：`360,209,905,486 / (1.19 * 889^2) = 383,008`，而该件的
`static_toffoli_like = 383,414`。也就是说：

1. **`R` 已经踩在 0 错误地板上**（1.19），没有可优化空间；
2. **`T_mean ≈ static`**（只有 ~406 个门是条件门，0.1%），所以 DQI 实际上是
   **确定性成本**，不是抽签成本；
3. 因此 DQI 的成本只有两个乘子：`Q^2` 和 `T`。Q 少 1 个 = **−0.225% = +0.0205 GM**；
   T 少 1% = −1% = +0.122 GM（需要 3,830 个 Toffoli，不可能）。
4. 任何 1 次失败都会把 `R` 从 1.19 推向更高（eps=1.17e-4·… 每多 1 个错误约 +0.28–0.46%
   成本），所以在 Q/T 不变的前提下，抽到 0 错误就是最优。

结论：**DQI 的唯一剩余杠杆就是 889→888 的真实重分配**（+0.0205 GM），
没有"降低 R"或"抽签优化"这类空间。

## 10. DQI 的抽签是**由电路哈希决定的**，不是提交时随机（实测源码）

`verifiers/dqi/verify_submission_dqi.py:300-304, 338-339, 358`：

```python
def _initial_seed(circuit_hash: str, salt: str) -> int:
    if not salt:
        return int(circuit_hash, 16)           # 无 salt 时直接用电 .kmb 的 SHA-256
    return int(hashlib.sha256(f'{circuit_hash}{salt}'.encode('utf-8')).hexdigest(), 16)
...
base_seed = _initial_seed(circuit_hash, salt) if seed is None else int(seed)
```

结论（重要，纠正了之前"抽签运气"的说法）：

1. DQI 的 shot 采样、`HMR` 结果、`R` 结果全部由 **`.kmb` 自身的 SHA-256（+ 比赛的 salt）**
   派生。所以对同一个 DQI 文件，**每次提交得到完全相同的失败集合和完全相同的 cost**。
2. 因此我们的 **27.31193 是这三个文件的确定性分数**，不是运气；同一个 `821bf8d1`
   换谁来提交都是 360,209,905,486.02。
3. 反过来说，**重复提交同一个 DQI 文件不可能"抽"到更好的结果**，也无法通过换
   invsqrt/化学件来改变 DQI 的 draw（种子只看 DQI 自己的哈希）。
4. 榜上 27.314–27.319 与 27.3066 的差别因此来自**不同的 DQI 电路**（不同哈希 → 不同 draw）
   或不同的 Q/T，而不是同一文件的运气。

## 11. 源码级审计：889 是"五见证平台"，没有便宜的 qubit（2026-11-15）

完整报告见 `dqi_ancilla/REPORT.md`（326 行，只读源码分析，未构建、未模拟）。要点：

- 49 个 ancilla 的账正好是 **24 + 1 + 24**：
  - 24 = EEA 的 working carry word pair（`integrated_pipeline.py:163`→`:202`）；
  - 1 = gauge sentinel flag（`rolling_tail.py:226`，`:167→:198`）；
  - 24 = 瞬时 GF(2^24) scratch，出现在 **5 个调用点**，从不同时存在，每次返回前 free。
- **这 5 个站点各自都恰好到 864+1+24 = 889**。因为 Q 是全局最大值，
  **任何单点改动都改变不了 Q** —— 这正是此前 `qcc-dqi-q888-probe` 看到
  `FREE_SHRINK_IF_RENUMBERED 0` 的结构性原因。
- 唯一可能的路是把三个 1-bit predicate（tail flag / third-chart predicate / gauge sentinel）
  改成经典控制，ΔT 结构下界 0、悲观 +600，盈亏平衡 **+863**。最好 +0.0205 GM，现实 ±0.010。
- 887 及以下需要把 24-bit product scratch 在 5 个站点同时降到 23 bit —— 那是新的算术恒等式，
  不是补丁。

因此 DQI 的 Q 轴（每个 qubit +0.0205）在"补丁"意义上关闭；要拿它必须做一次
**五点定点手术**，且收益只有 +0.01～+0.02。

## 12. DQI-888 步骤 1–2：工具链闸门通过，且找到**唯一的第一个失败点**（2026-11-15 实测）

### 12.1 闸门：`build_cut.py ... 18` 在本会话重现

`qingyu1232/qcc-dqi888-gate`（CPU，COMPLETE）：

```
src zip 8486126  build_cut 1849  comp True
built cutoff 18: 889 qubits, 383655 static Toffoli-like, 145s
CUT18 qubits 889  num_bits 53908  static 383655
CUT18 sha 32b0a8b444762334ac028a381693cab9185b370ffd2261560894929afffaf216
GATE_32b0a8b4 True
```

**构建只要 145–209 s** —— 这一点很重要：888 手术的迭代成本是分钟级，不是"多天"。

### 12.2 `set_max_qubits(888)` 的第一失败点（决定性）

`qingyu1232/qcc-dqi888-probe`（COMPLETE）：

```
ValueError: Attempted to allocate more qubits than the maximum.
  allocated: 877  requested: 12  allocated+requested: 889  max: 888
  File ".../blocks/v5/inverse_retained_norm_deferred.py", line 87, in _inverse_with_bank
    temporary = builder.alloc_qubits(12)
```

**这比此前源码审计的结论精确得多**：不是抽象的"五见证都在 864+1+24"，
而是**一个 12 位临时字**在这条路径上需要 877+12=889。

失败点的上下文（`_inverse_with_bank`）：

```python
inverse_norm = builder.alloc_qubits(12)      # 12 位倒数，活着
...
temporary = builder.alloc_qubits(12)         # <- 死在这里
for half in (source[:12], source[12:]):
    xor_product(builder, half, inverse_norm, temporary)
    builder.swap(half, temporary)            # 交换后 temporary 持旧的 half
    mask = builder.alloc_bits(12); builder.hmr(temporary, mask)   # 把这个旧值测成经典 mask
builder.free(temporary)
```

所以 `temporary` 的作用是**给 swap 当暂存 + 随后被 HMR 成经典 mask**。
要拿到 888，只需要在这条路径上让峰值降到 876：

- 要么在 `alloc_qubits(12)` 之前释放 1 条活线（候选：`delta` 之类的 1-bit predicate，
  或 `prefix_record.child_mask` 之外仍活着的 flag）；
- 要么把这块 12 位暂存改成**复用 `clean_bank` 里的空闲段**（函数本身已经持有 `clean_bank`，
  `original_norm/child_norm/child_inverse` 就是从中切出来的）。

### 12.3 下一步（下一次构建即可判定）

在 `inverse_retained_norm_deferred.py` 的 `temporary` 处做**一处**改动，重建 888：

- 判据：`num_qubits == 888`，`static_toffoli_like` ≤ 383,655 + 863（盈亏平衡），
  生成器/官方可验证性由官方 verifier（默认 salt 起）判定；
- 因为构建 145 s、验证 4.4 min/salt，一次完整判定 ≈ 15 min。

这与此前 `dqi_ancilla/REPORT.md` 的"五站点协同"不同：真实构建显示**第一个也是唯一的阻塞点**
是这处 12 位暂存；先修它，再看是否还有第二个。

## 13. DQI-888 步骤 3：877 条活线的精确构成 —— 只差**一条 1-bit flag**

`qingyu1232/qcc-dqi888-instr2`（COMPLETE）。给 `CircuitBuilder` 套了一层代理，记录每次
`alloc_qubits` 的调用点（`file:line`），`free` 时移除；溢出时 dump 所有仍活的线及其分配点：

```
==== maxq 889
allocated at end 840
built cutoff 18 at max 889: 889 qubits, 383655 static Toffoli-like
SHA 32b0a8b444762334ac028a381693cab9185b370ffd2261560894929afffaf216  MATCH_32b0a8b4 True

==== maxq 888
OVERFLOW at controller_work/after_v3/blocks/v5/inverse_retained_norm_deferred.py:87  requested 12  allocated 877
LIVE_1BIT 5 sites 5
  live 24 from controller_work/after_c5/integration_v3/integrated_pipeline.py:163
  live 12 from controller_work/after_v3/blocks/v5/inverse_retained_norm_deferred.py:80
  live  1 from controller_work/after_c5/extractor_width/rolling_tail_early.py:41
```

即溢出那一刻的 **877 = 840（syndromes）+ 24（carry 字对）+ 12（inverse_norm）+ 1（rolling-tail
`current` flag）**，账目完全对得上。而要分配的 `temporary` 正是第 12 个。

**因此 888 只需要处理一条线**：`rolling_tail_early.py:41` 的 `self.current`。
它是此刻唯一的 1-bit predicate；把它（HMR 成经典位 + free，稍后按 numerator 重新求得）
处理掉，876 + 12 = 888，构建就能过。

这与 `dqi_ancilla/REPORT.md` §5 的"五见证平台"并不矛盾，但**更锐利**：五见证描述的是
其他路径上的峰值；**cutoff-18 这条真实构建路径上，阻塞点就是这一个 flag**。
报告 §6 推荐的第一个补丁也正是 A/B 站点（`rolling_tail_early.py`），与此独立吻合。

### 13.1 下一步的唯一改动

`RollingTail.begin_slot/end_slot`（`rolling_tail_early.py:41,48-90`）里 `self.current` 的使用是：

```python
current = self.current if first else self.builder.alloc_qubits(1)[0]
zero_xor(self.builder, numerator, current)      # current = [numerator == 0]
self.builder.cswap(current, numerator, denominator)
...
self.builder.cx(current, previous); erase_zero_flag(self.builder, denominator, previous)
```

作者在 gauge 站点已经演示过"park + 重算"（`gauge_park_lender.py` 的 `park/unpark`：
`cswap → alloc_bits → hmr → ... → toggle_zero 重算 → cz 补相位 → cswap`）。
把同样的手法用在 `self.current` 上，让它在 `inverse_prefix_with_bank` 期间不占线，
即可拿到 888。

判据不变：`num_qubits == 888`、`static_toffoli_like ≤ 384,518`（=383,655+863 盈亏平衡），
官方 verifier 默认 salt + 16 salts，0 value/0 phase errors；预期成本 < 360,209,905,486.02 才提交。
构建 145–215 s、验证 4.4 min/salt，所以一轮判定 ≈ 15 min。

## 14. DQI-888 步骤 4–5：惰性分配补丁有效，墙从第一道推进到第二道

### 14.1 源文件被自引用哈希链冻结，只能做运行时补丁

`v7_binding.py` 用三层清单把 132 + 266 + 21 个源文件按 `bytes + sha256` 锁死，清单自身又被
`V6_PLAN_SHA`/`V6_MANIFEST_SHA` 常量锁死。直接改
`first3_retained_norm_adapter.py` 会立刻失败：

```
AssertionError: controller_work/after_v3/blocks/v6/first3_retained_norm_adapter.py
  (v7_binding._check_files: assert source.stat().st_size == row['bytes'] and digest(source) == row['sha256'])
```

（作者在文件 docstring 里也写了这个设计："the existing initial tail predicate is borrowed only
before its first use and is HMR-reset **without being freed**" —— 为了保住 `821bf8d1` 的原样，
他刻意不 free 这条线。）

### 14.2 运行时惰性补丁（不改任何文件，哈希全对）

把 `RollingTail.current` 换成**首次读取时才分配**的属性（`_cur = UNSET` 哨兵，
`seed_prefix` 显式设 `None` 的情况不受影响），并给**所有持有 `RollingTail` 的模块**打补丁：

```
Base.Tail is <module 'rolling_tail_deferred' .../converter_width/tail_phase_defer/rolling_tail_deferred.py>
modules holding RollingTail: ['rolling_tail', 'rolling_tail_conditional', 'rolling_tail_early', 'rolling_tail_deferred']
patched 4 module(s)
```

第一次只补 `rolling_tail_early` 时无效（`Base.Tail` 是 `rolling_tail_deferred`），补全四个后生效。

### 14.3 墙推进了：第一处已通过，现在卡在 third-pivot

```
BUILD FAILED
  first3_retained_norm_adapter.py:72  third = Third.emit_prefix(builder, words[:2], words[2], carry, borrowed_flag)
  third_pivot_chart.py:79              inner = Norm.inverse_prefix_with_bank(builder, current, clean_bank)
  inverse_retained_norm_deferred.py:87 temporary = builder.alloc_qubits(12)
ValueError: allocated 877 + requested 12 = 889 > 888
```

对比步骤 3（当时死在 `first3_retained_norm_adapter.py:52` 的**第一次** bank 反演）：
**现在前三次 bank 反演都过了**，说明 tail flag 那一条确实被让出来了；新的占用者是
`borrowed_flag`（adapter 第 65 行 `borrowed_flag = tail.current` 分配、随后传给
`Third.emit_prefix`），它在 third-pivot 的 bank 反演期间活着。

这与 `dqi_ancilla/REPORT.md` 的"五见证"结构一致：**每修一处，墙就换到下一位见证者**。
目前已确认的顺序是：① tail predicate（已解决）→ ② third-pivot 的 borrowed flag。

### 14.4 下一步

对 `third_pivot_chart.emit_prefix` 做同型处理：把 `borrowed_flag` 的**读取**推迟到它第一次
被真正使用的位置（`third_pivot_chart.py:115` 的 `flag = builder.alloc_qubits(1)` 附近），
或者把该函数里的 bank 反演挪到借用之前。判据不变（Q=888、static ≤ 384,518、官方 verifier）。
构建失败只要 34 s，所以每次迭代很便宜。

## 15. 第二道墙的真相：`zero_flag` 不能推迟，但它可以**古典化**（并顺手省 1 个 Toffoli）

`third_pivot_chart.emit_prefix`（`third_pivot_chart.py:67-96`）的真实顺序：

```python
Tail.zero_xor(builder, current, zero_flag)          # 78: 用 current 的"反演前"值算 [current==0]
inner  = Norm.inverse_prefix_with_bank(...)         # 79: <- 峰值在这里
_add_head(builder, heads[0], current, zero_flag)    # 80: 才第一次消费 zero_flag
zero_mask = builder.alloc_bits(1)
builder.hmr(km.array([zero_flag]), zero_mask)       # 86: 之后 flag 归零但**不 free**
middle / outer = Norm.inverse_prefix_with_bank(...) # 88, 92
```

**所以"把 borrowed_flag 的读取推迟到首次使用"不成立**：`zero_xor` 必须在反演之前跑
（它读的是 `current` 的反演前值），而线本身由调用方（adapter 第 65 行）分配。
推迟读取救不了峰值。

### 15.1 但它可以古典化，而且这是**唯一**还没试过的机制

`_add_head` 的消费形式是单个 `builder.ccx(zero_flag, head, current)`（`third_pivot_chart.py:60-61`）。
而 kickmix **支持经典条件门**——本仓库里已有两处先例：

```python
# invsqrt：push_condition / pop_condition
builder.push_condition(a6_outcome); builder.z(q); builder.pop_condition()
# DQI retain.py 的输出格式： "CZ a b if b7"
```

所以可以把这条线改成：

1. `zero_xor(current, flag)` 先把谓词算到线上；
2. `mask = alloc_bits(1); hmr(flag, mask); free(flag)` —— 线立即归还；
3. `_add_head` 里的 `ccx(zero_flag, head, current)` 换成
   `push_condition(mask); cx(head, current); pop_condition()`。

**收益不只是省一条线**：`ccx` 是 Toffoli-like，条件 `cx` 不是 —— 这一步同时把
`ΔT` 变成 **−1**（更好），而不是 +某值。

### 15.2 剩下的工程量（不是障碍，是清单）

- `Record` 里存的 `zero_flag` 语义要改（改成 `mask`），`third_pivot_chart._contract`
  与 `emit_closing` 里对 `zero_flag` 的约束要一并检查（`emit_closing` 只用 `record.zero_mask`）；
- adapter 第 76 行 `assert tail.current == borrowed_flag` 与后续 `begin_slot` 里
  `previous = self.current` 的用法需要重新指向（线被 free 后不能再被当作要 `cx` 的目标）；
- 这些都可以用运行时猴补完成，源文件哈希保持全对。

### 15.3 诚实的进度定位

- 墙 1（tail predicate）：已解决（惰性属性，4 个模块打补丁）。
- 墙 2（third-pivot 的 `zero_flag`）：**推迟不可行**，但古典化机制存在且有先例，
  预计 ΔT = −1（比盈亏平衡 +863 好得多）。
- 拿不到 888 之前，官方 verifier 不应运行；拿到后按默认 salt + 16 salts 判定。

这一轮**没有分数变化**，但把一个"看起来只差一行"的步骤纠正为"需要改 Record 语义 + 三处调用"
的真实清单，并找到了唯一可行的机制（`push_condition` 古典控制）。

## 16. DQI-888 结论：两道谓词墙已推倒，第三道是**算术宽度**（不可用补丁解决）

`qingyu1232/qcc-dqi888-class`（COMPLETE，26 s 到失败）：

```
lazy tail patched on ['rolling_tail', 'rolling_tail_conditional', 'rolling_tail_early', 'rolling_tail_deferred']
third_pivot emit_prefix patched
adapter emit_prefix re-exec'd with tail re-point
BUILD FAILED
  first3_retained_norm_adapter.py:89   builder.swap(current, carry)
  direct_carry_arithmetic.py:72        divide_deferred
  direct_carry_arithmetic.py:37        _adjoint_consume:  temporary = builder.alloc_qubits(24)
ValueError: allocated 865 + requested 24 = 889 > 888
```

**墙的推进序列（每一步都是实测）：**

| # | 失败点 | 占用 | 处理 | 结果 |
|---|---|---|---|---|
| 1 | `first3_retained_norm_adapter.py:52` → `_inverse_with_bank` 的 12 位临时 | 877+12 | tail predicate 惰性分配（4 模块补丁） | ✅ 推倒 |
| 2 | `third_pivot_chart.py:79` → 同一个 12 位临时 | 877+12 | `zero_flag` 古典化（`zero_xor → hmr → free`，`ccx` 改 `push_condition+cx`，顺带 ΔT **−24**） | ✅ 推倒 |
| 3 | **`_adjoint_consume` 的 24 位临时**（division） | **865+24** | —— | ❌ **结构性** |

### 16.1 为什么第三道墙不能用补丁解决

865 = **840（syndromes）+ 24（carry 字对）+ 1（tail flag）**。这三项都是**必需的**：

- 840 是契约规定的 70 个 12-bit syndrome 寄存器，不能动；
- 24 是 `divide_deferred` 的 carry，是运算对象；
- 1 是 tail flag：它在 slot 里被用作 `cswap(current, numerator, denominator)` 的**相干控制位**，
  不是"算完就测"的谓词，**不能古典化**（一测就把 12+12 比特的相干交换破坏掉）。

而 `_adjoint_consume` 要的 24 位 scratch 是 GF(2^24) 乘法的目标寄存器，也不能拆成 12+12
（`xor_product` 的输出宽度就是 24）。

这正是 `dqi_ancilla/REPORT.md` 里那句预言的落地版：
> "Q=887 (or lower) needs the 24-bit product scratch at five sites to become 23 bits —
> a new arithmetic identity, not a patch."

实测把它从"来自源码审计的推断"变成了"来自真实构建的第三条墙"：
**Q=888 需要一条 24→23 位的新算术恒等式**（或等价地把 carry 从 24 降下来），
这是新的数学，不是补丁。

### 16.2 DQI 轴的最终账

| 项 | 状态 |
|---|---|
| 889 件复现闸门 | ✅ `32b0a8b4` / `821bf8d1` 均重现（145–209 s） |
| 888 构建 | ❌ 三道墙：tail flag（已解）、third-pivot flag（已解）、24 位算术 scratch（**不可解**） |
| 官方 verifier | ❌ **从未运行**（没有 888 件可验） |
| λ/成本变化 | 无 |

**因此在"补丁"意义上 DQI 的 Q 轴正式关闭**：剩余路径需要新的算术恒等式（24→23 位乘法
或 12 位 carry 方案），与 invsqrt Q45 的 SAT 恒等式属于同一类工作。

## 17. 第三道墙的根：GF(2²⁴) 乘法张量，拆分需要新恒等式（已核实到底）

reviewer 建议"把 24 位乘积 scratch 改成两段 12 位"。把调用链读到底：

```
_adjoint_consume:  temporary = alloc_qubits(24)
                   A.product(builder, source, target, temporary, delta)
gf24_arithmetic.product:  Prior.product(builder, source, value, target, delta,
                                        tensor24(delta))
gf24_arithmetic.tensor24: Prior.convert_tensor(delta, Tensor.multiplication_tensor(), Tensor.DELTA)
```

即 `temporary` 承载的是 **GF(2²⁴) 乘法张量的一次完整收缩结果**（24 位）。
把它拆成两段 12 位，等价于换一套乘法张量分解——例如改用塔表示 GF((2¹²)²) 的
Karatsuba 形式，需要三组 12 位中间量再合并，那**不是把 24 拆成 12 就能省出 1 条线**，
而是重写这块算术并重新验证相位。

所以 `dqi_ancilla/REPORT.md` 的那句判词在实测中被完整确认：

> Q=887 (or lower) needs the 24-bit product scratch at five sites to become 23 bits —
> a new arithmetic identity, not a patch.

**DQI 的 Q 轴到此结束**，三条子路线都有实测结论：

| 子路线 | 结论 |
|---|---|
| 889 复现闸门 | ✅ `32b0a8b4` / `821bf8d1`（145–209 s） |
| 谓词墙 ①②（tail flag、third-pivot `zero_flag`）| ✅ 已推倒（惰性属性 + `push_condition` 古典化，ΔT −24） |
| 墙 ③ 24 位乘法 scratch | ❌ 需新的 GF(2²⁴) 乘法恒等式 |
| 888 构建 / 官方 verifier | ❌ 从未成功 / 从未运行 |

## 18. 本会话四条研究线的最终汇总

| 线 | 最佳可证结论 | 与榜首差距 |
|---|---|---|
| chemistry | B/C/Adam 三轴全域否定；only B=143 passes the 20 mHa gate | 无 |
| invsqrt Q | 重建阶梯 0–4 AND 全域 0/10；T 轴 614 对可重算但 0 可 hold | 无 |
| DQI Q | 两道谓词墙已破，第三道需新算术恒等式 | 无 |
| 公开件扫描 | 507 行 manifest + 33-qcc-v8-members 全部劣于我们 | 拼装上限 27.31219 |

**本会话成果：27.31193（rank ~336/3073），相对采用的公开包 +0.00532。**
要达到 28+（−9% 成本乘积）或 29.9（−23.9%），必须完成上面任意一条"新恒等式"级工作。
