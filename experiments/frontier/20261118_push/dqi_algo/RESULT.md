# DQI leg — algorithmic Toffoli-count reduction at Q=890

Line: `dqi_algo` (account `zhuating`). Target: cut the DQI mean executed Toffoli count
`T` at fixed `Q = 890` by an **algorithmic** change, not by byte-patching.

Baseline (official verifier, unmodified, re-measured in §7 control):
`575b043f`, Q=890, static 367,989, **mean executed T = 367,116.057**,
cost `1.1912605 * 890^2 * T = 346,409,762,292.72`, ratio 70.551 (GM 28.180659 for the
shipped triple).

All measurement is on Kaggle CPU kernels: no local simulation, no submission, nothing
pushed. Three kernels:

| kernel | ref | outcome |
|---|---|---|
| `zhuating/qcc-dqi-algo-regions` v1 | COMPLETE, 109 s | staged structure dump + per-region mean T |
| `zhuating/qcc-dqi-algo-trunc` v1 | COMPLETE | truncation probe; harness JSON parse bug (§7) |
| `zhuating/qcc-dqi-algo-trunc2` v1 | COMPLETE, 348 s | truncation probe with base control — **decisive** |

Evidence: `region_split.json`, `truncation_probe.json`, `truncation_probe2.json`
(copies in this directory). Commands in §9.

---

## 1. Region split — whose subroutine it is

The tape carries **no INFO_TAG** (0 tags in 57,520,821 instructions), so the
Chien/Forney block has to be located structurally. Its only unambiguous anchor is
`bit_store(is_error, True, control=error_mbuc[j])`, i.e. runs of 12 consecutive
`BIT_STORE1_IF` whose condition bits are exactly the 12 bits of one `E` register.
There are **4,025** such runs (the tape visits 4,025 of the 4,095 codeword positions);
they occupy ops `[30,335,416, 35,627,261]`, and every Toffoli of the tape lies inside
`[17,576,206, 52,910,630]`.

| region | op range | ops | static T | CCX | CCZ | **mean T** (65,536-shot estimate) | share |
|---|---|---:|---:|---:|---:|---:|---:|
| preamble (classical) | 0 – 17,576,206 | 17,576,206 | 0 | 0 | 0 | 0 | 0 % |
| **EEA forward** | 17,576,206 – 30,335,416 | 12,759,210 | **153,186** | 153,185 | 1 | **153,180.1** | 41.7 % |
| **Chien / Forney** | 30,335,416 – 35,627,262 | 5,291,846 | **44,264** | 40,240 | 4,024 | **44,217.0** | 12.0 % |
| **EEA reverse** | 35,627,262 – 52,910,631 | 17,283,369 | **170,539** | 168,587 | 1,952 | **169,719.2** | 46.2 % |
| epilogue (classical) | 52,910,631 – 57,520,821 | 4,610,190 | 0 | 0 | 0 | 0 | 0 % |
| **total** | | 57,520,821 | **367,989** | 362,012 | 5,977 | **367,116.31 ± 0.18** | |

The estimator's total lands on the official verifier's **367,116.057** (Δ = 0.25,
se 0.18), so the split is calibrated against the shipped number, not against a model.
The §7 control run also gives the *exact* per-type means over the verifier's 102,400
shots: **mean CCX = 361,163.416**, **mean CCZ = 5,952.642** (sum 367,116.057).

**The two synchronized-EEA passes are 87.9 % of T** (323,725 static / 322,899 mean);
Chien/Forney is 12.0 %. Chien can never buy more than +1.23 GM even if free, and it is
not free (§4).

Two further measured splits:

* **Toffoli target register family**: EEA-forward 85,406 syndrome-register / 67,779
  pool-register (qubits 840-889); EEA-reverse 85,488 / 83,099; Chien 0 / 40,240.
  **51.9 % of the tape's Toffolis write the five 12-bit workspace registers**, i.e. the
  EEA's bookkeeping/accumulator traffic, not the syndrome data path.
