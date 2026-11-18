# RESULT — chemistry push line (`brot`, public loaders, J, tree)

Date: 2026-11-18. Line owner: chem research subagent, Kaggle account `qingyu1232`.
Everything below marked **[measured]** was produced by the **unmodified official verifier
code** (`verifiers/dfthcsos/verify.py`, `verifiers/dfthcsos/scoreinfra/dfthc_math.py`)
running on **Kaggle CPU kernels**. Nothing was simulated locally, nothing was submitted,
nothing was pushed. Items marked **[model]** are pure arithmetic from the official cost
module or from the coordinator's closed J model.

Kernels (both private, CPU only, `enable_gpu=false`):

| kernel | slug | result |
|---|---|---|
| stage 1 | `qingyu1232/qcc-chem-brot-trade` | COMPLETE, 179 s |
| stage 2 | `qingyu1232/qcc-chem-brot-refit` | COMPLETE, ~14 min |

Nothing is left running and no kernel was submitted to the leaderboard. (A third private
scratch kernel `qingyu1232/qcc-chem-brot-probe` was used only to measure Kaggle's
kernel-source size limit — 800 KB accepted, 1.07 MB rejected — and is COMPLETE/idle.)

Local work was confined to pure arithmetic: `lambda_brot/check_helpers.py` was run once and
printed (a) `decode(encode(V8, 8)) == V8` to 1.15e-15, (b) the quadratic form
`t'Gt - 2b't + ||T||^2` equals a direct `||sum X (x) X - T||_F` to rel. err **0.0** at four
different scale vectors, (c) the non-negative QP solver activates 2 of 4 coordinates on a
fabricated case, (d) 7-bit / 6-bit / 5-bit quantisation of the shipped vectors has
`quant_sq` 2.170 / 6.299 / 19.936. No integrals were read and nothing was simulated locally.

---

## 0. Verdict

1. **`brot` is a floor, not a knob. NO-GO, and now with a mechanism.** At brot = 7 the
   shipped angle table's `error_2` is **4.26e-1 [measured]** — **21x** the 2.0e-2 gate —
   and a full 50,336-parameter L-BFGS refit of every inner weight moves it to
   **4.2598e-1 [measured]**, i.e. **-0.02 %**. The 7-bit word grid is ~20x too coarse for
   this rank-352 fit. `lambda_eff` also rises 54.3 % (72.39 vs 46.9217) because `E_gap`
   leaves its floor (9.217 vs 3.9149). Even with the accuracy gates waived, brot = 7 at
   the shipped 4,022 loader Toffolis would cost **441.8 M = +49.9 %** (GM 24.595,
   **-3.56**). Brot = 6 is worse again (`error_2` 7.12e-1, `lambda_eff` 94.73, GM 22.764).
2. **The shipped point is a genuine, fully-exploited corner.** `error_1 = error_2 =
   0.019999999735` (2.65e-10 below the gate) and `E_gap = 3.9148980003` (+2.6e-10 above
   its floor). A full 50,336-parameter refit at brot = 8 improves `error_2` by only
   **4.4e-5** and *raises* `error_1` to 0.02008 (a FAIL) and `lambda_eff` to 46.955.
   There is no free `w` refit left.
