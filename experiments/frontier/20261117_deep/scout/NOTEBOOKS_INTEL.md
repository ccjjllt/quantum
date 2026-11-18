# Notebook + forum intel sweep — 2026-11-17 (read-only)

Scope: mine the competition's **public notebooks (code + cell outputs)** and the
**discussion forum** for structural tricks we have not found. This is the first sweep of
that surface (previous sweeps mined *datasets* only; see `RESULT_20261117.md`).

**Nothing was run, simulated, pushed or submitted.** No circuit was loaded into a
simulator, no verifier was invoked, nothing was written to Kaggle. Work done: the Kaggle
CLI's read endpoints (`kernels list/pull`, `competitions topics list/topic-messages`,
`datasets files/download -f`), reads of the *local copy* of the official verifier source
(`data/competition/verifiers/…`, static text), and plain arithmetic. Publications pulled
to scratch space only (`$TMPDIR/opencode/qcc_nb/`), never into the repo.

---

## 0. Verdict

> **FOUND: invsqrt `563d0583`, cost 74,560.91, source `maoxin123/qcc-28-17-4-022-toffoli-chemistry-loaders` (2026-11-17 12:16 UTC).**
> 44 qubits, C = 1,694.5661 vs our 1,699.9401 → **−236.46 (−0.316 %)** on the invsqrt
> leg → **GM 28.150932 → 28.180659 (+0.029727)**.
>
> **FOUND (already reported by the dataset scout): chem `submission.npz` `703843d3`, 294,642,299.7630 vs our 294,643,137.7336, −837.97 (−0.000284 %) → +0.0000267 GM.**
>
> **No cheaper DQI exists anywhere public**: the best is `575b043f` = **346,409,762,293**
> (890 Q, T 367,116.05, zero-error draw) — *that is our own DQI*. Every sub-890-qubit
> public DQI is 4–143 % dearer; every 890-qubit public DQI is ≥ 347.1e9 on a one-draw
> basis and ≥ 347.88e9 on the 48-draw expected basis.
>
> **No sub-44-qubit invsqrt, no sub-427-qubit competitive chemistry, no chemistry below
> T = 14,706** exists in the public record (551-circuit manifest + forum).

So: **−0.32 % on one leg**, everything else is at parity with the public frontier. The
public frontier's best-per-task composite is **28.180686** (arithmetic on re-verified
costs); the leader is at 31.42723, i.e. **10 % of GM (1.39× in the cost product) sits in
private work that no public notebook or forum post discloses.**

---

## 1. What was inspected

### 1.1 Notebooks (pulled source + markdown; full list in §9)

