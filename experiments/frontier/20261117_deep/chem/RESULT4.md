# RESULT4 — k2/k3 loader: −6 Toffoli target, and why it could not be emitted this round

Date: 2026-11-17. Chemistry only. Local work = git restore + static reading.
**No simulation and no verifier run happened locally.** The candidate build needed a
Kaggle CPU kernel and that kernel could not be launched (§3) — recorded honestly, no
numbers are invented.

Baseline: 15 loaders / pass = `292, 287, 269, 269, 263×5, 264, 265×4, 266` = **4,022**
(`a73b25d2`, T 14,706, Q 427, λ_eff 46.921716818, cost 294,643,137.73, GM 28.15083).

## 0. Verdict

**NOT DELIVERED this round — the blocker is tooling/packaging, not the algebra.**
The emitter is restored and the arithmetic says a real, emittable win exists
(**k2/k3 269 → 264, −5 each, −10 T/pass, −20 T total, GM +0.0127**), and possibly
263 (−6 each, −24 T, GM +0.0153), but the 424 KB compiler port cannot be put on a
Kaggle CPU kernel with this account (§3). Nothing was run, nothing was submitted.

## 1. The exact arithmetic (all from `CODE2.md` §1 + the shipped qubit column)

Per loader: `T = products + high_cache + low_cache`, `products = (525 − Σcuts)/2`,
`525 = 15 low monomials × 35 outputs`, low cache 6.

| loader | T | products | Σcuts | high | low | note |
|---|---:|---:|---:|---:|---:|---|
| k2, k3 (shipped) | 269 | 195 | 135 | 68 | 6 | 6 above the family floor |
| **stored `basis_plan_k2.json`** | **270** | 196 | **133** | 68 | 6 | **a loss** (+1) — the plan family found only 133 cuts for k2 |
| port's best on this table (CODE2 §4) | **264** | 190 | **145** | 68 | 6 | −5 per loader, emittable |
| family floor (CODE2 §0.3) | **263** | 189 | 147 | 68 | 6 | needs 147 cuts; not found by the port |

So the realistic prize is **264 per loader** (`Σcuts = 145`), i.e. `−10 Toffoli/pass`,
`−20 T` (T 14,706 → 14,686), `cost × 0.998640`, **GM +0.0127** (28.15083 → 28.1635).
The full `263` would be `−24 T`, **+0.0153** (28.166) — but the port has never produced
147 cuts on this table, and the shipped 145-cut bases were already "a tie or a loss"
for the loaders that have slack.

Emittability: batches **0–8** are covered by the shipped emitter (`CODE2.md` §5);
k2/k3 are in that set (the un-emittable ones are k9–k14). So the only blocker here is
getting the compiler onto a kernel (§3), not an emitter-convention failure.

## 2. What was restored and read (so the next attempt starts warm)

```
git archive 8155189 experiments/frontier/20261116_push/chem/{code2,code3,anf_scan.py} \
  | tar -x -C experiments/frontier/20261117_deep/chem/work
```
→ `code2/` (1.1 MB, incl. `compiler/{emit_plan,planner,minrank,lowbasis,extract_matching,
parity_recover,low_helper_cache,padding_completion,transport_cuts,high_subspace_emitter}.py`),
`basis_plan_k{2,9,10,12,13,14}.json`, `compile_basis.py`, `emit_from_basis.py`,
`emit_DC_from_basis.py`, `code3/`.

Entry points, exactly as they work:

* `compile_basis.compile_one(W, k, outdir, seeds, trials)` = plan → matching → emit →
  **all-branch proofs**. `prove_one = None` in the port (the proof module is not
  shipped), so the proof line must be skipped — use the emit path of
  `emit_from_basis.build()` instead.
* `compile_basis.plan_one(target, seeds, trials, time_limit)` is the planner:
  `minrank.find_basis` (rank-74 low basis) → 75-slice annihilators → `descend_smart`
  (rank-guided top-down) → `local_search(seconds=LS_SECONDS)`; `STOP_AT = 145`.
  `STOP_AT` and `LS_SECONDS` are env/constant knobs: to chase 147 cuts set
  `STOP_AT=147`, `LS_SECONDS=240`.
