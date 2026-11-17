# RESULT — LB decomposition: what did the leaders improve?

2026-11-17, LB snapshot **2026-11-17T03:30:55Z** (CSV pulled 11:30 local). Read-only intel.
**No simulation, no verifier runs, no submission, no circuit bytes downloaded.** Only three kernel
*sources* (text, 19 KB total) and one 106 KB LB zip were fetched; see §9 for the exact receipts.

Sources read first: `intel/RESULT_topline.md`, `intel/RESULT_stability.md`, `intel/RESULT_sweep4.md`,
`intel/RESULT.md` §3–§4, `TARGETS.md`, `RESULT_verify_new4.md`. `RESULT_public_salt_model.md` does
**not** exist in this directory (checked: `ls | grep -i salt` returns nothing); the salt law used here is
the one stated in the task brief and already validated in `RESULT_stability.md` §4.

---

## 0. Verdict

1. **Snapshot**: 3233 teams. Leader **aadi_stonks 30.96645** (02:42:22 today, 26 subs), passing
   **Z³C¹oherence 30.96223** (11-16 14:36, 51 subs, 4 members). Gold line (rank 16) **28.68633**.
   Our last submission is **28.14703, rank 94**; our unsubmitted frontier (chem `a73b25d2`) is
   **28.15083**, which is rank 77 and the current *public-byte ceiling* (8 teams hold it).
2. **No single leg reaches the top using any floor we can defend.** At the defensible floors the best
   single-leg scores are DQI 840 → **29.257**, chemistry 13,219 (our own R=5/6 projection) → 29.169,
   invsqrt 40 → 29.060. Everything above **29.26** therefore needs either ≥2 legs, or a chemistry
   circuit materially below our own projection (a 12.7k chemistry *alone* would give 29.57 — §6.3 —
   but no such circuit is public and our shape work does not project it). The top-8 are all ≥2 legs.
3. **There is a hard no-chemistry wall at 30.20.** With chem frozen at T=14,706, the best possible
   score is DQI-840 × invsqrt-40 = **30.2016**. Rank 3 (30.28512) and above therefore **must** have a
   cheaper chemistry circuit. This is the strongest statement in this report.
4. **The top-2 need chem ≤ 13,643 T even in the best case** (both other legs at their aspirational
   floors 40Q/840Q). The realistic readings are **chem ≈12.40k with DQI 840** (−15.7% T), or
   **chem ≈12.15k with invsqrt 40**, or **chem ≈11.05k with both legs unchanged** (−24.9% T).
   In every case the chemistry leg is a *new-shape* circuit, not a cleanup of the 4,022/4,025 loader.
5. **The top-2 are the same solution 6 T apart** (Δproduct = 0.041 % ⇒ 6.0 T of chem, or 0.18 DQI
   qubits, or 0.018 invsqrt lines), i.e. one ~3-Toffoli loader refit between them. The margin of the
   top-2 over rank 3 is **0.681 GM = 6.9 % product**, which is exactly one chemistry generation step
   (T 13.26k → 12.40k at DQI 840).
