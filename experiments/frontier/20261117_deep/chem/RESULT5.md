# RESULT5 — k2/k3 loader rebuild, and the offline-packed compiler that made it runnable

Date: 2026-11-17. Chemistry only. Local work = git restore + zip/base64 packing of the
compiler port (**no kickmix, no simulation, no verifier locally**). All circuit work,
word recovery and the official verifier run are on the Kaggle CPU kernel in §4.

Baseline `a73b25d2`: 15 loaders/pass = `292, 287, 269, 269, 263×5, 264, 265×4, 266`,
T 14,706, Q 427, λ_eff 46.921716818, cost 294,643,137.73, GM 28.15083.

## 0. What this round adds

`RESULT4.md` recorded that the −6/−5 Toffoli k2/k3 win existed arithmetically but could
not be *run*, because a Kaggle **script** kernel uploads only `main.py` and this
account cannot create datasets (403). That blocker is now solved:

> the 63-file, 249,187-byte `code2/` port is packed as a **base64 zip literal inside
> `main.py`** (332,252 chars; `main.py` = 358 KB), unpacked at runtime into `/tmp/work`
> and put on `sys.path`. `kaggle kernels push` uploads only `code_file`, so this is the
> whole compiler on one script. No notebook, no dataset, no new account.

The exact arithmetic being targeted (unchanged from `RESULT4.md` §1):

| loader | T | products | Σcuts | high | low |
|---|---:|---:|---:|---:|---:|
| k2, k3 shipped | 269 | 195 | 135 | 68 | 6 |
| plan family's best on this table (`CODE2.md` §4) | **264** | 190 | **145** | 68 | 6 |
| family floor (`CODE2.md` §0.3) | 263 | 189 | 147 | 68 | 6 |

So `−5 per loader` → `−10 T/pass` → `−20 T` → cost ×0.998640 → **GM +0.0127**
(28.15083 → 28.1635). The stored `basis_plan_k2.json` is useless (133 cuts → 270, a
loss), so the plan must be re-found with `plan_one` (`STOP_AT = 147`,
`LS_SECONDS = 200`).

## 1. Kernel design (one script, one run)

```
1  unpack code2/ from the embedded zip; put compiler/ on sys.path
2  locate the shipped chem family: every /kaggle/input/**/submission.npz that has
   angle_k_0.kmb and angle_k_14.kmb; static per-loader counts via
   scoreinfra.circuits.circuit_costs; keep the family whose sum is closest to 4,022
3  recover the word table from the SHIPPED circuits with the official
   scoreinfra.circuits.recover_words_from_circuits(circuits, num_vectors=76+8*143,
   num_angles=75, seed=12345)  -> (1220, 75) words + angles_toffoli (simulation, kernel only)
4  for k in (2,3): compile_basis.compile_one(W, k, ..., seeds=(7,8,9)) with
   prove_one stubbed (the proof harness is not in the tree) -> plan_one -> 145..147 cuts
   -> emit .kmx -> read back, static max_magic, convert to .kmb with
   kickmix.Circuit.from_file(...,'kmx').to_file(...,'kmb')
5  assemble pkg/dfthcsos = shipped submission.npz + 13 shipped loaders + new k2/k3,
   print the per-k static Toffoli table and sha256 of all 17 members, then run the
   UNMODIFIED official verifiers/dfthcsos/verify.py (78,080 shots) as a subprocess
```

Nothing is submitted from the kernel; the package and the hash list are the deliverable.

## 2. Why the emitter is expected to work for k2/k3

`CODE2.md` §5: batches **0–8** are covered by the shipped emitter; the un-emittable
ones are k9–k14 (different `bit7 XOR bit6` helper convention for 9/10/14, six-AND
low-cache independence failing for 11–13). k2/k3 sit inside the supported set, and
`compile_one` also solves the off-domain padding slice (`solve_padding`) so the
padding rows are literal.

## 3. Decision rules

| measured result | verdict |
|---|---|
| k2 = k3 = 264, verify PASS, `angles_toffoli = 4,012`/pass (T = 14,686) | deliver: ship the 3 replaced members |
| k2 = k3 = 263 (147 cuts found), T = 14,682 | deliver, better |
| only one of k2/k3 improves | deliver the single replacement (−10 T) |
| both fail to beat 269, or verify FAILs | record the failure + minimal counter-example |