* `emit_from_basis.build(k, state_path, outdir)` takes a plan state and calls
  `emit_plan.emit(...)`, which writes **`.kmx`** (text). The verifier's family format is
  decided by `angle_k_0`'s extension — the shipped family is `.kmb`, so the new files
  must be converted: `kickmix.Circuit.from_file(kmx, format='kmx').to_file(kmb,
  format='kmb')` (the verifier's own `circuits.py` does the same at line 265).
* `emit_plan.emit` returns `{product_count, toffoli_count, num_qubits}` — that dict is
  the measurement; no simulation needed for T/Q.

## 3. Why no kernel was run (the actual blocker)

1. **Kaggle script kernels only upload `main.py`.** Verified twice today on
   `qingyu1232`: a second file in the pushed directory is not present at runtime
   (`ModuleNotFoundError: No module named 'fitlib'`, `/kaggle/src/script.py`), even
   with `/kaggle/working`, `/kaggle/src`, `cwd` on `sys.path`. So a 424 KB, ~9 k-line
   compiler port cannot ride along with the script.
2. **Dataset upload is forbidden for this account**: `kaggle datasets create` hung for
   600 s and `kaggle datasets status qingyu1232/qcc-chem-code2-emitter` returns
   **403 Forbidden**. So the "put code2 in a private dataset and mount it" route is
   closed here.
3. **The public source archive is not in the current dataset version**:
   `syed3000/vqcc-own-circuit-portfolio` v13 lists only the 15 circuits + npz + LICENSE/
   NOTICE/SHA256SUMS; its README states the builder sources "remain available in
   dataset version 12". A kernel input pinned to v12 was not attempted (the metadata
   form for a pinned version is not supported by `scripts/kgpu.py`; it would need a
   manual `dataset_sources: syed3000/vqcc-own-circuit-portfolio/versions/12`-style
   entry plus a working mount).

Minimal unblock (one of):
* **push a notebook kernel (`.ipynb`) instead of a script**: `kernel_type: notebook`
  embeds the whole document, so one cell can carry a base64 zip of `code2/`
  (424 KB → ~570 KB base64, within Kaggle's notebook size) that writes it to
  `/kaggle/working` and unzips before importing. This needs no dataset and no new
  account. **Recommended next step.**
* run the build on an account that can create datasets (then `dataset_sources` works),
  or
* mount `syed3000/vqcc-own-circuit-portfolio` **version 12** and inline only the
  60-line `plan_one` + `emit` driver from `compile_basis.py` / `emit_from_basis.py`
  (the rest — planner, minrank, lowbasis, matching, emitter — imports from the
  archive), or
* run the compiler where the port already lives (e.g. the local tree) and only push
  the resulting `.kmb` — but that needs kickmix **simulation-free** use: `emit` builds a
  kickmix circuit and prints counts, which is a static count, yet the task's hard rule
  puts *any* circuit work on Kaggle, so this needs an explicit exception.

## 4. `k0`/`k1` (−31 / −25) — the `windows` generator question

`k0_windows.json` is the only instance of the windowed schedule, and it is a *plan*
artifact, not a derived object: the window list encodes which address windows ANGLE_0
loads in each of its scheduled passes (`compiler/emit_k0.py` consumes it). Nothing in
the restored tree generates it — `compile_loaders.py` needs
`prove_loader_branches.py`, which is not shipped (`CODE2.md` §5). Reversing it from the
shipped `angle_k_0.kmb` gate dump is conceivable (the window boundaries are visible as
the blocks of addresses whose word XORs are applied per segment), but it is a
reconstruction project of the same size as the emitter port, and it shares the same
delivery blocker. Not attempted.

## 5. Verification scope

* Exact: the per-loader algebra (`T = products + 68 + 6`, `products = (525−Σcuts)/2`),
  the shipped column, the stored plan's `sum_cuts = 133 / products = 196` (a loss),
  the port's 145-cut figure (quoted from `CODE2.md` §4), the emission/format mechanics
  read from `emit_plan.emit` and `scoreinfra/circuits.py`.
* **Not run**: no planner, no emit, no Toffoli count of a new circuit, no verifier, no
  submission. Everything above about `264`/`263` is the repo's own plan arithmetic, not
  a fresh measurement.