6. **Most plausible single-leg improvement — two different answers depending on the target.**
   *For a single leg to explain 30.96*: chemistry is the only path that is merely very hard rather
   than impossible. DQI-alone needs **Q=771.4**, which is *below the 840Q contract floor*
   (70 syndrome registers × 12 bit) — **impossible by construction**; invsqrt-alone needs **33.06Q**,
   i.e. 11 retired lines from a body whose generator only writes 46/47/48 bodies (no evidence any
   exist); chemistry-alone needs **T=11,048** (−24.9 %), which no public circuit and no projection of
   ours reaches, but is not forbidden.
   *For a single leg to make a real step (gold band and below)*: **DQI width** is the most mechanical
   — its target is a hard discrete floor, public instances already exist 13 qubits below the shipping
   width (877Q in alexchilton's 92-entry census), each qubit is +0.0215 GM, and the move is a
   reschedule of a known circuit family rather than new synthesis. Its ceiling is +1.11 GM (29.257).
7. **No public artifact explains any leader leg.** Newest chemistry anywhere is still maoxin123's
   4,022-Toffoli loader family = T 14,706 (= our own leg). Newest DQI is `61c8348d` 890Q (= our leg).
   No invsqrt < 74,797 exists in any public list examined. The single public claim *below* our legs
   (a GitHub "72,956.40 invsqrt") is **refuted by its own leaderboard badge** (§7).

---

## 1. Snapshot and distribution

CSV: `artifacts/20261117_lb_decomp/google-...-publicleaderboard-2026-11-17T03:30:55.csv`
(3233 data rows; rank 1…3232 — one rank gap in the source). Parsed with
`experiments/frontier/20261116_push/intel/analyze_lb2.py`.

### 1.1 Top 30 (rank order = snapshot order)

| rank | team | score | last submission (UTC) | subs |
|---:|---|---:|---|---:|
| 1 | aadi_stonks | 30.96645 | 2026-11-17 02:42:22 | 26 |
| 2 | Z³C¹oherence | 30.96223 | 2026-11-16 14:36:44 | 51 |
| 3 | Entangled Team | 30.28512 | 2026-11-15 17:15:40 | 99 |
| 4 | Rithvik Redrouthu | 30.13063 | 2026-11-15 15:23:03 | 4 |
| 5 | taiseiu | 30.00881 | 2026-11-15 19:07:37 | 50 |
| 6 | Schrödinger's cat lived | 29.97900 | 2026-11-16 01:29:22 | 53 |
| 7 | yicheng guang | 29.79750 | 2026-11-16 00:03:38 | 51 |
| 8 | Slingshot Effect | 29.57281 | 2026-11-15 14:50:19 | 43 |
| 9 | Christoffer Thimsen | 29.21549 | 2026-11-17 00:26:35 | 12 |
| 10 | Some Joint | 29.14389 | 2026-11-13 20:41:25 | 51 |
| 11 | Annontrix | 28.92164 | 2026-11-17 02:49:44 | 17 |
| 12 | Yair Be'ery | 28.89937 | 2026-11-15 17:01:33 | 69 |
| 13 | Marko Rupnik | 28.82589 | 2026-11-15 13:14:58 | 24 |
| 14 | yu4u | 28.71339 | 2026-11-16 00:35:03 | 8 |
| 15 | trust the transpiler | 28.69153 | 2026-11-16 18:31:14 | 61 |
| 16 | Slow and Steady **(gold)** | 28.68633 | 2026-11-16 09:42:37 | 69 |
| 17 | Dyst-0 | 28.68303 | 2026-11-15 18:39:31 | 5 |
| 18 | Bingran You | 28.59774 | 2026-11-14 14:48:30 | 63 |
| 19 | Sankalp Sanand | 28.59708 | 2026-11-14 14:29:23 | 29 |
| 20 | New Team Name | 28.56411 | 2026-11-13 08:43:47 | 33 |
| 21 | Adisak Sukul | 28.54484 | 2026-11-15 15:59:26 | 53 |
| 22 | mliston | 28.51675 | 2026-11-16 23:35:35 | 27 |
| 23 | Toffoli or Not Toffoli | 28.50969 | 2026-11-17 00:59:21 | 74 |
| 24 | Md Boktiar Mahbub Murad | 28.45154 | 2026-11-17 00:45:57 | 20 |
| 25 | codebeforework | 28.42066 | 2026-11-16 23:44:44 | 80 |
| 26 | Almond Labs | 28.41107 | 2026-11-16 18:05:01 | 12 |
| 27 | kanra824 | 28.37962 | 2026-11-17 02:19:17 | 18 |
| 28 | Diana | 28.37551 | 2026-11-16 21:29:07 | 23 |
| 29 | SM1 | 28.37535 | 2026-11-17 00:42:12 | 19 |
| 30 | rekhasri | 28.37493 | 2026-11-16 19:20:05 | 74 |

Ranks 31–100: appendix A. Compared with `RESULT_topline.md` (00:55 UTC): aadi_stonks added
+0.18354 (30.78291 → 30.96645), Annontrix jumped 28.84750 → 28.92164, and the whole 28.15–28.35
band re-shuffled upward (ranks 24–77 are all new scores).

### 1.2 Score distribution, 0.05-wide bands (28.00 → 31.00)

| band | teams | band | teams | band | teams |
|---|---:|---|---:|---|---:|
| 28.00–28.05 | 17 | 29.00–29.05 | 0 | 30.00–30.05 | 1 |
| 28.05–28.10 | 365 | 29.05–29.10 | 0 | 30.05–30.10 | 0 |
| 28.10–28.15 | 347 | 29.10–29.15 | 1 | 30.10–30.15 | 1 |
| 28.15–28.20 | 33 | 29.15–29.20 | 0 | 30.15–30.20 | 0 |
| 28.20–28.25 | 9 | 29.20–29.25 | 1 | 30.20–30.25 | 0 |
| 28.25–28.30 | 4 | 29.25–29.30 | 0 | 30.25–30.30 | 1 |
| 28.30–28.35 | 4 | 29.30–29.35 | 0 | 30.30–30.50 | 0 |
| 28.35–28.40 | 5 | 29.35–29.40 | 0 | 30.50–30.55 | 0 |
| 28.40–28.45 | 2 | 29.40–29.45 | 0 | 30.55–30.60 | 0 |
| 28.45–28.50 | 1 | 29.45–29.50 | 0 | 30.60–30.65 | 0 |
| 28.50–28.55 | 3 | 29.50–29.55 | 0 | 30.65–30.70 | 0 |
| 28.55–28.60 | 3 | 29.55–29.60 | 1 | 30.70–30.75 | 0 |
| 28.60–28.65 | 0 | 29.60–29.65 | 0 | 30.75–30.80 | 0 |
| 28.65–28.70 | 3 | 29.65–29.70 | 0 | 30.80–30.85 | 0 |
| 28.70–28.75 | 1 | 29.70–29.75 | 0 | 30.85–30.90 | 0 |
| 28.75–28.80 | 0 | 29.75–29.80 | 1 | 30.90–30.95 | 0 |
| 28.80–28.85 | 1 | 29.80–29.85 | 0 | 30.95–31.00 | **2** |
| 28.85–28.90 | 1 | 29.85–29.90 | 0 | | |
| 28.90–28.95 | 1 | 29.90–29.95 | 0 | | |
| 28.95–29.00 | 0 | 29.95–30.00 | 1 | | |

Shape: **712 of 810 teams above 28.0 are in the two public-reassembly bands 28.05–28.15**
(365 + 347). The bands above 28.15 thin out almost immediately (33, 9, 4, 4, 5 …), and above 30.0
there are only **5 teams**. There is no "crowd" at the top: the top-8 are 8 distinct scores.

Cumulative counts (teams ≥ score):

| threshold | teams | meaning |
|---|---:|---|
| 28.09486 | 636 | old public-reassembly band (140 teams exactly) — now **rank ≈497–636** |
| 28.12769 | 319 | earlier public trio (120 teams exactly) |
| 28.14703 | 122 | trio with `703843d3` chem (32 exactly, incl. us at rank 94) |
| **28.15083** | **77** | trio with `a73b25d2` chem — **public-byte ceiling** (8 exactly) |
| 28.2 | 48 | |
| 28.3 | 35 | |
| 28.4 | 26 | |
| 28.5 | 23 | |
| 28.68633 | 16 | gold line |
| 29.0 | 10 | |
| 29.21549 | 9 | |
| 30.0 | 5 | |
| 30.28512 | 3 | |
| 30.96223 | 2 | |

**What each band buys today** (3233 teams ⇒ gold = rank 16, silver = rank 161, bronze = rank 323):

| rank | score | note |
|---:|---:|---|
| 16 | 28.68633 | gold line |
| 100 | 28.14703 | top-100 cut = our submitted score |
| 161 | 28.14049 | **silver cut** |
| 324 | 28.12681 | **bronze cut** |
| 636 | 28.09486 | bottom of the old public band — **no longer a medal** |

So the "public reassembly" score (28.09486) is now **bronze-or-worse**; our 28.14703 is silver with
~0.007 of margin over the silver cut; the unsubmitted 28.15083 is silver with 0.010 margin. Gold is
**−5.50 % product** away (28.68633 vs 28.15083), i.e. one real leg improvement of 5.5 %, not a refit.

### 1.3 Exact-score clusters (the reassembly ladder)

| score | teams | composition (verified by exact GM match, §6.1) |
|---|---:|---|
| 28.09486 | 140 | `f2cdab0b` + `ccc2ab84` + 894aef42-class (**old** public trio) |
| 28.09535 | 34 | `f2cdab0b` + `00ac37d4` + 894aef42-class |
| 28.12769 | 120 | `0af21cb8` + `66b4f18b` + `703843d3` (previous frontier) |
| 28.14703 | **32** | `0af21cb8` + `61c8348d`(clean draw) + `703843d3` = **us** (rank 94) |
| 28.15083 | **8** | `0af21cb8` + `61c8348d`(clean) + **`a73b25d2`** (T 14,706) = the public ceiling |

Everything above 28.15083 (69 teams) is **not** obtainable from public bytes; the 21 teams in
28.15083–28.2 differ only at the 0.001–0.05 GM level (micro-refits: a few T, or a few DQI T̄).

---

## 2. Model, calibration, baseline

`GM = (R1/C_inv · R2/C_dqi · R3/C_chem)^(1/3)`, refs
**2076774.233715 / 24439463583672.93 / 3355599588.3155375** (unchanged).

Our frontier legs and the *measured* cost laws:

| leg | file | cost | law (validated) | unit cost |
|---|---|---:|---|---:|
| invsqrt | `0af21cb8` | 74,797.36535717871 | cost = Q × C, **linear in Q** at fixed shots (200,540,928) | **1,699.940122 per Q** |
| DQI | `61c8348d` (public-salt-clean draw) | 346,413,579,540.4963 | **Q² at fixed T̄**, T̄ linear at fixed Q | 437,335.7 per Q² |
| chem | `a73b25d2` | 294,643,137.73357135 | **cost = 20,035.573081 × T**, linear in T at fixed λ_eff | 20,035.573081 per T |

**GM₀ = 28.150828634070** (ratios 27.76534 / 70.54996 / 11.38869).

### 2.1 Calibration of the two scalings (important correction to the brief)

* **Chemistry is cost ∝ T, not ∝ 1/T.** The two independent points give
  `294,643,137.73357135 / 14706 = 20,035.573081` and
  `294,762,512.64351326 / 14712 = 20,035.516085` — equal to **2.8 × 10⁻⁶ relative**.
  The product `cost × T` is *not* constant (4.3330e12 vs 4.3365e12), and the direction is fixed by
  `TARGETS.md` (T=14,000 scores **higher** than T=14,712; under 1/T it would score lower). So
  `T_required = C_required / 20,035.573081 = 14,706 × P`, where `P = (GM₀/S)³`.
* **DQI is cost ∝ Q²** (not linear). Check against the established single-point table: 890→840 at
  fixed T̄ predicts 29.195 on the old 28.09090 baseline vs the recorded 29.199; the linear model would
  predict 28.642. The `~389 × 10⁶ per qubit` in the brief is only the local slope
  (346.41e9/890); the correct marginal response is 2× that, i.e. −1 qubit = +0.0215 GM at this baseline.
* **invsqrt is cost = Q × C**; `C = 1,699.940122` for our file. Its second sub-axis is C itself
  (Toffoli-equivalent per qubit), which matters for the "one Toffoli less" family of refits:
  at fixed Q=44, cost 56,193 (the 30.966 single-leg value) ⇒ C = 1,277.1.

### 2.2 Independent validation that the inversion is trustworthy

The model reproduces exact leaderboard clusters to the displayed digit, e.g.
`2c125b39 + ccc2ab84 + 894aef42 = 28.085425` (the 9-team 28.08542 cluster), 
`f2cdab0b + 00ac37d4 + 894aef42 = 28.095345` (34 teams), 
`0af21cb8 + 61c8348d(clean) + 703843d3 = 28.147028` (our 32-team cluster),
`0af21cb8 + 61c8348d(clean) + a73b25d2 = 28.150829` (8 teams).
So a score uniquely pins the **product** of the three costs to ~1e-7; the only freedom in §3–§5 is
*which* leg supplies the product.

---

## 3. Single-leg inversion (the requested band table)

Each row holds the other two legs at our frontier. `P = (GM₀/S)³` is the required cost-product
multiplier; `Δproduct` is the change needed. `inv Q` is at fixed C=1,699.940122; `DQI Q` at fixed T̄
(Q² law); `T̄ ratio` is the alternative DQI move at fixed Q=890; `chem T` is at fixed λ_eff.

| score | P | Δproduct | inv cost | inv Q | `C` @44Q | DQI cost | DQI Q | T̄ ratio | chem cost | chem T |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 28.05 | 1.010823 | +1.082 % | 75,606.9 | 44.48 | 1,718.3 | 3.5016e11 | 894.8 | 1.0108 | 297,831,949 | 14,865.2 |
| 28.10 | 1.005436 | +0.544 % | 75,204.0 | 44.24 | 1,709.2 | 3.4830e11 | 892.4 | 1.0054 | 296,244,926 | 14,786.0 |
| 28.15 | 1.000088 | +0.009 % | 74,804.0 | 44.00 | 1,700.1 | 3.4644e11 | 890.0 | 1.0001 | 294,669,158 | 14,707.3 |
| **28.15083 (ours)** | 1.000000 | — | 74,797.4 | 44.00 | 1,699.9 | 3.4641e11 | 890.0 | 1.0000 | 294,643,095 | 14,706.0 |
| 28.2 | 0.994778 | −0.522 % | 74,406.8 | 43.77 | 1,691.1 | 3.4460e11 | 887.7 | 0.9974 | 293,104,546 | 14,629.2 |
| 28.3 | 0.984270 | −1.573 % | 73,620.8 | 43.31 | 1,673.2 | 3.4096e11 | 883.0 | 0.9921 | 290,008,397 | 14,474.7 |
| 28.4 | 0.973909 | −2.609 % | 72,845.9 | 42.85 | 1,655.6 | 3.3738e11 | 878.3 | 0.9870 | 286,955,703 | 14,322.3 |
| 28.5 | 0.963694 | −3.631 % | 72,081.7 | 42.40 | 1,638.2 | 3.3384e11 | 873.7 | 0.9816 | 283,945,702 | 14,172.1 |
| 28.6 | 0.953620 | −4.638 % | 71,328.3 | 41.96 | 1,621.1 | 3.3035e11 | 869.1 | 0.9765 | 280,977,653 | 14,023.9 |
| 28.65 | 0.948636 | −5.136 % | 70,955.5 | 41.74 | 1,612.6 | 3.2862e11 | 866.8 | 0.9740 | 279,509,132 | 13,950.6 |
| **28.68633 (gold)** | 0.945036 | −5.496 % | 70,686.2 | 41.58 | 1,606.5 | 3.2737e11 | 865.2 | 0.9716 | 278,448,517 | **13,897.7** |
| 28.7 | 0.943687 | −5.631 % | 70,585.3 | 41.52 | 1,604.2 | 3.2691e11 | 864.6 | 0.9709 | 278,050,826 | 13,877.9 |
| 28.8 | 0.933891 | −6.611 % | 69,852.6 | 41.09 | 1,587.6 | 3.2351e11 | 860.1 | 0.9657 | 275,164,509 | 13,733.8 |
| 28.9 | 0.924230 | −7.577 % | 69,130.0 | 40.67 | 1,571.1 | 3.2017e11 | 855.6 | 0.9605 | 272,318,002 | 13,591.7 |
| 28.92164 | 0.922157 | −7.784 % | 68,974.9 | 40.58 | 1,567.6 | 3.1945e11 | 854.7 | 0.9593 | 271,707,191 | 13,561.2 |
| 29.0 | 0.914702 | −8.530 % | 68,417.3 | 40.25 | 1,554.9 | 3.1687e11 | 851.2 | 0.9564 | 269,510,622 | 13,451.6 |
| 29.14389 | 0.901220 | −9.878 % | 67,408.9 | 39.65 | 1,532.0 | 3.1219e11 | 844.9 | 0.9494 | 265,538,393 | 13,253.4 |
| **29.21549 (rank 9)** | 0.894611 | −10.539 % | 66,914.5 | 39.36 | 1,520.8 | 3.0991e11 | **841.8** | 0.9458 | 263,590,865 | 13,156.1 |
| 29.3 | 0.886892 | −11.311 % | 66,337.2 | 39.02 | 1,507.7 | 3.0723e11 | 838.2 | 0.9420 | 261,316,612 | 13,042.6 |
| 29.5 | 0.868975 | −13.102 % | 64,997.1 | 38.24 | 1,477.2 | 3.0102e11 | 829.7 | 0.9329 | 256,037,650 | 12,779.2 |
| 29.57281 | 0.862573 | −13.743 % | 64,518.2 | 37.95 | 1,466.3 | 2.9881e11 | 826.6 | 0.9301 | 254,151,163 | 12,685.0 |
| 29.75 | 0.847252 | −15.275 % | 63,372.2 | 37.28 | 1,440.3 | 2.9350e11 | 819.2 | 0.9204 | 249,637,009 | 12,459.7 |
| 29.7975 | 0.843207 | −15.679 % | 63,069.6 | 37.10 | 1,433.4 | 2.9210e11 | 817.3 | 0.9182 | 248,445,076 | 12,400.2 |
| 29.979 | 0.827984 | −17.202 % | 61,931.0 | 36.43 | 1,407.5 | 2.8683e11 | 809.8 | 0.9098 | 243,959,904 | 12,176.3 |
| 30.0 | 0.826247 | −17.375 % | 61,801.1 | 36.36 | 1,404.6 | 2.8622e11 | 809.0 | 0.9090 | 243,447,947 | 12,150.8 |
| 30.00881 | 0.825519 | −17.448 % | 61,746.7 | 36.32 | 1,403.3 | 2.8597e11 | 808.6 | 0.9086 | 243,233,595 | 12,140.1 |
| 30.13063 | 0.815547 | −18.445 % | 61,000.8 | 35.88 | 1,386.4 | 2.8252e11 | 803.7 | 0.9035 | 240,295,281 | 11,993.4 |
| **30.28512 (rank 3)** | 0.803130 | −19.687 % | 60,072.0 | 35.34 | 1,365.3 | 2.7822e11 | 797.6 | 0.8946 | 236,636,636 | 11,810.8 |
| 30.5 | 0.786274 | −21.373 % | 58,811.2 | 34.60 | 1,336.6 | 2.7238e11 | 789.2 | 0.8870 | 231,670,300 | 11,563.0 |
| 30.78291 | 0.764794 | −23.521 % | 57,204.6 | 33.65 | 1,300.1 | 2.6494e11 | 778.3 | 0.8755 | 225,341,335 | 11,247.1 |
| 30.96223 | 0.751583 | −24.842 % | 56,216.4 | 33.07 | 1,277.7 | 2.6036e11 | 771.6 | 0.8671 | 221,448,724 | 11,052.8 |
| **30.96645 (leader)** | 0.751276 | −24.872 % | 56,193.4 | 33.06 | 1,277.1 | 2.6025e11 | 771.4 | 0.8669 | 221,358,202 | **11,048.3** |

Reading: the single-leg requirements are **all ≈ −25 %** at the top (by construction: GM ∝ C^(−1/3),
so a 1.331× product = 24.9 % per leg). What differs is whether the floor permits it (§5).

---

## 4. Two-leg conditional inversion

The tables above assume "only one leg moves". Since the leaders must move ≥2 legs, the useful form is
conditional: *given* a DQI width and invsqrt width, what chemistry is required?

### 4.1 Required chemistry T, by (invsqrt Q, DQI Q)

| inv Q | DQI Q | 28.68633 | 29.0 | 29.21549 | 30.00881 | 30.28512 | 30.78291 | **30.96645** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 44 | 890 | 13,897.7 | 13,451.6 | 13,156.1 | 12,140.1 | 11,810.8 | 11,247.1 | **11,048.3** |
| 44 | 880 | 14,215.4 | 13,759.1 | 13,456.8 | 12,417.6 | 12,080.8 | 11,504.1 | 11,300.8 |
| 44 | 870 | 14,544.0 | 14,077.2 | 13,768.0 | 12,704.7 | 12,360.1 | 11,770.1 | 11,562.1 |
| 44 | 860 | 14,884.2 | 14,406.5 | 14,090.0 | 13,001.8 | 12,649.2 | 12,045.4 | 11,832.5 |
| 44 | 850 | 15,236.5 | 14,747.4 | 14,423.5 | 13,309.6 | 12,948.6 | 12,330.5 | 12,112.6 |
| **44** | **840** | 15,601.4 | 15,100.6 | 14,769.0 | 13,628.3 | **13,258.7** | 12,625.8 | **12,402.7** |
| 43 | 890 | 14,220.9 | 13,764.4 | 13,462.1 | 12,422.4 | 12,085.5 | 11,508.6 | 11,305.2 |
| 42 | 890 | 14,559.5 | 14,092.2 | 13,782.6 | 12,718.2 | 12,373.2 | 11,782.6 | 11,574.4 |
| 42 | 860 | 15,593.0 | 15,092.5 | 14,761.0 | 13,621.0 | 13,251.6 | 12,619.0 | 12,396.0 |
| **42** | **840** | 16,344 | 15,829 | 15,472 | 14,277 | **13,890** | 13,227 | **12,993** |
| 41 | 890 | 14,914.6 | 14,435.9 | 14,118.8 | 13,028.4 | 12,675.0 | 12,070.0 | 11,856.7 |
| 40 | 890 | 15,287.5 | 14,796.8 | 14,471.8 | 13,354.1 | 12,991.9 | 12,371.8 | 12,153.1 |
| **40** | **840** | 17,161.6 | 16,610.7 | 16,245.9 | 14,991.2 | **14,584.6** | 13,888.4 | **13,642.9** |

Bold = the two readings that matter: **DQI 840 alone** (chem 12,403) and **both floors** (chem 13,643).

Note the asymmetry that decides the leader story: the *least demanding* chemistry value at 30.96645 is
**13,643 T**, and it requires **both** other legs at their aspirational floors (40Q and 840Q). If only
DQI reaches its floor, chemistry must be ≤ 12,403 T.

### 4.2 Required DQI Q, by chemistry T (invsqrt fixed at 44)

| chem T | 28.68633 | 29.0 | 29.21549 | 30.00881 | 30.28512 | 30.78291 | 30.96645 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 14,706 | 865.2 | 851.2 | 841.8 | 808.6 | 797.6 | 778.3 | 771.4 |
| 14,500 | 871.3 | 857.2 | 847.8 | 814.4 | 803.2 | 783.8 | 776.9 |
| 14,000 | 886.7 | 872.4 | 862.8 | 828.8 | 817.5 | 797.7 | 790.6 |
| 13,500 | 903.0 | 888.4 | 878.6 | 844.0 | 832.5 | 812.3 | 805.1 |
| **13,219** (our R=5/6 projection) | 912.6 | 897.8 | 887.9 | 852.9 | **841.3** | 820.9 | 813.7 |
| 13,000 | 920.2 | 905.3 | 895.3 | 860.1 | 848.3 | 827.8 | 820.5 |
| 12,500 | 938.4 | 923.3 | 913.1 | 877.1 | 865.1 | 844.2 | 836.7 |
| 12,000 | 957.8 | 942.3 | 931.9 | 895.2 | 883.0 | 861.6 | 854.0 |
| 11,500 | 978.4 | 962.6 | 951.9 | 914.4 | 901.9 | 880.2 | 872.3 |
| 11,000 | 1000.4 | 984.2 | 973.3 | 935.0 | 922.2 | 899.9 | 892.0 |

The 840Q contract floor appears at chem T ≈ **12,404** for the top-2 (12,403 at 30.96645, 12,409 at
30.96223) and at **13,259** for rank 3. That is the single most useful numeric statement in this report:
**a T≈13.26k chemistry plus a 840Q DQI lands on rank 3 (30.285); a T≈12.40k chemistry plus 840Q DQI
lands on the leader (30.966).**

### 4.3 Required invsqrt Q, by chemistry T (DQI fixed at 890)

| chem T | 28.68633 | 29.0 | 29.21549 | 30.00881 | 30.28512 | 30.78291 | 30.96645 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 14,706 | 41.6 | 40.2 | 39.4 | 36.3 | 35.3 | 33.7 | 33.1 |
| 14,000 | 43.7 | 42.3 | 41.3 | 38.2 | 37.1 | 35.3 | 34.7 |
| 13,500 | 45.3 | 43.8 | 42.9 | 39.6 | 38.5 | 36.7 | 36.0 |
| 13,219 | 46.3 | 44.8 | 43.8 | 40.4 | 39.3 | 37.4 | 36.8 |
| 13,000 | 47.0 | 45.5 | 44.5 | 41.1 | 40.0 | 38.1 | 37.4 |
| 12,500 | 48.9 | 47.3 | 46.3 | 42.7 | 41.6 | 39.6 | 38.9 |
| 12,000 | 51.0 | 49.3 | 48.2 | 44.5 | 43.3 | 41.2 | 40.5 |
| 11,500 | 53.2 | 51.5 | 50.3 | 46.4 | 45.2 | 43.0 | 42.3 |
| 11,000 | 55.6 | 53.8 | 52.6 | 48.6 | 47.2 | 45.0 | 44.2 |

Note how bad this path is: with chemistry at 13.2k and DQI untouched, the top-2 would need **36.8 Q**
(eight lines retired) — impossible. Only when chemistry goes to ≈12,000 does the invsqrt requirement
(40.5) come inside the 40Q aspiration. This is why the DQI-840 route is much more attractive than the
invsqrt route.

---

## 5. The three walls, and what the leaders must have done

### 5.1 Single-leg ceilings on our baseline (these supersede `TARGETS.md`'s table by +0.06, because
our baseline moved 28.09090 → 28.15083)

