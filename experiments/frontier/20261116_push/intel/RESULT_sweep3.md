# Sweep 23:27 UTC → 01:01 UTC + new-byte verdicts — 2026-11-17

Method: `kaggle kernels list -s {qcc,quantum} --sort-by dateRun` +
`kaggle datasets list -s {qcc,vqcc,quantum-circuit} --sort-by updated` at ~00:53 UTC;
downloaded every in-window candidate with output files (<200 MB rule: the one
exception is `grantk/dqi.kmb`, 479,128,630 B — already pulled as the kernel's sole
output file; local work limited to sha256 + zip-listing + log/audit JSON reads,
no simulation, no verifier runs). `shasum -a 256` every `.kmb`/`.npz` against the
known set `f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/`0af21cb8`/`5eeea23b`/`f425ea20`/
`b0983d55`/`eea2d627`/`bdae290f`/`sub1`/`f6e12f02`/`703843d3`/`0bd9c68f`/`a970f175`/
`93326853`/`f05297b4`. Nothing submitted.

## 1. Sweep table (window 2026-11-16 23:27 UTC → 2026-11-17 01:01 UTC)

Byte-new files (not in the known set):

| file | kind | sha256 (full) | size | claimed score | source | verify status |
|---|---|---|---|---|---|
| `61c8348d` | DQI | `61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de` | 479,128,630 B | **346,413,287,873.06 clean draws** (own-verifier, 102,400 shots; 348,004,440,260.46 on draws losing one shot; LB-claimed GM **28.14703** w/ 0af21cb8+703843d3) | grantprater 23:45 kernel output = byte-identical in `grantprater/vqcc-dqi-61c8348d-merged-closings` dataset (23:27:48, 95 MB zip w/ both parents + tools + README) | kernel-claim only (own verifier JSON in log `{'status':'PASS','score':348004440260.464,...}` is a one-lost-shot draw; clean-draw 346413287873.06116 from `q1116b` probe + README); needs independent official-verifier run |
| `957d6733` | DQI | `957d673345413fb770f32d041174277a6f662ae0b24348a4fdcda79705bce9fb` | 480,416,017 B (zip member) | **348,246,849,661.48**, mean T 367375.73, 1 value / 0 phase errors (kickmix-engine, NOT official verifier); GM **28.09754964** w/ 0af21cb8+703843d3 (`receipt.json`+`checks.csv`) | manwithacat hedge-wizardry 00:31 rerun `submission.zip` (sha `896bfe48…`, 18 members) | kernel-claim only (engine simulator); needs official-verifier run |

Known-bytes-only (all members hashed, no new bytes):

| candidate | verdict |
|---|---|
| asteriospanoras finer-chemistry-refit (23:41 COMPLETE; was RUNNING at sweep2 close) | **No new bytes.** Sole downloadable output is `receipt.json` (4,907 B): pins invsqrt `0af21cb8` + DQI `66b4f18b` + chem npz `f05297b4` (all known) + known 15 loaders; kernel-embedded official-verifier JSONs all PASS (dqi 347128304010.81165, chem 294762512.8596263, invsqrt 74797.36535717871, GM 28.1277). Refit converged to no-change (`refit lambda_eff … -> unchanged`); `submission.zip` was written to `/tmp`, not `/kaggle/working`, so no circuit bytes downloadable |
| leotang09 T7421 rerun (00:38, new zip sha `7bfa58bb…`, candidate dqi id 2238) | members byte-identical: `0af21cb8` + `66b4f18b` + `a970f175` + known loaders. Zip-wrapper change only |
| thomasgamet quantum-attempt-reset (23:47) | full official-verifier rerun of dataset `thomasgamet/qcc-nov16-shared-candidate`; receipt pins all 18 members to known bytes (`0af21cb8`+`66b4f18b`+`703843d3`+known loaders), GM 28.12769670312779. Zip members re-hashed, all known |
| grantprater `vqcc-dqi-61c8348d-merged-closings` dataset (23:27:48) | `dqi.kmb` inside = `61c8348d` (matches kernel output to the digit); parents `dqi_66b4f18b.kmb.xz` + `dqi_d54d3387.kmb.xz` shipped for rebuild |
| manwithacat `vqcc-hedge-wizardry` dataset (00:29, 433 MB) | over 200 MB, download skipped per mandate (rerun kernel output already covers its new `957d6733`) |
| ozertuu super-sota-verified-portfolio (23:33) | **ERROR**, `Missing required portfolio members: ['invsqrt.kmb']` — no output files, dead end |
| wilfredlin berkelium (00:02) | unrelated topic ("TOP 10 APPLICATIONS BERKELIUM"), skipped |

## 2. GM cross-checks (local arithmetic only; refs 2076774.233715 / 24439463583672.93 / 3355599588.3155375; legs 0af21cb8 + 703843d3)

| DQI x | score | r_dqi | GM(0af+703843d3+x) | vs claim |
|---|---|---|---|---|
| `61c8348d` (new) | 346,413,287,873.06116 | 70.550018 | **28.14703578** | matches README 28.14703 |
| `957d6733` (new) | 348,246,849,661.4793 | 70.178563 | **28.09754964** | exact match to receipt |
| `66b4f18b` (ref) | 347,128,304,010.81165 | 70.404698 | 28.12769670 | — |
| `f425ea20` (sweep2) | 346,992,317,312.82 | 70.432290 | 28.13137065 | — |
| `b0983d55` (sweep2) | 347,045,216,047.32 | 70.421554 | 28.12994126 | — |

**Ranking on equal legs: `61c8348d` (28.14704) > `f425ea20` (28.13137) >
`b0983d55` (28.12994) > `66b4f18b` (28.12770) > `957d6733` (28.09755).**
Caveat: only `66b4f18b` is independently verified; the other four are kernel-claims
(61c8348d own-verifier + LB entry; f425ea20 kernel-embedded official JSON;
b0983d55/957d6733 engine-simulator). `61c8348d` also carries the lost-shot tail
(~348.0044e9 draws); its clean-draw rate and salt behavior are unverified here —
verification is owned by the running verify-new2 task. No submission by this task.

## 3. Asterios finer-chem-refit answer (sweep2 blocker, resolved)

YES, it produced downloadable bytes after 23:27 UTC (run COMPLETE 23:41, receipt
mtime 23:53), but NO new circuit bytes: the refit converged to no-change and the
only captured output, `receipt.json`, pins the already-known triple
(`0af21cb8`/`66b4f18b`/`f05297b4`) with kernel-embedded official-verifier PASS
JSONs (GM 28.1277). A finer chem refit that beats `703843d3` did not materialize
in this window.
