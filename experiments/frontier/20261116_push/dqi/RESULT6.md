# DQI structural lever probe — 2026-11-16 (part 6)

Mandate: ONE structural lever that can exceed 1% — (1) out-of-place division,
(2) v13 CSWAP-free routing backport, else (3) fewer-products-per-pass with
preserved semantics. Base = v12 source (`zhuating/qcc-dqi-source-v12`),
sha `7cbe8ecf…`, Q 889 / static T 384,003 / mean T 383,156.29 /
cost 360,733,280,431.94.

## 0. Outcome

**All three prongs are closed with new measurements; no candidate, no
submission.** Concretely:

1. **Out-of-place division (preferred): patch-impossible, measured.** A
   per-site live-set census of the real build (k16) shows all 203
   peak-region 24-bit allocs land at exactly Q_before = 865 → 889, spread
   over *four* distinct call sites (`_adjoint_consume`, `emit_prefix`,
   `emit_closing`, synthesis `emit_prefix`). There is no dead 24-bit word at
   any divide/product site, and eliminating the peak requires removing all
   four simultaneously — i.e. the whole in-place arithmetic, which is the
   v15 redesign (weeks), not a patch. Target "Q ≤ 889 with T cut ≥ 5,000"
   is not reachable by patching; target "Q 864–880" needs the redesign. §2.
2. **CSWAP-free backport: T delta = 0 at same Q, measured.** Extended exact
   scans (k15) find 0 canonical-CCX pairs, 0 CCZ pairs, **0 CSWAP pairs**,
   0 folds, 0 degenerate deletions, 0 |0>-controls, 0 dead writes — saving
   **0 T**. The 12,384 CSWAPs are partitioned by call site (k16): 52.7% is
   one recursion sandwich (`swap_low`, load-bearing on both sides), the
   rest is route/exchange/rotate/local/tail/lender routing, every
   route/unroute pair separated by live readers. "Backporting" the v13
   routing without changing semantics is impossible as a patch: v13's
   unconditional-SWAP + classical-CX form requires early measurement of the
   routing flags, and re-deriving the phase repayment at the moved
   measurement is the decoder redesign itself. §1–§3.
3. **Fewer products per pass: irreducible as a set, sketched proof.** The
   1,184 extractor products (592 + 592) are the off-diagonal eliminations of
   a triangular system with provably nonzero diagonal (every coefficient
   asserted nonzero in source); inputs span the full Hilbert space, so no
   elimination is the identity. The return sweep restores words the
   converter later reads (dead-write scan: 0). MBU cannot replace the
   return (it uncomputes overwrites, not fresh-held garbage). Synthesis sums
   are forced by CRT window growth (+1 word/node). A decoder with fewer
   passes (BM) costs 8× multiplications (RESULT4 §2). §4.

A measured negative with precise reason is the acceptable outcome, and this
is it: **DQI stays at 890 Q / 368,139 T / 347.375e9 (shipped).**

## 1. k15: completion scan of the v12 tape (option-2 patch test)

Kernel `zhuating/qcc-dqi-v12cswapscan`: rebuild via `build.sh` (control),
then exact numpy scans over the 52,930,855-op tape with two soundness holes
in the k9 (v12tscan) indices fixed:

* k9's write/read indices ignored CSWAP operands entirely, so a CCX pair
  spanning a CSWAP touch could have misfired, and CCZ operands were
  invisible as readers. k15 extends the write index with both CSWAP targets
  and the read index with all CCZ/CSWAP operands (tape order
  `cswap(f,a,b) -> A=f,B=a,C=b`, consistent with k9's own C2 control
  check). All k9 zeros are re-confirmed under the strictly stronger rules.
* k9 lumped `CCX(a,a->t)` (= `CX(a->t)`, a fold needing rewrite, not a
  deletion) and CSWAP-dead-write (unsound: deleting `cswap(f,a,b)` because
  one target resets ignores the other target) into deletions. k15 splits
  folds from deletions and excludes CSWAP from dead-write. All fired 0, so
  no prior verdict changes, but the rules are now sound if they ever fire.

Measured (report.txt, log lines verbatim):

```
BUILD 0  455590024  7cbe8ecf... MATCH
A3 Q 889  n 52930855  staticT 384003  nbits 53911
A4 opcodes {CCX 364619, CCZ 7000, CSWAP 12384, CX 31293155, CZ 538932,
            SWAP 378664, HMR 71531, R 48210, ...}
B0 touch pairs 65847811
C0 canonical-CCX cancel pairs 0
C0z CCZ cancel pairs 0
C0s CSWAP cancel pairs 0
C1 folds (rewrite, not counted) 0
C1b degenerate deletions (swap-same) 0
C2 |0>-control Toffolis 0
C3 dead to R 0 / dead to unused HMR 0
C4 total sound deletions 0, implied T saving 0 => T ~ 384003
D0 no candidate: the v12 T surface is saturated too
```