3. **Item 2 of the work programme is a no-op.** The public "4,022-Toffoli chemistry
   loaders" ARE our loaders: that notebook's own report prints `angle_k_0` sha prefix
   `ed648708` and `T 14,706 / Q 427`, and our 15 files hash to exactly
   `ed6487084d30b0c7…`. Our measured static sum is **4,022 [measured]**, and
   `T_total = 2*4,022 + 6,662 = 14,706` reproduces exactly. **Delta = 0.**
   (The brief's "4,025" was stale. The brief's target `lambda_eff = 46.92158337` is that
   notebook's *better* npz `703843d3` — it is already the bar, not something to beat; see §6.)
4. **Item 4 confirmed from the code:** `T_h` cannot depend on `tree_edges`.
   `verify.heuristic_costs(num_orbitals, rank_r, bases_b, ensemble_c, brot)` takes no tree
   argument, and `resource_costs` calls it with `inputs.num_orbitals` (from the FCIDUMP)
   only. `Q_total` likewise: `angles["persistent_qubits"] = layout.batch_size *
   layout.brot` comes from the circuit registers, and the heuristic part comes from the
   same tree-free call. Only `error_1/error_2/Lambda/E_gap/lambda_eff` depend on the tree.
5. **Item 3 (J) accepted as closed** by the coordinator's model, reproduced in §5.
6. **Zero chem improvement was found. The shipped chem cost stays
   294,643,137.73 [measured, re-verified end to end].** The only live chem lever is the
   loader compiler (row permutation / address split / cut search), owned by another line;
   I stand by as its verification owner (§8).

---

## 1. Measured baseline re-verification (the control)

The shipped package (`submission.npz` + `angle_k_0..14.kmb`, 16 files) was rebuilt inside the
kernel from embedded bytes and run through `dfthcsos.verify.verify()` unchanged:

| field | value |
|---|---|
| status | **PASS** |
| score | **294,643,137.73357135** |
| lambda_eff | **46.92171681802857** |
| toffoli_count | **14,706** |
| num_qubits | **427** |
| brot / batch_size / num_circuits | 8 / 5 / 15 |
| angles_toffoli (fwd+rev mean) | **8,044** (= 2 x 4,022) |
| heuristic_toffoli | **6,662** (outer 317 + inner 4,095 + givens 2,250) |
| angles_qubits | 128 (= QUBIT_CAP) |
| persistent / temporary qubits | 124 / 303 |
| error_1 | 0.019999999735095 |
| error_2 | 0.019999999735099 |
| Lambda | 283.145810612929 |
| E_gap | 3.914898000264657 |
| `delta_score_vs_shipped` | **0.0** exactly |

Note the rebuilt npz has `submission_sha256 = 261f2ad5…` (different from the shipped
`93326853…`, because `U` is only reproducible to 7e-16) yet the score is **bit-identical**:
`U`'s values are unused by the verifier (only its shape is read), and the words are
recovered deterministically from the classical loaders. That is a useful demonstration
that the chem leg is seed-independent.

`angles_toffoli == 2 * (static CCX/CCZ count)` exactly, because these loaders are
classical on computational-basis inputs: every `HMR` outcome and every `if b0` CZ is
deterministic. **So for these loaders, mean-per-shot Toffoli = static Toffoli count.**

---

## 2. `brot` — the measured kill (stage 1 + stage 2)

Word table: `encode(decode(W8))` at each `brot` (exact inverse of the verifier's ordered
Givens tree, `theta/pi = word / 2**(brot-1)`). At `brot = 8` this is a true identity on the
*vectors* — `decode(encode(V8, 8)) == V8` with `quant_sq = 0.0` — although the word table
itself is not unique (see the artifact note at the end of this section), so the 8-bit
control below uses the shipped `angle_words` unchanged.

### 2.1 Raw re-quantisation (official `evaluate_dfthc_vectors`) [measured]

| brot | quant_sq vs 8-bit vectors | error_1 | error_2 | Lambda | E_gap | lambda_eff | gate |
|---:|---:|---:|---:|---:|---:|---:|---|
| **8** | 0.0 | **0.0199999997** | **0.0199999997** | 283.1458 | 3.914898 | **46.921717** | PASS |
| 7 | 2.1698 | 2.0455 | **0.426064** | 288.5322 | 9.301274 | 72.669940 | FAIL x21 |
| 6 | 6.2983 | 3.5831 | **0.712320** | 294.8610 | 15.63011 | 94.726552 | FAIL x36 |

### 2.2 Best one-body re-derivation (`brot`-grid search over the 75 Givens angles) [measured]

Coordinate descent in the Givens sweep with the exact closed-form best grid angle
(overlap at rotation *t* is `A cos + B sin + const`, vectorised over the 2**brot grid),
objective `sum_j lambda_j^2 (v_j . v*_j)^2`, 6 passes, 3 restarts.

| brot | error_1 naive -> best | error_2 | verdict |
|---:|---:|---:|---|
| 8 | 0.0199999997 -> **0.049777** (worse: round-to-nearest already beats it) | 0.0199999997 | — |
| 7 | 2.0455 -> **0.481304** | 0.426064 | 24x over gate |
| 6 | 3.5831 -> **0.768047** | 0.712320 | 38x over gate |

### 2.3 Exact 352-parameter `w` refit (per-`(rho,c)` block scales) [measured]

`error_2(s)^2 = (s^2)'G(s^2) - 2 b'(s^2) + ||T||^2` is exact — `G_ij = <X_i,X_j>^2`,
`b_i = x_i' T_sym x_i` — checked against direct evaluation (rel. err 0.0), and against the
official `error_2` at scale 1 (0.019999999512 vs 0.019999999735, rel 1.1e-8).
Solved as a non-negative QP over the 352 scales.

| brot | error_2 at scale 1 | error_2 minimum over 352 scales | active | `s` at the gate |
|---:|---:|---:|---:|---|
| **8** | 0.019999999735 | **0.019952361** (-0.24 %) | 352 | 0.99994 / 1.00006 (no gain) |
| 7 | 0.426063700529 | **0.365587203** (-14 %) | 352 | **none exists** |
| 6 | 0.712319537028 | **0.619521939** (-13 %) | 352 | none exists |

### 2.4 Full 50,336-parameter refit (L-BFGS-B on the exact official residual) [measured]

`f(w) = || sum_{rho c} X_rc(w) (x) X_rc(w) - T_sym ||_F^2` with the analytic gradient
`g_{rcb} = 4 u_b' M_rc u_b`, `M_rc = (T_sym . vec(X_rc)).reshape(N,N)`.

| brot | evals | error_2 before -> after | error_1 | Lambda | E_gap | lambda_eff |
|---:|---:|---|---:|---:|---:|---:|
| 8 | 52 | 0.0199999997 -> **0.0199991254** (-4.4e-5) | 0.020080 (FAIL) | 283.173 | 3.9201 | 46.955 |
| 7 | 31 | 0.4260637 -> **0.4259766** (-0.02 %) | 2.0365 / 0.5422 (best 1-body) | 288.896 | 9.2173 | 72.393 |

**This is the decisive number.** Refitting every weight of the 7-bit table changes
`error_2` by 2e-4. The 7-bit table's accuracy is not a refit problem, it is a grid
problem: 21x the gate.

### 2.5 What brot would cost if the gates were waived [model, official cost module]

`T_h` and `Q` are exact from `heuristic_costs` (**[measured]** in-kernel):
`Q_total = 84 + J*brot + 303` and `T_h` = 6,662 / 6,362 / 6,062 / 5,762 at brot 8/7/6/5.

| brot | T_h | Q | measured lambda_eff | T at 4,022 loaders | chem cost | ratio | GM |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **8 shipped** | 6,662 | **427** | **46.921717** | 14,706 | **294,643,137.73** | 1.0000 | **28.15093** |
| 7 | 6,362 | 422 | 72.669940 (72.393 after full refit) | 14,406 | **441,784,693.10** | **1.4994** | **24.595** (-3.556) |
| 6 | 6,062 | 417 | 94.726552 | 14,106 | **557,200,711.90** | **1.8911** | **22.764** (-5.387) |

The `brot` lever *only* exists if the gates hold. They do not hold, by 21x, and the
`lambda_eff` penalty (+54 %) is a second, independent failure.

Cross-check: an independent line measured brot = 7 at `error_2 = 419.5 mHa`,
`lambda_eff = 74.94`, and brot = 6 at `error_2 = 823.8 mHa`, `lambda_eff = 105.70`
(full chem verify, recovered words instead of the npz table). Same conclusion; the
10-20 % spread is the encoding gauge (which of the `±pi` representatives of each subtree
is stored), which the verifier treats identically.

**Artifact note:** the 8-bit shipped table and a naive 8-bit re-encoding differ on 51,974
of 91,500 entries while decoding to the *same* vectors to 1e-15 — the ordered-Givens
encoding is not unique (per-subtree `pi` gauge plus a degenerate-subtree choice). This is
also why the word tables must be compared by their decoded vectors, never by their bytes.

---

## 3. Flow-through to the cost formula (verified from the source)

`Q_total = 84 + J*brot + max(outer_temp 90, inner_temp 303, angles_temp)`. The 303 is the
inner-QROAM temporary of `B = 143` at `k2 = 4`. The shipped loaders sit exactly on the
128-qubit cap, so at brot = 8 `angles_temp = 128 - 11 - 5*8 = 77`; the cap allows at most
82 / 87 at brot 7 / 6, always below 303. So the loader workspace is effectively free and
**Q depends on `brot` and `J` only through `J*brot`**: `Q = 387 + J*brot` exactly
(**[measured]** in-kernel at brot 8/7/6/5 = 427/422/417/412).

---

## 4. `tree_edges` vs `T_h` (item 4)

* `verify.py:489` `heuristic = heuristic_costs(inputs.num_orbitals, rank_r, bases_b,
  ensemble_c, brot)` — no `tree_edges` parameter anywhere on the path.
  `inputs.num_orbitals` is `ref["orbitals"]` = 76 from the FCIDUMP.
  **`T_h` is provably tree-independent.**
* `verify.py:491` `persistent_qubits = heuristic["persistent_qubits"] +
  angles["persistent_qubits"]`, and `angles_costs` sets
  `persistent_qubits = layout.batch_size * layout.brot` from the submitted registers.
  **`Q_total` is tree-independent** (for a fixed loader family).
* `tree_edges` *is* in the hashed npz key list, so changing it changes
  `submission_sha256` (hence the simulator seed) but not the score, and it does change
  `error_1/error_2/Lambda/E_gap`. Since every candidate word table needs its own 15
  loader plans anyway, a tree change is only interesting together with a loader rebuild —
  and §2 shows the accuracy wall is 21x, not a few percent.

---

## 5. `J` (item 3) — closed, arithmetic reproduced

`emit_plan.py` hardcodes 5 words per loader (`words[:,5*k-5:5*k]`, `for j in range(5)`)
and every loader pays a fixed `high_cache = 69` CCX plus its low computes, independent of
`J`. `J` loaders pay `ceil(75/J) * 69`:

| J | loaders | fixed high-cache | loader sum/pass | T_total | Q | cost ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 19 | 1,311 | 4,298 | 15,258 | 419 | **1.01810 (worse)** |
| **5** | **15** | **1,035** | **4,022** | **14,706** | **427** | **1.00000** |
| 6 | 13 | 897 | 3,884 | 14,430 | 435 | 0.99962, **and 11+6*8+77 = 136 > 128 qubits => illegal** |

Matches the coordinator's numbers. Also confirmed independently here: `Q = 387 + J*brot`.

---

## 6. The public "4,022-Toffoli loaders" (item 2) — already ours

* `/tmp/pull_ghaz/…4-022-toffoli-chemistry-loaders.ipynb` (fork of maoxin123) states in its
  own header that chemistry is "same 15 loaders, npz `703843d3`", `T 14,706`, `Q 427`, and
  `angle_k_0` sha prefix **`ed648708`**.
* Our 15 files hash to `ed6487084d30b0c7…` (= `ed648708`), and their static count is
  **4,022 [measured with kickmix metadata]** which reproduces `T = 14,706` exactly.
* **Therefore the public claim equals ours: delta 0, nothing to adopt.**
* The one thing worth taking from that notebook is its npz `703843d3`
  (`lambda_eff = 46.92158337`, cost **294,642,299.76**, i.e. **-838** vs our local npz's
  46.92171682). It is the brief's quoted target. The packaging line should prefer it if
  it verifies — it is the same words/U/tree, only `W` and `H2_I` change.

---

## 7. Artifacts, commands, checksums

### Layout

```
experiments/frontier/20261118_push/chem/
  RESULT.md                                  this file
  lambda_brot/
    analysis.py                              stage-1 kernel body
    analysis2.py                             stage-2 kernel body (full refit + end-to-end)
    make_kernel.py                           embeds payload, emits k_*/main.py
    check_helpers.py                         local pure-arithmetic unit check (exact inverse
                                             encoder, quadratic-form identity, QP solve)
    k_brot_trade/{main.py,kernel-metadata.json}
    k_brot_refit/{main.py,kernel-metadata.json}
    out/brot_trade.json                      stage-1 measured JSON
    out/qcc-chem-brot-trade.log
    out2/brot_stage2.json                    stage-2 measured JSON
    out2/qcc-chem-brot-refit.log
    out2/dfthcsos/                           control package: submission.npz + 15
                                             angle_k_*.kmb (16 files), official PASS,
                                             score 294,643,137.73357135
```

`out2/dfthcsos/` is the **control**, not a candidate: `delta_score_vs_shipped = 0.0`.
It exists to prove the harness; do not ship it in place of the packaged `a73b25d2`/`703843d3`.

### sha256

```
98ba225cc57c97d979f8c9e994210847cc9d7222ee176f47dc8d34b3a2550f38  lambda_brot/analysis.py
9a254f459a01fe8ef47c0ec3fe53b00c1309b55f68ca744393692285edc5fe6d  lambda_brot/analysis2.py
ea6f7b856c2c6f7273c2ba76b088e400bcccc7c1c26dcacc18e9165453c276e3  lambda_brot/make_kernel.py
f1fde77f666b5b53923ebf78e8db6e14f6060105ccc4f106d32c5c78686bd4a5  lambda_brot/check_helpers.py
ecfed518ec6837416aa5f264fd63cd3a062dd256df060f410d13573dd27321b6  lambda_brot/k_brot_trade/main.py
18de518b81c256d73e8d0667d3a56172b4126ae0712ec97f3e944ea99da10d0e  lambda_brot/k_brot_refit/main.py
c91a4313900317430c674dfee785e543c732b51af0810e04005a1f32d44db579  lambda_brot/out/brot_trade.json
eed88592d37272667dec64d7d8255a869fb0933c0857a4113c10d7560ef06b21  lambda_brot/out/qcc-chem-brot-trade.log
ab57d73f58d244475e2dea32f3849d22376282e115bdad198a70cbcbc32913cf  lambda_brot/out2/brot_stage2.json
baa2bd4f2c580fa0a958100471baee37896c7e5d4ff6ae13dcd88e20843b2c11  lambda_brot/out2/qcc-chem-brot-refit.log
0dfabe07d094276a691c8fd5d4692a5ac09ff8157138287a428a73df95c13c21  lambda_brot/out2/dfthcsos/submission.npz
```

Shipped loader sha256 (identical to the public release; `angle_k_0` = `ed6487084d30b0c7…`):

```
ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538  angle_k_0.kmb
8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd  angle_k_1.kmb
e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f  angle_k_2.kmb
b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e  angle_k_3.kmb
ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d  angle_k_4.kmb
21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856  angle_k_5.kmb
1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1  angle_k_6.kmb
8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0  angle_k_7.kmb
0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563  angle_k_8.kmb
b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71  angle_k_9.kmb
41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6  angle_k_10.kmb
76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca  angle_k_11.kmb
e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f  angle_k_12.kmb
9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8  angle_k_13.kmb
fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f  angle_k_14.kmb
```

### Exact commands

```bash
# build the two kernels (payload = shipped npz weights + the 15 shipped .kmb, lzma+b64)
cd <repo>/experiments/frontier/20261118_push/chem/lambda_brot
KERNEL_DIR=k_brot_trade ANALYSIS=analysis.py    ../../../../.venv/bin/python make_kernel.py
KERNEL_DIR=k_brot_refit ANALYSIS=analysis2.py   ../../../../.venv/bin/python make_kernel.py

python scripts/kgpu.py new   --dir …/lambda_brot/k_brot_trade --slug qcc-chem-brot-trade \
                             --account qingyu1232 --competition
python scripts/kgpu.py push  --dir …/lambda_brot/k_brot_trade --account qingyu1232
python scripts/kgpu.py new   --dir …/lambda_brot/k_brot_refit --slug qcc-chem-brot-refit \
                             --account qingyu1232 --competition
python scripts/kgpu.py push  --dir …/lambda_brot/k_brot_refit --account qingyu1232
python scripts/kgpu.py status --kernel qingyu1232/qcc-chem-brot-trade --account qingyu1232
python scripts/kgpu.py fetch  --kernel qingyu1232/qcc-chem-brot-trade --account qingyu1232 \
                              --out …/lambda_brot/out
python scripts/kgpu.py fetch  --kernel qingyu1232/qcc-chem-brot-refit --account qingyu1232 \
                              --out …/lambda_brot/out2

# local pure-arithmetic unit check (no integrals, no circuits, no simulation)
.venv/bin/python check_helpers.py
```

Kernel-source budget note: Kaggle's `kernels push` rejects scripts above ~1 MB
(800 KB accepted, 1.07 MB rejected). The payload is therefore lzma+b64 (890 KB total);
`U` is not stored because the verifier only reads its shape.

### GM deltas (`scripts/gm.py`)

```
shipped                        chem 294,643,137.73    GM 28.15093204   (+0.00000)
brot=7, gates waived           chem 441,784,693.10    GM 24.59544401   (-3.55550)
brot=6, gates waived           chem 557,200,711.90    GM 22.76430178   (-5.38664)
```

(`scripts/gm.py --current` carries `invsqrt = 74,797.365` rather than the brief's
`74,560.907`, so its absolute GM is 28.1509 where the brief says 28.1807 with the local
salt. Only the deltas are meaningful here; they are exact for a chem-only change:
`dGM/GM = -(1/3) * dchem/chem`.)

Equivalently, the brief's sizing rule inverted: chem cost must reach
**<= 277,665,074.39** (-5.76 %) for gold with the other two legs held — and the chem
frontier inside this submission-controlled family is exhausted.

---

## 8. Verification runbook (standing role)

When the loader line produces a candidate `submission.npz` + `angle_k_*.kmb`:

1. Build a 24-file check dir: the 15 candidate `.kmb` (contiguous `angle_k_0..K-1`,
   `K = ceil(75/J)`), the candidate `submission.npz` (keys `U, W, H2_I, H1_I,
   Hsym_lower, tree_edges` as `.npy` entries, `angle_words` optional record), and nothing
   else `.kmb`/`.kmx` in the directory (`read_circuit_family` rejects extras).
2. Push one CPU kernel (`enable_gpu=false`) that runs, unchanged:
   `python $COMP/verifiers/dfthcsos/verify.py <dir>` with
   `PYTHONPATH=$COMP/kickmix:$COMP/verifiers`.
3. Read the printed JSON. PASS requires: `error_1 <= 0.020`, `error_2 <= 0.020`,
   `0 < E_gap <= 2*Lambda`, `Lambda > 49.0`, `E_gap > 3.914898`,
   `angles_qubits <= 128`, and `num_circuits == ceil(75/J)`.
4. Report `toffoli_count` (= `2*loader_sum + T_h`), `num_qubits`, `lambda_eff`, and
   `cost = lambda_eff*T*Q` with the `scripts/gm.py` delta.
5. **Watch the margins.** The shipped `a73b25d2` sits 2.65e-10 below *both* error gates and
   2.6e-10 above the `E_gap` floor. Any candidate that keeps its words must keep
   `error_1`/`error_2`/`E_gap` **bit-for-bit**; a candidate that changes the words must
   clear the gates with room to spare, because the corner is already spent.
6. Also assert `angles_toffoli == 2 * static CCX/CCZ` (the loaders are classical, so the
   two must agree); a mismatch means a conditioned gate that is not deterministic, which
   would make the count seed-dependent.

The stage-1 kernel already contains every piece of that harness (payload embedding,
official calls, `heuristic_costs`, the full `verify()` call) and can be re-pointed at a
candidate directory by swapping the payload.

---

## 9. What this does NOT close

* Whether a **from-scratch** fit at `brot = 7` (words co-designed with the 7-bit grid,
  trained end to end) could reach 0.020. Measured here: a re-quantised 8-bit fit cannot
  get below `error_2 = 0.426` even with all 50,336 weights refit. A from-scratch 7-bit
  fit would have to beat that by **21x**. Given that even the 8-bit fit only barely sits
  at the gate after being co-designed with its grid, the expectation is that it cannot —
  but it was not run, so it is not a result.
* Any loader-side improvement at `brot = 8` (row permutation, address split, cut search).
  Not attempted here, by instruction.
* `Lambda` reduction below 283.15 at `error_2 = 0.020` — measured here: the 352-scale and
  the full 50,336-parameter refits both leave `error_2` at >= 0.019999 and `Lambda` at
  >= 283.15, so the shipped point is a local optimum in `w`. The global question (a
  better formulation, not a refit) remains open and is what the top teams' ~31.4 GM
  implies somewhere, but this line found no chem handle on it.
