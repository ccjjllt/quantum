# Scout — new bytes, public methods, dfthc-sos baselines — 2026-11-17 (window 05:30 → 07:50 UTC)

Read-only on the local machine (file reads, sha256, numpy on <3 MB npz, arithmetic,
Kaggle MCP / web). Every circuit grading run is the **unchanged official verifier at
full shots** on a Kaggle CPU kernel (`enable_gpu=false`, `enable_tpu=false`). Nothing
submitted, nothing pushed.

## 0. Verdict

1. **One new byte exists and it is real, but it is worth +0.00010 GM, not ≥0.1%.**
   `dqi_575b043f` (grantprater dataset v4, xz 20,858,792 B) is `61c8348d` with four
   product-retention pairs added: 367,989 static Toffoli-likes instead of 367,993.
   Independently verified PASS 3/3 salts; clean-draw score **346,409,762,292.7187**
   (default salt, 0/0) → GM with our invsqrt/chem legs **28.15093204** vs 28.15082863
   (`61c8348d`). Δcost on the DQI leg **−0.0011%**; on the public LB that would display
   28.15093, i.e. rank ≈115 instead of 120.
2. **The public frontier above us is a band of few-ppm product gains of the same class,
   not a new leg.** LB 07:46: rank 89 28.15100, ranks 90–91 28.15097, ranks 92–96
   28.15096 (includes `E-Max AI`, whose release record names exactly this DQI sha256 in a
   28.1509587 local portfolio), ranks 97–114 28.15094 (18 teams), 115–116 28.15086,
   117–118 28.15085, 119 28.15084, then **33 teams at exactly 28.15083 (ranks 120–152,
   ours)**.
3. **No other new byte.** Everything published after 05:30 UTC is a stub output
   (~650–740 B marker files) or a repack of known bytes. Details in §2.
4. **The dfthc-sos starter-kit hypothesis is dead** (§4): the starter kit *is* public
   (dataset `sohier/verifiable-circuit-compilation-starter-kit`, 464 MB) and its
   `starter_kit/baselines/` holds the 8 NPZs, but **only one is for the competition
   system** (FeMoCo76o113e) and it is **worse than ours**: Λ = 308.4485, λ_eff = 49.2547,
   error_2 = 16.13 mHa — a *valid* factorization, but 4.6% dearer in λ_eff and >10× dearer
   in T. No public factorization anywhere has Λ < 283.15.
5. **The chemistry lever is Λ, and it is short by a factor of ~4** (§4.3). The known
   refit headroom on a fixed factorization is ≈−0.13% λ_eff (≈−0.26% Λ), while +0.05 GM
   needs Λ −1.0% and gold needs Λ −10.6%. Our error_2 already sits at 19.9999997 mHa
   against the 20 mHa gate, i.e. there is no accuracy margin left to sell for Λ.

## 1. New-byte table

| name | sha256 (full) | size | kind | verified cost (official, full shots) | scope |
|---|---|---:|---|---|---|
| `dqi_575b043f` | `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155` | 479,128,738 (xz 20,858,792) | DQI `.kmb` | **346,409,762,292.7187** default salt, 0/0, T 367,116.06, Q 890, R 1.1912605 | 3 salts, 3/3 PASS (2 clean, 1 lost-shot 348,000,563,990.93) |

- Source: dataset `grantprater/vqcc-dqi-61c8348d-merged-closings` (v4, 02:32:19), member
  `dqi_575b043f.kmb.xz`; shipped with `pairs_4_on_61c8348d.json`, the window prover and
  `README.md` claiming 367,989 static Toffoli-likes and clean costs 346,409,762,293 /
  346,409,819,618. Both claims reproduce to the digit.
- Kernel ref: **`qingyu1232/qcc-scout-verify-dqi-575b043f` v2** (COMPLETE,
  `artifacts/20261117_scout/out_575b043f_v2/verify_results.json`). Pins checked in-kernel:
  `verifiers/dqi/verify_submission_dqi.py` = `f14274bc…94e65`,
  `kickmix/kickmix.so` = `c66b3216…e5005e` (same as every prior verify run).