Notes on the new rules (all exact, no sampling):

* C0 canonicalises control order (`(a,b)/(b,a)` pairs would now match; 0).
* C0z: CCZ is fully symmetric and diagonal, so equal write-versions on all
  three operands + unconditional on both gates suffices — no read check
  needed (diagonal gates commute with readers; HMR/R between would bump
  versions via the write index). 0.
* C0s: same `(f,a,b)` write-versions + no touch of either target strictly
  between (f is a pure control) + unconditional. This is the patch version
  of the CSWAP lever: any hit would be a same-Q T deletion with no
  redesign. 0.
* Dead-write extended to all three CCZ operands (symmetry); CSWAP excluded
  (unsound, see above). 0.

Guard was saving ≥ 200 for candidate+verify (k9 rule); 0 ⇒ no candidate,
no verifier run from k15.

## 2. k16: where the T and the Q sit (blockers for options 1 and 2)

Kernel `zhuating/qcc-dqi-v12csiteattr`: k14-exact instrumented rebuild
(`TOTAL 384003 == official`, `SHA 7cbe8ecf… MATCH`, so the instruments
change nothing) plus (S1) outermost-`controller_work`-frame attribution of
every CSWAP/CCZ/init_and emission and (S2) a census of every
`alloc_qubits(count ≥ 12)` as `(count, Q_before, site)`.

### 2.1 CSWAP by call site — the 3.22% has no single elidable home

Total 12,384 = 3.22% of static T (exact; `cswap_folded` = 0, i.e. no
classical-control swap exists anywhere — the v13 form is wholly absent):

| T | share of CSWAP | site | role |
|---:|---:|---|---|
| 6,528 | 52.7% | `transpose14_core.py:45 swap_low` | frame recursion sandwich: `swap_low` … recurse on `(B,low)` … `swap_low` — the recursion reads both sides, so the pair cannot cancel |
| 768 | 6.2% | `transpose14_window.py:54 route` | conditional rotate of the window |
| 768 | 6.2% | `transpose14_core.py:94 exchange` | head ↔ prior-head exchange around `local` |
| 672 | 5.4% | `transpose14_core.py:157 route` | conditional rotate, second route site |
| 576 | 4.7% | `transpose14_core.py:42 rotate` | conditional rotate primitive |
| 480+480 | 7.8% | `rolling_tail_deferred.py:60,98` | tail slot/return routing |
| 384+384 | 6.2% | `transpose14_core.py:107,123 local` | local head exchanges |
| 168+168 | 2.7% | `gauge_park_lender.py:98,114` | gauge sentinel park/unpark |
| 6×96+4×96 | 7.8% | retained-flag / transpose-handoff windows | matched-flag routing |
| 4×12 | 0.4% | tail gauge/seed sites | one-off routes |

Every route/unroute pair has live readers between the two halves by
construction (scales, lowers, source divisions, recursion), and k15 proves
no two identical CSWAPs are adjacent-modulo-commutation anywhere on the
tape. The largest site (`swap_low`, 1.7% of T) is itself a sandwich, not a
spike. There is no ≥1% CSWAP sub-lever that is sound by construction.

### 2.2 Large-alloc census — the 889 peak is hit 528 times at 4 sites

`max(Q_before + count) = 889`; 528 allocs reach Q ≥ 889. 24-bit allocs:
n = 228, min Q_before = 840, max = 865, mean = 864.8, **203 at
Q_before = 865** (i.e. landing exactly on 889):

| 24-bit allocs at Q_before=865 | site |
|---:|---|
| 67 | `gf24_nested_norm.py:269 emit_prefix` (forward input-scale products) |
| 51 | `direct_carry_arithmetic.py:37 _adjoint_consume` (cofactor products) |
| 50 | `gf24_nested_norm.py:305 emit_closing` (return-sweep pair closes) |
| 34 | `fused_crt_synthesis.py:111 emit_prefix` (synthesis prefix products) |
| 1 | `unit_jet_tensor.py:180 emit_prefix` |

The remaining 25 sit at 864 (12+12, first-three region) and 840 (1,
key prefix). 12-bit allocs reach 889 from 877 (`_consume_halves`,
`_inverse_with_bank`) — i.e. the scalar path already runs at the peak too.

