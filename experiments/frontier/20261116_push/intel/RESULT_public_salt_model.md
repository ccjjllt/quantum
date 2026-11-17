# Public-salt model: the leaderboard score is a deterministic function of fixed per-file costs — 2026-11-17

Scope: **zero compute**. Local arithmetic over (a) the submission ledger
(`kaggle competitions submissions -c google-verifiable-quantum-circuit-compilation --csv`,
account qingyu1232, read 2026-11-17 ~10:5x local) and (b) costs already recorded in
`intel/RESULT_verify_new{,2,3,4}.md`, `intel/RESULT_stability.md`,
`pipeline/RESULT_2814703.md`, `pipeline/RESULT_2812994.md`, `pipeline/RESULT_2815083.md`.
No simulation, no verifier runs, no downloads, no submission.
Reproducible: `intel/public_salt_model.py` (`python3 public_salt_model.py`).
Refs throughout R1 = 2076774.233715, R2 = 24439463583672.93, R3 = 3355599588.3155375.

## 0. Verdict

1. **The model holds, re-derived independently and with no contradiction.** 11 ledger
   rows invert to a DQI cost that lands within **1.5e-6** of either that file's clean cost
   or clean x 1.0045926 (one lost shot). Separation is 4.59e-3, i.e. ~3000x the
   measurement ambiguity. Four same-file pairs across submissions agree to 5.5e-7 / 1.1e-7 /
   4.6e-7 / 0. **No ratio anywhere is neither ~1.0000000 nor ~1.0045925** — no 2-lost-shot
   file and no second penalty value has ever been observed.
2. **Two DQI legs were already revealed LOST before 58453168 was spent.** `f425ea20`
   (58451475 -> 28.08843) and — decisively — **`b0983d55` itself, whose public cost is
   348,639,035,601.5 = clean x 1.00459254, i.e. LOST**, giving exactly the observed
   28.08701. `61c8348d` is revealed **CLEAN** (58452435 -> 28.14703).
3. **Best known-byte combo: `0af21cb8` + `61c8348d`(public-clean) + `a73b25d2` =
   28.15083075.** It is the argmax under *both* requested models — worst case (a) and
   40%-lost (b) — and it is **already submitted** as ref **58454232**. Because
   `61c8348d`'s public status is revealed CLEAN, that pending score is not an expectation
   but an **exact prediction: 28.15083**.
4. **No known byte can beat it, even under the most optimistic draw assignment.**
   `0af21cb8` / `346,413,579,540.5` / `a73b25d2` are each the minimum known cost in their
   leg, and the best *clean* outcome of every leg not already revealed clean
   (957d 28.14430, f425 28.13517, b098 28.13374, 00ac 28.12529) is below 28.15083. Gold
   28.68633 needs a **5.496% single-leg cut** (invsqrt 70,686.26, or DQI 327,373,473,967,
   or chem 278,448,580) — ~10x the largest DQI step on record, so gold is not reachable by
   recombining known bytes.
5. **`RESULT_stability.md` was wrong because it ranked mismatched draw states.** It priced
   `b0983d55` at its *clean* cost (3/3 clean) and `61c8348d` at its *lost* cost (1/3 clean),
   then read the ranking off as an expectation. The public salt does not care about either
   lab record: `61c8348d` came out CLEAN and `b0983d55` came out LOST, the exact opposite.
   The corrected rule is: **use the revealed public cost when known; otherwise rank on clean
   cost, never on lab clean-frequency.** On that rule `b0983d55` was *strictly dominated
   before the slot was spent* — even clean it lands 0.01709 GM behind `61c8348d`.

---

## 1. The model

### 1.1 Shape and the one non-deterministic leg

`GM = (R1/ci * R2/cd * R3/cc)^(1/3)`, solved for the DQI leg:

```
cd = R1*R2*R3 / (GM^3 * ci * cc)
```

