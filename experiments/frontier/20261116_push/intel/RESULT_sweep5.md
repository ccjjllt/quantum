# Sweep 03:06 UTC → 03:44 UTC + gap backfill 02:31 → 03:06 — 2026-11-17

Method: `kaggle kernels list -s {qcc,quantum,vqcc} --sort-by dateRun` (first pass
03:31, re-list 03:43:49) + `kaggle datasets list -s {qcc,vqcc,quantum-circuit,verifiable}
--sort-by updated` (03:32, re-list 03:44) + `kaggle competitions leaderboard
google-verifiable-quantum-circuit-compilation --download` (snapshot stamp
`2026-11-17T03:32:23`, 3,233 teams), account qingyu1232. Every downloadable
in-window output pulled with `kaggle kernels output` (largest complete zip 85.6 MB;
one member captured only in part, 97.5 MB of 480 MB, see §2) and every `.kmb`/`.npz`
member hashed with `shasum -a 256`. Local work limited to sha256 + zip-listing +
log/audit-JSON reads + GM arithmetic; **no simulation, no verifier runs, nothing
submitted.** Known set as of sweep4/verify_new4 was NOT re-verified.

## 1. Window table (2026-11-17 03:06 UTC → 03:44 UTC)

| # | item | time (UTC) | kind | verdict |
|---|---|---|---|---|
| 1 | `kawh1111/qcomp-harvest-2813` | 03:24:47 (COMPLETE) | kernel output `submission.zip` 85,597,166 B / 18 members | **known bytes only** (§2) |
| 2 | `wenbodai/qcc-28-1277-public-frontier-verified-end-to-end` | 03:26:37 | kernel output `submission/` tree (18 files, 480 MB nominal) | **known bytes only**, partial capture (§2); kernel deleted/private mid-sweep |
| 3 | datasets (`qcc`/`vqcc`/`quantum-circuit`/`verifiable`, sorted by updated) | — | — | **no in-window dataset.** Newest are `ratnachand/vqcc-verified-public-floor` 02:44:30 and `grantprater/vqcc-dqi-61c8348d-merged-closings` 02:32:15 — both pre-window, both already hash-checked (`ratnachand` in `RESULT_verify_new4.md` §5; `grantprater` in `RESULT_sweep3.md` §1) |
| 4 | public LB top 100 | 03:32:23 | CSV | exactly **one** submission in-window: `varianceofx` **28.14701** at 03:06:05 (rank 124) — below the 28.15083 frontier and equal to its own pre-window 28.14703/28.14704 bundle level; top-30 identical to the 00:55 snapshot apart from pre-window moves (latest 02:49:44). No new public output from varianceofx (its only QCC kernel is the 01:08 cost-model bundle, pre-window) |
| 5 | top-30 teams × public notebooks/datasets | 03:36–03:42 | 51 member handles enumerated (`kernels list --user`, `datasets list --user`) | **no QCC notebooks or datasets in-window.** Only QCC hit is `somejoint/quantum-circuits-24-65-local-gm-chem-refit` (2026-11-04, GM 24.65, far below frontier, pre-window) |

LB anchors (03:32:23 snapshot): **1 aadi_stonks 30.96645** (last sub 02:42:22),
2 Z³C¹oherence 30.96223, 3 Entangled Team 30.28512; gold line rank 16
"Slow and Steady" **28.68633**. Our paper frontier **28.15083 would be rank 79**
(rank-79 score 28.15074 — the 28.15 band is a very tight cluster).
Only in-window LB move: `varianceofx` 03:06:05 → **28.14701** (rank 124), i.e.
its known bundle level, still below the frontier and worth no new bytes.

### Byte-new verdict

**NO NEW BYTES FOUND in the 03:06 → 03:44 window.** Both in-window kernels
repackage already-known circuits; there were no in-window datasets; nothing in
the top 30 of the LB has public output.

## 2. Known-bytes-only (every member hashed)

