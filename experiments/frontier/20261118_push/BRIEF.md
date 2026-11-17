# 2026-11-18 push — shared brief for parallel research subagents

Read this file first. It is the only context you need to start. Do not re-derive
facts marked **[measured]**; they were verified by the official verifiers.

## Mission

Raise the Kaggle score of the competition *Google Quantum AI – Verifiable Quantum
Circuit Compilation* substantially. Score is a geometric mean of three independent
cost ratios (lower cost is better):

```
GM = ( ref_inv/cost_inv * ref_dqi/cost_dqi * ref_chem/cost_chem ) ** (1/3)
REFERENCE = {invsqrt: 2076774.233715, dqi: 24439463583672.93, chem: 3355599588.3155375}
```

Every leg has **equal log weight**: a 10 % cost cut in ONE leg = GM x 1.0323,
i.e. about **+0.9 GM**. That is the sizing rule for every experiment.
`scripts/gm.py` is the authoritative calculator.

### Current best (verified, package ready to submit when quota resets)

| leg | circuit | Q | Toffoli | T / other | cost | ratio |
|---|---|---:|---:|---:|---:|---:|
| invsqrt | `563d0583` | 44 | 1,454.0008 | T=962.256 (rotations) | **74,560.90687** | 27.853 |
| dqi | `575b043f` | **890** | static 367,989 | mean executed **T=367,116.06** | **346,409,762,292.72** | 70.551 |
| chem | `a73b25d2` + 15 loaders | **427** | T=**14,706** | loader sum 4,025 x2 | **294,643,137.73** | 11.389 |

GM 28.180659 (local salt). LB best submitted 28.15094, rank 156. Gold 28.71339.
Top of LB is 31.42723 — so much more is possible than the "current generation
is capped" story says. Find where it comes from.

### Cost formulas (exact, from the official verifiers)

* invsqrt: `score = Q * (toffoli_count + t_count/4)`; Q = `circuit.num_qubits`;
  x-register is 22 qubits; 200,540,928 shots; rotations priced
  `0.56*log2(1/eps)+5.3 T` each at the largest eps that fits tolerance.
* dqi: `score = rep_factor * Q^2 * mean_toffoli`; `rep_factor` is a constant
  1.1912605 given 0 errors on 102,400 shots (Clopper-Pearson at delta=2^-128);
  **only Q and T are levers**. Q = `circuit.num_qubits`. Contract floor
  **Q >= 840** (70 syndrome registers x 12 bits). Mean error weight of a shot is
  **31.05**, P(k<=3) ~ 7e-21, so no low-weight classical fast path exists.
* chem: `score = lambda_eff * T_total * Q_total`;
  `T_total = 2*sum(loader Toffoli) + T_h`, `T_h = outer + inner + givens`;
  `Q_total = 84 + J*brot + max(outer_temp, inner_temp, angles_temp=77)`.
  `lambda_eff` floor measured 46.786; shipped 46.9216.
  Loader cap: every angle circuit must use **<= 128 qubits** (`QUBIT_CAP`), and
  loader qubits are **not** in Q_total (free), only loader Toffolis are paid.

## NEW finding (2026-11-18, not yet exploited): `brot` is submission-controlled

In `verifiers/dfthcsos/verify.py` the verifier reads `brot` and `J` from the
**word registers of your own loader circuits**, and passes `beta = brot` to
`SpinFreeData_V1`. Exact model values for the shipped shape (R=8,B=143,C=44,N=76,
chi=10 fixed, J=5):

| brot | givens | T_h | Q_total |
|---:|---:|---:|---:|
| 8 (shipped) | 2250 | 6,662 | 427 |
| 7 | 1950 | 6,362 | 422 |
| 6 | 1650 | 6,062 | 417 |
| 5 | 1350 | 5,762 | 412 |
| 4 | 1050 | 5,462 | 407 |

