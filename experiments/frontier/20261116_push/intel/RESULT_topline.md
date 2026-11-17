# Topline — public leaderboard snapshot + GM inversion — 2026-11-17 ~00:55 UTC

Read-only. No simulation, no verifier runs, no downloads beyond the 106 KB LB zip.
Sources: `RESULT.md` (08:01 11-16 snapshot), `RESCAN.md` (09:41), `RESULT_sweep2.md` §2
(GM context), `TARGETS.md` (single-point table). Snapshot CSV:
`artifacts/20261116_intel/lb3/google-...-publicleaderboard-2026-11-17T00:55:00.csv`
(3224 teams). Command: `kaggle competitions leaderboard -c
google-verifiable-quantum-circuit-compilation -d` (+ `--show --page-size 200 -v`
for the top-30 read).

## 0. Headline changes vs the 08:01 11-16 snapshot

1. **New top, well above old top**: `Z³C¹oherence` **30.96223** (11-16 14:36, 51 subs,
   4 members) and `aadi_stonks` **30.78291** (11-16 17:51 — same team was 29.98444 at
   07:20, **+0.80 in ~10 h**, 25 subs total). Old top `Entangled Team` 30.28512 is now rank 3.
2. **New rank 9**: `Christoffer Thimsen` **29.21549** (11-17 00:26 today, only 12 subs).
3. **Gold line moved up**: `Slow and Steady` 28.65386 → **28.68633** (11-16 09:42, rank 16).
4. **Our combo is now the public-shared band**: 112 teams at exactly **28.12769** —
   that is `0af21cb8` + `66b4f18b` + `703843d3` (GM 28.12769670 → displays 28.12769).
   We (`ccjjllt`) are rank **228**, 28.12769 (26 subs). The old 28.09486 band shrank
   187 → **165** teams.
5. 431 teams now score above 28.09486 (was 91 at 09:41) — almost all of the growth is
   the 28.095–28.15 reassembled-public-frontier cluster, not new 29+ jumps.

## 1. Top-30 (rank order = snapshot order; all scores distinct in top-30)

| rank | team | last submission (UTC) | score |
|---:|---|---|---:|
| 1 | Z³C¹oherence | 2026-11-16 14:36:44 | 30.96223 |
| 2 | aadi_stonks | 2026-11-16 17:51:01 | 30.78291 |
| 3 | Entangled Team | 2026-11-15 17:15:40 | 30.28512 |
| 4 | Rithvik Redrouthu | 2026-11-15 15:23:03 | 30.13063 |
| 5 | taiseiu | 2026-11-15 19:07:37 | 30.00881 |
| 6 | Schrödinger's cat lived | 2026-11-16 01:29:22 | 29.97900 |
| 7 | yicheng guang | 2026-11-16 00:03:38 | 29.79750 |
| 8 | Slingshot Effect | 2026-11-15 14:50:19 | 29.57281 |
| 9 | Christoffer Thimsen | 2026-11-17 00:26:35 | 29.21549 |
| 10 | Some Joint | 2026-11-13 20:41:25 | 29.14389 |
| 11 | Yair Be'ery | 2026-11-15 17:01:33 | 28.89937 |
| 12 | Annontrix | 2026-11-15 16:26:21 | 28.84750 |
| 13 | Marko Rupnik | 2026-11-15 13:14:58 | 28.82589 |
| 14 | yu4u | 2026-11-16 00:35:03 | 28.71339 |
| 15 | trust the transpiler | 2026-11-16 18:31:14 | 28.69153 |
| 16 | Slow and Steady (gold) | 2026-11-16 09:42:37 | 28.68633 |
| 17 | Dyst-0 | 2026-11-15 18:39:31 | 28.68303 |
| 18 | Bingran You | 2026-11-15 14:48:30 | 28.59774 |
| 19 | Sankalp Sanand | 2026-11-14 14:29:23 | 28.59708 |
| 20 | New Team Name | 2026-11-13 08:43:47 | 28.56411 |
| 21 | Adisak Sukul | 2026-11-15 15:59:26 | 28.54484 |
| 22 | mliston | 2026-11-16 23:35:35 | 28.51675 |
| 23 | Toffoli or Not Toffoli | 2026-11-16 19:03:29 | 28.50886 |
| 24 | codebeforework | 2026-11-16 23:44:44 | 28.42066 |
| 25 | Almond Labs | 2026-11-16 18:05:01 | 28.41107 |
| 26 | Diana | 2026-11-16 21:29:07 | 28.37551 |
| 27 | rekhasri | 2026-11-16 19:20:05 | 28.37493 |
| 28 | SM1 | 2026-11-17 00:07:08 | 28.37010 |
| 29 | Md Boktiar Mahbub Murad | 2026-11-16 19:55:57 | 28.35035 |
| 30 | smcEmpty | 2026-11-17 00:00:13 | 28.33818 |

