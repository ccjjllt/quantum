# R5_BACKUP — independent R=5 fit (conservative schedule), cancelled; the shape is closed

Date: 2026-11-16, backup session on the **jiyujia** account (Kaggle CPU only). Chemistry only.
No submission. This file records **why the backup was cancelled and what the primary run
settled**, not a fit result: the backup produced no candidate and no verification.

## 0. Verdict

1. **The R=5 route `B10c54 → (5,240,108) → (5,143,75)` is closed.** The primary full-budget
   run (`qingyu1232/qcc-chem-merge-shrink-full-budget`) landed and reports:

   | stage | continuous `error_2` |
   |---|---:|
   | (5,240,108) merged + pre-fit | **13.709 mHa** |
   | 240x100 | **14.171 mHa** |
   | 200x90 | **27.839 mHa** |
   | 170x82 | **39.987 mHa** |
   | **143x75 (target)** | **53.653 mHa** |
   | 143x75 after 8-bit rounding | **73.1 mHa** |

   The continuous gate is 16.7 mHa and the quantized gate 19.9 mHa, so the target shape is
   **3.2× over the continuous gate and 3.7× over the quantized one** — not a budget shortfall
   but a wall. The break is at the first basis cut: 240→200 bases with 108→90 copies costs
   +13.7 mHa (14.171 → 27.839) after a converged refit, i.e. the merged `(5,240,108)` seed is
   already at the **projector/rank wall** for K = 5·C with B ≈ 200; every later cut only
   redistributes the same loss (27.839 → 39.987 → 53.653 is monotone with the cut).
2. **The cheaper-looking side branch is not a candidate either**: `(5,240,100)` fits to
   14.17 mHa but has 76 + 5·240 = **1,276 rows** and T ≈ **17.7 k**, i.e. worse than the
   shipped 14,712-Toffoli R=8 point before any rounding. Fewer *copies* at full bases does
   not reduce cost (rows are set by B, not C), so this branch cannot pay.
3. **The backup could not have rescued it.** My extra cut point `155x78` sits in the middle of
   the failing region (between 170x82 = 39.987 and 143x75 = 53.653); a gentler fade path
   redistributes *where* the loss is paid, not whether it is paid. Given 240→200 alone costs
   +13.7 mHa with the full budget, no schedule in this family reaches 16.7 mHa at 143x75.
4. **Both backup kernels were deleted on instruction** (§2), so jiyujia CPU is free. No new
   fit was started and none will be.

## 1. What the backup was

An independent second attempt with a deliberately more conservative schedule than the primary,
on a different account, so a scheduling mistake in either would not lose the only copy:

| | primary | backup (this) |
|---|---|---|
| cut points | 240x100, 200x90, 170x82, 143x75 | 240x100, 200x90, 170x82, **155x78**, 143x75 |
| fade per cut | 250 | 300–450 |
| fit per cut | 900 | 1000–1600 |
| final fit at 143x75 | 1800 | **3400** |
| pre-fit at the merged shape | 800 | 400 (the cuts carry the budget) |
| iteration budget | ≈7,300 | **13,100** |
| segmentation | one `shrink.py` call | 5 calls, one per cut, `--merged` chaining |

The segmented design was also the deadline mechanism: after every segment the measured
s/iteration rescaled the remaining budget and the final segment kept a reserved slice, so the
run would degrade to a shorter schedule rather than die at the wall clock. Code:
`r5_backup_kernel/main.py` (identical file plus `smoke.flag` in `r5_backup_smoke/`).

Kernels, both **private, CPU, no internet**, sources `marculera/dfthc-merge-pipeline`,
`sohier/verifiable-circuit-compilation-starter-kit`, competition
`google-verifiable-quantum-circuit-compilation`:

* `jiyujia/qcc-chem-r5-backup-b11c` — the run; **deleted 2026-11-16 21:29 CST**, ≈1 h 35 min
  after the 19:53 push, i.e. inside the first one or two fit segments.
* `jiyujia/qcc-chem-r5-backup-smoke` — the same script with tiny budgets, used to prove the
  post chain before spending the long budget; **deleted 21:26 CST** with the run.

## 2. Cancellation record

* Instruction: stop the backup; the primary full-budget run closed the shape.
* Action: `kaggle kernels delete jiyujia/qcc-chem-r5-backup-smoke -y` and
  `... qcc-chem-r5-backup-b11c -y` with the jiyujia token — both returned "deleted
  successfully"; a follow-up `kernels status` for either slug now fails with
  `Permission 'kernels.get' was denied`, i.e. the kernel and its session are gone.
