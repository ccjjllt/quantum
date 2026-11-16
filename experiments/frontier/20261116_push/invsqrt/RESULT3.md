# invsqrt RESULT3: v12 first-loader certificate re-search (cap 20 -> 17), proven exact

Work in `experiments/frontier/20261116_push/invsqrt/`.
Source pin: `invsqrt_source_zip` sha256 `7d9801ae20e942dba2211a656bba6014a0a16d57da534c0b60328d1c5d9d8254`
(dataset `jiyujia/qcc-invsqrt-v12-generator-source`).  **All searches, builds and proofs ran on
Kaggle CPU kernels** (Python 3.13.18, numpy 2.1.3, competition `kickmix.so`); local work was
static source reading only.

## 0a. FINAL BLOCKER (line closed 2026-11-16 — no further invsqrt compute)

**Q=42 is blocked. No candidate exists, the official verifier was never run for a Q<=42
circuit, and nothing was submitted.**  With the proven cap-17 first-loader certificate the
body reaches Q=42 at these blocks and stops:

```
load_joint16 (first loader)   42   fits   (cap-17 certificate, proven exact)
prepare_H3_initial / H4       42   fits
root / normalization          39 / 37      fits
coefficient_forward           43   -1     <- first blocker (both coefficient stages)
seed_forward                  45   -3     (44 with PACK, which the Q<=45 runs measured)
product_forward               46   -4
divider_cleanup               46   -4
coefficient_inverse           46   -4
```