so brot 8->7 alone is `(422/427)*(14412/14706)` = 0.9685 on chem cost = **+0.30 GM**,
if the 75 angle words can be re-quantised to 7 bits while keeping
`error_1,error_2 <= 0.020` and `Lambda >= 49`. `theta/pi = word / 2**(brot-1)`.
This needs a refit (7-bit word quantisation is coarser). Explore it.

## Rules (hard)

1. **All circuits run on Kaggle CPU kernels. NEVER simulate/verify locally** —
   the local machine has memory pressure. Local work is limited to reading
   files, pure-arithmetic scripts (small numpy), and editing code.
2. CPU only: `enable_gpu=false`, `enable_tpu=false` (scripts/kgpu.py enforces it).
3. **Do not submit to Kaggle** and **do not git push**. No dataset publishing.
4. Do not delete or overwrite other lines' files. Write only inside your own
   directory under `experiments/frontier/20261118_push/<your line>/` plus
   `artifacts/`. Keep records: hypothesis, exact commands, measured JSON.
5. Kaggle CPU session cap is ~5 concurrent. **Run at most 1-2 kernels at a time**
   and cancel/finish before pushing more. Prefer one kernel that sweeps many
   candidates.
6. Use the account assigned in your task. Token files: `~/.kaggle/access_token_<acct>`
   (`qingyu1232`, `zhuating`, `jiyujia`, `ccjjllt_check`).

## How to run a Kaggle CPU kernel

`python scripts/kgpu.py new --dir DIR --slug SLUG --account ACCT [--dataset O/S ...] [--competition]`
then `python scripts/kgpu.py push --dir DIR --account ACCT`,
`status --kernel O/S --account ACCT`, `fetch --kernel O/S --account ACCT --out DIR`,
`logs --kernel O/S --account ACCT`.

A kernel that needs the competition data adds
`competition_sources: ["google-verifiable-quantum-circuit-compilation"]`.
Mount path: `/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation`.
Find `kickmix` + `verifiers` by walking up from `FeMoCo76o113e.fcidump`:

```python
COMP = None
for p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for up in (p.parents[1], p.parents[2], p.parents[3]):
        if (up / "kickmix").is_dir():
            COMP = up; break
    if COMP: break
```

Run an official verifier (unmodified) as a subprocess:

```python
env = dict(os.environ, PYTHONPATH=f"{COMP/'kickmix'}:{COMP/'verifiers'}")
subprocess.run([sys.executable, str(COMP/"verifiers/dqi/verify_submission_dqi.py"),
                str(path), "--salt", "s1"], env=env, cwd=str(COMP/"verifiers"))
```

* dqi verifier: default 102,400 shots, takes a few minutes; `--salt` optional.
* invsqrt verifier: 200,540,928 shots (long, ~tens of minutes).
* chem verifier: `verify.py <dir>` where `<dir>` contains `dfthcsos/submission.npz`
  and `dfthcsos/angle_k_*.kmb`; it simulates every address x 64 shots.
Always read the printed JSON: `status`, `score`, `toffoli_count`, `num_qubits`,
`value_errors`, `phase_errors`.

You can mount other public notebooks/datasets by adding their refs to
`dataset_sources` / `kernel_sources` and reading them under `/kaggle/input`.
If an input is a notebook that produced `submission.zip`, extract it first.

## Already closed — do not spend time re-measuring

* invsqrt 44Q liveness: peak exactly 44, 0 of C(44,2) wire pairs disjoint;
  renaming search space empty. 42Q needs `retire+recompute` >=132 C per pair vs
  80.95 C slack; 42Q even free is only 28.5909. (A *fresh* 42Q synthesis or a
  cheaper rotation block is still open.)
* chem rows: `rows = 76 + R*B`; accuracy needs rows >= ~1160 at <=20 mHa;
  R=5/R=4 shapes are 130-180 mHa even continuous; merging groups is structurally
  lossy (0.16-0.39 Ha per merge). Probe at 791 rows could not even plan a
  rank-74 loader basis. Closed.