- GM arithmetic: r_inv 27.76533938, r_dqi 70.55082535 (575b043f clean) vs 70.54995828
  (61c8348d measured clean), r_chem 11.38869079 → **28.15093204** / 28.15093585 (second
  clean draw). Lost-shot draw: GM 28.10797141.
- **Caveat (from the author's own release record, `royalacecat/qcc-28-1509587-e8-submission`):
  this DQI fails a *fixed* `q1116d` weight-35 witness 256/256 while the organizer
  reference is 0/256.** The official verifier's random-shot distribution does not hit it
  (3/3 PASS here), but the file is not universally correct. Its draw risk is the same as
  `61c8348d` (1 lost shot in ~1/3 of draws), and the gain is +0.0001 GM. Not worth a slot;
  record it as a byte, not as a leg.

## 2. Scan window 2026-11-17 05:30 → 07:50 UTC

Method: Kaggle MCP (`search_notebooks` competition filter `sortBy=DateRun`,
`search_datasets` `qcc`/`vqcc`/`verifiable quantum`/`quantum circuit` `sortBy=Updated`,
`list_competition_topics sortBy=New`, per-user notebook sweeps for the 14 high-output
handles), plus `kaggle competitions leaderboard --download` (3246 teams, 07:46 UTC).

| item | time (UTC) | verdict |
|---|---|---|
| `royalacecat/qcc-28-1509587-e8-submission` | 07:03 | release record for API submission 58460103; claims local GM 28.1509587233 with DQI `575b043f`; **no output files**, score PENDING_API; documents the `q1116d` 256/256 failure. Not a usable byte |
| `atakanaldemir/qcc-shared-products-and-controlled-refits` | 07:01 | **stub outputs** (18 files, 675–737 B each); the run's real contribution is dataset `atakanaldemir/qcc-shared-4022-loaders-and-own703-weights` (06:53, 1.30 MB) = `science17.xz`, a repack of **known** bytes (`0af21cb8` + `703843d3` + the 15 SMALL loaders, sha list in `science17_package.json`), status `EXACT17_DATA_PACKAGE_FORMAT_ONLY_PHYSICS_PENDING` |
| `seshurajup/quantum-circuits-3-tasks-lb-27-2900` | 07:19 | stub (`submission.zip` 658 B), LB 27.29 < ours |
| `mizeroluckygall/quantum-circuits-reference-package-to-28-147` | 07:27 | stub (6 files, 680–699 B), title 28.147 < ours |
| `ozertuu/residual-sibling-gating-apex-better` | 07:15 | **different competition** (Name That LLM), ignore |
| `tuantran225/vqcc-verified-portfolio-28-14-open-source` | 05:12 | no output files; pre-window; title 28.14 < ours |
| datasets (`qcc`, `vqcc`, `verifiable quantum`, `quantum circuit`) | — | newest are the two above; nothing else after `ratnachand/…public-floor` 04:45 |
| discussions | — | **no new topic after 759760 (01:37)**; the only new comment is grantprater's 04:52 edit of 759760 announcing `dqi_575b043f` and 37/37 proven chains |

LB snapshot 07:46 (3246 teams): 1 `aadi_stonks` 31.01379 · gold rank 16 `yu4u` 28.71339 ·
silver 28.14724 (rank 161) · bronze 28.12769 (rank 323) · ours 28.15083 = ranks 120–152
(33 teams at exactly that score). Above us: 28.15100 (89), 28.15097 ×2, 28.15096 ×5
(incl. `E-Max AI`), **28.15094 ×18 (97–114)**, 28.15086 ×2, 28.15085 ×2, 28.15084 ×1.
The whole gap 28.15083 → 28.15100 is a few ppm of product, not a leg change.

## 3. Methods / open source / papers (task B)

| source | version / date | what it gives | can it make a cheaper leg? | reproduce cost |
|---|---|---|---|---|
| **arXiv:2610.23832** Khattar, Rubin, Gidney, Broughton, Low, Babbush, *Leveraging verifiable structure…* | v1 2026-10-16 | the competition paper: kickmix gate set, Fiat–Shamir verifier, all three benchmarks, DFTHC cost accounting, 1/√x reference (Q=260, 7735 T, C=7988, score Q·C = 2.08e6) | **No.** Its own Bench I reference is 27.8× above our score (74,797); the Bench II reference (1893 Q, 5.7e6 T) is 11× above ours in Q²T | reading only |
| **arXiv:2610.22367** Gu, Kemeny, Yelin, Lukin | v1 2026-10-15 | LLM-discovered circuits; DQI Reed–Solomon BM decoder at **T=4.4e5, Q=1837** (Q²T 1.49e12), Fe2S2 alias-select, modular inversion | **No for us.** 1837 Q is 2.1× our width and T is 1.2× ours; Q²T is 5.1× worse than our 2.91e11. **No code released** (no code-availability section) | none |
| **arXiv:2502.15882** Low et al., PRX 15 041016 (2025) | published 2025 | DFTHC-SOS factorization; FeMoCo-54o54e λ_eff 20–24 Ha across shapes; the theory behind Bench III | indirectly: it is what the starter kit implements | code = starter kit |
| `sohier/verifiable-circuit-compilation-starter-kit` | 2026-10-22, 464,512,716 B | **the dfthc-sos starter kit**: trainer, angle encoder, circuit builder, verifier copy, 8 baseline NPZs, 6 FCIDUMPs | see §4 — **no** | 1 Kaggle CPU kernel (done) |
| `Agnuxo1/qvc-chemistry-compiler` v0.4.0 (GitHub) | release v0.4.0 | generators for 46Q invsqrt / 889Q DQI / FeMoCo; own composite 26.975–27.016 | **No** (below 28.15); its generators are Syed Asad Ali's, already public | repo (GitHub timed out on fetch; discussion 759244 carries the description) |
| `github.com/noetl/quantum` | 2026 | pipeline harness with `tasks/` stubs for invsqrt/dqi/dfthcsos, scoring/packaging scripts | **No circuits** | — |
| `jday96314` GitHub | — | no qcc repo (only Kuzushiji); its Schur CF decoder ships only inside `alexchilton/qcc-schur-dqi-rebuild` (137 MB, 2026-10-27, 882Q-class `dqi_oz882.qzip`) | **No.** Oct-27 era, LB 24.94; 889Q/382,600 T class | dataset mount |
| `manwithacat/vqcc-chemistry-negative-results` v22 | 2026-11-16, 8 MB | **the best single document for the chem line**: 279-row ledger of killed axes with numbers | **No circuit**, but it kills most Λ ideas for us (§4.3) | 3 small files |
| Qualtran / kickmix | PyPI + Qualtran main | simulator, QROM/state-prep bloqs; `kickmix` now on PyPI (Windows/Linux/macOS wheels, discussion 753307) | no cheaper 1/√x or QROM estimate than the public circuits | pip |

## 4. dfthc-sos starter kit and the Λ question (added task)

### 4.1 What exists and where

Dataset **`sohier/verifiable-circuit-compilation-starter-kit`** (Apache-2.0, updated
2026-10-22, 464,512,716 B, 25,214 downloads). Relevant files:

```
FeMoCo76o113e.fcidump                       128,128,348
FeMoCo76o113e.fixed_shifts.npz                   61,028
starter_kit/baselines/<8 research NPZs>      60 KB … 15.8 MB
starter_kit/starter/task1_factorization/FeMoco76_65_60_60.npz  2,150,130
starter_kit/{dfthc,starter,verifier}/…       trainer, encoder, builder, verifier copy
starter_kit/data/integrals/<6 FCIDUMPs>
```

The 8 baselines are **eight different molecules**, not eight factorizations of ours:

| file | system | (R,B,C) | λ_H2 (local, official formula) |
|---|---|---|---|
| Fe2S2-20o30e_15_20_20 | Fe2S2 | 15,20,20 | 35.659 |
| Fe4S4-36o54e_32_22_22 | Fe4S4 | 32,22,22 | 70.596 |
| FeMoCo54o54e_40_40_40 | FeMoCo (54o) | 40,40,40 | 60.639 |
| **FeMoCo76o113e_65_60_60** | **competition system** | **65,60,60** | **295.576** |
| XVIII100o100e_70_70_70 | XVIII | 70,70,70 | 184.559 |
| XVIII150o150e_120_120_120 | XVIII | 120,120,120 | — |
| XVIII56o64e_50_50_50 | XVIII | 50,50,50 | — |
| cpd1X58o63e_40_45_45 | cpd1X | 40,45,45 | 84.206 |

Only the FeMoCo76o113e row can be submitted (the verifier hard-codes N=76, η=113).

### 4.2 Official metrics of the only usable baseline

Kernel **`qingyu1232/qcc-scout-dfthc-baselines` v2** (COMPLETE;
`artifacts/20261117_scout/out_dfthc2/dfthc_floors.json`), official
`load_inputs` + `evaluate_dfthc_vectors`, unchanged verifier code, 128 MB FCIDUMP:

| quantity | starter-kit baseline (65,60,60) | ours `a73b25d2` family (8,143,44) |
|---|---:|---:|
| error_1 | 1.7e-14 | 0.0199999997 |
| error_2 | **0.0161332** (16.13 mHa) | **0.0199999997** (at the gate) |
| **Λ** | **308.4485** | **283.1458** |
| λ_H1 | 12.87 (self-reported) | 13.0307 |
| **λ_H2** | **295.5758** | **270.1151** |
| E_SOS | −22144.2314 | −22144.1882 |
| E_gap | 3.95802 | 3.9148980 (= the floor, +2.6e-10) |
| **λ_eff** | **49.2547** | **46.9217** |
| passes accuracy | **yes** | yes |
| T (heuristic, brot 12) | 13,757 + angle circuits | 6,662 + 2×4,022 |
| Q (heuristic) | 634 + angles | 427 |
| cost, heuristic-only | **429,596,318** | 294,643,138 |
| cost with real angle circuits | ≈3.36e9 (T_angles 79,480 at J=8) | 294,643,138 |

The baseline NPZ also carries its trainer's own diagnostics
(`values__Lambda` 308.4448, `values__lambda_H2` 295.5758, `values__lambda_eff` 49.1637,
`values__error_h2` 0.016120, `values__sos_gap` 3.94336, metadata R,B,C = 65,60,60,
50k epochs) — consistent with the in-kernel official evaluation.

**Conclusion: the starter kit's baseline is valid but dominates nothing.** It is 4.6%
dearer in λ_eff, ~1.5× dearer in the heuristic T·Q, and ~11× dearer once its real angle
loaders are counted. The organizers' own reference is *worse* than the public frontier.

### 4.3 Why Λ is the chem lever, and how far it has to move

`score = λ_eff · T · Q`, `λ_eff = sqrt(E_gap·(2Λ−E_gap))`, so at fixed E_gap
`dλ/λ = E_gap·dΛ/λ² = 0.001778·dΛ`, i.e. **λ_eff ∝ √Λ**:

| target GM | chem cost needed | Δλ_eff | **Λ needed** | ΔΛ |
|---|---:|---:|---:|---:|
| 28.15083 (now) | 294.643 M | 0 | 283.15 | 0 |
| **28.20** | 293.105 M | −0.52% | **280.22** | **−1.0%** |
| 28.68633 (gold) | 278.449 M | −5.50% | 253.09 | −10.6% |
| 29.0 | 269.511 M | −8.53% | 237.22 | −16.2% |

So the gold chemistry bar is "Λ −10.6%", not "T −5.5%". Three hard facts:

1. **Our factorization is already pinned to the accuracy gate.** error_1 = error_2 =
   0.019999999735 (the gate is 0.020). There is no error budget left to sell for Λ.
2. **λ_H2 is 95.4% of Λ; λ_H1 is 13.03 and cannot be removed** (it is a spectral
   absolute sum of the target h1′; the offsets only move it at cusp cost).
3. **Independent evidence that the Λ/accuracy frontier is tight**: manwithacat's
   279-row negative-results ledger reports, on different public factorizations,
   λ_eff 47.4–49.3 across dozens of shapes, a fixed-word λ_eff refit gain of **−0.081%
   decaying to ≈−0.13%** (NR-0011), offset-scale/gauge steps that all *raise* λ_eff
   (NR-0005/6/15/17), column pruning that raises λ_eff 0.3–0.4 above break-even
   (NR-0032/43), and rank floors R·C ≥ 290 for 20 mHa (Eckart–Young). That is ≈4×
   short of the −1% Λ needed even for 28.20.
A Frobenius floor exists but is not binding: ¼·‖tei + (S⊗I+I⊗S)/2‖_F = **3.70**
(‖tei‖_F = 17.28, ‖sym_shift‖_F = 5.21, ‖target‖_F = 14.81), so the information-theoretic
bound does not forbid Λ ≈ 50 — but dozens of independent optimizations and the
organizers' own baseline all land at Λ 283–308 with error_2 at 16–20 mHa, so a 2× Λ
reduction would be a new algorithmic result, not a refit.

The `Λ > 49.0` gate is a **validity floor** (reject a degenerate/cheating LCU), set
≈16% of the organizers' own baseline Λ = 308.4; it is not evidence that Λ ≈ 50 is
reachable at error_2 ≤ 20 mHa. Note it is a *lower* bound: a submission with Λ < 49 is
rejected even though it would score better.

### 4.4 Any public chemistry npz with Λ ≪ 283?

No. Every public chem byte is the same weights family (`703843d3`, `a73b25d2`,
`93326853`, `0bd9c68f`, `114cff00`, `58db29ce`, `f05297b4`, …): verified λ_eff
46.9216–46.9217 and cost 294.64–296.64 M. The two Φ variants in the sweeps differ only
in angle quantisation/loader count, never in Λ.

## 5. Negative / infra notes for the next session

1. **Kernel-import gotcha.** The competition ships `kickmix` as a bare extension module
   (`kickmix/kickmix.so`, no `__init__.py`). Putting the competition root on
   `PYTHONPATH` makes `import kickmix` resolve to a namespace package and the verifier
   dies with `module 'kickmix' has no attribute 'Circuit'` (kernel v1). Put
   `<root>/kickmix` itself on `PYTHONPATH` (kernel v2 works). All 3 salts then run in
   ~85 s each.
2. Stub-output notebooks are now the norm: 4 of the 5 in-window QCC notebooks wrote only
   650–740 B marker files. Do not spend download budget on them; check `list_notebook_files`
   sizes first.
3. `download_dataset` + `fileName` works for single members over MCP and gives a signed
   URL; `ledger.csv` (278 KB) and the baseline NPZ (2.2 MB) were read that way. Never
   commit the signed URLs.
4. `score_from_metrics` requires `resources["angles_qubits"]`; a circuits-free estimate
   must inject it or compute `λ_eff·T·Q` directly (kernel v1 errored on exactly this).

## 5b. Evidence on disk (git-ignored)

```
artifacts/20261117_scout/out_575b043f_v2/verify_results.json      # 3 official DQI JSONs
artifacts/20261117_scout/out_575b043f_v2/qcc-scout-verify-dqi-575b043f.log
artifacts/20261117_scout/out_dfthc2/dfthc_floors.json             # baseline metrics + Frobenius floors
artifacts/20261117_scout/google-…-publicleaderboard-2026-11-17T07:46:23.csv
experiments/frontier/20261117_deep/scout/kernel_575b043f/{main.py,kernel-metadata.json}
experiments/frontier/20261117_deep/scout/kernel_dfthc/{main.py,kernel-metadata.json}
```


## 6. What the next line should do

**Do not chase the dfthc starter kit or public factorizations for chemistry; the only
chem move left is a *new* factorization with Λ ≤ 280.2 (σ +0.05 GM) — i.e. −1% Λ at
error_2 still ≤ 20 mHa, which needs a structural change (dictionary/shape), not a refit —
while the cheap, already-verified win on the table is the +0.0001 GM DQI `575b043f`
swap, which is not worth a submission slot.**
