# QCC Circuit Atlas

**Every public circuit of Google's quantum compilation contest, with tools.** A deduplicated, credited map of the circuits that people have published for the Google Quantum AI
[Verifiable Quantum Circuit Compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation) competition, the readable text (kmx) of every invsqrt and
chemistry circuit whose licence allows it, and a small set of pure-numpy tools (simulator, liveness, splicing, a
chemistry loader check) that run without the competition's `kickmix` package.

## At a glance

| Task | Distinct files listed | Included here | What is included |
|---|---:|---:|---|
| invsqrt | 54 circuits | 54 | readable `.kmx` text |
| chemistry (dfthcsos) | 1,342 loaders + 272 factorizations in 338 families | 1,342 + 272 (318 complete families) | `.kmx` text, `.npz` |
| dqi | 51 circuits | 0 | metadata only (each file is very large) |

Collected from 130 public notebooks and 3 public datasets by
8 scan run(s) (qcc-public-scan, qcc-public-scan-2, qcc-public-scan-3, qcc-public-scan-4, qcc-public-scan-5, qcc-public-scan-6, qcc-public-scan-7, qcc-public-scan-8).
7 files or families carry an official-verifier result from our own submissions.

## Why this dataset

* **One table of the public landscape.** Who published which circuit first, how many notebooks re-use it, its
  qubits and static Toffoli count: filter, sort and plot the frontier in two lines of pandas.
* **Circuits you can read.** The competition's `.kmb` files are binary. The `.kmx` text here is the same circuit,
  one op per line (`CCX q3 q7 q12`), ready for `grep`, diffing, and your own analysis.
* **Tools that run anywhere.** `tools/kmsim.py` simulates the invsqrt task exactly with numpy; on circuit
  `9c708f7b9abc` its worst error over tolerance (0.9993237694056958) equals the official verifier's.
* **Credit where it is due.** Every row names its first source and author and lists every other source that holds
  the identical bytes.

## Files

| Path | What it is |
|---|---|
| `circuits.csv` | One row per distinct file (circuit or chemistry factorization) found in public sources, deduplicated by SHA-256 prefix. 1,719 rows. |
| `families.csv` | One row per distinct chemistry family (a set of angle_k loaders plus its factorization). 338 rows. |
| `sources.csv` | One row per scanned public notebook, dataset or competition data folder, with its licence. 133 rows. |
| `kmx/invsqrt/<sha12>.kmx` | invsqrt circuits as kickmix text. 54 files, 31.4 MB. |
| `kmx/chemistry/loaders/<sha12>.kmx` | Chemistry angle loaders as kickmix text, each stored once. 1,342 files, 81.2 MB. |
| `factorizations/<sha12>.npz` | Chemistry factorizations (`submission.npz`), byte for byte. 272 files, 358.6 MB. |
| `tools/` | Apache-2.0 Python tools and their tests; see `tools/README.md`. |
| `tools/build/` | The scripts that built this dataset from the scan outputs. |
| `cover.png` | Cover image: qubits against static Toffoli count of every measured public circuit. |

Chemistry loaders are shared between many families, so they are stored once, by hash. To get the folder of one
family (angle_k_*.kmx plus submission.npz), run `python tools/atlas_family.py FAMILY_ID OUTDIR`.

## Quick start

**1. Load the table and look at the invsqrt frontier**

```python
import pandas as pd
ROOT = "/kaggle/input/qcc-circuit-atlas"   # adjust to where the dataset is attached
c = pd.read_csv(f"{ROOT}/circuits.csv")
inv = c[(c.task == "invsqrt") & c.qubits.notna()]
print(inv.sort_values(["toffoli_static", "qubits"])[["sha12", "qubits", "toffoli_static", "author", "n_sources"]].head(10))
print(c.groupby(["task", "file_type"]).included.agg(["size", "sum"]))
```

**2. Simulate an invsqrt circuit with kmsim (no kickmix needed)**

```python
import sys, numpy as np
sys.path.insert(0, f"{ROOT}/tools")
import kmsim
report, sim = kmsim.check(f"{ROOT}/kmx/invsqrt/6c6a734dbcb6.kmx", np.arange(1, 4097, dtype=np.int64))
print(report)   # worst_ratio < 1 on these x, restored input, clean scratch, mean Toffolis
```

or from a shell: `python tools/kmsim.py kmx/invsqrt/6c6a734dbcb6.kmx --xmax 4096` (use `--xmax 3133452` for every input; minutes).

**3. Rebuild and check one chemistry family**

```python
import subprocess
fam = pd.read_csv(f"{ROOT}/families.csv")
print(fam[fam.complete_in_atlas].sort_values("toffoli_static_sum").head())
subprocess.run([sys.executable, f"{ROOT}/tools/atlas_family.py", "alexchilton__24-94-lb-verified-three-task-portfolio__e9cffb841c4b", "/kaggle/working/fam"], check=True)
subprocess.run([sys.executable, f"{ROOT}/tools/loader_check.py", "/kaggle/working/fam"], check=True)
```

`loader_check.py` emulates the chemistry loader contract locally (clean workspace, unchanged selection, no phase,
forward and reverse word blocks); a PASS is a local check, not an official score.

## Column dictionary

### circuits.csv

