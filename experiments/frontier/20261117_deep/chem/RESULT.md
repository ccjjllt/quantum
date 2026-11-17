# RESULT — chemistry shape axis (rows = N + R·B) and the brot=7 rebuild

Date: 2026-11-17 (this session). Chemistry (dfthcsos) only.
All local work is closed-form arithmetic: the verifier's own
`scoreinfra/costs_prepare.SpinFreeData_V1`, the rank-K floors read from the stored
`artifacts/H_spectrum.npy` (2,926 eigenvalues of H, produced by earlier work), and
the measured `rho` law of `RESULT2.md`. **No integrals were read, no kickmix import,
no simulation and no verifier run on this machine.** Circuit work, if any, is on
Kaggle CPU kernels only (refs in §6).

Baseline under attack: `a73b25d2` = v13 member (sha256 `93326853…b9c9e`,
T 14,706, Q 427, λ_eff 46.921716818) → cost **294,643,137.73**; the bdae-λ twin
is 294,762,512.64. GM 28.12994 here; gold needs a −5.496 % leg.

## 0. Verdict (go/no-go)

1. **NO-GO for the whole row-reduction direction, and it is now arithmetic, not a
   fit-quality argument.** `rows − 76 = K·(B/C)` is an identity, so "fewer rows at
   fixed K" *is* "smaller B/C"; and the official cost model charges every
   `B ≤ 128` shape an inner-QROAM temporary of 510–575 qubits instead of the
   pocket's 303 (§2.2). That is **Q ≥ 629 (+47 %)**, worth −3.9 GM by itself, and
   every shape in the request list `(8,96,44) (8,76,44) (8,64,44) (8,64,64)
   (6,96,59) (6,64,59) (4,128,88)` has B ≤ 128.
2. **The only row reduction that keeps Q = 427 is B ∈ [129, 255]**, i.e.
   `rows ≥ 76 + 129·R`; at K = 352 that means **rows ≥ 1,108** and necessarily
   `B/C ≥ 2.93`. That point, `(8,129,44)`, is already measured: continuous
   **19.83 mHa** against a 15.07 mHa gate (**1.32×**), so it fails; and its whole
   cost prize is **+0.16 GM**. The shipped `(8,143,44)` is therefore the corner of
   the legal family, exactly as the public frontier behaves.
3. **brot = 7 is worth +0.30 GM, not +0.60**, because `inner_state_prep` does not
   depend on β at all (only the Givens adder does): T_h falls **300**, not 1,305
   (§2.4). Its 7-bit grid halves the angle resolution, which doubles the measured
   8-bit rounding penalty (13.7 → ~27 mHa) — the same wall that pins every other
   T lever. **NO-GO**, and it would need a loader re-code anyway (a 7-bit word
   table changes the loader algebra that was engineered at 8 bits).
4. **No candidate package can be built for ANY new shape with the shipped
   tooling**: the public reference QROM is 4.5× the shipped loader
   (15 × (rows−2) ≈ 18,270 vs 4,025 Toffolis/pass, §5), and the shipped
   planner/emitter hardcodes 1,220 rows / 77 high values / 11 selection bits.
5. `(C)` free shape reduction is **closed**: no zero copy column, no zero base
   row, no zero rank in the shipped `W` (§4).
6. **The shape axis is exhausted. Stop chemistry shape work.** The only
   unmeasured chemistry lever left is loader T at *fixed* shape (closed by
   `CODE2/RESULT5`), not shape.

## 1. Hypotheses and what was measured

