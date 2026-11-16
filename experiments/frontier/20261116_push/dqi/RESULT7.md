# Intel sweep + new-circuit verification — 2026-11-16 (part 7)

Window: **2026-11-16 10:00 UTC → 15:23 UTC** (LB snapshot
`google-verifiable-quantum-circuit-compilation-publicleaderboard-2026-11-16T15:23:43.csv`,
3,191 teams). Method: `kaggle kernels list --sort-by dateRun` (18 kernels in window),
`kaggle datasets list -s {qcc,vqcc,quantum-circuit} --sort-by updated`, download every
candidate < 200 MB, sha256-compare every `.kmb`/`.npz` against known
`f2cdab0b` / `ccc2ab84` / `bdae290f` / `sub1(367d46e9)` / `f6e12f02` / `894aef42` /
`8b410e77` / `4b350932` / `821bf8d1`. Local work limited to hash + 88-byte header parse
(no simulation); the only verifier runs are the unchanged official DQI verifier on Kaggle
CPU (k18). Nothing submitted.

## 0. Outcome

**The sweep found byte-new circuits, so task 2 (toy model) is not triggered.**
Two byte-new DQI circuits both beat 28.09486 on claimed score, and both had their bytes
verified end-to-end (sha256 MATCH + unchanged official DQI verifier PASS, 0/0, exact
claimed score at the default salt):

| circuit | sha256 | Q | static T | mean T (verified) | score (verified) | claimed GM | LB | bytes verify |
|---|---|---:|---:|---:|---:|---|---|
| **66b4f18b** DQI (balramsrinivasan) | `66b4f18b85273bdc…a315c2` | 890 | 368,750 | 367,877.549 | 347,128,304,010.81 | **28.10154** | rank 76, Balram Srinivasan, 14:31 UTC | **sha MATCH + verifier PASS 0/0, score to the digit** |
| **00ac37d4** DQI (boristown 11:43 run) | `00ac37d4ae4ee4ac…5a853a8` | 890 | 368,991 | 368,120.884 | 347,357,914,646.97 | **28.09535** (combo) | ~60-team band incl. author 暗黑AGI 12:06 | **sha MATCH + verifier PASS 0/0, score to the digit** |

Four more byte-new files with claimed score > 28.09486 (not DQI, so no verifier run per
mandate; kernel self-reports only):

| file | kind | sha256 | claimed score | source |
|---|---|---|---|---|
| 0af21cb8 | invsqrt | `0af21cb8…` (179,768 B) | **74,797.37**, combo GM **28.12102** (kernel log) | maoxin123 kernel 14:51 run; official-verifier PASS lines in log; **not on LB** |
| 5eeea23b | invsqrt | `5eeea23b…` (179,768 B) | LB **28.09487** (ADITYA RAVI, 10:41) | adityaravi2 refit kernel; `variant_validation.json` ALL_CHECKS_PASS |
| 0bd9c68f | chem npz | `0bd9c68f…` | 294,762,518.66, combo 28.09535516 | junmiaotiao Q dataset/kernel; same score as independently verified 161e80cf (likely identical arrays, different zip container) |
| 703843d3 | chem npz | `703843d3…` | 294,762,512.86, combo 28.09535245 | atakanaldemir kernel 15:12 run |

## 1. Dataset candidates (all < 200 MB downloaded, all members hashed)

| dataset | updated | members | verdict |
|---|---|---|---|
| `balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings` | 15:16, 55.4 MB | dqi **66b4f18b** (NEW) + f2cdab0b + f6e12f02 | **new DQI, verified §3**; self-claim: 41 nested-norm closings replaced by norm-preserving tower closings, 890Q/367,877.55T, GM 28.10154. Gadget + tools + `results/RESULT_dqi_66b4f18b.json` shipped alongside |
| `junmiaotiao/qcc-frontier-20261116q` | 13:38, 22.5 MB | dqi **00ac37d4** (NEW) + npz **0bd9c68f** (NEW container) + f2cdab0b | **new DQI+chem, verified §3**; kernel-claimed combo 28.09535516 @ `notebook-verification` |
| `maoxin123/qcc-frontier-dqi-chem-mirror` | 14:36, 20.1 MB | dqi = ccc2ab84, npz = bdae290f | known bytes only |
| `jezzlin/vqcc-verified-base-portfolio-20261116` | 14:54, 56 MB | f2cdab0b + 4b350932 + bdae290f | known bytes only (self-described transport copy) |
| `ghazarosbarseghyan91/vqcc-combo-candidates` | 10:08, 56 MB | f2cdab0b + ccc2ab84 + bdae290f | known bytes only; LB Ghazaros 28.09486 (09:31, pre-window) |
| `ozertuu/quantum-sim-linalg-cache` | 14:48, ~112 MB | dqi = **00ac37d4**, npz = **0bd9c68f** | repack of the new bytes under a misleading title; nothing new |
| `manwithacat/vqcc-chemistry-negative-results` | 11:50, 8 MB | ledger NR-0276/0277 (7-group GPU fits, Fable noise-gain; both kill) | no circuits |

