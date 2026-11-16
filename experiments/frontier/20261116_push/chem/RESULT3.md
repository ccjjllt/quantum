# RESULT3 — the R=5/6 merge-pipeline attempt, the λ refit, and the code/loader path

Date: 2026-11-16 (third session). Chemistry only. `RESULT.md` (R=8 decomposition) and
`RESULT2.md` (rank/projector walls) stand. No submission made.

## 0. Verdict

1. **λ refit: closed.** The public chemistry point `bdae290f` (λ 46.92160235, cost
   **294,762,632.08**) is a genuine corner: `error_2` is at the gate −1.5e-9,
   `error_1` at the gate −2e-9, `E_gap` at the floor +1.5e-9, and the only *fully
   free* lever — orthogonal rotations of each group's copy columns (which preserve
   e2, h1′ and E_gap exactly) — is **exhausted**: a 72-angle pair sweep × 6 Haar
   random restarts per group finds **0.0000 %** improvement in the L1 term
   (270.115287), while a random rotation is 2× worse. A projected gradient on the
   offsets with the exact λ/E_gap gradients accepts **no admissible step** (every
   direction that lowers λ leaves one of the three gates). The −330 needed for
   28.09487 is therefore **not available from these words**.
2. **R=5/6: the route exists and the pipeline runs, but the CPU budget is the
   binding resource.** The public merge pipeline reaches the shape only from a
   ≥10-group seed (`B10c54`, (10,120,54) → merge pairs → **(5,240,108)** exactly);
   the public (8,143,44) seed **cannot** reach it (pairs → 4 groups, K=300, rank
   floor 16.7 mHa ⇒ dead). A tiny-budget smoke run on Kaggle CPU (pre 20, fade 8,
   fit 12, final 25) improves the merged seed 16.163 → **15.847 mHa** at
   (5,240,108) but collapses during the shrink (copy fade 108→100 → 33.2; base
   shrink → 246; end 321 mHa) — i.e. the numbers are *unconverged*, not a shape
   verdict. A full-budget run (8,200 iterations ≈ 7.5 h) is launched and pending.