| single move | new GM | ΔGM |
|---|---:|---:|
| invsqrt 44→43 | 28.367 | +0.216 |
| invsqrt 44→42 | 28.591 | +0.440 |
| invsqrt 44→41 | 28.821 | +0.670 |
| invsqrt 44→40 | **29.060** | +0.909 |
| DQI 890→880 | 28.364 | +0.213 |
| DQI 890→870 | 28.581 | +0.430 |
| DQI 890→860 | 28.802 | +0.651 |
| DQI 890→850 | 29.027 | +0.876 |
| DQI 890→840 (**contract floor**) | **29.257** | +1.106 |
| chem 14,706→14,000 | 28.616 | +0.465 |
| chem →13,500 | 28.965 | +0.814 |
| chem →13,219 (our R=5/6 projection) | **29.169** | +1.018 |
| chem →13,000 | 29.332 | +1.181 |
| chem →12,500 | 29.718 | +1.567 |
| chem →12,000 | 30.125 | +1.974 |
| chem →11,048 (leader-as-single-leg) | 30.967 | +2.816 |

### 5.2 Wall 1 — 29.26: the best single leg at a *defensible* floor

`max(inv40, dqi840, chem13219) = 29.257` (DQI). Therefore:

* every score **> 29.257** needs **≥2 legs or a chemistry circuit below 13.2k**; the three legs have
  very different floor characters — DQI has a *hard contractual* floor (840), invsqrt has a practical
  floor (44 for every body that exists), chemistry has **no hard floor at all** (any T is allowed if
  the error gates pass), which is why the chemistry escape hatch exists;