- `ci` (invsqrt) and `cc` (chem) are **salt-invariant** — verified identical to all digits
  across the default salt and two extra salts (`RESULT_verify_new` §0/§3,
  `RESULT_verify_new2` §0/§3, `RESULT_verify_new4` §0/§3). Their public cost therefore
  equals their verified cost, full stop.
- `cd` (DQI) is **draw-dependent in the lab but fixed in public**: the hidden public salt
  selects one shot-realisation of the file, and that realisation is the same every time
  the file is graded. So each DQI file carries one *fixed* hidden constant, either its
  clean cost or clean x rho.

### 1.2 What rho is, exactly

The DQI score is `const * mean_toffoli_count * repetition_factor`, confirmed to 10 dp:

| file | score ratio lost/clean (observed) | rho x (T_lost/T_clean) | T ratio |
|---|---|---|---|
| `61c8348d` | 1.0045923740 | 1.0045923740 | 0.9999997320 |
| `f425ea20` | 1.0045922726 | 1.0045922726 | 0.9999996310 |
| `957d6733` | 1.0045934095 | 1.0045934095 | 1.0000007628 |

with `rho = R(1 err)/R(0 err) = 1.1967314991687559 / 1.1912604648115832 =
` **1.0045926433**.

Consequence that matters for the rest of this note: **the lost-shot ratio is not exactly
1.0045925 for every file/salt.** `mean_T` itself wobbles between salts by up to 7.6e-7
relative (observed: `957d6733` clean-vs-lost T ratio 1.00000076). So the operative statement is

> public cost is `clean x 1.0000000` or `clean x 1.0045926`, each **+/- ~1.0e-6**.

A 2-error draw would be `rho^2 = 1.0092064` (GM -0.086). **Never observed** — see §4.

### 1.3 Precision budget (why the clean/lost call is safe)

| source | effect on implied `cd` |
|---|---|
| public GM published to 5 dp | +/- 3 x 0.5e-5/GM = **+/- 5.4e-7** rel |
| per-salt `mean_T` wobble | **+/- ~1.0e-6** rel |
| legacy ledger legs recorded at 2 dp (74,797.37 etc.) | +<= 7e-8 rel |
| **total ambiguity** | **+/- ~1.5e-6 rel** |
| clean vs lost separation | **4.59e-3 rel = ~3000x ambiguity** |

At `cd ~ 3.47e11` the ambiguity is ~5e5 absolute; one lost shot is 1.6e9.

---

## 2. Proof set (re-derived, not copied)

`A` below is the inverse solve with each row's *other two* legs as recorded in that row's
own description. If the public cost were a fresh per-submission random draw, the two rows
of a pair would agree only when both drew the same realisation *and* the same `mean_T`.

| # | file | submission A | submission B | leg that differs | implied `cd` A | implied `cd` B | disagreement |
|---|---|---|---|---|---|---|---|
| 1 | `ccc2ab84` | 58420406 (`8b410e77` + `f6e12f02`) | 58424363 (`f2cdab0b` + `sub1`) | **invsqrt AND chem** | 347,375,773,909.6 | 347,375,963,170.6 | **5.5e-7** |
| 2 | `66b4f18b` | 58442668 (`0af21cb8`) | 58436763 (`f2cdab0b`) | invsqrt | 347,128,411,781.4 | 347,128,375,432.2 | **1.1e-7** |
| 3 | `821bf8d1` | 58382097 (chem `v119`) | 58350759 (chem `4033`) | chem | — | — | implied chem ratio 0.99961785 vs recorded 0.99961831, **4.6e-7** |
| 4 | `e9` trio | 58190972 (self-built zip) | 58181743 (upstream zip) | *nothing* (same three circuit bytes) | 25.22676 | 25.22676 | **0** |

Pair 3 is a genuine test even though it does not isolate `cd`: two submissions share both
`invsqrt` and DQI, so their GM ratio must equal `(cc_B/cc_A)^(1/3)` if and only if neither
the DQI nor the invsqrt cost moved. It matches the recorded chem ratio to 4.6e-7.