| Column | Type | Meaning |
|---|---|---|
| `task` | string | Competition task: invsqrt, dqi or chemistry (the dfthcsos task). |
| `file_type` | string | circuit (a kickmix .kmb circuit) or factorization (a chemistry family's submission.npz). |
| `file_name` | string | File name in the source, e.g. invsqrt.kmb, dqi.kmb, angle_k_3.kmb or submission.npz. |
| `angle_k` | integer | Chemistry loaders only: the k of angle_k_<k>.kmb (loader position in its family). Empty otherwise. |
| `sha12` | string | First 12 hex characters of the SHA-256 of the file bytes as published (the row key; files are deduplicated by it). |
| `sha256` | string | Full SHA-256 when known (from our official-verifier receipts, or computed from factorization bytes). Empty when unknown. |
| `qubits` | integer | Number of qubits of the circuit, read by kickmix in the scan. Empty when not measured. |
| `toffoli_static` | integer | Static count of Toffoli-like ops (CCX, CCZ, CSWAP) in the file, from kickmix operation statistics in the scan. Not the verifier's expected count. Empty when not measured. |
| `ops` | integer | Number of operations in the circuit, from the scan. Empty when not measured. |
| `metrics_status` | string | ok, not a circuit (factorizations), or why qubits/toffoli_static/ops are empty. |
| `family_ids` | string | Chemistry only: the family_id(s) in families.csv that contain this file (one file can be shared by several families), separated by ';'. |
| `first_source_type` | string | notebook, dataset or competition: the kind of the first source (see first_source_ref). |
| `first_source_ref` | string | Kaggle owner/slug of the source credited for the file: the competition if the file is official data, else the first public notebook that holds it, else the first dataset. |
| `first_source_url` | string | Kaggle URL of first_source_ref. |
| `first_source_path` | string | Where the file sits inside that source's output (archive:member for zip files). |
| `author` | string | Kaggle user name of the owner of first_source_ref. |
| `author_url` | string | Kaggle profile URL of author. |
| `credited_notebook_url` | string | When the first source is the aggregator dataset manwithacat/vqcc-apache-public-circuits: the original notebook it credits for this circuit or family. Empty otherwise. |
| `credited_author` | string | Display name of the author that manwithacat/vqcc-apache-public-circuits credits (see credited_notebook_url). |
| `n_sources` | integer | Number of distinct public sources (notebooks, datasets) whose output holds the identical file. |
| `all_sources` | string | All those sources as owner/slug, separated by ';', first source first. |
| `first_seen_scan` | string | Name of our scan run (Kaggle notebook) that first recorded the file. |
| `first_seen_date` | string | UTC date of that scan run's output. |
| `licence` | string | Licence of the source we redistribute the file under (licence_source), lower-case Kaggle licence name; competition-data for official files. |
| `licence_basis` | string | How the licence was established (dataset metadata read with the Kaggle CLI, a recorded notebook footer, or the Kaggle default for public notebooks). |
| `licence_source` | string | The source whose licence applies to the copy in this dataset (normally first_source_ref). |
| `included` | boolean | True when a copy of the file is in this dataset (at included_path). |
| `included_path` | string | Path of the copy in this dataset: kmx/invsqrt/<sha12>.kmx, kmx/chemistry/loaders/<sha12>.kmx or factorizations/<sha12>.npz. |
| `exclusion_reason` | string | Why the file is metadata only (empty when included). |
| `verified_status` | string | PASS/FAIL from the official verifier in one of our own submission receipts, when this exact file (by full SHA-256) was scored there. invsqrt and dqi only. |
| `verified_score` | number | Task score from that official verifier run (lower is better). |
| `verified_toffoli_count` | number | Expected Toffoli count reported by that official verifier run. |
| `verified_receipts` | string | Which of our receipts scored this file (folder and notebook name), separated by ';'. |

### families.csv

| Column | Type | Meaning |
|---|---|---|
| `family_id` | string | Family key: <owner>__<slug>__<factorization sha12> of the first source holding this exact set of files ('set-<hash>' when there is no single factorization). |
| `first_source_type` | string | notebook, dataset or competition. |
| `first_source_ref` | string | Kaggle owner/slug of the first source of the family (same rule as circuits.csv). |
| `first_source_url` | string | Kaggle URL of first_source_ref. |
| `first_source_path` | string | Folder of the family inside that source's output (or inside its submission archive). |
| `author` | string | Kaggle user name of the owner of first_source_ref. |
| `credited_notebook_url` | string | Original notebook credited by manwithacat/vqcc-apache-public-circuits when that dataset is the first source. |
| `credited_author` | string | Display name credited by manwithacat/vqcc-apache-public-circuits. |
| `npz_sha12` | string | sha12 of the family's factorization (submission.npz). |
| `n_loaders` | integer | Number of angle_k loader circuits in the family. |
| `angle_ks` | string | The loader indices k present, separated by ';'. |
| `loader_sha12s` | string | k:sha12 for every loader, separated by ';' (look the files up in circuits.csv). |
| `qubits_max` | integer | Largest qubit count over the loaders (from the scan). Empty if any loader was not measured. |
| `toffoli_static_sum` | integer | Sum of the loaders' static Toffoli-like counts (from the scan). Not the verifier's cost. Empty if any loader was not measured. |
| `ops_sum` | integer | Sum of the loaders' op counts. Empty if any loader was not measured. |
| `n_sources` | integer | Number of distinct sources holding this exact family. |
| `all_sources` | string | Those sources as owner/slug, separated by ';'. |
| `first_seen_scan` | string | Our scan run that first recorded the family. |
| `loaders_included` | integer | How many of the family's loaders are in this dataset. |
| `factorization_included` | boolean | True when the family's submission.npz is in this dataset. |
| `complete_in_atlas` | boolean | True when every loader and the factorization are in this dataset (tools/atlas_family.py can rebuild the folder). |
| `verified_status` | string | PASS/FAIL of the official chemistry verifier in one of our receipts, when it scored exactly this family. |
| `verified_score` | number | Chemistry task score from that run (lower is better). |
| `verified_toffoli_count` | number | Toffoli count reported by that run. |
| `verified_lambda_eff` | number | lambda_eff reported by that run. |
| `verified_num_qubits` | integer | Qubit count reported by that run. |
| `verified_receipts` | string | Which of our receipts scored this family. |

### sources.csv

| Column | Type | Meaning |
|---|---|---|
| `source_ref` | string | Kaggle owner/slug (competition:<slug> for the competition's own data). |
| `source_type` | string | notebook, dataset or competition. |
| `owner` | string | Kaggle user name of the owner. |
| `slug` | string | Kaggle slug of the notebook or dataset. |
| `url` | string | Kaggle URL. |
| `licence` | string | Licence (lower-case Kaggle name). |
| `licence_basis` | string | How the licence was established. |
| `scans` | string | Our scan runs that read this source, separated by ';'. |
| `distinct_files` | integer | Distinct circuit/factorization files found in this source. |
| `first_source_of` | integer | Rows of circuits.csv credited to this source. |
| `first_source_of_included` | integer | Of those, how many are included in this dataset. |

Empty cells mean "unknown or not applicable", never zero.

## Provenance and collection method

1. **Sources.** The list of public notebooks of the competition that publish circuit files, plus the public datasets
   that hold circuits, was attached read-only as inputs to our private scan notebooks on Kaggle
   (qcc-public-scan, qcc-public-scan-2, qcc-public-scan-3, qcc-public-scan-4, qcc-public-scan-5, qcc-public-scan-6, qcc-public-scan-7, qcc-public-scan-8). Nothing from a source was executed.
2. **Scan.** Each scan walks the attached inputs and opens every `*.kmb`, `*.kmb.xz`, `*.npz` and every `.kmb`/`.npz`
   inside `.zip` archives. A file is classified by name (`invsqrt*`, `dqi*`, `angle_k_*`, `*.npz`), hashed with
   SHA-256, and loaded once per distinct hash with the competition's own `kickmix` (qubits, Toffoli-like count,
   op count); invsqrt and chemistry circuits are written out as `.kmx` text with kickmix.
3. **Merge (this dataset).** `tools/build/build_atlas.py` merges all scan runs, deduplicates by hash, picks the
   first source (competition data, then notebooks, then datasets; ties in scan order), groups chemistry files into
   families (files that sit in one folder or archive of one source, keyed by their exact set of hashes), applies
   the licence rule below and copies the allowed files. It is deterministic and re-run when new scan runs arrive.
4. **Verification results** come only from the official verifier output in our own submission receipts
   (`verified_*` columns); every other number comes from the scan.
5. **Credits** for files that we found only in the aggregator dataset manwithacat/vqcc-apache-public-circuits are
   copied from its manifest (names and links only).

Scan runs used for this version:

| Scan run | Rows | Output date (UTC) |
|---|---:|---|
| qcc-public-scan | 5,672 | 2026-11-12 |
| qcc-public-scan-2 | 316 | 2026-11-12 |
| qcc-public-scan-3 | 321 | 2026-11-12 |
| qcc-public-scan-4 | 472 | 2026-11-12 |
| qcc-public-scan-5 | 368 | 2026-11-12 |
| qcc-public-scan-6 | 440 | 2026-11-12 |
| qcc-public-scan-7 | 347 | 2026-11-12 |
| qcc-public-scan-8 | 307 | 2026-11-12 |

## Licences

This dataset is released under **Apache 2.0**. A file is copied here only when a source that holds it allows
redistribution:

| Source type | Licence | Sources |
|---|---|---:|
| dataset | apache-2.0 | 2 |
| dataset | cc0-1.0 | 1 |
| notebook | apache-2.0 | 130 |

* **Public notebooks.** Kaggle releases public notebooks and their outputs under Apache 2.0 by default; we did not
  check each notebook page, so `licence_basis` says so (or names the recorded footer evidence where we have it).
  If you are an author and your notebook uses another licence, tell us and the file will be removed.
* **Datasets.** Licence read with `kaggle datasets metadata` (Apache 2.0 or CC0 for all scanned datasets).
* **Competition data** (the official sample files) is listed for reference but never copied.
* **DQI circuits** are listed but not copied (each is hundreds of MB as text); follow `first_source_url`.

Files that are metadata only, and why:

| Reason | Files |
|---|---:|
| DQI circuits are too large for this dataset: metadata only, binary at the source | 51 |

## Credits

Thank you to everyone who published their circuits. Every included file is credited in `circuits.csv`; by author:

| Kaggle user | Source(s) of included files | Included files |
|---|---|---|
| [adilshamim8](https://www.kaggle.com/adilshamim8) | [google-quantum-ai-101](https://www.kaggle.com/code/adilshamim8/google-quantum-ai-101) | 13 |
| [ahmedberatozer](https://www.kaggle.com/ahmedberatozer) | [quantum-ai-df-thc-group-compression](https://www.kaggle.com/code/ahmedberatozer/quantum-ai-df-thc-group-compression) | 17 |
| [ahoirg](https://www.kaggle.com/ahoirg) | [qcc-reproducible-circuit-portfolio](https://www.kaggle.com/code/ahoirg/qcc-reproducible-circuit-portfolio) | 17 |
| [aiokajima](https://www.kaggle.com/aiokajima) | [quantum-syed-own-reproduction-v3-public](https://www.kaggle.com/code/aiokajima/quantum-syed-own-reproduction-v3-public) | 2 |
| [alexahern](https://www.kaggle.com/alexahern) | [vqcc-v45-frontier-25-09-local-21-63-65-22-11-20](https://www.kaggle.com/code/alexahern/vqcc-v45-frontier-25-09-local-21-63-65-22-11-20) | 2 |
| [alexchilton](https://www.kaggle.com/alexchilton) | [24-94-lb-verified-three-task-portfolio](https://www.kaggle.com/code/alexchilton/24-94-lb-verified-three-task-portfolio) | 18 |
| [anazemcev](https://www.kaggle.com/anazemcev) | [quantum-circuits-881q-paired-dqi-r6-df-thc](https://www.kaggle.com/code/anazemcev/quantum-circuits-881q-paired-dqi-r6-df-thc), [quantum-circuits-signed-digit-memory](https://www.kaggle.com/code/anazemcev/quantum-circuits-signed-digit-memory), [quantum-circuits-source-exact-compilation](https://www.kaggle.com/code/anazemcev/quantum-circuits-source-exact-compilation), [quantum-circuits-thc-joint-norm-881q-dqi](https://www.kaggle.com/code/anazemcev/quantum-circuits-thc-joint-norm-881q-dqi) | 81 |
| [anglolodorf](https://www.kaggle.com/anglolodorf) | [qcc-agentic-qwen-sota-portfolio](https://www.kaggle.com/code/anglolodorf/qcc-agentic-qwen-sota-portfolio) | 23 |
| [apihpih](https://www.kaggle.com/apihpih) | [qcc-baseline-copy-of-yoyobar-portfolio-lb-24-94](https://www.kaggle.com/code/apihpih/qcc-baseline-copy-of-yoyobar-portfolio-lb-24-94) | 2 |
| [apogean](https://www.kaggle.com/apogean) | [vqcc-verified-portfolio-reproducible-assembly](https://www.kaggle.com/code/apogean/vqcc-verified-portfolio-reproducible-assembly) | 16 |
| [atakanaldemir](https://www.kaggle.com/atakanaldemir) | [qcc-early-measurement-and-domain-aware-inverse](https://www.kaggle.com/code/atakanaldemir/qcc-early-measurement-and-domain-aware-inverse), [qcc-gap-3-residue-repair-and-c43-native-compiler](https://www.kaggle.com/code/atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler), [qcc-shared-products-and-controlled-refits](https://www.kaggle.com/code/atakanaldemir/qcc-shared-products-and-controlled-refits), [qcc-terminal-readout-and-phase-folds](https://www.kaggle.com/code/atakanaldemir/qcc-terminal-readout-and-phase-folds), [quantum-circuits-iso-gap-dqi-h5](https://www.kaggle.com/code/atakanaldemir/quantum-circuits-iso-gap-dqi-h5) | 41 |
| [auriclee](https://www.kaggle.com/auriclee) | [25-23800-one-small-step](https://www.kaggle.com/code/auriclee/25-23800-one-small-step) | 3 |
| [avazaku](https://www.kaggle.com/avazaku) | [c60-gauge-descent-full-xor-qrom](https://www.kaggle.com/code/avazaku/c60-gauge-descent-full-xor-qrom), [epigraph-rank-scales-889-qubit-dqi](https://www.kaggle.com/code/avazaku/epigraph-rank-scales-889-qubit-dqi), [free-gap-sqp-889-qubit-dqi](https://www.kaggle.com/code/avazaku/free-gap-sqp-889-qubit-dqi), [probe-ranked-jacobi-889-qubit-dqi](https://www.kaggle.com/code/avazaku/probe-ranked-jacobi-889-qubit-dqi), [quantum-circuits-7-bit-bounds](https://www.kaggle.com/code/avazaku/quantum-circuits-7-bit-bounds) | 51 |
| [ayodejiibrahimlateef](https://www.kaggle.com/ayodejiibrahimlateef) | [vqcc-24-56308-local](https://www.kaggle.com/code/ayodejiibrahimlateef/vqcc-24-56308-local) | 17 |
| [busyaprime](https://www.kaggle.com/busyaprime) | [lb-25-33133-grimoire-33-every-gate-a-pixel](https://www.kaggle.com/code/busyaprime/lb-25-33133-grimoire-33-every-gate-a-pixel) | 1 |
| [chetanamachireddy](https://www.kaggle.com/chetanamachireddy) | [quantum-circuit-compilation-from-source](https://www.kaggle.com/code/chetanamachireddy/quantum-circuit-compilation-from-source) | 2 |
| [clarelaurent](https://www.kaggle.com/clarelaurent) | [observatory-three-audited-circuit-studies](https://www.kaggle.com/code/clarelaurent/observatory-three-audited-circuit-studies) | 15 |
| [dedquoc](https://www.kaggle.com/dedquoc) | [quantum-circuit-synthesis-loop](https://www.kaggle.com/code/dedquoc/quantum-circuit-synthesis-loop) | 1 |
| [dmitriigluzdov](https://www.kaggle.com/dmitriigluzdov) | [quantum-circuit-compilation-from-source](https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source) | 1 |
| [gengsr](https://www.kaggle.com/gengsr) | [lb-25-2268-shifter-46-own-chemistry-loaders](https://www.kaggle.com/code/gengsr/lb-25-2268-shifter-46-own-chemistry-loaders) | 16 |
| [guruprasaathas111](https://www.kaggle.com/guruprasaathas111) | [quantum-circuit-visualizer-diagnostic-guide-0](https://www.kaggle.com/code/guruprasaathas111/quantum-circuit-visualizer-diagnostic-guide-0) | 2 |
| [heliosli](https://www.kaggle.com/heliosli) | [quantum-ai-v1](https://www.kaggle.com/code/heliosli/quantum-ai-v1) | 13 |
| [hypery11](https://www.kaggle.com/hypery11) | [invsqrt-prototype-packaged-submission](https://www.kaggle.com/code/hypery11/invsqrt-prototype-packaged-submission) | 1 |
| [ibillxia](https://www.kaggle.com/ibillxia) | [qcc-25-23789-v104-invsqrt-dqi-marculera-chem](https://www.kaggle.com/code/ibillxia/qcc-25-23789-v104-invsqrt-dqi-marculera-chem) | 1 |
| [isabe11am00re](https://www.kaggle.com/isabe11am00re) | [qcc-v47-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v47-submission), [qcc-v49-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v49-submission), [qcc-v58x-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v58x-submission), [qcc-v65wqq-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v65wqq-submission), [qcc-v66s33w-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v66s33w-submission) | 52 |
| [jakomina](https://www.kaggle.com/jakomina) | [kickmix-v1](https://www.kaggle.com/code/jakomina/kickmix-v1) | 1 |
| [kamalkadakara](https://www.kaggle.com/kamalkadakara) | [gq26-q2-public-25137](https://www.kaggle.com/code/kamalkadakara/gq26-q2-public-25137) | 2 |
| [kirilltym](https://www.kaggle.com/kirilltym) | [quantum-circuits-conditional-uncompute-audit](https://www.kaggle.com/code/kirilltym/quantum-circuits-conditional-uncompute-audit), [quantum-circuits-exact-gauge-5-word-qrom](https://www.kaggle.com/code/kirilltym/quantum-circuits-exact-gauge-5-word-qrom), [quantum-circuits-four-loaders-eight-toffolis](https://www.kaggle.com/code/kirilltym/quantum-circuits-four-loaders-eight-toffolis) | 11 |
| [koushikkumardinda](https://www.kaggle.com/koushikkumardinda) | [verifiable-quantum-circuit-compilation](https://www.kaggle.com/code/koushikkumardinda/verifiable-quantum-circuit-compilation) | 1 |
| [kozykappa](https://www.kaggle.com/kozykappa) | [google-quantum-ai-verifiable-quantum-circuit-comp](https://www.kaggle.com/code/kozykappa/google-quantum-ai-verifiable-quantum-circuit-comp), [quantum-ai-reproducible-verified-portfolio](https://www.kaggle.com/code/kozykappa/quantum-ai-reproducible-verified-portfolio), [quantum-circuits-sparse-sos-factors-and-circuit](https://www.kaggle.com/code/kozykappa/quantum-circuits-sparse-sos-factors-and-circuit) | 52 |
| [lightningv08](https://www.kaggle.com/lightningv08) | [bezout-schur-5-word-qrom](https://www.kaggle.com/code/lightningv08/bezout-schur-5-word-qrom) | 17 |
| [liuzewen123](https://www.kaggle.com/liuzewen123) | [qcc-three-task-portfolio-v1](https://www.kaggle.com/code/liuzewen123/qcc-three-task-portfolio-v1) | 1 |
| [magmacot](https://www.kaggle.com/magmacot) | [quantum-circuits-clean-workspace-reuse](https://www.kaggle.com/code/magmacot/quantum-circuits-clean-workspace-reuse) | 17 |
| [malavika2003nair](https://www.kaggle.com/malavika2003nair) | [quantum-7](https://www.kaggle.com/code/malavika2003nair/quantum-7) | 1 |
| [manwithacat](https://www.kaggle.com/manwithacat) | [vqcc-apache-public-circuits](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits), [vqcc-hedge-wizardry-notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook), [vqcc-quantum-voodoo](https://www.kaggle.com/code/manwithacat/vqcc-quantum-voodoo) | 793 |
| [maoxin123](https://www.kaggle.com/maoxin123) | [lb-24-798-pi-gauge-loaders-refit-chem-weights](https://www.kaggle.com/code/maoxin123/lb-24-798-pi-gauge-loaders-refit-chem-weights), [lb-24-94-chem-weight-refit-on-syed-loaders](https://www.kaggle.com/code/maoxin123/lb-24-94-chem-weight-refit-on-syed-loaders), [lb-25-303-combined-invsqrt-refit-chem](https://www.kaggle.com/code/maoxin123/lb-25-303-combined-invsqrt-refit-chem) | 19 |
| [marculera](https://www.kaggle.com/marculera) | [df-thc-10x-compact-groups-from-the-hamiltonian](https://www.kaggle.com/code/marculera/df-thc-10x-compact-groups-from-the-hamiltonian), [df-thc-merge-groups-before-dropping-them](https://www.kaggle.com/code/marculera/df-thc-merge-groups-before-dropping-them) | 91 |
| [masonbradleygilhool](https://www.kaggle.com/masonbradleygilhool) | [qcc-floor-portfolio-verified-three-task-submissi](https://www.kaggle.com/code/masonbradleygilhool/qcc-floor-portfolio-verified-three-task-submissi) | 2 |
| [michaelrustad](https://www.kaggle.com/michaelrustad) | [vqcc-r10-merged-group-chemistry-12-87-lb](https://www.kaggle.com/code/michaelrustad/vqcc-r10-merged-group-chemistry-12-87-lb) | 12 |
| [mizeroluckygall](https://www.kaggle.com/mizeroluckygall) | [quantum-circuits-rotation-calibration](https://www.kaggle.com/code/mizeroluckygall/quantum-circuits-rotation-calibration), [quantum-circuits-rotation-calibration-39-char](https://www.kaggle.com/code/mizeroluckygall/quantum-circuits-rotation-calibration-39-char), [quantum-circuits-rotation-margin-calibration](https://www.kaggle.com/code/mizeroluckygall/quantum-circuits-rotation-margin-calibration) | 32 |
| [mos3santos](https://www.kaggle.com/mos3santos) | [quantum-circuits](https://www.kaggle.com/code/mos3santos/quantum-circuits) | 16 |
| [mrmeows](https://www.kaggle.com/mrmeows) | [21-0-circuits-let-s-all-reach-the-plateau](https://www.kaggle.com/code/mrmeows/21-0-circuits-let-s-all-reach-the-plateau), [qcc-14-50-everything-i-learned-open-circuits](https://www.kaggle.com/code/mrmeows/qcc-14-50-everything-i-learned-open-circuits) | 23 |
| [ndaedzomukhuba](https://www.kaggle.com/ndaedzomukhuba) | [quantum-chem-refit](https://www.kaggle.com/code/ndaedzomukhuba/quantum-chem-refit) | 7 |
| [nursrijan](https://www.kaggle.com/nursrijan) | [qcc-25-2268-verified-sota-portfolio](https://www.kaggle.com/code/nursrijan/qcc-25-2268-verified-sota-portfolio) | 16 |
| [pablodiegoo](https://www.kaggle.com/pablodiegoo) | [google-quantum-compilation-starter-notebook](https://www.kaggle.com/code/pablodiegoo/google-quantum-compilation-starter-notebook) | 1 |
| [phucthaiv02](https://www.kaggle.com/phucthaiv02) | [qcc-verified-portfolio-df-thc-retraining-study](https://www.kaggle.com/code/phucthaiv02/qcc-verified-portfolio-df-thc-retraining-study) | 27 |
| [pramitdas](https://www.kaggle.com/pramitdas) | [qcc-public-frontier-submission-25-218](https://www.kaggle.com/code/pramitdas/qcc-public-frontier-submission-25-218) | 3 |
| [qiuqiuh](https://www.kaggle.com/qiuqiuh) | [qcc-refresh-v65w-sx-sy7-inverse](https://www.kaggle.com/code/qiuqiuh/qcc-refresh-v65w-sx-sy7-inverse) | 17 |
| [ranjeet258](https://www.kaggle.com/ranjeet258) | [qcc-verified-portfolio-improvement](https://www.kaggle.com/code/ranjeet258/qcc-verified-portfolio-improvement) | 12 |
| [rdaccel](https://www.kaggle.com/rdaccel) | [qcc-25-29657-reproduction-busyaprime](https://www.kaggle.com/code/rdaccel/qcc-25-29657-reproduction-busyaprime), [qcc-v58-c40b-reproduction-lb-23-73311-heliosli](https://www.kaggle.com/code/rdaccel/qcc-v58-c40b-reproduction-lb-23-73311-heliosli) | 4 |
| [rudrabhaskar](https://www.kaggle.com/rudrabhaskar) | [highest-public-score-direct-polynomial-phasing](https://www.kaggle.com/code/rudrabhaskar/highest-public-score-direct-polynomial-phasing) | 10 |
| [saddamaditya](https://www.kaggle.com/saddamaditya) | [narrowed-877q-dqi-and-progressive-r10-chemistry](https://www.kaggle.com/code/saddamaditya/narrowed-877q-dqi-and-progressive-r10-chemistry) | 16 |
| [seyitkaangunes](https://www.kaggle.com/seyitkaangunes) | [verified-circuit-quick-wins](https://www.kaggle.com/code/seyitkaangunes/verified-circuit-quick-wins), [verified-portfolio-best-public-circuit-per-task](https://www.kaggle.com/code/seyitkaangunes/verified-portfolio-best-public-circuit-per-task) | 17 |
| [sigmaborov](https://www.kaggle.com/sigmaborov) | [22-85569-lb-exact-gauge-search](https://www.kaggle.com/code/sigmaborov/22-85569-lb-exact-gauge-search) | 2 |
| [somejoint](https://www.kaggle.com/somejoint) | [quantum-circuits-24-65-local-gm-chem-refit](https://www.kaggle.com/code/somejoint/quantum-circuits-24-65-local-gm-chem-refit) | 16 |
| [soukeaizenz](https://www.kaggle.com/soukeaizenz) | [vqcc-from-source-gf2-banked-chemistry](https://www.kaggle.com/code/soukeaizenz/vqcc-from-source-gf2-banked-chemistry) | 2 |
| [syed3000](https://www.kaggle.com/syed3000) | [vqcc-24-43-portfolio](https://www.kaggle.com/code/syed3000/vqcc-24-43-portfolio) | 2 |
| [tuannm3812](https://www.kaggle.com/tuannm3812) | [verifiable-quantum-circuit-compilation-portfolio](https://www.kaggle.com/code/tuannm3812/verifiable-quantum-circuit-compilation-portfolio) | 1 |
| [zongaobian](https://www.kaggle.com/zongaobian) | [quantum-circuits-signed-digits-bm-psi-qrom](https://www.kaggle.com/code/zongaobian/quantum-circuits-signed-digits-bm-psi-qrom) | 16 |

Files taken from the aggregator dataset [manwithacat/vqcc-apache-public-circuits](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits) are credited there to these original notebooks (also in the `credited_*` columns):

| Author (as credited there) | Original notebook |
|---|---|
| Aamod06 | [the-dataset-is-public-now-enjoy](https://www.kaggle.com/code/aamod06/the-dataset-is-public-now-enjoy) |
| Agniv Banerjee | [quantum-circuits-22-44-local-gm-our-chemistry](https://www.kaggle.com/code/somejoint/quantum-circuits-22-44-local-gm-our-chemistry) |
| Agniv Banerjee | [quantum-circuits-22-67-local-gm-full-xor-chem](https://www.kaggle.com/code/somejoint/quantum-circuits-22-67-local-gm-full-xor-chem) |
| Agniv Banerjee | [quantum-circuits-23-46-local-gm-900-qubit-dqi](https://www.kaggle.com/code/somejoint/quantum-circuits-23-46-local-gm-900-qubit-dqi) |
| Agniv Banerjee | [quantum-circuits-23-65-local-gm-898-qubit-dqi](https://www.kaggle.com/code/somejoint/quantum-circuits-23-65-local-gm-898-qubit-dqi) |
| Agniv Banerjee | [quantum-circuits-23-85-local-gm-892-qubit-dqi](https://www.kaggle.com/code/somejoint/quantum-circuits-23-85-local-gm-892-qubit-dqi) |
| Agniv Banerjee | [qcc-ladder-parts](https://www.kaggle.com/datasets/somejoint/qcc-ladder-parts) |
| Ahmed Berat Özer | [quantum-ai-df-thc-group-compression](https://www.kaggle.com/code/ahmedberatozer/quantum-ai-df-thc-group-compression) |
| Akmal Xodarev (Busya PRIME) | [23-910-local-gm-exact-dqi-rewrites-892-qubits](https://www.kaggle.com/code/busyaprime/23-910-local-gm-exact-dqi-rewrites-892-qubits) |
| Akmal Xodarev (Busya PRIME) | [lb-22-86841-22x-cheaper-than-google-s-circuits](https://www.kaggle.com/code/busyaprime/lb-22-86841-22x-cheaper-than-google-s-circuits) |
| Akmal Xodarev (Busya PRIME) | [lb-24-73387-top-30-qcc-notebooks-re-verified](https://www.kaggle.com/code/busyaprime/lb-24-73387-top-30-qcc-notebooks-re-verified) |
| AlekseiProvorov | [but-some-q-squared-width-lab](https://www.kaggle.com/code/leoprovorov/but-some-q-squared-width-lab) |
| AlekseiProvorov | [full-xor-chemistry-no-borrowed-bits](https://www.kaggle.com/code/leoprovorov/full-xor-chemistry-no-borrowed-bits) |
| AlekseiProvorov | [the-unbearable-lightness-of-quantum-circuits](https://www.kaggle.com/code/leoprovorov/the-unbearable-lightness-of-quantum-circuits) |
| Alex Ahern | [vqcc-v36-portfolio-23-37-local-20-65-61-36-10-07](https://www.kaggle.com/code/alexahern/vqcc-v36-portfolio-23-37-local-20-65-61-36-10-07) |
| alex chilton | [22-57-lb-verified-three-task-portfolio](https://www.kaggle.com/code/alexchilton/22-57-lb-verified-three-task-portfolio) |
| alex chilton | [23-87-lb-verified-three-task-portfolio](https://www.kaggle.com/code/alexchilton/23-87-lb-verified-three-task-portfolio) |
| alex chilton | [24-79-lb-verified-three-task-portfolio](https://www.kaggle.com/code/alexchilton/24-79-lb-verified-three-task-portfolio) |
| Andrew Oscar | [qcc-24-86-fork](https://www.kaggle.com/code/andrewoscar/qcc-24-86-fork) |
| ANGOUAH | [quantum-ai-frontier-v10](https://www.kaggle.com/code/anglolodorf/quantum-ai-frontier-v10) |
| Atakan Aldemir | [qcc-17-product-dqi-reuse-at-892-qubits](https://www.kaggle.com/code/atakanaldemir/qcc-17-product-dqi-reuse-at-892-qubits) |
| Atakan Aldemir | [qcc-gap-3-residue-repair-and-c43-native-compiler](https://www.kaggle.com/code/atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler) |
| Atakan Aldemir | [quantum-circuits-iso-gap-dqi-h5](https://www.kaggle.com/code/atakanaldemir/quantum-circuits-iso-gap-dqi-h5) |
| avazaku | [active-face-sqp-895-qubit-dqi](https://www.kaggle.com/code/avazaku/active-face-sqp-895-qubit-dqi) |
| avazaku | [gauge-prox-sign-copy-qrom](https://www.kaggle.com/code/avazaku/gauge-prox-sign-copy-qrom) |
| avazaku | [google-quantum-ai-r8-block-gauge-5-word-qrom](https://www.kaggle.com/code/avazaku/google-quantum-ai-r8-block-gauge-5-word-qrom) |
| avazaku | [slack-homotopy-897-qubit-dqi](https://www.kaggle.com/code/avazaku/slack-homotopy-897-qubit-dqi) |
| Baidalin Adilzhan [dsmlkz] | [quantumai-improved-public-oct29](https://www.kaggle.com/code/baidalinadilzhan/quantumai-improved-public-oct29) |
| Den Pugovkin | [twelve-bits-fails](https://www.kaggle.com/code/denpugovkin/twelve-bits-fails) |
| Dmitrii Gluzdov | [quantum-circuit-compilation-from-source](https://www.kaggle.com/code/dmitriigluzdov/quantum-circuit-compilation-from-source) |
| Dmitry Abulkhanov | [vqcc-cand-0040-bit-identical-submission-rebuild](https://www.kaggle.com/code/dmitriyab/vqcc-cand-0040-bit-identical-submission-rebuild) |
| Dmitry Abulkhanov | [vqcc-cand-0044-bit-identical-submission-rebuild](https://www.kaggle.com/code/dmitriyab/vqcc-cand-0044-bit-identical-submission-rebuild) |
| Heliosli | [the-dataset-is-now-public-now-enjoy](https://www.kaggle.com/code/heliosli/the-dataset-is-now-public-now-enjoy) |
| Heliosli | [the-dataset-is-public-now-enjoy](https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy) |
| i want to run gemma 9b | [vqcc-dfthc-soft-word-loaders](https://www.kaggle.com/datasets/iwanttorungemma9b/vqcc-dfthc-soft-word-loaders) |
| i want to run gemma 9b | [vqcc-team-experiments-condensed](https://www.kaggle.com/datasets/iwanttorungemma9b/vqcc-team-experiments-condensed) |
| Isabe11aM00re | [qcc-v47-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v47-submission) |
| Isabe11aM00re | [qcc-v49-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v49-submission) |
| Isabe11aM00re | [qcc-v58x-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v58x-submission) |
| Isabe11aM00re | [qcc-v65wqq-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v65wqq-submission) |
| Isabe11aM00re | [qcc-v66s33w-submission](https://www.kaggle.com/code/isabe11am00re/qcc-v66s33w-submission) |
| Kaliden Aiarys | [quantum-circuit-compilation-public-lb-24-59425](https://www.kaggle.com/code/kalidenaiarys/quantum-circuit-compilation-public-lb-24-59425) |
| kawh1111 | [qcomp-harvest-v32](https://www.kaggle.com/code/kawh1111/qcomp-harvest-v32) |
| Kirill Tymchishin | [quantum-circuits-exact-gauge-5-word-qrom](https://www.kaggle.com/code/kirilltym/quantum-circuits-exact-gauge-5-word-qrom) |
| Kirill Tymchishin | [quantum-circuits-four-loaders-eight-toffolis](https://www.kaggle.com/code/kirilltym/quantum-circuits-four-loaders-eight-toffolis) |
| Kirill Tymchishin | [quantum-circuits-retained-product-audit](https://www.kaggle.com/code/kirilltym/quantum-circuits-retained-product-audit) |
| Kirill Tymchishin | [quantum-compilation-19](https://www.kaggle.com/code/kirilltym/quantum-compilation-19) |
| Kozykorpesh | [lb-21-38884-quantum-ai-q-circuits](https://www.kaggle.com/code/kozykappa/lb-21-38884-quantum-ai-q-circuits) |
| Leo Tang | [vqcc-t7421-submission](https://www.kaggle.com/code/leotang09/vqcc-t7421-submission) |
| Lera | [df-thc-10x-compact-groups-from-the-hamiltonian](https://www.kaggle.com/code/marculera/df-thc-10x-compact-groups-from-the-hamiltonian) |
| Magmucot | [qcc-76q-881q-dqi-verified-blend](https://www.kaggle.com/code/magmacot/qcc-76q-881q-dqi-verified-blend) |
| MAIDANG | [lb-24-94096-c44-and-exact-dqi-product-reuse](https://www.kaggle.com/code/daifanhao/lb-24-94096-c44-and-exact-dqi-product-reuse) |
| manwithacat | [vqcc-hedge-wizardry-notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook) |
| manwithacat (friends composite assembly) | [the-real-150k-was-the-friends-we-made](https://www.kaggle.com/code/manwithacat/the-real-150k-was-the-friends-we-made) |
| manwithacat (Hedge Wizardry HW-15) | [vqcc-hedge-wizardry-notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook) |
| maoxin123 | [lb-24-786-pi-gauge-loaders-transferred-weights](https://www.kaggle.com/code/maoxin123/lb-24-786-pi-gauge-loaders-transferred-weights) |
| maoxin123 | [lb-24-94-chem-weight-refit-on-syed-loaders](https://www.kaggle.com/code/maoxin123/lb-24-94-chem-weight-refit-on-syed-loaders) |
| maoxin123 | [lb-25-283-combined-invsqrt-refit-chem](https://www.kaggle.com/code/maoxin123/lb-25-283-combined-invsqrt-refit-chem) |
| matousakura | [best-of-public-portfolio-vqcc-24-0x-class](https://www.kaggle.com/code/matousakura/best-of-public-portfolio-vqcc-24-0x-class) |
| Michael Rustad | [vqcc-r10-c46-four-word-chemistry-21-41-lb](https://www.kaggle.com/code/michaelrustad/vqcc-r10-c46-four-word-chemistry-21-41-lb) |
| milos | [qcc-24-80-best-per-task-where-the-cost-goes](https://www.kaggle.com/code/milosg/qcc-24-80-best-per-task-where-the-cost-goes) |
| mrmeows | [qcc-1375-open-circuits](https://www.kaggle.com/datasets/mrmeows/qcc-1375-open-circuits) |
| Nilanjan_Saha123 | [21-87-fused-dqi-c46-chemistry-gold](https://www.kaggle.com/code/nilanjansaha123/21-87-fused-dqi-c46-chemistry-gold) |
| Nilanjan_Saha123 | [auto-assemble-the-best-qcc-portfolio-22-70](https://www.kaggle.com/code/nilanjansaha123/auto-assemble-the-best-qcc-portfolio-22-70) |
| Nilanjan_Saha123 | [auto-portfolio-drop-in-best-of-all-circuits](https://www.kaggle.com/code/nilanjansaha123/auto-portfolio-drop-in-best-of-all-circuits) |
| Nilanjan_Saha123 | [auto-updating-verified-quantum-portfolio-picker](https://www.kaggle.com/code/nilanjansaha123/auto-updating-verified-quantum-portfolio-picker) |
| Or4k2! | [quantum-circuit-compilation-pipeline](https://www.kaggle.com/code/orecord/quantum-circuit-compilation-pipeline) |
| Pablo Diego Pereira | [google-quantum-compilation-starter-notebook](https://www.kaggle.com/code/pablodiegoo/google-quantum-compilation-starter-notebook) |
| Pizzaboi | [task-iii-xor-contract-minimal-reproducer](https://www.kaggle.com/code/asimandia/task-iii-xor-contract-minimal-reproducer) |
| prvsiyan | [verifier-guided-quantum-circuit-optimization](https://www.kaggle.com/code/prvsiyan/verifier-guided-quantum-circuit-optimization) |
| prvsiyan | [vqcc-hw12-chemistry-circuits-snapshot](https://www.kaggle.com/datasets/prvsiyan/vqcc-hw12-chemistry-circuits-snapshot) |
| qiuqiu | [qcc-refresh-v70z-k5-ay3-bound-dqi](https://www.kaggle.com/code/qiuqiuh/qcc-refresh-v70z-k5-ay3-bound-dqi) |
| qwertykeypadapple | [qcc-kernel-search-24-65](https://www.kaggle.com/code/qwertykeypadapple/qcc-kernel-search-24-65) |
| Rishabh Bafna | [quantum-circuit-compilation-3-task-portfolio](https://www.kaggle.com/code/rishabhbafnaiiitd/quantum-circuit-compilation-3-task-portfolio) |
| Sargis Khachatryan | [column-epigraph-889-qubit-dqi](https://www.kaggle.com/code/avazaku/column-epigraph-889-qubit-dqi) |
| Sargis Khachatryan | [gauge-amplitude-cycle-888-qubit-dqi](https://www.kaggle.com/code/avazaku/gauge-amplitude-cycle-888-qubit-dqi) |
| SeshuRaju 🧘‍♂️ | [quantum-circuits-3-tasks-lb-19-2629](https://www.kaggle.com/code/seshurajup/quantum-circuits-3-tasks-lb-19-2629) |
| SeshuRaju 🧘‍♂️ | [quantum-circuits-3-tasks-lb-23-9062](https://www.kaggle.com/code/seshurajup/quantum-circuits-3-tasks-lb-23-9062) |
| sigmaborov | [22-85569-lb-exact-gauge-search](https://www.kaggle.com/code/sigmaborov/22-85569-lb-exact-gauge-search) |
| Syed Asad Ali | [vqcc-24-43-portfolio](https://www.kaggle.com/code/syed3000/vqcc-24-43-portfolio) |
| Syed Asad Ali | [vqcc-own-circuit-portfolio-notebook](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook) |
| tiraJoon | [qcc-portfolio-assembly](https://www.kaggle.com/code/junmiaotiao/qcc-portfolio-assembly) |
| Vyas Senthilkumar | [verified-assembly-of-public-qcc-circuits](https://www.kaggle.com/code/vyassenthilkumar/verified-assembly-of-public-qcc-circuits) |
| yoyobar | [lb-22-99-invsqrt-101-62-qubits](https://www.kaggle.com/code/yoyobar/lb-22-99-invsqrt-101-62-qubits) |
| yoyobar | [qcc-local-sota-20261031](https://www.kaggle.com/datasets/yoyobar/qcc-local-sota-20261031) |
| Zongao Bian | [quantum-circuits-signed-digits-bm-psi-qrom](https://www.kaggle.com/code/zongaobian/quantum-circuits-signed-digits-bm-psi-qrom) |
| Дворкин Евгений Владимирович | [google-quantum-ai-deep-eda-with-analogies](https://www.kaggle.com/code/evgendvorkin/google-quantum-ai-deep-eda-with-analogies) |

The [VQCC public circuits](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits) dataset by
manwithacat, with its own manifest and verifier runs, is a complementary collection of the original `.kmb` files;
use it when you need binaries, and this atlas when you want text, tools and one table across all sources.
The circuit language, verifiers and tasks are by the competition organisers (Google Quantum AI, Qualtran).

**AI assistance.** The scan, the builder, the tools and this README were written with the help of an AI coding
assistant (Anthropic's Claude), under the direction of and reviewed by the dataset owner. Every number comes from
the scan runs or official verifier receipts, not from the assistant.

## Update policy

Updated when new scan runs or new public circuits appear, until the competition ends: re-running the builder over
all scan outputs gives the next version; rows are never renamed (the key is `sha12`), new rows are appended.
Expected update frequency: weekly during the competition, then never.

## Limitations

* `toffoli_static` is a static count of Toffoli-like ops in the file, not the verifier's expected (average)
  Toffoli count or the task score.
* Some circuits come from research or candidate folders of a notebook and were never that notebook's submission.
* A notebook can change after we read it; the hash identifies exactly which bytes are described.
* Rows with `metrics_status` "not measured" were recorded in a scan run in which kickmix could not be loaded; they
  are listed with hash and source only.
* No claim about who designed a circuit is made beyond its first public source.

Not affiliated with Google, Qualtran or Kaggle.
