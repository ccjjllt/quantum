# DQI width: the exchange rate, and why every reachable shed loses

Date: 2026-11-17. Scope: arithmetic against the official cost formula
`score = R(eps_plus)·Q²·T` (`data/competition/verifiers/dqi/verify_submission_dqi.py:16,420`,
transcribed and validated to residual 0 in `intel/RESULT_cost_model.md` / `intel/cost_model.py`),
applied to the shipped tape `61c8348d` (Q=890, mean T=367,120.004, R=1.1912605, official
clean cost 346,413,579,540.50) and to the mechanism costs measured in `dqi/RESULT.md`
§3/§3b and `dqi/RESULT2.md` §2. **No simulation, no verifier runs, no submission.**
Reproducible: `python3 dqi/width_budget.py`.

Refs R1 = 2076774.233715, R2 = 24439463583672.93, R3 = 3355599588.3155375. Best combo
28.15083 (ref 58454232). Gold 28.68633.

## 0. Verdict

1. **Width is a quadratic term, so the price of a qubit is fully determined:**
   `dcost/cost = 2·dQ/Q`. Shedding `k` qubits buys `1 − ((890−k)/890)²` of cost, and the
   T allowance is the same quantity. Break-even therefore rises slowly with `k`:

   | k shed | Q | cost gain | break-even T allowance | per qubit |
   |---:|---:|---:|---:|---:|
   | 1 | 889 | 0.225 % | +826 T | 826 |
   | 5 | 885 | 1.120 % | +4,160 T | 832 |
   | 10 | 880 | 2.235 % | +8,391 T | 839 |
   | 20 | 870 | 4.441 % | +17,073 T | 854 |
   | 25 | 865 | 5.540 % | +21,527 T | 861 |
   | 26 | 864 | 5.752 % | +22,428 T | 863 |
   | 50 | 840 | 10.933 % | +45,005 T | 900 |

2. **Gold is not a width problem, it is a T-neutrality problem.** Because 865Q with *flat*
   T already scores 28.69066 (gold + 0.0043), the gold T allowance collapses to almost
   nothing at every partial shed:

   | Q | free-T GM | T allowance for gold 28.68633 |
   |---:|---:|---:|
   | 889 | 28.17194 | −5.284 % (impossible) |
   | 880 | 28.36369 | −3.336 % (impossible) |
   | 870 | 28.58062 | −1.101 % (impossible) |
   | **865** | **28.69066** | **+0.045 % (166 T total)** |
   | 864 | 28.71279 | +0.277 % (1,017 T) |
   | **840** | **29.25713** | **+6.089 % (22,354 T)** |

   So there are exactly two gold-capable width moves: **Q865 at +166 T** (T-flat, i.e. a
   pure relabelling — which `RESULT.md` §3 proved impossible: `FREE_SHRINK_IF_RENUMBERED 0`),
   or **Q840 at +22,354 T**. Everything in between is dead on arrival.

3. **Every measured mechanism is far outside both.** `RESULT.md` §3 gives the cheapest
   possible release of the cheapest pool wire (`q864`) as **≥925 T for one CCX per plateau
   episode** (925 episodes), realistically **≥7,195 T**; and `RESULT2.md` §2 measured the
   888 build at **15,864 T for 2 qubits = 7,932 T/qubit**.

   | mechanism | T/qubit | vs break-even at Q865 (861) | vs gold at Q865 (6.6) |
   |---|---:|---:|---:|
   | optimistic bound (`q864`, 1 CCX/episode) | 925 | 7.4 % over | **140× over** |
   | realistic bound (`q864`, 1 CCX/product) | 7,195 | 8.4× over | 1,090× over |
   | measured 888 build | 7,932 | 9.2× over | 1,200× over |
   | needed for gold at Q865 | 6.6 | — | — |

4. **Therefore the width line is arithmetically closed for this tape, on a stronger basis
   than `RESULT.md` §0's "closed for this tape".** It is not that no mechanism was found:
   *any* mechanism costing ≥861 T/qubit cannot even improve on 28.15083, and *any* mechanism
   costing ≥6.6 T/qubit cannot reach gold at Q865. The only surviving form is the full
   in-place 840Q decoder with a **+6.09 % T budget (22,354 T)**, whose blocked ingredient is
   already identified in `RESULT.md` §3b: the 24-bit carry bank `q840..q863` is a permanent
   accumulator touched inside 62–72 % of helper windows, so it cannot be borrowed.

## 1. Where the 890 comes from (recap of the measured structure)

`890 = 840 + 4×12 + 2`: the 840 contract qubits (70 syndrome registers × 12 bits), **four**
12-bit working words, and two flags. `RESULT.md` §3 measures: HMR-delimited peak 50,
`peak_without = 890` for each of the 50 taken alone, 3.59 M ops (6.1 % of the tape) at width
890 across 925 episodes, no droppable wire, no retention wire, and no qubit idle inside an
episode. So the pool is genuine simultaneity, not sloppy allocation — a relabelling cannot
help, which is exactly what makes the marginal mechanism expensive.

## 2. What would have to be true for the width line to pay

Only one statement is worth carrying forward:

> A gold-capable DQI width move exists iff there is an in-place (840Q) decoder formulation
> whose mean Toffoli-like count stays ≤ 389,474 (+6.09 %, i.e. **447 T per qubit shed**),
> which is **2.07× below** the optimistic mechanism bound (925) and **17.7× below** the
> measured 888 build (7,932). It must fold four 12-bit working words into the syndrome
> registers themselves with essentially no recomputation.

`RESULT2.md` §0 already records that classicalising the 1-bit predicates reaches 888 (+4.3 %
T) and that "Q = 864–865 is unreachable from this architecture" — so the 840Q target needs the
v13→v15 generation change, not a patch. The budget for that change is **+22,354 T**, and the
only measured partial step toward it spent **15,864 T for 2 qubits**. Nothing in our records
shows a mechanism within 100× of the required exchange rate, so this line should not be
reopened without a genuinely new in-place formulation (i.e. an algorithmic idea, not a
resynthesis).

## 3. Consequence for the overall frontier

With this note the three legs are all closed by measurement *and* by arithmetic:

| leg | why it is closed |
|---|---|
| invsqrt | `C = Toffoli + T/4`; Toffoli surface scraped (0 cancel pairs, 0 zero-controls), 33 rotations cost 29.08 T each only because `worst_error_over_tolerance = 0.99956` leaves no synthesis margin (`intel/RESULT_cost_model.md` §0.5) |
| DQI | this note: every reachable shed is ≥925 T/qubit against a 6.6 T/qubit gold budget at Q865; 840Q needs +6.09 % T and the carry bank cannot be borrowed |
| chemistry | `λ_eff·T·Q` with `error_2` margin 2.6e-10, `E_gap` at its floor, loaders exactly at `QUBIT_CAP = 128`, R/C axes measured closed |

So **28.15083 is the ceiling of (public bytes) × (three measured-floor legs)**, and gold
28.68633 requires a new circuit generation on one of them. That is a research decision, not a
compute decision.