Consequences for option 1: at every divide/product site in the peak region
the live set is exactly 864 data + 1 flag with no dead word — the retained
`1/Norm(u)` scalar path (`_consume_halves`, 12 bits) is already the
narrowest sound form (RESULT2 §4 point 2: 12 bits provably insufficient for
the variable×variable cofactor step), and even a synthesis-local fix would
leave the extractor's 168 peak allocs. Q < 889 requires eliminating *all*
24-bit peak allocs at once — the out-of-place redesign of RESULT2 §5
(new accumulate target, re-derived repayment through `DivisionRecord`,
`restore_with_shared_norm`, `rolling_tail` slot/return, matched inverses),
not a patch. No out-of-place candidate was built: any such edit changes
values/phases everywhere and cannot be verified except by the full
official verifier after a complete re-derivation.

## 3. Why the v13 routing cannot be backported as a patch

v13's form (unconditional SWAP + classically-conditioned CX, per
RESULT3 §2.1) is what you get by measuring each routing flag early (it is
measured anyway at `erase_zero`/HMR release) and making every downstream
use classical — which folds `cswap→SWAP`, `ccx→CX`, `ccz→CZ-if-b`,
`init_and→R+CX` (all 0 T by the k14 rule). Sound in general only by
deferred measurement, which fails here as a patch for three concrete
reasons, each visible in the v12 source:

1. **The flag is targeted between creation and measurement.** E.g.
   `window_transpose_shared.py:96 builder.cx(middle, third)`: a flag wire
   is a CX target mid-lifecycle. Moving its HMR earlier changes the
   measured distribution unless the intervening coherent uses are
   re-derived too.
2. **The repayment predicate is location-dependent.** `erase_zero` repays
   `(-1)^{m·[word=0]}` against the *routed* position (`B[-1]` after
   route/unroute sandwiches whose permutation is flag-dependent). An
   earlier measurement repays against a different intermediate state; the
   correction is only valid at the point it was derived.
3. **HMR is X-basis + Z-reset** (RESULT5 §3): the outcome is a fresh random
   bit whose phase kickback the existing repayment exactly cancels *at the
   existing point*. There is no Z-basis measurement primitive to certify a
   routing predicate early.

So "backport the routing without changing semantics" is self-contradictory:
the semantics-preserving version IS the phase-repayment re-derivation,
i.e. the v15 decoder — same cost class as the out-of-place division.
T delta of the patch version at same Q: **0** (k15 C0s).

Calibration (inherited, RESULT3 §2.1): even a magical full CSWAP
elimination gives 371,619 T at 889 Q = 349.2e9, still short of the shipped
347.375e9. The v12 line cannot win on this axis at any achievable T.

## 4. Prong 3: fewer products per pass (irreducible as a set)

Measured counts (RESULT4/RESULT5, independently reproduced by k16 totals):

* Extractor ladder: `Σ_{i=3}^{34} i = 592` GF(2^24) products forward and
  592 on the return = **1,184 × 99 T = 117,216 T (30.5% of T)**.
* Synthesis: prefixes `Σ_{r=1}^{34}(r+2)·42 = 27,846 T`, returns
  `Σ r·42 = 24,990 T`, 34 paired closings `34×363 = 12,342 T`.
  The `+2` per prefix node is the in-place `out = N+T` linear map with an
  `r`-word `N` and a trinomial multiply needing `r+2` (RESULT2 §3-D).

Sketch why no fewer-products variant preserves semantics:

* Each forward `query_step(old,i)` is the off-diagonal elimination of one
  pair in a triangular continuant/Möbius tableau, dividing by the scalar
  `node(old)[1] ^ node(new)[1]`, which the source asserts nonzero at every
  site. A triangular system with nonzero diagonal needs *all* off-diagonal
  eliminations for exactness; the inputs are superposed over all values,
  so no elimination is the identity on the verified state (a skipped step
  leaves a generically-nonzero residual → value errors at full shot
  count).
* The return sweep is the exact inverse restoring head words the converter
  and matched-inverse calls later read; liveness is confirmed by the
  dead-write scan (0, k15 C3) — no restored word is dead.
* Measurement-based uncompute cannot replace the return: MBU applies to
  fresh-held garbage (AND targets, `del_and` = 0 T, already fully used —
  48,210 `del_and_folded`), not to in-place overwrites `d ← (d+P·n)/q`
  whose outputs stay live.
* Rank is already optimal per product (99 = 11×9, 42 = 7×6; proven ranks
  in `20261112_mulrank`); the count of products is the remaining
  degree of freedom, and it is forced by the tableau shape.