That is **13 wire-slots** (1 + 3 + 4 + 4 + 4, or 12 if `seed_forward`'s PACK figure is used)
against a remaining budget of **+17.7 Toffoli-equivalents** (C is 1768.17, ceiling 1785.87), i.e.
**<= ~1.3 Toffolis per slot**.  Only dead-wire reclamation (one-time XOR zeroing, free CX) can hit
that price, and the v12 identity library is spent: `agents/composer/p/` holds exactly three
programs (`hret_s15k7a_s15.json`, `v9_form_e2.json`, `w2core_e2.py`) and
`patch_coef2_q46` / `patch_seedinv` / `patch_h2ret` / `patch_hret_sat_s15k7a` already consumed the
`coefficient_forward`, `coefficient_inverse` and `divider_cleanup` sites.  The published
`tools/minand_sat.py` that produced those programs is not in the source tree, and a cap-17 search
recovery (~20 T-eq) does not touch the 13 slots.

**Decision: the invsqrt width line is closed at this point.**  Best verified artifacts on record:
the shipped 44Q `f2cdab0b` (75,006.38, full-shot official PASS, `RESULT.md`) and the cap-17
first-loader certificate (80 Toffolis, work_peak 17, exact full-domain proof `6646f5e0…01d1`).

## 0. What this session delivered

1. **The first-loader certificate lever works, and it is proven exact.**  The tree's own bounded
   search (`work/c10/narrow/research/joint_loader/adaptive_loader_v2.py --mode first_raw`) produces
   certificates at work caps **19, 18, 17, 16** (the shipped one is cap 20).  With the cap-17
   certificate the body emits and the **unchanged exact full-domain prover** returns

   ```
   proof PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
         proved_inputs 3133452   HMR 1309   circuit_sha256 6646f5e09646e23bab17ceb79a1c33711fe503f00c8822960cec34daaad7011d
   ```

   so the loader's width contribution drops from `25 owners + 20` to `25 + 17 = 42` — exactly the
   Q=42 requirement — at a cost of +24 Toffolis (56 -> 80).

2. **The next blocker at Q=42 is named**: with the cap-17 loader the census reads
   `load_joint16 42 (fits)`, `prepare_H3/H4 42 (fits)`, and the build stops in
   **`coefficient_forward` at 43** (one over).  Beyond it, the Q=46 baseline census says
   `product_forward 46`, `divider_cleanup 46`, `coefficient_inverse 46` — i.e. **13 wire-slots
   remain, in four blocks**, and the whole Q=42 budget for them is **+17 Toffoli-equivalents**
   (C is already 1768.17 against a 1785.87 ceiling).

3. **No Q=42 circuit and no candidate**: the remaining 13 slots need structural work that does not
   exist in the tree (see §5).  The official verifier was therefore **not** run; nothing submitted.

## 1. The loader lever, measured

`adaptive_loader_v2.py --mode first_raw --work-cap C --seed s --seconds 22` (bounded stochastic
search, 128 MiB guard, ~15-22 s per run).  Every cap completed with all 16 outputs loaded:

| work cap | Toffolis | work_peak | status | note |
|---:|---:|---:|---|---|
| 20 (shipped) | **56** | 20 | shipped `first_cap20_56b8.json` | reference |
| 19 | 72 | 19 | COMPLETE | my quick search |
| 18 | 73 | 18 | COMPLETE | |
| **17** | **80** | **17** | COMPLETE | **proven exact, §2** |
| 16 | 88 | 16 | COMPLETE | 25+16 = 41 |

Search certificates are deterministic per (cap, seed) but vary run to run in cost (e.g. cap 17 gave
78, 80, 82 Toffolis on different seeds/sessions) — the 56-Toffoli cap-20 reference came from a much
longer sweep, so a longer search should bring cap 17 well below 80.

Drop-in is a two-line change, both in the *patch layer* (never in a pinned file):

```python
# patches/patch_ld_first20_56b8.py
-    assert data['work_cap'] == data['work_peak'] == 20
+    assert data['work_cap'] == data['work_peak'] and 14 <= data['work_cap'] <= 20
```
plus `LD_FIRST_JSON=<certificate path>`.

**Operational trap:** `build.sh` deliberately `unset`s `LD_FIRST_JSON` ("variables the generator
reads as overrides; they must not leak in from the caller"), so a certificate override has to be
driven manually — `tools/build_variant.py` (with the env var) then `tools/pipeline.sh`.  Doing that
is what produced the PASS in §2; going through `build.sh` silently reproduces `321aff83`.

## 2. Exactness receipt for the cap-17 loader

Manual pipeline, cap-17 certificate `v7_first_cap17_s0.json` (sha `9a99784e216bd09457ba024e47b04`
`93ee35f0464ff36badbac3f1299801a84db`, 80 Toffolis, work_peak 17):

```
generator rc=0  18 s   static toffoli_like 1631  T 4  rotations 33  HMR 1304
pipeline  rc=0 113 s   affine round 1: 5 findings (-5 Toffolis); round 2: 0
                       zpow merge: 37 Z_POW, 1 group merged, T 4 -> 3
compiled 6646f5e09646e23bab17ceb79a1c33711fe503f00c8822960cec34daaad7011d
                       Q 46  toffoli_like 1536.5703  T 3.0  33 rotations
                       C = 1768.168   modelled cost 81,335.75
proof PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
      proved_inputs 3,133,452   independent_HMR_variables 1,309
```

So the certificate is *exact* on every official input and every HMR transcript — the lever is
sound, not merely a resource count.  (The 46Q body it produces is of course worse in cost than the
shipped one: 81,335 vs 80,163.  It is a stepping stone, not a candidate.)

## 3. Census with the cap-17 loader (what Q=42 now needs)

| block | shipped body (cap 20) | cap-19 loader | **cap-17 loader** | Q=42 need |
|---|---:|---:|---:|---:|
| `load_joint16` (first loader) | 45 | 44 | **42** | 0 (fits) |
| `prepare_H3_initial` / `prepare_H4` | 44 | 42 | 42 | 0 (fits) |
| **`coefficient_forward`** | 46 | 45 | **43** | **-1** (first blocker) |
| `product_forward` | 46 | — | 46 | **-4** |
| `divider_cleanup` | 46 | — | 46 | **-4** |
| `coefficient_inverse` | 46 | — | 46 | **-4** |
| `seed_forward` | 45 | — | 45 | -3 |
| `root` / `normalization` | 39 / 37 | — | 39 / 37 | 0 |

Measured stops (each with the guard relaxed so the emitter really runs):

```
Q=45, PACK=True, cap-20 loader : product_forward 45+1 = 46   -> 1 over   (only block)
Q=44, PACK=True, cap-19 loader : coefficient_forward 44+1 = 45 -> 1 over   (loader 44 fits)
Q=43/42, cap-19 loader         : load_joint16 25+19 = 44      -> 1-2 over
Q=42, cap-17 loader            : coefficient_forward 42+1 = 43 -> 1 over   (loader 42 fits)
```

The five pinning blocks and the two largest 46-peaks are unchanged from `RESULT2.md`:
`raw_root_restored_with_paid_R` (5,632 ops at 46, live 29) and `divider_return` (3,309 ops, live 15)
carry the `HELD = {q22..q25}` flags, and the file-level **liveness bound is 41**.

## 4. Cost bookkeeping for the Q=42 target

```
shipped 46Q body (321aff83)      C = 1742.7   ->  46 * C = 80,162.73
Q=42 body with cap-17 loader     C = 1768.17  ->  42 * C = 74,263     GM 28.184 (+0.093)
Q=42 ceiling                     C <= 75006.38 / 42 = 1785.87  -> only +17.7 Toffoli-eq left
Q=42 with f2cdab0b's C (1704.69) C = 1704.69  ->  42 * C = 71,597     GM 28.53  (+0.44)
```

So the cap-17 lever already pays for itself at Q=42, but the remaining 13 wire-slots must cost
**at most ~1.3 Toffoli each on average** — which is only possible for *dead-wire reclamation*
(one-time XOR zeroing, free CX), not for new AND identities.

## 5. The exact blocking sites for the remaining 13 slots

1. **`coefficient_forward` (+1 needed at Q=42, and the first blocker).**  Both coefficient forwards
   run `baseline.coefficient_forward`; the Q48-era patches already spent one wire here
   (`patch_coef2_q46.py`: measure `D12` in the second coefficient forward and rebuild with
   **+1 Toffoli**, `patch_w47_body.py` PACK for the first).  A third wire needs a new certificate-
   level identity — the tree's identity library is only `agents/composer/p/{hret_s15k7a_s15.json,
   v9_form_e2.json, w2core_e2.py}`, all three already used.
2. **`product_forward` (+4 at Q=42, +1 at Q=45).**  The 46th wire is the segmented carry allocated
   inside `engine/fusion/arithmetic.py::_compute_carry` (byte-length-locked via `INPUTS.json`, so it
   can only be bypassed by replacing `baseline.product_forward` from the patch layer).  The
   2026-11-15 INV-45 session exhausted the reconstruction search here: the 10 wires that are idle
   through that window have **no affine relation and no <=3-AND relation** (and the 46Q line had
   already gone to 6 ANDs, 0/10), so the carry cannot be rebuilt from live wires.
3. **`divider_cleanup` (+4).**  `divider.compute_phase_cleanup`; the shipped
   `patch_hret_sat_s15k7a.py` already retires history signs 13..15 with per-line SAT-AND programs
   (`agents/composer/p/hret_s15k7a_s15.json`) — the identity source for that site is used up.
4. **`coefficient_inverse` (+4).**  `baseline.coefficient_inverse`; `patch_seedinv.py`
   (v0/v1/v3 across the inverse product) and `patch_h2ret.py` (H2, 3-AND rebuild) already took
   their wires here.

Common structure of the block: **peak live = 41 vs occupied 46**, so all 13 slots are *dead* wires
kept allocated, and the cheapest fix would be one-time XOR zeroing at each handoff (free CX, no
rebuild site).  That is a strictly easier problem than the f2cdab0b one, but it still requires an
identity per handoff, and the v12 identity library has none left for these four blocks.

## 6. Verification scope (explicit)

* **Exact full-domain proof, PASS**: the 46Q body emitted with the cap-17 first-loader certificate
  (`6646f5e0…01d1`, 3,133,452 inputs, 1,309 HMR variables).  This is a *stepping stone* artifact:
  C = 1768.17 at Q=46 = 81,335 modelled, i.e. worse than the shipped 46Q body.
* **Not run**: the official `verify_submission_invsqrt.py` — there is no Q<=42 circuit, so there is
  no candidate.  No submission.
* **Census numbers** are allocation-demand measurements from the real pinned generator with the
  body guard relaxed (`max_qubits` reported as 46 so `emit_body` runs, real limit enforced).

## 7. Next step

1. **Longer cap-17 search** (more seeds / `--resume` chains): the reference cap-20 certificate is 56
   Toffolis from a long sweep, while a 20-25 s slice gives 78-82 at cap 17.  Recovering ~60 would
   return ~20 Toffoli-equivalents of the Q=42 budget.
2. **`coefficient_forward` +1**: the cheapest of the four remaining blocks; it is a
   measure-and-rebuild of one coefficient wire, the same shape as `patch_coef2_q46.py` (which cost
   exactly +1 Toffoli).  A SAT-AND program for the new wire is the only missing artifact
   (`tools/minand_sat.py`, unpublished; the tree's three programs are used).
3. Then `product_forward` / `divider_cleanup` / `coefficient_inverse`, 4 slots each — dead-wire
   reclamation with one-time XOR zeroing (free CX) if identities can be found.

## 8. Files

| path | purpose |
|---|---|
| `gen_v12loader.py`, `kaggle/v12loader/` | loader certificate re-search at caps 20/19/18 + drop-in census |
| `gen_v12valid.py`, `kaggle/v12valid/` | cap 19/17/16 searches + first (scrubbed-env) validation attempt |
| `gen_v12cap17.py`, `kaggle/v12cap17/` | cap-17 search + Q=42 census naming `coefficient_forward` |
| `gen_v12proof17.py`, `kaggle/v12proof17/` | **manual-pipeline proof of the cap-17 loader body (PASS)** |
| `gen_v12census.py`, `kaggle/v12census/` | build gate + per-block allocation census (RESULT2) |
| `gen_v12blocks.py`, `kaggle/v12blocks/` | Q=45/44/42 enforced-width runs + 46-peak live sets (RESULT2) |
| `RESULT.md`, `RESULT2.md` | emitted-file study of `f2cdab0b`; v12 census and blocker table |
