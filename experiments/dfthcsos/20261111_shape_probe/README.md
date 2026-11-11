# Shape probe (5,129,68): cheap static win, accuracy closed at 5k steps

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
No verifier call, no quantization, no circuits; heuristic costs are exact
official arithmetic and the accuracy probe is the same continuous L-BFGS
objective used in the R5/R4 training logs.

Question: does R=5, B=129, C=68 (721 vectors) give a cheaper set?  Exact
answer: heuristic T 6,516 and Q_total **427** (not 387; 387 is the heuristic
`qubits` field before the +J·brot=40).  With today's loaders the cost is only
−0.98 %; with linear loader scaling it is −23.6 %, but the shape cannot reach
the 20 mHa gate.

## 1. Exact official costs (`cost_sweep.py`)

Output: `artifacts/20261111_shape_probe/cost_sweep.txt`.

| shape | heuristic T (outer+inner+givens) | persistent | inner temp | Q_total | T with 8,246 angles | T·Q | score at 46.907537 |
|---|---|---:|---:|---:|---:|---:|---:|
| (8,143,44) baseline | 6,662 (317+4,095+2,250) | 84 | 303 | 427 | 14,908 | 6,365,716 | 298,600,061.555 |
| **(5,129,68)** | **6,516 (313+3,953+2,250)** | **84** | **303** | **427** | **14,762** | **6,303,374** | **295,675,751.857** |
| (5,129,44) | 5,319 (276+2,793+2,250) | 84 | 302 | 426 | 13,565 | 5,778,690 | 271,064,117.486 |
| (5,135,70) | 6,627 (317+4,060+2,250) | 84 | 303 | 427 | 14,873 | 6,350,771 | 297,899,028.408 |
| (4,131,83) | 6,442 (311+3,881+2,250) | 83 | 303 | 426 | 14,688 | 6,257,088 | 293,504,589.579 |
| (6,143,59) | 6,682 (318+4,114+2,250) | 84 | 303 | 427 | 14,928 | 6,374,256 | 299,000,651.925 |
| (6,180,90) | 10,211 (386+7,575+2,250) | 86 | 304 | 430 | 18,457 | 7,936,510 | 372,282,139.909 |

`Q_total = persistent(84) + J·brot(40) + max(90, 303, 77) = 427`.
The +40 is mandatory; the recon's "Q 387" is the heuristic `qubits` field
(84+303), not the scored Q.

Break-even with today's loaders: lambda_eff ≤ **47.371465** (+0.989 %).  The
shape's lambda_eff at 40 mHa is likely ≥47, so even the −0.98 % T gain can be
erased by the weight degradation.

Linear-loader projection (721/1,220 vectors; **assumption, no circuit built**):
angles 4,873.251, T 11,389.251, Q 427, score **228,121,209.808** (−23.6 %),
break-even lambda_eff 61.399786.  The recon's 231.1e6 is close; our exact
arithmetic with Q=427 gives 228.12e6.  The projection is not a measured
loader: no 721-address family was synthesized.

## 2. Accuracy probe (continuous, same objective as R5/R4)

Seed: `experiments/dfthcsos/20261106_train_r5/seed_numpy.py` (NumPy-only,
pivoted-Cholesky leaves + balanced k-means + OMP), 11.6 s, seed continuous
`error_2 = 661.08 mHa` (SHA `a0342b18…0f5abbd`).

Training: separate venv `artifacts/20261111_shape_probe/venv` (jax/optax from
the uv cache; the shared `.venv` was not modified), `slim_train.py` on
`prob_r5.npz` (the target matrices are shape-independent), 500 + 4,500 steps.

Measured continuous `error_2` (mHa), total steps:

| 500 | 1,000 | 1,500 | 2,000 | 2,500 | 3,000 | 3,500 | 4,000 | 4,500 | 5,000 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 169.05 | 124.95 | 105.14 | 93.78 | 86.36 | 80.56 | 76.06 | 72.73 | 70.14 | **67.82** |

5,000 steps took 174 s.  Free 3-parameter fit `a + b t^-p`:
a=26.4 mHa, b=4,094, p=0.540; predicted 50k = **38.3 mHa**.  Control
R5/B135/C70 (same optimizer/loss, 751 vectors, U params 51,300) measured
182.00 @500, 84.82 @2k, 49.85 @10k, **40.24 @50k**; free fit a=36.5.  The
(5,129,68) basin is the same ~40 mHa class, not 20.

Why 20 mHa is not credible for this shape: the current 20 mHa solution uses
U params 8·143·76 = 86,944; any 721-vector shape has R·B = 645, hence at most
5·129·76 = **49,020** U params (56 % fewer).  History: R4/B131/C83 (U 39,824)
73.07 @20k; R5/B135/C70 (U 51,300) 40.24 @50k; R6/B143/C59 (U 65,208) 33–37;
R6/B180/C90 (U 82,080) 23.74 but T 18,457 (worse than baseline).  The 20 mHa
region needs the larger U basis that the 721-vector shape cannot hold.

The continuous error is before 8-bit quantization; the baseline's quantized
e2 is 19.99998 mHa.  Even the free-fit 50k value 38.3 mHa is ~2× the gate
before quantization, so a 7-bit/8-bit encode cannot rescue it.

## 3. Verdict

**Closed.**  The static projection is large only under linear loader scaling
(not built), and the measured accuracy basin is ~40 mHa continuous, ~2× the
20 mHa gate.  Do not start a 50k training; the 5k probe and the R5 control are
decisive.  The (4,131,83) shape is also closed by its measured 73.07 mHa;
(5,129,44) has even fewer U params and is not worth probing.

## 4. Files / SHAs

`artifacts/20261111_shape_probe/` (gitignored):
- `seed_5x129x68.npz` `a0342b18fd2e6c54924cf7841a6f6c21d69d840ffb14cde70de7530ee0f5abbd`
- `train_5x129x68_500.npz` `0beece08f2098830421bd776a0ccd31a9e5dfd5a57430e98fe5e443dd5a8a2ab`
- `train_5x129x68_5000.npz` `f4773a634689e2b17dfced7967ac0e5c57642fd746d999bf28b184efe60e33ff`
- `seed_5x129x68.log`, `train_5x129x68_500.log`, `train_5x129x68_5000.log`, `cost_sweep.txt`, `venv/`

## 5. Verification scope

- `heuristic_costs` exact (official); continuous L-BFGS only (no quantization,
  no Givens encode, no circuit, no `evaluate_words`, no `verify.py`).
- The 228.12e6 linear projection is an assumption, not a verified score.