Pair 4 is the semantic anchor: Kaggle code-competition grading is a deterministic function
of the submitted artefacts, so two zips carrying the same three circuit files must score
identically — and they do, to 5 dp, which is tighter than the `mean_T` wobble would allow
if the salt were resampled.

**Result: 11/11 inverted rows are consistent, 0 contradictions.** The residual spread
across all 11 rows is <= 1.5e-6, which is the measurement floor of a 5-dp GM.

---

## 3. Task 1 — every ledger row, inverted

### 3.1 Invertible rows (invsqrt and chem costs both recorded)

`dGM` = public GM minus the GM the same trio would score at the **lab-recorded** DQI cost.
`dGM ~ 0` => the public salt drew the same realisations the lab did; `dGM ~ -0.043` => the
public salt drew a lost shot the lab did not.

| ref | DQI | public GM | GM at lab cost | dGM | implied public `cd` | ratio vs lab cost | class |
|---|---:|---:|---:|---:|---:|---:|---|
| 58453168 | `b0983d55` | 28.08701 | 28.12994 | **-0.04293** | 348,639,035,601.5 | 1.00459254 | **LOST** |
| 58452435 | `61c8348d` | 28.14703 | 28.14703 | +0.00000 | 346,413,501,394.4 | 0.99999977 | **CLEAN** |
| 58451475 | `f425ea20` | 28.08843 | 28.13137 | **-0.04294** | 348,586,162,329.2 | 1.00459332 | **LOST** |
| 58442668 | `66b4f18b` | 28.12769 | 28.12769 | -0.00000 | 347,128,411,781.4 | 1.00000031 | **CLEAN** |
| 58436763 | `66b4f18b` | 28.10154 | 28.10154 | -0.00000 | 347,128,375,432.2 | 1.00000021 | **CLEAN** |
| 58424363 | `ccc2ab84` | 28.09486 | 28.09487 | -0.00001 | 347,375,963,170.6 | 1.00000142 | **CLEAN** |
| 58420406 | `ccc2ab84` | 28.09090 | 28.09091 | -0.00001 | 347,375,773,909.6 | 1.00000087 | **CLEAN** |
| 58410043 | `4b350932` | 28.07502 | 28.07503 | -0.00001 | 347,760,915,214.4 | 1.00000059 | **CLEAN** |
| 58392219 | `46446af1` | 28.05896 | 28.05896 | -0.00000 | 347,904,390,448.7 | 1.00000047 | **CLEAN** |
| 58228252 | `9fcda0c1` | 25.30340 | 25.30339 | +0.00001 | 374,684,771,340.9 | 0.99999937 | **CLEAN** |
| 58190972 | `e9` | 25.22676 | 25.18827 | **+0.03849** | 374,687,053,099.6 | 0.99542943 | **LOST-lab -> CLEAN public** |

