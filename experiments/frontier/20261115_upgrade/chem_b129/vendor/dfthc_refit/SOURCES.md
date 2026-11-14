# Upstream source, version and licence of everything under `vendor/dfthc_refit/`

All files in `vendor/dfthc_refit/` are third-party code, copied verbatim except for the one
documented excerpt noted below. They are **not** our work.

| Field | Value |
|---|---|
| Dataset | [`marculera/dfthc-compact-pipeline`](https://www.kaggle.com/datasets/marculera/dfthc-compact-pipeline) version **7** |
| Directory | `dfthc_refit/` inside that dataset |
| Dataset last updated | 2026-11-03T11:44:36Z |
| Upstream `VERSION` | `704091bf1e1325b090202343e4d8130ff1c80b64` (see `vendor/dfthc_refit/VERSION`) |
| Licence | **Apache-2.0** (`vendor/dfthc_refit/LICENSE`, `vendor/dfthc_refit/NOTICE`) |
| Author | Lera / `marculera` on Kaggle |
| Cited as | `dfthc_refit 1.1.0/1.2.0/1.5.0/1.6.0-dev` in `manwithacat/vqcc-hedge-wizardry` HW-15..HW-24 |
| Method lineage (per upstream docstrings) | `ahmedberatozer/quantum-ai-df-thc-group-compression` (Apache-2.0): `chemistry_refine.py` `sparsify_columns` / `optimize_effective_norm`; kozykappa (sparse rotations); anazemcev (effective norm); phucthaiv02 (the "spend the error budget on lambda_eff" idea); michaelrustad (L-BFGS quantization); SomeJoint/Agniv Banerjee (Reed-Muller coded low bit) |

SHA-256 of the vendored files (as shipped in dataset v7):

```
LICENSE           (Apache-2.0 text, unchanged)
NOTICE            (upstream NOTICE, unchanged)
paths.py          verbatim
encode.py         verbatim
onebody.py        verbatim
onebody_quant.py  verbatim
refine.py         verbatim
refit_weights.py  verbatim
quantize.py       EXCERPT -- see below
UPSTREAM_README.md  upstream dfthc_refit/README.md, verbatim
VERSION           verbatim
```

Run `shasum -a 256 vendor/dfthc_refit/*` to record them; they were verified against the
byte counts published in the dataset listing when this directory was created.

## The one modification: `quantize.py`

`onebody_quant.py` (verbatim) does `from quantize import decode` inside `quantize_coded()`, and the
upstream `quantize.py` imports `optax` and the starter kit's `dfthc` package at module level. The
vendored `quantize.py` is therefore an **excerpt containing only `levels()` and `decode()`, copied
verbatim**, with a short header saying so. No behaviour is changed; the Adam/optax/L-BFGS rounding
stages of `quantize.py` are not used by this experiment (we never round two-body words — they are
the shipped 8-bit words).

## Why this package

`refit_weights.py` is the constrained weight refit the public 4,033-family refits used: it minimises
`log lambda_eff` over `(w, W)` with **exact numpy gradients** for `error_2`, `E_gap` and `Lambda`,
under quadratic penalties for `error_2 > target` and `E_gap < floor`, then polishes with the exact
column-gauge moves of `refine.py`. `refine.py` supplies `Problem`, `optimize_offsets`,
`rotate_columns`, `assemble` and `official` (the last one calls the unmodified official
`dfthcsos.verify.evaluate_words`).

Nothing in this directory optimises the Givens words, the tree, `brot`, `J` or the shape: the
experiment only refits `w (R,B,C)` and `W (R,C)` at fixed words, and reads everything back through
the official verifier functions.

## What was inspected and not used

| Source | Finding |
|---|---|
| `prvsiyan/verifier-guided-quantum-circuit-optimization` (kernel, pulled 2026-11-15) | A **verification** notebook: it attaches `submission.zip` outputs, rebuilds the archive deterministically and reruns the three official verifiers. It contains **no refit code**. Its dataset `prvsiyan/vqcc-verified-best-of-circuits-1106a` holds circuits + `MANIFEST.json` only. |
| `asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit` v4 (kernel) | Ships the refit **result** as an lzma+base64 blob (`REFIT_B64`) and says the refit code is Apache-2.0 from `prvsiyan`'s line, "ported to numpy with a full-Newton restoration". No optimiser source is embedded in the notebook, and the upstream it points at (prvsiyan) has none either, so there is nothing to copy from this pair. |
| `junmiaotiao/qcc-frontier-20261114f` | Not a notebook: it is a **dataset** (`qcc-frontier-20261114b pinned portfolio (G)`, 15.1 MB, 2026-11-14 15:0xZ) holding a pinned portfolio's circuit bytes. No refit code. |
| `marculera/dfthc-refit` (dataset `dfthc-compact-pipeline`) | **Used.** Full Apache-2.0 `dfthc_refit/` package with the constrained refit, its own LICENSE and NOTICE, and a pinned `VERSION`. |

## Attribution to keep in any derived release

Apache-2.0 requires keeping `LICENSE` and `NOTICE` and stating changes. If a candidate produced with
this code is ever packaged, credit `marculera` (dfthc_refit), `ahmedberatozer` (group-compression
refiner), `phucthaiv02`, `michaelrustad`, `kozykappa`, `anazemcev`, and — for the table and words —
`maoxin123`, `ozertuu`, `prvsiyan`, `syed3000`, `marculera`, `ahmedberatozer`, `atakanaldemir`.