* a chemistry-only solution at T=12,685 would score 29.57281 (see §6.3) — so this wall is a statement
  about *what we can defend*, not a mathematical impossibility;
* the **top-8** (30.00881 … 30.96645) are all ≥2 legs;
* **rank 9 = 29.21549 sits *below* the DQI-floor ceiling** — it is consistent with a *single* leg at
  DQI ≈ 841.8Q (implied), or equivalently 29.2-ish from a near-floor width build. This is the only
  place on the board where a single-leg story is the *cheapest* explanation, and it is exactly where
  the DQI floor predicts it. Ranks 10–20 (29.14 → 28.56) similarly map to implied widths
  844.9 → 870.8 — a smooth width ladder that is *not* visible below 28.15 (see §6.2).
  Alternatively ranks 9–20 are chemistry-only solutions at T = 13,156 → 14,028, which would mean
  nobody in that band has done any width work at all. The board cannot separate the two readings;
  the DQI reading is cheaper because 877Q is public and T<14,000 is not.

### 5.3 Wall 2 — 30.20: chemistry is mandatory above it

Given the DQI contract floor (840Q) and taking 40Q as the invsqrt floor,
`DQI-840 × invsqrt-40 × chem(14,706) = 30.2016`. Therefore:

* **rank 3 (30.28512) and above require a cheaper chemistry circuit** — there is no way around it;
* with the more realistic invsqrt 42, the no-chem ceiling is only **29.72**;
* the five teams above 30.0 are, by construction, chemistry-improved teams.