| # | ref | last run (UTC) | reported score | what it contains |
|---|---|---|---|---|
| N1 | `maoxin123/qcc-28-17-4-022-toffoli-chemistry-loaders` | 2026-11-17 12:16 | local GM **28.17402** | **invsqrt `563d0583` embedded (base64+zlib, sha pinned) = 74,560.91**; chem 15 loaders at 4,022 T/pass + own weights = 294,643,137.73 (T 14,706, Q 427, λ_eff 46.9217168); DQI `957d6733` (890 Q, 346,654,664,786 clean draw) |
| N2 | `ahoirg/qcc-reproducible-circuit-portfolio` | 2026-11-17 14:11 | expected GM **28.1740** | independent re-verification of `563d0583` (**74,560.91, "re-verified here", default salt, 200,540,928 shots**) and of chem `703843d3` (**294,642,299.76, re-verified here**); DQI not re-run |
| N3 | `ghazarosbarseghyan91/vqcc-28-15096-best-per-task` | 2026-11-17 13:27 | **28.15096** (LB sub 58469117) | the 28.15096 portfolio: `0af21cb8` (74,797.40) + `575b043f` (3.46410e11) + chem `703843d3` (294,642,299.76); one DQI value error at salt `notebook-verification` → 28.10799 |
| N4 | `ratnachand/vqcc-verified-floor-and-circuit-anatomy` | 2026-11-17 08:47 | 28.15096 | same floor; **circuit anatomy**: invsqrt 44 Q peak uses all 22 scratch wires ⇒ "qubit re-allocation cannot shrink it further"; DQI undo pass is not a mirror; chem loader structure (bit7 = bit6 ⊕ fixed low-bit product; "coded" bit 0; 654 low-bit monomials where a generic table needs 470 ⇒ a generic compiler needs ~25 % more ANDs) |
| N5 | `asteriospanoras/qcc-28-15096-frontier-finer-chemistry-refit` | 2026-11-17 10:42 | 28.15096 | re-verifies the three files; refit toolkit in `qcc-circuit-atlas` |
| N6 | `alexchilton/28-15-lb-which-circuits-survive-private-salt` | 2026-11-17 13:35 | 28.15 | ships `563d0583` + `575b043f` + `703843d3`; **8-salt study table** (invsqrt `0af21cb8` 8/8, thinnest margin 0.9995605646; `563d0583` **not** in the salt study); best-public table; 30-odd nulls |
| N7 | `atakanaldemir/qcc-shared-products-and-controlled-refits` | 2026-11-17 13:32 | — | hybrid `563d0583` + own 703843d3 + `575b043f`; "our703843 weights beat the source weights by 837.97054 cost units" |
| N8 | `atakanaldemir/qcc-terminal-readout-and-phase-folds` | 2026-11-16 21:54 | — | DQI `eea2d627` (890 Q, ≈414 fewer T than base) + 14 retained products; ships chem `703843d3` |
| N9 | `grantprater/vqcc-dqi-merged-patches-closings-at-all-49` | 2026-11-17 01:37 | 28.14703 | `61c8348d` (890 Q, 367,993 static) and `575b043f` (367,989 static, ≈346,409.8e6 clean); **caveat**: the 890 line loses ~0.33 shots/draw (13/39), every lost input also fails earlier files of the line |
| N10 | `manwithacat/vqcc-hedge-wizardry-notebook` (v32) | 2026-11-17 | — | HW-29 `957d6733` = 890 Q, 367,375.47 mean T, 48-draw expected **3.474075e11**; full **technique index** (§7.1); negative-results index |
| N11 | `mizeroluckygall/quantum-circuits-28-17-stack-new-44q-invsqrt` | 2026-11-17 13:36 | 28.17402 / 28.13102 | walkthrough of N1; source run drew one DQI failure |
| N12 | `vumaniacom/qcc-verified-portfolio-and-where-the-gap-to-32-is` | 2026-11-17 09:06 | 28.14515 | **gap arithmetic**: "only chemistry has a priced lever: 219 M → 31.07, 242 M → 30.06, 269 M → 29.0; DQI and invsqrt micro-levers exhausted at 0.01–0.1 %" |
| N13 | `vaibhavp747/dfthcsos-why-c44-is-hard-to-beat` | — | — | C44 is a KKT point (residual 0.3 %); (8,120,44) levels at ~30 mHa; reproduces the official `T = 2·per_pass + h["toffoli"]`, `Q = h["persistent"] + J·brot + max(h["temporary"], s-1)` |
| N14 | `hirokikanotmc/invsqrt-removing-166-toffolis-that-never-fire` | — | (on the **reference** 260-Q circuit) | constant-propagation deleting `CCX` with a statically-0 control: 7,735 → 7,569 T, 2,076,774 → 2,033,614. Irrelevant to our 44 Q file, but a valid pass to run on anything new |
| N15 | `davidpiln/vqcc-sat-certificates-and-dqi-failure-classes` | — | — | SAT/LRAT certificates: **no 1-gate local improvement in 558 short windows** of the invsqrt pick |
| N16 | `atakanaldemir/qcc-early-measurement-and-domain-aware-inverse` | — | 25.09 (62 Q era) | domain-aware deletion of one CSWAP on the 62-Q line; the technique that later produced the 44-Q line |
| N17 | `harshitsama/quantum-notebook-score-claims` | — | — | only 26/276 notebook titles carry a score; titles are **unverified** claims |
| N18 | `arzarei/…`, `evgendvorkin/…deep-eda`, `kirilltym/*-audit`, `boristown/…`, `marculera/df-thc-11.38x`, `junthewise/…`, `iwanttorungemma9b/…evidence`, `davidpiln/what-didn-t-work`, `avazaku/*888-qubit-dqi` | — | — | read for claims; all either superseded, or restate the same frontier, or are 2026-10-3x era (888-Q DQI at 398.7e9, etc.) |

### 1.2 Forum (all topics on the competition, 6 pages, 2026-10-23 → 2026-11-17)

Every topic title was read; 20 topics were read in full. The load-bearing ones:

| # | topic | date | content that matters |
|---|---|---|---|
| F1 | **759820** "27.29 → 28.09 in three days … seven ideas that didn't work" | 11-17 | DQI key-equation stage = 87.6 % of Toffolis, scan at its 11 T/point floor; GF(2^36) nodes +48 k T; chem loader re-plan k9–k14: k10 floor 190 vs current 189; **every public 14,712-T chem refit sits 1.5e-9 Ha inside the e1/e2/E_gap limits** |
| F2 | **753633** "dfthcsos: why λ_eff can't go much below ~46.8" | 10-28 | proof from the verifier's own formulas: at the gap floor `λ_eff ≥ 46.79`; "chemistry gains have to come from T × Q, not λ_eff" |
| F3 | **753185** "What didn't work: 30-odd measured nulls" (+11 comments) | 10-27 | chem: brot 7 = 349.7 mHa, brot 6 = 794.5; every fit at Λ 290–308; **Eckart–Young floors R·C ≥ 290 / 307 / 330 for 20 / 15 / 10 mHa**; DQI: 888 Q from three edits passes but 4.759e11 vs 4.486e11 at 889; **R floor 1.1913 at 0 errors/102,400**; invsqrt: dropping 1/2/3 rotations → worst error/tol 1.354/2.214/3.937 |
| F4 | **757030** "Open problems we are stuck on" | 11-08 | loader ≈ 2√(mL) bound, public loaders close to it; invsqrt "one qubit ≈ 25 Toffolis" (62-Q era); CSWAP-shifter SAT problem |
| F5 | **755302** "Is resetting workspace with R allowed in place of uncomputation?" | 11-03 | **unanswered by the hosts.** Do not build on it |
| F6 | **755427** "Final evaluation scope" | 11-03 | 15 votes, **no host answer**. ANGLE_k is only checked on the reachable forward/reverse chain, and the README says passing does not prove arbitrary-target XOR |
| F7 | **752344** "dqi ~8e-5 phase errors" | 10-24 | **Tanuj Khattar (host side, Qualtran)**: the residual is the decoder's own bug; gives the exact `CCX/CCZ/HMR + CZ if b0` identity, i.e. MBUC with a conditioned Clifford correction is a *sanctioned, zero-Toffoli* uncompute |
| F8 | **753424** "Reading DQI leaderboard scores" | 10-28 | the DQI draw is seeded from **circuit hash + salt**; a byte change re-rolls the public draw; 877/889-Q decoders fail ~1/100,000 per shot |
| F9 | **751951** "Checks the metric runs that the standalone verifiers don't" | 10-23 | exactly one file per task; `angle_k_0..n-1` contiguous; named registers; npz float/little-endian; **MAX_QUBIT_OR_BIT_ID = 2^30/1536 = 699,050** |
| F10 | **759048** "rank-173 decomposition of (H·D, H_hi·D²) over GF(2^24)" | 11-13 | 176 → 173 products per block, −546 static T over 182 blocks (**0.14 %**), but **only on the older 392 k-family**; "the newest family's 1,376 GF(2^24) products each act on their own operands, so the pair blocks do not exist" |
| F11 | **756476** "Two exact finite-field multiplication complexities" | 11-06 | **μ₄(6) = 14** (asymmetric included, Lean 4 proof) ⇒ the GF(4)^6 tower for GF(2^12) needs 3·14 = 42 products and cannot be beaten in that structure; a global rank < 42 is still open (only lower bounds exist). Closes the best-known DQI multiplier tower at 42 |
| F12 | **759459** "Open tooling for agents" | 11-15 | the public tool inventory we could use: `qhdl peak/runs/idle/retain/measure-first --apply/measure-out`, `qrom-plan`, `dfthc-refit`, `loader checker`, `kickmix-engine` |
| F13 | 759655 / 759435 / 758678 / 757363 / 756824 | 11-07…11-16 | RezOps briefings: weekly frontier tables; "the leader is 10 % above the public line, and the leaderboard still does not tell which task that gap sits in" |
| F14 | 757522 "Chemistry ANGLE XOR contract and reachable input states" | 11-09 | an accepted packet is correct only on reachable states; **no host ruling** (5 comments, unanswered) |

### 1.3 The two public indexes that make the search exhaustive

* `manwithacat/vqcc-apache-public-circuits` → `manifest.csv`, **551 credited circuits**
  (348 chemistry / 102 DQI / 101 invsqrt), snapshot 2026-11-16 17:46 UTC, with
  `qubits`, `local_task_score`, `T_total`, `Q_total`, `lambda_eff`, `R/B/C/J/brot`,
  `dqi_expected_cost` per row. Downloaded (604 kB) and queried.
* `manwithacat/vqcc-chemistry-negative-results` → `ledger.csv`, **278 closed-lever cards**
  with numbers and kill conditions. Downloaded (278 kB) and queried.

Both are Apache-2.0 public datasets announced on the forum; they are the community's own
answer to "what has already been tried", and they close most of the hypotheses a
notebook/forum sweep would otherwise raise (§6).

---

## 2. The public frontier, exactly (2026-11-17 ~14:00 UTC)

Cost models as in the official verifiers (re-read locally, see §5):

* invsqrt `= Q · (mean Toffoli + t_count/4)`
* DQI `= R(eps⁺) · Q² · mean Toffoli`
* chem `= λ_eff · T · Q`, `T = 2·per_pass + heuristic_toffoli`

| task | file | Q | cost | ref/cost | T (mean) | tier |
|---|---|---:|---:|---:|---:|---|
| invsqrt | `0af21cb8` (ours) | 44 | 74,797.36535717871 | 27.76534 | Toffoli 1,459.375; T-eq 240.565 (962.26 T gates) | official (ours) |
| invsqrt | **`563d0583`** | **44** | **74,560.91** (74,560.86 at salt `s1`) | 27.85339 | Toffoli **1,454.0**; T-eq 240.566 | author + ahoirg re-verified |
| DQI | `575b043f` (ours) | 890 | 346,409,762,293 (clean draw) | 70.55074 | 367,116.05 | third-party reported (N3/N6/N9) |
| DQI | `957d6733` | 890 | 346,654,664,786 (clean) / **3.474075e11** (48-draw expected) | 70.5009 | 367,375.47 | author (HW-29) |
| chem | `703843d3` + 4,022 loaders | 427 | **294,642,299.7630** | 11.38872 | 14,706 | official verifier run by our dataset scout |
| chem | `56ef2562` + 4,022 loaders (ours) | 427 | 294,643,137.7336 | 11.38869 | 14,706 | official (ours) |