* chem shapes (8,303,44)=318M, (4,303,128)=462.5M, (4,333,44)=342M and
  (8,136,96)=369M are all worse; public baseline (65,60,60) lambda 49.30/Q 634.
* chem Q axis: exact formula above; k2 selector maximises inner_temp; Q_min=427
  for gate-legal shipped-family shapes.
* chem loader cuts: 15 shipped loaders total 4,025 Toffoli; k0/k1 have no rank-74
  basis (5 seeds each); k2/k3 search lands 271 > 269; algebraic ceiling 375 cuts
  is loose; known reachable 149 cuts. Remaining realistic gain ~+0.1 GM.
* DQI width: full-tape liveness peak 890 exactly (3 models, 0 dead wires,
  0 restorable covers at any k). 890 = 840 syndromes + 50 pool. A **new
  generation** (<=864Q) is the only width path; the public `dqi_reference_circuit.py`
  is a *wider* (1272+ wire) syndrome-form generator, not a drop-in.
* DQI T: "saturated" only means conditional execution saves 873 T in the current
  tape. Product-cache/measured-uncomputation rewrites still exist in principle:
  the public dataset `grantprater/vqcc-dqi-61c8348d-merged-closings` documents
  ~686 more Toffoli-likes waiting in closings and has the tools
  (`vqcc_measure_out.py`, `vqcc_pair_window.py`, `vqcc_stream_diff.py`,
  `vqcc_ir.py`, `vqcc_bitsim.py`). Our `575b043f` is 4 static Toffolis better
  than their `61c8348d` (367,989 vs 367,993), but their tooling was not applied
  to the *pair-finder inside condition blocks* problem (open item #3 there).

## Public intel (2026-11-18 00:00 Beijing)

Top LB: 31.42723 (Z3C1oherence), 31.01379 (aadi_stonks), 30.28512, 30.13063,
30.00881, 29.97900, 29.57281, 29.21549, 29.14389, 28.92557 ... gold 28.71339
(rank 15). Public notebooks we already have locally:
`artifacts/20261117_lb_decomp/` (harvest/leotang/ratna),
`/tmp/pull_ghaz` (28.18 | 4,022-Toffoli loaders),
`/tmp/pullintel` (boristown C43 native compiler),
`/tmp/pull_oz` (super-SOTA 28.091).
New public artifacts appearing hourly — check
`tools.kaggle.search_notebooks` (sort `DateRun`) and
`tools.kaggle.search_datasets` (sort `Updated`, search "qcc"/"vqcc").
Known: `grantprater/vqcc-dqi-61c8348d-merged-closings` (DQI + tools),
`srinath2495/vqcc-portfolio-v23-artifacts`, `ratnachand/vqcc-verified-public-floor`,
`ghazarosbarseghyan91/vqcc-combo-candidates`.

## Key local paths

* `docs/session-20261117.md`, `docs/ceiling-20261117.md` — roadmap + per-leg ceilings.
* `experiments/frontier/20261117_deep/SUMMARY2.md` — all measured closures.
* `experiments/frontier/20261117_deep/integration/{make_members.py,make_main.py,members_2818066.json}`
  — packaging path (`make_main --invsqrt-b64` expects zlib-compressed base64).
* `experiments/frontier/20261117_deep/chem/work/ds/code2/` — chem emitter
  (`planner.py`, `compile_basis.py`, `emit_from_basis.py`, `climb_cuts.py`,
  `basis_plan_k*.json`), generalised off 1,220 rows.
* `experiments/frontier/20261117_deep/chem/work/k_emit_r5/main_template.py` —
  row-general emission kernel; `k_probe791/main.py` is a complete working example.
* `experiments/frontier/20261117_deep/dqi/` — DQI audit/liveness/EEA kernels.
* `data/competition/verifiers/` — unmodified official verifiers (kickmix.so is
  Linux; on macOS use the PyPI `kickmix` only for tiny metadata reads, and never
  for simulation).
