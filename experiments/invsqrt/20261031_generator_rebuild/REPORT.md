# invsqrt generator rebuild, 2026-10-31

The 5% cost target is still open. This report does not claim that target. The best measured circuit costs **144,556.97**, against the recorded baseline **100,940.61** and the planning threshold **95,893.58**. No portfolio zip was written, and no zip is presented as meeting the target. No Kaggle submission was made. The full official verifier was not run.

## Source reproduction

Branch `invsqrt-generator-rebuild`. The comparison baseline is the read-only file `artifacts/20261030_public_best/candidate/invsqrt.kmb`, SHA-256 `6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4`, recorded cost `100,940.61`. The official verifier path is `data/competition/verifiers/invsqrt/verify_submission_invsqrt.py`, SHA-256 `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a`. It was not modified.

Dmitrii dataset `dmitriigluzdov/vqcc-femoco-public-factorization` version 39, Apache-2.0, retrieved 2026-10-31. The minimum `marsyas` and `round10` sources are in `vendor/`. Generation imports the explicit modules in `src/`, not the upstream source-rewriting entry points and not a Linux `kickmix.so`. File hashes:

| file | sha256 |
| --- | --- |
| `vendor/model.py` | `65bf89538e736f5d02add43c7f74bb57c02b4fa3f699df02b9e83cd984a58162` |
| `vendor/build.py` | `eef91d07c4c99d92545272d5d6e4daeb78a925e3d7307d27b093699d34f49e3e` |
| `vendor/hsplit.py` | `fc1fa942a08425bc580980d980b3cd34bfcda47f6db6b7ab137595ae2d4513ec` |
| `vendor/fit.py` | `0ab68492466fde0156cb54379a4e18d6673b183d83e4674101f55b58a43111d0` |
| `vendor/round10_inv.py` | `8450a5ccbc2730d59abea83d36688036dd614d3054757f623f9bdc35bea91cb9` |
| `vendor/round10_lookup.py` | `6444cef6426ea9f3485792118e1ae714d4b765e20ae4d1a9fa0b57f6173a5bc7` |
| `vendor/round10_virtual.py` | `6b72cfb26841262d33a6fa27ab109310a93f1b066fd2afe206a1c308eb27d5bb` |
| `vendor/round10_fit.py` | `3ae38a7c4bb5e959328a0f1500ad81696d6a527d6dda96643ac7586cd7d17500` |
| `vendor/LICENSE` | `3ddf9be5c28fe27dad143a5dc76eea25222ad1dd68934a047064e56ed2fa40c5` |

The same hashes are in `PROVENANCE.json`.

The reproduced recipe is `F0=28`, `FT=19`, `F2=8`, `G0=1`, `LB=21`, `S=20`, signed-digit rows with `dropA=[5]`, `tcap` on, derivative virtual low bit, curvature retire 3, direct unary lookup, and the upstream window plan `17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0`. Two builds wrote the same canonical KMB SHA-256 `994c1c41469fc38eedf01b048979ff1c74fd654e025f33cf3fafd0b483d03858`. This recipe is another version. It does not reconstruct `6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4`.

Integer truncation, rounding, overflow, and phase units are printed by `generate_circuit.py`. In short: right shifts floor; signed-digit rows round half up; `T` must stay in `[0, 2^(FT-1))` and `Y'` in `[0, 2^(F0-1))`; angles are integers of `2^-64` turns, and `Z_POW` takes half-turns. The HMR cleanup is measurement-record version 1: after an even unshift of width `d`, the flag is 1 exactly when the top `d` bits are 0; the conditional prefix parity cancels the measured branch. Lookup and curvature masks use the same `(-1)^{m · table[address]}` correction. Entry wires are the 22-bit `x` register plus clean ancillas. Exit wires are restored `x` and zero scratch. The total phase is the sum of the high-word and low-word calibrated angles. Equality of instruction text was not used as a proof; the simulator phase was compared with `hsplit.phases_multi`.

