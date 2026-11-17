# Independent verification of four sweep-byte files — 2026-11-16/17

Scope: the four byte-new files from `RESULT_sweep2.md` §1 (kernel-claim only, never
independently verified). Known bytes (`f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/
`0af21cb8`/`5eeea23b`/`bdae290f`/`sub1`/`f6e12f02`/`703843d3`/`0bd9c68f`/`eea2d627`-research-only)
were NOT re-verified. Local work limited to sha256 + zip/log reads (no simulation, no
verifier runs). All grading runs are the UNCHANGED official verifiers at FULL shots on a
Kaggle CPU kernel (DQI 102,400, chem 78,080; default salt + 2 extra salts for every PASS).
Nothing submitted; pipeline decides.

## 0. Verdict

**All four PASS at the default salt (full shots), and PASS at 2 extra salts each
(12/12 PASS).** Both DQI claims reproduce to the digit at the default salt.

| file | sha256 (full) | size | claim | verified (default salt, full shots) |
|---|---|---:|---|---|
| DQI `f425ea20` | `f425ea20c4a3700af5d08868d41b8a8853813fc64eddbfd6137a838395795002` | 480,415,367 | PASS 346992317312.82, 0/0 (boristown `reproduction_audit.json` official JSON; 2nd claim asterios `receipt.json`) | **PASS 346992317312.81555**, 102,400 shots, 890Q, mean T 367733.43387695315, 0/0 |
| DQI `b0983d55` | `b0983d55f58db5b743702bf269683e30a7fe9eacccafa9607c8d930d0327eb27` | 480,413,639 | engine-only 347045216047.32, mean T 367789.49 (`checks.csv`) | **PASS 347045216047.3212**, 102,400 shots, 890Q, mean T 367789.4945800781, 0/0 |
| chem `a970f175` | `a970f1753e1d9ab610c0dcd6ab50b0dd9a77e222611d760b4114c05465f38832` | 1,847,692 | unknown (no score in kernel log) | **PASS 294762689.353492**, 78,080 shots, T14712, λ 46.92161146686036 |
| chem `93326853` | `93326853f42800cc5bb6cf8cac44cce456ebf20e01986ae4b1edc13b485b9c9e` | 1,847,692 | implied ≈ 294762409 ± ~160 (from claimed combo 28.12770) | **PASS 294762512.64351326**, 78,080 shots, T14712, λ 46.921583337394644 |

Extra salts (same pair as `RESULT_verify_new`: `qcc-rebase-refit-8ad413d9…`,
`qcc-rebase-refit-3b61c944…`): all PASS. Chem scores are salt-invariant (identical to
all digits); DQI varies per draw (sampling), all PASS:

| file | salt 8ad413d9 | salt 3b61c944 |
|---|---|---|
| `f425ea20` | PASS 348585800615.90533 (**1 value error**, 0 phase; worse score = larger R) | PASS 346992211342.40283, 0/0 |
| `b0983d55` | PASS 347044985354.3402, 0/0 | PASS 347045638537.53455, 0/0 |
| `a970f175` | PASS 294762689.353492 (identical) | PASS 294762689.353492 (identical) |
| `93326853` | PASS 294762512.64351326 (identical) | PASS 294762512.64351326 (identical) |

Notes:
- `93326853` verified at 294762512.64351326 — inside the implied window, and **0.2161
  cheaper than `703843d3` (294762512.8596263)**. It is now the cheapest verified chem
  (see §5). The 28.12770 combo claim inverts to ≈ 294762409 only because 5-dp rounding
  of the GM loses the last ~100 units; exact score is above.
- `a970f175` (294762689.353492) is the most expensive verified chem so far (+176.5 vs
  `703843d3`); PASS but not pipeline-useful except as spare.
- `f425ea20` salt-8ad413d9 drew 1 value error (empirical rate 9.77e-6, R 1.19673 vs
  1.19126) — pure draw noise, still PASS; the other two salts are clean 0/0.

## 1. Identity (local hash + zip listing only)

Downloads (Kaggle CLI, account zhuating): `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler`
(20:30, 51 MB `submission.zip`), `leotang09/vqcc-t7421-submission` (22:46, 51 MB
`submission.zip`, sha `24d131d6…`), `manwithacat/vqcc-hedge-wizardry-notebook` (22:18,
51 MB `submission.zip`, sha `0b6fde7d…`), `ratnachand/vqcc-verified-floor-and-circuit-anatomy`
(20:30, 51 MB `submission.zip` + `ratnachand/vqcc-verified-public-floor` dataset 20:29).

- `f425ea20` byte-identical in boris and leo zips (480,415,367 B). Borise/leo invsqrt =
  known `0af21cb8`; boris chem = known `0bd9c68f` (not re-verified).
- `b0983d55` in man zip (480,413,639 B); man chem = known `703843d3`, invsqrt = known
  `0af21cb8` (not re-verified).
- `a970f175` in leo zip (1,847,692 B). `93326853` in ratna zip (1,847,692 B); ratna dqi
  = known `66b4f18b` (480,411,479 B), invsqrt = known `0af21cb8` (not re-verified).
- All four zips share byte-identical 15 loaders (`aed6aa7c…` … `ab06b98f`,
  sizes 415169…362314), same pinned set as `RESULT_verify_new` §1; re-corroborated by
  leo kernel log (prints all 15 hashes) and local hashes.

## 2. Verification kernel (CPU only, no submission)

- Kernel **`zhuating/qcc-verify-new2` v1** (script `verify_new2.py`, CPU, no GPU/TPU/internet),
  status **COMPLETE** 2026-11-16 23:41:10Z → 23:57:10Z (~16 min; chem ~23–27 s per full
  run, DQI ~133–140 s per full run).
- Inputs: `zhuating/qcc-verify-new2-files` (20 files: the 4 candidates + 15 shared loaders +
  `pins.json`; all staged by sha256 after locate-by-hash) + competition mount
  `google-verifiable-quantum-circuit-compilation`.
- Unchanged-verifier assertion (same pins as pipeline v5 / `RESULT_verify_new` §2, all MATCH):
  `verifiers/dfthcsos/verify.py` = `0775be7a…b8ec9d`,
  `verifiers/dqi/verify_submission_dqi.py` = `f14274bc…94e65`,
  `verifiers/invsqrt/verify_submission_invsqrt.py` = `ddef520d…073fa`;
  `kickmix/kickmix.so` = `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`
  (same kickmix hash as aditya's `variant_validation.json`).
- Invocation: `[py, verify.py, <file|run_dir>]` with no shot flags (defaults = full
  102,400 / 78,080), plus `--salt S` for the two extra salts; `JAX_PLATFORMS=cpu`.
  Chem run-dirs = candidate npz + the 15 pinned loaders. DQI ran as direct `.kmb` files.
- Outputs: `verify_results.json` (staged hashes, official JSONs, per-salt summary) + per-run
  stdout/stderr logs + restaged inputs (working dir only, nothing submitted).

## 3. Exact official JSONs (default salt, full shots)

### DQI `f425ea20` — PASS (reproduces boristown's `reproduction_audit.json` and asterios's `receipt.json` to the digit)

```json
{"status": "PASS", "score": 346992317312.81555, "m": 4095, "n": 70, "degree": 12, "r": 2016, "verified_shots": 102400, "value_errors": 0, "phase_errors": 0, "empirical_error_rate": 0.0, "effective_error_rate": 0.0008660587301657926, "log2_delta": -128.0, "repetition_factor": 1.1912604648115832, "mean_error_weight": 31.046737331746634, "toffoli_count": 367733.43387695315, "max_toffoli_count": 368606, "reaction_depth": 40196, "num_ops": 57667218, "num_qubits": 890, "num_bits": 59815, "circuit_sha256": "f425ea20c4a3700af5d08868d41b8a8853813fc64eddbfd6137a838395795002"}
```

Extra salts: `8ad413d9` → PASS 348585800615.90533 (value_errors 1, phase 0,
empirical 9.765625e-06, effective 0.0009104197583220583, R 1.1967314991687559, mean T
367733.2981835937); `3b61c944` → PASS 346992211342.40283 (0/0, R 1.1912604648115832,
mean T 367733.32157226565). Same circuit_sha/max_toffoli/depth/bits in all three.

### DQI `b0983d55` — PASS (reproduces manwithacat's `checks.csv` 347045216047.3212 to the digit; the first official-verifier grading of this file — prior was kickmix-engine only)

```json
{"status": "PASS", "score": 347045216047.3212, "m": 4095, "n": 70, "degree": 12, "r": 2016, "verified_shots": 102400, "value_errors": 0, "phase_errors": 0, "empirical_error_rate": 0.0, "effective_error_rate": 0.0008660587301657926, "log2_delta": -128.0, "repetition_factor": 1.1912604648115832, "mean_error_weight": 31.046737331746634, "toffoli_count": 367789.4945800781, "max_toffoli_count": 368662, "reaction_depth": 40196, "num_ops": 57667026, "num_qubits": 890, "num_bits": 59894, "circuit_sha256": "b0983d55f58db5b743702bf269683e30a7fe9eacccafa9607c8d930d0327eb27"}
```

Extra salts: `8ad413d9` → PASS 347044985354.3402 (0/0, mean T 367789.2500976563);
`3b61c944` → PASS 347045638537.53455 (0/0, mean T 367789.94232421875).

### chem `a970f175` — PASS (first grading of any kind; no kernel score existed)

```json
{"status": "PASS", "score": 294762689.353492, "lambda_eff": 46.92161146686036, "toffoli_count": 14712.0, "num_qubits": 427, "brot": 8, "batch_size": 5, "num_circuits": 15, "reaction_depth": 176, "num_ops": 606711, "verified_shots": 78080, "submission_sha256": "75938ca180583b82a7028e8364aead03ff746271c6fc2e1916a0e08a8645ddfe", "metrics": {"error_1": 0.019999998500003037, "error_2": 0.019999998499999935, "Lambda": 283.14454669550213, "E_SOS": -22144.188248017654, "E_gap": 3.9148980176541954, "lambda_eff": 46.92161146686036, "gap_in_domain": true}}
```

Both extra salts: PASS 294762689.353492 identical (resources block identical to the
`703843d3`/`0bd9c68f` shape: same 14712 T / 427Q / 176-depth / 606711-ops envelope).

### chem `93326853` — PASS (first exact score; ratnachand's "≈ 294762409" was a 5-dp-rounding inversion)

```json
{"status": "PASS", "score": 294762512.64351326, "lambda_eff": 46.921583337394644, "toffoli_count": 14712.0, "num_qubits": 427, "brot": 8, "batch_size": 5, "num_circuits": 15, "reaction_depth": 176, "num_ops": 606711, "verified_shots": 78080, "submission_sha256": "bc046fa7572e32052ce094a9c078972ce5cad82a1588538e040a13b2da2f2771", "metrics": {"error_1": 0.019999999967803092, "error_2": 0.019999999958312698, "Lambda": 283.14421079435954, "E_SOS": -22144.188248000246, "E_gap": 3.914898000246467, "lambda_eff": 46.921583337394644, "gap_in_domain": true}}
```

Both extra salts: PASS 294762512.64351326 identical.

## 4. Asterios recheck (was RUNNING at sweep close)

`asteriospanoras/qcc-28-1277-frontier-finer-chemistry-refit` is now COMPLETE (23:29 UTC).
Its only output file is `receipt.json` — **no new downloadable `.npz`/`.kmb`** (the kernel
log shows a `submission.zip` written to `/tmp` but never saved as output). Receipt contents:
- DQI `f425ea20` official-verifier PASS 346992317312.81555 (independent 2nd kernel-claim,
  matches boristown to the digit; now superseded by §3's independent verification).
- chem `submission.npz` sha `f05297b4a490e811ef613c62974a16df4c967ce537f95b1b37c7230f05243895`
  with score 294762512.8596263 / `submission_sha256 59bd9047…` — i.e. `703843d3`-identical
  score, repackaged container (different file hash, same weights grading). Not downloadable,
  no action.
- invsqrt `0af21cb8`, combo line `GM 28.13137` (= §5's 0af+f425+703843d3 recompute).
- No finer-refit chem weights materialized as an output file — §2's chem-swap standing.

## 5. Context GMs (local arithmetic only, refs 2076774.233715 / 24439463583672.93 / 3355599588.3155375)

Verified legs: invsqrt `0af21cb8` 74797.36535717871 (`RESULT_verify_new` §0/§3),
DQI `f425ea20` 346992317312.81555 + `b0983d55` 347045216047.3212 (§3),
chems `93326853` 294762512.64351326 + `703843d3` 294762512.8596263 + `a970f175` 294762689.353492.

| combo (0af + DQI + chem) | GM |
|---|---|
| `f425ea20` + **`93326853`** (cheapest verified chem) | **28.131370656** |
| `f425ea20` + `703843d3` | 28.131370649 (Δ −6.9e-09 vs above) |
| `f425ea20` + `a970f175` | 28.131365034 (Δ −5.6e-06) |
| `b0983d55` + `93326853` | 28.129941265 |
| `b0983d55` + `703843d3` | 28.129941258 (= manwithacat's `check.json` 28.129941258441313) |
| `b0983d55` + `a970f175` | 28.129935644 |

- `93326853` is the cheapest verified chem (Δ −0.2161 vs `703843d3`, −0.0204 vs `0bd9c68f`
  294762518.6638708); the GM gain over `703843d3` on fixed legs is only ~7e-9 (FP noise
  ~1e-13, so the sign is real but the magnitude is negligible for slot decisions).
- `f425ea20` beats `66b4f18b` by +0.00368 GM on same legs (28.13137066 vs 28.12769291);
  `b0983d55` adds only +0.00225 (28.12994127), roughly 60% of the f425 gain at the same
  890Q/368k-T class.

## 6. Gate flag for pipeline (no submission made by this task)

**`f425ea20` verified PASS at the claimed score to the digit (12/12 incl. extra salts).**
Gate combo **invsqrt `0af21cb8` (verified 74797.36535717871) + DQI `f425ea20` (verified
346992317312.81555, §3) + cheapest-verified-chem `93326853` (verified 294762512.64351326, §3)**
with the standard refs:

**GM = 28.131370656** (ratios 27.76533938 / 70.43229018 / 11.38407852) — clears the
28.09490 gate by a wide margin (~28.1314+ as anticipated).

Cheapest-leg alternative with the same DQI+invsqrt and `703843d3` gives 28.131370649
(identical to 8 dp); pipeline owns the slot/allocation decision. No package built, no
slots spent, no submission made. Kernel refs: boristown 20:30 rerun, leotang09 T7421 22:46
(`24d131d6…`, candidate_ids 2237/2239/2235), manwithacat 22:18 (`0b6fde7d…`),
ratnachand 20:30 + `vqcc-verified-public-floor` 20:29, asteriospanoras finer-refit 23:29
(receipt-only); verification kernel `zhuating/qcc-verify-new2` v1 + dataset
`zhuating/qcc-verify-new2-files`.
