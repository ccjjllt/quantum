# QCC frontier 28.0948 sub1 pipeline

Reusable Kaggle **CPU** pipeline for the 2026-11-16 sub1 candidate.

**Status 2026-11-16 10:00 UTC:** sub1 was submitted as ref **58424363**, COMPLETE at public
**28.09486** — exactly the plateau, not silver. The bdae chemistry variant was then verified at
GM **28.0948754** (kernel v4, all three verifiers PASS, 18/18 hashes) but is **HELD, not
submitted**: it is still below the only worth-submitting gate **>= 28.09490**, and a later tie
submission would worsen our in-tie rank. Two daily slots remain. See `RESULT.md`,
`RESULT_bdae.md`, and `submission_receipt_bdae_hold.json`.

**CODE2 handoff (11:56 UTC):** `chem/CODE2.md` is a negative result. The 145-cut / 190-product
bases are a tie or loss against shipped products 189/190/191; the k14 one-gate win is not
emittable, and the mixed package was a failed negative control. No CODE2 candidate exists; no
slot was spent. See `CODE2_STATUS.md`.

## Candidate

| Task | File | SHA-256 (first 12) | Q | Expected official cost |
|---|---|---|---:|---:|
| invsqrt | `invsqrt.kmb` (embedded, maoxin123 `f2cdab0b`) | `f2cdab0b7afc` | 44 | 75,006.38 |
| DQI | `dqi.kmb` (`ccc2ab84`) | `ccc2ab84ed71` | 890 | 347,375,470,572 |
| chemistry | `dfthcsos/submission.npz` + `angle_k_0..14.kmb` (frontier table/loaders, `bdae290f` W/H2_I refit) | `bdae290f5d6b` | 427 | 294,762,632.08 |

Expected geometric mean **28.0948754**. The 28.09486 plateau has grown to 185 teams
(ranks 93-277) and the silver cutoff rank 156 is inside it, so **both sub1 (28.0948733) and bdae
(28.0948754) are HOLDs, not submits**. Only a measured **>= 28.09490** is worth another slot.

The `bdae290f` weights differ from the public frontier `f6e12f02` npz only in `W` and `H2_I`;
all other arrays, all 15 angle loaders, the DQI circuit and the invsqrt circuit are
byte-identical to the frontier package.

## What the kernel does

1. Finds the official competition root under `/kaggle/input` and asserts the three official
   verifier source hashes. It records the `kickmix.so` hash.
2. Finds every one of the 18 members **by SHA-256**, including decompressing `dqi.kmb.xz` and
   reading members out of zips if necessary. It asserts every hash and size after staging.
   The 44-qubit invsqrt is embedded as zlib/base64 and its decoded hash is asserted.
3. Runs the **unchanged** official verifiers at default salt and default shot counts:
   chemistry 78,080 shots, DQI 102,400 shots, invsqrt 200,540,928 shots.
4. Prints the full official JSON receipts and writes them to `logs/` and `receipt.json`.
5. Packages exactly 18 files into `submission.zip` (whitelist only, so no macOS `._` files),
   reads the zip back and re-asserts every member hash.
6. Sets `decision=SUBMIT` only if all three verifiers PASS and the geometric mean is
   `>= 28.09490` (strictly above the 28.09486 tie; the next public score is 28.09498).
   A GM in `28.0930 .. 28.09489` is written as `decision=HOLD_TIE` and exits 0 without
   spending a submission. A verifier failure or GM `< 28.0930` is `DO_NOT_SUBMIT` and exits 2.

## Files

| File | Purpose |
|---|---|
| `main.py` | self-contained Kaggle script kernel (generated) |
| `main_template.py` | source template; `INV_B64` placeholder |
| `invsqrt_f2cdab0b.kmb.b64` | zlib-compressed/base64 invsqrt payload |
| `make_main.py` | regenerates `main.py` from the template + payload |
| `members.json` | 18-member hash/size/source manifest and expected scores |
| `kernel-metadata.json` | Kaggle CPU metadata (no GPU, no TPU, no internet) |

## Run

```bash
cd experiments/frontier/20261116_push/pipeline
python3 make_main.py

export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)
~/.local/bin/kaggle kernels push -p .
~/.local/bin/kaggle kernels status qingyu1232/qcc-frontier-28094-verify

rm -rf /private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/pipeline_out
mkdir -p /private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/pipeline_out
~/.local/bin/kaggle kernels output qingyu1232/qcc-frontier-28094-verify \
  -p /private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/pipeline_out
```

## Submit only after a PASS + GM check

This is a Kaggle **code competition**: the local file-upload form of `competitions submit` hangs
on the GCS upload. Submit the verified kernel version and its named output instead:

```bash
export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)
~/.local/bin/kaggle competitions submit \
  -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-frontier-28094-verify -v 3 \
  -f submission.zip \
  -m "sub1 chem refit on 28.091 frontier: invsqrt f2cdab0b 44Q 75,006.38 + DQI ccc2ab84 890Q 347,375,470,572 + chem sub1 427Q 294,762,697.44; all 18 SHA-256 asserted; unchanged official verifiers PASS; GM 28.094873. Apache-2.0 credits: Syed Asad Ali, Ali Haydar Ozdag, Ertugrul Ozer, Asterios Panoras, James Barlow, Leo Tang, Hayato Hikawa, boristown, Lera/marculera, Google Quantum AI/Qualtran."

~/.local/bin/kaggle competitions submission <REF>
~/.local/bin/kaggle competitions submissions -c google-verifiable-quantum-circuit-compilation | head
```

Use at most **one** submission for this candidate. Record the ref before and after. The
`-k/-v` form submits the existing kernel output without re-uploading 50 MB and without re-running
the verifiers. The 2026-11-16 intermediate submission used this exception on kernel v3 and
scored 28.09486; do not repeat it for another tie package.

## Reuse for a later candidate

Replace the `MEMBERS`, `EXPECTED`, `REFERENCE` and `MIN_GM` constants in
`main_template.py` (or copy this directory and edit), replace `invsqrt_f2cdab0b.kmb.b64` and
`members.json`, regenerate `main.py`, and push with a new kernel `id`. The member locator,
hash assertions, official-verifier invocation, receipt and zip whitelist stay unchanged.

## Attribution

The submission description and `receipt.json` preserve Apache-2.0 attribution for the Syed
Asad Ali invsqrt/DQI generator lineage, Ali Haydar Özdağ's 64-row table, Ertuğrul Özer,
Asterios Panoras, James Barlow, Leo Tang, Hayato Hikawa's C8 milestone, boristown's merge
patches, Lera/marculera and the c44 chemistry lineage, and Google Quantum AI / Qualtran for
`kickmix` and the official verifiers.
