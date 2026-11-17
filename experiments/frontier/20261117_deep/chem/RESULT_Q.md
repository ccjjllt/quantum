# RESULT — the Q axis of the chemistry leg (`λ_eff·T·Q`)

Date: 2026-11-17. Chemistry (`dfthcsos`) only.

**Everything here is closed-form arithmetic on the verifier's own cost module**
(`data/competition/verifiers/dfthcsos/scoreinfra/costs_prepare.py`,
`SpinFreeData_V1`, numpy only) plus the stored `artifacts/H_spectrum.npy` (2,926
eigenvalues) and the shipped `submission.npz`. No integrals were read, no
`kickmix` import, no circuit, no simulation, **no verifier run, no local
simulation, no Kaggle push, no submission**. Reproduce with
`experiments/frontier/20261117_deep/chem/Q_AXIS/main.py` (log: `Q_AXIS/run.log`).

Baseline: `a73b25d2`, **Q = 427, T = 14,706** (8,044 angle + 6,662 heuristic),
λ_eff = 46.921716818, cost **294,643,137.73**, gold needs ≤ 277,662,014.70.

## 0. Verdict

1. **The k2 = 3 lead is provably blocked, and not narrowly.** `inner_temp` is
   **not** `31·(2k2−1)+18+6`; the `(2^k2−1)` factor multiplies `b2 = ceil(log2 B)+11`,
   not 31. The real k2 = 3 value would be `152`, giving **Q = 276** (cost 190.45 M,
   GM 32.56) — the prize is real, the reach is not. k2 = 3 requires the k2 = 4
   candidate to *overflow* the model's ancilla bound, which needs
   `15·b2 + ceil(log2(RC·B/16)) ≥ 75·brot`. At the only brot the accuracy gates
   allow (brot = 8) that means **B ≥ 67,108,865**, i.e. rows ≈ 5.4·10⁸ and
   T ≈ 3.5·10⁹. At every brot where B stays sane (≤ 4) the angle grid alone puts
   `error_1` at 16× the shipped value.
2. **Q is not an independent axis.** Over the whole (R,B,C) grid — 3.8 M shapes
   scanned at brot = 8, J = 5 — the minimum Q that clears the accuracy model is
   **exactly 427**, and it is attained by the shipped `(8,143,44)`. The rest of the
   gate-legal set splits into two blocks: **Q ∈ [427, 437]** for `B ≥ 129` and
   **Q ≥ 695** for `B ≤ 128` (the `inner_temp` cliff). The floor is structural:
   `Q = 84 + J·brot + inner_temp` with `inner_temp ∈ {303,…,307}` for every
   `B ≥ 129`, and 510–575 below it.
3. **The best gate-legal triple is the shipped one**: `(T, Q, λ_eff, cost) =
   (14,706, 427, 46.921716818, 294,643,137.73)`, which is **+16,981,123.03
   (+6.12 %) above** the gold threshold. At fixed T, gold needs **Q ≤ 402.39**
   (25 qubits below the floor); at fixed Q, gold needs **T ≤ 13,858.45**
   (847 below the loader floor). Both are outside the reachable set.
4. Under the model there is exactly one family of configurations below gold —
   260.29 M at `(5,136,96)`, 266.76 M at `(6,136,72)`, 267.38 M at `(4,152,128)` —
   and **none of it is a Q result** (their Q is 427–430, i.e. worse than shipped).
   They win purely on T (rows 684–892) and each needs a fit and a loader that
   neither exist nor have been measured: see §5.3, extrapolation only, 1.1–1.3×
   outside the measured box.

## 1. The exact cost-model code

