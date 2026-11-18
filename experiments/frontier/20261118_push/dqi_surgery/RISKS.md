# Risk list — normalized-divstep EEA surgery on `575b043f`

Ordered by expected cost of being wrong. R1 and R2 are the two that can kill the 31.4 target;
R4 and R5 are the two that can cost a whole round.

---

## R1 — the leading-coefficient move (normalization). Priced: the whole 15,623 T of slack.

`c = lead(a)/lead(b)` must be one field element so that a step is one row. The three ways and their
measured prices (details in `SPEC.md` §3):

| way | T/step | both passes | mean T | GM | fit? |
|---|---:|---:|---:|---:|---|
| projective / deferred division | 0 | 0 | 249,087 | 32.07 | yes |
| one 12-bit quantum inverse per step (tape idiom, 315 T) | 315 | 43,470 | 292,557 | 30.40 | **no** |
| fraction-free (two rows per step) | 1,470 | 202,860 | 451,947 | 26.29 | **no** |

The slack in the gate is 264,700 − 249,087 = **15,613 T = 113 T per step over 138 steps**. So a
per-step inversion is only affordable if it is amortised 3× (e.g. normalize once every third step by
batching three degree-drops into one composite row) or avoided entirely.

*Mitigation:* the projective form is legal because every consumer of `(σ, ω)` is homogeneous of
degree 0 (`σ(α^{-j}) == 0` test, `e_j = ω/σ'`, and the `popcount(e_j & M_j)` phase are all
scale-invariant). Prove it at `m=63, n=6, degree=4` (see `VERIFY.md` §6) before generating anything
at 4095/70/12.
*Early warning:* if the small-parameter run needs an extra row per step to be correct, stop — the
target is unreachable and the round should be spent elsewhere.

## R2 — window shrink vs left alignment: the budget assumes `len(b)` really drops to 1.

The 35-word average in `69 × 35 × 42` comes from a window that shrinks 69 → 1. If the array is kept
70 words wide with the dead words explicitly zeroed and multiplied anyway, the cost is
`69 × 70 × 42 × 2 = 405,720 T` and GM falls to 26.3 — worse than shipping nothing.

*Mitigation:* the window must be a **compile-time slice**. Since the number of steps is fixed at 69
by `Σδ = 69` (`SPEC.md` §1.1), step *s* always multiplies the first `69 − s` words: no runtime
length is needed, the zero words are simply never touched. This is the same trick the tape's own
Chien uses (a compile-time `j → tested word` map, `INTERFACE.md` §5).
*Second-order effect:* 69 word-drops leave the array rotated by 69 ≡ −1 (mod 70) words. Restoring
the syndrome array to its original positions is a 12-lane rotate = ~2,520 `CX` = **0 T**, and the
tape already demonstrates this exact move (183,037 `CX`, 0 T, `INTERFACE.md` §4). Budget it, do not
"optimise" it away: the tape's contract is that `S0..S69` come back bit-identical.

## R3 — `n_A` / counter semantics: not needed, and that is measurable, not assumed.

Measured on the forward EEA region: **153,185 `CCX`, zero of them conditioned**, `BIT_STORE0` 619,
`BIT_STORE1_IF` 18, and `153,175 = 3,647 × 42 + 1`. The arithmetic has no data-dependent branch —
the schedule is unrolled and fixed. So there is no counter to reproduce: a 69-step divstep with a
compile-time step count is the same class of object.

The counter-looking classical state that *does* exist (`11,591 Z_IF`, `147,153 CZ_IF`, `13,042
HMR`) is phase bookkeeping, 0 T. Do not try to mirror it — the adjoint of the new forward pass
replaces it.

*But note:* the reverse pass is a different matter (§R4). Its `6,441,970 BIT_INVERT_IF` are real
classical work and a naive "reverse = mirror of forward" assumption does not describe the tape.
It describes the *replacement*, which is what we ship.

## R4 — "reverse = forward†" is a design choice, not a description of the tape.

Measured asymmetry between the two passes:

| op | fwd EEA | rev EEA |
|---|---:|---:|
| `BIT_INVERT_IF` | 3,527 | **6,441,970** |
| `BIT_STORE0` | 619 | 166,451 |
| `SWAP` | 58,470 | 226,522 |
| `CZ_IF` | 147,153 | 337,960 |

The tape implements the inverse map twice, differently. Shipping `new_fwd†` is legitimate (the
composite must be the identity and the Chien only sees the state at the cut), but two things follow:

* T-count symmetry is **not** a correctness check — do not use it to validate;
* the reverse pass must undo the *classical* bits too, in reverse order, including any `E` bit the
  forward pass touched. A missed `BIT_STORE` leaves a stale mask and produces value errors only on
  some salts — the worst failure mode to debug.

## R5 — the cut at 30,335,416 is a trap.

The anchor-based boundary sits **inside** the first Chien position: its 10-`CCX` chain is at
30,335,009…30,335,027 and its `E2730` permutation runs to 30,335,415. Splicing there ships a
half-position. Use `P2 = 30,151,421` (last EEA `CCX` at 30,151,420, depth 0) and keep the
183,995-op realignment sweep verbatim.

*Mitigation:* the sweep is 0 T, so there is no temptation to remove it; and `splice.py` will not
catch this (depth is 0 on both sides) — only the Toffoli-count check in `VERIFY.md` §5.2 will
(153,175 vs 153,185 = 10 CCX, a 10-unit mismatch on a budget that closes to 0.006 %).

## R6 — layout reproduction (TODO-1/TODO-2 in `INTERFACE.md` and `SPEC.md`).

Not measured: which coefficient index sits in `word 0` (orientation), which word holds `ω`, and
whether the 42-CCX block multiplies two words of the *same* half (then the Bezout row is free) or one
of each half (then it is a second row and the budget doubles — see `SPEC.md` §2.1 TODO-2).

*Mitigation:* one dump of the first three multiply blocks with `CX` fan-out resolved settles all
three. It is a ~2-minute kernel. Do it **before** writing the generator: TODO-2 changes the T budget
by 2×, which is the difference between 32.08 and 26.3.

## R7 — salt robustness of a 0-Toffoli-control design.

The measured mean T is `HMR`-outcome dependent (the verifier seeds `HMR`/`R`). A replacement that
moves work into `HMR`-conditioned corrections can be cheap on one salt and lose a shot on another
(this exact failure cost a previous candidate 0.043 GM). The divstep's zero-tests and the `δ`
comparison are exactly such `HMR`-conditioned predicates.

*Mitigation:* three salts is the minimum, not a luxury; treat "0/0 on salt 1" as no information.
Keep predicates few and local: the Chien's idiom (10 `HMR` + 10 `CZ_IF` per position, 0 T) is the
template, and it is already salt-stable in the tape.

## R8 — scope creep into the Chien.

The Chien is 46,217 T and was closed twice (`dqi_chien/RESULT.md`: the 10 `CCX` are the quantum root
predicate, not mask redundancy; the `M_j` mask is already 0 T). Do not "fix" it while splicing: any
change there destroys the only measured-stable part of the design.

---

## One-line decision summary

Proceed with the projective divstep only if (a) `m=63, n=6, degree=4` passes 0/0 at three salts
with `T <= 0.6 ×` the reference generator, and (b) the TODO-2 dump shows the Bezout row is the same
42-CCX block, not a second one. If either fails, the lever is closed at ~292k T (GM 30.4) and the
round should go to Q reduction instead.
