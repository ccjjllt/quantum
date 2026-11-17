# Independent verification of sweep4 chem byte + ratnachand hash-check — 2026-11-17

Scope: the sweep4 §1 byte-new chem file `a73b25d2` + its 15 new small loaders
(kernel-claim only, never independently verified). The 19 known bytes were NOT
re-verified. The varianceofx cost-model bundle (`4b350932`/`2c125b39`/`6aa80150`,
sweep4 §1) is explicitly out of scope — below-frontier model arithmetic, no
verifier value. Local work limited to sha256 + zip-listing + log reads + GM
arithmetic (no simulation, no local verifier runs). All grading runs are the
UNCHANGED official chemistry verifier at FULL shots (78,080) on a Kaggle CPU
kernel (default salt + 2 extra salts). Nothing submitted; pipeline decides.

## 0. Verdict

**`a73b25d2` PASSes at the default salt (full shots) at the claimed score to the
digit, and PASSes at 2 extra salts (3/3 PASS, salt-invariant identical scores).**

| file | sha256 (full) | size | claim | verified (default salt, full shots) |
|---|---|---:|---|---|
| chem `a73b25d2` | `a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3` | 1,847,552 | **294,643,137.73357135** (maoxin123 v27 02:04 + loaders 02:16 kernel-embedded official-verifier PASS, T 14706, λ_eff 46.92171681802857) | **PASS 294643137.73357135**, 78,080 shots, T14706, λ 46.92171681802857, Q427 |

Extra salts (same pair as verify_new/verify_new2/verify_new3): all PASS, identical
to all digits (chem is salt-invariant so far):

| file | salt 8ad413d9 | salt 3b61c944 |
|---|---|---|
| `a73b25d2` | PASS 294643137.73357135 (identical) | PASS 294643137.73357135 (identical) |

## 1. Identity (local hash + zip listing only)

Downloads (Kaggle CLI, account jiyujia):
- `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` (02:04, `submission.zip`
  51,101,767 B) + `maoxin123/qcc-28-14-4-022-toffoli-chemistry-loaders` (02:16,
  `submission.zip` 51,101,767 B). Zip-level sha differ (timestamps), **all 18 members
  byte-identical** (byte-identical sibling confirmed): chem npz `a73b25d2` +
  15 small loaders below + `dqi.kmb` = known `957d6733` + `invsqrt.kmb` = known
  `0af21cb8` (context only, not re-verified).
- 15 small loaders (the DIFFERENT, smaller family — not the standard
  415169…362314 set; run-dir must pair npz with THESE):

| k | sha256 (full) | size |
|---|---|---:|
| 0 | `ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538` | 180,436 |
| 1 | `8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd` | 151,084 |
| 2 | `e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f` | 135,545 |
| 3 | `b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e` | 134,697 |
| 4 | `ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d` | 130,825 |
| 5 | `21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856` | 130,454 |
| 6 | `1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1` | 129,631 |
| 7 | `8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0` | 130,875 |
| 8 | `0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563` | 130,222 |
| 9 | `b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71` | 130,054 |
| 10 | `41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6` | 131,074 |
| 11 | `76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca` | 130,646 |
| 12 | `e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f` | 129,613 |
| 13 | `9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8` | 130,455 |
| 14 | `fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f` | 130,774 |

All 16 hashes match sweep4 §1 exactly. Kernel-log claim lines re-corroborated locally:
`chemistry PASS 294643137.73357135 lambda_eff 46.92171681802857 T 14706.0 …
E_gap 3.9148980002646567`, `dfthcsos cost 294643137.733571 ratio 11.38869`,
`geometric mean, this run 28.10134` (identical lines in both kernel logs).

## 2. Verification kernel (CPU only, no submission)

- Kernel **`jiyujia/qcc-verify-new4-chem-a73b25d2` v3** (script `verify_new4.py`, CPU, no
  GPU/TPU/internet), status **COMPLETE** 2026-11-17 02:45:59Z → 02:47:09Z (~71 s;
  chem ~23.6 / 21.4 / 21.2 s per full run).
- Inputs: `jiyujia/qcc-verify-new4-files` (17 files: candidate npz + 15 small loaders
  + `pins.json`; staged by sha256 after locate-by-hash) + competition mount
  `google-verifiable-quantum-circuit-compilation`.
- Unchanged-verifier assertion (same pins as pipeline v5 / verify_new §2, all MATCH):
  `verifiers/dfthcsos/verify.py` = `0775be7a…b8ec9d`,
  `verifiers/dqi/verify_submission_dqi.py` = `f14274bc…94e65`,
  `verifiers/invsqrt/verify_submission_invsqrt.py` = `ddef520d…073fa`;
  `kickmix/kickmix.so` = `c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e`
  (same kickmix hash as all prior verify runs).
- Invocation: `[py, verifiers/dfthcsos/verify.py, <run_dir>]` with no shot flags
  (default = full 78,080), plus `--salt S` for the two extra salts; `JAX_PLATFORMS=cpu`.
  Chem run-dir = candidate npz (as `submission.npz`) + the 15 pinned SMALL loaders.
- Outputs: `verify_results.json` (staged hashes, official JSONs, per-salt summary) +
  per-run stdout/stderr/JSON logs + restaged inputs (working dir only, nothing submitted).
- Infra note: v1/v2 went ERROR (`/kaggle/input` empty) because kernel-metadata.json used
  the wrong keys (`dataset_data_sources`/`competition_data_sources` — silently ignored).
  Correct keys are **`dataset_sources` / `competition_sources`** (per `kaggle kernels
  init` template); v3 with fixed keys mounted both inputs. Future verify kernels: copy
  v3's metadata.