Band counts: >30: 5 teams · 29–30: 5 · 28.6–29: 7 · 28.3–28.6: 16 · 28.15–28.3: 32 ·
28.13–28.15: 61 · 28.09486–28.13: 305. Notable exact-score clusters: 28.12769 ×112
(our trio, see §0.4), 28.09535 ×44, 28.12149 ×26, 28.12101 ×23, 28.13790 ×13,
28.14703 ×7. The last two sit **above** the fully-verified ceiling (see §3, last rows) —
flagged for the sweep tasks, no byte claims made here.

## 2. GM formula and baseline legs

`GM = (Rinv/Cinv · Rdqi/Cdqi · Rchem/Cchem)^(1/3)`, refs
**2076774.233715 / 24439463583672.93 / 3355599588.3155375**.

| leg | file | cost | status |
|---|---|---:|---|
| invsqrt | `0af21cb8` | 74797.36535717871 | verified PASS (`RESULT_verify_new.md` §0/§3) |
| DQI | `66b4f18b` | 347128304010.81165 | verified PASS |
| DQI (alt) | `f425ea20`-class | 346992317312.82 | kernel-embedded official-JSON claim only, NOT independently verified |
| chem | `703843d3` | 294762512.8596263 | verified PASS |

Ratios: r_inv 27.76533938 · r_dqi 70.40469850 (verified) / 70.43229018 (f-class) ·
r_chem 11.38407851.
**Verified-trio baseline GMv = 28.12769670** (matches our 28.12769 display).
With f-class DQI: GMf = 28.13137065 (+0.00367). All inversions below use the verified
GMv; f-class numbers differ by ≤0.04 pp (recomputed spot values in §3 table notes).

Single-point rescale of the `TARGETS.md` table onto the new baseline (same Q²-model
for DQI, linear for invsqrt/chem; cross-checked against `RESULT.md` §3.1 method):
DQI→840Q = **29.233** · invsqrt→40Q = **29.036** · chem T=14000/13500/13000/12000 =
**28.597 / 28.945 / 29.312 / 30.104**.

## 3. Inversion: what each band demands (two legs fixed at verified best)

P = (GMv/S)³ = required cost-product multiplier. Single-leg columns hold the other
two legs fixed. DQI Q-equiv assumes cost ∝ Q² at fixed T (per `RESULT.md` §3.1) and
Q0≈890 — approximate; invsqrt Q-equiv is linear in Q (per `TARGETS.md` convention) —
approximate; chem T-equiv is at fixed λ_eff (46.92158337).

| S (band) | P (Δproduct) | invsqrt-only C (Qlin) | DQI-only C (Q~) | chem-only T (λ-fixed) |
|---|---|---|---|---|
| 28.65 (asked gold) | 0.94630 (−5.370%) | 70,780.7 (41.64) | 328.49e9 (~865.8) | 13,922 |
| **28.68633 (actual gold, rank 16)** | 0.94271 (−5.729%) | 70,512.1 (41.48) | 327.24e9 (~864.1) | 13,869 |
| **29.0** | 0.91245 (−8.755%) | 68,248.8 (40.15) | 316.74e9 (~850.1) | 13,424 |
| 29.21549 (rank 9) | 0.89241 (−10.759%) | 66,749.7 (39.27) | 309.78e9 (~840.8) | 13,129 |
| 30.00881 (rank 5) | 0.82349 (−17.651%) | 61,594.6 (36.23) | 285.86e9 (~807.6) | 12,115 |
| 30.28512 (rank 3) | 0.80115 (−19.885%) | 59,924.0 (35.25) | 278.10e9 (~796.6) | 11,787 |
| 30.78291 (rank 2) | 0.76291 (−23.709%) | 57,063.7 (33.57) | 264.83e9 (~777.4) | 11,224 |
| 30.96223 (rank 1) | 0.74973 (−25.027%) | 56,078.0 (32.99) | 260.25e9 (~770.6) | 11,030 |