| source | member | sha256 (full) | size | known as |
|---|---|---|---:|---|
| kawh1111 03:24 (repack of dataset `pramitdas/qcc-public-frontier-28-1277`) | `dqi.kmb` | `66b4f18b85273bdc0b325500c43a810aba2772275b977f371731cfc400a315c2` | 480,411,479 | DQI `66b4f18b` |
| same | `invsqrt.kmb` | `0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b` | 180,382 | invsqrt `0af21cb8` |
| same | `dfthcsos/submission.npz` | `703843d35a722f07b7f833b3a6565c54f00ec5ce4e692f7192593c79728f8ce9` | 1,847,692 | chem `703843d3` |
| same | `dfthcsos/angle_k_0…14.kmb` (15) | `aed6aa7cde8cefae06376546c276208a667a1a402ebfe9e57cb33881868ab089` (k0) … `ab06b98fc22fce8a33b591db9caf73e93d407342a6c0f3d2e2e1416dffffdfd7` (k14) | 415,169 … 362,314 | standard loader family |
| wenbodai 03:26 | `submission/dfthcsos/submission.npz` | `703843d35a722f07b7f833b3a6565c54f00ec5ce4e692f7192593c79728f8ce9` | 1,847,692 | chem `703843d3` |
| wenbodai 03:26 | `submission/dfthcsos/angle_k_0…14.kmb` (15) | same 15 standard-loader hashes as above (`aed6aa7c…` k0, `ab06b98f…` k14) | 415,169 … 362,314 | standard loader family |
| wenbodai 03:26 | `submission/dqi.kmb` | **not fully downloadable** — 97,517,568 B of 480,411,479 captured before the kernel became inaccessible; prefix sha256 `eab0ace262ad5c64ec67bf33f0f9b3173d36dfb71e52a3dc81fdbf269179ff6c` = byte-identical to the same-length prefix of known DQI `66b4f18b` (0 differing bytes over 97.5 MB, `cmp -l`), and total size matches that file exactly | 480,411,479 | DQI `66b4f18b` |

Notes on row 2 of the window table: `wenbodai/…` was reachable for one `kernels
output` call at ~03:32; from 03:33 `kernels status` / `files` / `logs` returned
`Permission 'kernels.get' was denied`, the legacy `/api/v1/kernels/output` URL
returned 403, and by 03:43:49 the kernel no longer appears in any
`kernels list -s qcc|quantum|vqcc` result. Logs and claim lines are therefore
unavailable; the captured bytes above are all we have. Its chem + 15 loaders are
member-identical to `pramitdas/qcc-public-frontier-28-1277` (18:42:27), i.e. the
28.1277 portfolio, and its DQI is size- and prefix-identical to `66b4f18b`; its
`invsqrt.kmb` was never captured (zip order put it after the 480 MB member).

`kawh1111`'s log carries no score claim — only
`wrote /kaggle/working/submission.zip 85597166 / entries 18 / layout OK`.

## 3. Gap backfill 02:31 → 03:06 (uncovered by sweep4, outside the mandated window)

sweep4 closed at 02:31 and this sweep starts at 03:06, so the kernels below were
checked and reported for completeness. **All known bytes / receipt-only, except
two new DQI candidate claims with no downloadable bytes.**