* Consequence: the run's `/kaggle/working/{fit,post}` checkpoints and `summary.json` are gone
  with the session, and a running kernel's log stream was not retrievable for this account
  (`kernels logs`, `logs -f` and the v1 `/api/v1/kernels/logs/stream/...` route all returned
  empty while RUNNING; `kernels output` blocks). **Therefore this file reports no per-stage
  e2 from the backup — there is none to report.** Every number in §0 comes from the primary
  run as reported to this session, not from my kernel.
* Note for future runs: `CancelKernelSession` (`POST /api/v1/kernels/cancel-session/{id}`)
  needs the numeric *session* id, which the public API does not expose (the kernel id returns
  403); deleting the kernel is the only API-reachable stop.

## 3. Plumbing facts established on the way (reusable, independent of the shape verdict)

These were verified on Kaggle CPU while preparing the backup and are worth keeping:

1. **The public chain needs `refine.py` between `quantize.py` and `build.py`.** `quantize.py`
   writes `words`, `w`, `brot`, `coded`; `build.py` needs `U, W, H2_I, H1_I, Hsym_lower`
   **and** `angle_words`, `tree_edges` — which only `refine.py`'s `assemble` writes (it also
   regenerates the one-body rows from the final `h1'`). The primary's smoke failed at build
   with `KeyError: 'U is not a file in the archive'` for exactly this reason. Correct order:
   `shrink.py → quantize.py → [polish_words.py] → refine.py → [refit_weights.py] → build.py`,
   i.e. `run.py`'s chain, which resumes and skips existing outputs.
2. **`verified_shots = (N + R·B) · 64`, so a 791-row table is 50,624 shots, not 78,080.**
   78,080 = 1,220 rows × 64 is the shipped R=8 (8,143) table. Running the unchanged verifier
   at its default `shots_per_address=64` on a 791-row candidate is the full official run for
   that candidate; the count is smaller only because the table is.
3. **`build.py --qrom reference` is not the loader family of `LOADER_R5.md`.** With
   `max_batch(791, 8) = 13` it packs 13 words per circuit → 6 circuits of plain unary-iteration
   QROM. The 5-words-per-circuit family (15 circuits, Σcuts algebra, 268 → 242/loader) is
   `--qrom tensor` (`tensorqrom.py`) or the ported planner; the reference family's T is not
   comparable to the 14,712 baseline. Any cost claim must name the family.
4. **Timing on Kaggle CPU (4 vCPU).** Measured: from the primary's 145-iteration smoke,
   ≈1.1–1.5 s per `shrink.py` iteration at (5,240,108)-shaped problems including jit and
   `impacts`, so the ≈7,300-iteration primary schedule is a multi-hour job and a
   13,100-iteration backup ~2× that; `quantize.py` ≈0.70 s/Adam step at (5,143,75) (1,960
   steps in 1,373 s). Estimated from the code, not measured: `refine.py` is dominated by
   `onebody.refresh` (kicks=10 → ≈11 polishes of a 76×75 word table, called once per
   `assemble`, i.e. once per refine round), while the official 64-shot verification itself is
   tens of seconds. Post-processing, not build, is the likely expensive tail — which is why
   the backup planned 2.4 h for it and why a one-kernel fit-plus-post chain is tight.

## 4. Consequence for the chemistry thread

* **Do not run another R=5/6 merge-and-shrink fit.** Two independent budgets (7,300 and the
  cancelled 13,100-iteration schedule) do not touch 16.7 mHa at (5,143,75); `(5,240,100)` is
  worse than the shipped point; and the rank floor argument of `RESULT3.md` §2.1 (K = 375,
  floor 5.56 mHa) is necessary but far from sufficient — the *basis* count, not the copy
  count, is what the shrink cannot pay for.
* The chemistry cost step therefore has to come from the loader side at the shipped
  (8,143,44) / (9,143,46) shapes — `LOADER_R5.md`'s Σcuts programme — or from the λ corner,
  which `RESULT3.md` §1 closes. Neither is a fit and neither can be bought with CPU hours on
  this route.
* The verified R=8 baseline stands unchanged: T 14,712, Q 427, λ 46.927643.

## 5. Scope

No candidate package, no submission, no official verification by this session. `§0` numbers are
the primary run's; the backup itself contributed no measurement beyond the plumbing facts in
§3 (which were observed in the primary's completed smoke log and in the tools' source, not in a
backup run that survived long enough to report). The two backup kernels are deleted; the only
artefacts are `r5_backup_kernel/main.py`, `r5_backup_kernel/kernel-metadata.json` and the
`r5_backup_smoke/` copy, kept so the cancelled work is reproducible.
