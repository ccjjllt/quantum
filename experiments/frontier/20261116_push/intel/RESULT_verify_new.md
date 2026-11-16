# Independent verification of four kernel-claim-only bytes — 2026-11-16

Scope: the four untested files from `dqi/RESULT7.md` §0–§2 (kernel-claim only, never
officially verified). Known bytes (`f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/`bdae290f`/
`sub1`/`f6e12f02`) were NOT re-verified. Local work limited to sha256 + 88-byte header
parse (identity only); no local simulation, no local verifier runs. All grading runs are
the UNCHANGED official verifiers at FULL shots on a Kaggle CPU kernel. Nothing submitted;
pipeline decides.

## 0. Verdict

**All four PASS at the default salt (full shots), and PASS at 2 extra salts each
(12/12 PASS).** Every kernel claim reproduces to the digit at the default salt.

| file | sha256 (full) | size | claim | verified (default salt, full shots) |
|---|---|---:|---|---|
| invsqrt `0af21cb8` | `0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b` | 180,382 | 74,797.37 (maoxin 14:51 log) | **PASS 74797.36535717871**, 200,540,928 shots, Q44, worst/tol 0.9995605646154175 |
| invsqrt `5eeea23b` | `5eeea23bd561c167584d338dcd98621c0e5e0da3b0b98e6452a93b4a6a8f13ac` | 179,768 | LB 28.09487 (ADITYA RAVI) | **PASS 75006.40286232081**, 200,540,928 shots, Q44, worst/tol 0.9864596519495844 |
| chem `703843d3` | `703843d35a722f07b7f833b3a6565c54f00ec5ce4e692f7192593c79728f8ce9` | 1,847,692 | 294,762,512.86 (atakan audit) | **PASS 294762512.8596263**, 78,080 shots, T14712, λ 46.92158337179646 |
| chem `0bd9c68f` | `0bd9c68f376b5702617512c6c6ebd2837c6a0c7faf4f738e59257e4937c94101` | 1,847,692 | 294,762,518.66 (junmiaotiao) | **PASS 294762518.6638708**, 78,080 shots, T14712, λ 46.92158429574143 |

Extra salts (`qcc-rebase-refit-8ad413d9…`, `qcc-rebase-refit-3b61c944…`, the two
adityaravi2 published salts): all PASS. Chem scores are salt-invariant (identical to
all digits); invsqrt varies at the 1e-2 level per salt (sampling), all PASS:

| file | salt 8ad413d9 | salt 3b61c944 |
|---|---|---|
| `0af21cb8` | PASS 74797.36796904955 | PASS 74797.38784421439 |
| `5eeea23b` | PASS 75006.30286552115 (= aditya draw1 to the digit) | PASS 75006.37662063513 (see §4 note) |
| `703843d3` | PASS 294762512.8596263 | PASS 294762512.8596263 |
| `0bd9c68f` | PASS 294762518.6638708 | PASS 294762518.6638708 |

Gate combo (mandate): **invsqrt `0af21cb8` (verified 74797.36535717871) + chem `bdae290f`
+ DQI `66b4f18b` (verified 347128304010.81165)** with refs
2076774.233715 / 24439463583672.93 / 3355599588.3155375:

**GM = 28.127692911** (ratios 27.76533938 / 70.40469850 / 11.38407391).
That clears the 28.09490 gate — it is ~28.128, not ~28.121 (the 28.12102 kernel number
used DQI `ccc2ab84`; `66b4f18b` adds ×1.000237). Cross-check: atakan's
`0af21cb8`+`00ac37d4`+`703843d3` measured_GM 28.12149767744216 recomputes to
28.12149767744089 from my verified numbers. No submission by this task; pipeline decides.

## 1. Identity (local hash + 88-byte header only)

Sources (downloaded 2026-11-16 ~18:15 UTC): `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`
(14:51 run, `submission.zip` 51,854,818 B), `adityaravi2/qcc-frontier-rebase-refit-validation-20261116`
(12:20, `submission.zip` + `variant_validation.json`), `atakanaldemir/qcc-terminal-readout-and-phase-folds`
(16:33 rerun, `submission.zip` 51,843,850 B), `junmiaotiao/qcc-portfolio-assembly` (13:39,
`submission.zip` + `submission_summary.json`).

- `0af21cb8` extracted from maoxin zip (also byte-identical in the atakan 16:33 rerun zip).
  **Correction to RESULT7 §0: it is 180,382 B, not 179,768 B.** The 179,768 B size class
  holds `5eeea23b` and `f2cdab0b`.
- `5eeea23b` extracted from aditya zip (179,768 B). Its 88-byte header is byte-identical to
  `f2cdab0b`'s header (same `d750c7d5…ff50…` prefix, same size — same structure, body differs);
  `0af21cb8`'s header differs (`…6151…` at the same offsets).
- `703843d3` / `0bd9c68f` extracted from atakan / junmiaotiao zips (both 1,847,692 B;
  zip-of-float64-npy, headers differ only in CRCs).
- All four zips share byte-identical `angle_k_0..14.kmb` loaders
  (`aed6aa7c…` … `ab06b98f…`, sizes 415169…362314); that loader set was pinned and reused
  for both chem run-dirs. 88-byte header of `0af21cb8':
  `d750c7d5c329d326e3cc9f6834f2b8bf020000002c00000079010000010000006151…'.

## 2. Verification kernel (CPU only, no submission)

- Kernel **`zhuating/qcc-verify-new-4-files` v1** (script `verify_new.py`, CPU, no GPU/TPU/internet),
  status **COMPLETE** 2026-11-16 ~19:27 UTC (run 18:23:29Z → 19:27:36Z, ~64 min; invsqrt
  ~608–622 s per full run, chem ~24–30 s per full run).
- Inputs: `zhuating/qcc-verify-new-4files` (20 files: the 4 candidates + 15 shared loaders +
  `pins.json`; all staged by sha256 after locate-by-hash) + competition mount
  `google-verifiable-quantum-circuit-compilation`.
- Unchanged-verifier assertion (same pins as pipeline v5, all MATCH):
  `verifiers/dfthcsos/verify.py` = `0775be7a…b8ec9d`,
  `verifiers/dqi/verify_submission_dqi.py` = `f14274bc…94e65`,
  `verifiers/invsqrt/verify_submission_invsqrt.py` = `ddef520d…073fa`;
  `kickmix/kickmix.so` = `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`
  (same kickmix hash as aditya's `variant_validation.json`).
- Invocation: `[py, verify.py, <file|run_dir>]` with no shot flags (defaults = full
  200,540,928 / 78,080), plus `--salt S` for the two extra salts; `JAX_PLATFORMS=cpu`.
  Chem run-dirs = candidate npz + the 15 pinned loaders. DQI verifier never run (no new DQI bytes).
- Outputs: `verify_results.json` (staged hashes, official JSONs, per-salt summary) + per-run
  stdout/stderr logs + restaged inputs (working dir only, nothing submitted).

## 3. Exact official JSONs (default salt, full shots)

### chem `703843d3` — PASS (reproduces atakan's `reproduction_audit.json` to the digit, incl. `submission_sha256 59bd9047…`)

```json
{"status": "PASS", "score": 294762512.8596263, "lambda_eff": 46.92158337179646, "toffoli_count": 14712.0, "num_qubits": 427, "brot": 8, "batch_size": 5, "num_circuits": 15, "reaction_depth": 176, "num_ops": 606711, "verified_shots": 78080, "submission_sha256": "59bd9047aebb98807a354f342ab6abed141305f60f6e2f2416aaec39bab89f0b", "resources": {"brot": 8, "keep_bits": 10, "angles_toffoli_per_pass": 4025.0, "angles_toffoli": 8050.0, "angles_qubits": 128, "angles_selection_qubits": 11, "angles_persistent_qubits": 40, "angles_temporary_qubits": 77, "outer_state_prep_toffoli": 317, "inner_state_prep_toffoli": 4095, "givens_rotations_toffoli": 2250, "outer_state_prep_persistent_qubits": 40, "outer_state_prep_temporary_qubits": 90, "outer_state_prep_qubits": 130, "inner_state_prep_persistent_qubits": 44, "inner_state_prep_temporary_qubits": 303, "inner_state_prep_qubits": 347, "heuristic_persistent_qubits": 84, "heuristic_temporary_qubits": 303, "heuristic_toffoli": 6662, "heuristic_qubits": 387, "persistent_qubits": 124, "temporary_qubits": 303, "toffoli": 14712.0, "qubits": 427, "angles_within_cap": true}, "metrics": {"error_1": 0.019999999900000568, "error_2": 0.01999999990013515, "Lambda": 283.14421121705783, "E_SOS": -22144.1882480001, "E_gap": 3.9148980001009477, "lambda_eff": 46.92158337179646, "gap_in_domain": true}}
```

### chem `0bd9c68f` — PASS (score identical to junmiaotiao's `notebook-verification`-salt 294762518.6638708; scoring is salt-invariant here)

```json
{"status": "PASS", "score": 294762518.6638708, "lambda_eff": 46.92158429574143, "toffoli_count": 14712.0, "num_qubits": 427, "brot": 8, "batch_size": 5, "num_circuits": 15, "reaction_depth": 176, "num_ops": 606711, "verified_shots": 78080, "submission_sha256": "1a0c35cba8c2b0e38459c727c664e131c2893a0943cd32433f1d8bcbc868edd6", "resources": {"brot": 8, "keep_bits": 10, "angles_toffoli_per_pass": 4025.0, "angles_toffoli": 8050.0, "angles_qubits": 128, "angles_selection_qubits": 11, "angles_persistent_qubits": 40, "angles_temporary_qubits": 77, "outer_state_prep_toffoli": 317, "inner_state_prep_toffoli": 4095, "givens_rotations_toffoli": 2250, "outer_state_prep_persistent_qubits": 40, "outer_state_prep_temporary_qubits": 90, "outer_state_prep_qubits": 130, "inner_state_prep_persistent_qubits": 44, "inner_state_prep_temporary_qubits": 303, "inner_state_prep_qubits": 347, "heuristic_persistent_qubits": 84, "heuristic_temporary_qubits": 303, "heuristic_toffoli": 6662, "heuristic_qubits": 387, "persistent_qubits": 124, "temporary_qubits": 303, "toffoli": 14712.0, "qubits": 427, "angles_within_cap": true}, "metrics": {"error_1": 0.019999998500025328, "error_2": 0.019999998500001566, "Lambda": 283.1442221910007, "E_SOS": -22144.1882480015, "E_gap": 3.9148980015015695, "lambda_eff": 46.92158429574143, "gap_in_domain": true}}
```

### invsqrt `0af21cb8` — PASS (reproduces maoxin 14:51 / atakan fresh-run 74797.36535717871 to the digit; note same binding input `worst_x 231` and same worst ratio as `f2cdab0b`, with lower mean T 1459.3749 vs 1464.1251, depth 1233 vs 1244)

```json
{"status": "PASS", "score": 74797.36535717871, "toffoli_equivalent": 1699.9401217540617, "toffoli_count": 1459.3748802688297, "max_toffoli_count": 1560, "t_count": 2.499900279707492, "rotation_count": 33.0, "rotation_eps": 1.6406054738480745e-13, "num_qubits": 44, "reaction_depth": 1233, "num_ops": 20833, "verified_shots": 200540928, "worst_error_over_tolerance": 0.9995605646154175, "worst_x": 231, "circuit_sha256": "0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b"}
```

### invsqrt `5eeea23b` — PASS (reproduces aditya `raw_default` 75006.40286232081 to the digit)

```json
{"status": "PASS", "score": 75006.40286232081, "toffoli_equivalent": 1704.690974143655, "toffoli_count": 1464.1257071075288, "max_toffoli_count": 1559, "t_count": 2.5000024832836116, "rotation_count": 33.0, "rotation_eps": 1.6406054738480745e-13, "num_qubits": 44, "reaction_depth": 1244, "num_ops": 20735, "verified_shots": 200540928, "worst_error_over_tolerance": 0.9864596519495844, "worst_x": 219317, "circuit_sha256": "5eeea23bd561c167584d338dcd98621c0e5e0da3b0b98e6452a93b4a6a8f13ac"}
```

## 4. Discrepancy note (5eeea23b second salt)

Salt `…8ad413d9` reproduces aditya's draw-1 invsqrt **exactly**
(75006.30286552115, same worst 0.9864596519495844) — setup fidelity confirmed (same
circuit bytes, same salt, same verifier, same kickmix). Salt `…3b61c944` does not:
mine **75006.37662063513** vs their published draw-2 **75006.38432087375** (Δ 0.0077,
1.0e-7 relative; their three numbers are internally GM-consistent, so it is a genuine
second execution, not a typo). Commands match their notebook cell 11 exactly
(`verify_submission_invsqrt.py <refit> --salt <salt>`, defaults otherwise), and the
verifier seeds chunks deterministically from `(circuit_hash, salt)`, so same-salt reruns
should agree — the cause is unexplained from available evidence (their draw ran in their
12:20 kernel, mine in the 18:23 kernel; no local rerun was attempted per mandate).
Both are PASS; GM impact is 9.6e-7 (28.094863492 vs 28.094862531 with their DQI/chem),
and `5eeea23b` is a tie-band file either way (raw-default stack GM 28.09486886), so this
does not affect any gate decision. Flagged for the record, not resolved.

## 5. Context GMs (local arithmetic only, refs §0)

- `0af21cb8` + `66b4f18b` + `bdae290f` = **28.127692911** ← clears 28.09490 (all three bytes independently verified: this file, RESULT7 §3, known).
- `0af21cb8` + `00ac37d4` + `703843d3` = 28.12149768 (= atakan's 28.12149767744216).
- `0af21cb8` + `00ac37d4` + `0bd9c68f` = 28.12149749.
- `5eeea23b`(default) + `ccc2ab84` + `f6e12f02` = 28.09486886 (tie band, matches aditya `raw_default_gm`).
- No package built, no submission made, no slots spent.