| item | time (UTC) | result |
|---|---|---|
| `grantprater/vqcc-dqi-merged-patches-closings-at-all-49` | 02:33:32 | single output `dqi.kmb` (480 MB nominal). **Not downloaded (200 MB cap) and not hashed.** Its dataset `grantprater/vqcc-dqi-61c8348d-merged-closings` updated 02:32:15 (137,449,876 B) is named for `61c8348d`, and the 23:45 run of this kernel was byte-identical to that file (sweep3 §1) — judged known, flagged unhashed |
| `asteriospanoras/qcc-28-1277-frontier-finer-chemistry-refit` | 02:35:47 | **receipt only** (`receipt.json` 4,809 B + log; no `submission.zip`). Pins `0af21cb8` + `61c8348d` + `f05297b4` + standard 15 loaders — all known. Embedded official JSONs: DQI PASS **348,004,440,260.464** (`value_errors 1`, 102,400 shots, `circuit_sha256 61c8348d…` — the known lost-shot draw of `61c8348d`), chem PASS **294,762,512.8596263** (T 14712, λ_eff 46.92158337179646). No circuit bytes |
| `ratnachand/vqcc-verified-floor-and-circuit-anatomy` | 02:45:38 | already hash-checked, `RESULT_verify_new4.md` §5 — no new bytes |
| `aiokajima/quantum-pramit-281277-reproduction-public` | 02:53:34 | `submission.zip` 49,724,603 B / 18 members: `66b4f18b` (480,411,479) + `0af21cb8` (180,382) + `703843d3` (1,847,692) + standard 15 loaders. Log: 18/18 manifest hashes verified, rebuilt archive, ratios 27.765339 / 70.404698 / 11.384… (28.1277 portfolio). Known bytes |
| `leotang09/vqcc-t7421-submission` | 02:55:17 | `submission.zip` 50,990,328 B / 18 members: `61c8348d` (479,128,630) + `0af21cb8` (180,382) + **`a73b25d2`** (1,847,552) + the **15 SMALL loaders** `ed648708…b4a2d0ce` (129,631–180,436). This is exactly the 28.15083 gate combo repackaged. Log = sha256 manifest + downstream candidate ids `{invsqrt 2237, dqi 2240, dfthcsos 2241}`; no score claim. Known bytes |
| `thomasgamet/quantum-attempt-reset` | 03:00:49 | **receipt-only, two NEW DQI candidate claims, no candidate bytes** — see §3.1 |

### 3.1 `thomasgamet` 03:00 run — two new DQI candidate *claims* (no new bytes obtainable)

Run verified its own pinned portfolio (GM 28.12769670312779 = known
`0af21cb8` + `66b4f18b` + `703843d3`), then ran an exact-factorisation DQI
closing search with full official verification of parent and candidate at
102,400 shots:

| selection | score (official JSON, default salt) | value/phase errors | toffoli | circuit sha256 |
|---|---:|---|---:|---|
| `dqi_quadratic_192` | **346,947,172,543.98676** | 0 / 0 | 367,685.59 | `1b106443d646dcbc3d1e248fd799a5f5daf5e524c282e83f5c4766dd6fe46cad` |
| `dqi_quadratic_400` | **346,750,900,116.7399** | 0 / 0 | 367,477.59 | `f0e646c7d2ea539616b6b47c3ff8c6c3fbafe1561120ce2a481b8b6ba54afb35` |

Receipts also record the chain: parent `66b4f18b` 347,128,304,010.81165 →
`1b106443` 346,947,172,543.98676 → `f0e646c7` 346,750,900,116.7399
(measured fractional cost improvements 0.0522% and 0.0566%,
`estimated_points_if_other_tasks_unchanged` 0.00489 / 0.00531).

**No downloadable candidate bytes.** The kernel's output tree contains only
`pinned_portfolio/{dfthcsos/*, dqi.kmb}` + the 4 stdout files + 2 receipts. The
`pinned_portfolio/dqi.kmb` there is the **parent**: 480,411,479 B with the first
26,214,400 B byte-identical to known `66b4f18b` (`cmp -l`, 0 differing bytes), and
the pinned chem is `703843d3` + standard loaders. The candidate circuits live only
inside the run's `/kaggle/working/submission.zip`, which is not part of the
downloadable output. So these are **claim-only** (unlike sweep4's `a73b25d2`,
these have no bytes to verify at all).

GM with our verified invsqrt/chem legs (refs 2076774.233715 / 24439463583672.93 /
3355599588.3155375; local arithmetic only):

| DQI leg | ratio | GM with `0af21cb8` + `a73b25d2` |
|---|---:|---:|
| frontier `61c8348d` clean (346,413,579,540.4963) | 70.54996 | **28.15082863** |
| `f0e646c7` (new, claim) | 70.48133 | 28.14169726 (−0.00913) |
| `1b106443` (new, claim) | 70.44145 | 28.13638956 (−0.01444) |
| `66b4f18b` (parent) | 70.40470 | 28.13149485 |

## 4. Scoreboard against the three high-value asks

