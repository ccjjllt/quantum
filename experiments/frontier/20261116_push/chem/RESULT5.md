# RESULT5 — the delta-helper emitter: implemented, measured, negative

Date: 2026-11-16 (late session). Chemistry only. Task: unblock k9/k14 via the
missing emitter feature, verify byte-level T reduction, target
`cost <= 294,762,300` (≈ `>= 28.09490` GM). No submission. **No Kaggle run was
made: nothing passed the local T gate, so there was no candidate to verify**
(same policy as `RESULT4.md` §8). All work is classical numpy/GF(2) plus
*kickmix static counts* (no simulation); the one local simulation attempted
was an 11-address smoke test that caught the fork's invalid output.

## 0. Verdict

1. **The brief's premise is refuted on both counts.** The stored plans are not
   "−1/−3 wins waiting for an emitter": they are 145-cut plans (190 products)
   against shipped 147-cut (k9: 189) and 143-cut (k14: 191) plans — i.e. k9 is
   **+1 by plan alone**, k14 is **−1 by plan alone**.
2. **The missing emitter feature is real but costs ANDs, not CXs.** The
   delta-helper `D = Hp^Hc` (308 nonzero entries for k9/k10/k14) is low-only,
   and every nonzero X word is a **single degree-2 low monomial whose only
   representation is its own b7 qubit** (`delta_cost.py` §2/3). Adding it needs
   a fresh addr-only AND (+1T each); CX-only handling is impossible (proved by
   exhaustion of control sources, §3), reset breaks reversibility, spare-copy
   leaves the workspace dirty.
3. **Correct emission of the stored plans is a loss on all four loaders**:
   k9 266 (+2), k10 268 (+3), k12 269 (+4), k14 270 (+4) vs shipped
   264/265/265/266. The 68-high offset that marculera uses is **impossible on
   our k14 plan** (needed high-rank 77 = full space, §4).
4. Consequence: **no T reduction, no cost change, gate not met, no step 2**
   (conditional on step 1). Chemistry stays at **294,762,632.08**
   (`T 14,712`, `Q 427`, `lambda_eff 46.92160235`). The +80 T headroom of
   `CODE2.md` §1 remains behind 147+-cut plans that do not exist, not behind
   the emitter.

## 1. What the brief claimed vs what is on disk

| loader | brief claim | stored plan | shipped | plan-only delta |
|---|---|---|---|---|
| k9 | −1 | 145 cuts / 190 prod (`basis_plan_k9.json`) | 264 (189 prod) | **+1** |
| k14 | −3 | 145 cuts / 190 prod (`basis_plan_k14.json`) | 266 (191 prod) | −1 |
| k10 | tie | 145 cuts / 190 prod | 265 (190 prod) | 0 |
| k12 | tie | 145 cuts / 190 prod | 265 (190 prod) | 0 |

Static recount of the shipped build (kickmix `operation_statistics`, no
simulation) confirms the shipped column byte-exactly:
`[294,288,269,269,263×5,264,265,265,265,265,266]`, qubits
`[128,126,125×7,126,126,125,125,125,126]`, total `T = 14,712`.

## 2. What was implemented (and why it is marked INVALID)

`code2/compiler/emit_delta.py`: fork of `emit_plan.emit` with a per-batch
helper convention — `X_pre = Hp^slow` before products, `X_post = slow^Hc`
after, replacing `high_helper_ops`. Zero new ANDs/qubits by construction.
It emits k9/k10/k12/k14 without assertion failures (190 prod + 69 + 6 = 265).

It is INVALID: every nonzero X word needs `CX q{z} q{z}` (control == target),
which kickmix rejects at parse (`smoke_dc.py` caught:
`CX q18 q18`, `CX q34 q34`, `CX q50 q50`). The file header says so; the
`build_dc/` outputs were deleted. The smoke harness `code2/smoke_dc.py`
(11 addresses: loader forward check + selection-preserved + workspace-clean)
is kept — it is what caught the bug.

## 3. Why CX-only handling is impossible (measured)

`code2/delta_cost.py` (single repro script, numpy only) establishes:

1. **D is low-only.** `D = Hp^Hc` (308 entries, k9/k10/k14) separates as
   `lowD(t)^highD(h)` with `highD = 0` (§1). Affected words: k9 {w0}, k10
   {w4}, k14 {w2} — one popcount-4 low truth each. k11–13 have `D = 0` but
   per-batch tables (616 diffs vs batch 0).
2. **Each X word is one degree-2 monomial with a singleton SELF mask**
   (k9-post w0 = mono 3 → `[q18]`; k14-pre w0/w4 = mono 3/10 → `[q18]/[q50]`;
   k14-post w0/w2/w4 = mono 3/6/10 → self; k10/k12 likewise, §2/3).
