# Independent verification of two sweep3 DQI bytes — 2026-11-17

Scope: the two byte-new DQI files from `RESULT_sweep3.md` §1 (kernel-claim only, never
independently verified). The 10 known bytes (`f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/
`0af21cb8`/`5eeea23b`/`f425ea20`/`b0983d55`/`eea2d627`/`bdae290f`/`sub1`/`f6e12f02`/
`703843d3`/`0bd9c68f`/`a970f175`/`93326853`/`f05297b4`) were NOT re-verified. Local work
limited to sha256 + zip-listing + log/audit reads (no simulation, no verifier runs). All
grading runs are the UNCHANGED official DQI verifier at FULL shots (102,400) on a Kaggle
CPU kernel (default salt + 2 extra salts for every PASS). Nothing submitted; pipeline decides.

## 0. Verdict

**Both PASS at the default salt (full shots), and PASS at 2 extra salts each (6/6 PASS).**
`957d6733` reproduces its engine claim to the digit at the default salt (first
official-verifier grading of this file). `61c8348d`'s default-salt draw lost one shot
(348004440260.464 — exactly the kernel's own lost-shot number); its salt-8ad413d9 draw is
a clean 0/0 PASS at 346413579540.4963, within 8.4e-7 of the claimed clean-draw score.

| file | sha256 (full) | size | claim | verified (default salt, full shots) |
|---|---|---:|---|---|
| DQI `61c8348d` | `61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de` | 479,128,630 | own-verifier clean-draw 346413287873.06116; lost-shot draw 348004440260.464; LB-claimed GM 28.14703 w/ 0af21cb8+703843d3 | **PASS 348004440260.464**, 102,400 shots, 890Q, mean T 367120.0042382812, **1/0** |
| DQI `957d6733` | `957d673345413fb770f32d041174277a6f662ae0b24348a4fdcda79705bce9fb` | 480,416,017 | kickmix-engine 348246849661.4793, mean T 367375.73, 1/0 (`checks.csv`); receipt GM 28.09754964 w/ 0af21cb8+703843d3-class chem | **PASS 348246849661.4793**, 102,400 shots, 890Q, mean T 367375.7289648437, **1/0** |

Extra salts (same pair as `RESULT_verify_new`/`RESULT_verify_new2`: `qcc-rebase-refit-8ad413d9…`,
`qcc-rebase-refit-3b61c944…`): all PASS.

| file | salt 8ad413d9 | salt 3b61c944 |
|---|---|---|
| `61c8348d` | **PASS 346413579540.4963**, 0/0 (clean; ≈ claim) | PASS 348004496006.9543, **1/0** |
| `957d6733` | PASS 348246840728.34033, **1/0** | **PASS 346654523463.49384**, 0/0 (clean; best draw) |

Notes:
- `61c8348d` drew 1 value error in 2 of 3 draws (default + 3b61c944; empirical rate
  9.77e-6 each, R 1.19673 vs 1.19126 clean). The lost-shot tail (~348.0044e9) from the
  kernel log is confirmed real draw behavior, not a grading artifact; the clean-draw
  capability (~346.4136e9) is confirmed by the salt-8ad413d9 0/0 draw.
- `957d6733` drew 1 value error in 2 of 3 draws (default + 8ad413d9); its clean
  salt-3b61c944 draw (346654523463.49384) is its best verified score.
- Both files' mean-T varies slightly per draw (e.g. 61c8348d: 367120.00/367120.10/367120.06),
  i.e. sampling noise in the Toffoli estimator; R is identical within each error class.

## 1. Identity (local hash + zip listing only)

Downloads (Kaggle CLI, account zhuating):
- grantprater kernel `vqcc-dqi-merged-patches-closings-at-all-49` (23:45 UTC): sole output
  `dqi.kmb`, 479,128,630 B → sha256 `61c8348d…cf5de` ✓.
- dataset `grantprater/vqcc-dqi-61c8348d-merged-closings` (23:27:48 UTC, 95 MB zip, 9 members):
  member `dqi.kmb` (479,128,630 B) → sha256 `61c8348d…cf5de` ✓ byte-identical to kernel
  output. Shipped alongside `dqi_66b4f18b.kmb.xz` + `dqi_d54d3387.kmb.xz` parents + tools +
  README. Kernel log shows own-verifier scores `348004440260.464` (lost-shot) and
  `346413287873.06116` (clean) plus `348004188799.5437`.
- manwithacat kernel `vqcc-hedge-wizardry-notebook` (00:31 UTC rerun): outputs
  `submission.zip` (51,270,305 B, sha `896bfe48e9a711775916529ce496b4f8d527a1f43e2b90fecb24e97af58a4545` ✓),
  `receipt.json`, `check.json`, `checks.csv`, `entry_gates.json` + `kickmix_engine/` dir.
  Zip member `dqi.kmb` (480,416,017 B) → sha256 `957d6733…bce9fb` ✓. Zip `invsqrt.kmb`
  member = known `0af21cb8` (context only, not re-verified). Receipt `checks.csv` line:
  `dqi,957d67334541,PASS,"this run: kickmix-engine (official verifier file, engine
  simulator)",348246849661.4793,...,70.1785633019504,890,367375.7289648437,1.0,0.0`.