## 2. Kernel candidates (lastRun ≥ 10:00 UTC; outputs pulled and hashed where present)

| kernel (lastRun) | output | verdict |
|---|---|---|
| junmiaotiao/qcc-portfolio-assembly (13:39) | submission.zip: f2cdab0b + **00ac37d4** + **0bd9c68f**; summary GM 28.09535516 | new bytes (§3); LB tiraJoon 28.09535 (13:19) |
| boristown/qcc-gap-3-residue-repair-and-c43-native-compiler (11:43) | submission.zip: f2cdab0b + **00ac37d4** + **0bd9c68f**; log GM 28.09535227 | **origin of 00ac37d4** (alexchilton audit: "boristown 2026-11-16 11:43 UTC run"; also shipped by asterios 12:07) |
| atakanaldemir/qcc-terminal-readout-and-phase-folds (15:12) | f2cdab0b + **00ac37d4** + npz **703843d3**; combo 28.09535245; joint226 scans mostly 0 (hits of 1/2/19 static T) | new chem npz, marginally cheaper than 161e80cf (−5.8) |
| maoxin123/qcc-v27-a-44-qubit-invsqrt… (14:51) | invsqrt **0af21cb8** + ccc2ab84 + bdae290f; log: invsqrt PASS 74,797.365, GM 28.12102 | new invsqrt, kernel-claim only |
| adityaravi2/qcc-frontier-rebase-refit-validation-20261116 (12:19) | invsqrt **5eeea23b** + ccc2ab84 + f6e12f02; ALL_CHECKS_PASS | new invsqrt refit; LB ADITYA RAVI 28.09487 |
| alexchilton/28-09-lb-which-circuits-survive-private-salt (13:35) | audit source: VERIFIED dict already lists **00ac37d4** (368,120.88T, 0/0) and 161e80cf; "no public board score known for 00ac37d4" (pre-dates LB band) | independent corroboration |
| ozertuu/quantum-ai-fast-runner-starter-notebook (15:18) | 1ba197b0 + 821bf8d1 + 3b7d0cd9 | stale 27.31-era bytes |
| masumhuq / rdaccel / muchat007 / shadab / evgendvorkin / ayman / pablodiegoo / yorixum / radhesh / ghazaros-portfolio | — | no above-band LB under own names (muchat chem verified worse: T 15,540); pablodiegoo output = NOTICE only (LB 28.09536 private); davidpiln kernel is methods-only (LB David Pilný 28.21784 private) |

## 3. Verification (k18, unchanged official DQI verifier, default salt, 102,400 shots)

Kernel `zhuating/qcc-dqi-verifynew-66b4-00ac` (Kaggle CPU, no internet, competition data
+ the two public datasets attached; `verify_submission_dqi.py` + `kickmix.so` from the
competition mount, unmodified):

* v1 had a path-selection bug (`rglob("dqi.kmb")` matched the competition
  `sample_submission/dqi.kmb` first) and a 62-char PIN_B typo — both visible in the v1
  log (sample verified as 1893Q/reference-score, correctly identified as wrong file).
* v2, both candidates from the dataset mounts, sha256 MATCH, then:

```
VERIFY A {'status': 'PASS', 'score': 347128304010.81165, 'num_qubits': 890,
          'toffoli_count': 367877.5490429688, 'value_errors': 0, 'phase_errors': 0,
          'circuit_sha256': '66b4f18b85273bdc0b325500c43a810aba2772275b977f371731cfc400a315c2'}
VERIFY B {'status': 'PASS', 'score': 347357914646.9683, 'num_qubits': 890,
          'toffoli_count': 368120.8844238281, 'value_errors': 0, 'phase_errors': 0,
          'circuit_sha256': '00ac37d4ae4ee4ac6a8fe9a2aad241731c20be1c81d6332766f4f4d5a5a853a8'}
```

Both scores reproduce the claimants' numbers to the digit (66b4f18b: dataset
`results/RESULT_dqi_66b4f18b.json`; 00ac37d4: boristown log + junmiaotiao summary +
alexchilton VERIFIED dict). GM arithmetic re-checked locally: 66b4f18b combo gives
exactly 28.10154 against the reference costs. No candidate was packaged or submitted
(mandate: verification only).

## 4. Task 2 disposition

Not executed: the mandate triggers the toy in-place-vs-out-of-place prototype **only if
(1) finds nothing**. (1) found two verified byte-new DQI circuits, so there is no blocker
to report for the toy and no toy numbers were produced. The full-redesign cost-class
question from RESULT6 §2 stands answered by measurement on the real tape instead.

## 5. Board context (15:23 UTC snapshot; read-only)

Top moved: 30.96223 Z³C¹oherence (14:36), 30.53130 aadi_stonks (11:22). In-window slope
teams with no public bytes (private): David Pilný 28.21784 (11:04), Pablo Diego Pereira
28.09536 (14:13), plus the 28.10–28.24 slope (§LB band 33–111). maoxin123 sits at 28.15071
(02:35, pre-window); the 0af21cb8/28.12102 kernel combo has no LB entry. ccjjllt still
28.09486 (rank 321, 09:06).