## 3. Exact official JSON (default salt, full shots; salt1/salt2 JSONs byte-identical)

### chem `a73b25d2` — PASS (reproduces both kernels' embedded claim to the digit)

```json
{"status": "PASS", "score": 294643137.73357135, "lambda_eff": 46.92171681802857, "toffoli_count": 14706.0, "num_qubits": 427, "brot": 8, "batch_size": 5, "num_circuits": 15, "reaction_depth": 177, "num_ops": 224256, "verified_shots": 78080, "submission_sha256": "1e6c9f65453e9bde3e5148c99be8749f9b45faec06b9b0e57e529c09b3ff0e45", "metrics": {"error_1": 0.01999999973509546, "error_2": 0.019999999735098823, "Lambda": 283.1458106129289, "E_SOS": -22144.188248000264, "E_gap": 3.9148980002646567, "lambda_eff": 46.92171681802857, "gap_in_domain": true}}
```

Shape notes (vs the standard 14712 family): T 14706 (6 fewer), depth **177** (vs 176),
ops **224256** (vs 606711), angles 8044 total / 4022 per pass (vs 8050 / 4025) —
a genuinely different circuit, not a repack. `submission_sha256 1e6c9f65…` is the
run-dir hash (npz + small loaders), not the file hash. Both extra salts: PASS with
identical score/metrics/resources.

## 4. Context GMs (local arithmetic only, refs 2076774.233715 / 24439463583672.93 / 3355599588.3155375)

Verified legs: invsqrt `0af21cb8` 74797.36535717871 (verify_new), DQI
`61c8348d`-clean 346413579540.4963 salt-8ad413d9 0/0 (verify_new3) /
`f425ea20` 346992317312.81555 (verify_new2) / `957d6733` 348246849661.4793 1/0
+ 346654523463.49384 clean (verify_new3), chems `93326853` 294762512.64351326 /
`703843d3` 294762512.8596263 (verify_new2) / `a73b25d2` 294643137.73357135 (§3).

| combo (0af + DQI + chem) | GM |
|---|---|
| `61c8348d`-clean + **`a73b25d2`** (best-mix w/ new chem) | **28.15082863** (27.76534 / 70.54996 / 11.38869) |
| `61c8348d`-clean + `703843d3` (verify_new3 gate) | 28.14702788 |
| `f425ea20` + `a73b25d2` | 28.13516929 |
| `f425ea20` + `93326853` (verify_new2 gate) | 28.13137066 |
| `957d6733`-clean + `a73b25d2` | 28.14430500 |
| `957d6733` (1err) + `a73b25d2` (maoxin kernel claim) | 28.10134372 (= log 28.10134) |

- `a73b25d2` beats `703843d3` by 119,375.13 (~0.04%) on verified score; on fixed legs
  the GM gain is +0.00380 (28.15082863 vs 28.14702788). Note: sweep4 §2 wrote
  "+0.00038" for this gap — that is a 10x decimal typo; the recompute from both
  numbers gives +0.00380.
- The 28.15082863 number is exact-match to sweep4 §2's paper value (was computed from
  the kernel claim; the claim is now verified to the digit, so the paper value stands).

## 5. Secondary: ratnachand kernel + dataset hash-check (sweep3 window gap, report only)

- Kernel `ratnachand/vqcc-verified-floor-and-circuit-anatomy` (00:59:48) output
  `submission.zip` (51,268,657 B): all 18 members known — invsqrt `0af21cb8`,
  DQI `f425ea20`, chem `93326853`, standard 15 loaders `aed6aa7c…` … `ab06b98f`
  (sizes 415169…362314). **No new bytes.**
- Dataset `ratnachand/vqcc-verified-public-floor` (00:58:41, 52.7 MB): members
  `dqi.kmb` = `f425ea20` ✓, `invsqrt.kmb` = `0af21cb8` ✓, `dfthcsos/submission.npz`
  = `93326853` ✓, 15 loaders = standard pinned set ✓. **No new bytes.**
- Both corroborate the verify_new2 verified set; nothing to verify.

## 6. Gate flag for pipeline (no submission made by this task)

**`a73b25d2` verified PASS at the claimed score to the digit (3/3 incl. extra salts,
salt-invariant).** Gate combo **invsqrt `0af21cb8` (verified 74797.36535717871) +
DQI `61c8348d` (verified clean 346413579540.4963, salt-8ad413d9 0/0, §verify_new3) +
new-cheapest-verified-chem `a73b25d2` (verified 294643137.73357135, §3)** with the
standard refs:

**GM = 28.15082863** (ratios 27.76534 / 70.54996 / 11.38869) — clears the 28.09490
gate by a wide margin and beats every other verified combo (next-best verified:
`61c8348d`-clean + `703843d3` at 28.14702788; `f425ea20` + `a73b25d2` at 28.13516929).

Caveats for pipeline: (a) the DQI leg is a single-salt clean draw of a
draw-luck-sensitive file (lost a shot in 2/3 verify_new3 draws — private-salt risk
unchanged); (b) the chem leg rides the SMALL loader family (T 14706, depth 177) —
the package must pair `a73b25d2` with these 15 loaders, not the standard set;
(c) `a73b25d2` is now the cheapest verified chem (Δ −119,375 vs `703843d3`).
No package built, no slots spent, no submission made. Kernel refs: maoxin123 v27
02:04 kernel + loaders 02:16 kernel (sibling-identical zips); verification kernel
`jiyujia/qcc-verify-new4-chem-a73b25d2` v3 + dataset `jiyujia/qcc-verify-new4-files`.