### 5.4 Wall 3 — the leader's chemistry bound

For S = 30.96645 (`P = 0.751276`):

| assumption | required chem T | chem cut vs 14,706 |
|---|---:|---:|
| inv 44, DQI 890 (chem alone) | 11,048.3 | −24.9 % |
| inv 44, DQI 850 | 12,112.6 | −17.6 % |
| **inv 44, DQI 840** | **12,402.7** | **−15.7 %** |
| inv 42, DQI 860 | 12,396.0 | −15.7 % |
| inv 42, DQI 840 | 12,993 | −11.6 % |
| inv 40, DQI 890 | 12,153.1 | −17.3 % |
| **inv 40, DQI 840 (best case)** | **13,642.9** | **−7.2 %** |

So the *weakest* possible claim is: **the leader's chemistry is at most 13,643 T** (a −7.2 % cut),
and that bound requires simultaneously reaching 40Q invsqrt and 840Q DQI. Every softer assumption on
those two forces chemistry to 12.0–12.6k.

### 5.5 What the leaders most plausibly did

Ranking the decompositions by "how much unproven work each requires":

| # | decomposition | chem T needed | verdict |
|---:|---|---:|---|
| 1 | **chem new shape T≈12.4k + DQI 840** | 12,403 | **most likely** — one new-shape chemistry (−15.7 %) plus the contract-floor width; explains rank 3 too (13,259) and the ladder below |
| 2 | chem T≈12.2k + invsqrt 40 | 12,153 | possible but requires the *hardest* leg (11 lines retired) — less likely than #1 |
| 3 | chem T≈12.4k + DQI 860 + invsqrt 42 | 12,396 | "all three moderate": needs 30 DQI qubits and 2 invsqrt lines; more total work, same chemistry |
| 4 | chem T≈13.6k + DQI 840 + invsqrt 40 | 13,643 | only 7 % chemistry, but needs both aspirational floors; this is the *cheapest chemistry* story and would be the natural rank-3 reading (13,259 at DQI 840 alone) |
| 5 | chem alone at 11.05k | 11,048 | a −25 % T cut with no other leg; beyond our own R=5/6 projection (13,219) by a further 16 %; possible only with a fundamentally better factorization + loader |

The margin structure supports this: **top-2 vs rank 3 = 0.681 GM = 6.90 % product**, which is the
size of one chemistry generation step (13,259 → 12,403 is exactly 6.90 %). The top-2's mutual gap
(0.00422 GM = 0.041 % product) is **6 T** of chemistry — i.e. the same circuit with one ~3-Toffoli
loader refit. That is the signature of a *shared private chemistry family*, refined twice, not of a
lucky salt draw (a DQI salt step is 0.15 % GM, 3.7× larger).

---

## 6. Score forensics: what the arithmetic can and cannot prove

### 6.1 Exact-cluster identification (validated)

The known-combo test (`analyze_lb3.py`) matches every reassembly cluster to the digit — e.g.
28.085425 = `2c125b39`+`ccc2ab84`+894aef42, 28.095345 = `f2cdab0b`+`00ac37d4`+894aef42,
28.147028 = ours, 28.150829 = the 8-team ceiling. This is what makes the *product* inversion
trustworthy. It also means: **a team's score is a fingerprint of its three file costs**. Every cluster
from 28.084 to 28.151 resolves to a known triple; **no score above 28.15083 resolves to any of the 330
triples formable from the known leg inventory**, i.e. every team above the public ceiling uses at least
one leg we do not have.

### 6.2 Integer-lattice residual test (negative result — useful)

