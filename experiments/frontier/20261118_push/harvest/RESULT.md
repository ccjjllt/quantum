# Harvest line — public artifacts and frontier (closed 2026-11-18 02:05)

Scope: sweep the public notebooks/datasets/discussions for any component cheaper than our
verified legs, and check the top teams' public traces. Everything below is either measured by
the unmodified official verifiers (ours or the publisher's published receipt) or explicitly
marked unverified.

## Verdict

**The public frontier is our package.** `atakanaldemir/qcc-shared-products-and-controlled-refits`
reports an **observed public score 28.18070** with the identical members: invsqrt `563d0583`,
DQI `575b043f`, chem `703843d3` weights on the 4,022-Toffoli loaders. Our verified package is
**28.180659** with `a73b25d2` weights (the only difference is the chem weight file, 837.97 cost
units apart = 2.8 ppm). No public artifact beats any of our three legs.

## Public files checked (sha / published official cost)

| artifact | task | status |
|---|---|---|
| `563d0583` (maoxin123 / junmiaotiao frontier notebook) | invsqrt | **74,560.90 — identical bytes to ours; the public floor** |
| `f2cdab0b` / `8b410e77` / `0af21cb8` | invsqrt | 75,006.38 / 75,038.13 / 74,797.37 (all worse) |
| `575b043f` (grantprater / jezzlin / atakan) | DQI | **346,409,762,292.72 — ours; best of the five public files at 3 salts** |
| `61c8348d` / `66b4f18b` / `ccc2ab84` / `d54d3387` | DQI | 348.00e9 (loses a shot on all 3 salts) / 347.13e9 / 347.38e9 / 347.34e9 |
| `a73b25d2` / `703843d3` chem weights | chem | 294,643,137.73 / 294,642,299.76 (the latter −838, 2.8 ppm; public frontier uses it) |
| 4,022-Toffoli loaders | chem | byte-identical to ours (`angle_k_0` sha `ed648708…`) |
| `vumaniacom/qcc-verified-portfolio-and-where-the-gap-to-32-is` | — | a 28.145 portfolio; despite the title it contains no gap analysis and no new circuit |
| `asteriospanoras/qcc-28-1277-frontier-finer-chemistry-refit` | chem | 3-minute weight refit of the same 703843d3 family; no new floor |
| `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` | all | our own 28.180686 estimate, same members |
| `srinath2495/vqcc-portfolio-v23-regenerator` | all | regenerator of the v23 portfolio; no cheaper leg |
| `manwithacat/vqcc-hedge-wizardry`, `jezzlin/*` | DQI | mirrors of the same public files |

## Top-team traces

The 29.98–31.43 teams (Z3C1oherence 31.42723, aadi_stonks 31.01379, Entangled Team 30.28512,
Rithvik Redrouthu 30.13063, Yicheng Guang 30.00881, Schrödinger's cat 29.97900, Slingshot
Effect 29.57281) have **no public notebook or dataset** with their per-leg costs. Their scores
sit 1.8–3.3 GM above the public frontier, which — from our measured ceilings — cannot be
reached by any permutation of the public members: it needs a fundamentally cheaper DQI
decoder (see `dqi_algo/`) and/or a general loader product decomposition (see `gendecomp/`).

## Frontier literature (read, not implemented)

* arXiv:2510.10967 (the reference DQI decoder): the reference generator is 1,893 Q /
  5,725,108 mean T (verified by us on the competition's own `sample_submission/dqi.kmb`).
  Our tape is 890 Q / 367,116 T = 2.1x narrower and 15.6x cheaper in T. The paper's
  "2nb" schemes are wider than our tape (the published space optimum is 1,680 Q), so they
  are not a route to a lower score.
* arXiv:2308.12352 (invsqrt): our 44 Q / 1,454 Toffoli / 33-rotation circuit is the public
  floor; the 33 rotations are within 1 of the dyadic-ladder lower bound (measured).
* DF-THC state preparation: the cost model is fixed (`SpinFreeData_V1`); our measurements
  close every model parameter except the loader Toffoli count, which is at its 150-cut floor.

## What would change the verdict

Only a new DQI decoder generation (T <= 265k at 890 Q, or Q <= 840 with T <= 300k) or a
general GF(2) loader decomposition below 188 products. Both are open research lines, not
harvest items.