Correction to the task prompt's example: gold 28.65 needs **−5.37%** product vs
28.12769, not −8.9%. The −8.9% figure (−8.755%) belongs to the **29.0** band.
(F-class baseline: 28.65 → −5.333%; 29.0 → −8.719%; 30.28512 → −19.853%;
30.96223 → −24.997% — same verdicts.)

Sanity anchor: chem-only T=11030 reproduces rank 1 exactly (30.96228), and the gold
row reproduces `RESULT.md` §3.1's DQI-864.1Q figure (864.1 both times) — method consistent.

## 4. Which leg MUST have moved — verdicts per band

Floors (from `RESULT.md` §3–§4, `TARGETS.md`): DQI Q ≥ 840 (contract), invsqrt Q ≥ 40
in any known-body model (public best 44), chem loader 4025 T/pass proven 0-removable
in the correct dirty-word model (so sub-14712 T needs a new shape/basis, not cleanup).

- **28.65–28.69 (gold): no leg MUST have moved — any single leg can carry it in
  principle.** DQI ~866Q (above 840), invsqrt ~41.5Q-equiv (−5.4% cost), or chem
  T≈13.9k all clear their floors. Public evidence shows none of the three (public
  bests remain 890Q / 44Q / T=14712), so gold = at least one private improvement on
  any axis. Cheapest reading per the rescaled single-point table: chem T≈14,000
  alone gives 28.597, DQI 870-class gives ~28.56 — gold needs a touch more than
  either, i.e. one solid private step on any axis. **Points at: all three axes
  (whoever owns a private step of −5–6% on any single leg takes gold).**
- **29.0: DQI-width is the only single-leg path that stays above a floor**
  (850Q > 840). invsqrt-only would need 40.15Q-equiv — the entire 44→40 jump at the
  floor limit; chem-only needs T≈13.4k (new shape). So 29.0 = either DQI 850-class
  width work **or** a ≥2-leg split. **Points at: DQI width first (890→850 = +0.88,
  lands 29.01), chem shape second.**
- **≥29.22 (rank 9+): DQI-width alone is dead** — 29.21549 needs 840.8Q-equiv at
  fixed T, i.e. the full run to the contract floor with zero margin; anything above
  rank 9 forces a second leg (T cut alongside, or invsqrt/chem help). **Points at:
  DQI width + one more leg (release-and-recompute schedule that also trims T, or
  chem-shape help).**
- **30.28–30.96 (ranks 1–3): all single legs impossible** (DQI 771–797Q « 840;
  invsqrt 33–35Q; chem T 11.0–11.8k). Minimum is a 2-leg split at the floors, e.g.
  DQI-840 (×0.8906) + chem T≈12,379 (30.96) / T≈13,186-class (30.28, cf. `RESULT.md`
  §3.4 — recomputed on GMv this pair gives ~30.33, same neighborhood); a 3-leg
  split such as DQI-840 + invsqrt-41 + chem-T≈13,285 also reaches 30.96. The aadi
  +0.80 jump in 10 h and Z³C¹oherence's 51-sub climb both fit multi-leg private
  stacks, not one lucky refit. **Points at: chem shape (R=5/6-class, T 12–13k) as
  the largest block, DQI width to the 840 floor as the second, invsqrt line-count
  as the third — ranks 1–3 need at least two of the three.**
- **Above-verified-ceiling clusters (28.13790 ×13, 28.14703 ×7): need more than the
  f-class DQI alone** (−0.11% / −0.21% product vs verified trio; f-class covers only
  −0.04%). Consistent with f-class DQI plus a small private touch elsewhere (e.g.
  invsqrt refit ~−0.1/−0.2%, or chem below 703843d3) — i.e. the f425ea20-class leg
  plus ppm-level help. Left for the sweep tasks to source; no byte claims here.

## 5. Axis pointers (unchanged priority, tightened thresholds)

1. **Chem shape** is the only leg with headroom past 30.0 singly (T=12000 →
   30.104) — still the biggest block, still needs R=5/6-class basis+loader, not cleanup.
2. **DQI width** 890→850 decides the 29.0 band and is a mandatory half of any 30+
   split; rank 9 (≈29.22) marks where width-alone exhausts (840 floor).
3. **invsqrt line-count** 44→42 (+0.44-class) decides gold when paired with any
   −2%-class help elsewhere; 44→40 (+0.91-class) is needed singly only at 29.0 and
   is at its floor there.

No submission made. No verifier run. LB zip is 106 KB (under the 50 MB cap).