## Full-domain classical check

`screen_classical.py` walked all **3,133,452** legal inputs of the published coefficient and phase tables. Tolerance violations **0**, overflows **0**, minimum absolute margin **51,187,461** units of `2^-64` turns, maximum error/tolerance **0.9999341616745385**. Named sets covered normalization boundaries, segment endpoints, segment centers, carry boundaries, and `x=161`, `x=888`. On those two tight points of the submitted 62Q circuit, this model uses only 0.308 of the tolerance. This is a model pass, not a circuit pass and not an official PASS. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/classical_screen.json`.

`search_grid_margin.py` then refit every cell of mantissa segment bits `{6,7}` × `F0∈{27,28,29}` × `FT∈{18,19,20}` × `F2∈{7,8,9,10}` × `G0∈{0,1,2}`: **216** cells, each with radius `rad1=6`, `rad2=3` and local descent. None is a truncation of the published table, and none is identical to it. Every cell records the full-domain absolute margin. Where that margin is positive, synthesis is `n_rot * (0.56 log2(1/eps)+5.3)` with `n_rot = F0-G0+7` and `eps = pi * margin / 2^64 / n_rot`. A non-positive margin leaves `synthesis_T` null. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/grid_margin.json`.

| segment bits | cells | numeric pass | positive absolute margin | synthesis charged |
| --- | ---: | ---: | ---: | ---: |
| 6 | 108 | 0 | 0 | 0 |
| 7 | 108 | 35 | 35 | 35 |

The least-negative 6-bit margin is **-3,761,524,881** at `F0=28, FT=20, F2=10, G0=2`, first failure `x=65`. The largest 7-bit margin is **346,366,659** at `F0=29, FT=20, F2=10, G0=0`, synthesis **980.08 T**. The cheapest positive synthesis is **913.40 T** (228.35 Toffoli-equivalents) at `F0=28, FT=20, F2=10, G0=2`. The recipe-precision refit passes with margin **40,189,295** and synthesis **983.22 T**, which is a different table from the published one. These synthesis figures are not measured circuit costs. The emitted circuit uses 44 general rotations, not `F0-G0+7`.

## Local simulation

`diagnose_circuit.py --mode local` rebuilt the reproduced circuit and simulated four fixed input sets. Simulator seeds were `101`, `202`, and `303`. Those seeds drive the simulator. They do not redraw the inputs.

The uniform set is the existing 8,192-draw from numpy seed `20261030` (8,187 unique). The boundary set is the existing 2,816 slots (2,791 unique). Segment endpoints are the union of the 6-bit and 7-bit bin edges: all 383 seven-bit screen endpoints, all 352 six-bit endpoints, and the occupied-segment minima and maxima, 704 unique in total. Counterexamples are the 240 recorded first-failure and worst inputs from `grid_margin.json` and `cubic_control.json`, padded to 256 slots. That list includes `x=1`, `x=65`, `x=161`, `x=193`, `x=888`, `x=2049`, `x=753025`, `x=966657`, `x=1032289`, `x=2206945`, and `x=2621345`.

Every one of the 35,904 shots restored `x`, left scratch clear, and matched `hsplit.phases_multi`. This sample is not an official PASS.

Executed Toffoli-like means, weighted by shots:

| set | shots | seed 101 | seed 202 | seed 303 |
| --- | ---: | ---: | ---: | ---: |
| uniform | 8,192 | 1,343.5546875 | 1,342.9375 | 1,342.75 |
| boundary | 2,816 | 1,343.5546875 | 1,342.9375 | 1,342.75 |
| segment endpoints | 704 | 1,343.559659090909 | 1,342.9375 | 1,342.7017045454545 |
| counterexamples | 256 | 1,343.5546875 | 1,342.9375 | 1,342.75 |

Mean T-like gates 1. Mean general rotations 44. Qubits **87**. The uniform mean across the three seeds remains **1,343.08**.