Best-per-task composite (arithmetic on the above):
`GM(563d0583, 575b043f, 703843d3) = 28.180686`.

Cross-checks that the model is exact: `GM(0af21cb8, 575b043f, 56ef2562) = 28.150932`,
which is our own public score 28.15094 to 5e-6; `GM(0af21cb8, 575b043f, 703843d3) =
28.150954`, which is the leaderboard's 28.15096 (sub 58469117).

---

## 3. Candidate cheaper components, itemised

### 3.1 invsqrt `563d0583` — **new, worth shipping** (+0.0297 GM)

* **Exact reported number:** 74,560.91 at the default salt, 74,560.86 at salt `s1`
  (N1 §Checks; N2 "re-verified here"; N6 credits). Q = 44; worst error/tolerance
  **0.99956** (5 digits; `0af21cb8`'s is 0.9995605646 — consistent with an identical
  angle set, but that is an inference, not a measurement).
* **Shape / parameters:** `C = 74,560.91 / 44 = 1,694.5661`; mean Toffolis **1,454.0**;
  33 fine rotations. Our file: `C = 1,699.9401`, mean Toffolis 1,459.375, 33 rotations.
  **The rotation/T part is identical by arithmetic**: ΔC = 5.3740 and ΔToffoli = 5.375,
  so `T-eq/4` is 240.565 in both (1,699.9401 − 1,459.375 = 240.5651; 1,694.5661 − 1,454.0
  = 240.5661). This is a *pure structural* Toffoli reduction of 5.375 mean, i.e. the same
  33 angles, so the phase margin — and the salt risk — should be the same as
  `0af21cb8`'s (which passed 8/8 salts).
* **Provenance:** `maoxin123`, on Syed Asad Ali's 46-Q generator + Ali Haydar Özdağ's
  64-row table + Ertuğrul Özer's angle refit; "rescheduled to 44 qubits" (v27's
  rescheduling idea taken one step further). Cell index 5 of N1 carries the bytes:
  `INV = "eNrtvQm…"` → `zlib.decompress(base64.b64decode(INV))`, sha256 must equal
  `563d0583f736afc2d8111f376bc1bd5ce6aef686525b0dd281fc1f2b4eb09321`.
* **Verifiable from the text alone?** The *claim* cannot be derived from prose — it is a
  verifier output. But the exact bytes are in the notebook with a pinned hash, **two
  independent notebooks report the same official-verifier cost at default salt and full
  200,540,928 shots** (N1 author, N2 ahoirg), and a third ships it (N6, N7). Tier:
  author-reported ×2 + shipped by two more, not yet in an 8-salt study, **not** run by us.
* **Risk:** worst error/tol 0.99956 leaves 4.4e-4 of headroom; `0af21cb8` has the same
  number and passed 8 salts. If the angles are byte-identical (likely, per the T-eq
  arithmetic) the salt behaviour is identical. Not proven.
* **Do not confuse with** `c5ad9f1a`/`56ef2562` (chemistry hashes) — the `563d` string is
  the invsqrt only.

### 3.2 chemistry `submission.npz` `703843d3` (+0.0000267 GM)

* 294,642,299.7630277 vs our 294,643,137.73357135, i.e. **−837.97** on the leg,
  λ_eff 46.9217168 → marginally lower (the text quotes the same 46.9217168 to 8 digits;
  the delta is in the 9th). Same 15 loaders (4,022 T/pass), same words, same Q = 427.
* Already found by the dataset scout (`RESULT_20261117.md` §2) and verified with the
  official `dfthcsos/verify.py`; reported again here only so the notebook/forum ledger is
  complete. Ship it; expect nothing.

### 3.3 Nothing else

* **DQI:** no public file is cheaper than 890 Q / 367,116 mean T. Details in §4.
* **chem:** no public T below 14,706 and no competitive Q below 427. Details in §4.
* **invsqrt:** no public Q below 44 and no C below 1,694.57. Details in §4.

---

## 4. Explicit negatives (what the public record *does not* contain)

From `manifest.csv` (551 rows, snapshot 2026-11-16 17:46) plus the 17-Nov notebooks:

**invsqrt** — Q histogram: 44 ×9, 46 ×11, 62 ×53, 63 ×10, 64/66/68/76/82/89/90/93/95,
105, 140/145, 208, 256/258/260, 273.
* min cost per Q: 44 → 74,797.37 (ours); 46 → 78,673.54; 62 → 93,555.26; 63 → 102,286.22.
* **no Q ∈ {42, 43} exists at all.** 43 Q on the 44-Q file is independently closed by
  `NR-0275`: the longest releasable scratch wire holds `[x ≤ 63]`, "not a single wire or
  2-AND of live values", budget 39.7 charge units/shot. 42 Q on our geometry is priced by
  our own closed line: it needs C ≤ 1,781.06 to reach gold, i.e. a 4.78 % cut in C.