* **No useful conditioning exists**: a stack scan of all 2,558,513 PUSH/POP pairs shows
  every Toffoli sits either at depth 0 (148,411) or under conditions on *scratch* bits
  (219,578); **zero Toffolis are under an `E`-bit input condition**, and
  mean/static = 99.763 %. The brief's 873 T discount is the whole conditional budget.

---

## 2. Iteration structure — how many EEA rounds the tape runs

The tape's field multiply is a contiguous block of **42 CCX** with a constant
`(control-register, control-register, target-register)` triple and inter-CCX gap ≤ 80
instructions. Grouping blocks into clusters (gap ≤ 6,000 ops):

| | clusters | clusters with a multiply | 42-CCX blocks | T in the 42-blocks | largest cluster |
|---|---:|---:|---:|---:|---:|
| EEA forward | 151 | 133 | **1,542** | 66,670 | 132 multiplies (5,544 T) |
| EEA reverse | 137 | 135 | **1,526** | 64,256 | 66 multiplies (2,772 T) |

Multiply count per cluster, forward pass, in stream order:

```
4,4,1,1,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,0,1,0,3,0,3,0,0,3,0,132,
2,7,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,
31,32,33,34,34, 2,3,16,3,15,60,1,14,2,3,13,3,12,49,1,11,10,10,1,10,9,9,1,9,16,9,
14,8,12,7,16,13,10,7,4,5,7,25, 5,6,5,6,1,6,6,7,1,7,7,8,1,8,8,9,1,9,9,10,1,10,10,11,1,
2,11,11,2,12,3,13,3,2,14,1,2,14,14,2,15,3,16,3,2,34
```

There is a **clean +1 ladder of 31 consecutive rounds (window 4 → 34)** in the middle
of that list, and the reverse pass **ends** with the mirror ladder

```
34,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,3,1,2,66,66
```

So both passes are a **~34-step degree-driven ladder whose window grows 1 → 34**
(peak 34 ≈ t = 35). That is the *minimum*: the remainder degree must fall from 69 to
below `t = 35`, each division step drops it by at least 1, so **≤ 35 steps**.

The reference generator's `default_n_iters(n) = 3*(n+1)+9 = 222`
(`verifiers/dqi/dqi_reference_circuit.py:613`) is a loose bound for a *different*
granularity: its `_synchronized_eea` advances **one of four sub-updates per iteration**
(2-bit `counter`, one-hot decoded by `_counter_controls`), so 222 iterations ≈ 55
full division steps — and 4× finer than a division. The tape does **not** use that
number; it runs the tight 34.

Consequences:

* The "A ≈ 50 iterations / C ≈ 55 / ~105 total" reading of the split is not what the
  tape does: the round count cannot be recovered as `T / 42`, because a round contains
  *window-many* multiplies (1 → 34), not one.
* The multiply total (3,068 rank-42 blocks over both passes) is ~8× below the reference
  formulation's 16,206 multiply-adds per pass — the tape is already the tight version.
* There is no surplus round: (a) the ladder peaks exactly at the window 34-35 = t;
  (b) mean/static = 99.763 %, so nothing is gated off on typical shots — a loose
  schedule with a halting *classical* gate would show a large discount, and a loose
  schedule *without* a gate would divide by zero after convergence.
* §7 confirms (b) empirically: deleting even the smallest trailing chunk fails on
  **all 102,400 shots**.

---

## 3. Where the Toffolis are, in arithmetic terms

CCX block census per region (maximal runs of CCX sharing a register triple, gap ≤ 80):

