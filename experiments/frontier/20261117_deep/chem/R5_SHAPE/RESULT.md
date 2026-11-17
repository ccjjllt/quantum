# R=5 / R=4 shape mission — NO-GO: the gate is not reachable at B=143

Date: 2026-11-18 (session started 2026-11-17). Chemistry (`dfthcsos`) only.
Branch: `main` worktree (research records and candidates only; nothing pushed,
nothing submitted).

## 0. Verdict

**No cost-positive shape reached `error_2 <= 20 mHa`, continuous or quantized.**
The best continuous 5-group fits are **135.2 mHa** `(5,136,96)` and **136.8 mHa**
`(5,143,88)`, i.e. 6.5–6.8× the gate. A full-span (C=B) optimal-w pass with the
same U changes this only to 131.3–132.9 mHa, so the limitation is the five
143-vector group subspaces, not the number of columns.

The only shape that clears continuous 20 is `(8,143,88)` at **13.77 mHa**, but
(a) its rows are 1220, so its official cost is **366.3 M**, worse than the
shipped 294.64 M, and (b) 8-bit Givens quantization of that continuous fit
raises the official `error_2` to **80.55 mHa**. It is not a candidate.

All numbers below are measured locally on CPU with the competition's own
`scoreinfra` code on the packaged FCIDUMP (SHA-256 checked). The official metrics
path is validated against the shipped `submission.npz`: it reproduces
`error_1 = 0.019999999968`, `error_2 = 0.019999999958`,
`Lambda = 283.144210794`, `E_gap = 3.914898000`, `lambda_eff = 46.921583337`.
No Kaggle kernel was run; no submission was made.

## 1. Method

Three independent fitting routes at fixed `(R,B,C)`:

1. **Lera-style seed** (`seed_numpy.py`, port of `dfthc_refit/df_init.py`):
   pivoted-Cholesky leaves of the shifted packed target, balanced k-means over
   the leaf profiles, simultaneous OMP for the B bases, least-squares w.
   Seeds: (5,143,88) 651.5, (5,136,96) 832.6, (6,136,72) 620.0,
   (4,143,128) 721.5, (7,143,63) 398.3, (7,136,63) 430.2 mHa.
2. **Shipped-warm-start** (`init_span.py`): the 352 shipped columns plus the top
   residual SVD directions to K=R·C, grouped by leading-orbital k-means, basis
   selected from the 1144 shipped U vectors, greedy in-span matched filter.
   Initial errors 12.9–14.9 Ha; descended to ~1 Ha after two rounds.
3. **Long alternating L-BFGS** (`fit_ckpt.py`): 300 w iterations + 250 U
   iterations per round, one checkpoint per round; every result below is
   re-evaluated in the full 2926-dimensional space (`Problem.e2_full`).

Plus structural measurements: exact pair-merge truncation, fresh 143-vector fits
to pair unions, 5/6/7/8-subset of the eight shipped groups, and Cholesky-cluster
fits at B=143/160/200.

## 2. Continuous `error_2` at the target shapes

All values are mHa, exact full-space objective `||Y Y^T - H||_F`.

| shape | K | rows | floor(K) | Lera seed | best continuous | full-span w (C=B, fixed U) |
|---|---:|---:|---:|---:|---:|---:|
| **(5,143,88)** | 440 | 791 | 2.577 | 651.5 | **136.76** (4 rounds) | 131.26 |
| **(5,136,96)** | 480 | 756 | 1.630 | 832.6 | **135.20** (shipped warm start, 2 extra rounds) | 132.88 |
| **(4,143,128)** | 512 | 648 | 1.140 | 721.5 | **176.76** (3 rounds) | — |
| (6,136,72) | 432 | 892 | 2.828 | 620.0 | **127.69** (4 rounds) | — |
| (7,143,63) | 441 | 1077 | 2.539 | 398.3 | not run to plateau | — |
| (8,143,88) | 704 | 1220 | 0.338 | — | **13.77** (grow from shipped) | — |
| (8,143,55) | 440 | 1220 | 2.577 | — | 18.05 (on-grid, fixed shipped U) | — |
| shipped (8,143,44) | 352 | 1220 | 7.361 | — | 16.55 continuous, **20.00 official** | — |

The R=5 fits were still descending ~3–10% per round when stopped; the long-run
trend and the full-span result bound the reachable region at ~130 mHa, not 20.
The 5-group optimiser never went below 135; the 4-group fit never below 176.