With the published margin 51,187,461, rotation synthesis is 1,272.97 T. Equivalent cost `C = 1,661.57`. Score `Q * C = 144,556.97`. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/local_diagnosis.json`.

The batch loop now keeps one measurement stream per simulator seed instead of constructing a new simulator for every batch. Two successive batches of the fixed numpy-seed `20261030` uniform draw, both under simulator seed `101`, have measurement fingerprints `fcb00b4d79f10a511a7b41906a29b2a69f1e6fc470277f6712bfcb0859815937` and `5e707e5805c51fb6ccfde3dae68f3b2d5cd176f3636986b75a33274acfac71de`. Repeating the first batch reproduces the first fingerprint. Both batches restored `x`, cleared scratch, and matched the model phase. Executed Toffoli-like means were 1,342.75 and 1,343.0234375. This sample is not an official PASS. The table above was measured when each batch restarted the seed.

## Full official verification

Not run, and this section does not record an official PASS. No candidate that passed the classical screen and the local diagnosis has a measured cost at or below 0.95 times the recorded baseline, so the 200,540,928-shot verifier was not started for the baseline seed `20261031` or a candidate seed `20261101`. A shorter run is not a substitute. Python in this workspace is 3.12 and kickmix is 1.0.0; that stack was used for generation and the local sample only. No portfolio zip exists for this experiment.

## Actual cost change

The 5% target is still open. The best measured cost is **144,556.97**. That is the executed reuse circuit, not a grid synthesis estimate. No portfolio zip was written.

| circuit | qubits | executed Toffoli-like | score | versus 100,940.61 |
| --- | ---: | ---: | ---: | ---: |
| recorded 62Q baseline | 62 | about 1,331.5 | 100,940.61 | 1 |
| planning threshold |  |  | 95,893.58 | 0.95 |
| best emitted recipe | 87 | 1,343.08 | 144,556.97 | 1.432 |

The best emitted score is 43.2% higher than the recorded baseline. Free synthesis would still leave `87 * 1,343.33 = 116,869.77`, which is above both the recorded baseline and the threshold. The gap is the width. The adder-carry peak during the output Horner is 87 qubits (`B add n=20`), and every schedule stayed at or above that.

Charging the cheapest positive grid synthesis (228.35 Toffoli-equivalents) on top of the measured 1,343 Toffolis at 87 qubits still gives about **136,700**, above 95,893.58. That figure is an illustration from before the fit and the angles were required to correspond. It does not exclude those cells. The corrected evaluation is in the next section. The 108 six-bit cells have negative margins, so they have no synthesis charge and no cost win.

## Corrected evaluation of the 35 passes

The 35 seven-bit cells that passed the earlier grid were refit with the even constant word and the derivative virtual-bit parity inside the score. An even-word adjustment changes none of those constant words. None is a truncation of the published table. A cell is not excluded because the earlier mismatched-angle or width-fixed illustration was expensive.

`F0=27, FT=20, F2=10, G0=0` fails the constrained model: 10 tolerance violations, overflow 0, absolute margin **-79,381,055**, first failure `x=734557`. It has no circuit cost.

`G0=0` phases the real low-word LSB. `u` is even, so that bit is `(Y' - C0) & 1`, the parity of the rounded output rows, not a fresh `|0>`. A smoke sample of `F0=28, FT=19, F2=8, G0=0` and one of `F0=28, FT=20, F2=8, G0=0` both restored `x`, cleared scratch, and matched the model phase.

The other 34 cells that pass the constrained model were built on that path. Angles are the absolute-margin calibration of that table. The recipe-precision refit reproduces the published even table, so it keeps the published calibration. Qubits run from 87 to 98. Static Toffoli-like counts run from 1,354 to 1,465. The lowest static product is `87 × 1,354 = 117,798`, which is above 95,893.58 before rotation synthesis.

| F0 | FT | F2 | G0 | status | margin | Q | static Toffoli | angles |
| ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 27 | 20 | 10 | 0 | fail | -79,381,055 |  |  | model failed, no circuit |
| 28 | 19 | 8 | 0 | measured | 5,891,269 | 87 | 1,360 | calibrated to this table |
| 28 | 19 | 8 | 1 | measured | 5,891,269 | 87 | 1,354 | published table calibration |
| 28 | 19 | 9 | 0 | measured | 101,134,417 | 88 | 1,371 | calibrated to this table |
| 28 | 19 | 9 | 1 | measured | 71,904,517 | 88 | 1,364 | calibrated to this table |
| 28 | 19 | 9 | 2 | measured | 26,994,355 | 88 | 1,359 | calibrated to this table |
| 28 | 19 | 10 | 0 | measured | 115,821,808 | 89 | 1,370 | calibrated to this table |
| 28 | 19 | 10 | 1 | measured | 115,821,808 | 89 | 1,366 | calibrated to this table |
| 28 | 19 | 10 | 2 | measured | 37,859,211 | 89 | 1,359 | calibrated to this table |
| 28 | 20 | 8 | 0 | measured | 106,855,201 | 88 | 1,398 | calibrated to this table |
| 28 | 20 | 8 | 1 | measured | 106,855,201 | 88 | 1,392 | calibrated to this table |
| 28 | 20 | 9 | 0 | measured | 208,335,547 | 89 | 1,410 | calibrated to this table |
| 28 | 20 | 9 | 1 | measured | 205,424,028 | 89 | 1,405 | calibrated to this table |
| 28 | 20 | 9 | 2 | measured | 151,436,154 | 89 | 1,398 | calibrated to this table |
| 28 | 20 | 10 | 0 | measured | 236,384,815 | 90 | 1,415 | calibrated to this table |
| 28 | 20 | 10 | 1 | measured | 222,681,612 | 90 | 1,409 | calibrated to this table |
| 28 | 20 | 10 | 2 | measured | 177,976,186 | 90 | 1,403 | calibrated to this table |
| 29 | 19 | 8 | 0 | measured | 125,343,749 | 95 | 1,408 | calibrated to this table |
| 29 | 19 | 8 | 1 | measured | 125,343,749 | 95 | 1,402 | calibrated to this table |
| 29 | 19 | 8 | 2 | measured | 37,063,412 | 95 | 1,396 | calibrated to this table |
| 29 | 19 | 9 | 0 | measured | 186,386,851 | 96 | 1,418 | calibrated to this table |
| 29 | 19 | 9 | 1 | measured | 167,220,594 | 96 | 1,412 | calibrated to this table |
| 29 | 19 | 9 | 2 | measured | 157,157,806 | 96 | 1,407 | calibrated to this table |
| 29 | 19 | 10 | 0 | measured | 200,775,026 | 97 | 1,420 | calibrated to this table |
| 29 | 19 | 10 | 1 | measured | 194,617,324 | 97 | 1,413 | calibrated to this table |
| 29 | 19 | 10 | 2 | measured | 170,510,980 | 97 | 1,407 | calibrated to this table |
| 29 | 20 | 8 | 0 | measured | 196,867,263 | 96 | 1,448 | calibrated to this table |
| 29 | 20 | 8 | 1 | measured | 181,101,203 | 96 | 1,442 | calibrated to this table |
| 29 | 20 | 8 | 2 | measured | 164,145,343 | 96 | 1,436 | calibrated to this table |
| 29 | 20 | 9 | 0 | measured | 293,143,425 | 97 | 1,461 | calibrated to this table |
| 29 | 20 | 9 | 1 | measured | 293,143,425 | 97 | 1,455 | calibrated to this table |
| 29 | 20 | 9 | 2 | measured | 290,148,643 | 97 | 1,449 | calibrated to this table |
| 29 | 20 | 10 | 0 | measured | 321,057,626 | 98 | 1,465 | calibrated to this table |
| 29 | 20 | 10 | 1 | measured | 335,065,303 | 98 | 1,459 | calibrated to this table |
| 29 | 20 | 10 | 2 | measured | 299,816,822 | 98 | 1,453 | calibrated to this table |

Adder peak on the corrected builder, published recipe: prefix 0 allocates **87** qubits at `B add n=20 cached=0`, static Toffoli-like 1,354. Prefix 8, the plain-qubit prefix attempt, still peaks at **87** on that same add and raises the static count to 1,372. The peak did not fall. The 5% target is still open. No portfolio zip was written. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/corrected_grid.json`.

## Failed routes and counterexamples

Recovery, with writes, reads, clears, and phase corrections counted. Scratch was clean on every simulated schedule. 64 qubits was not treated as a limit. The best measured score is still the executed reuse circuit at **144,556.97**. No schedule below is a 5% improvement, and no portfolio zip was written.

A fresh refit of `F0=28, FT=19, F2=8, G0=1` (proxy 0.963, not a truncation) was laid out at every neighbor of `LB=21, S=20`. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/recovery_split.json`.

| LB | S | refit layout | note |
| --- | ---: | --- | --- |
| 20 | 19 | no | nearest even C0 move on segment 0 is 20,272, far outside the absolute-margin budget |
| 20 | 20 | no | same obstruction |
| 21 | 19 | yes | nH=8; published-table build is Q 87 and 1,358 static Toffolis |
| 21 | 20 | yes | recipe split, nH=7 |
| 21 | 21 | no | C0 residue misses the low-word window; ±1,024 even search fails at segment 1 |
| 22 | 19, 20, 21 | yes | wider low word; published-table builds at S=20 and S=21 are Q 89 |

On that refit, three recovery schedules were built. `init_and` is the adder's product write and is inside the static Toffoli total; `del_and` is its clear. Explicit CCX, CSWAP, HMR, and Z_POW are counted separately.

| schedule | windows | carry bits | Q | static Toffoli | writes | reads | clears | phase corrections | decision |
| --- | ---: | --- | ---: | ---: | --- | --- | --- | --- | --- |
| reuse `17:11,10;…;7:1,0` | 6 | 2,2,2,2,2,2 | 87 | 1,355 | 801 init_and + 163 CCX | 20 CCX | 801 del_and + 11 CCX + 78 CSWAP + 5 HMR | 88 CCX + 104 CSWAP + 48 HMR + 47 Z_POW | reject: best measured score 144,556.97 stays above 95,893.58 |
| retain 1 intermediate | 1 | 7 | 92 | 1,455 | 911 init_and + 158 CCX | 15 CCX | 911 del_and + 11 CCX + 78 CSWAP + 5 HMR | same 88/104/48/47 | reject: Q 92 and static Toffoli 1,455, clears included, worse than reuse |
| retain 2 intermediates | 2 | 5,5 | 90 | 1,399 | 853 init_and + 159 CCX | 16 CCX | 853 del_and + 11 CCX + 78 CSWAP + 5 HMR | same 88/104/48/47 | reject: Q 90 and static Toffoli 1,399, clears included, worse than reuse |

The one-window and two-window plans do not fit in a 3-bit carry. They fit only at 7 bits and 5 bits, and both raise Q and the static Toffoli count. Retaining intermediates does not pay for itself.

Derivative high/low split. The upstream 1-guard window is **10** bits: bits below 10 stay in the low window, and bits at and above 10 are the high part folded through the guard. `derivative_split_sweep.py` refit `F0=28, FT=19, F2=8, G0=1` at radius `rad1=6`, `rad2=3` for each of 9, 10, and 11. None of those tables is a truncation of the published table. The arithmetic does not depend on the window, so each refit has the same full-domain absolute margin **40,189,295** and the same official synthesis charge **983.22 T**. The circuit cost does depend on the window. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/derivative_split.json`.

| split | guard | absolute margin | synthesis T | recovery-clear Toffolis | static Toffolis | Q | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 9 | no, low max 1084 exceeds limit 1024 | 40,189,295 | 983.2245431270703 | not built |  |  | reject: low window of the derivative does not fit the 1-guard range; recovery would be wrong |
| 10 | yes, low range -1443..1596, limit 2048 | 40,189,295 | 983.2245431270703 | 89, plus 801 free `del_and` clears and 5 HMR | 1,355 | 87 | reject: comparison row for the upstream split; score illustration 139270.13 stays above 95893.58, so this is not a 5% accept |
| 11 | yes, low range -2467..2547, limit 4096 | 40,189,295 | 983.2245431270703 | 89, plus 815 free `del_and` clears and 5 HMR | 1,369 | 87 | reject: higher qubits, billed Toffolis, or recovery-clear Toffolis than the upstream derivative split |

No row is a 5% accept. The target remains open. The best measured cost is still **144,556.97**.

Other rejected reuse variants, from `schedule_sweep.json`: retire 0 raises Q to 90; Cuccaro prefixes 8 and 16 do not fire on the peak add because its sources are computed products, so Q stays 87 and Toffolis rise.

The complete quadratic grid is the 216-cell refit in `grid_margin.json`. Every cell uses radius `rad1=6`, `rad2=3`. All 108 six-bit cells fail. Their absolute margins are negative, so synthesis is not charged; the least-negative margin is -3,761,524,881 and its first failure is `x=65`. Of the 108 seven-bit cells, 73 fail and 35 pass. The 35 passes improve some relative errors, including the recipe-precision refit at worst ratio 0.963 against the published table's 0.99993, and their synthesis charges run from 913.40 T to 980.08 T. None was emitted as a narrower circuit, and none has a measured score at or below 95,893.58. They are rejected.

Centered cubic on segment bits `{4,5}`, signed-digit Horner with a third multiply, from `cubic_control.py`. Stride 32. There is no passing point, so there is nothing to step back to.

| segment bits | F0 | FT | F2 | F3 | worst ratio | worst x | first failing x | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4 | 28 | 19 | 8 | 6 | 90.767 | 2621345 | 1 | fail |
| 5 | 28 | 19 | 8 | 6 | 19.373 | 131073 | 1 | fail |
| 4 | 36 | 28 | 16 | 12 | 1.753 | 2206945 | 2049 | fail |
| 5 | 36 | 28 | 16 | 12 | 3.077 | 966657 | 193 | fail |
| 7 | 28 | 19 | 8 | 4 | 1.026 | 1032289 | 1032289 | fail |
| Newton control |  |  |  |  | 2.548e-8 at x=753025 | 753025 | none on stride 64 | control only, not a candidate: 260 qubits, 7,735 static Toffoli-like gates |

The 7-bit row is the same fraction width as the quadratic recipe plus one cubic coefficient. It still fails, at `x=1032289`, and it would add a Horner multiply if it had passed. Newton is only a control, built by the unmodified `nr_reference_circuit.py`: 260 qubits, 7,735 static Toffoli-like gates. On stride 64 its worst sample is `x=753025` with relative error `2.548e-8`, under the tolerance `5.960e-8`. That is not a tolerance counterexample. The control is the width and the gate count. Artifact: `artifacts/20261031_invsqrt_generator_rebuild/cubic_control.json`.

## Why the target stays open

Beating 95,893.58 from a circuit whose Toffoli count is already about 1,343 requires the width to fall to about 71 even with free synthesis, and to about 57 at the measured synthesis cost. The register floor of this schedule is the live sum of the 22-bit input, the 20-bit low word, the 17-bit derivative, the remaining curvature bits, and the adder carries. On the corrected builder the carries still set the peak at 87 (`B add n=20`), and a prefix of 8 does not remove them. The lowest static product among the 34 built cells is 117,798. No searched precision, segment size, window plan, or cubic table produced a measured score under the threshold. The 5% target is still open.