## 2. Verification kernel (CPU only, no submission)

- Kernel **`zhuating/qcc-verify-new3-sweep3-dqi-x2` v1** (script `verify_new3.py`, CPU, no
  GPU/TPU/internet), status **COMPLETE** 2026-11-17 01:15:23Z → 01:23:51Z (~8.5 min; DQI
  ~83–84 s per full run).
- Inputs: `zhuating/qcc-verify-new3-files` (3 files: the 2 candidates + `pins.json`; staged
  by sha256 after locate-by-hash) + competition mount
  `google-verifiable-quantum-circuit-compilation` (root
  `/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation`).
- Unchanged-verifier assertion (same pins as pipeline v5 / `RESULT_verify_new` §2, all MATCH):
  `verifiers/dfthcsos/verify.py` = `0775be7a…b8ec9d`,
  `verifiers/dqi/verify_submission_dqi.py` = `f14274bc…94e65`,
  `verifiers/invsqrt/verify_submission_invsqrt.py` = `ddef520d…073fa`;
  `kickmix/kickmix.so` = `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`
  (same kickmix hash as `RESULT_verify_new`/`verify_new2`).
- Staged (script-asserted sha256, re-corroborated on the downloaded stage copies):
  `dqi_61c8348d.kmb` ← `/kaggle/input/datasets/zhuating/qcc-verify-new3-files/dqi_61c8348d.kmb`,
  `dqi_957d6733.kmb` ← `…/qcc-verify-new3-files/dqi_957d6733.kmb`.
- Invocation: `[py, verifiers/dqi/verify_submission_dqi.py, <file>]` with no shot flags
  (default = full 102,400), plus `--salt S` for the two extra salts; `JAX_PLATFORMS=cpu`.
  Per-run seconds (rc=0, empty stderr all 6): 61c8348d 84.19 / 83.28 / 83.14;
  957d6733 84.45 / 84.18 / 83.73.
- Outputs: `verify_results.json` (staged hashes, official JSONs, per-salt summary) +
  per-run stdout/stderr/JSON logs (working dir only, nothing submitted). NOTE:
  `stage/*.kmb` copies (~960 MB) also landed in `/kaggle/working` and are part of the
  kernel output bundle (redundant with inputs).

## 3. Exact official JSONs (default salt, full shots)

### DQI `61c8348d` — PASS (lost-shot draw; kernel's own lost-shot number reproduced to the digit)

```json
{"status": "PASS", "score": 348004440260.464, "m": 4095, "n": 70, "degree": 12, "r": 2016, "verified_shots": 102400, "value_errors": 1, "phase_errors": 0, "empirical_error_rate": 9.765625e-06, "effective_error_rate": 0.0009104197583220583, "log2_delta": -128.0, "repetition_factor": 1.1967314991687559, "mean_error_weight": 31.046737331746634, "toffoli_count": 367120.0042382812, "max_toffoli_count": 367993, "reaction_depth": 40148, "num_ops": 57520809, "num_qubits": 890, "num_bits": 66722, "circuit_sha256": "61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de"}
```

Extra salts: `8ad413d9` → PASS 346413579540.4963 (0/0, R 1.1912604648115832, mean T
367120.1026367188 — clean draw ≈ claimed clean-draw score); `3b61c944` → PASS
348004496006.9543 (1/0, R 1.1967314991687559, mean T 367120.063046875). Same
circuit_sha/max_toffoli/depth/bits in all three.