## 3. The structural barrier: one 143-vector group cannot host two channels

The shipped solution is eight 143-vector groups, each with 44 columns. A 5-group
shape with 88 columns/group has to merge the eight channels. Measured losses:

| operation | measured loss / error |
|---|---:|
| rank-88 truncation of a pair of 88-column groups `(8,143,88)` | **156.3–180.2 mHa** |
| rank-96 truncation of a pair of 96-column groups `(8,136,96)` | **184.5 mHa** |
| rank-44 truncation of a pair of 44-column groups `(8,143,44)` | **668.4–875.2 mHa** |
| fresh B=143 fit to the union of two 44-column groups (88 columns) | **224.6–255.5 mHa** (CP-ALS, pool/random) |
| top-44 eigenvectors of H, one group B=143 | **462–689 mHa** column error |
| 88 Cholesky leaves, one group B=143 | **215–240 mHa** |
| same 88 leaves, B=160 / B=200 | **154.4 / 90.9 mHa** |
| best 5 of the 8 shipped groups, 88 columns each, on-grid U | **823.0 mHa** |
| best 6 of the 8 shipped groups, 72 columns each | **581.7 mHa** |
| best 7 of the 8 shipped groups, 63 columns each | **402.0 mHa** |
| all 8 shipped groups, 55 columns each, on-grid U | **18.05 mHa** |

The merge trajectory from `(8,136,96)` is a concrete stage record:

```
start (8,136,96)                    17.46 mHa
pair (4,7) rank-96 truncation loss 184.52 mHa
merged init (7,136,96)            1519.19 mHa
after GN(1) on merged group        744.99 mHa
after GN(2) on merged group        498.74 mHa
```

Interpretation: the eight groups are nearly orthogonal channels (group Gram
correlations 0.00–0.17) and each 143-vector span is tailored to its own 44/88
columns. A 143-vector span does not contain the union of two channels to better
than ~200 mHa; five spans therefore cover at most five of the eight channels.
Dropping the other three costs 6.2 Ha (the best 5-subset of the `(8,143,88)`
fit has error 6184 mHa; the best 5-subset of the shipped 44-column groups with
88 columns each is 823 mHa).

## 4. Three further gates that a continuous `error_2` does not capture

### 4.1 8-bit quantization is not a small perturbation

The shipped `U` **is** the decoded 8-bit word set. The official `error_2 = 20.00`
is the error of that discrete factorization, not a continuous fit plus noise.
For a continuous fit that is not already on the grid, rounding is catastrophic:

| object | continuous | nearest 8-bit grid | after w refit |
|---|---:|---:|---:|
| (8,143,88) | 13.77 | **80.55** | 70.11 |
| shipped U + 0.001 Gaussian noise per row | 20.00 | — | 85.72 |
| shipped U + 0.004 noise | 20.00 | — | 337.9 |

So a continuous fit must be at the grid points, or the candidate must be
optimized directly on the discrete words. The Lera `quantize.py` does this with
staged rounding + Adam/LBFGS; it is not in this repository. Our continuous R=5
fits at ~135 mHa are far outside the region where any rounding could help.

### 4.2 The one-body `W` (H2_I) couples to the new X basis

`W` is not free once the two-body X basis changes. Reproducing the shipped
`h1_prime` by least squares `A W = vec(base - h1_prime)` gives:

- shipped (8,143,44): residual 1.7e-13, `Lambda 283.144`, `E_gap 3.914898`,
  `lambda_eff 46.9216` — exact.
- (8,143,88): residual 0.025, `Lambda 293.05`, `E_gap 4.093`, `lambda_eff 48.81`
  (still feasible; this is the only new shape whose W behaves).
- (5,136,96): the least-squares W is huge; `Lambda 725`, `lambda_eff 78.4`.
- (5,143,88) / Lera seeds: worse (10^3–10^6).

The on-grid `(8,143,55)` result is the sharpest illustration: its official
`error_2` is **18.05 mHa** (passes accuracy) but `Lambda = 501.0`,
`lambda_eff = 63.90`, and its modelled cost is **313.8 M** (worse than shipped).
The extra columns move the X span and force a large W.

### 4.3 `error_1` is a third gate, also 8-bit

