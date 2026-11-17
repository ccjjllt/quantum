# RESULT6 — k2/k3 loader emit on the shipped table: planner cannot find a plan in budget

Date 2026-11-17. Kernel `qingyu1232/qcc-chem-emit-k2k3` v1 **COMPLETE** (Kaggle CPU).
This is the *independent* attempt that removed both blockers reported in `RESULT5.md`:
the compiler port was carried inline as a base64 zip (script kernel is enough) and the
**shipped** word table was read straight from the shipped `submission.npz`'s own
`angle_words` (no `recover_words_from_circuits`, no simulation of the family).

## 0. What worked

```
[11:23:48] port at /tmp/work/code2 files 31            ← base64 zip decoded, imports OK
[11:23:48] shipped zip: /kaggle/input/notebooks/maoxin123/qcc-v27-.../submission.zip
[11:23:50] angle_words (1220, 75) npz .../dfthcsos/submission.npz
[12:11:53] shipped loaders found: 15
```
So the *packaging* blocker is solved for good: a Kaggle **script** kernel can carry the
whole `code2` port inline (`main.py` = 133,864 B) and can read the exact 4,022-Toffoli
table (`a73b25d2`, `angle_words (1220,75)`, k2/k3 = 269).

## 1. What failed (decisive for the budget, not a proof)

```
k2  seed 7: full [31,31,31,31,31] no perfect pairing on the descent path (692 s)
    seed 8: no rank-74 basis found (1346 s)
    → planner found nothing
k3  seed 7: ... (765 s)
    seed 8: no rank-74 basis found (1536 s)
    → planner found nothing
```

`compile_basis.plan_one(target, seeds=(7,8,9), trials=60, time_limit=900)` with
`STOP_AT=145`, `LS_SECONDS=120` could not reach a perfect pairing for either loader on
the shipped table. The shipped `basis_plan_k2.json` (133 cuts → 196 products → 270) is
therefore not superseded: **no cheaper k2/k3 loader was produced this round**, and
nothing was assembled or verified (the kernel's own guard skipped the verifier).

## 2. What this changes

- The `−10 T/pass = −20 T = +0.0127 GM` (k2/k3 → 264) is **not reachable with this
  planner in a 15-minute budget**. The CODE2 §4 "190 products" result was obtained on a
  *different* basis/loader, not on k2/k3 of this table.
- The recommended next attempt (recorded, not run) is the same call with
  `time_limit=3–6 h`, `seeds=(7,8,9,11,13)`, `generic=True` and `STOP_AT=147`; the
  packaging and table-access parts are now proven, so only planner time is missing.
- Chemistry therefore stays at **T 14,706 / cost 294,643,137.73** for this round.

## 3. Scope

All numbers above are printed by the kernel; no verifier run happened (nothing to
verify), nothing was submitted. The base64-inline technique is the reusable result.

## 4. Long-budget run left in flight

`qingyu1232/qcc-chem-emit-k2k3` **v2** re-runs the same, self-contained kernel with
`time_limit=5400` per loader, `seeds=(7,8,9,11,13)`, `trials=120`, `LS_SECONDS=600`
and a fixed competition-data locator (`parents[1..3]`), so a full plan has ~6× the
budget that failed above. If it finds a plan it prints `COMPILED` with
`toffoli_count`, converts `.kmx → .kmb`, assembles `dfthcsos/` (npz + 13 shipped +
2 new) and runs the unchanged official verifier (78,080 shots) in the same kernel.

Gate for the next submission slot (UTC 00:00 reset): chemistry `toffoli_count ≤ 14,696`
and PASS; then rebuild the 18-member manifest with
`experiments/frontier/20261117_deep/integration/make_members.py`, regenerate
`main.py` with `make_main.py --min-gm 28.15094`, push the integrator, and submit.