3. **No valid zero-cost control exists.** The monomial (e.g. `t0t1`) is held by
   no correct-valued qubit: addr bits are degree-1, the hi-cache is high-only,
   the lo-cache computes degree-3+ truths, and the only live holder is the
   target itself (wrong value at X_pre time / self at X_post time). The shipped
   6-AND synth provably needs its helper reads (`CCX q0 q34`, `CCX q0 q52`;
   reps reference q18/26/34/42/50 — instrumented in §3), so b7 must equal the
   synth table during products: the prefix fix is unavoidable when `Hp≠slow`.
   Fresh addr-only ANDs (+1T each) are the only clean+unitary source.
4. **Escapes refuted.** `R`-reset: non-unitary, breaks the reverse pass (and
   `R` semantics on used qubits are unverified). Spare-copy: the saved value
   cannot be uncomputed (source overwritten) → dirty workspace → verifier
   FAIL. Per-batch synth table: `Hp` spans are 9/8/8 (k10/k12/k14, need 10).

## 4. The 68-high offset is impossible on our k14 plan

Needed high functions (190 product high-columns + 35 ah-correction truths,
padded words so the h=76 slice is in-span) have **rank 77 = the full space**
(product cols alone: 76). A 68-AND cache spans ≤ 76 dims → cannot cover.
Marculera's 68+7 split works only with their 147-cut plans (which spare a
high monomial); ours needs all 69 (`CODE2.md` §4 exact check, confirmed).

## 5. Correct-emission cost table (prefix ANDs + post ANDs)

Each nonzero X word = 1 addr-only AND into a reused spare (+1 qubit, ≤ 127 ≤
128 cap), MBU-uncomputed. No other change (products/cache/ah/al identical).

| k | shipped | plan prod | prefix+post ANDs | correct T | delta |
|---|---:|---:|---:|---:|---:|
| 9 | 264 | 190 | 0+1 | 266 | **+2** |
| 10 | 265 | 190 | 1+2 | 268 | **+3** |
| 12 | 265 | 190 | 2+2 | 269 | **+4** |
| 14 | 266 | 190 | 2+3 | 270 | **+4** |

Net accounting vs the brief's "+2T per touched loader" clause: our toolchain
adds no overhead of its own here (same 69+6 cache, +1 reusable spare qubit);
the +2–4 T is the helper tax itself (prefix+post ANDs), on top of plans that
are already 0–1 products short of shipped (k9 is a full product behind before
the helper is even considered). A touched loader must therefore emit below its
shipped T to win; every correct emission above is at or above shipped, by
+2 (k9), +3 (k10), +4 (k12, k14). No loader qualifies — k14's plan-only −1
becomes +4 once correctly emitted.

## 6. Step 2 not attempted

Conditional on step 1 succeeding; it did not. For the record: k10/k12 are ties
at best (now losses, §5); k0 needs the unshipped window-schedule generator
(`CODE2.md` §5b); k1's best plan is 85 cuts vs 99 shipped (+14T loss,
`CODE2.md` §9). Nothing in step 2 can pass the gate either.

## 7. e1/e2/E_gap, cost, kernels

*Unchanged*: no new words/weights/package exist. `e1 19.999998`,
`e2 19.9999985`, `E_gap 3.9148980015`, `lambda_eff 46.92160235`,
cost **294,762,632.08** (frozen point bdae290f). Target `<= 294,762,300`
not met (shortfall: the full 332.08, i.e. no T reduction of any size).
*No new kernels*: no candidate passed the local T gate, so the unchanged
official verifier (78,080 shots, default + 2 salts) was correctly not run.
Existing kernel refs: `qingyu1232/qcc-chem-r5-loader-verify`
(single-loader correctness pattern reused by `smoke_dc.py`),
`qingyu1232/qcc-chem-t-decomposition-and-loader-slack` (baseline PASS).

## 8. Files

* `code2/delta_cost.py` — the five decisive measurements, one script.
* `code2/smoke_dc.py` — 11-address single-loader smoke harness (caught the
  self-CX bug; full 1,232-address sweep intentionally left for Kaggle).
* `code2/compiler/emit_delta.py` — INVALID fork, kept as a failure record.
* `code2/emit_DC_from_basis.py` — driver for the invalid fork (kept with it).
* Deleted: `code2/build_dc/` (invalid circuits containing `CX q{z} q{z}`).

## 9. Recommendation (unchanged from `RESULT.md` §9)

Freeze chemistry at 294,762,632.08. The loader headroom is behind 147+-cut
plans (none on disk, none found in-repo) *multiplied* by a +1–5 AND helper
tax per loader — not behind a missing CX-only emitter trick. Direct remaining
effort at `invsqrt`/`dqi`.