* The only known fewer-passes decoder (BM retain/replace) costs 8× the
  multiplications (RESULT4 §2: ~950 vs 7,560) — a T disaster, not a lever.

A −5,000 T cut needs ~51 fewer 24-bit products or ~119 fewer 12-bit
products with zero behavioural change; the tape has no duplicated, dead,
or removable product (all sound peephole classes empty, k15 §1).

## 5. k17: 3-salt control verification (unchanged official verifier)

Kernel `zhuating/qcc-dqi-v12verify3`: rebuild via `build.sh`, then the
unchanged `verifiers/dqi/verify_submission_dqi.py`
(`ProblemSpecDQI.benchmark_instance()`, 102,400 shots, batch 256,
4 workers) at salts `''`, `'dqi-salt-2'`, `'dqi-salt-3'` (same extra salts
as the k12 retain candidate, for comparability). Measured:

```
VERIFY salt=''         125s  Q 889  T 383156.2909  score 360733280431.941  err 0/0  sha 7cbe8ecf…  +0.000000%
VERIFY salt='dqi-salt-2' 129s  Q 889  T 383156.4100  score 360733392563.461  err 0/0  sha 7cbe8ecf…  +0.000031%
VERIFY salt='dqi-salt-3' 126s  Q 889  T 383156.0100  score 362389734021.225  err 1/0  sha 7cbe8ecf…  +0.459191%
```

The default salt reproduces the published baseline to the digit
(360,733,280,431.94, 0/0). Salt-2 is identical to 3e-5. Salt-3 shows
**1 value error / 0 phase errors with status still PASS** and a +0.46%
score move — i.e. the single error is inside the verifier's tolerance and
reads as a shot-noise/tolerance event on the unmodified control (same
signature as k12's retain candidate, which was 1/0 at salt-2 and 0/0 at
the other two salts while losing on cost regardless). Baseline T is stable
across salts to ±0.2 T; baseline cost to ±0.0001% at 0 errors.

## 6. Receipts

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k15 | `zhuating/qcc-dqi-v12cswapscan` | rebuild control + extended exact scans (canonical CCX, CCZ, CSWAP pairs; folds split; CSWAP-free dead-write; CSWAP-aware indices) | **complete**: sha MATCH, 0/0/0/0/0/0/0, saving 0, no candidate |
| k16 | `zhuating/qcc-dqi-v12csiteattr` | exact rebuild + CSWAP/CCZ/init_and call-site attribution + large-alloc Q census | **complete**: TOTAL MATCH, sha MATCH, site table (§2.1), 203/228 peak 24-bit allocs at 865 (§2.2) |
| k17 | `zhuating/qcc-dqi-v12verify3` | rebuild + unchanged official verify, 3 salts | **complete**: sha MATCH, 0/0, 0/0, 1/0(PASS); T stable ±0.2, cost ±0.0001% at 0 errors (§5) |
| control | `zhuating/qcc-dqi-v12build` (k8) | v12 as published | 889 Q / 383,156.29 T / 360.733e9 / 0-0 |

All runs Kaggle CPU (`enable_gpu: false`, no internet, competition data
attached, DQI source `zhuating/qcc-dqi-source-v12`); nothing simulated
locally, nothing packaged, nothing submitted.

## 7. Verification scope, stated honestly

* Scores quoted are the unchanged official DQI verifier on Kaggle CPU.
  k15/k16 built no candidate so they ran no verifier (guard: saving ≥ 200).
  k17 verifies the unmodified control at 3 salts (§5: 0/0, 0/0, 1/0-PASS;
  the single salt-3 value error is inside verifier tolerance on the
  unmodified build, same signature as k12's observation).
* Static counts (Q, 384,003, opcode census, per-wire touch counts, CSWAP
  site table, alloc census) are read from the built tape / instrumented
  build whose TOTAL equals the official count exactly and whose SHA
  reproduces `7cbe8ecf…` byte-for-byte, so the instruments change nothing.
* The k9→k15 index fixes (CSWAP-aware write/read maps, fold/deletion
  split, all-operand CCZ checks) make the zeros strictly stronger than
  RESULT3 §2; the two k9 rules that were unsound-as-stated (CCX-a==b
  deletion, CSWAP dead-write) fired 0 times, so no earlier verdict changes.
* Prong-3 irreducibility is a proof sketch over the pinned source
  (triangular exactness + liveness + MBU inapplicability), not a machine
  check; the counts it rests on are measured (k16 totals, k10/k11b
  call-site n=1,184 × 99 T).
* No leaderboard number was produced; the gold-28.65 calibration is
  inherited frontier intel, not measured here.
