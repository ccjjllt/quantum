# `chem_b129` — Stage A: can `B = 143 → 129` pass the 8-bit gate?

Self-contained, CPU-only screen for the one chemistry lever with a ≥1% GM payoff
([`../chem_plan.md`](../chem_plan.md) §4–5): keep the shipped (8,143,44) 8-bit coded-word table,
drop 14 of the 143 basis vectors per group, refit **only the weights** `W (R,B,C)` and `H2_I (R,C)`
at fixed words / `U` / tree, and read the official metrics back.

`B` is the only free knob in the cost model because `b2 = ceil(log2 B) + 11 = 19` and
`ceil((B+1)/16) = 9` are constant for `B ∈ [129,143]`: `Q` stays 427, the inner PREPARE moves
4,095 → 4,067, and the ANGLE address count falls 1,144 → 1,032 (loader 4,033 → ≈3,756/pass). The
whole question is whether the accuracy gates survive.

---

## Result of the first run (2026-11-15, this machine)

| B | C | rows | e1 (mHa) | e2 (mHa) | Λ | E_gap | λeff | T | Q | gate |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| **143** | 44 | 1,220 | 16.21 | **19.99997** | 282.970 | 3.9149074 | **46.9070** | 14,728 | 427 | **PASS** (control) |
| 139 | 44 | 1,188 | 24.08 | 65.03 (→ **64.31** at 2,500 it) | 317.7 | 4.366 | 52.49 | 14,558 | 427 | FAIL e2 |
| 129 | 44 | 1,108 | 26.02 | 138.07 | 369.5 | 5.604 | 64.10 | 14,142 | 427 | FAIL e2 |
| 139 | 48 | 1,188 | 23.55 | 65.02 | 318.0 | 4.376 | 52.57 | 14,692 | 427 | FAIL e2 |
| 129 | 48 | 1,108 | 25.67 | 138.12 | 369.4 | 5.593 | 64.03 | 14,580 | 427 | FAIL e2 |

- **The control reproduces the shipped point exactly**: e2 = 19.999968 mHa, Λ = 282.9696,
  λeff = 46.90701, E_gap = 3.914898004 before the offset solve (and 3.914907 after it). Cost
  294.93 M vs the shipped 294.99 M — the −0.02% is the loader model's 4,031 vs the measured 4,033,
  not a real gain.
- **`B < 143` fails by 3.3× (B=139) to 6.9× (B=129) the gate, and `C` does not help**: C=48 is
  identical to C=44 to three digits. So the blocker is the *missing basis rows*, not the copy rank:
  re-weighting the kept rows cannot rebuild the dropped directions.
- The plateau is reached early: B=139 goes 118 → 67.6 (200 it) → 65.0 (600) → 64.31 (2,500). More
  iterations buy ~1 mHa, not 44.
- **Conclusion for the plan: the cheap form of the `B → 129` lever is closed.** Opening `B < 143`
  needs a full refit of `U` (new continuous vectors, re-rounded → a new word table → 15 new
  loaders), not a weight refit at fixed words. That is the "new factorization" research programme,
  not a Stage A screen.

Bonus observation (free, no score change): the shipped one-body rows are **not** polished — aligning
them to the eigenbasis and running `onebody.polish` takes `error_1` from 19.9976 to **16.21 mHa** at
zero cost in `T`, `Q` or λeff.

---

## Files

```
stage_a.py                     the whole screen (Kaggle script kernel or local CLI)
vendor/dfthc_refit/
    LICENSE  NOTICE            Apache-2.0, unchanged, from the upstream dataset
    VERSION                    704091bf1e1325b090202343e4d8130ff1c80b64
    SOURCES.md                 provenance, hashes, what was inspected and rejected
    UPSTREAM_README.md         upstream dfthc_refit/README.md, verbatim
    paths.py  encode.py  onebody.py  onebody_quant.py  refine.py  refit_weights.py   verbatim
    quantize.py                EXCERPT: `levels()` + `decode()` only (see SOURCES.md)
```

## Attribution and licence

