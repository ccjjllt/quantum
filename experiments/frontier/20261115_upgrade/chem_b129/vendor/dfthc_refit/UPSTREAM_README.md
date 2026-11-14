# dfthc-refit: cheaper dfthcsos block encodings by merging DF-THC groups

A pipeline for the chemistry benchmark (`dfthcsos`, FeMoCo 76 orbitals) of the Google Verifiable
Quantum Circuit Compilation competition: train a DF-THC factorization, round its Givens angles to
10 or 8 bits, refine the identity offsets, refit the weights, build the ANGLE circuits and score
them with the official verifier. One recipe file describes a whole run.

**Best verified: 9 × 143 × 43 at 8 bits, 10.03× the reference, from our own weights** (2026-10-30,
`runs/r10/finish_c43`, four random salts of the official metric): a seed built directly at the scoring
shape from pivoted-Cholesky leaves of the shifted Hamiltonian, clustered by orbital profile
(`experiments/compact_seed.py`), six 60k-iteration float64 L-BFGS refits (12.79 mHa), one million Adam
steps at the shape (`experiments/adam_train.py`: 12.38), rows dealt by strength over the 16-address
blocks (`experiments/deal_rows.py`), rounded to 8 bits with a coded bit 0 on batches 3-14
(`quantize.py --coded 3-14`: 19.55), refined, refit with an augmented Lagrangian that spends the error
budget (`experiments/refit_al.py`) and built: 1,287 rows, 16,534 Toffolis (9,528 in the angle circuits),
428 qubits, λ_eff 47.27, error_2 19.56 mHa, error_1 10.21. No public weights enter this build; the same
recipe at (9, 143, 46) gives 9.89× (`runs/r10/finish_cat9c`).

**From the public seed: 9 × 143 × 46 at 8 bits, 9.47×**: the public (26, 60, 30) factorization
merged in threes to (9, 180, 90), shrunk by fading vectors and copies with long float64 L-BFGS refits
(`experiments/shrink.py`, `fastfit.py`), refit at the final shape with κ = 2e-5 (12.81 mHa), rounded
to 8 bits with L-BFGS stages until half the angles are frozen (`quantize.py --lbfgs-until 0.5
--lbfgs-iters 20000`: 19.83 mHa) and finished with `recipes/finish_merged_b8.toml`: 1,363 rows,
17,479 Toffolis, 428 qubits, λ_eff 47.35, error_2 19.96 mHa. The (24, 60, 30) factorization the same
way, with the recipe's rounding, gives 8 × 156 × 60 at 8.96× (1,324 rows, 18,416 Toffolis, 430 qubits,
λ_eff 47.28, error_2 17.79 mHa). At 10 bits: 10 × 120 × 54, 3.97× (1,276 rows, 25,434 Toffolis, 690 qubits, λ_eff 48.17, error_2
19.68 mHa).

