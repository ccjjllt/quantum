# Fresh sweep 19:27 UTC → 23:27 UTC + chem-swap math — 2026-11-16

Method: `kaggle kernels list -s {qcc,quantum} --sort-by dateRun`, `kaggle datasets list
-s {qcc,vqcc,quantum-circuit} --sort-by updated`; downloaded every candidate < 200 MB,
`shasum -a 256` every `.kmb`/`.npz` against known
`f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/`5eeea23b`/`bdae290f`/`sub1`/`f6e12f02`/`703843d3`/`0bd9c68f`.
Local work limited to hash + zip-listing + log/audit reads (no simulation, no verifier runs).
Nothing submitted.

## 1. Sweep table (window 2026-11-16 19:27 UTC → 23:27 UTC; now = 23:27 UTC)

Byte-new files (not in the known set):

| file | kind | sha256 (full) | size | claimed score | source | verify status |
|---|---|---|---|---|---|
| `f425ea20` | DQI | `f425ea20c4a3700af5d08868d41b8a8853813fc64eddbfd6137a838395795002` | 480,413,xx (zip member) | **346,992,317,312.82**, 0/0 (boristown `reproduction_audit.json` official-verifier JSON) | boristown 20:30 rerun output; also repackaged byte-identical in leotang09 T7421 22:46 zip | kernel-embedded official JSON claim; NOT independently re-verified here |
| `b0983d55` | DQI | `b0983d55f58db5b743702bf269683e30a7fe9eacccafa9607c8d930d0327eb27` | 480,413,639 B | **347,045,216,047.32**, mean T 367789.49, 0/0 (`checks.csv`; kickmix-engine, NOT official verifier) | manwithacat hedge-wizardry-notebook 22:18 (`submission.zip`, 18 members, sha `0b6fde7d…`) | kernel-claim only (engine simulator); needs official-verifier run |
| `a970f175` | chem npz | `a970f1753e1d9ab610c0dcd6ab50b0dd9a77e222611d760b4114c05465f38832` | 1,847,692 B | **unknown** (no score in kernel log; manifest dataset not located) | leotang09 T7421 22:46 zip (loaders = known 15-set per kernel log) | unscored; needs official-verifier run |
| `93326853` | chem npz | `93326853f42800cc5bb6cf8cac44cce456ebf20e01986ae4b1edc13b485b9c9e` | 1,847,692 B | **implied ≈ 294,762,409 ± ~160** (inverted from notebook-claimed combo 28.12770, 5-dp rounded; see §3) | ratnachand floor kernel 20:30 zip + `vqcc-verified-public-floor` dataset 20:29 | kernel-claim only ("re-run with official verifiers" per notebook text, no exact score published); needs official-verifier run |
| `eea2d627` | DQI | `eea2d627326328cfce2ebdf1791c1097c01c268cacafc60254ee432ad0ed4028` | 480,413,857 B | **none** (research artifact; static T 368,336; `GF24_MERGE400_RETAINED14_STRUCTURAL_PASS_FRESH_FULL_PENDING`, no verifier grading, no submission ZIP) | atakanaldemir 21:54 rerun output | unscored research file, do not use |

Known-bytes-only (all members hashed, no new bytes):

| candidate | verdict |
|---|---|
| igorholt `vqcc-28cluster-field-circuits` dataset (20:06, 22 MB) | invsqrt `0af21cb8`, DQI = `66b4f18b` (inside `dqi.kmb.xz`, decompress-verified), chem `703843d3`, loader `angle_k_0` = `aed6aa7c` |
| pramitdas `qcc-public-frontier-28-1277` dataset (18:42, pre-window bonus check) | `0af21cb8` + `66b4f18b` + `703843d3` (SHA256SUMS pins all 18); SOURCES claims GM 28.127697 but with chem 703843d3 the recompute is 28.12150-class (see §2; treat their GM line as inconsistent) |
| ahoirg `qcc-reproducible-circuit-portfolio` (19:45) | `0af21cb8` + `00ac37d4` + `703843d3` (+ embedded PASS JSONs matching verified scores) |
| alexchilton audit (19:55) | `0af21cb8` + `66b4f18b` + `703843d3` |
| evgendvorkin EDA (20:40) | `0af21cb8` + `66b4f18b` + `703843d3` |
| boristown 20:30 rerun | `0af21cb8` + **`f425ea20`** (new, §1) + `0bd9c68f` |
| atakan iso-gap kernel (Nov 13, ratna SOURCE trace) | old bytes only (`dcde7078`/`821bf8d1`/`56913801`); not the 93326853 source |
| igorholt kernels 20:10/20:26 | no output files |
| manwithacat `vqcc-hedge-wizardry` dataset (22:16, 380 MB) | over 200 MB, download skipped per mandate (kernel output already covers its `b0983d55`) |
| grantprater `vqcc-dqi-61c8348d-merged-closings` (23:11, size 0) | empty placeholder dataset, nothing to download |

**Blocker:** `asteriospanoras/qcc-28-1277-frontier-finer-chemistry-refit` (23:07, "Finer
Chemistry Refit") is still `RUNNING` at 23:27 UTC — its output could not be pulled. Recheck
after it completes; a finer chem refit is exactly the file class that could move §2.

## 2. Chem-swap math (local arithmetic only)

Fixed legs: invsqrt `0af21cb8` = 74,797.36535717871, DQI `66b4f18b` = 347,128,304,010.81165.
Refs: 2076774.233715 / 24439463583672.93 / 3355599588.3155375.
Ratios: r_inv = 27.76533937790204, r_dqi = 70.40469849704834.

| chem x | score | r_chem | GM(0af+66b4+x) |
|---|---|---|---|
| `bdae290f` (pipeline choice) | 294,762,632.0817748 | 11.384073905896617 | **28.127692910871872** |
| `703843d3` | 294,762,512.8596263 | 11.3840785103958 | **28.12769670312652** |
| `0bd9c68f` | 294,762,518.6638708 | 11.384078286228984 | 28.127696518503285 |

**Winner: `703843d3`**, GM 28.12769670312652 — beats pipeline's `bdae290f` choice by
**ΔGM = +0.000003792 (≈ +3.79e-06)**. `0bd9c68f` is second (+3.61e-06 over bdae).
`703843d3` is the cheapest verified chem (Δcost −119.22 vs bdae), so this follows directly;
the pipeline doc's "`bdae290f` maximizes GM per RESULT_verify_new §5" line is not supported by
§5 (which never ranks the three chems against the same DQI+invsqrt legs) and is contradicted
by the arithmetic above (FP noise ~1e-13, far below the 3.8e-6 gap).

**Flag for pipeline (no submission made by this task): the pipeline's submitted bdae leg is
NOT the GM-maximal verified chem; `703843d3` (already verified PASS 294762512.8596263,
RESULT_verify_new §0/§3) gives +3.79e-06 GM on the same 0af+66b4 legs.** Whether a 3.8e-6
gain is worth a slot is pipeline's call.

Loader identity (§1 RESULT_verify_new confirmed): all three verified chems share byte-identical
15 loaders (`aed6aa7c…` … `ab06b98f`, sizes 415169…362314), pinned and reused across run-dirs.
Re-corroborated this sweep: pramitdas SHA256SUMS lists the identical 15 hashes; Leo kernel log
prints the identical 15 hashes; manwithacat `check.json`/receipt EXPECTED dict identical;
ratnachand EXPECTED dict identical; local `angle_k_0` hashes from ratna_floor + igor_field both
`aed6aa7c…`. The swap is weights-only, no loader risk.

Context (kernel-claim, unverified — for pipeline awareness, not action):
- `f425ea20` (boristown official-JSON claim 346,992,317,312.82) + 0af + `0bd9c68f` recomputes to
  GM **28.13137046**; + `703843d3` would be marginally higher still. Needs independent verification.
- `b0983d55` (engine-only claim 347,045,216,047.32) + 0af + `703843d3` recomputes to single-draw
  GM **28.12994126** (matches their `check.json`); expected-48-draw 28.10960 per their log.
  Needs official-verifier run.
- `93326853` implied ≈ 294,762,409 (from claimed 28.12770): cheaper than all three verified
  chems if the rounded GM inverts cleanly, but ±~160 uncertainty from 5-dp rounding — exact
  score unknown, needs official-verifier run.

## 3. Kernel refs / blockers (no submission)

- New-byte sources: `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` (20:30 run,
  `reproduction_audit.json` embeds the `f425ea20` official-verifier PASS JSON);
  `leotang09/vqcc-t7421-submission` (22:46, `submission.zip` sha `24d1316…`, candidate_ids
  invsqrt 2237 / dqi 2239 / dfthcsos 2235; lineage in kernel source comments);
  `manwithacat/vqcc-hedge-wizardry-notebook` (22:18, `submission.zip` sha `0b6fde7d…`,
  `receipt.json` + `check.json` + `checks.csv`);
  `ratnachand/vqcc-verified-floor-and-circuit-anatomy` (20:30) + dataset
  `ratnachand/vqcc-verified-public-floor` (20:29, 55 MB).
- Unscored research: atakan 21:54 `eea2d627` (structural pass only, explicitly
  `FRESH_FULL_PENDING`, no submission ZIP — do not use).
- **Blocker:** asterios 23:07 finer-chem-refit kernel still RUNNING at sweep close — recheck
  and hash its output on completion before any pipeline slot decision.
- No submission made by this task; pipeline owns all slot decisions. Coded-quantizer/R-line
  work untouched per mandate.