| ask | bar | found in this window | verdict |
|---|---|---|---|
| DQI cost below `61c8348d` clean 346,413,579,540.50 | < 346.414e9 | thomasgamet `1b106443` 346.947e9, `f0e646c7` 346.751e9 (claims, no bytes); all other DQI bytes = known `66b4f18b` / `61c8348d` | **miss** — both new DQI numbers are 0.10–0.15% *worse* |
| chemistry `T < 14,706` | < 14706 | nothing new (`703843d3` T 14712 and `a73b25d2` T 14706 re-served, both known) | **miss** |
| invsqrt cost < 74,797.37 | < 74797.36535717871 | nothing new (only `0af21cb8`) | **miss** |

Scale of a win (local arithmetic, refs above): **+1% on any one leg = GM
28.24530 (+0.09447, ≈ LB rank 41)**; +0.1% = 28.16022. To reach **GM 28.20** the
single-leg bar is DQI ≤ 344,604,649,201, chem ≤ 293,104,546, or invsqrt ≤
74,406.78 — i.e. only a 0.52% DQI gain or 0.52% chem gain is needed, so a 1%-class
find is worth ~0.094 GM. Draw-risk context: `61c8348d`'s known 1-value-error draw
scores 348,004,440,260.464 (reproduced again by asteriospanoras 02:35, §3) and
drops the frontier to GM 28.10787 (−0.0430).

## 5. Notes and corrections

1. **`a73b25d2` hash typo in `RESULT_sweep4.md` §1.** sweep4's string is 63 hex
   chars; the 64-char hash confirmed by `RESULT_verify_new4.md` §1 is correct:
   `a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3`
   (1,847,552 B). Independently re-derived here as a by-product of hashing
   leotang09's 02:55 zip. Use the 64-char form for any pin/manifest.
2. **`wenbodai` kernel vanished mid-window.** Listed (03:26:37) and downloadable at
   03:32, 403 on every metadata endpoint from 03:33, absent from search at 03:43.
   Only the partial capture in §2 exists; `invsqrt.kmb` was never obtained.
3. **`thomasgamet`'s new DQI candidates are unreachable bytes** (§3.1) — do not
   schedule a verification run for `1b106443`/`f0e646c7` unless the author
   publishes them; even if valid they lose to `61c8348d` clean.
4. Unhashed item: `grantprater` 02:33 kernel's 480 MB `dqi.kmb` (200 MB cap).
   Judged `61c8348d` by dataset name/lineage, not by hash.
5. No in-window datasets; no new public notebook from any of the 51 handles in
   the LB top 30; the only in-window LB move (`varianceofx` 28.14701 at 03:06:05)
   is below the frontier and produced no new bytes.

No submission, no package, no verifier runs by this task.

## Addendum — window 03:44 → 04:40 UTC (same day, second pass)

Method: `kaggle kernels list -s {qcc,quantum} --sort-by dateRun` +
`kaggle datasets list -s vqcc --sort-by updated` at ~04:40 UTC (account qingyu1232).

| item | time (UTC) | verdict |
|---|---|---|
| `ozertuu/vqcc-super-sota-verified-portfolio-28-091` | 04:23:40 | re-run of the **28.091** bundle already submitted as ref 58420406 (`8b410e77` + `ccc2ab84` + `f6e12f02`, GM 28.09090). Known bytes; below our frontier by 0.060. |
| `kawh1111/qcomp-harvest-2813` | 03:24:47 | already in §1 (known bytes only) |
| `thomasgamet/quantum-attempt-reset` | 03:00:49 | pre-window, already in the gap backfill |
| `leotang09/vqcc-t7421-submission` | 02:55:17 | pre-window, repack of our own 28.15083 trio (already recorded) |
| `vuhuycong/qa-dar-v46-full-train-20261103` | 04:33:02 | unrelated (QA-DAR training notebook), no QCC output |
| datasets (`vqcc`, `qcc`, `quantum-circuit`, `verifiable`) | — | **no dataset newer than `ratnachand/vqcc-verified-public-floor` 02:44:30** — nothing in-window |

**Verdict: no byte-new file.** The three frontier targets (DQI < 346.414e9 clean,
chem T < 14,706, invsqrt < 74,797.37) all still stand unmatched, and the only in-window
activity is a competitor re-running a bundle 0.060 GM below ours.