For every score ≥ 28.15 I computed the residual to the nearest integer on each of three hypotheses:
chem T integer (`14,706 × P`), DQI Q integer (`890 √P`, clean or ×1.0045925 salt draw), invsqrt Q
integer (`44 P`). Median |residual| (0.25 = uniform null):

| band | n | chem T | chem T (lost draw) | DQI Q | DQI Q (lost) | inv Q |
|---|---:|---:|---:|---:|---:|---:|
| 28.15–28.30 | 38 | 0.247 | 0.261 | 0.211 | 0.183 | 0.099 |
| 28.30–28.60 | 18 | 0.285 | 0.225 | 0.254 | 0.255 | 0.186 |
| 28.60–29.00 | 7 | 0.293 | 0.211 | 0.196 | 0.216 | 0.418 |
| 29.00–30.00 | 5 | 0.198 | 0.241 | 0.204 | 0.130 | 0.346 |
| 30.00–31.00 | 5 | 0.223 | 0.249 | 0.404 | 0.213 | 0.116 |

**No axis shows a clean lattice above 28.15.** In particular the earlier `RESULT.md` §3.3 H1 result
("DQI integer-Q residual median 0.0035 across ranks 16–87") does **not** reproduce on the current
snapshot (median 0.21–0.25). Conclusion: the 28.15–28.7 ramp is *not* a DQI qubit ladder — it is a
mixture of micro-refits on all three legs (DQI T̄ cuts of a few hundred, chem T cuts of a few T,
invsqrt Toffoli counts), consistent with dozens of independent teams doing small private cleanups.
This kills the tempting shortcut "everyone above us just reduced DQI width".

### 6.3 Isolated near-exact chemistry hits (treat as hints, not proof)

Three scores land within 0.01 T of an integer chemistry T under a specific salt assumption:

| score | team | assumed other legs | implied chem T |
|---|---:|---|---:|
| 29.57281 | Slingshot Effect | ours, clean DQI | **12,684.996** (residual 0.004) |
| 28.17320 | Andre | ours, clean DQI | **14,670.995** (residual 0.005) |
| 29.21549 | Christoffer Thimsen | ours, **lost** DQI (×1.0045925) | **13,096.000** (residual 0.000) |

With 77 scores and 4 hypotheses, ~0.15 hits at this precision are expected by chance, so *one* such hit
is not significant; but 28.17320 (T=14,671, i.e. 35 T cheaper than our 14,706) is a plausible real
micro-refit, and 29.57281 at T=12,685 would be the *first* sub-14k chemistry on the board. I list them
because they are falsifiable with a single byte download later; **no weight is put on them in §5.5.**

### 6.4 aadi_stonks' trajectory

| time (UTC) | score | step | product step |
|---|---:|---:|---:|
| 11-16 07:20 | 29.98444 | — | — |
| 11-16 17:51 | 30.78291 | +0.798 | +8.20 % |
| 11-17 02:42 | 30.96645 | +0.184 | +1.80 % |

One big step (8.3 % ≈ a chemistry generation or a DQI 890→850), then a small refit (1.8 % ≈ 260 T of
chem or 8 DQI qubits). Consistent with "one private structural leg + refinement", not with a single
lucky artifact.

---

## 7. Artifact hunt

Method: LB-competition kernel list sorted by `dateRun` (100 rows, newest 03:24:47), plus term searches
`qcc / quantum / vqcc / dfthcsos / invsqrt / dqi`, plus dataset lists sorted by `updated` for the same
terms; two GitHub repository searches and four README fetches. **Nothing > 200 MB downloaded; no
outputs; no verifier runs.** HuggingFace's API was unreachable from this host (transport error on both
attempts) — recorded as *not checked*, not as *nothing there*.

| source | claim | verdict |
|---|---|---|
| `leotang09/vqcc-t7421-submission` (kernel, 02:55, source pulled) | "T7421" is a **label**, not a T-count. Packs `0af21cb8` + `61c8348d` + `a73b25d2` + 15 loaders | = our exact frontier, **28.15083**. No new leg |
| `ratnachand/vqcc-verified-floor-and-circuit-anatomy` (02:45, source pulled) | "verified floor 28.13517", DQI `f425ea20` 3.46992e11 | **worse than our DQI** (`61c8348d` clean 3.4641e11). No lead |
| `maoxin123/qcc-28-14-4-022-toffoli-chemistry-loaders` (02:16) | 4,022 Toffoli/pass | T **14,706** = our chem leg. Public chem frontier moved only 14,712→14,706 (−6 T) |
| `grantprater/vqcc-dqi-61c8348d-merged-closings` (02:32, 137 MB dataset) | 61c8348d with merged patches | = our DQI leg. No new bytes |
| `asteriospanoras/qcc-28-1277-frontier-finer-chemistry-refit` (02:35) | finer λ refit | λ_eff unchanged, 28.1277. No lead |
| `kawh1111/qcomp-harvest-2813`, `aiokajima/...reproduction`, `igorholt/...portfolio`, `ozertuu/...portfolio` | repacks of 28.09–28.13 | all ≤ 28.13. No lead |
| `https://github.com/Javier-Herreros-Pinilla/Google-Quantum-AI---Verifiable-Quantum-Circuit-Compilation` (pushed 11-16 23:09) | **invsqrt 44Q, C=1,658.10 → "72,956.40" (+2.5 % vs ours)**, internal GM 28.358 | **refuted.** Its own LB badge is **28.08542** = `2c125b39`+`ccc2ab84`+894aef42, i.e. the submitted invsqrt is the **75,082.09** file. Claim is unsubmitted and contradicted by the board |
| `https://github.com/leejianrong/quantum-circuit-compilation` (pushed 11-17 02:59) | LB 25.218; own DQI 889Q at 3.63e11 | below public DQI. No lead |
| `https://github.com/kito2718/kaggle_002_VQCC` | Japanese translation docs | no circuits |
| `https://github.com/harshulchess77-arch/Google-Quantum-AI-Verifiable-Quantum-Circuit-Compilation` | Oct-29 repo | no scores |
| Top-team accounts `aadistonks`, `cudacoding`, `honganzhu`, `shanzhong8`, `yannan90` | `kernels list --user` | **no competition notebooks at all** (only unrelated competitions) |

**Bottom line of the hunt:** there is **no public artifact** — Kaggle kernel, dataset, GitHub or HF —
that supplies a leg better than ours. Every public leg is byte-identical to what we already hold:
invsqrt 44Q/74,797 (`0af21cb8`), DQI 890Q/346.41e9 (`61c8348d` clean), chem T=14,706 (`a73b25d2`).
The leaders' improvements are **private**.

---

## 8. Ranked directions

### ① Chemistry new shape (R=5/6 + large C + 791-row Maoxin-class loader), target T 12.4k–13.3k — **the only route past 30.2**

Evidence for:
* Every score > 30.20 requires chemistry (§5.3). The top-2 need ≤ 13,643 T even with both other legs
  at their aspirational floors, and 12,403 T with DQI 840.
* Our own projection `(R,B,C)=(5,143,75)` gives **T ≈ 13,219**; paired with DQI 840 that is **30.315**,
  and the observed rank-3 score 30.28512 corresponds to **T = 13,259** at DQI 840 — a 40 T difference,
  i.e. the same shape family at our projected loader size. A `12.4k` variant of that family, paired
  with DQI 840, is **30.966** (the leader).
* The cleanup path is provably dead (`mizeroluckygall` exact 2,048-address scan: 4,025 T/pass,
  **0 removable** in the correct dirty-word model), and all 266 public chemistry entries are ≥ 14,712.
  So this block is protected: nobody can reach it by editing public bytes.