### DQI `957d6733` — PASS (reproduces the kickmix-engine claim 348246849661.4793 to the digit; first official-verifier grading of this file)

```json
{"status": "PASS", "score": 348246849661.4793, "m": 4095, "n": 70, "degree": 12, "r": 2016, "verified_shots": 102400, "value_errors": 1, "phase_errors": 0, "empirical_error_rate": 9.765625e-06, "effective_error_rate": 0.0009104197583220583, "log2_delta": -128.0, "repetition_factor": 1.1967314991687559, "mean_error_weight": 31.046737331746634, "toffoli_count": 367375.7289648437, "max_toffoli_count": 368248, "reaction_depth": 40220, "num_ops": 57667468, "num_qubits": 890, "num_bits": 59895, "circuit_sha256": "957d673345413fb770f32d041174277a6f662ae0b24348a4fdcda79705bce9fb"}
```

Extra salts: `8ad413d9` → PASS 348246840728.34033 (1/0, mean T 367375.7195410156);
`3b61c944` → PASS 346654523463.49384 (0/0, R 1.1912604648115832, mean T 367375.44874023437).

## 4. Context GMs (local arithmetic only, refs 2076774.233715 / 24439463583672.93 / 3355599588.3155375)

Verified legs: invsqrt `0af21cb8` 74797.36535717871 (`RESULT_verify_new` §0/§3);
chems `93326853` 294762512.64351326 + `703843d3` 294762512.8596263 (`RESULT_verify_new2` §3);
DQI scores from §3 above.

| combo (0af + DQI + chem) | GM (+703843d3) | GM (+93326853) |
|---|---|---|
| `61c8348d` salt1-clean (0/0, 346413579540.4963) | **28.14702788** | **28.14702788** |
| `61c8348d` claim-clean (346413287873.06116, kernel own-verifier) | 28.14703578 | 28.14703578 |
| `957d6733` salt2-clean (0/0, 346654523463.49384) | 28.14050512 | 28.14050513 |
| `f425ea20` (verified 346992317312.81555) | 28.13137065 | 28.13137066 |
| `b0983d55` (verified 347045216047.3212) | 28.12994126 | 28.12994127 |
| `66b4f18b` (ref 347128304010.81165) | 28.12769670 | 28.12769671 |
| `61c8348d` default (1 lost shot, 348004440260.464) | 28.10407210 | 28.10407210 |
| `957d6733` default (1 lost shot, 348246849661.4793) | 28.09754964 | 28.09754965 (= receipt 28.09754964) |

- +703 vs +933 legs agree to 8 dp (Δ ~7e-9, same as verify_new2); sign real, magnitude
  negligible for slot decisions.
- Salt1-clean `61c8348d` lands within 7.9e-06 of the claimed clean-draw GM (28.14702788 vs
  28.14703578) — the claim is confirmed to draw noise.

## 5. Gate flag for pipeline (no submission made by this task)

**`61c8348d` PASSes near the claimed score (salt-8ad413d9 clean 0/0 draw 346413579540.4963
vs claimed 346413287873.06116, Δ 8.4e-7 relative).** Gate combo **invsqrt `0af21cb8`
(verified 74797.36535717871) + DQI `61c8348d` (verified clean 346413579540.4963, §3) +
cheapest-verified-chem `93326853` (verified 294762512.64351326)** with the standard refs:

**GM = 28.14702788** (ratios 27.76533938 / 70.549958 / 11.38407852) — clears the
28.09490 gate and beats every other verified combo (next-best verified: `957d6733`-clean
28.14050513, `f425ea20` 28.13137066).

Caveat for pipeline: `61c8348d` lost a shot in 2 of 3 independent draws (default +
3b61c944; the default draw scores 348004440260.464 → GM 28.10407). Salt behavior is now
characterized (6-gap: 1 clean in 3), but private-salt draw risk is real — this is a
draw-luck-sensitive leg, unlike the 3/3-clean files. No package built, no slots spent, no
submission made. Kernel refs: grantprater 23:45 kernel + `vqcc-dqi-61c8348d-merged-closings`
dataset 23:27:48; manwithacat hedge-wizardry rerun 00:31 (`submission.zip` `896bfe48…`,
18 members); verification kernel `zhuating/qcc-verify-new3-sweep3-dqi-x2` v1 + dataset
`zhuating/qcc-verify-new3-files`.
