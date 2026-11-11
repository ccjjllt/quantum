# Public chemistry survey (2026-11-11): no set cheaper than 298,600,061.56

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
Read-only survey; no Kaggle submission, no push, no verifier/data modification.
Baseline: busyaprime `8afd4c67` npz + Maoxin k1–k3 290-Toffoli loaders,
local official 78,080-shot PASS **298,600,061.555139**.  Fresh re-run this
session at salt `recon-baseline-20261111`:
`artifacts/20261111_recon_verify/baseline_full.log`, exit 0, PASS,
`verified_shots=78080`, `submission_sha256=8edbcb64…c543de`.

## 1. Sources checked (all timestamps UTC)

| source | version / last update | result |
|---|---|---|
| `marculera/dfthc-c44-build` | v4, 2026-11-10 21:46 | 14,926-Toffoli build; no 11-11 update. 4,129 static/pass. |
| `busyaprime/33-qcc-v8-members` | v13, 2026-11-11 10:42 | the baseline itself (`8afd4c67`). |
| `heliosli/qcc-circuits-live` | v95, 2026-11-11 10:36 | npz `8d4c99a2` + the same Maoxin loaders: **298,600,262.29** (+200.73). |
| `junmiaotiao/qcc-frontier-20261111` | v1, 2026-11-11 11:34 | npz `e627ac4d` (pablodiegoo v10) + Lera loaders: **298,859,435.63** (+259,374.08). |
| `manwithacat/vqcc-apache-public-circuits` | v115, 2026-11-11 11:18 | catalog of 284 chemistry families; `parts/assembly_best.json` = `8d4c99a2` + best loaders = **298,600,262.29**. |
| `atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler` | run 2026-11-05 | no newer dataset; C43/gap3 inputs dataset last updated 2026-10-31. |
| `saddamaditya/narrowed-877q-dqi-and-progressive-r10-chemistry` | run 2026-10-27 | old; DQI/R10 chemistry, no dataset newer. |
| `marculera/df-thc-merge-groups-before-dropping-them` | run 2026-10-29 | old; superseded by the 11.2x build. |
| `avazaku/quantum-circuits-7-bit-bounds` | not in public kernel list; `kernels.get` denied | no downloadable dataset; could not read a claim. |

No dataset updated after 2026-11-11 11:34 contains a chemistry set; the newest
two are the baseline (`10:42`) and junmiaotiao (`11:34`, worse).

## 2. Exact numbers (official functions, shots=2 where circuits were run)

Static recompute: `experiments/dfthcsos/20261111_public_survey/static_eval.py`
(`evaluate_words` + `recover_words_from_circuits` + `heuristic_costs`).
Outputs: `artifacts/20261111_survey/heliosli_static.txt`,
`artifacts/20261111_survey/junmiaotiao_static.txt`.

| set | npz SHA-256 | T | Q | lambda_eff | score | delta |
|---|---|---:|---:|---:|---:|---:|
| **baseline** `8afd4c67` + Maoxin | `8afd4c67…e55ae7b` | 14,908 | 427 | 46.907537433 | **298,600,061.555** | 0 |
| heliosli v95 `8d4c99a2` | `8d4c99a2…c623063` | 14,908 | 427 | 46.907568966 | 298,600,262.287 | +200.732 |
| junmiaotiao `e627ac4d` | `e627ac4d…25eb3cc6` | 14,920 | 427 | 46.910522887 | 298,859,435.631 | +259,374.075 |
| catalog assembly `8d4c99a2` | `8d4c99a2…c623063` | 14,908 | 427 | 46.907568966 | 298,600,262.287 | +200.732 |
| catalog best own family `f2069b927370` | `d7e8880e…b3189ba` | 14,908 | 427 | 46.907638344 | 298,600,703.931 | +642.376 |
| T01 best `0f4278f03211` | (catalog `parts/families.csv`) | 14,956 | 427 | 46.890745821 | 299,454,243.648 | +854,182.093 |
| T02 best `cb2daab65c2e` | (catalog) | 14,958 | 427 | 46.891275464 | 299,497,671.213 | +897,609.658 |
| T03 best `9706e2c7ecff` | `2d53f957…24fef6b` | 15,181 | 427 | 46.874650995 | 303,854,940.775 | +5,254,879.220 |

`words_match=True` for heliosli and junmiaotiao (`static_sum` 4,123 and 4,129,
`qubits_max=128`). T01/T02/T03 rows are the catalog's local verifier numbers;
we did not re-run their circuits.

Why the low-lambda T03 sets are not competitive: T03's cheapest loaders cost
8,440 per shot (4,220 static/pass) versus T00's 8,246 (4,123/pass), and C=45
raises the heuristic from 6,662 to 6,741: T +273 for lambda_eff −0.033
(46.9075 → 46.8747), a net loss. T01/T02 are +48/+50 T for −0.036/−0.035 %
lambda_eff, also a net loss. T00 remains the cost sweet spot, and `8afd4c67`
is its best public weight set; the catalog (which does not contain
`8afd4c67`) tops out at `8d4c99a2`, 200.73 above the baseline.

## 3. Verification scope

- One official `manual_verify.py dfthcsos` run this session on the baseline
  (`--salt recon-baseline-20261111`, default 78,080 shots): **PASS**
  298,600,061.555139, log `artifacts/20261111_recon_verify/baseline_full.log`.
- The two downloaded candidates were checked with the official
  `evaluate_words` and `recover_words_from_circuits` at 2 shots/address
  (words deterministic, reverse clears, selection/workspace/phase checked by
  the function). That is a local official-function simulation, not the full
  verifier. They were not run at 78,080 shots because both are already worse
  on the exact static cost.
- `kernels.get` is denied by the current Kaggle token, so notebook pages /
  outputs could not be read; datasets and `datasets files` worked.

## 4. Files

Under `artifacts/20261111_survey/` (gitignored):
- `heliosli_v95/` (npz `8d4c99a2…`, 15 loaders), `heliosli_std/` (standard-name symlinks)
- `junmiaotiao_v1/dfthcsos/` (npz `e627ac4d…`, 15 loaders, `MANIFEST.json`)
- `mwc_parts/` (`manifest.csv`, `parts/*.csv`, `assembly_best.json`)
- `manwithacat_files.csv`, `mwc_all.txt` (284 chemistry families listed)
- `heliosli_static.txt`, `junmiaotiao_static.txt`

## 5. Next step

No public-file adoption. The only remaining chemistry levers are circuit-level
or shape-level; see `20261111_mbu_probe/`, `20261111_shape_probe/` and
`20261111_7bit_probe/`.