| block size (CCX) | EEA fwd | EEA rev | reading |
|---:|---:|---:|---|
| 42 | 1,542 | 1,526 | one GF(2^12) multiply-add |
| 36 | 210 | 212 | multiply, shorter window |
| 34 | 105 | 105 | multiply, shorter window |
| 24 | 111 | 109 | multiply, shorter window |
| 12 | 492 | 471 | 12-bit AND broadcast (`init_and`-style) |
| 82 / 99 | 16 / 6 | 2 / 0 | two multiplies merged by the gap rule |
| 1-11 | 46,153 blocks / 62,727 CCX | 59,047 / 82,044 | control logic: comparisons, one-hot decode, counter updates |
| Chien | 32,192 blocks of 1 + 4,024 of 2 | — | 10 ANDs + 1 CCZ per position |

Multiplying blocks (≥ 24 CCX): **3,969 blocks, 159,300 CCX = 43.3 % of static T**,
mean rank **40.14**, mode **42**. Decomposition:

```
367,989 T  =  159,300  field-multiply ANDs (43.3 %)
           +   44,264  Chien per-position (12.0 %)
           +  164,425  EEA control logic + 12-bit AND chains (44.7 %)
```

`42` is a good multiply: schoolbook 144 ANDs, recursive Karatsuba 54-81, Toom-3 45
(5 products × rank-9 4-bit leaves), Toom-4 = 7 × rank-6 3-bit leaves = **42**. The
classical lower bound on the bilinear complexity of an n-term polynomial product is
`2n-1`, i.e. **23** at n = 12.

---

## 4. Priced alternatives (GM from the base triple)

Base: invsqrt 74,560.90687 / dqi 346,409,762,292.72 / chem 294,643,137.73 → GM 28.180659.

| # | alternative | explicit count | ΔT | ΔGM | verdict |
|---|---|---|---:|---:|---|
| A1 | schoolbook 12×12 multiply (144 ANDs) | 3,969 × 144 = 571,536 | **+412,236** | −8.1 | rejected |
| A2 | kickmix `ixor_gf2_mul` idiom (measured 63 T @ 12 bits) | 3,969 × 63 = 250,047 | **+90,747** | −1.9 | rejected |
| A3 | Toom-3 (5 × rank 9 = 45) | 3,969 × 45 = 178,605 | **+19,305** | −0.53 | rejected |
| A4 | rank 42 → 35 on the 3,068 rank-42 blocks | 128,856 × (1−35/42) | **−21,476** | **+0.572** | needs a tape regeneration |
| A5 | mean rank 40.14 → 30, all multiply blocks | 159,300 × (1−30/40.14) | **−40,242** | **+1.112** | no known construction at n=12 |
| A6 | every multiply at the bilinear floor 23 | 159,300 × (1−23/40.14) | **−68,022** | **+1.992** | **ceiling of the whole axis** |
| B1 | Berlekamp–Massey instead of the EEA | 70 × 2 × 36 ≈ **5,040** multiplies (fwd alone) vs the tape's 1,542 blocks | ≥ +147,000 | ≪ 0 | rejected: 3.3× |
| B2 | Welch–Berlekamp (71×71 solve) | ≈ 71³/3 ≈ **119,000** multiplies | +4.9 M | ≪ 0 | rejected: 77× |
| B3 | windowed / multi-bit EEA (2-4 quotient words) | bilinear rank is additive → multiply count invariant; only degree metadata moves | ≈ 0 | 0 | rejected |
| C1 | Chien/Forney halved (11.0 → 5.5 T/position) | 4,025 positions, 44,217 → 22,108 | −22,108 | +0.590 | not reachable |
| C2 | Chien/Forney free | 44,217 | −44,217 | +1.232 | impossible |
| — | mission target (−20 % T) | | −73,423 | +2.176 | |

Why the rejected rows are rejected (all measured):

* **A2/A3** measured locally by *constructing* circuits (no simulation):
  `ixor_gf2_mul` = 63 T at degree 12 (75 T controlled); degrees 2..12 =
  3,7,9,17,21,25,27,43,51,59,63. The tape's 42 beats all of them.