The verifier also requires `error_1 <= 20 mHa` after decoding the 76 one-body
rows. New shapes do not automatically pass it:

- `(8,143,88)` npz, newly encoded eigenvectors of the new `h1_prime`:
  `error_1 = 52.13 mHa` (FAIL); using the shipped one-body words instead:
  308.3 mHa.
- `(8,143,55)` npz, own one-body words: 50.19 mHa (FAIL); **shipped one-body
  words: 20.95 mHa** (just over; the W residual 0.0145 causes the 0.95 mHa
  excess). With a smaller ridge `lambda=1e-6` (h1_prime residual 0.0023) the
  shipped one-body words give **20.117 mHa** — still 0.117 mHa over. The
  shipped words already sit at 20.00 mHa, so any nonzero h1_prime mismatch
  pushes the new shape over the gate.

The shipped one-body words are exact eigenvectors of the shipped `h1_prime`;
reusing them works only when the new `W` reproduces that `h1_prime` almost
exactly. This is another coupling between the two-body basis and the one-body
encoding.

## 5. Official costs at the final `(R,B,C)`

`T_h` and `Q` are the exact `SpinFreeData_V1` values (N=76, chi=10, beta=8),
with the verifier's shared-workspace formula and `J=5, brot=8`
(`angles_temp = 77`, selection = `ceil(log2(rows))`). `T_total` uses the **modelled**
loader density `2·4025·rows/1220`; no 791/756/648-row loader has been emitted,
so the loader leg is not measured.

| shape | rows | **T_h** | **Q** | T_total (model) | cost (M) | vs shipped 294.643 M |
|---|---:|---:|---:|---:|---:|---:|
| shipped (8,143,44) | 1220 | 6662 | 427 | 14,712 | 294.76 (measured 294.64) | 1.000 |
| **(5,143,88)** | 791 | **7539** | **429** | 12,758 | **256.82** | **0.872** |
| **(5,136,96)** | 756 | **7916** | **430** | 12,904 | **260.36** | **0.884** |
| **(4,143,128)** | 648 | **8243** | **429** | 12,519 | **251.99** | **0.855** |
| (6,136,72) | 892 | 7433 | 427 | 13,319 | 266.85 | 0.906 |
| (7,143,63) | 1077 | 7550 | 429 | 14,656 | 295.03 | 1.001 |
| (8,143,88) | 1220 | 10104 | 430 | 18,154 | 366.28 | 1.243 |
| (8,143,55) | 1220 | 7539 | 429 | 15,589 | 313.80 | 1.065 |

The prize shapes are indeed ~13–15% cheaper **if** they were legal; they are not.

## 5b. Diagnostic artifacts (not candidates)

Two complete npz files were built to exercise the full key set and the official
metrics path. **Neither is shippable**; they are kept only as evidence.

| file | shape | error_1 | error_2 | Lambda | E_gap | lambda_eff | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| `artifacts/20261117_lambda_measure/diag_8_143_88.npz` | (8,143,88), rows 1220 | 0.05213 | 0.08055 | 293.24 | 4.4551 | 50.921 | FAIL error_2 |
| `artifacts/20261117_lambda_measure/diag_8_143_55.npz` | (8,143,55), rows 1220 | 0.05019 | 0.01805 | 501.02 | 4.0917 | 63.900 | FAIL error_1; cost 313.8 M |
| `artifacts/20261117_lambda_measure/diag_8_143_55.npz` + shipped one-body words | (8,143,55) | 0.02095 | 0.01805 | 501.02 | 4.0917 | 63.900 | FAIL error_1 by 0.95 mHa |

SHA-256:

```
aca87a19f464539625c789bcca05c5971a4287e06681685d8da5611f23bd9804  diag_8_143_88.npz
7fee17facbbe96d6d1f6c31be95bf2d54b241d0ba182b22820ba94c6b6e61211  diag_8_143_55.npz
```

Keys and shapes (verified):

```
U (8,143,76)  W (8,143,88/55)  H2_I (8,88/55)  H1_I ()
Hsym_lower (2926,)  tree_edges (75,2)  angle_words (1220,75)
```

