# Official cost models, decomposed — where the 5.496 % actually has to come from

Date: 2026-11-17. Scope: read-only source analysis of the unmodified official verifiers
under `data/competition/verifiers/` + arithmetic on the numbers the verifiers already
printed in `pipeline/RESULT_2815083.md`. **No simulation, no verifier runs, no downloads,
nothing submitted.** Reproducible: `intel/cost_model.py` (`python3 cost_model.py`).

Refs throughout R1 = 2076774.233715, R2 = 24439463583672.93, R3 = 3355599588.3155375.
Current best: public **28.15083** (ref 58454232). Gold: **28.68633**.

## 0. Verdict

1. **All three official cost formulas are now transcribed and reproduce our shipped
   scores exactly.** invsqrt residual **0.000e+00**, chemistry residual **0.000e+00**,
   DQI lost-shot draw **348,004,440,260.464** to the digit (clean draw reproduces to
   2.7e-7, the difference being the clean run's own mean T). So the score is fully
   explained by three products of counted quantities — nothing is hidden.
2. **The three legs are structurally different, and only one of them has a factor with
   real headroom:** invsqrt is Toffoli-dominated (`Q·(Toff + T/4)`), DQI is
   **quadratic in width** (`R·Q²·T`), chemistry is a **three-way product**
   (`λ_eff·T·Q`) already pinned at its accuracy corner.
3. **Gold needs, per leg, with the other two held at current best** (product must
   shrink 1.058160×):
   - invsqrt: `C 1699.940 → 1606.506` — i.e. 93.4 C-units, = **12.85 fewer
     non-Clifford rotations** (33 → 20.1) or 6.4 % fewer Toffolis.
   - DQI: `Q²T → /1.058` — i.e. **Q 890 → 865.2 at constant T** (25 qubits) or
     `T 367,120 → 346,942` (−5.50 %).
   - chemistry: `T 14,706 → 13,898` (−808), or `Q 427 → 403.5` (−23.5), or
     `Λ 283.15 → 267.69` (−5.46 %).
4. **The single most favourable of the nine numbers above is the DQI width one**: 25
   qubits, against a **T budget of +5.85 %** at Q865 (the budget is `(890/Q)²−1`;
   at Q888 it is only +0.45 %, which is exactly why our measured 888 build lost).
   Every other route needs a 5.5 % cut in a quantity that our own records have
   already measured at its floor.
5. **A lever that looked free is now provably dead: invsqrt rotation precision.** 14.11 %
   of the invsqrt cost is the 33 non-Clifford rotations at 29.0837 T each
   (`0.56·log2(1/ε)+5.3` with `ε = 1.64e-13`). ε is forced that small because
   `worst_error_over_tolerance = 0.99956` — the circuit leaves essentially no margin,
   and the verifier must spend it on synthesis error. Making ε usefully larger needs a
   ~4e6× larger margin, which is not available; and even one rotation removed is worth
   only 0.428 % of C. **Do not chase this.**

## 1. The formulas

### 1.1 invsqrt — `score = Q · C`, `C = Toffoli + T/4`

`data/competition/verifiers/invsqrt/verify_submission_invsqrt.py:31-41,327`

```
Toffolis  mean Toffoli-like (CCX, CCZ, CSWAP) gates executed per shot
Z_POW     Clifford angles free; T angles 1 T; other angles 0.56*log2(1/eps)+5.3 T each
C         Toffolis + T/4
Q         circuit.num_qubits
score     Q * C
```

Verification (from the shipped JSON: `toffoli_count 1459.3748802688297`,
`t_count 2.499900279707492`, `rotation_count 33`, `rotation_eps 1.64e-13`, `Q 44`):

```
T per rotation = 0.56*log2(1/1.6406e-13) + 5.3 = 29.0837
C = 1459.3749 + (2.4999 + 33*29.0837)/4       = 1699.940122
score = 44 * 1699.940122 = 74797.365357      official 74797.365357   residual 0.000e+00
```

Split: **Toffoli 85.85 %, rotation synthesis 14.11 %.** One rotation = 7.271 C-units
(0.428 % of C).

### 1.2 DQI — `score = R(eps_plus) · Q² · T`

`data/competition/verifiers/dqi/verify_submission_dqi.py:16,420`

```
R(eps) = ln2 / -ln(1/2 + 2*sqrt(eps))     eps = one-sided Clopper-Pearson upper bound
                                          at confidence 1-2^-128 over N shots
Q      circuit.num_qubits                 (contract registers S0..S69 are b=12 wide => 840)
T      mean Toffoli-like gates per shot
score  R(eps_plus) * Q^2 * T
```

Verification: clean CP bound at N = 102,400, δ = 2⁻¹²⁸ is `eps = 8.660587e-04`,
`R = 1.191260465`; with Q = 890, T = 367,120.0042:

```
clean      346,413,486,692   observed 346,413,579,540.4963   residual -9.3e4 (2.7e-7 rel)
1 error    R = 1.196731499  ->  348,004,440,260.464   observed 348,004,440,260.464  exact
```

So the whole "lost shot" penalty is `R` moving from 1.191260 to 1.196731
(= ×1.0045925 on cost, −0.043 GM) — the ledger constant in
`RESULT_public_salt_model.md` is now derived from the official formula, not fitted.

**Width is quadratic.** The contract fixes 70 syndrome registers × 12 bits = **840
qubits**; our decoder uses **890**. That 50-qubit gap alone costs
`(890/840)² = 1.122591`, i.e. **12.26 % of the whole DQI leg** — 2.2× the gold gap.
The catch is the T budget: `T_max(Q) = 367120·(890/Q)²`, so

| Q | 888 | 880 | 870 | 865.2 | 860 | 850 | 840 |
|---|---|---|---|---|---|---|---|
| T budget | +0.45 % | +2.29 % | +4.65 % | **+5.85 %** | +7.10 % | +9.63 % | +12.26 % |
| per qubit shed | 0.226 % | 0.229 % | 0.233 % | **0.235 %** | 0.241 % | 0.245 % | 0.245 % |

The per-qubit budget is **essentially constant at 0.225 %/qubit** — the quadratic term
does not make a large shed cheaper per qubit, it only makes it larger in total. Our
measured 888 build spent 4.3 % T for 2 qubits (2.15 %/qubit), i.e. **9.6× over budget**;
any width route must find a mechanism ~10× cheaper in T than that one.

### 1.3 chemistry — `score = λ_eff · T_total · Q_total`

`data/competition/verifiers/dfthcsos/verify.py:4,53-58,128-139,389-412,470-511`

```
lambda_eff = sqrt(E_gap * (2*Lambda - E_gap))        first factor, from the words we ship
T_total    = angles_toffoli + (outer + inner + givens)_toffoli
Q_total    = persistent + temporary
             persistent = heuristic_persistent + angles_persistent
             temporary  = max(heuristic_temporary, angles_temporary)
score      = lambda_eff * T_total * Q_total
```

Our shipped numbers decompose exactly (`RESULT_2815083.md` §chem JSON):

```
λ_eff = sqrt(3.914898 * (2*283.1458106129289 - 3.914898)) = 46.921716816  (JSON 46.921716818)
T_total = 8,044 (angles) + 6,662 (heuristic: outer 317 + inner 4,095 + givens 2,250) = 14,706
Q_total = 40 (angles persistent = J*brot = 5*8)
        + 40 (outer_state_prep persistent)
        + 44 (inner_state_prep persistent)
        + 303 (temporary = max(303, 77))                        = 427
score   = 46.921716818 * 14706 * 427 = 294,643,137.73357    official 294,643,137.73357  residual 0
```

Note `cost/T = λ_eff · Q_total = 20,035.57308` — exactly the two-point rate measured
from T14,706 and T14,712, which is why chemistry cost is a clean linear function of T.

Constraints that are already tight (`verify.py:118-139` and our JSON):
`ERROR_1_THRESHOLD = ERROR_2_THRESHOLD = 0.020` with observed
`error_2 = 0.0199999997351` (**margin 2.6e-10**), `E_GAP_FLOOR = 3.914898` and our
`E_gap` is at it, `LAMBDA_FLOOR = 49.0` and we are at `Λ = 283.15`, `KEEP_BITS = 10`
fixed by the competition, `QUBIT_CAP = 128` on the loaders and our
`angles_qubits = 128` — **exactly at the cap**. There is no slack in any of them.

## 2. Sensitivity: 1 % of each factor, in GM

Holding the other two legs fixed at 28.15083 (`0af21cb8` / `61c8348d`-clean / `a73b25d2`):

| leg | quantity | 1 % cheaper gives | quantity needed for gold |
|---|---|---|---|
| invsqrt | `C` | +0.094 GM | `C 1699.940 → 1606.506` (−5.496 %) |
| invsqrt | `Q` 44 | +0.094 GM | Q → 41.58 (not a task-legal width) |
| invsqrt | 1 rotation | +0.040 GM | 12.85 rotations (33 → 20.1) |
| DQI | `Q` at fixed T | **+0.189 GM** (squared) | Q 890 → **865.2** |
| DQI | `T` | +0.094 GM | T → 346,942 |
| DQI | `R` (clean) | — | already at the 0-error CP bound |
| chem | `T` | +0.094 GM | T → 13,898 |
| chem | `Q` | +0.094 GM | Q → 403.5 |
| chem | `Λ` | +0.094 GM | Λ 283.15 → 267.69 |

(Check: GM ∝ x^(−1/3), so a 1 % cut in a quantity that enters linearly is +0.0946 GM at
28.15083; a 1 % cut in `Q` for DQI is 1.990 % on cost, hence +0.189 GM.)

DQI `Q` and `T` enter as a product, so they rank together; `Q` is the one with a
contractual target (840) and the one the board proves somebody reached.

## 3. Which route is real, ranked

**① DQI width, Q 890 → 865.2 with T held within +5.85 %.** Only 25 qubits, and the
target is a **contractual integer** (840 = 70 registers × 12 bits); the board itself
shows a competitor at it (rank 9 = 29.21549 ≡ 841.8Q at constant T, or equivalently
T ≈ 328 k at Q890). But the budget is **per qubit**, not per shed: since
`budget(Q) = (890/Q)² − 1`, the slope is a near-constant **0.225 %/qubit** at every Q, so
shedding 25 qubits costs exactly the same 0.225 %/qubit as shedding 2. Our measured 888
build (`dqi/RESULT2.md` §2, cost 360.72e9, **worse**) spent **4.3 % T for 2 qubits =
2.15 %/qubit — 9.6× over budget**. So the question is not "is the budget generous at
Q865" (it is not, it is the same), it is **"does a qubit-shedding mechanism exist that
is ~10× cheaper in T than the one we measured"**. That is the single highest-value
unknown in the project, and it is an architecture question, not a re-scheduling one.

**② chemistry T, 14,706 → 13,898 (−808 T).** Cost is exactly linear in T, all other
factors pinned. But the accuracy corner is at 2.6e-10 margin and `QUBIT_CAP` is exactly
saturated, so this requires a genuinely different word table, not a re-fit. Our R-axis
and C-axis are measured closed (`chem/RESULT2.md`–`RESULT7.md`), and R=5/6 measures
53.65 mHa against a 16.7 mHa gate.

**③ chemistry Λ, 283.15 → 267.69.** `λ_eff` is the first factor and `Λ` is a pure
property of the words we ship, so this is algebraically the cleanest lever — but
`RESULT3.md` §1 measured the λ corner exhausted (rotation sweep 0.0000 % improvement,
gradient accepts no admissible step), and every 1 % of Λ also moves `error_2`, which
has 2.6e-10 of room.

**④ invsqrt.** 85.85 % Toffoli / 14.11 % rotation. Removing all 33 rotations would give
only 14.1 % and is not algorithmically possible; the rotation ε is margin-locked as
shown in §0.5. Needs a new synthesis body (our 0–7 AND ladder is empty, 200/200 and
300/300 positive controls), so it is the most expensive per unit of GM.

## 4. What this means for the 30.96 leader

With the formulas in hand the leader is not mysterious and does not need a
mis-modelled task: `30.96645` is the product of the same three factors.
Taking our invsqrt and chemistry, the needed DQI is
`346,413,501,394 · (28.15083/30.96645)³ = 260.4e9` ⇒ **Q ≈ 771 at constant T**,
below the 840 contract — so the leader cannot be DQI-only. Taking our DQI and
chemistry, invsqrt would need `56,183` ⇒ Q ≈ 33, likewise impossible. Therefore the
leader is **at least two legs**, most plausibly chemistry well below T14,706 plus a DQI
near the 840 floor. Separately, the "no-chemistry wall" computed in
`RESULT_lb_decomp.md` (30.2016 with DQI 840 × invsqrt 40 × chem 14,706) says the same
thing from the other direction: **rank 3 and above must carry a cheaper chemistry.**