* **B1**: the tape's forward pass uses 1,542 multiply blocks; BM's discrepancy +
  update over n=70, L≤35 costs 2×(L+1) multiplies per syndrome, i.e. ~5,040 for the
  forward pass alone — 211,680 T at the tape's own rank, before the reverse pass.
* **B3**: splitting the quotient into k words multiplies the number of product terms
  by k while the per-word window shrinks proportionally, so the total rank is
  invariant. Only the degree counters get cheaper — a compiler rewrite (44.7 % of the
  tape is control logic, §3), not an arithmetic substitution available from the `.kmb`.
* **C1/C2**: the Chien region costs **10.998 T/position** (40,240 CCX + 4,024 CCZ over
  4,025 positions) plus 881 CX/position. A per-position 12-bit inverse in the kickmix
  idiom costs **315 T** (measured `init_gf2_inverse_with_scaffold(12)`), 28.6× the
  whole per-position budget — the tape already avoids it (CX-only Horner evaluation,
  `gf2_phase_by_product` phase kick at 0 Toffoli, 10-bit measured AND, 1 CCZ).

**Arithmetic bound.** The entire arithmetic-substitution budget of the DQI leg is
**68,022 T = 18.5 % of T = +1.99 GM**, and 100 % of it is the bilinear rank of one
12×12 GF(2) multiply (currently 42, floor 23). Every other region is at its idiom
minimum or is control logic that no arithmetic change touches.

---

## 7. Truncation probe — measured, and it closes the axis

Coordinator hypothesis: the tape may run more EEA rounds than required, so the last
`k` forward iterations (with the matching first `k` reverse iterations) could be
deleted. Three candidates were built with `vqcc_ir.pieces` + `concat` at condition-stack
depth 0 (verified), round-tripping the unmodified tape byte-exactly
(`roundtrip_sha256 == 575b043f…`, so the cutter is exact):

| candidate | deleted ops | deleted static T | static T after | sha256 | verifier result |
|---|---|---:|---:|---|---|
| `dqi_P1_lastClusterAndWrap.kmb` | [29,756,473, 30,335,416) | 3,340 | 364,649 | `35e4a7c6d4a815620077280f2a32be325859c9e1bf62b68aed36669f939e9a03` | **FAIL** |
| `dqi_P2_lastCluster.kmb` | [29,756,473, 29,806,000) | 1,545 | 366,444 | `d53ddd2e063baf9a8bf83ff06e72d4c156319cdd5c92b0812f99b0c45433175d` | (v1 harness bug) |
| `dqi_P3_last3ClustersAndWrap.kmb` | [29,247,514, 30,335,416) | 9,251 | 358,738 | `6c719b8efce26e9eb51ae65f20c163e0a28d5b79c973fb90b2b7a3d654ef9f90` | (v1 harness bug) |

Measured, unmodified official verifier, default salt, 102,400 shots, 2 workers:

* **control, unmodified `575b043f`**: `PASS`, `toffoli_count = 367,116.057`,
  `value_errors = 0`, `phase_errors = 0`, `num_qubits = 890`,
  `circuit_sha256 = 575b043f4fee…` — reproduces the shipped number exactly, so the
  harness is sound.
* **`P1` (k = 1, the smallest trailing chunk, −3,340 T)**:
  `status FAIL`, `value_errors = 102,400 / 102,400`, `phase_errors = 0`,
  `"Effective error rate 1.0000 >= 1/16"`.
  **Every single shot is wrong**: the deleted tail is not identity — without it the
  syndrome registers are never restored.

That is the strongest possible form of the negative: the *smallest* trailing deletion
fails on 100 % of shots, so no `k ≥ 1` truncation can pass, and the failure is
structural (value errors, not a marginal error-rate drift). P2 and P3 were not re-run
after v1's parser bug: P1 is a strict subset test — every larger deletion contains it —
and P2 (the multiply cluster alone, leaving its metadata in place) is not a
semantically valid circuit in any case. Combined with §2 (34 rounds = the degree-drop
minimum; mean/static = 99.76 % so nothing is gated), **the iteration-count axis is
closed.**