- Notebook: [DF-THC: Merge Groups Before Dropping Them](https://www.kaggle.com/code/marculera/df-thc-merge-groups-before-dropping-them)
  (`notebooks/dfthc-merge`) replays the result on a CPU, explaining each step and calling these
  modules.
- Dataset: [dfthc-merge-pipeline](https://www.kaggle.com/datasets/marculera/dfthc-merge-pipeline)
  holds this pipeline as `dfthc_refit/`, the 10-bit factorization files `B10c54.npz` (trained),
  `B10c54_q10s.npz` (rounded) and `B10c54_pol.npz` (polished), and three finished 8-bit builds:
  `B239_b8.npz` (a pruned public (4, 255, 128), not merged, 8.11×), `M8x156x60_b8.npz` (merged in
  threes, 8.96×) and `M9x143x46_b8.npz` (merged in threes, κ 2e-5 refit, longer rounding, 9.47×).

By default the notebook loads the rounding and the polish from the dataset: the polish takes ~3
min on a fast laptop but over an hour on Kaggle's CPU. `POLISH = True` reruns it.

## The idea

The chemistry cost `λ_eff × Toffolis × qubits` is driven by the `76 + R·B` rows the ANGLE circuits
load. Public pipelines shrink `R·B` with many small groups (26 × 60). This one **merges** groups
first: two groups combine exactly into one with twice the vectors and copies (block-diagonal
weights), it retrains so every copy can use all the merged vectors, and only then drops groups.

- At equal rows and equal weights (28 × 60 × 60 against 14 × 120 × 60, three seeds) merged groups
  reach 16.2 mHa at 10 bits against 19.5.
- From the public (26, 60, 30) factorization with the same budget per stage, small groups fail the
  20 mHa gate even at 24 groups (1,516 rows), while merged groups pass at 10 (1,276 rows). Nine
  merged groups fail (17.8 mHa before rounding, 22.1 at 10 bits).

## Status of the claim

Merging is obvious once someone thinks to try it; writing it down does not establish the result.
What had to be tested, and where it stands:

1. **It trains better at the same parameter budget:** yes, at equal rows and equal weights
   (28 × 60 × 60 against 14 × 120 × 60, three seeds: 19.5 against 16.2 mHa at 10 bits).
2. **The gain survives the extra costs** (at equal rows ≈4% more Toffolis, 34 more qubits, ≈2%
   more λ_eff): yes, because merged groups reach 22% fewer rows than the seed.
3. **It rounds and compiles within the verifier's gates:** yes, verified at 3.97× with 10-bit words
   and 9.47× with 8-bit words (merged in threes, (9, 143, 46)).
4. **It persists across independent initializations and other molecules:** yes for initializations,
   since 2026-10-30: a seed built from the Hamiltonian alone, with no public weights, reaches 10.03×
   (the compact-seed bullets under "Findings"); other molecules are untested. How it got there: two controls
   run on 2026-10-29 (A100, `notebooks/colab/make_colab.py` plans `s9` and `m9`) repeat the nine-group
   schedule of the public-seed run `r9` ((9, 180, 90) → (9, 143, 46), float64 L-BFGS, 60k-iteration
   refits, κ 5e-5) from random structures (the starter kit's init, `experiments/random_init.py`):
   `s9` fits a random (9, 180, 90) directly (240k iterations, 19.20 mHa) and shrinks; `m9` fits a
   random (27, 60, 30) (240k iterations, 27.88 mHa), merges it exactly in threes and continues like
   `s9`. Error before rounding, mHa:

   | shape | r9: public (26, 60, 30) merged | m9: own random groups merged | s9: random, no merge |
   |---|---|---|---|
   | (9, 180, 90) after the pre-fit | 8.42 (at (9, 176, 84)) | 16.38 | 19.20 |
   | (9, 176, 84) | 6.40 | 15.88 | 17.20 |
   | (9, 166, 70) | 6.84 | 17.17 | 17.46 |
   | (9, 162, 66) | 7.35 | 17.96 | 17.63 |
   | (9, 156, 60) | 8.63 | 18.6 at (9, 160, 64), stopped | 18.34 |
   | (9, 150, 54) | 10.18 | | 19.72 |
   | (9, 143, 46) | 13.51 | | 20.76 at (9, 149, 52), stopped |

   A third start, our own and not from a public notebook (`experiments/kit_seed.py`, plan `k9`): the
   competition's baseline (65, 60, 60) at 16.13 mHa, two groups dropped and the rest merged exactly
   in sevens to (9, 420, 420), pre-fit 60k iterations to 10.22 mHa, then shrunk geometrically with
   20k-iteration refits: 11.28 at (9, 405, 394), rising a mHa per step at 2.3× the rows of
   (9, 180, 90); stopped there. The baseline's groups are too weakly trained for the shrink to
   reach the public seed's numbers.

   A fourth start, seeded from the Hamiltonian alone (`experiments/df_init.py`, plans `d9`, `d9h`):
   the structure is a sum of squares of one-body operators, so the verifier-weighted two-body
   target eigendecomposes into exact one-body leaves; the R·C largest leaves become the copies
   (round-robin over the groups), each group's bases are picked among its leaves' eigenvectors
   and the weights solved by least squares. No factorization, public or otherwise, goes in. The
   seed fits twelve times lower than a random start at equal iterations (25.4 against 283 mHa
   after 5k on a CPU) and, under r9's recipe, reaches **6.78 mHa at (9, 180, 90)** after the 240k
   pre-fit, level with the merged public seed; it then drifts up ~0.1 mHa per shrink step where
   the public seed drifted down: 6.92 / 8.03 / 8.43 at (9, 176, 84) / (9, 166, 70) / (9, 164, 68)
   against r9's 6.40 / 6.84 / 7.15 (`runs/r10/colab_d9_out`). A longer pre-fit (334k) and refits
   (83k) with an OMP-selected basis changed nothing (6.84, then 7.11 at (9, 176, 84)). So the
   bases of a trained seed are better shared than those of an exact decomposition, and the gap,
   about 1.3 mHa, is what training the small groups buys.

   Reading: the merge transports the seed's training, it is not an optimizer. Fitting the target
   shape directly from a random start stalls at 17-20 mHa, where the merged public seed is 2.7×
   lower at the same shape with less budget: the merged numbers are not reachable by direct fitting.
   Merging our own weak seed starts 2.8 mHa ahead of the random start, but the lead erodes and is
   gone by C ≈ 66. So the gain is real and comes from the seed, and independence from this
   particular seed is still open: a from-scratch seed needs far more training than 240k L-BFGS
   iterations from a unit-normal init (the starter kit's trainer, hours per group). One molecule
   (FeMoCo, 76 orbitals) as before. Logs and checkpoints: `runs/r10/colab_s9_out`, `colab_m9_out`.

Better final solution or faster convergence? The equal-weights runs are 41,000 steps and the
equal-budget runs 150,000 steps per stage. Merged groups stay ahead at the end of those schedules,
but neither shape was trained to full convergence.

Next experiments, before any paper: three independent initializations per shape (different seeds
or factorizations, not jitter), trained to convergence; then the best comparison on another system
from the starter kit (Fe2S2, Fe4S4, FeMoCo-54). The gap-floor finding is secondary: the weight
refit now recovers it (~2% of λ_eff).

Assessment: a small but legitimate contribution, a specific structural choice tested under this
benchmark's constraints, not a new method.

## Quick start

Requirements: Python ≥ 3.11, `numpy`, `scipy`, the competition's `kickmix`, and for training `jax`
and `optax` (a GPU helps: a step takes ~16 ms on a Kaggle T4, ~200 ms on a laptop CPU).

Data: the competition data (the directory with `verifiers/`), the hosts' starter kit (training
only) and a public seed factorization. In this repository they live under `data/`; elsewhere set
`DFTHC_DATA` and `DFTHC_STARTER` (see `paths.py`) and put the seed under
`$DFTHC_DATA/public/group26/dfthc_group_v2_26_60_30.npz`
([ahmedberatozer/df-thc-group-compression-factorization](https://www.kaggle.com/datasets/ahmedberatozer/df-thc-group-compression-factorization)).
On Kaggle, attach the competition, the starter kit and that dataset; paths are found automatically.

```
python notebooks/dfthc-refit/run.py recipes/merged_10x120x54.toml                   # the published result (~3.5 h on a T4)
python notebooks/dfthc-refit/run.py recipes/merged_10x120x54.toml --scale 0.0002    # a 2-minute smoke test of the whole chain
python -m pytest notebooks/dfthc-refit/tests                                        # exactness and circuit checks (< 1 s)
```

A run writes every step into `runs/recipes/<recipe>/` (or `--out`), ending with `submission/` (a
complete `dfthcsos` folder) and `result.json` (the verifier's verdict). A step whose output exists
is skipped, so rerunning resumes an interrupted run.

On Kaggle GPUs, `make_kernel.py` packs the modules and recipes into one private script kernel:

```
python notebooks/dfthc-refit/make_kernel.py --id YOU/your-kernel --job "run.py recipes/merged_10x120x54.toml"
kaggle kernels push -p notebooks/dfthc-refit/kaggle
```

Several `--job`s run side by side, one per GPU.

The 8-bit merged build (a GPU with fast float64, e.g. an A100: `--device` runs L-BFGS on it at ~140
iterations per second; `notebooks/colab/make_colab.py` sizes the steps to a time budget):

```
python notebooks/dfthc-refit/public_seed.py SEED24.npz group24                         # decode the public (24, 60, 30)
python notebooks/dfthc-refit/experiments/shrink.py SEED24.npz OUT --merge 3 --device \
    179x88,177x86,...,156x60 --pre 120000 --fit 60000 --final 120000 --save 156x60      # (24,60,30) -> (8,180,90) -> (8,156,60)
python notebooks/dfthc-refit/run.py recipes/finish_merged_b8.toml --start OUT/8x156x60.npz   # round, refine, refit, build
```

## Recipes

```toml
seed = "group26"          # public seed: group26 (26, 60, 30), group24 (24, 60, 30), group32 (32, 60, 30) or public (65, 60, 30)
merge = 2                 # merge groups this many at a time (1: no merging)
shape = [10, 120, 60]     # final (R, B, C); B and C are fixed after merging

[[train]]                 # one fresh optimizer per entry
groups = 12               # drop to this many groups first (fade, then fit), or keep the count
fade = 2000
fit = 150000
lr_final = 1e-5           # any other middle.py option: lr, warmup, kappa, jitter, rng, ...

[lbfgs]                   # optional: lbfgs_fit.py options (before rounding)
iters = 3000
kappa = 5e-5

[round]                   # quantize.py options
brot = 10                 # 8: see recipes/merged_*_b8.toml
stage_steps = 3000
final_steps = 8000        # also free = "1.0,0.9995,..." and fit_steps

[polish]                  # optional: polish_words.py options
sweeps = 4

[refit]                   # optional: refit_weights.py options
target = 19.92            # error_2 kept below this (mHa)

[build]
qrom = "four"             # four-address circuits (10-bit words), "tensor" (five 8-bit words), or "reference"
shots = 64
```

`recipes/merged_10x120x54.toml` is the published result (`merged_10x120x60.toml`, without the copy
cut, gives 3.80×); `recipes/small_24x60x30.toml` is the
many-small-groups comparison. Natural next recipes: gap-aware training (`rho_lam`), other merge
factors (9 merged groups fail, see above).

## Pipeline

| Step | Module | Notes |
|---|---|---|
| Recipe | `run.py` | chains the steps below, resumable; `--scale` for smoke tests, `--dry-run` to print the commands |
| Seed | `public_seed.py` | public factorizations, decoded from their 10-bit words |
| Merge | `structure.py` | exact merging, group importance, the represented tensor (numpy only) |
| Train | `middle.py` | staged drops with fades, Adam on ε_fro + κ·D(w); `--init` continues; a larger B grows every group (new random bases, 1e-4 weights) |
| Fit | `lbfgs_fit.py` | optional: float64 L-BFGS on the same objective before rounding (15.35 against Adam's 17.99 mHa on a (4, 239, 128) structure) |
| Fit, on the GPU | `fastfit.py` | `error_2` in the packed space of orbital pairs (equal to the verifier's to 1e-15) and optax L-BFGS in jitted chunks, with no host round trips |
| Shrink | `experiments/shrink.py` | exact merge in threes, then steps that fade each group's weakest vectors and copies (×0.5, ×0.2) while the rest refits, remove them and refit; `--device` uses `fastfit.py` |
| Round | `quantize.py` | progressive rounding in the signed gauge, highest-impact angles first; `--free` sets the schedule (a leading 1.0 is a continuous refit), angles are not clipped and rows are moved into the signed gauge exactly at the end |
| Polish | `polish_words.py` | exact coordinate descent on the rounded words (±1 per angle, exact error_2 change), then w refit; 19.95 → 19.57 mHa in 4 sweeps on the 54-copy structure (−0.5 mHa on 9 groups) |
| Offsets | `refine.py` | orthogonal gauge of each group's copy columns (exact pair sweeps, then descent on the orthogonal group with basin hopping) alternated with L-BFGS on λ_eff (E_gap is convex in the offsets) |
| Weights | `refit_weights.py` | refit (w, W) at fixed words under an error_2 target, with an exact error_2 formula; recovers the gap-floor tax (λ_eff −2%) |
| Circuits | `fourqrom.py` | four-address ANGLE circuits in ≤ 128 qubits: an ANF load (one Toffoli per address monomial of degree ≥ 2, the don't-care rows cancel the rest), paired combine (41 Toffolis instead of 81) and a measurement-based erase whose phase lookup is also ANF (rows/4 + ~57 Toffolis per pass, 376 at 1,276 rows) |
| Circuits, 8 bits | `tensorqrom.py` | five 8-bit words per circuit with no bank: every address monomial cached (low 4 bits and high bits), mixed terms covered two per Toffoli by a GF(2) decomposition, erase by measurement (~293 Toffolis per pass at 1,032 rows, 123 qubits); `--qrom tensor` |
| One-body rows | `onebody.py` | exact ±1/±2 word moves plus random kicks on the one-body rows (error_1 54 → 13 mHa at 8 bits); exact signed-gauge conversion; used by `refine.py` when brot ≤ 9 |
| Score | `build.py` | writes a `dfthcsos` folder and runs the official verifier |

Support: `paths.py` (data locations), `encode.py` (Givens angles ↔ words, verifier metrics),
`landscape.py` / `landscape4.py` (cost models), `make_kernel.py` (Kaggle GPU kernels).
`experiments/` keeps the superseded first pipeline and the dead ends below, as a record.

## Findings

- Hard pruning wrecks the fit (B 60 → 50: 855 mHa); fade removed groups out and refit in stages.
- Weights are ~1e-4 in scale: a fresh optimizer on a converged structure needs a warm-up.
- Long fits matter: 150k steps per stage, and 10 groups needed 150k more to pass.
- Random starts do not catch up: a random (9, 180, 90) sits at 17-20 mHa through the whole shrink
  where the merged public seed is at 6-13; merging our own 240k-iteration seed helps early and not
  below C ≈ 66 (the table under "Status of the claim").
- A seed from the Hamiltonian's own eigen-leaves (`experiments/df_init.py`) matches the merged
  public seed at (9, 180, 90) (6.78 mHa) with no trained weights at all, then loses ~0.1 mHa per
  shrink step to it; basis selection (eigenvalue rank, OMP) and refit length do not change that.
- DF-seeded small groups (27, 60, 30), trained and merged exactly in threes, beat the direct DF
  seed of the merged shape at equal iterations (24.3 against 25.4 mHa after 5k on a CPU, D(w) 45
  against 78): the merge keeps the block structure a trained seed has (`experiments/df_merge.py`).
  The advantage does not survive long fits: with 240k iterations on the small groups (19.26 mHa at
  (27, 60, 30), against 27.88 for random groups) and 240k on the merged (9, 180, 90), the merged DF
  arm lands at 7.37, above the direct DF seed's 6.78 (plan `dm9`, stopped there). On our own seeds
  the merge of trained groups only pays when the groups are trained far better than that.
- DF seeds built directly at a scoring shape, with no shrink, plateau near 19 mHa after 240k
  iterations at both (9, 143, 46) and (8, 143, 60) (plans `t9`, `t8`), against 13.51 for the shrunk
  public seed and 15.83 for the public (8, 143, 60): the shrink was not what cost the DF seed; its
  bases do not reach a trained seed's quality at small shapes.
- Merged structures are rounding-sensitive (at 10 groups: rounding to nearest +36 mHa,
  progressive +3.9 mHa); the damage sits in a few high-curvature angles.
- Merged groups need their copies: cutting 60 → 30 fails at every stage (24.8 / 29.7 mHa at 12 /
  11 groups). The 640-vector dictionary cannot lose copies either (384 → 256: 116 mHa).
- Training w on ε + D raises the convex floor of E_gap at fixed w (3.91 → 4.08 Ha), about 2% of
  λ_eff; `refit_weights.py` recovers it after rounding.
- No effect: Givens-tree relabeling (±1 mHa), AdaRound, a second-order rounding direction,
  training through the rounded vectors, reordering rows to zero four-address bank bits.
- **8 bits.** The cost model's inner state preparation drops from 576 to 304 workspace qubits at
  brot 8, only for B ≥ 129; it also adds 514 Toffolis at every B = 16k (so B = 16k − 1).
  Clipping angles to the signed range cost up to two rounding steps on 3% of the angles; with
  free angles, an L-BFGS fit and κ = 5e-5, a (4, 239, 128) structure rounds to 8 bits at 18.8 mHa.
  Merged (6, 159, 80) and (7, 143, 64) from the (26, 60, 30) seed stop at 19.7 and 20.4 mHa before
  rounding. Short L-BFGS refits between freezing stages converged too slowly (20.9 mHa at 7% frozen);
  with 6,000 iterations per stage they work for the first 10% of the angles (`quantize.py
  --lbfgs-until 0.1`), and Adam takes the rest.
- **Merging in threes passes at 8 bits:** (24, 60, 30) → (8, 180, 90), no group dropped, shrunk to
  (8, 156, 60) at 10.72 mHa, rounded to 17.80, verified at 8.96×. Vectors are nearly free to remove
  with long refits; copies below ~60 are what cost. Rounding costs more as the shape shrinks (nine
  groups: +5.1 mHa at (9, 176, 84), +6.6 at (9, 150, 54), +6.85 at (9, 143, 46), which rounds from 13.51
  to 20.36 and fails; eight groups: +7.1 at (8, 156, 60)). (9, 143, 46) passes after a κ = 2e-5 refit
  at the shape (8 × 60k iterations: 13.51 → 12.81, D(w) 5.7 → 10.9; at κ = 5e-5 the same refits gain
  0.03) and a rounding with L-BFGS until half the angles freeze (`--lbfgs-until 0.5 --lbfgs-iters
  20000`: 19.83, D(w) back to 7.3): 9.47× (`runs/r10/finish_9x143x46_f9k2`). Other schedules (60k-step
  final refits, κ 2e-5 inside the rounding, second-order rounding directions) do no better on (8, 156, 60):
  ~7 mHa of rounding loss is the floor of this family.

- Adam seed training (`experiments/adam_train.py`, the way the public seeds were trained: a decaying
  learning rate over millions of steps) is what the own seeds lacked at the start shape, not at the
  shrink: the DF (27, 60, 30) seed goes to 17.08 mHa after 3M steps (L-BFGS: 19.26; the public
  small-group seeds measure 19.8 to 20.0 as 10-bit words), merges and pre-fits to 6.63 at
  (9, 180, 90) (plan `am9`), and a second Adam pass on the merged structure takes it to 6.38 (plan
  `am9a`), level with the merged public seed. The shrink still drifts +0.1 to +0.2 mHa per step
  (6.50, 6.73 at (9, 179, 88), (9, 177, 86) against r9's 6.30, 6.26; plan `am9s`), so the public
  seed's edge is in what it lets the shrink remove, and no training recipe tried transfers it.

- **Orbital compactness is what the public seed has.** Its groups span ~18 effective orbitals each
  with a profile overlap of .13 between groups; our DF and Adam seeds span ~30 at .28, and that, not
  basis quality, is what the shrink could not fix. A seed that has it from the start: pivoted-Cholesky
  leaves of the multiplicity-weighted target, R groups by balanced k-means on the leaves' orbital
  profiles, OMP bases per group (`experiments/compact_seed.py`). Built directly at (9, 143, 46) with
  no shrink it fits to 12.08 mHa after six 60k refits where the shrunk public seed stands at 13.51
  (plan `t9c`). `df_init.py --leaves chol --assign cluster` has the same construction but weights the
  target by the multiplicity rather than its square root; use `compact_seed.py`.
- **Screening the k-means start.** Effective orbitals per group at the seed stage predict the fit
  after two refit rounds (five starts: 11.87 → 13.36 mHa, 12.27 → 13.97, 12.28 → 14.08, 12.52 → 13.35,
  13.04 → 14.56); overlap differences of .001 do not (`compact_seed.py --kmeans-seed`, a CPU minute each).
- **Adam at the final shape** gains 0.4-0.5 mHa on L-BFGS-converged tables with D(w) flat (1M steps,
  1e-4 → 1e-6, κ 5e-5: 12.08 → 11.69 at C = 46, 12.79 → 12.38 at C = 43).
- **Dealt rows make the coded bit cheap.** Rows sorted by strength put the heavy words in the same
  16-address blocks (heaviest block 4.7× the mean); dealing each group's rows round-robin over the
  blocks (1.5×, `experiments/deal_rows.py`, error unchanged) lets the coded bit 0 (an affine word per
  block, after somejoint's public notebook) cost ~1.1 mHa for 624 fewer angle Toffolis (10,154 → 9,530).
- **Rounding noise adds in quadrature**, 15.1-15.6 mHa for every table here (√(19.55² − 12.38²),
  √(19.48² − 11.69²)), so a table must fit to ≈12.5 mHa before rounding; that number picks the shape
  (at λ_eff 47.2: C = 46 models 9.9×, C = 44 10.0×, C = 43 10.05×).
- **Augmented-Lagrangian refit** (`experiments/refit_al.py`): `refit_weights.py`'s L-BFGS stops at the
  E_gap penalty kink after two iterations with the error budget unspent; the AL version spends it
  (19.48 → 19.98 mHa, λ_eff 47.305 → 47.163 at C = 46). At C = 43 the gap constraint binds first and
  it leaves error_2 at 19.56.

## Credits

Built on public Kaggle work, all Apache-2.0:

- **ahmedberatozer, DF-THC Group Compression:** the D(w) penalty, staged group dropping,
  sensitivity-ordered quantization and long refits; its factorizations are the seeds.
- **kozykappa, Complete-Domain Affine Compilation** (on the banked QROM of Kozykorpesh and Sumit
  Chongder): the four-address lookup with difference banks and the signed gauge.
- **kozykappa (sparse SOS factors) and Artem1410 (anazemcev):** the gauge rotation of the copy
  columns and the effective-norm refinement. `refine.py` is adapted from the group-compression
  notebook's implementation of both (`chemistry_refine.py`); `quantize.py` and `fourqrom.py` are
  our own code, written after reading its `dfthc_train.py` and `gauge_qrom.py`.
- **phucthaiv02, QCC Verified Portfolio + DF-THC Retraining Study:** the paired combine (reconstructed
  in `fourqrom.py` from its description), refitting w and W after rounding (`refit_weights.py`, our
  own implementation), exact word-level coordinate descent (our `polish_words.py`), and a per-group
  orthogonal copy gauge, an idea it credits to haideptry (our own search in `refine.py`).
- **ANF loading and erasure** (algebraic normal form of the table, with the never-addressed rows as
  don't-cares) appear in the public banked-QROM code (`banked_lab.py` in the group-compression
  notebook, after Kozykorpesh and Sumit Chongder) and in phucthaiv02's pruned ANF erase; the ANF load
  and erase in `fourqrom.py` are our own construction for the four-address circuit.
- **somejoint, Toffoli Diet:** the 640-vector dictionary, and the coded low bit (an affine word per
  16-address block) that `quantize.py --coded` follows.
- **mrmeows, QCC open circuits and sources:** the exact lookup emitter's design that `tensorqrom.py`
  follows (cached address monomials, paired affine products, measurement erasure; our decomposition
  and code) and `refresh_one_body8.py`'s ±1 one-body polish (our `onebody.py` adds kicks, ±2 moves
  and the exact gauge conversion).
- **lightningv08:** five words per ANGLE circuit. **michaelrustad:** the B ≥ 129 cliff at 8 bits and
  L-BFGS continuous refits of merged groups. **ahmedberatozer (v8 components):** the fine start of the freezing
  schedule.
- **k256net and Dmitrii Gluzdov:** the public 10-bit (65, 60, 30) factorization.
- **The hosts:** the verifier, kickmix (whose `del_lookup` the truncated erase follows) and the
  starter kit (the DF-THC residual used in training).

Our own: merging as a warm start and the merged schedules, the equal-weights and equal-budget
comparisons, the convexity of the gap floor, the exact error_2 formula for the refit, the
four-address ANF load and erase construction, the triple merge with per-group fades and the on-device
float64 fit, the Gray-ordered top level and truncated erase of
the unary variant, and the recipe runner.