Legs used (recorded in each row's own description): `8b410e77` 75,038.134 /
`f2cdab0b` 75,006.37653863191 / `2c125b39` 75,082.09 / `47b31838` 75,170.62 /
`a15b0d73` 93,925.35 / `26ebf39d` 94,537.59; chems `f6e12f02` 294,762,732.9775791 /
`sub1` 294,762,697.43843937 / `bdae290f` 294,762,632.0817748 / `881d9dae` 294,763,525.68 /
`marculera6` 294,800,582.44 / `maoxin303` 298,720,881.30 / `79f790fa` 299,497,670.48.

Three readings worth keeping:

- **`e9` is the mirror image of `b0983d55`.** Its ledger cost (376,407,450,170) is the
  *lost* draw; the public inversion gives 374,687,053,099.6 = recorded/rho to 1.1e-6. So a
  file the lab saw fail, the public salt saw clean. Lab and public draws are independent.
- **58392219 is an independent calibration of rho on a third file.** The publisher reported
  "28.059 default, 28.016 on the two salts with one failed DQI shot"; the inversion gives
  `cd(46446af1) = 347,904,390,448.7` (x 1.0000005 vs the recorded 347,904,227,556), and
  the GM at `cd x rho` is **28.01614** vs the reported 28.016. Clean.
- The three pre-frontier DQI data points requested (347,904,227,556 / 374,685,006,336 /
  376,407,450,170) resolve to **CLEAN / CLEAN / LOST-lab** respectively. They add no new
  penalty value — they only widen the clean population.

### 3.2 Rows with identifiable hashes that cannot be inverted

Two of the three costs were never recorded numerically, so no `cd` can be extracted. These
are **not** model failures; they are missing data.

| ref | DQI | public GM | why not invertible |
|---|---:|---:|---|
| 58382097 | `821bf8d1` | 27.31541 | `ci(1ba197b0)` never recorded numerically |
| 58350759 | `821bf8d1` | 27.31193 | same; chem 294,991,455.82 recoverable only from the A/B pair |
| 58349843 | `821bf8d1` | 27.30661 | two costs unknown |
| 58299045 | `7cbe8ecf` | 27.00209 | 46Q family, no costs recorded |
| 58290992 | `392k-swap` | 25.44039 | chem never recorded numerically |
| 58271862 | `eae396ba` | 25.40482 | chem never recorded numerically |
| 58265561 | `eae396ba` | 25.39570 | `ci` never recorded numerically |
| 58256166 | `cd71c482` | 25.38868 | `cd` never recorded numerically |
| 58239559 | `cd71c482` | 25.36085 | `ci` never recorded numerically |
| 58235797 | `cd71c482` | 25.33133 | `ci` and `cc` never recorded — see note |
| 58222873 | (Ozertuu portfolio) | 25.29661 | no per-file costs |
| 58181743 | `e9` | 25.22676 | upstream zip; same bytes as 58190972 |
| 58123354 | `4432ec5f` | 25.14222 | no costs |
| 58041132 / 58014726 / 57980157 / 57876561 / 57808271 | — | 24.94081 / 24.78590 / 24.54651 / 23.83790 / 23.00037 | no hashes in the ledger |

> **Caution on 58235797 vs 58239559.** Same invsqrt (`6c6a734d`), same DQI (`cd71c482`),
> same loader-table name (`8afd4c67`) — yet public 25.33133 vs 25.36085. This is *not* a
> determinism violation: `8afd4c67` is the **loader table**, not the chem npz hash, and the
> two rows used different chem weights (Grimoire33 vs Maoxin v22). The pair inverts to
> `cc(58235797) = 297,558,526.59 x (25.36085/25.33133)^3 = ` **~298.6e6**, i.e. a worse
> chem that was later upgraded. A same-file pair must use the *npz* hash, not the loader
> name.

---

## 4. Task 2 — definitive per-file table

`clean` = the lab 0-error cost. `public` = the inverted hidden constant. `ratio` =
public/clean. `class` threshold +/-1.5e-6 (§1.3).

| DQI file | clean cost (lab) | **public cost** | ratio | **status** |
|---|---:|---:|---:|---|
| `61c8348d` | 346,413,579,540.5 | 346,413,501,394.4 | 0.99999977 | **CLEAN** |
| `957d6733` | 346,654,523,463.5 | *unrevealed* | — | **?** |
| `f425ea20` | 346,992,317,312.8 | 348,586,162,329.2 | 1.00459332 | **LOST** |
| `b0983d55` | 347,045,216,047.3 | 348,639,035,601.5 | 1.00459254 | **LOST** |
| `66b4f18b` | 347,128,304,010.8 | 347,128,411,781.4 | 1.00000031 | **CLEAN** |
| `00ac37d4` | 347,357,914,647.0 | *unrevealed* | — | **?** |
| `ccc2ab84` | 347,375,470,571.7 | 347,375,963,170.6 | 1.00000142 | **CLEAN** |
| `4b350932` | 347,760,709,936.5 | 347,760,915,214.4 | 1.00000059 | **CLEAN** |
| `46446af1` | 347,904,227,556.0 | 347,904,390,448.7 | 1.00000047 | **CLEAN** |
| `9fcda0c1` | 374,685,006,336.0 | 374,684,771,340.9 | 0.99999937 | **CLEAN** |
| `e9` | 374,686,648,057.2 | 374,687,053,099.6 | 1.00000108 | **CLEAN** |
| `821bf8d1` | not recorded | fixed across 3 submissions, class unknown | — | **?** |

**Anomaly scan: none.** No ratio falls outside `{1 +/- 1.5e-6}` ∪ `{1.0045926 +/- 1.5e-6}`
∪ `{0.9954281 +/- 1.5e-6}`. In particular:

- **No 2-lost-shot file.** `rho^2 = 1.0092064` would show as a GM 0.086 below clean, four
  times the one-shot signature, and nothing in the 25.2-28.15 history shows it.
- **No alternative penalty.** Every lost observation is the same `R(1)/R(0)` to 1e-6, on
  four different files (`61c8348d`, `f425ea20`, `957d6733`, `b0983d55`) plus the
  publisher's `46446af1` report. The penalty is a property of the verifier, not the file.

**Revealed public tally: 7 CLEAN / 2 LOST / 0 double-lost over 9 distinct files.**
That implies per-draw `P(clean) ~ 0.78`, `P(1 error) ~ 0.19`, `P(2+ errors) <~ 0.03`,
equivalently a per-file Poisson rate `lambda ~ -ln(7/9) ~ 0.25` per 102,400-shot grading.
This is the only defensible base rate — see §7.3.

**Lab-vs-public concordance is 7/9, which is exactly what independence predicts.** Two
independent draws from a 78%-clean population agree with probability
`0.78^2 + 0.22^2 = 0.657`; the two disagreements are precisely the informative cases
(`b0983d55` 3/3-clean -> LOST, `e9` lost-lab -> CLEAN). There is **no evidence that a lab
draw tells you anything about the public draw.**

---

## 5. Task 3 — every candidate combo under both models

Fixed legs: `0af21cb8` (74,797.36535717871) and `a73b25d2` (294,643,137.73357135).
No known invsqrt is cheaper than `0af21cb8` (next: `f2cdab0b` 75,006.38; `5eeea23b`
75,006.40; `8b410e77` 75,038.13; `2c125b39` 75,082.09; `47b31838` 75,170.62).
Chem alternatives move the GM by at most 3.8e-3 and never reorder the DQI legs (§5.2), so
a 7x4 matrix collapses to the 7 rows below.

**Model definitions used here** — this is the part that `RESULT_stability.md` got wrong, so
be precise:

- **(a) worst case.** Every DQI leg with a **revealed** public cost uses that exact cost (no
  randomness remains — it is a constant). Every **unrevealed** leg is priced at
  `clean x rho`.
- **(b) 40%-lost expectation.** Revealed legs again use their exact revealed cost
  (a 40% prior is meaningless once the outcome is known). Unrevealed legs use
  `E[cd] = 0.6 clean + 0.4 clean x rho`, plus the exact `E[GM] = 0.6 GM_clean + 0.4 GM_lost`
  (GM is concave in `cd`, so `E[GM] > GM(E[cd])` by ~3e-5).

| DQI | status | cd under (a) | **GM (a)** | cd under (b) | **GM (b)** | E[GM] (b) | if it were CLEAN |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`61c8348d`** | **CLEAN** | 346,413,501,394 | **28.15083** | 346,413,501,394 | **28.15083** | **28.15083** | 28.15083 |
| `957d6733` | unknown | 348,246,584,028 | 28.10135 | 347,291,347,689 | 28.12709 | 28.12712 | 28.14430 |
| `66b4f18b` | CLEAN | 347,128,411,781 | 28.13149 | 347,128,411,781 | 28.13149 | 28.13149 | 28.13149 |
| `ccc2ab84` | CLEAN | 347,375,963,171 | 28.12481 | 347,375,963,171 | 28.12481 | 28.12481 | 28.12482 |
| `00ac37d4` | unknown | 348,953,205,636 | 28.08237 | 347,996,031,043 | 28.10809 | 28.10812 | 28.12529 |
| `f425ea20` | LOST | 348,586,162,329 | 28.09222 | 348,586,162,329 | 28.09222 | 28.09222 | 28.13517 |
| `b0983d55` | LOST | 348,639,035,602 | 28.09080 | 348,639,035,602 | 28.09080 | 28.09080 | 28.13374 |

- **Best under (a): `61c8348d` at 28.15083.**
- **Best under (b): `61c8348d` at 28.15083.**
- Second under both: `66b4f18b` at 28.13149 (it is revealed CLEAN, so it is also exact).

Sensitivity: applying the 40% prior to *all* legs including the revealed ones still leaves
`61c8348d` first (`E[GM] = 0.6 x 28.15083 + 0.4 x 28.10786 = 28.13364` vs
`66b4f18b` 28.13149 — a 0.0022 margin, because `66b4f18b` is a genuinely weak clean leg).
The only way to promote another leg is to assume `61c8348d` is lost, which the ledger
contradicts. Note this sensitivity is hypothetical only: 58452435 already fixed the answer.

### 5.1 The selected combo is already in flight

Ref **58454232** (`0af21cb8` + `61c8348d` + `a73b25d2`) is exactly this combo and is
**PENDING** in the ledger. Because `61c8348d`'s public constant is revealed CLEAN by
58452435, its score is **deterministic: 28.15083075 -> displays 28.15083**. Not an
expectation, not a resample: the same DQI constant, a cheaper chem, `+0.00380` over the
28.14703 currently on the board.

### 5.2 Chem sub-ranking (on `0af` + `61c8348d`-public-clean, exact)

| chem | cost | GM |
|---|---:|---:|
| **`a73b25d2`** | 294,643,137.7336 | **28.15083** |
| `93326853` | 294,762,512.6435 | 28.14703 |
| `bdae290f` | 294,762,632.0818 | 28.14703 |
| `sub1` | 294,762,697.4384 | 28.14702 |
| `f6e12f02` | 294,762,732.9776 | 28.14702 |

`a73b25d2` is worth +0.00380; the other four are within 7e-6 of each other and irrelevant
for slot decisions. Note the pairing constraint: `a73b25d2` requires the 15 **SMALL**
loaders (T 14,706, depth 177, ops 224,256), not the standard 14,712 family.

---

## 6. Task 4 — ceiling and the gold gap

### 6.1 Can any known byte beat the current best?

**No.** 28.15083 is the exact maximum over the known byte set:

| leg | min known cost | file |
|---|---:|---|
| invsqrt | **74,797.36535717871** | `0af21cb8` |
| DQI | **346,413,501,394.4** (revealed public) | `61c8348d` |
| chem | **294,643,137.73357135** | `a73b25d2` |

GM is strictly decreasing in each leg, so the product of per-leg minima is the ceiling.
And the ceiling survives every optimistic draw assignment: the best *clean* outcome of every
leg not already revealed clean is 957d 28.14430, f425 28.13517, b098 28.13374,
66b4 28.13149, 00ac 28.12529 — all below 28.15083. The gap to the runner-up with a
*revealed* cost is 0.01934, and to the best hypothetical clean draw 0.00653.

Consequently: **58454232 will set the new public best at 28.15083**, and no re-ship of any
known byte can improve on it. The only remaining lever over known bytes is `957d6733`
*if* its unrevealed constant were clean — but even then it lands at 28.14430, i.e. 0.00653
**below** what is already pending. **The byte inventory is exhausted.**

### 6.2 What it would take to reach gold 28.68633

Held at the current best, GM must rise by 0.53550; since GM is the cube root of the
reciprocal cost product, **the cost product must shrink 5.816%**, i.e. one leg must be
divided by **1.058160 (-5.496%)**:

| leg | required cost | current | required cut |
|---|---:|---:|---:|
| invsqrt | **70,686.256** | 74,797.365 | -5.496% |
| DQI | **327,373,473,967.0** | 346,413,501,394.4 | -5.496% |
| chem | **278,448,580.1** | 294,643,137.7 | -5.496% |

Or, spread evenly, **-1.867% on all three** (each divided by 1.019023).

Calibration against what is actually achievable:

- The required DQI cut is **20,215 mean-Toffoli off 367,789**. The largest DQI improvement
  on record is the 11-13 "392k swap" at -0.526% T — **10.4x short**. The whole 28.09 ->
  28.15 frontier advance was ~0.2%.
- The required invsqrt cut is ~4,111 cost units; the entire 44Q line has moved from
  75,170.62 to 74,797.37 (-0.50%) across the whole push.
- The required chem cut is 16.2e6 (5.5%); the best chem refit in this push was 0.04%
  (`a73b25d2` vs `703843d3`).

**Conclusion: gold is not reachable by recombination or by tuning known bytes.** It needs a
genuinely new circuit class (-5.5% on one leg), consistent with `RESULT_topline.md`'s
independent gold calibration.

---

## 7. Task 5 — correcting `RESULT_stability.md`

### 7.1 What it said, and what happened

`RESULT_stability.md` §0.2/§0.4/§5 recommended **SUBMIT `0af21cb8` + `b0983d55` +
`93326853`**, on the grounds that `b0983d55` was "the sole 3/3-clean DQI leg",
"E[GM] = 28.12993954", "worst-verified floor 28.12992985 still above every other leg's
expectation". That became ref **58453168**, submitted 02:43:35, which read back
**28.08701**.

The ledger inversion says the public constant of `b0983d55` is
**348,639,035,601.5 = clean x 1.00459254** — a lost shot — and the forward GM at that
constant is **28.08701 exactly**, to all five published digits. The prediction failed by
0.04293 because the leg drew the outcome with probability ~0.2.

### 7.2 Why the reasoning was wrong — three separable errors

**(i) It ranked mismatched draw states.** §3(a) of that file ranks by "default-draw GM".
For `61c8348d` the lab default draw *was* the lost draw (28.10407), while for `b0983d55`
it was a clean draw (28.12994). So the comparison set `61c8348d`'s bad draw against
`b0983d55`'s good draw and concluded `b0983d55` was better. The correct same-state
comparison is clean-vs-clean:

| file | clean cost | GM with `a73b25d2` |
|---|---:|---:|
| `61c8348d` | 346,413,579,540.5 | **28.15083** |
| `b0983d55` | 347,045,216,047.3 | 28.13374 |

`61c8348d` wins by 0.01709 *before any draw occurs*. Its clean cost is 0.1824% lower.

**(ii) It treated the lab clean-frequency as the public probability.** `E[GM]` was computed
as the mean over the file's own lab draws. But the public salt is one fixed constant, drawn
independently of the lab. Three clean lab draws say almost nothing: under the empirical
public rate (§4) the posterior for a 3/3 file is P(public clean) ~ 0.83, and even taking
that prior seriously:

```
E[b0983d55 | 3/3] = 0.833 x 28.13374 + 0.167 x 28.09081 = 28.12658
E[61c8348d | 1/3] = 0.667 x 28.15083 + 0.333 x 28.08701 = 28.13651
```

`61c8348d` still wins by 0.0099 — and once 58452435's readback revealed `61c8348d` CLEAN,
by **0.0243** with no uncertainty left. The "3/3 clean" property was never worth the 0.0171
GM it was asked to pay for.

**(iii) It called a lab floor a bound.** "Worst-verified floor 28.12992985" is the minimum
over the file's *lab* draws. It bounds nothing about the public salt; the true worst case
was the 1-error cost, 28.08701. A three-sample floor cannot exclude anything.

### 7.3 Corrected selection rule

> **R1. Sort by revealed public cost first.** Once a file's constant is on the board, it is
> a known number. Use it. Never re-derive it from lab draws, never average it with anything.
>
> **R2. Among unrevealed candidates, sort by clean cost — full stop.** The public draw is a
> lottery the submitter cannot influence and the lab cannot predict. The only quantity lab
> work can actually improve is the clean cost. Lab clean-frequency is not a tiebreaker.
>
> **R3. Never spend a slot on a leg that is dominated in the best case.** If
> `clean_cost(candidate) > public_cost(current_best)`, the candidate cannot win even if it
> draws clean, so the slot buys information at best, never score. Submit only when the
> candidate's *clean* cost beats the incumbent's *revealed* cost.
>
> **R4. Price the residual risk at the population rate, not the file rate.** For prediction
> intervals on unrevealed legs use the empirical public draw distribution
> (7 clean / 2 one-error / 0 double over 9 files; `P(clean) ~ 0.78`, `P(1 error) ~ 0.19`,
> `P(2+ errors) <~ 0.03`, cost penalties `rho = 1.0045926` and `rho^2 = 1.0092064`).
> A per-file k/n from three draws carries a standard error of ~0.3 and must not be used as
> a probability.
>
> **R5. The ceiling test comes before the slot decision.** Compute
> `max over known bytes = GM(min ci, min revealed cd, min cc)`. If it equals the combo
> already pending, the correct action is HOLD, and the only remaining work is new bytes.

### 7.4 Replaying the last four slots against the rule

| ref | when | DQI used | what R1-R3 say | verdict |
|---|---|---|---|---|
| 58451475 | 01:36 | `f425ea20` | lowest clean cost among *independently verified* files at the time (346.992e9); it drew LOST | **correct process, bad luck** (28.08843) |
| 58452435 | 02:13 | `61c8348d` | lowest clean cost of any then-known file (346.414e9) | **correct** -> 28.14703, new public best |
| 58453168 | 02:43 | `b0983d55` | clean 347.045e9 > `61c8348d`'s revealed 346.414e9; dominated even if clean; nothing better than the already-submitted 58452435 existed | **should have been a HOLD** -> 28.08701 |
| 58454232 | 03:23 | `61c8348d` | ceiling combo with the newly-verified cheapest chem | **correct** -> 28.15083 exact |

The pipeline's judgement was right on every slot until the stability memo swapped the
criterion from clean cost to lab clean-rate. Note also that with `a73b25d2` verified only at
02:47, the 02:43 slot had no better content available than 58452435's bytes — so the memo
did not merely pick the wrong DQI, it spent a slot where the correct answer was *no
submission*.

---

## 8. Reproduction and open items

Reproduce everything with `python3 intel/public_salt_model.py` (pure arithmetic, ~0.05 s,
no I/O beyond stdout). All inputs are quoted in §3.1 and §5; no cost in this note is
estimated.

Open items that would change predictions:

1. **`957d6733` and `00ac37d4` public constants are unrevealed.** Both clean costs
   (346.655e9, 347.358e9) are above `61c8348d`'s revealed 346.414e9, so neither can win.
   No slot should be spent on them.
2. **`821bf8d1` is fixed but unclassified** — its clean cost was never recorded. Three
   submissions agree on it (proof 3), so the constant is established; only the label is
   missing. It is far above the frontier (370e9-class) and irrelevant.
3. **No double-lost draw has ever been observed.** If one occurs on a frontier file the GM
   drops ~0.086, twice the familiar -0.043. Prediction intervals should carry that tail
   (`P <~ 3%` per grading at the empirical rate).
4. **58454232 is the last pending datum of interest.** It is predicted exactly
   (28.15083). If it reads back anything else, the salt model as stated is wrong and this
   note should be withdrawn — that would be the single cleanest falsification test
   available, since the same DQI constant already produced 28.14703 in 58452435.

No submission was made and no slot was spent by this task.