**DQI** — Q histogram: 877, 880, 881, 882, 883 ×4, 888 ×9, 889 ×13, 890 ×5, 891 ×11,
892 ×45, 893, 895, 896, 897 ×2, 898, 900 ×2, 1797, 1818, 3299.
* best per Q (one-draw `local_task_score`, or 48-draw where available):
  877 → 444.2e9; 883 → 434.8e9; **888 → 398.7e9**; **889 → 360.9e9**; **890 → 347.88e9**
  (48-draw expected; one-draw 347.13e9); 891 → 375.6e9; 892 → 371.9e9.
* the Q² term means an 888-Q file must have T ≤ 367,116·(890/888)² = **368,772** to win;
  the best 888-Q public file is ~419 k T. Reducing Q *and* T together is exactly what
  `NR-0260`/`NR-0259`/`NR-0081`/`NR-0130` show is blocked: every 888-wide stretch holds a
  one-bit flag (≈135 flag lifetimes would be needed to cover all crossings), and the
  chain-pole wire is information-bearing at first use.
* **the 48-draw expected cost of every public 890-Q file is ≥ 347.88e9** — our 346.41e9
  is the cheapest *and* the cleanest (R = 1.19126 = the 0-error Clopper–Pearson floor).

**chemistry** — 348 rows, all competitive ones at Q = 427, T ∈ {14,712 (16 rows),
14,706 (17-Nov only)}; Q = 423 exists (10 rows) but at T = 18,126–20,966 → 368–426 M.
* **no row with T < 14,706**; **no row with Q < 427 at T < 18,000**.
* shape family is unanimous: R = 8, B = 143, C = 44, brot = 8, J = 5.
* `NR-0020`: Eckart–Young floor R·C ≥ 290 / 307 / 330 for 20 / 15 / 10 mHa — our K = 352
  is ~10 % above the 20 mHa floor, and every attempt to walk down (F3, `NR-0051`,
  `NR-0060`, `NR-0147`, `NR-0161`, `NR-0269`, `NR-0276`) lands at 22–30 mHa after 8-bit
  rounding. Dead end, not an oversight.

---

## 5. Verifier / cost-model facts that bear on how we optimise

These are read off the **local, unmodified** verifier source in `data/competition/`
(file/line cited), not off secondary posts.

1. **`T` is a per-shot *mean*, in all three tasks — conditioned gates are discounted by
   how often they fire.** This is the single most important thing on this list.
   * `verifiers/dfthcsos/scoreinfra/circuits.py:445-447`: "The Toffoli count is the mean
     number of Toffoli-like gates (`CCX`, `CCZ`, `CSWAP`; **a conditioned gate counts only
     on the shots whose bit is set**) executed per shot over the forward and reverse pass
     together."
   * `verifiers/dqi/verify_submission_dqi.py:418-421`: `toffolis = sum(r[2] …)/num_shots`.
   * `verifiers/invsqrt/verify_submission_invsqrt.py:317-326`: `toffoli_count =
     sum(r[2])/num_shots`, `t_base = sum(r[3])/num_shots`, `n_rot = sum(r[4])/num_shots`
     (mean Z_POW at Clifford level ≥ 4), `t_count = t_base + n_rot·rotation_t_count(eps)`.
   * Consequence: a `CCX … if b` costs 0 on the shots where `b = 0`; a Clifford
     correction (CZ/CCZ) gated on a measurement outcome is **free** (it is neither
     Toffoli-like nor a rotation). This is precisely why `qhdl measure-out` / `measure-first`
     pay, and Tanuj Khattar published the identity (F7).
   * **This is already harvested on the public frontier**: `NR-0256` scanned the DQI pick
     for measure-out sites → **0 buildable** (1,343 sites had no free spare wire);
     `NR-0143` shows the chemistry loaders already recompute their 4-wire low-address
     cache "after each measurement-based uncomputation". Do not redo that scan.
2. **`Q` is static, `T` is sampled.** For invsqrt, `Q = circuit.num_qubits` and the
   *rotation* cost is set by the **global worst** `error/tolerance` over all 3,133,452 x
   (`min_margin` over chunks → `eps`), so one thin input sets the T price for every shot;
   you cannot average the margin down. For chem, `Q = persistent + max(heuristic_temp,
   angles_temp)` with the ANGLE part capped at `QUBIT_CAP = 128` (`verify.py:134,539`).
3. **`Q` in chem is a formula, not a measurement**: `Q = h.persistent + J·brot +
   max(h.temporary, angles_temp)` (`verify.py:487-517`). With `brot = 8`, `J` costs
   `+8` qubits per word and never relaxes the temporary term (304 > any angles_temp), so
   J-variants are a wash: `NR-0128` prices J6 at −2.0 % T / +1.86 % Q. Closed.