3. **Code/loader path (2–9 gates): blocked on the planner, not on the codes.** My
   cost model measures the *feature support* (saturated: all 15 low × 77 high
   present for every loader) and the *degrees*, which are necessary but not
   sufficient; the Toffoli count is set by the planner's column/pairing
   optimisation (syed's matroid-parity search), which is not in the public code.
   Without that planner a code change cannot be priced, let alone built.

## 1. λ refit: the exact numbers and why it is closed

Base `bdae290f` (boristown, `submission.zip` → `dfthcsos/submission.npz`):

```
error_1 19.999998 mHa   error_2 19.9999985 mHa   Lambda 283.144439
E_gap 3.9148980015 Ha (floor 3.914898)   lambda_eff 46.92160235   cost 294,762,632.08
```

Free-parameter inventory at fixed words (the verifier reads only `w`, `H2_I`; the
submitted `U`, `H1_I` and `Hsym_lower` are ignored — `H1_I`/`Hsym_lower` are replaced
by the fixed baseline shifts):

| lever | invariants | status |
|---|---|---|
| orthogonal rotation of a group's `C` copy columns | `w wᵀ` (e2), `w H2_Iᵀ` (h1′, error_1), |`H2_I|²` (E_gap) | **exhausted** — 0 improvement (§0.1) |
| offsets `W = H2_I − Σ_b w` (352 numbers) | changes λ, h1′ and E_gap | **blocked** — projected gradient step rejected by the gates |
| changing `w` magnitudes/signs | changes e2 (at gate −1.5e-9) | blocked |

Measured margins: `error_2` 20 − 19.9999985 = **1.5e-6 mHa**; `error_1` 2e-6 mHa;
`E_gap` **1.5e-9 Ha**. The sign-mixing excess in the L1 term is 0.153859 (worth
−80,644 of cost if it were removable for free); it is not, because removing it
changes the Gram `w wᵀ` and hence e2.

The three targets and what each needs:

| target | chem cost | λ_eff needed | Δλ vs bdae | verdict |
|---|---:|---:|---:|---|
| public best (bdae) | 294,762,632 | 46.9216024 | — | current |
| 28.09487 (rank 92) | ≤ 294,762,367 | ≤ 46.9215443 | −5.8e-5 (−1.2 ppm) | not reachable |
| 28.09490 | ≤ 294,761,300 | ≤ 46.9213852 | −2.2e-4 (−4.6 ppm) | not reachable |

Evidence that this is a real corner rather than a search failure: the public
frontier has produced λ 46.9276 → 46.92174 → 46.921613 → 46.921602 over many
independent refits (marculera/atakan/asteriospanoras/sub1/bdae), i.e. the last
several teams all converge within 1e-5 of the same point, and my independent
rotation search (`rotate_columns.py`, 72-angle sweeps with 6 Haar restarts per
group, 8 groups) and offset probe (`offset_probe.py`, exact gradients, gates
enforced) both reproduce it and cannot move it.

## 2. R=5/6 via the public merge pipeline

### 2.1 The route (and why the (8,143,44) seed cannot take it)

`structure.merge(p, k, C)` merges k groups into one (bases and copies are unions,
weights block-diagonal — an *exact* merge) and pads copies only up to
`max(C, k·C₀)`; the shrink schedule then only **fades/removes** bases and copies.
Hence:

* (8,143,44) merged in pairs → **(4,286,88)** → shrink → (4,143,75): K=300, rank
  floor 16.7 mHa > the 14.5 mHa continuous gate ⇒ dead by the rank wall.
* (10,120,54) merged in pairs → **(5,240,108)** exactly (e2 unchanged, 16.163 mHa)
  → shrink to (5,143,75): K=375, floor 5.56 mHa. **This is the only route**, which
  is why the earlier (8,143,44) attempts were doomed regardless of the optimiser.

### 2.2 Pipeline runs on Kaggle CPU (proven)

Kernel `qingyu1232/qcc-chem-merge-pipeline-smoke` (CPU, no GPU, no internet) ran
the public chain end to end: `experiments/shrink.py --merge 2 --device` (rc=0,
293 s), `quantize.py --brot 8 --x64` (rc=0, 1373 s), `build.py` (rc=0). Timings:
shrink ≈ **3.3 s/iteration**, quantize ≈ **0.7 s/Adam step**.

Smoke result, explicitly **unconverged** (pre 20, fade 8, fit 12, final 25 vs the
public's pre 2500 / fade 300 / fit 1200 / final 4000):

```
start (5,240,108):                     error_2  16.163 mHa
pre-fit (5,240,108):                   error_2  15.847 mHa
240x100 (copy fade only) -> 5x240x100:  33.2 mHa
190x90                 -> 5x190x90:   300.0 mHa
160x82                 -> 5x160x82:   434.9 mHa
143x75 (target)        -> 5x143x75:   321.5 mHa
```

The merged seed at (5,240,108) is **15.85 mHa continuous** — already below the
16.7 mHa gate for 791 rows — and the shrink is what must be paid for. The public
experience on its own route ((9,180,90) → (9,143,46), B −21 %, C −49 %) is
**12.81 mHa continuous** after long refits, i.e. the shrink can *improve* a merged
seed when it is given thousands of iterations. Our route needs B −40 % (240→143)
and C −31 % (108→75), which is more aggressive.

### 2.3 Full-budget run: **the gate fails at the base shrink**

Kernel `qingyu1232/qcc-chem-merge-shrink-full-budget` (COMPLETE, 6,513 s of shrink +
2,644 s of quantize, CPU):

```
start (5,240,108):            16.163 mHa
pre-fit (5,240,108):          13.709
240x100 (copies only):        14.171        <- the copy shrink 108->100 is cheap
200x90 (bases 240->200):      27.839        <- the base shrink is what breaks
170x82:                       39.987
143x75:                       53.653  continuous   (gate 16.7)
quantize --brot 8:            73.1 mHa 8-bit       (gate 19.9)
```

**So the R=5/6 line is closed by a real-pipeline measurement, not by a model:** the
continuous error at the target shape is **53.65 mHa**, 3.2× the 16.7 mHa gate, and the
8-bit quantization takes it to 73.1. The failure is localised: the copy reduction is
almost free (16.2 → 14.2 through 108 → 100 copies) but compressing the **basis**
240 → 200 → 170 → 143 multiplies the error each step — the same projector-saturation
effect measured in `RESULT2.md` §4 (the 143-projector spans are already exhausted at
44 copies). The one shape on this route that *does* fit, (5,240,100) at 14.17 mHa, has
rows 1,276 and `T_heur` 9.2 k, i.e. T ≈ 17.7 k — worse than the current 14,712.
The loader side is nevertheless ready: `LOADER_R5_PORT.md` has a Kaggle-verified
791-row loader at **238 T / 99 qubits** (exact word match on all 800 addresses).

## 3. Code/loader path (2–9 gates below 4,025)

What my model can and cannot say:

* `grid1232.py` (16×77 plan grid) shows the union feature support is **saturated**
  for every loader (all 15 low × 77 high coefficients appear), and
  `anf_scan.py` shows the naive ESOP cost is 2,036 monomials — so the cost is not
  set by the support or the degrees, it is set by the **planner's column/pairing**
  (the shipped 193 products pair 386 columns; syed's `matching`/`transport_cuts`
  solve it as a matroid-parity problem).
* The marculera §3 degrees (bit 0 affine from batch 1, XOR-of-five affine at bit 1
  and degree 2 at bit 2) are *constraints* a code must satisfy, not a cost
  functional: many codes satisfy them and differ by a few products, which is
  exactly the 2–9 gate range the private teams found.
* **Blocking site**: the planner is not in the public code (`marculera/dfthc-c44-build`
  ships the 15 `.kmb` and the table only; `dfthc_refit` ships QROM builders
  (`fourqrom.py`, `tensorqrom.py`) but not the coded-word ESOP planner). Without it a
  code assignment cannot be priced, and building it needs the emitted plan, not
  just the word table. Reproducing it is a multi-day task (it is the same planner
  `RESULT.md` §4 documents), not a search over codes.

## 4. Files, kernels, scope

* `rotate_columns.py` — free-rotation search (e2/h1′/E_gap invariant), 0 gain.
* `offset_probe.py` — projected gradient on the offsets with the exact λ/E_gap
  gradients and the error_1/E_gap gates enforced; no admissible step.
* `merge_shrink_probe.py` — weights-only shrink probe (shows vectors must be
  re-optimised; hard truncation ⇒ 795 mHa, hence the fade is essential).
* `score_published.py` — scores the public merged factorizations in the exact
  error_2 geometry (validates against the verifier: `M9x143x46_b8` 19.964 mHa,
  `M8x156x60_b8` 17.787, `B10c54` 16.163, seeds and 8-bit rows identical where the
  npz already holds rounded structure).
* Kernels (CPU, no internet): `qingyu1232/qcc-chem-merge-pipeline-smoke` (COMPLETE),
  `qingyu1232/qcc-chem-merge-shrink-full-budget` (v2, pending),
  `qingyu1232/qcc-chem-lambda-refit-fixed-words` (public `refine.py` from sub1,
  running; expected to reproduce the corner), plus
  `qingyu1232/qcc-chem-merge-shrink-fit-to-5x143x75` (my numpy reimplementation of
  the same objective, superseded by the real pipeline).
* No candidate package, no submission. The verified R=8 baseline is unchanged
  (T 14,712, Q 427, λ 46.927643, 294,800,582.44 at 3 salts; the refit-weights
  variant 294,762,697.44 metrics-only).

## 5. Recommendation

* **Do not spend the remaining slot on a chemistry λ refit or on a loaders-2–9
  search**: the λ corner needs −330 and is closed by three simultaneous gates plus
  an exhausted rotation lever; the loader gates need the private/planner-side
  coded-word ESOP search that is not in any published code.
* The one live chemistry thread is the pending full-budget merge run (§2.3). It is
  the only route that can produce a *real* T step, and its first converged numbers
  will decide it. **The loader side of that route is priced in `LOADER_R5.md`**: at
  791 rows the shipped plan family costs 171-242 per loader (cache 49 +
  (525 - sum_cuts)/2), i.e. <= 237 is likely and even the pessimistic end is a
  +0.36 GM step; the cap is *easier* (78 workspace vs 77) and the cut space is
  47-72 % larger because there are 49 high slices instead of 76.