The refit is **not our code**. It is `dfthc_refit` from
[`marculera/dfthc-compact-pipeline`](https://www.kaggle.com/datasets/marculera/dfthc-compact-pipeline)
version 7 (2026-11-03), directory `dfthc_refit/`, pinned by its own `VERSION`
`704091bf1e1325b090202343e4d8130ff1c80b64`, **Apache-2.0** (`vendor/dfthc_refit/LICENSE` and
`NOTICE` are shipped unchanged). Method lineage credited by upstream: `ahmedberatozer`
(group-compression refiner), `phucthaiv02` (spend the error budget on λeff), `michaelrustad`,
`kozykappa`, `anazemcev`, SomeJoint/Agniv Banerjee (Reed–Muller coded low bit).

The table and words are `maoxin123`'s (CC0), on the table line of `ozertuu` and `prvsiyan` with
`syed3000`/`marculera`/`ahmedberatozer`/`atakanaldemir` loaders. The verifiers are Google Quantum AI's,
used unmodified.

Checked and not usable: `prvsiyan/verifier-guided-quantum-circuit-optimization` is a *verification*
notebook with no refit code; `asteriospanoras/qcc-27-307-frontier-finer-chemistry-refit` embeds only
the refit *result* (base64) and points back at prvsiyan; `junmiaotiao/qcc-frontier-20261114f` is a
dataset of pinned circuit bytes, not a notebook. Details in `vendor/dfthc_refit/SOURCES.md`.

## What runs unmodified

- `dfthcsos.verify.load_inputs`, `evaluate_words`, `heuristic_costs` — the official verifier, straight
  from the competition data (`DFTHC_DATA/verifiers`, or `/kaggle/input/...`).
- `refit_weights.error_terms`, `refit_weights.WeightProblem` (exact `error_2`/`E_gap`/`Lambda`
  gradients), `refine.Problem`, `refine.optimize_offsets`, `refine.rotate_columns`, `refine.official`.
- The objective, its two quadratic penalties, the per-block rescaling and the L-BFGS-B settings are
  copied line-for-line from `refit_weights.refit()`.

## The three deliberate differences

1. **The acceptance wrapper is opened up.** Upstream `refit()` returns the *input* when the refit
   misses the gates, which is exactly the case this screen must measure. `refit_w_W()` keeps
   upstream's objective/optimiser and returns the achieved state plus an L-BFGS trace.
2. **One-body rows: no JAX.** `refine.assemble` calls `onebody.refresh`, which imports the JAX module
   `onebody_quant`. The screen uses the same two numpy candidates `refresh` already offers
   (rounded eigenvectors of h1′, and the caller's rows) polished with `onebody.polish`, and drops the
   JAX progressive-rounding candidate plus the random kicks. `error_2/Λ/E_gap/λeff` do not depend on
   the one-body rows; only `error_1` does. `--final` runs the untouched upstream path for finalists.
3. **One-body rows are aligned to the eigenbasis first.** The verifier pairs each submitted one-body
   row with an eigenvector of h1′ by an optimal |overlap| assignment
   (`reconstruct_h1_thc` → `linear_sum_assignment`), so row order is free for it — but
   `onebody.polish`/`onebody.error` assume row *j* is the *j*-th ascending eigenvector. The shipped
   4,033 rows are in a different order, and polishing them unaligned silently optimises the wrong
   pairing (`onebody.error` reads 2,324 mHa instead of 19.998). `_align_rows()` applies the same
   assignment the verifier will. Without this the table shows a fake `error_1 ≈ 25 mHa` and the
   e1 column is meaningless.

## Inputs, pinned

| Item | Value |
|---|---|
| Source | `maoxin123/qcc-chemistry-4033-toffoli-loaders` **v1**, CC0, 2026-11-14T13:02:23Z, 7,375,711 B |
| `submission.npz` SHA-256 | `3f864a7aeaa4d78984c8822761782b63be2d553b229f487e79640a73be147c44` |
| Official submission digest | `598adb7bcde2502bb35cfacb078d02a2bd2abba549595b30129e4ee56aecb3cf` |
| Competition data | `verifiers/dfthcsos/` incl. `FeMoCo76o113e.fcidump` (`e5a48af7…e1bd`) and `FeMoCo76o113e.fixed_shifts.npz` |
| Geometry | `R=8`, `brot=8`, `J=5`, `tree_edges` unchanged |

The script refuses to run if the SHA-256 does not match.

## Run instructions

### Kaggle (script kernel, CPU, internet only for the signed URL)

1. *Add Input* → **Competition data**: `Google Quantum AI - Verifiable Quantum Circuit Compilation`.
2. *Add Input* → **Your Datasets**: `maoxin123/qcc-chemistry-4033-toffoli-loaders`.
3. Create a **Script** kernel, CPU, no GPU, no accelerator. Paste `stage_a.py` as the only file.
4. One of:
   - `!python stage_a.py --submission-path /kaggle/input/qcc-chemistry-4033-toffoli-loaders/submission.npz`
   - get a signed URL for the same file and `!python stage_a.py --submission-url "$URL"`
     (or set the `CHEM4033_URL` environment variable), or
   - in Python: `import os; os.environ["CHEM4033_URL"] = URL` then run the script.
5. `DFTHC_DATA` is auto-detected from `/kaggle/input`; nothing else to configure.
6. Outputs: the table on stdout plus `stage_a_results.json` next to the script.

### Local

```bash
cd experiments/frontier/20261115_upgrade/chem_b129
export DFTHC_DATA=$PWD/../../../../data/competition      # or let the script default to it
python stage_a.py --submission-path ../../../../artifacts/20261115_chem/chem4033/submission.npz \
                  --dry-run                              # 25 s: inputs + cost model only
python stage_a.py --submission-path .../submission.npz   # full grid
```

Local runs use the PyPI `kickmix` (the repo rule); on Kaggle `paths.py` puts the competition's
`kickmix/` on the path. Only `numpy`, `scipy` and the competition verifiers are needed; `jax` is
needed only for `--final`.

### Knobs

```
--b-list 143,139,135,131,129     --c-list 44,46,48
--target 19.99                   error_2 target in mHa (gate 20.0; λeff is smallest at the
                                 largest allowed error, so the public refits sit at 19.999)
--margin 1e-5                    Ha above the E_gap floor.  The floor is strict; the offset solve
                                 lands ~3e-7 Ha low, so 1e-5 Ha (1.3e-6 of λeff) is the smallest
                                 safe cushion.  1.5e-9 as in the plan is not holdable.
--maxiter 6000                   L-BFGS iterations per point
--rounds 1                       refine.py gauge+offset rounds (upstream default 3; 1 screens fine)
--gauge-hops 10                  basin hopping inside refine.rotate_columns (0 is faster)
--final / --dry-run / --no-early-stop / --max-minutes / --json-out
--drop-metric l2|l1|max          how the B kept rows per group are chosen (default l2 on W)
```

## Runtime

Measured here (Apple CPU, one core) and estimated for a Kaggle CPU box (4 cores, no vector units):

| Stage | Here | Kaggle CPU |
|---|---|---|
| `encode.decode` of 1,220 rows | 4 s | 5–10 s |
| `error_terms` (K, Q, T²; one 5,776² × 1,144 matmul) | 0.3 s | 5–20 s |
| one L-BFGS iteration (f + grad + `eigh`) | 40 ms | 60–150 ms |
| one `assemble` (two one-body polishes) + gauge round | 10 s | 20–40 s |
| **per grid point** | **25 s + 40 ms·maxiter** | **45 s + 0.1 s·maxiter** |

So: ~0.5 min for a point that converges (B=143 needs 15 L-BFGS iterations), ~10.5 min for one that
runs to 6,000 iterations. With the early stop the full 15-point grid costs about **30–45 min** on Kaggle CPU
(it stops at the first `e2 > 20.5 mHa` per `C`); with `--no-early-stop` budget **1–2.5 h**. The
measured validation runs were 30 s (control, `--rounds 1 --gauge-hops 10`) and 1 min 43 s (4 points at
`--maxiter 600`).

`--max-minutes` is a wall-clock guard; the run stops cleanly and still writes what it has.

## The gate

Per grid point, PASS requires **all** of (official `evaluate_words`):

```
error_1 <= 0.020 Ha     error_2 <= 0.020 Ha     E_gap > 3.914898 Ha     Lambda > 49.0
```

and the cost must also clear the decision threshold: `cost <= 288.8 M` ⇔ GM ≥ 27.50
(`BASE_COST` = 294,991,455.82). The script prints `gate` = `PASS` or `FAIL:<gate names>`, plus
`pass_decisive` (the same test without `e1`) because `e1` is the only column affected by the
no-JAX one-body substitution.

`e2 > 20.5 mHa` prints a `FLAG` and stops the `B` descent for that `C` (smaller `B` can only be
worse); `--no-early-stop` overrides.

The trailing verdict is one of
`PASS at (B,C) …` (Stage B is worth running), `PARTIAL` (`e2` clears but the numpy one-body step did
not — rerun with `--final`), or `FAIL` (no point clears the decisive gates).

## Known limits (read before quoting a number)

- **The loader term is a model, not a measurement.** `L/pass = 15·(80 + d·R·B)`,
  `d = 0.16509 = (4033/15 − 80)/1144`, anchored on the measured 4,033/pass, with
  `d = 0.1686` from Lera's (9,143,40) family as the pessimistic bound (second cost column). No ANGLE
  circuit is built here — Stage B does that.
- **`Q` is exact for the geometry** but assumes the ANGLE circuits still fill the 128-qubit cap, as
  the shipped `k0` does (`angles_temp = 128 − 11 − 40 = 77`). `Q = per + 40 + max(303, 77) = 427`
  either way, so this assumption cannot move the answer.
- **Truncation choice.** `--drop-metric l2` drops the 4 smallest `W` columns per group. That is not
  the optimal 4-subset; a greedy set search (566 refits) might shave a few mHa. It cannot close a
  3.3× gap, but it is the honest caveat.
- **`error_1` here is the no-JAX construction** (≤26 mHa on the failing points, 16.2 on the control).
  It is not what decides any row.
- **Not run here:** no official 78,080-shot verifier run, no loaders, no `--final` (no jax on this
  machine), no submission. The numbers above are `evaluate_words` + the official cost model.