4. **`T` in chem is `2·per_pass + heuristic`**, where `per_pass` is our measured loader
   Toffoli count (4,022) and `6,662` is the shape-only heuristic for (8,143,44,8).
   So the loader is 54.7 % of T. Exchange rates at the §2 frontier: **1 Toffoli off
   `per_pass` = +0.00128 GM; 1 % of `per_pass` = +0.0512 GM; 1 % of the whole chem cost
   (whether via `λ_eff` or `T`) = +0.0933 GM.** The ladder: `per_pass` 3,620 → GM 28.7138
   (gold at today's line), 3,416 → 29.000, 2,764 → 30.000, 2,193 → 31.000, 2,011 → 31.348.
5. **`R` has a hard floor** `1.1912605` at 0 errors in 102,400 shots (one-sided
   Clopper–Pearson at 2⁻¹²⁸). One failed shot moves R to 1.19673 (**+0.459 %**, ≈1,685 T
   equivalent); two to 1.20139 (+0.85 %). Our DQI sits exactly on the floor.
6. **The DQI draw is `f(circuit sha256, salt)`** (F8, and `initial_seed(submission_sha256(...), salt)` in `circuits.py`).
   Any byte change re-rolls the public draw. The private salt is unknown.
   Corollary: a "clean default-salt draw" is not evidence about the private draw; the
   48-draw expected cost is the right ranking key (manwithacat's convention).
7. **Metric-only file checks** that no standalone verifier performs (F9): exactly one
   `invsqrt.kmb`, one `dqi.kmb`, one `dfthcsos/` per zip (searched recursively — a stale
   backup copy anywhere fails the whole entry); `angle_k_0..n-1` with no gaps; every
   register named; `submission.npz` arrays float / little-endian (`tree_edges` integer);
   every qubit/bit id < **699,050**. One failed task = whole submission rejected.
8. **Chem: the verifier overwrites the submitted one-body shift and `Hsym_lower`** with the
   packaged baseline (`load_fixed_shifts`), so BLISS-style symmetry shifts are not a lever
   (`NR-0135`, `NR-0272`). Rotating the orbital basis is a no-op because all metrics are
   computed in the FCIDUMP basis (`NR-0136`).
9. **`Z_POW` is rejected in chemistry ANGLE circuits** (`_reject_rotations`), so the
   "conditional rotation" trick is unavailable there — it only exists for invsqrt
   (`n_rot` is a mean) and DQI (no rotations at all).
10. **What is known about the private split:** each split runs the published verifier
    with its own secret salt (F8, F9); participants' reading is that a task failing the
    verifier at the private salt rejects the whole entry (not host-confirmed).
    **What is not known:** whether the final scoring adds any correctness check
    beyond the published verifier — F6 (15 votes) and F5 asked exactly this and got **no
    host answer**. Treat "correct only on reachable states" as accepted practice (every
    frontier loader is built that way), but do **not** rely on `R`-reset-instead-of-
    uncompute (F5, unanswered) and do not assume a local default-salt PASS is a proof.

---

## 6. The community's own closed-lever ledger (the part we should not re-derive)

From `vqcc-chemistry-negative-results/ledger.csv` (278 cards). These close the hypotheses
that a notebook sweep naturally raises; each has a measured number and a stated reopen
condition. Selected:

| card | claim | number |
|---|---|---|
| NR-0137 | chemistry loader is optimal within each product group; global re-layout is the only way down | loaders = **80 cache + 178–221 products**; counting estimate 80+153–191 ⇒ ceiling **≈ −5 % chem**; 130 M flip moves found nothing |
| NR-0268 | loader synthesis toward the counting floor on the current pick | floor 270 vs 291 shipped; walks reach 277; **whole-line ceiling ≈ −1.8 % chem, +0.6 % GM** |
| NR-0231 | AND-minimising loader synthesis with don't-cares (828 unused addresses) | shipped 270 CCX = 75 caches + 195 products; per-plane ranks sum 470, **unchanged** by don't-cares; 500 M moves → 0 reductions |
| NR-0255 | re-implement maoxin123's block-of-three loader search | v1 214 / v2 212 products; our from-scratch planner 217; 0 progress from v1's 97 relations |
| NR-0273 | generic minimum-AND synthesis of one loader | dense ANF start 2,036 ANDs vs 294 shipped |
| NR-0143 | history caches on the C43 loaders | 2,048 addresses: **0 repeated products, 0 returning targets, 0 affine products** |
| NR-0128 | J = 6/7/8 loaders under the 128-q cap | J6: 4,480/pass and Q 438 ⇒ **+5.77 % cost** despite the −2.0 % address-cache T saving; J7 +5.09 %, J8 +7.66 % |
| NR-0183 | 5/6 and 3/8 address splits, phased caches | 3/8 needs 194 q (cap 128); the rest repay per phase; **nothing built** |
| NR-0020 | Eckart–Young floor on R·C | ≥ 290 / 307 / 330 for 20 / 15 / 10 mHa |
| NR-0060/0147/0161/0269/0276/0277 | every route below R·C ≈ 480 | 7-group shapes round to 22–24 mHa; (8,129,44) → 19.96 continuous but 0.947× cost only if feasible; all killed |
| NR-0207 | weight refit at fixed words/loaders, how much is left | λ 46.89276 → 46.89199; convex bound **46.8497** ⇒ **≈0.09 % chem left** |
| NR-0278 | cheap XOR codes on the shipped angle table | 3,288 → 3,283 products for λ +0.095 % ⇒ net **−0.03 %** |
| NR-0059 | invsqrt restricted to reachable x (sums of three squares) | 76.46 % of x; **FAILS** the official all-x verifier (x = 2255); only −0.076 % even on R |
| NR-0275 | 43 Q on our 44-Q invsqrt by release-and-recompute | q25 = `[x ≤ 63]`, not a 1- or 2-AND of live wires; budget 39.7 units/shot → **kill** |
| NR-0264 | replace a Toffoli by a Clifford because another live wire holds the value | **0 hits** over 1,421 CCX/CCZ sites, 3 outcome models, all x |
| NR-0108 | borrow zero/affine wires, drop degenerate Toffolis | 0 degenerate controls in ~1,500 Toffolis |
| NR-0238 | cheaper invsqrt coefficient lookup (many families) | 167 CCX shipped; sub-167 forms need 41–156 wires against ≤39 free |
| NR-0256 | measure-out on the DQI pick | **0 buildable sites** |
| NR-0257 | resynthesise the 12-Toffoli bilinear block (1,183 copies) | rank 12 = 3+9 (GF(4)×GF(16)); rank 11 would be **+0.103 % GM**; 3×4e9 walk + kissat: nothing |
| NR-0258 | third aligned elliptic pair (173 → 168 products) | the H-side condition held 0/16,704; applies only to the older 392 k family |
| NR-0260/0259/0081/0130/0139/0167/0168/0213/0237 | every route from 890/889/892 down | every wide stretch holds an information-bearing flag; a qubit is worth ~825–960 T; all killed |
| NR-0065 | drop the zero flags of the 17 last synthesis folds (hengck23's idea) | all 17: −1,190 T but +2 value errors; **even folds 2–16 only: −560 T, 0/0 errors, −0.127 % cost** (partial, unshipped) |
| NR-0223 | debt-free forward/reverse epoch | certified prize 2.2–2.9 k T/shot ≈ +0.2 % GM (partial, unshipped) |
| NR-0001 | "one free stage explains the leader" envelope | even a free DQI phase stage or free angle lookups does **not** reach a 2.24× gap; "the architecture or factorization must change" |

**Reading:** the community has spent measurable effort on every lever we would think of,
and the sum of all remaining *public* chem headroom is ~1.8 % — not the 10 % the leader holds.
Two `partial` cards (NR-0065, NR-0223) are small, unshipped, and worth a look on our own
bytes (§8).

---

## 7. Technique index worth internalising (as documented, not re-derived)

7.1 **manwithacat's technique index** (N10, verbatim names): release-and-recompute
(spooky pebbling); liveness ledger; constrained λ_eff refit at fixed words (projected
L-BFGS + Gauss–Newton retraction); refit alternated with a per-rank orthogonal column
gauge; KKT shadow prices of the error margins; slack-spending stepped-e1 continuation;
measurement-based uncomputation of a borrowed-wire AND (Gidney); multi-input AND with a
clean-wire ladder (≈2.25 T/site instead of 16); porting a tweak by site census;
conditionally clean flag computation; GF(2) kernel-relation search for QROM loaders
(**each admissible relation saves half a Toffoli per pass**); block-design relation plans
with exchange repair; **dead-word flips** (rotations on zero-amplitude branches are free
don't-cares); padding rows as don't-cares (Lera's table has 1,232 addressed rows but
1,220 real ones — the 12 padded rows are free); a reusable `dfthc_refit replan`;
gauge-aware loader emission for a π-gauge table; joining two public circuits where they
are byte-identical / agree on every wire; **measure-out through a free wire**;
**measure-first rewrite emitter**.

7.2 **Numbers that tell us where the remaining money is** (chem): loader 4,022/pass
(54.7 % of T), heuristic 6,662 (45.3 %). Within a loader: 80 cache Toffolis + ~190
products, and the products are *co-trained with the words* ("coded words": 654 low-bit
monomials where a generic table needs 470). DQI: 87.6 % of T is the key-equation stage,
the scan is 11 T/point at its floor; `NR-0265` records that 81 % of the Toffolis are
field products (1,376 GF(2^24)@99 + 2,853 GF(2^12)@42) and that three
compute/uncompute pairs hold 86 %.

7.3 **What the 44-Q invsqrt is actually made of**: Syed Asad Ali's generator, 64-row
table (Ali Haydar Özdağ), 33 rotations (Özer refit), 22 scratch wires all live at the
peak. The 5.375-Toffoli delta between `0af21cb8` and `563d0583` is rescheduling (and, per the
credits, the measured-CZ / dead-write line), not new arithmetic.

---

## 8. Open leads, ranked, with price tags (all unverified by us)

| # | lead | where it comes from | value if it works | what would have to be true |
|---|---|---|---|---|
| L1 | ship `563d0583` (invsqrt) | §3.1 | **+0.0297 GM** | one official-verifier run on our side at default + 2 salts |
| L2 | measure-first / measure-out / retain on **our** three files | F12, N10 | 0 to +0.01 GM (DQI pick already 0 sites, NR-0256) | cheap to check with `qhdl peak/runs/idle`; likely 0 |
| L3 | NR-0065 "even folds 2–16 only": drop zero flags of the last synthesis folds | ledger card (partial) | −560 T on the 889 netlist = **−0.127 % DQI ⇒ +0.012 GM** | it must apply to the 890-Q lineage, and the 0/0 error record must survive several salts |
| L4 | NR-0223 debt-free epoch repayments | ledger card (partial) | 2.2–2.9 k T/shot = −0.68 % of T ⇒ **+0.064 GM** by our arithmetic (the card writes "~+0.2 % GM") | needs a mirror-aware rebuild of the normalize arithmetic; priced, never built |
| L5 | push `per_pass` from 4,022 to ≤ 3,620 | §5.4 | **gold** at 3,620 (GM 28.7138); 28.741 at 3,600 | loader synthesis below the counting floor — the whole public field failed (NR-0137/0268/0231/0255) |
| L6 | DQI 890 → 864 at constant T | our own closed line | +0.562 GM | our own closed line already says this is the theoretical floor and lands 0.0005 *under* gold |
| L7 | find the leader's 10 % | F13, N12 | +1.3 GM or more | a private architecture change; no public trace. N12's own conclusion: only chemistry has a priced lever of that size (219 M ≈ 31.07) |

Ranking rationale: L1 is the only certain positive; L3/L4 are the only unshipped
*measured* partials; L5 is the only public lever of gold size, and it is closed by four
independent searches; L7 is private.

---

## 9. Reproduce (read-only)

```bash
export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)

# notebooks (source only; ~50-900 kB each)
kaggle kernels pull maoxin123/qcc-28-17-4-022-toffoli-chemistry-loaders -p /tmp/nb -m
kaggle kernels pull ahoirg/qcc-reproducible-circuit-portfolio            -p /tmp/nb -m
kaggle kernels pull ghazarosbarseghyan91/vqcc-28-15096-best-per-task    -p /tmp/nb -m
kaggle kernels pull alexchilton/28-15-lb-which-circuits-survive-private-salt -p /tmp/nb -m

# the invsqrt bytes: cell 5 of the first notebook
#   python -c 'import json,base64,zlib,hashlib;nb=json.load(open("<...>.ipynb"));cell=[c for c in nb["cells"] if "563d0583" in "".join(c["source"])][-1];src="".join(cell["source"]);ns={};exec(src.split("data =")[0],ns);d=zlib.decompress(base64.b64decode(ns["INV"]));print(len(d),hashlib.sha256(d).hexdigest())'
#   -> sha256 must be 563d0583f736afc2d8111f376bc1bd5ce6aef686525b0dd281fc1f2b4eb09321

# the two exhaustive public indexes
kaggle datasets download manwithacat/vqcc-apache-public-circuits   -f manifest.csv -p /tmp/idx --unzip
kaggle datasets download manwithacat/vqcc-chemistry-negative-results -f ledger.csv  -p /tmp/idx --unzip

# forum
kaggle competitions topics list google-verifiable-quantum-circuit-compilation
kaggle competitions topics show google-verifiable-quantum-circuit-compilation 753633
kaggle competitions topic-messages google-verifiable-quantum-circuit-compilation 753185 -n -1 --format json
```

Queries used on the manifest (arithmetic only):

```
min local_task_score per task;  Q histogram per task;  best per Q;
chem: rows with Q_total < 427, rows with T_total < 14706;
dqi: min dqi_expected_cost, best per Q
```

Queries used on the ledger: `outcome != kill`, `date_tested >= 2026-11-12`,
keyword scans for `measure/uncomput/conditional/anchor/reset/HMR/releas/pebbl`, `loader`,
`shape`, `eckart`, `leader`.

---

## 10. Uncertainty / limits of this sweep

* The invsqrt and chem costs in §3 are **publisher-reported** (plus, for chem, an official
  run by our dataset scout). I did not run any verifier. The DQI number is
  third-party-reported three ways and equals ours, which is consistent.
* `manifest.csv` is a 2026-11-16 17:46 snapshot; it does **not** contain the 17-Nov
  `563d0583` or the 4,022-loader entries. Conclusions about "nothing cheaper" for those
  two are from the 17-Nov notebooks, not the manifest.
* Notebook *titles* are unreliable (N17: only 26/276 carry a score, none verified). I
  used reported costs only where the text states the verifier output, and I say which.
* The ledger's `kill`/`null` verdicts are the community's, not the hosts'. They are the
  best available map of what has been tried; they are not proofs.
* Nothing here explains the leader's 10 %. The one public quantitative statement about
  that gap (N12) says a chemistry cost of ~219 M would give 31.07 with the other two legs
  at the public frontier; that is a *scenario*, not a diagnosis.