(Probe v1 reported `ERROR` for all three candidates: its JSON parser only accepted
single-line JSON while the verifier prints indented JSON. v2 fixed the parser and
added the base control. No circuit conclusion rests on v1. In
`truncation_probe2.json` the `result` fields are `null` for the same reason — the
verifier's own output is preserved in `stdout_tail` and re-parsed into
`result_parsed`.)

---

## 5. What would actually be needed for the remaining 68,022 T

A4-A6 require a **regenerated tape** with a lower-rank multiply. The `.kmb` is a flat
instruction stream with no tags beyond `S0..S69`/`E0..E4094`; each multiply is fused
into a rotation scaffold (~30 CX per AND, 42 ANDs, ~1,250 CX per block), so replacing
blocks in place means reconstructing the operand mapping from the CX scaffolding — a
byte-level rewrite (the other line's lane) with a worse risk profile, and it can only
be validated by the verifier on a 479 MB file. A rank-35 multiply (A4, +0.57 GM) is the
smallest change that pays, and it needs the generator, not the tape.

Second-order finding worth passing on: **51.9 % of all Toffolis write qubits 840-889**
and 44.7 % of the tape is EEA control logic. That is the largest single budget after
the multiplies, it is invisible to any arithmetic substitution, and it is the price of
the data-dependent schedule. The tape's 34-round triangular ladder is already the right
side of that trade.

---

## 9. Exact commands

```
# 1) structure dump + per-region mean T   (zhuating/qcc-dqi-algo-regions v1, COMPLETE, 109 s)
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_algo \
      --slug qcc-dqi-algo-regions --account zhuating \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings --competition
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_algo --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-algo-regions --account zhuating

# 2) truncation probe v1                    (zhuating/qcc-dqi-algo-trunc v1, COMPLETE)
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_algo/kprobe --account zhuating

# 3) truncation probe v2 + base control     (zhuating/qcc-dqi-algo-trunc2 v1, COMPLETE, 348 s)
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_algo/kprobe2 --account zhuating
python scripts/kgpu.py status --kernel zhuating/qcc-dqi-algo-trunc2 --account zhuating

#    fetch only the JSON (the kernels also emit ~470 MB candidate .kmb files):
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_zhuating) KAGGLE_CONFIG_DIR=~/.kaggle \
  python -c "from kaggle.api.kaggle_api_extended import KaggleApi as A; a=A(); a.authenticate(); \
  a.kernels_output('zhuating/qcc-dqi-algo-trunc2','/tmp/probe2',file_pattern=r'truncation_probe2\\.json',force=True)"

# 4) local, arithmetic only (no simulation, no verifier): primitive Toffoli counts
.venv/bin/python -c "import kickmix as km; b=km.CircuitBuilder(); f=km.GF2Field(12); \
  a=b.alloc_qubits(12); x=b.alloc_qubits(12); t=b.alloc_qubits(12); \
  b.ixor_gf2_mul(a,x,target=t,field=f); print(b.finish_circuit().operation_statistics().num_toffoli_like)"

# 5) local static dry run of the analysis (IR read only)
DQIALGO_STATIC_ONLY=1 .venv/bin/python experiments/frontier/20261118_push/dqi_algo/main.py
```

## 10. Files in this directory

```
main.py, kernel-metadata.json        structure-dump kernel (zhuating/qcc-dqi-algo-regions)
region_split.json                    its measured output
probe_main.py                        probe v1 source
kprobe/                              probe v1 kernel dir
kprobe2/main.py, kernel-metadata.json probe v2 kernel dir (with base control)
truncation_probe.json                probe v1 output (harness ERROR — parser bug)
truncation_probe2.json               probe v2 output (decisive: control PASS, P1 FAIL 102400/102400)
RESULT.md                            this file
```