Expected verifier signature if it passes: `error_1 19.999998 mHa`, `error_2 19.9999997
mHa`, λ_eff 46.9217168 unchanged, Q 427 unchanged, `angles_toffoli` = 2·(new sum).

## 4. Kernel and measured output

`qingyu1232/qcc-chem-k2-k3-loader-rebuild` (CPU only, `enable_gpu=false`,
`enable_tpu=false`), pushed 2026-11-17, inputs: competition data +
`marculera/dfthc-c44-build` + `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`.

**Measured output: §5 below, filled only from the kernel log. Nothing assumed.**

## 5. Measured (kernel `qingyu1232/qcc-chem-k2-k3-loader-rebuild`, COMPLETE)

### 5.1 The packing solution works

The kernel unpacked `code2/` from the embedded base64 (63 files) and imported
`compile_basis`, `planner`, `minrank`, `lowbasis`, `extract_matching`, `emit_plan`
straight from `/tmp/work`. **A 358 KB `main.py` pushes and runs.** That blocker from
`RESULT4.md` §3 is closed.

### 5.2 Two independent negatives (both measured, neither is the k2/k3 verdict)

**(a) The right table was not mounted.** Only one chemical family was visible to the
glob: `/kaggle/input/datasets/marculera/dfthc-c44-build` (static per-loader
`[294, 288, 265, 265, 265, 265, 266, 269, 269, 263×5, 264]`, sum **4,025**). The
`kernel_sources` mount of `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`
did not surface a `submission.npz` + `angle_k_*.kmb` pair, so the target family
(`a73b25d2`, 4,022, k2/k3 = 269) was **not** the one planned on. k2/k3 also differ in
position/values between the two tables, so the run below is on the wrong words.

**(b) Word recovery from the circuits failed at the official seed.**
`recover_words_from_circuits(...)` raised `ANGLE_2: uncorrected phase (measurement
kickback)` at both `initial_seed(submission_sha256(...))` and seed 0. Planning therefore
used the npz's own `angle_words` (1220, 75) — legitimate for planning, and the final
verifier would re-derive and reject a mismatch loudly, but it means the recovery path
is unproven and should be debugged (it is also what `verify.py` itself does, so a
package that passes will have exercised it).

### 5.3 The planner found no plan for k2 or k3 in the budget

```
k2   seed 7: full [31, 31, 31, 31, 31]  no perfect pairing on the descent path (692 s)
     compile_one -> None
k3   seed 7: full [31, 31, 31, 31, 31]  no perfect pairing on the descent path (764 s)
     compile_one -> None
k2/k3 .kmb missing -> no package, no verifier
```

`plan_one` broke out of the seed loop after the first seed (its `time_limit=600` is
per loader, and one seed costs ~700 s), so only **one** of the three requested seeds was
ever tried, with `generic=False`. Result: **no emitted circuit, no Toffoli count, no
verifier run, no package, no submission.**

### 5.4 What this does and does not settle

* Does **not** refute the k2/k3 win: the target table was not mounted, and 1 seed of 3
  was tried. `RESULT4.md`'s arithmetic (269 → 264 at 145 cuts) is untouched.
* Does show the search is **expensive per seed** (~700 s) and that rank-74 + 31-dim
  blocks with this descent path yields no perfect pairing for these loaders on the
  marculera table — consistent with `CODE2.md` §4 ("at most 145 cuts … a tie or a loss,
  never a win").
* Next attempt should: (i) mount the actual `a73b25d2` family (explicit dataset or the
  exact maoxin kernel output path — verify with a directory listing first), (ii) run
  `plan_one` with `time_limit=3–6 h`, `seeds=(7,8,9,11,13)` and `generic=True` on the
  later attempts, and `STOP_AT=147`; (iii) if the best is 145 cuts, expect **264**
  (`−5`) per loader, i.e. `−20 T` and GM +0.0127, and ship that instead of chasing 263.

## 6. Verification scope

* Measured on Kaggle CPU only: the family census (static `max_magic` per loader), the
  word-recovery failure, the planner trajectories and the absence of a plan.
* **Not measured**: any new circuit's Toffoli count, any verifier run, any sha256 list.
  No package was produced and nothing was submitted.