The brief's hypothesis: `angles_Toffoli = 8,044` is 55 % of T and grows ~linearly
in `rows = 76 + R·B`; the error floor depends only on `K = R·C`; so reduce
`B/C` at fixed `K` (e.g. `(8,64,44)`: K = 352, rows 588, "loader T nearly
halved"). Tested here: (i) the exact cost model over the whole (R,B,C,brot) grid,
(ii) the inner-temp pocket census, (iii) the measured precision frontier
(`rho` law, 4 measured points), (iv) the brot axis, (v) free reductions in the
shipped npz, (vi) whether a candidate could be built at all.

## 2. Exact walls (all from the verifier's own cost module)

### 2.1 The identity

```
rows = N + R*B,  K = R*C   =>   rows - 76 = K * (B/C)
```

So at fixed K, rows and B/C are the same knob. There is no third way to cut rows.

### 2.2 The Q cliff: `B ≤ 128` ⇒ inner_temp 510–575, Q ≥ 629

`inner_state_prep` picks `k2` from `QR(R*C*B, b2)` and only ever *lowers* it while
`ceil(log2(RC·ceil(B/2^k2))) + (2^k2−1)·b2 < brot·(N−1)`. At brot = 8 the
threshold is 600; with `b2 = ceil(log2 B) + 11`:

| B | 32 | 48 | 63 | 64 | 80 | 96 | 128 | **129** | 136 | **143** | 144 | 160 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rows (R=8,C=44) | 332 | 460 | 580 | 588 | 716 | 844 | 1100 | 1108 | 1164 | 1220 | 1228 | 1356 |
| b2 | 16 | 17 | 17 | 17 | 18 | 18 | 18 | 19 | 19 | 19 | 19 | 19 |
| k2 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | **4** | 4 | **4** | 4 | 4 |
| inner_temp | 510 | 541 | 541 | 543 | 574 | 574 | 575 | **303** | 303 | **303** | 303 | 303 |
| Q_total | 629 | 661 | 661 | 664 | 696 | 696 | 698 | **427** | 427 | **427** | 427 | 427 |
| T_h | 4143 | 4230 | 4260 | 4622 | 4687 | 5071 | 5495 | 6634 | 6648 | 6662 | 7016 | 7400 |

The shipped point sits on the exact discontinuity: 8·(N−1) = 600, and the k2 = 5
temporary is exactly 600, so the strict `<` pushes the model to k2 = 4 (303).
`B = 129` is the smallest B that is inside the pocket; `B = 144` is the first B
that costs +354 T (inner 4,095 → 4,449).

### 2.3 Inner-temp pocket census (whole grid, R 4..16, B 32..384, C 24..128, brot 8)

| inner_temp | B range | k2 | #shapes | Q range | R·C range |
|---|---:|---:|---:|---:|---:|
| 253 | 32 | 4 | 36 | 369–370 | 96–170 |
| 254 | 32 | 4 | 81 | 370–374 | 172–256 |
| 268 | 33–63 | 4 | 716 | 385–386 | 96–170 |
| 269 | 33–64 | 4 | 917 | 386–390 | 96–261 |
| 270 | 64 | 4 | 13 | 388–389 | 104–136 |
| 284 | 65–79 | 4 | 30 | 403 | 96–100 |
| 285 | 65–96 | 4 | 179 | 404–405 | 96–140 |
| 302 | 129–239 | 4 | 660 | 423–427 | 130–225 |
| 303 | 129–255 | 4 | 24,056 | 424–430 | 130–455 |
| 304 | 129–256 | 4 | 58,123 | 426–431 | 130–910 |
| 305 | 129–256 | 4 | 63,716 | 429–434 | 243–1815 |
| 306 | 129–256 | 4 | 23,577 | 432–437 | 483–2048 |

Two facts: (i) the low-temp pockets (253–285) exist only for **small R·C**
(K ≤ 261), i.e. they are precision-dead (floor(K=235) = 45.3 mHa, floor(282) =
22.6, floor(352) = 7.36 mHa — need K ≳ 340 for the 20 mHa gate); (ii) at
K ≈ 350 the pocket is only `B ∈ [129,255]`. So `B ≤ 128` is *always* paid for,
and the mini-pocket at K ≤ 261 buys Q but destroys precision.

### 2.4 brot axis at (8,143,44): −300 T, −5 Q, not −1305

| brot | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|
| inner_state_prep | 4095 | 4095 | **4095** | 2991 | 2991 |
| k2 / inner_temp | 4/303 | 4/303 | **4/303** | 5/606 | 5/606 |
| givens 2(N−1)(2β−1) | 1650 | 1950 | **2250** | 2550 | 2850 |
| T_h | 6062 | 6362 | **6662** | 5858 | 6158 |
| Q_total | 417 | 422 | **427** | 735 | 740 |
| cost @ λ (T = 2·4,025 + T_h) | 276.0 M | **285.4 M** | 294.6 M | 442 M | 450 M |

`inner_state_prep` has no β dependence (`b2 = ceil(log2 B)+chi+1`); β enters only
through the `k2` threshold `β(N−1)` and the Givens adder. So the brot=7 prize is
**−300 T and −5 Q = +0.30 GM** (285.4 M), not +0.6 GM. brot ≥ 9 falls off the
pocket (+308 Q = −7 GM).

## 3. Shape scan (exact T_h/Q; e2 predicted from the 4-point rho law)

`rho ≈ 1.93·(3.25/(B/C))^1.95`, `gate_c(rows) = sqrt(20² − (13.8·sqrt(rows/1220))²)`
mHa (8-bit rounding penalty in quadrature). `L` = loader Toffolis/pass; three
models: **lin** 4,025·rows/1220 (the old optimistic one), **cons** 15·(6+high+193)
(row-independent product term; calibrates to 4,020 vs measured 4,025),
**cut** 15·(6+high+(525−cuts)/2) with the allowed-cut bound (calibrates 3,975).
Cost at λ = 46.9216.

| shape | rows | K | B/C | T_h | Q | floor | gate | rho | e2 pred | L(cons/cut) | cost cons | cost cut | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **(8,143,44)** shipped | 1220 | 352 | 3.25 | 6662 | 427 | 7.36 | 14.48 | 1.93 | **14.2 meas** | 4020/3975 | 294.6 | 294.6 | PASS (20.00 after 8-bit) |
| (8,129,44) | 1108 | 352 | 2.93 | 6634 | 427 | 7.36 | 15.07 | 2.36 | **19.83 meas** | 3915/3885 | 289.8 | 277.5 | FAIL 1.32× |
| (8,132,46) | 1132 | 368 | 2.87 | 6797 | 427 | 6.06 | 14.94 | 2.46 | 14.9 | 3930/3820 | 293.7 | 282.8 | untested, ≤ +0.4 GM |
| (7,143,50) | 1077 | 350 | 2.86 | 6643 | 427 | 7.55 | 15.23 | 2.48 | 18.7 | 3885/3625 | 288.8 | 273.4 | predicted FAIL |
| (6,150,59) | 976 | 354 | 2.54 | 7050 | 427 | 7.18 | 15.74 | 3.12 | 22.4 | 3795/3450 | 293.3 | 267.5 | predicted FAIL |
| (8,144,44) | 1228 | 352 | 3.27 | 7016 | 427 | 7.36 | 14.43 | 1.90 | 14.0 | 4020/3975 | 301.7 | 299.9 | T +354, worse |
| (8,96,44) | 844 | 352 | 2.18 | 5071 | **696** | 7.36 | 16.38 | 4.20 | 30.9 | 3675/2730 | 405.6 | 348.0 | FAIL (Q + e2) |
| (8,76,44) | 684 | 352 | 1.73 | 4679 | **696** | 7.36 | 17.12 | 6.62 | 48.7 | 3525/2415 | 383.0 | 311.0 | FAIL |
| (8,64,44) | 588 | 352 | 1.45 | 4622 | **664** | 7.36 | 17.56 | 9.26 | 68.1 | 3435/1890 | 358.0 | 261.7 | FAIL 4× gate |
| (8,64,64) | 588 | 512 | 1.00 | 5243 | **666** | 1.14 | 17.56 | 19.2 | 21.9 | 3435/1890 | 378.5 | 282.0 | closest; 1.25× gate |
| (6,64,59) | 460 | 354 | 1.08 | 4630 | **664** | 7.18 | 18.12 | 16.4 | 117.8 | 3330/1890 | 351.8 | 250.2 | FAIL |
| (4,128,88) | 588 | 352 | 1.45 | 5495 | **697** | 7.36 | 17.56 | 9.26 | 68.1 | 3435/1890 | 404.4 | 346.7 | FAIL (Q + e2) |

Cost-only frontier (rho-law-feasible set, 209,270 cap-legal shapes of 481,845):

| rank | shape | rows | K | B/C | T_h | Q | e2 pred / gate | cost (cut / cons) | dGM (cut / cons) |
|---:|---|---:|---:|---:|---:|---:|---|---:|---|
| 1 | (14,32,44) | 524 | 616 | 0.73 | 4821 | 633 | 17.5 / 17.84 | 243.0 / 343.7 M | **+1.87 / −1.00** |
| 2 | (14,32,45) | 524 | 630 | 0.71 | 4856 | 633 | 16.8 / 17.84 | 244.0 / 344.7 M | +1.83 / −0.96 |
| 3 | (14,32,46) | 524 | 644 | 0.70 | 4888 | 633 | 16.3 / 17.84 | 245.0 / 345.7 M | +1.79 / −0.92 |
| 4 | (15,32,39) | 556 | 585 | 0.82 | 4747 | 633 | 16.9 / 17.70 | 247.0 / 343.3 M | +1.71 / −0.98 |
| 5 | (8,64,80) | 588 | 640 | 0.80 | 5600 | 666 | 12.9 / 17.56 | 293.1 / 388.9 M | +0.07 / −1.75 |
| 6 | (8,64,64) | 588 | 512 | 1.00 | 5243 | 666 | 21.9 / 17.56 | 282.0 / 378.5 M | +0.42 / −1.53 |
| — | (8,143,44) | 1220 | 352 | 3.25 | 6662 | 427 | 14.2 / 14.48 | 294.6 / 294.6 M | 0 |

Reading: every shape that would actually *win* lives at `B/C ≤ 1.0`, i.e. a
**2.2–4× extrapolation below the lowest measured B/C (1.58, where e2 was 73 mHa
= 4.2× its gate)**, and its sign flips between the two loader models. Every shape
whose row count is close enough to be comfortable is over the precision gate.

### 3.1 The measured rows → e2 curve at K ≈ 352 (this is the decisive plot)

| shape | rows | B/C | floor | gate | measured continuous e2 | e2/gate |
|---|---:|---:|---:|---:|---:|---:|
| (8,143,44) | 1220 | 3.25 | 7.36 | 14.48 | **14.20** | 0.98 |
| (8,129,44) | 1108 | 2.93 | 7.36 | 15.07 | **19.83** | 1.32 |
| (5,135,70) | 751 | 1.93 | 7.55 | 16.82 | **40.24** | 2.39 |
| (4,131,83) | 600 | 1.58 | 9.69 | 17.50 | **73.07** | 4.17 |

(All four are earlier measured continuous fits; three are quoted from
`RESULT2.md` §4b, the shipped one from `RESULT4.md`.)

**What K would it take to reach the gate at rows ≤ 600?** With
`B/C = (rows−76)/K`:

| K | 350 | 400 | 450 | 500 | 550 | 600 | 650 | 700 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B/C at rows 600 | 1.50 | 1.31 | 1.16 | 1.05 | 0.95 | 0.87 | 0.81 | 0.75 |
| floor (mHa) | 7.55 | 4.13 | 2.30 | 1.30 | 0.79 | 0.54 | 0.41 | 0.34 |
| rho needed | 2.3 | 4.2 | 7.6 | 13.5 | 22.2 | 32.4 | 42.7 | 51.4 |
| rho (law) | 8.75 | 11.4 | 14.3 | 17.5 | 21.1 | 25.0 | 29.3 | 33.8 |
| e2 pred / gate 17.5 | 66 | 47 | 33 | 22.8 | 16.7 | 13.5 | 11.9 | 11.5 |

So a rows-600 shape needs **K ≈ 550–650, i.e. C ≈ 69–82 at R = 8 or R ≈ 14 with
B = 32**, and a `rho` of 22–32 — **12–17× worse fit quality than the best measured
point (1.93)** and 4× beyond the lowest B/C ever measured. That is the
quantitative statement of the corner.

### 3.2 Cheapest legal alternatives to the shipped point (B ≥ 129, Q = 427)

| shape | rows | T_h | Q | cost (cons / cut) | dGM | precision |
|---|---:|---:|---:|---:|---:|---|
| (8,129,44) | 1108 | 6634 | 427 | 289.8 / 277.5 M | +0.16 / +0.57 | **19.83 measured → FAIL** |
| (8,132,46) | 1132 | 6797 | 427 | 293.7 / 282.8 M | +0.04 / +0.39 | 14.9 predicted, untested |
| (7,143,50) | 1077 | 6643 | 427 | 288.8 / 273.4 M | +0.19 / +0.71 | 18.7 predicted → FAIL |
| (6,150,59) | 976 | 7050 | 427 | 293.3 / 267.5 M | +0.05 / +0.93 | 22.4 predicted → FAIL |
| (8,140,45) | 1196 | 6735 | 427 | 294.8 / 290.0 M | −0.00 / +0.15 | 14.0 predicted |
| (8,144,44) | 1228 | 7016 | 427 | 301.7 / 299.9 M | −0.22 / −0.16 | 14.0 predicted |

The largest *measured*-supported prize on the whole axis is **+0.16 GM**, and it
belongs to a shape that fails the gate by 32 %.

## 4. `(C)` free shape reductions in the shipped npz — closed

`W (8,143,44)`: no all-zero copy column across all (rank, base); no all-zero base
row across all (rank, copy); no all-zero rank. Min over (ρ,c) of Σ_b |w| = 0.717
(no near-zero column either). `U` is read for its shape only, and it is
(8,143,76) = the legal `(R,B,N)`. **Nothing to shave.**

## 5. Why no candidate package can be built for a new shape

* The reference QROM (`example_submission/angle_k_reference_circuit.py`, the only
  published builder) is an ordinary segment-tree QROM: **≤ rows−2 Toffolis per
  circuit**, 15 circuits (ceil(75/5)) → **≤ 18,270 Toffolis/pass** at 1,220 rows
  vs the shipped **4,025** (4.5×). At the shipped shape that alone is
  T = 2·18,270 + 6,662 = 43,202 → **865 M** (GM −13).
* The shipped loader is a 4.5× compression that exists only as a plan for the
  1,220-row / 77-high / 11-selection geometry; `planner.py`/`emit_plan.py` hardcode
  those constants (`CODE2.md`, `RESULT5.md`), and no plan exists at 524–844 rows.
* Therefore a shape that passes precision is still **not deliverable**, and the
  loader T at low rows is not merely unknown but *unbuildable with the published
  toolchain* (its honest range is 1,890–3,435 per pass at 588 rows — a 1.8× band
  that decides ±1.5 GM).

## 6. Kaggle kernels (CPU only, `enable_gpu=false`, `enable_tpu=false`)

* `qingyu1232/qcc-chem-bc-axis-shape-fits` — exact-objective (fitlib, unchanged)
  continuous-e2 fits for `(8,143,44)` control, `(8,96,44)`, `(8,76,44)`,
  `(8,64,44)`, `(8,64,64)`, `(8,64,80)`, `(14,32,44)`, `(6,96,59)`, `(6,64,59)`,
  `(4,128,88)`, two protocols (A: historical spectral init; B: warm start from the
  shipped table projected onto B projectors/group). Pushed 2026-11-17; status and
  results appended in §7 when COMPLETE. **No verifier run and no submission.**
* The historical calibration of protocol A on `(8,143,44)` is **360 mHa**
  (`RESULT2.md` §5), i.e. 25× the real 14.2; only protocol B can be read
  absolutely, and its control value is the calibration to watch.

## 7. Measured fits (to be filled from the kernel)

_(appended below once the kernel is COMPLETE; nothing here is assumed)_

## 8. Verification scope

* Exact: all `T_h`, `Q_total`, `inner_temp`, `k2`, `b2`, pockets, the Q cliff and
  the brot table — computed with the verifier's own `SpinFreeData_V1`.
* Exact: the rank floors (stored H spectrum, 2,926 eigenvalues), the identity
  `rows−76 = K(B/C)`, the `(C)` scan of the shipped `W`.
* Model (labelled): `rho` law (4 measured points, ±15 %), 8-bit rounding penalty
  `13.8·sqrt(rows/1220)` mHa, and the three loader models.
* Measured by others, quoted: continuous e2 14.20 / 19.83 / 40.24 / 73.07 mHa.
* **Not run here**: no circuit simulation, no official verifier, no submission.
  The only kernel work in flight is classical fitting on Kaggle CPU.

## 9. Negative results recorded (do not redo)

| experiment | result |
|---|---|
| `(8,64,44)` shape (rows 588, K 352) | Q 664 (+55 %) and e2 68 mHa predicted (3.9× gate) — dead twice |
| `(8,96,44)`, `(8,76,44)` | Q 696 unchanged at +63 %, e2 31 / 49 mHa — dead |
| `(6,96,59)`, `(6,64,59)`, `(4,128,88)` | Q 664–697, e2 53 / 118 / 68 mHa — dead |
| `(8,64,64)` (the closest) | e2 21.9 predicted vs 17.6 gate; needs rho ≤ 15.4 against a law value of 19.2 |
| `(8,144,44)` | +354 T (inner QROAM step), cost +0.16…+0.22 GM |
| brot = 7 | −300 T, −5 Q = +0.30 GM ceiling; 7-bit rounding ≈ 27 mHa; loader re-code needed → dead |
| brot = 9, 10 | k2 5 → inner_temp 606 → Q 735/740 → −7 GM |
| `B/C` row reduction at fixed K | = rows reduction (identity); the only legal pocket is B ∈ [129,255] ⇒ rows ≥ 76+129R |
| free shape shave of the shipped npz | none (no zero column/row/rank) |
| reference QROM as a replacement builder | 4.5× the shipped loader T → 865 M at the same shape |
| public baseline `FeMoCo76o113e_65_60_60` | Λ 308.45, λ_eff 49.25, e2 16.13, heuristic 429.6 M — worse on every axis (scout line) |
| λ refit | ceiling −0.13 % (λ 46.786); e1/e2 at the gate → closed (LAMBDA.md) |

## 10. What a winning shape would have to satisfy (the quantitative condition)

For a shape to beat 294.64 M it needs, simultaneously:

1. `B ∈ [129, 255]` (else Q ≥ 629 and the leg loses ~+3.9 GM before any T gain), or
2. `B ≤ 128` **and** `rows ≤ 588` **and** `K ≳ 550` **and** an actual fit with
   `e2 ≤ 17 mHa` at `B/C ≤ 0.95` — a 4× extrapolation of the measured rho curve,
   where the one measured point at B/C 1.58 is already 4.2× over its gate; **and**
3. a loader plan at that row count (37 high masks, 10–11 selection bits) that
   beats 3,435 Toffolis/pass, which does not exist in any published toolchain,
4. plus a 7-bit-or-better word table whose rounding penalty stays under ~13 mHa.

No point in the 481,845-shape legal grid satisfies 1–2 with a measured-supported
fit, and the measured-frontier maximum is +0.16 GM at `(8,129,44)` which fails
precision by 32 %. **Conclusion: chemistry's shape axis is at its corner; the
remaining chemistry value is in loader synthesis at fixed shape, not in shapes.**
