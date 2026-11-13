# VQCC Negative Results

A ledger of ideas tried on the [Google Quantum AI verifiable circuit compilation competition](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)
and how each one failed, for all three tasks: inverse square root (`invsqrt`), DQI decoding (`dqi`) and FeMoCo
chemistry (`dfthcsos`, called `chemistry` here). It holds our own closed lines, from preregistered work cards (source `ours`), the
closed lines of our second, ChatGPT-based research pathway (source `R`), and other entrants' public nulls, dead ends and untested ideas, each credited by Kaggle name and linked to the post or
notebook where the author reported it. It is a research log, not a submission artefact: no circuits, no
submission files and no leaderboard claim. It was prepared with AI assistance.

The notebook [VQCC Negative Results](https://www.kaggle.com/code/manwithacat/vqcc-negative-results) shows the
ledger as a map of mechanism families per task, what is new, a timeline, the ideas still open, community
contributions, a filterable table and a query helper.

## The ledger

* `ledger.csv` and `ledger.parquet`: one row per idea, same columns in both. Rows are append-only and IDs
  (`NR-0001`, ...) never change; a correction is a new row with `supersedes`.
* `LEDGER_SCHEMA.md`: every column, the allowed values of `task`, `outcome` and `evidence_tier`, and a query example.

Key columns: `task`, `mechanism`, `family_target`, `date_tested`, `source` (`ours`, `R` or the author's Kaggle name),
`link`, `evidence_tier`, `outcome` (`kill`, `null`, `partial`, `open idea`, `observation`), `key_numbers`, `why_it_failed`,
`reopen_if`, `related_cards`, `dataset_files`, `keywords`, `licence`.

```python
import pandas as pd
L = pd.read_csv("/kaggle/input/vqcc-chemistry-negative-results/ledger.csv")
L[(L.task == "dqi") & L.mechanism.str.contains("flag", case=False)]   # has dropping a flag been tried on DQI?
```

## Observations

An `observation` row records a measured fact about the circuits or the task that constrains future work but was not
an idea tried. Its data sits under `observations/`:

* `observations/dqi-failure-atlas.csv`: one row per DQI input (salt, seed, batch, slot, error weight k) that fails in
  SomeJoint-line decoders, with the failure mechanism and pass/fail in each of four circuits (ledger row NR-0122).
* `observations/README.md`: what the atlas is, how to reproduce a row with the official verifier, and why it is a
  diagnostic, not a score predictor.

**Evidence tiers.** `official verifier` (the unmodified official verifier ran on a circuit), `measured by us`
and `local prescreen` (the same tier under two names: our local analysis with the official equations, native
simulation or exact algebra, no verifier run), `static model` (arithmetic or resource
projection), `paper only`, `author-reported` (another entrant's own claim; not re-verified by us unless the row
says so). A lower tier is never presented as a higher one.

**Others' entries.** Rows whose `source` is not `ours` summarise the author's public post or notebook in our words,
with the numbers they reported. Read the linked original before relying on them; corrections are welcome in the
dataset's discussion and will be added as new rows.

**Updates.** Rows are appended as the project's daily research routine closes work cards and reads the forum. A
few raw spellings in the master ledger are normalised when a version is staged; the map is in `LEDGER_SCHEMA.md`
("Normalisation at staging").

<!-- chemistry-2026-10-26 -->












## Part 2: chemistry negative results and tools (first version, 2026-10-26)

Negative results and small tools from one team's work on the chemistry task (`dfthcsos`, the FeMoCo DF-THC-SOS factorization) of the [Google Quantum AI verifiable circuit compilation competition](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation). For each attempt that did not work, the dataset holds the raw numbers (training trajectories, spectra, solver reports) and the scripts that make the structural reason checkable on a CPU. The narrative, with every result explained, is the notebook [Chemistry negative results: what fails and why](https://www.kaggle.com/code/manwithacat/chemistry-negative-results-what-fails-and-why).

**What this is not.** It contains no circuits, no submission files and no leaderboard claim. Every number states its evidence tier: **local analysis** (official equations on the official tensor, no circuit), **local prescreen** (official equations, no circuit), **hosted GPU prescreen** (same, on a rented A100), **verifier PASS/FAIL** (the unmodified official verifier run privately on Kaggle), or **author-reported** (another entrant's claim, credited by name).

### Headline findings

| Result | Number | Evidence tier | Why it is bounded |
| --- | --- | --- | --- |
| Precision without refit: 12 to 11-bit words on the official factorization | `error_1` 76.9 mHa, `error_2` 29.7 mHa (limit 20); control 3.19 / 18.64 | verifier FAIL (control PASS) | weights were co-fitted to the exact words, so precision is a joint variable with weights and offsets |
| Same factorization at 10 and 8-bit words | `error_2` 40.0 and 155.4 mHa | local prescreen | same reason; mrmeows reports (author-reported) about 111 mHa for plain 8-bit rounding of a good 10-bit fit |
| Gauge and offset descent on public factors | weakest-copy prune +0.29% `lambda_eff`; fixed-word refit -0.08% after 10 stages, decaying toward about -0.13% | local prescreen | Lambda is a one-norm on a cusped surface; mrmeows bounds the gain on a fixed factorization near 0.5% (author-reported), about 0.17% in the geometric mean |
| Shrinking the dictionary at R = 1 | (1, 460, 384) A100 38 min: 20.52 mHa, slope 1e-4 mHa per Gauss-Newton iteration after 3,764 iterations; (1, 496, 300): 22.44 | hosted GPU prescreen / local prescreen | 11-bit quantization costs about 3 mHa, so about 17 mHa continuous is needed (public shape reaches 17.07); capacity limit of the dictionary |
| Shared eigenbasis for the pair-space factors | mean commutator norm 0.148 vs random null 0.161; off-diagonal mass 17.6% to 16.4%; greedy dictionary 1,279 mHa at B = 496 (public: 19.99) | local analysis | the eigen-slice rotation is one gauge among infinitely many and the joint fit already chooses it |
| Variable projection (exact inner solve) | public weights 19.99 mHa vs best legal weights 19.47 vs unconstrained 19.19; dictionary-only L-BFGS 17.585 vs joint trainer 17.072 mHa at 35 min (pruned: 22.987 vs 21.64) | local analysis / local prescreen | public weights are near-optimal for their dictionary; first-order dictionary search loses to joint Gauss-Newton; the raw-basis clip-then-truncate recipe (30.8 mHa) is wrong because it ignores the QR metric |
| Rank floors from the official tensor | minimal R x C 290 / 307 / 330 for 20 / 15 / 10 mHa; floor 4.98 mHa at rank 384 | local analysis | Eckart-Young; a necessary condition only |

The frontier moved along word width (an 8-bit workspace cliff) and many small groups, not along the axis searched here. Details and credit are in the notebook.

### Files

#### `results/`

Paths under `results/` mirror the project's `outputs/` directory.

* `chemistry_negative_results.json` is the output of the hosted notebook run (version 2). Keys: `notebook`, `environment`, `python`, `numpy`, `evidence`, `input_sha256` and `pins` (SHA-256 of the official inputs and the public factorization file used), `spectrum` (`min_rank`, `floor_mHa_at_k`), `inner_solve` (`B`, `C`, `brot`, `control_public_weights_mHa`, `unconstrained_mHa`, `raw_clip_mHa`, `raw_clip_truncate_mHa`, `exact_psd_mHa`, `exact_psd_rankC_mHa`, `exact_psd_rankC_official_mHa`), `cost_model` (list of scored cases), `embedded_sources_sha256`, `cell_seconds`.
* `chemistry-campaign-2026-10-25/local-diag/r1_b460_c384_gn1500/` and `.../r1_b496_c384/`: Mac CPU trainer runs. `chunk_000N_lbfgs/history.jsonl` and `chunk_0006_gn/history.jsonl` are one JSON object per logged step. L-BFGS lines have `step`, `calls`, `E2` (two-body error in Hartree; multiply by 1000 for mHa), `seconds`, `dtype`, `optimizer`, `device`, `R`, `B`, `C`, `regularizer`, `status`. Gauss-Newton lines have `iteration`, `E2`, `float_objective`, `best_E2` and timing fields. `train_report.json` is the run summary.
* `chemistry-campaign-2026-10-25/refit-extension/public-19p99-10stages/refit_report.json` and `public-19p99-20k/refit_report.json`: fixed-word `lambda_eff` refit reports (homotopy stages).
* `chemistry-campaign-2026-10-25/target_spectrum.json`: eigenvalue spectrum of the pair-space target and Eckart-Young floors by rank.
* `colab-chem-2026-10-25/runs/chem-1-20261025T192250Z/`: Colab A100 run 1. `ckpt/ckpt-00NN.npz` are eight pulled checkpoints (arrays of the trainer state), `stage1-1x460x384.txt` and `stage1-1x496x300.txt` are the stage logs.
* `colab-chem-2026-10-25/runs/chem-2-20261025T210558Z/out/stage-1-1x460x384/`: Colab A100 run 2 (75% of the budget in Gauss-Newton), same `history.jsonl` and `train_report.json` layout.
* `chemistry-negative-results-2026-10-26/chem1_checkpoint_error2.json`: pair-space `error_2` of the eight chem-1 checkpoints, computed with the official target (chem-1's per-iteration logs were lost). Keys: `card`, `evidence_tier`, `run`, `final_from_stage1_logs`, `checkpoints` (per file: `checkpoint`, `shape`, `shape_key`, `E2_mHa`).
* `chemistry-shared-basis-2026-10-25/shared_basis_diagnostic.json`: commutator statistics, joint diagonalization and the greedy dictionary curve. `varpro_gate.json` and `varpro-dictionary/{A_b496_public,B_b460_pruned}/report.json`: exact inner solve and dictionary-only search reports.
* `plots/`: the five figures of the notebook (`trajectory-plot.png`, `spectrum.png`, `limbo-plot.png`, `greedy-plot.png`, `refit-decay-plot.png`).

Every file under `results/` that the notebook embeds has its SHA-256 pinned in the notebook and in `SHA256SUMS`.

#### `tools/`

Copies of the scripts, unmodified, laid out so their relative imports work (`tools/scripts/...`). See `tools/README.md`.

* `scripts/chemistry_campaign/scoring.py`: offline cost scorer; wraps Google Quantum AI's official `scoreinfra` equations (loaded by path from the competition data).
* `scripts/chemistry_campaign/common.py`: helpers imported by `scoring.py`.
* `scripts/chemistry_varpro_gate.py`: exact QR-metric inner solve (best two-body error for a fixed dictionary).
* `scripts/chemistry_shared_basis_diagnostic.py`: spectrum, commutators, joint diagonalization, greedy dictionary.
* `scripts/run_notebook_cells.py`: runs every code cell of a notebook headless and times each cell.

#### Root

`SHA256SUMS`, `LICENSE` (Apache-2.0), `NOTICE`, `cover.png`.

### How to use

The tools need the official competition data (`verifiers/dfthcsos/`, which holds the FCIDUMP, fixed shifts and `scoreinfra`), numpy and scipy. Put or link the competition's `verifiers` folder at `tools/data/official_full/verifiers`, then follow `tools/README.md`. The public `(1, 496, 384)` factorization is [Dmitrii Gluzdov's dataset](https://www.kaggle.com/datasets/dmitriigluzdov/vqcc-femoco-public-factorization); it is not redistributed here. To read a trajectory: `import json; [json.loads(l) for l in open(path)]`, then plot `E2 * 1000` against `seconds`.

### Provenance

* Built 2026-10-26 from the project's experiment card `2026-10-26-chemistry-negative-results-notebook` and the cards it cites. The trainer runs date from 2026-10-25.
* Source notebook: <https://www.kaggle.com/code/manwithacat/chemistry-negative-results-what-fails-and-why>, hosted CPU run, version 2 (local build SHA-256 `a1198d8106d9bedc4012b7edf184d1cd51aabc4e5d35507e74766d6e07386f87`).
* Pinned official inputs (SHA-256): FCIDUMP `e5a48af7...e1bd`, fixed shifts `7b7facf6...cd87`, `dfthc_math.py` `ae82898d...f8`, `reference.py` `a2d5a631...ed71`, `costs_prepare.py` `7f1e190c...cf`; full values in `results/chemistry_negative_results.json`.
* The public file used for the inner-solve numbers is Gluzdov's `femoco_thc_r5.npz` (SHA-256 `a0da3225ba2047f43ae24f31881f2a71500d3f73eda24fadc73e9f67da68e13f`, dataset v5).
* Per-file hashes: `SHA256SUMS`.

### Credits

* [Google Quantum AI](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation): competition, verifiers, `scoreinfra`, cost model, starter kit ([paper](https://arxiv.org/html/2610.23832v2), [Qualtran kickmix](https://github.com/quantumlib/Qualtran/tree/main/kickmix)), Apache-2.0.
* [Dmitrii Gluzdov](https://www.kaggle.com/datasets/dmitriigluzdov/vqcc-femoco-public-factorization): public `(1, 496, 384)` factorization with 11-bit words (Apache-2.0).
* [anazemcev (Artem1410)](https://www.kaggle.com/datasets/anazemcev/vqcc-viberteam-verified-circuits): joint-norm refit; the PyTorch structure trainer and refit code behind the trajectories (vendored, Apache-2.0).
* [Ahmed Berat Ozer](https://www.kaggle.com/code/ahmedberatozer/quantum-ai-df-thc-group-compression): group compression, 10-bit signed gauge, banked lookups.
* [Phuc Thai](https://www.kaggle.com/code/phucthaiv02/qcc-verified-portfolio-df-thc-retraining-study): retraining study and the fixed-word refit.
* [mrmeows](https://www.kaggle.com/code/mrmeows/15-75-circuits-let-s-all-reach-the-plateau): 8-bit workspace cliff, exact ANF lookups, the 0.5% gauge bound (author-reported).
* [michaelrustad](https://www.kaggle.com/michaelrustad): the `(10, 129, 60)` factorization; [marculera](https://www.kaggle.com/marculera): exact lookup compilers.
* [Alex Chilton](https://www.kaggle.com/code/alexchilton/toffolis-go-18-3-schur-dqi-at-883-qubits): public portfolio combining these components.

### License

Apache-2.0 (see `LICENSE` and `NOTICE`). Reused code keeps its own Apache-2.0 notices.