* Reward: T=13.5k → 28.965 (+0.81); 13.2k → 29.169 (+1.02); 12.4k → 29.798 (+1.65); with DQI 840
  simultaneously, 30.28–30.97.

Evidence against / risk: the R=5 8-bit quantization e2 floor (must stay ≤ 19.9 mHa with B=143),
and our local loader was 26 % worse than Maoxin's, so the T=13.2k projection assumed a loader we have
not yet built. This is the largest work item in the repo.

### ② DQI width 890→870/860 (then 850/840), plus DQI T̄ micro-surgery — the most mechanical axis with a hard target

Evidence for:
* It is the only axis with a **hard, close, contractual target**: 840Q (70 × 12). −1 qubit = +0.0215 GM.
* Public width evidence exists: alexchilton's 92-entry census has **min Q 877**, and the cheapest
  sub-890 file is 889Q at +3.69 % — so low-Q files are not cheap yet, but the width is demonstrably
  reachable below 890 without breaking the decoder.
* Rank 9 (29.21549) sits *below* the DQI-floor ceiling 29.257 and maps to an implied **841.8Q** — the
  board itself shows somebody at/near the floor.
* Reward: 870 → 28.581 (+0.43); 860 → 28.802 (+0.65); 850 → 29.027 (+0.88); 840 → 29.257 (+1.11).
* Pairing 860 with chem 13.2k gives 29.84; pairing 840 with chem 12.4k gives 30.97.

Evidence against: `NR-0259/0260` — 889→888 needs ~3,100 T rebuild against an ~860 T budget; it is a
release-and-recompute rewrite. And §6.2 shows the 28.15–28.7 ramp is **not** a width ladder, so width
work does not explain anyone else's position below 29.2.

### ③ invsqrt 44→43/42 — biggest single-step per line, but the hardest synthesis

Evidence for: +0.216 per line (44→43 = +0.216, →42 = +0.440, →40 = +0.909); a 42Q build plus a
13.2k chemistry lands 29.63 without any DQI work.
Evidence against: all 61 public invsqrt files are 44Q or 46Q; the generator writes only 46/47/48 bodies;
Q45 is blocked at one `alloc_qubits(1)` line; the 0–7 AND ladder is empty (200/200 and 300/300 positive
controls — a real measurement, not a failure). It requires a new body + a new loader certificate.
Per unit of GM it is the most expensive of the three.

### Dead ends (do not spend time here)

1. **Chemistry loader cleanup / don't-care removal.** Exhaustive scan: 4,025 T/pass, 0 removable;
   the zero-word model's 40 candidates all FAIL the official verifier. Closed.
2. **λ_eff refit at fixed words.** Rotation lever 0.0000 %; offsets blocked by the E_gap/e2 gates;
   magnitude changes blocked by e2 (1.5e-6 mHa margin). The corner is real: every independent refit
   converges to 46.9216 ± 1e-5. Worth ≤ 1e-5 GM.
3. **DQI salt re-rolling.** The public score is deterministic per file; the only two states are clean
   and ×1.0045925 (−0.15 % GM). Re-submitting the same bytes cannot improve; a lost draw is a
   permanent 0.04–0.05 GM loss for that file.
4. **Public reassembly.** Ceiling 28.15083, 69 teams already above it; the old 28.09486 band (140
   teams) is now **below the bronze cut** (28.12681). Zero remaining value.
5. **"C43 native compiler" / "C44 universal XOR" / AND-merge refits.** No cheaper bytes: the C43 title
   did not change the 4,025 loader; the C44 emitter is +7.7 % T (317.4e6); joint226 saves 0 on
   `ccc2ab84`. Sub-0.01 GM.
6. **New algorithm families.** Only public "other family" is 442k T / 1,837Q (Q²T far worse); no new
   invsqrt/DQI family in any 11-16/11-17 artifact.
7. **The GitHub "72,956.40 invsqrt".** Contradicted by its own LB badge 28.08542 (= the 75,082.09 file);
   the claimed C=1,658.10 is not backed by any submitted score.

---

## 9. Receipts

* LB: `~/.local/bin/kaggle competitions leaderboard google-verifiable-quantum-circuit-compilation
  --download --csv` with `KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)`; zip 106,371 B →
  `artifacts/20261117_lb_decomp/google-...-publicleaderboard-2026-11-17T03:30:55.csv` (3233 rows).
* Kernel listings: `kaggle kernels list --competition ... --sort-by dateRun --page-size 100 -v`
  (100 rows, newest 2026-11-17 03:24:47) → `kernels_daterun.csv`; term searches
  `-s qcc|quantum|vqcc|dfthcsos|invsqrt|dqi --sort-by dateRun`; dataset searches
  `-s qcc|vqcc|dfthcsos|invsqrt|dqi|quantum-circuit --sort-by updated` → `datasets_qcc.csv`.
* Kernel sources pulled (text only): `leotang09/vqcc-t7421-submission` (9.5 KB .py),
  `kawh1111/qcomp-harvest-2813` (2.1 KB .ipynb), `ratnachand/vqcc-verified-floor-and-circuit-anatomy`
  (7.1 KB .ipynb) → `k_leotang/`, `k_harvest/`, `k_ratna/`. No outputs, no circuit bytes.
* GitHub: `api.github.com/search/repositories?q=quantum+circuit+compilation+kaggle`,
  `...?q=dfthcsos`; READMEs of `leejianrong/...`, `Javier-Herreros-Pinilla/...`, `kito2718/...`.
  HuggingFace `api/datasets?search=vqcc` → transport error (not checked).
* Analysis scripts (local arithmetic only):
  `intel/analyze_lb2.py` (top-100, bands, single-leg inversion, lattice),
  `intel/analyze_lb3.py` (chem/DQI/inv integer lattices, exact-combo match),
  `intel/analyze_lb4.py` (residual medians by band),
  `intel/analyze_lb5.py` (conditional tables, single-leg ceilings, walls).
* No simulation, no verifier run, no local kickmix import, no submission.

### Appendix A — ranks 31–100