`scoreinfra/costs_prepare.py`, lines 169–190 (the inner PREPARE qubit cost — this
is where *all* of Q's freedom lives):

```python
def inner_state_prep_qubit_cost(self) -> dict[str, int]:
    b_k2 = self.chi
    b2 = math.ceil(math.log2(self.B)) + b_k2 + 1
    k2_opt = QR(self.R * self.C * self.B, b2)[0]

    if self.optimize_qubits:
        k2_opt = self.find_qroam_size_to_minimize_global_temp_ancilla(b2)

    RC = self.R * self.C
    persistent_uniform = math.ceil(math.log2(self.B + 1)) + 2
    temporary_uniform = max(0, math.ceil(math.log2(self.B + 1)) - 2)
    persistent_for_qroam = b2 + b_k2 + math.ceil(math.log2(self.R)) + 2
    temporary_for_qroam = math.ceil(math.log2(RC * math.ceil((self.B + 1) / 2**k2_opt))) + ((2**k2_opt) - 1) * b2

    return {
        "persistent": persistent_for_qroam + persistent_uniform,
        "temporary": temporary_uniform + temporary_for_qroam,
        ...
```

and the selector, lines 84–99:

```python
def find_qroam_size_to_minimize_global_temp_ancilla(self, b2: int) -> int:
    k2_opt = QR(self.R * self.C * self.B, b2)[0]
    if self.optimize_qubits:
        for j in range(k2_opt + 1):  # start from zero in case k2_opt is already optimal
            k2_opt_new = k2_opt - j
            if math.ceil(math.log2(self.R * self.C * math.ceil(self.B / 2**k2_opt_new))) + ((2**k2_opt_new) - 1) * b2 < self.beta * (self.N - 1):
                k2_opt = k2_opt_new
                break
        else:
            raise ValueError(...)
    return k2_opt
```

The score side, `verify.py` lines 461–468 and 490–493:

```python
    costs["persistent_qubits"] = outer_persistent + inner_persistent
    costs["temporary_qubits"] = max(outer_temporary, inner_temporary)
...
    toffoli = angles["toffoli"] + heuristic["toffoli"]
    persistent_qubits = heuristic["persistent_qubits"] + angles["persistent_qubits"]
    temporary_qubits = max(heuristic["temporary_qubits"], angles["temporary_qubits"])
    qubits = persistent_qubits + temporary_qubits
```

`optimize_qubits` is never overridden: `verify.py:436-443` constructs
`SpinFreeData_V1(R=…, B=…, C=…, N=…, chi=KEEP_BITS, beta=brot)` with the default
`True`. `KEEP_BITS = 10`, `QUBIT_CAP = 128` (`verify.py:134,139`), `N = 76`.

Reproduction at the shipped point (exact, asserted in the script):

```
b2 = 19   k2 = 4   outer_temp = 90   inner_temp = 297 + 6 = 303   ang_temp = 77
Q = (40 + 44) + J*brot(5*8 = 40) + max(90, 303, 77) = 427
T_h = 317(outer) + 4095(inner) + 2250(givens) = 6,662
```

## 2. What 31, 19, 11 and 6 actually are (the guess corrected)

```
inner_temp = temporary_uniform + temporary_for_qroam
           = max(0, ceil(log2(B+1)) - 2)                        <-- the "+6"
           + ceil(log2(RC * ceil((B+1)/2^k2)))                  <-- the "11" or "12"
           + (2^k2 - 1) * b2                                    <-- the "589" or "285"
```

At `(R,B,C,brot) = (8,143,44,8)`: `B+1 = 144`, `RC = 352`, `b2 = ceil(log2 143) + 10 + 1 = 8+11 = 19`.

| symbol | value | is |
|---|---:|---|
| `chi` | 10 | `KEEP_BITS`, fixed by the competition, not a submission choice |
| `b2` | 19 | inner-QROAM **word width** = `ceil(log2 B) + chi + 1` (address bits + keep bits + 1 sign/pad) |
| `2^k2 − 1` | 31 at k2 = 5, 15 at k2 = 4 | number of QROAM **blocks minus one** at block size `2^k2` — a count of gadgets, not of terms and not of central terms |
| 589 | `31 × 19` | `(2^5 − 1)·b2` = block count × word width = **temporary qubits of the inner QROAM** at k2 = 5 |
| 11 | `ceil(log2(352·5))` | address bits of the widened block: `ceil(log2(RC·ceil(B/2^k2)))` = `log2(1760)` |
| 600 | `589 + 11` | the k2 = 5 candidate, which must be **strictly** `< brot·(N−1) = 8·75 = 600` → **fails by 0** |
| 297 | `285 + 12` | the k2 = 4 candidate: `15·19 + ceil(log2(352·9)) = 285 + 12` |
| 6 | `ceil(log2 144) − 2` | `temporary_uniform` (the uniform-superposition counter), present at every k2 — constant **within a binade of B** (6 for B ∈ [129,255], 5 for B ∈ [65,127], 4 for B ≤ 63), not a global constant |

So the guessed pattern `31·(2k2−1)+18+6` is a coincidence: `31` is `2^5−1` and
`19` is `b2`, and there is no `+18`. The correct k2 = 3 value is
`7·19 + ceil(log2(352·18)) + 6 = 133 + 13 + 6 = **152**`, i.e. **Q = 276**
(−35.4 %, chem 190.45 M, GM 32.56) — bigger than the guess, and still
unreachable (§4).

**The 600 threshold is `brot·(N−1)`,** i.e. the *Givens rotations'* persistent
ancilla (75 rotations × brot bits). Note the scorer never charges that register:
`verify.py:491-493` adds only `heur_persistent + angles_persistent` and
`max(heur_temp, angles_temp)`. The selector therefore spends an ancilla budget
the score does not bill, and it spends it **maximally** (it takes the *largest*
k2 that fits, which is the *largest* `inner_temp` under 600). `inner_temp = 303`
is not a minimiser; it is the model's own non-Q-optimal choice, and it is not
tunable by the submitter.

## 3. What k2 is and what selects it

`k2` is the **QROAM block width** (log2 of the number of addresses loaded per
lookup) of the inner state preparation. Selection is a two-step, top-down rule:

1. Start from the unconstrained cost optimum
   `k2_QR = argmin_{k ∈ {⌊h⌋,⌈h⌉}} [ RCB/2^k + b2·(2^k − 1) ]`, `h = ½·log2(RCB/b2)`
   — for `(8,143,44)`: `QR(50336, 19) = (6, 1984)`.
2. **Decrement** `k2 = k2_QR, k2_QR−1, …` and **stop at the first** value with
   `ceil(log2(RC·ceil(B/2^k2))) + (2^k2 − 1)·b2 < brot·(N−1)`; raise if none fits.

Trace at the shipped shape (`brot·(N−1) = 600`, strict `<`):

| k2 | `ceil(log2(RC·ceil(B/2^k2)))` | `(2^k2−1)·b2` | sum | `< 600` | action |
|---:|---:|---:|---:|:--:|---|
| 6 | 11 | 1197 | 1208 | no | try 5 |
| 5 | 11 | 589 | **600** | **no** | try 4 |
| 4 | 12 | 285 | 297 | yes | **accept → k2 = 4** |

It is **not** a ceiling on central terms per block, **not** `ceil(log2(K·k2))`,
and **not** a `brot·(N−1)` bound on the number of terms. It is exactly the
inequality above. Consequences, all exact:

* `brot = 9` *raises* the threshold to 675, so the k2 = 5 candidate (600) now
  passes and `inner_temp` jumps 303 → 606 → **Q = 735**. Higher precision makes
  Q worse; that is why brot = 8 is the knife edge (`RESULT.md` §2.4, reconfirmed).
* `brot = 7` lowers the threshold to 525 and keeps k2 = 4 → Q = 422, but the
  angle grid halves (see §4.2).
* `B ≤ 128` → `b2 ≤ 18` and `ceil(B/32) ≤ 4`, so **k2 = 5** fits and
  `inner_temp` = 510–575 → Q ≥ 629 on the grid (≥ 695 once the rank floor is
  applied) (`RESULT.md` §2.2, reconfirmed exactly).

## 4. The k2 = 3 lead — reachability, exactly

### 4.1 The forcing condition

k2 = 3 is selected **iff the k2 = 4 candidate fails**:

```
ceil(log2(RC·ceil(B/16))) + 15·b2  ≥  brot·(N−1),   b2 = ceil(log2 B) + 11
```

Since `15·b2 ≥ 165` and the log term is 9–16 for any sane `RC·B`, this reduces to
`ceil(log2 B) ≳ 5·brot − 12`. Solving over B with the real selector:

| brot | threshold `75·brot` | **min B giving k2 = 3** | b2 | rows (R=8) | inner_temp | Q |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 150 | 8 | 14 | 140 | 110 | 195 |
| 3 | 225 | 9 | 15 | 148 | 117 | 208 |
| 4 | 300 | **257** | 20 | 2,132 | 161 | 267 |
| 5 | 375 | 4,097 | 24 | 32,852 | 197 | 316 |
| **8** | **600** | **67,108,865** | 38 | **536,870,996** | 323 | 485 |
| 9 | 675 | 2,147,483,649 | 43 | 1.7·10¹⁰ | 368 | 545 |
| 12 | 900 | 35,184,372,088,833 | 57 | 2.8·10¹⁴ | 494 | 714 |

Note that even when reached, Q is **not** 276: at these B, `b2` itself has grown
from 19 to 38 and both `persistent_for_qroam` (= `b2 + 12 + ceil(log2 R)`) and
`persistent_uniform` grow with `log B`, so `pers` goes 84 → 122 while
`inner_temp` goes 152 → 323. Q = 485 at brot = 8, not 276. **The 276
counterfactual only exists at the shipped B with k2 = 3, which the model never
selects.**

### 4.2 Why every reachable k2 = 3 is illegal

Two disjoint cases, both dead:

* **brot ≥ 8** (the only legal regime, see below): needs `B ≥ 67,108,865`
  at brot = 8 → `rows = 76 + 8B ≈ 5.4·10⁸` → `T_angles ≈ 2·4022·rows/1220 ≈
  3.5·10⁹`, cost ~10¹². Not a cost trade, a category error.
* **brot ≤ 4** (where B = 9…257 is sane): the angle word grid is `2^-brot`.
  The shipped point has `error_1 = error_2 = 0.0199999985`, i.e. **1.5·10⁻⁹
  under** the 0.02 gate, and both shrink with brot (`verify.py` docstring for
  `error_1`: "It shrinks with `brot`"). One bit less doubles the residual:
  brot = 7 → ≈ 0.040 (already 2× over), brot = 4 → ≈ 16× → ≈ 0.32 (16× over).
  The modelled *two-body* rounding alone at brot = 4 is `14.09·16 = 225 mHa`,
  11× the whole 20 mHa budget.

Measured against the same standard as `RESULT.md` §2.4: **brot ≥ 8 is a hard
gate**, and with brot ≥ 8 the k2 = 3 branch does not exist below B = 6.7·10⁷.

### 4.3 Best *cost* achievable inside the k2 = 3 branch (even ignoring accuracy)

| brot | min B | rows | Q | T_h | cost (lin loader) | modelled e2 |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 8 | 140 | 195 | 1,821 | 25.1 M | 3,942 mHa |
| 3 | 9 | 148 | 208 | 2,138 | 30.4 M | 3,127 mHa |
| 4 | 257 | 2,132 | 267 | 13,921 | **350.5 M** | 298 mHa |
| 5 | 4,097 | 32,852 | 316 | 187,089 | 5,986 M | 585 mHa |
| 6 | 131,073 | 1,048,660 | 376 | 5,901,394 | 226,101 M | 1,652 mHa |

**Even with accuracy switched off, the k2 = 3 branch only wins at brot ≤ 3, where
the error is 150–200× the gate.** The cheapest k2 = 3 configuration that is
shape-legal (B ≤ 512) is 350.5 M — **19 % worse than the shipped 294.6 M** —
and its e2 is 298 mHa. So the lead fails on cost as well as on accuracy;
there is no scenario in which it is the thing to chase.

## 5. The (R,B,C,brot) sweep

Grid: R ∈ {4,5,6,7,8,9,10,12,14,16}, B ∈ 96…256 step 8 plus {129,143,255},
C ∈ {24,28,32,36,40,44,48,52,56,60,64,72,80,88,96,112,128}, brot ∈ {6,7,8,9,10},
J = 5 → **20,400 configurations**, every `T_h`, `Q`, `k2`, `inner_temp` exact
from the official module. Accuracy is a *model* (4 measured points + calibrated
8-bit rounding), not a verifier result:

```
rows = 76 + R*B,  K = R*C
e2_cont  = 1.93 * (3.25/(B/C))^1.95 * floor(K)        # calibrates 14.20 at the shipped point
rounding = 14.087 * sqrt(rows/1220) * 2^(8-brot)      # 8-bit term, calibrated to 20.00 total
e2_total = hypot(e2_cont, rounding)  <= 20 mHa        # gate
floor(K) from artifacts/H_spectrum.npy (rigorous lower bound)
```

### 5.1 Q is a constant across the legal set

| Q | cheapest modelled-legal shape | brot | rows | K | k2 | inner_temp | T_h |
|---:|---|---:|---:|---:|---:|---:|---:|
| **427** | **(6,136,72)** | 8 | 892 | 432 | 4 | 303 | 7,433 |
| 428 | (6,144,72) | 8 | 940 | 432 | 4 | 304 | 7,881 |
| 429 | (4,152,128) | 8 | 684 | 512 | 4 | 304 | 8,773 |
| 430 | (5,136,96) | 8 | 756 | 480 | 4 | 304 | 7,916 |
| 431 | (9,129,52) | 8 | 1,237 | 468 | 4 | 304 | 7,784 |
| 437 | (16,129,128) | 8 | 2,140 | 2,048 | 4 | 306 | 22,835 |
| 695+ | any B ≤ 128 | 8 | — | — | 5 | 574–575 | — |

**No gate-legal configuration anywhere in the grid has Q < 427.** A wider exact
scan (R 2…32, B 8…599, all C, 3.8 M shapes, brot = 8) finds the same floor:
minimum legal Q = **427**, first attained at `(8,143,44)`, `(8,144,44)`,
`(8,139,45)`, `(4,232,100)`, `(8,176,40)`… The sub-427 pockets of `RESULT.md`
§2.3 (inner_temp 253/254/268–270/284/285 → Q 369–405) all need `R·C ≤ 285`, and
the rank floor alone kills them: `floor(261) = 31.3`, `floor(282) = 22.6`,
`floor(292) = 19.2` mHa against a 14.2 mHa continuous gate. Q = 426 by the other
route (`R ≤ 4`, saving one bit of `ceil(log2 R)`, `pers = 83`) additionally needs
`RC·B ≤ 65,536`, i.e. `K ≤ 292` at the B/C ≥ 3 the accuracy needs — same death.
Q = 425/424 need `K ≤ 227` (`floor(225) = 52.4`). **Q = 426 and below is not
reachable at any legal K.**

The three Q levers, and why none moves:

| lever | term | status |
|---|---|---|
| `J·brot` | 40 | J = 5 is the measured optimum of its family (official `resource_costs` on that constructor: J = 1/2/3/4 = 485.3/398.3/358.2/349.6 M vs J = 5 = 339.4 M, i.e. J = 4 is **+3.0 %**); J = 6 breaks the 128-qubit cap (11+48+69+4 = 132). brot = 7 would give −5 Q but is accuracy-dead (§4.2). **Closed.** |
| `pers` | 84 | `40 + 44`. Reducing it needs `RC ≤ 128` (kills K) or `B ≤ 127` (k2 → 5, +270 Q). **Closed.** |
| `max(…, inner_temp, …)` | 303 | `outer_temp = 90` and `ang_temp = 77` never bind (`ang_temp = 128−11−8J ≤ 77 < 303`). `inner_temp` is k2-locked at 303 for `B ∈ [129,143]`, 304–306 above. **Closed.** |

### 5.2 Gate-legal vs accuracy-breaking, in the measured box

Restricting to where the rho law is *interpolating* rather than extrapolating
(K ∈ [320,360], B/C ∈ [1.50,3.60]; the four measured points are
`(8,143,44) 14.20`, `(8,129,44) 19.83`, `(5,135,70) 40.24`, `(4,131,83) 73.07`):

| shape | brot | rows | K | B/C | Q | T_h | T (lin) | cost | vs shipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **(8,143,44)** shipped | 8 | 1,220 | 352 | 3.25 | 427 | 6,662 | 14,706 | **294.64 M** | — |
| (9,129,40) | 8 | 1,237 | 360 | 3.23 | 428 | 6,713 | 14,869 | 298.61 M | +1.35 % |
| (8,144,44) | 8 | 1,228 | 352 | 3.27 | 427 | 7,016 | 15,113 | 302.79 M | +2.76 % |
| (9,136,40) | 8 | 1,300 | 360 | 3.40 | 428 | 6,727 | 15,298 | 307.23 M | +4.27 % |
| (8,129,44) | 8 | 1,108 | 352 | 2.93 | 427 | 6,634 | 14,464 (cons) | 289.8 M (cons) | **FAIL, measured 19.83 vs 14.82 gate** |

It is the only in-box shape cheaper than the shipped point, and it is the one that
is **measured** to fail. Everything else in the box is worse. This is the same
conclusion as `RESULT.md` §3.2, now with Q shown to be flat at 427–428 across
the whole box.
**Gate-legal = the shipped point. Everything below it in cost is either measured
to fail ((8,129,44)) or requires an unmeasured extrapolation (§5.3).**

### 5.3 The modelled-legal configurations below gold — flagged, not claimed

Exactly three shapes in the 20,400-point grid come in below 277,662,014.70:

| shape | brot | rows | K | B/C | Q | T_h | T | cost | vs shipped | e2 margin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (5,136,96) | 8 | 756 | 480 | 1.42 | 430 | 7,916 | 12,901 | **260.29 M** | −11.6 % | 15.88 vs 16.65 (+4.6 %) |
| (6,136,72) | 8 | 892 | 432 | 1.89 | 427 | 7,433 | 13,314 | 266.76 M | −9.5 % | 15.72 vs 15.97 (+1.6 %) |
| (4,152,128) | 8 | 684 | 512 | 1.19 | 429 | 8,773 | 13,283 | 267.38 M | −9.2 % | 15.67 vs 16.99 (+7.8 %) |

None of this is a Q result — Q is 427–430, i.e. **three worse than shipped** at
best. The whole gain is `rows 684–892 → T_angles ≈ 4,500–5,900` instead of 8,044.
Three independent reasons none of them is a result:

1. **They are extrapolations, and the law is known to err in the fatal
   direction.** (5,136,96) and (4,152,128) sit below the lowest measured B/C
   (1.42 and 1.19 vs 1.58) and all three sit at K = 432–512 against a largest
   measured K of 352. The rho law is a 4-point fit, all at K ≈ 350, and at the
   one point where it can be checked against a real fit at low B/C — (8,129,44),
   B/C 2.93, K 352 — it predicts 17.37 where the fit measured **19.83 (+14 %)**.
   Applied here, a +14 % error puts all three at 17.9–18.1 mHa against gates of
   16.0–17.0, i.e. **all three fail**. The only honest statement is that a real
   fit is needed, and the prior work's measured curve (73 mHa at B/C 1.58) says
   the odds are poor.
2. **The loader does not exist.** The shipped 4,022 Toffolis/pass is a 4.5×
   compression hardcoded to the 1,220-row / 77-high / 11-selection geometry
   (`RESULT.md` §5). At 756 rows the published reference QROM costs
   `15·(rows−2) ≈ 11,310`/pass, which would make (5,136,96) cost **≈ 1,080 M**;
   the `15·(...)` product model that makes it 260 M is an unbuilt plan.
3. **The E_gap floor is a factorization constraint.** `E_gap = E_upper − E_SOS`
   with `E_SOS = ecore − ηβ_1 − 2N_neg − ½ΣW²`, and the shipped table sits at
   `ΣW² = 1,079.8456` against the cap `1,080` (verified from `submission.npz`:
   `W = H2_I − Σ_b w`), i.e. `2N_neg + ½ΣW² = 540.0` exactly. Any new (R,B,C)
   needs a refit that lands back on that boundary — with 80–160 extra columns
   this is unproven in either direction.

So: **Q is closed; the residual lead is the old shape/T axis, already NO-GO on
measurement, and it is the only thing in the grid that could clear gold.**

## 6. Best gate-legal triple, and the distance to gold

| | T | Q | λ_eff | cost | vs gold 277,662,014.70 |
|---|---:|---:|---:|---:|---:|
| **verified shipped point** | **14,706** | **427** | **46.921716818** | **294,643,137.73** | **+16,981,123.03 (+6.116 %)** |
| best modelled-legal *alternative* | 14,869 | 428 | 46.9217 | 298.61 M | +7.55 % |
| counterfactual k2 = 3 at shipped B (unreachable) | 14,706 | 276 | 46.9217 | 190.45 M | −31.4 % |

Required to close the gap, from the exact identity `cost = λ·T·Q`
(`cost per T = λ·Q = 20,035.573`):

| held fixed | requirement | available | shortfall |
|---|---|---|---|
| T = 14,706 | **Q ≤ 402.39** | Q_min(legal) = **427** | **25 qubits** |
| Q = 427 | **T ≤ 13,858.45** | T_min(loader-bound, measured) = 14,706 | **847 Toffolis** |
| T, Q | λ_eff ≤ 44.2175 | 46.9217 (intrinsic, 6 refits within 1e-5) | 2.70 |

**Q reduction is a closed path.** The only 25-qubit move in the entire model is
`inner_temp 303 → 152`, and it requires `k2 = 3`, which requires either
`B ≥ 6.7·10⁷` (rows 5.4·10⁸) or `brot ≤ 4` (error 16× the gate). Intermediate
steps do not exist: the gate-legal Q values are `[427, 437]` then `≥ 695`, with
nothing in between (the sub-427 pockets die on the rank floor, §5.1).

## 7. Verification scope

* **Exact** (official `SpinFreeData_V1`, imported unmodified): all `T_h`, `Q`,
  `k2`, `inner_temp`, `b2`, `outer/inner_persistent`, `ang_temp`, the Q cliff at
  `B ≤ 128`, the k2 selection trace, the minimum-B-for-k2=3 table, and the Q
  floor of 427 (3.8 M shapes scanned).
* **Exact** (from `submission.npz`): `ΣW² = 1,079.8456412639948`, hence
  `½ΣW² = 539.9228` and the `E_gap` headroom of 0.077 in the `2N_neg + ½ΣW² = 540`
  identity.
* **Exact** (from `artifacts/H_spectrum.npy`): `floor(225) = 52.41`,
  `floor(320) = 11.74`, `floor(352) = 7.361`, `floor(432) = 2.83`, `floor(480) = 1.63`.
* **Model, labelled**: the `rho` law (4 measured points, ±15 %), the 8-bit
  rounding term `14.087·sqrt(rows/1220)·2^(8−brot)`, and the three loader models
  (`lin` = shipped density held constant, `cons`/`cut` = the product forms).
* **Assumed, labelled**: λ_eff held at 46.921716818 for every shape (needs a
  refit to confirm at K ≠ 352), and `error_1 ≈ error_2` in brot-scaling.
* **Not run here**: no official verifier, no `kickmix`, no circuit simulation,
  no integrals read, no Kaggle kernel, no submission, no push. All heavy work
  would go to a Kaggle CPU kernel (`enable_gpu=False`, `enable_tpu=False`).

## 8. Negative results recorded (do not redo)

| experiment | result |
|---|---|
| `inner_temp ≈ 31·(2k2−1)+18+6` | **wrong formula.** `589 = (2^5−1)·b2` with `b2 = 19`; correct k2 = 3 value is 152 (Q 276), not 179 (Q 303) |
| force k2 = 3 at brot ≥ 8 | needs B ≥ 67,108,865 (brot 8) / 2.1·10⁹ (brot 9) → rows ≥ 5.4·10⁸, T ≈ 3.5·10⁹ |
| force k2 = 3 at brot ≤ 4 (B = 9…257) | error 16×–200× the gate; and the cheapest shape-legal one is 350.5 M (+19 %) |
| J = 4 or 6 | official `resource_costs` J table: J = 4 is +3.0 %, J = 6 breaks the 128-qubit cap |
| Q < 427 anywhere legal | does not exist: the sub-427 pockets all need `R·C ≤ 285` (floor ≥ 19.2 mHa vs the 14.2 continuous gate); the `R ≤ 4` one-qubit saving needs `RC·B ≤ 65,536`, i.e. K ≤ 292, same death |
| B ≤ 128 as a Q pocket | k2 = 5 → inner_temp 510–575 → Q 629–698 on the whole grid, ≥ 695 on gate-legal shapes (−3.9 GM) |
| brot = 7 (Q 422, T 14,406, 285.3 M) | error_1 doubles to ≈ 0.04 → hard fail; even if legal it is only +0.30 GM and does not reach gold |
| `(8,129,44)` (the only cheaper in-box shape) | measured 19.83 mHa vs the 14.82 gate → fail; Q is 427 anyway |
| `(5,136,96)` 260.29 M | model-only: K = 480 unmeasured, loader 11,310/pass would make it 1,080 M, ΣW²/E_gap unproven |

## 6. SPRINT adjacent-rotation merging — measured, CLOSED

Literature lead (`docs/frontier-20261117.md` §chem): SPRINT (arXiv:2606.30741) claims that
merging adjacent basis rotations halves the rotations per Trotter step. If our 1,144
two-body rows were `(U_k, U_k^dagger)` pairs, rows would drop 1,144 -> 572, `rows = 648`,
`T = 6.59*648 + 6,662 = 10,935`, `T*Q` -25.6 %, GM ~31.07.

Measured on the shipped `dfthcsos/submission.npz` `angle_words (1220, 75)` (pure array
arithmetic, no simulation):

| block | rows | duplicates | adjacent identical | adjacent `255 - x` |
|---|---:|---:|---:|---:|
| two-body (rows 76..1219) | 1,144 | 0 | 0 | 0 |
| one-body (rows 0..75) | 76 | 0 | 0 | 0 |

Per-rho pairing (`B = 143`, 71 pairs per rho, rho = 0, 1): 0 identical, 0 complement.
All 1,144 two-body rows are distinct. **There is no pair structure to merge**, so the
SPRINT compression gives exactly 0 here. The row count is intrinsic to this factorization,
not a redundant double-write.

This is consistent with §3: rows = `N + R*B`, so the only way to cut rows is to cut
`R*B`, which trades directly against `error_2` (pinned at 0.0199999985, 1.5e-9 under the
0.02 gate).