The `angle_words` were produced by the inverse Givens-tree encoder
(`encode_test.py` / `build_candidate.py`): start from the target unit vector,
walk the 75 tree edges in reverse, set `theta_t = atan2(v_child, v_parent)`,
store `round(theta_t/pi * 128) mod 256`, and set the parent to
`hypot(v_parent, v_child)`, child to zero. Decoding with the verifier's forward
rotation reproduces each row to `<1.1e-15` before quantization; after 8-bit
quantization the per-row norm is 1.0 (min 0.9999999999999997, max 1.0000000000000002)
and the overlap with the target row is 0.999759–0.999990 (mean 0.9999902).
The shipped words decoded with the verifier's forward rotation reproduce the
shipped U to overlap 0.9999999999999998–1.0000000000000004 (the 2.0 max-norm
difference is only the per-row global sign gauge); our encoder's round-trip on
one row is 2.1e-16 before quantization and 0.018–0.022 vector error after 8-bit
quantization for random unit vectors.

## 6. What was not run

- No Kaggle kernel: no shape produced a candidate that could pass the gate, so
  there was nothing to verify on Kaggle CPU.
- No official `dfthcsos/verify.py` circuit run (needs 15 `.kmb` loaders). The
  official **metrics** function (`evaluate_dfthc_angle_words`) was run on the
  shipped words and on the `(8,143,88)` quantized words; the shipped result
  matches the known 20.00 mHa / 46.9216 λ.
- No submission, no Kaggle push, no git push.

## 7. Reproduction

Scripts in this directory (copied from the session, paths/ROOT adjusted):

- `seed_numpy.py` — Lera-style seed at any `(R,B,C)`.
- `seed_to_x.py` — seed npz → `x` checkpoint.
- `fit_ckpt.py` — checkpointed alternating L-BFGS fit.
- `block_w.py` — exact in-span rank-C w update (generalized eigendecomposition).
- `cpals.py` — symmetric CP-ALS for a single group.
- `encode_test.py` — Givens encode/decode and shipped-word check.
- `build_candidate.py` — full `submission.npz` builder (ridge W, 8-bit words,
  official metrics). Validated on the shipped and the `(8,143,55)` on-grid fit.

Run from `experiments/frontier/20261117_deep/chem/LAMBDA_MEASURE/` (the scripts
import `fitlib.py` / `infra.py` from that directory; `seed_numpy.py` has ROOT
hard-coded to this checkout). Example:

```sh
P=/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python
$P ../R5_SHAPE/seed_numpy.py \
   /Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261117_lambda_measure/seeds/seed_5_143_88.npz \
   5 143 88
$P ../R5_SHAPE/seed_to_x.py .../seeds/seed_5_143_88.npz .../seeds/seedx_5_143_88.npz
$P ../R5_SHAPE/fit_ckpt.py 5 143 88 load:.../seedx_5_143_88.npz 40 300 250
```

Key artifacts (in `artifacts/20261117_lambda_measure/`):

```
seeds/seed_5_143_88.npz        651.5 mHa seed
seeds/seed_5_136_96.npz        832.6 mHa seed
seeds/seed_6_136_72.npz        620.0 mHa seed
seeds/seed_4_143_128.npz       721.5 mHa seed
ck_5_143_88_load.npz           136.76 mHa continuous
ck_5_136_96_loadbestc.npz      135.20 mHa continuous
ck_6_136_72_load.npz           127.69 mHa continuous
ck_4_143_128_load.npz          176.76 mHa continuous
fit_8_143_88.npz                13.77 mHa continuous (cost 366 M; quantizes to 80.55)
artifacts/20261117_lambda_measure/fit_8_143_55_ongrid.npz    18.05 mHa on-grid (Lambda 501, cost 314 M)
```

## 8. Recommendation

The `B`-governed law is confirmed **at fixed R=8** but is not sufficient to
reduce R. The channel count is the binding resource: the eight 143-vector
spans are independent, and a 143-vector span cannot absorb a second channel
without ~200 mHa. A cost-positive R<8 shape would need either

1. a genuinely new seed whose 5 (or 4) subspaces are trained jointly from
   scratch on the discrete words (not a merge of the shipped channels), with
   `C` near the full span, or
2. a larger `B` (the 88-column cluster needs B≈200 for 91 mHa; B≈300+ for 20),
   which makes `rows = 76 + R·B` more expensive than the shipped shape.

Neither is reachable with the current CPU budget or the current binary
`error_2` gate. The loader-cut axis and the DQI/invsqrt axes remain closed as
recorded in `SUMMARY2.md`; this result closes the R=5/R=4 shape axis as well.