| rank | team | score | last | subs |
|---:|---|---:|---|---:|
| 31 | smcEmpty | 28.36440 | 2026-11-17 00:43 | 20 |
| 32 | Karmanya Iyer | 28.32945 | 2026-11-17 00:45 | 24 |
| 33 | Syed Asad Ali | 28.32010 | 2026-11-16 19:03 | 68 |
| 34 | Aman Khanna | 28.31215 | 2026-11-16 17:14 | 47 |
| 35 | Jack Donz | 28.31098 | 2026-11-17 02:51 | 87 |
| 36 | Hello, World! | 28.29657 | 2026-11-16 13:10 | 27 |
| 37 | Joe Penn | 28.28624 | 2026-11-16 20:48 | 13 |
| 38 | Yoshihiko Suzuki | 28.27555 | 2026-11-17 02:30 | 44 |
| 39 | smlcr | 28.27467 | 2026-11-16 00:57 | 13 |
| 40 | David Pilný | 28.24791 | 2026-11-17 02:24 | 87 |
| 41 | ktm | 28.24506 | 2026-11-16 10:57 | 30 |
| 42 | Jongwon | 28.24036 | 2026-11-17 00:40 | 17 |
| 43 | Jan Steindl-Starlinger | 28.23874 | 2026-11-17 00:06 | 50 |
| 44 | maoxin123 | 28.23084 | 2026-11-17 02:33 | 41 |
| 45 | Yuri-M-Dias | 28.22896 | 2026-11-16 19:48 | 40 |
| 46 | Kotaro Terada | 28.21531 | 2026-11-16 23:08 | 58 |
| 47 | chipssy | 28.20919 | 2026-11-17 02:33 | 71 |
| 48 | susuky | 28.20061 | 2026-11-17 03:00 | 67 |
| 49 | catv eg | 28.19073 | 2026-11-15 17:15 | 27 |
| 50 | Norman Swai | 28.18874 | 2026-11-17 00:09 | 54 |
| 51 | sekken | 28.18457 | 2026-11-17 00:03 | 60 |
| 52 | Sagnik Dey | 28.18061 | 2026-11-16 20:22 | 56 |
| 53 | Akshan Sameullah | 28.17910 | 2026-11-17 00:57 | 4 |
| 54 | Andre | 28.17320 | 2026-11-16 16:58 | 82 |
| 55 | megan Park | 28.17086 | 2026-11-17 02:22 | 22 |
| 56 | philip georgiev | 28.16856 | 2026-11-16 19:13 | 70 |
| 57 | Nic Barthelemy | 28.16728 | 2026-11-17 00:02 | 107 |
| 58 | T DeSouza-QuantufAi | 28.16473 | 2026-11-17 02:56 | 41 |
| 59 | Jinwon Baik | 28.16045 | 2026-11-17 02:34 | 29 |
| 60 | itsuki-data | 28.15958 | 2026-11-16 05:27 | 60 |
| 61 | Cody_Null | 28.15892 | 2026-11-15 01:48 | 1 |
| 62 | Kenny Löffler | 28.15748 | 2026-11-15 15:04 | 34 |
| 63 | Hiểu Vy | 28.15547 | 2026-11-16 19:48 | 15 |
| 64 | syouya tobita | 28.15541 | 2026-11-17 00:08 | 66 |
| 65 | Max Freedom Pollard | 28.15344 | 2026-11-17 00:00 | 116 |
| 66 | xthixsl_ml | 28.15227 | 2026-11-17 02:37 | 15 |
| 67 | ETHAN KOH | 28.15143 | 2026-11-17 02:47 | 61 |
| 68 | Yassine Alouini | 28.15109 | 2026-11-17 02:29 | 83 |
| 69 | GCYYfun | 28.15097 | 2026-11-17 02:59 | 13 |
| 70 | CW | 28.15083 | 2026-11-17 02:23 | 28 |
| 71 | ALI MAAD (L3LIM3D) | 28.15083 | 2026-11-17 02:28 | 56 |
| 72 | chikaran | 28.15083 | 2026-11-17 02:37 | 46 |
| 73 | srikalyan | 28.15083 | 2026-11-17 02:38 | 15 |
| 74 | Thadeus Burgess | 28.15083 | 2026-11-17 02:54 | 10 |
| 75 | Chidera Onyebu | 28.15083 | 2026-11-17 02:54 | 12 |
| 76 | Leo Tang | 28.15083 | 2026-11-17 02:58 | 39 |
| 77 | Haoming Yang | 28.15083 | 2026-11-17 03:03 | 15 |
| 78 | yuki0731 | 28.15074 | 2026-11-17 01:15 | 33 |
| 79 | Ali | 28.15050 | 2026-11-16 21:38 | 49 |
| 80 | StupidXie | 28.15017 | 2026-11-17 02:57 | 59 |
| 81 | wangqianlongucas | 28.15011 | 2026-11-17 00:11 | 54 |
| 82 | Quantogolf | 28.14988 | 2026-11-17 02:54 | 44 |
| 83 | Massimiliano Pianges | 28.14906 | 2026-11-17 01:09 | 40 |
| 84 | Uttam Limbani | 28.14855 | 2026-11-16 19:26 | 9 |
| 85 | keiz | 28.14854 | 2026-11-16 20:22 | 59 |
| 86 | Calera Labs | 28.14787 | 2026-11-16 21:39 | 27 |
| 87 | Kevin E R MILLE | 28.14741 | 2026-11-17 01:38 | 51 |
| 88 | Orion Chen | 28.14724 | 2026-11-17 00:01 | 83 |
| 89 | Carlos Bosch | 28.14720 | 2026-11-17 00:55 | 5 |
| 90 | 无上奶蛙大帝 | 28.14714 | 2026-11-17 01:40 | 62 |
| 91 | kotaross | 28.14703 | 2026-11-17 02:31 | 34 |
| 92 | Luon may Man | 28.14703 | 2026-11-17 01:33 | 75 |
| 93 | PavelLiashkov | 28.14703 | 2026-11-17 01:49 | 88 |
| 94 | **ccjjllt** | **28.14703** | 2026-11-17 02:43 | 29 |
| 95 | 38tter | 28.14703 | 2026-11-17 00:58 | 17 |
| 96 | OceFFFF | 28.14703 | 2026-11-17 01:24 | 55 |
| 97 | Golden Path | 28.14703 | 2026-11-16 22:40 | 1 |
| 98 | yuu2704 | 28.14703 | 2026-11-17 00:16 | 48 |
| 99 | Abdoul Aw | 28.14703 | 2026-11-17 00:32 | 22 |
| 100 | OAO noir | 28.14703 | 2026-11-17 00:46 | 30 |

## Addendum (same day) — two corrections from our own measured records

1. **The DQI width ladder is not linear and is not reachable on the current lineage.**
   DQI cost is `≈ 1.19 · Q² · T` (validated on two points: `61c8348d` Q890/T368,139
   → 1.187963; the 888 build in `dqi/RESULT2.md` §2 Q888/T384,003 → 1.191269; the two
   constants agree to 2.8e-3). So "+0.0215 GM/qubit" is only true at constant T; the
   real statement is a **T budget of +12.26 % at Q840, +4.65 % at Q870, +0.45 % at
   Q888**. The measured 888 build spent **+4.3 % T for 2 qubits** (cost 360.72e9 vs
   346.41e9, i.e. **3.7 % worse**), which is the opposite of the budget. `dqi/RESULT2.md`
   §0 already recorded the verdict: *"Stop pursuing Q < 888 on the v12 lineage."*
   Rank 9's implied 841.8Q is therefore **not** a width result — it is a
   `Q²T`-equivalent, and is equally explained by T ≈ 328 k at Q890.
2. **Direction #1 (chem R=5/6 → T 12.4–13.3 k) is already measured closed, not
   open.** `chem/RESULT2.md` §2 and `chem/RESULT3.md` §2 measured the route on the
   real merge pipeline: at the (5,143,75) target shape the continuous error is
   **53.65 mHa, 3.2× the 16.7 mHa gate**, and 8-bit quantization takes it to **73.1
   mHa**. The `T = 13,219` ↔ GM 29.111 figure in `chem/LOADER_R5.md` /
   `LOADER_R5_PORT.md` is a *projection conditioned on accuracy passing*, and it does
   not. The only shape on that route that fits, (5,240,100) at 14.17 mHa, is T ≈ 17.7 k
   — worse than the shipped 14,706.

Net: the three legs are each at their measured floor, and the two "new" directions in
§"Ranked directions" are closed by our own measurements. The surviving question is
therefore not "which known axis" but "does any public byte exist with a cheaper leg" —
sweep5 (03:06→03:44 UTC) found none, and `leotang09` 02:55 is a repack of our own trio.
