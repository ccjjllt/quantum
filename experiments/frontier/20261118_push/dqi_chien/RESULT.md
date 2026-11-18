# DQI — Chien/Forney phase mechanism: the 10 CCX are the quantum root predicate

Line: `dqi_chien` (account `jiyujia`). Question asked of this line: *is the 44,264 static T of the
Chien/Forney region (ops `[30,335,416, 35,627,262)`) a redundant encoding of the classical MBUC
mask `M_j`, replaceable by classically conditioned `Z` gates at 0 Toffoli?*

**Verdict: no. Lever closed.** The region contains no materialised 12-bit `e_j` register: the phase
is applied as a **multi-controlled phase on syndrome qubits**, where 10 of the 11 Toffolis are the
*quantum* predicate (an all-zero / Chien-root test on a 12-bit register) and the mask `M_j` is
already free (it enters only as `PUSH_CONDITION` / classically conditioned `CX`). There is no
classical bit register holding `e_j`, so "conditioned Z per error bit" has no operand.

Nothing was submitted, nothing was pushed, no verifier was run (no candidate was built). One
CPU-only Kaggle kernel (`jiyujia/qcc-dqi-chien-dump`) read the tape; it is staged from
`grantprater/vqcc-dqi-61c8348d-merged-closings`, never read locally.

---

## 1. Priced ceiling of the axis (for the record)

Base: `575b043f`, Q = 890, mean executed T = **367,116.046** (implied exactly by the shipped cost
`346,409,762,292.72 = 1.1912605 * 890^2 * T`), GM 28.180659.

| what is removed | ΔT | T after | cost after | GM | ΔGM |
|---|---:|---:|---:|---:|---:|
| the whole Chien region (impossible ceiling) | 44,217 | 322,899.05 | 304,686,714,197.60 | 29.4124 | **+1.232** |
| only the 40,240 CCX (the premise of this line) | 40,240 | 326,876.05 | 308,439,401,224.63 | 29.2926 | **+1.112** |

So the premise was worth pinning down: +1.1 GM if the CCX were mask redundancy. They are not
(§4). Achievable saving from the rewrite: **0 T**.

---

## 2. Tape identity and region counts (measured, kernel v2)

```
kmb sha256  575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155   479,128,738 bytes
num_ops 57,520,821    num_qubits 890    num_bits 66,726    registers 4,165 (70 S x 12 q + 4,095 E x 12 b)
BIT_STORE1_IF runs of 12 consecutive conditions = one E register : 4,025
anchors (first op of each run)  min 30,335,416  max 35,627,261   visited j range 7 .. 4094
region B Toffolis 44,264 = 40,240 CCX + 4,024 CCZ
distinct 11-Toffoli block signatures over the 4,025 anchors : 33 (top-10 group size 126 each)
```

`40,240 / 4,024 = 10` and `4,024 CCZ` — i.e. **exactly 4,024 complete blocks of 10 CCX + 1 CCZ
= 11 T**, and `4,024 x 11 = 44,264`. The 4,025th anchor sits at `B` and its block falls in
region C, which is why the region shows 4,024 CCZ rather than 4,025.

---

## 3. The block, dumped

Full listings: `evidence/window_p0.txt` (531 ops, 29 KB), `window_p1.txt`, `window_p2000.txt`,
`window_plast.txt`. Registers are printed as `S57[3]` = bit 3 of syndrome register S57,
`E2730[5]` = bit 5 of the classical MBUC register of position j = 2730.

### position 0 of the region, j = 2730, anchor op 30,335,416

| ops | what it is |
|---|---|
| 30,335,415 | `BIT_STORE0 B53665` — clear `is_error` |
| 30,335,416–27 | 12 x `BIT_STORE1_IF B53665 c=E2730[0..11]` — `is_error = OR_k M_j[k]` (the anchor) |
| 30,335,428 | `PUSH_CONDITION c=B53665` (`is_error`) — the body then runs at condition depth 93 |
| 30,335,429–40 | 12 x `X S57[0..11]` (complement the tested register) |
| 30,335,441–60 | **the 10 CCX**: `R Q881; CCX(S57[0],S57[1],Q881); R Q876; CCX(Q881,S57[2],Q876); … ; R Q888; CCX(Q864,S57[10],Q888)` — a chained conjunction, `Q888 = AND_{k=0..10} ~S57[k]`, i.e. **`S57[0..10] == 0`** |
| 30,335,461–71 | 11 x `BIT_STORE0` (clear scratch flags `B53666..B53676`) |
| 30,335,472–548 | selection cascade, k = 1..11: `BIT_INVERT_IF B536(77-k) c=E2730[k]`, `PUSH`, `SWAP S54[0],S54[k]`, 3 x `BIT_INVERT_IF` swapping `E2730[0] <-> E2730[k]`, `POP` |
| 30,335,549–81 | **the mask contraction**: for k = 1..11 `PUSH c=E2730[k]; CX(S54[k] -> S54[0]); POP`, with **`CCZ(Q888, S57[11], S54[0])` at 30,335,583 under `PUSH c=E2730[0]`** |
| 30,335,584–617 | the same contraction in reverse (uncompute, 11 `CX`) |
| 30,335,618–83 | the selection cascade in reverse (11 `SWAP`, E-bit swaps) |
| 30,335,684–703 | **measured uncomputation of the conjunction, 0 Toffoli**: `HMR Q888 -> B49782; CZ_IF(Q864,S57[10]) c=B49782; HMR Q864; … ; CZ_IF(S57[0],S57[1]) c=B49782` (10 HMR + 10 CZ_IF) |
| 30,335,704–15 | 12 x `X S57[0..11]` (restore) |
| 30,335,716–17 | `POP_CONDITION`; `BIT_STORE0 B53665` (clear `is_error`) |

Opcode census of the block (from the dump): 294 `BIT_INVERT_IF`, 46 `PUSH`/`POP`, 24 `X`,
22 `SWAP`, 22 `CX`, 14 `BIT_STORE0`, 10 `R`, 10 `HMR`, 10 `CZ_IF`, **10 `CCX`, 1 `CCZ`**.

The block is a template with rotating registers — position 2000 (j = 3949) is the same shape with
`S25` / `E3949` instead of `S57` / `E2730` — which is what the 33 distinct 11-Toffoli signatures
count.

---

## 4. Mechanism reading, against the official generator

`verifiers/dqi/dqi_reference_circuit.py::_chien_search_and_forney_mbuc`, lines 571–599, per position:

| line | reference call | role | tape's form (dumped) |
|---|---|---|---|
| 573 | `bit_store(is_error[0], True, control=error_mbuc[j])` | `is_error = OR(M_j)` | 12 `BIT_STORE1_IF` on `E2730[k]` (identical) |
| 574 | `push_condition(is_error[0])` | gate the block on `M_j != 0` | `PUSH c=B53665` (identical) |
| 576 | `cx(fwd_src, fwd_dst)` | CX-only Horner evaluation | the conditional `CX` contraction + 22 `SWAP` (CX-only) |
| 577 | `flip_if_equal(sigma, 0, target=is_sigma_zero)` | **quantum** predicate: is `alpha^{-j}` a root? | the **10 CCX** chain `AND_{k<=10} ~S(.)[k]` (all-zero test) |
| 579–580 | `init_gf2_inverse_with_scaffold(sigma_prime, …, …)` | per-position field inverse | **absent from the block** — it contains no inverse chain at all (11 Toffolis in total), so the tape's division is done elsewhere |
| 582 | `init_and(is_sigma_zero, omega, located)` | `located = predicate AND omega` (the ANDs) | the same conjunction, fused into the 10-CCX chain |
| 583–584 | `gf2_phase_by_product(located, sigma_prime_inv, mask=error_mbuc[j])` | phase, `mask` classical | **1 `CCZ`**, with the mask as `PUSH`/`CX` conditions |
| 585 | `del_and(is_sigma_zero, omega, located)` | 0-Toffoli uncompute (stabilizer) | 10 `HMR` + 10 `CZ_IF` (0 Toffoli) |
| 587–588 | `del_gf2_inverse_with_scaffold(...)` | uncompute the inverse | not needed |
| 591–595 | `flip_if_equal`, `cx(rev_src,rev_dst)`, `pop`, `bit_store(is_error,False)` | mirror | the reverse cascade / contraction / `POP` / `BIT_STORE0` |

**The decisive point for this line.** The 10 CCX are *not* a re-encoding of the classical mask.
They build a conjunction — an all-zero / root test — over **11 syndrome qubits**
(`S57[0..10]`), and the phase then needs one more quantum bit (`S57[11]`) plus the contraction bit
(`S54[0]`): a 13-input monomial, realised as 10 CCX + 1 CCZ. The classical `E2730` bits appear only
as `PUSH_CONDITION` and classically conditioned `CX`/`CZ_IF`, i.e. **the mask is already at 0 T**.
What is left is the quantum predicate, and a classical condition cannot supply it: at the phase
point the only object holding it is a qubit, and `HMR` there is not a read-out either — it is the
X-basis measurement the block already uses at 30,335,684–703 to uncompute the conjunction
coherently (a basis-state ancilla measured in X returns a *random* bit with Clifford corrections,
not the predicate value).

A classically conditioned `Z` needs a `km.b` operand per error bit; the tape never materialises the
12-bit `e_j`, exactly as in the reference, where the phase operand `located` is a *qubit* register
built from the quantum predicate at line 582.

---

## 5. The 11 T is the idiom floor (locally measured by construction, no simulation)

`.venv` kickmix 1.0.0, construction only, `operation_statistics().num_toffoli_like`:

| construct | toffoli_like |
|---|---:|
| `init_and(1 q-control, 12 q-targets)` (reference 582) | **12** |
| `init_and` + `del_and` (reference 582 + 585) | **12** (`del_and` = 1 `HMR` + 1 `CZ`, free) |
| `gf2_phase_by_product(12, 12, mask=12 bits)` (reference 583) | **0** (144 `CZ` + 104 `BIT_INVERT` + 10 `BIT_STORE0`) |
| `multi_controlled_x(12 controls, 1 target)` | **11** |
| `ccz(3 qubits)` | 1 |
| `z(km.b)` -> `NEG_IF` | **0** |
| `cx(km.b, qubit)` -> `CX_IF` | **0** |

Consequences:

* The tape's **11 T/position equals `multi_controlled_x(12,1)` = 11**, i.e. one Toffoli per
  conjoined bit minus one: it is the cost of the conjunction, not of the mask. `4,024 x 11 = 44,264`
  exactly.
* A faithful reference-style build of the same step would cost **12 T** for `init_and` alone
  (the tape is 1 T/position better), plus **315 T** for the per-position
  `init_gf2_inverse_with_scaffold(12)` (measured earlier on the `dqi_algo` line) which the tape's
  per-position block does not contain — the dumped block is 11 Toffolis in total. The tape is
  therefore ~29x below a faithful reference formulation of this step.
* `z(km.b)` and `cx(km.b, qubit)` costing 0 is precisely why the premise looked attractive — but the
  free gates are already used for the mask, and there is nothing classical left to condition on.

Residual note (not attempted, not priced): the only remaining direction would be to *share* the
conjunction across positions instead of rebuilding it per position — a regenerated tape, not a
patch, and outside this line's scope. The `.kmb` is a flat stream with no tags (0 `INFO_TAG` in
57,520,821 instructions, measured on the `dqi_algo` line), so a per-position rewrite would also
have to reconstruct the operand mapping for 4,024 blocks whose registers rotate over 33 variants.

---

## 6. Dump-kernel status (so the evidence is not overstated)

| kernel | ref | result |
|---|---|---|
| `jiyujia/qcc-dqi-chien-dump` v1 | — | `KernelWorkerStatus.ERROR`: my opcode-name table called `ir.name()` on invalid opcodes (KeyError) in the first version |
| `jiyujia/qcc-dqi-chien-dump` v2 | COMPLETE (Kaggle status), 33 s | decompression + sha256 + anchor detection + 4 window dumps written; then the aggregate section raised `IndexError: boolean index did not match indexed array … size of axis is 40240 but … 44264` on `QB0[ccx_m][sel0]` (`ccx_m` already masks `inB`; `sel0` must be masked the same way). Caught, written to `out/error.txt`. |

So `out/chien_dump.json`, the `registers.json` summary and `out/touch_history_p0.txt` were **not**
produced. The evidence that *was* produced and is kept here: the four `evidence/window_*.txt` full
instruction listings (with register-resolved operands), the kernel log `evidence/dump_kernel.log`,
and the traceback `evidence/dump_error.txt`. Nothing in §2–§5 depends on the crashed section: the
counts are in the kernel log, and the mechanism is read directly off the listings.

No verifier was run on this line: there is no candidate circuit, so there is no
`verify_submission_dqi.py` JSON to report. No Kaggle submission, no git push, no dataset upload.

---

## 7. Exact commands

```bash
# kernel (CPU only, GPU/TPU false, internet off): dump one Chien position window + counts
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_chien \
      --slug qcc-dqi-chien-dump --account jiyujia \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings --competition
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_chien --account jiyujia
python scripts/kgpu.py status --kernel jiyujia/qcc-dqi-chien-dump --account jiyujia      # COMPLETE

# fetch the small outputs only (the kernel decompresses the tape into /tmp, not /kaggle/working)
KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_jiyujia) KAGGLE_CONFIG_DIR=~/.kaggle \
  ~/.local/bin/kaggle kernels output jiyujia/qcc-dqi-chien-dump -p /tmp/chien1

# local, construction only (no simulation, no verifier): the Toffoli costs in §5
.venv/bin/python -c "import kickmix as km, collections; f=km.GF2Field(12); \
  b=km.CircuitBuilder(); p=b.alloc_qubits(1); om=b.alloc_qubits(12); loc=b.alloc_qubits(12); \
  b.init_and(km.array([p[0]]*12), om, loc); \
  print(b.finish_circuit().operation_statistics().num_toffoli_like)"           # 12
#   ... same with b.del_and(...) -> still 12 ; gf2_phase_by_product(x,y,mask=bits) -> 0 ;
#   b.multi_controlled_x(12 qubits, 1) -> 11 ; b.z(bit) -> 0 ; b.cx(bit, qubit) -> 0
```

## 8. Files in this directory

```
main.py                    dump kernel (jiyujia/qcc-dqi-chien-dump), CPU only
kernel-metadata.json       its metadata (enable_gpu/tpu false, internet off)
evidence/window_p0.txt     full 531-op listing around anchor 30,335,416 (j = 2730)   <- the evidence
evidence/window_p1.txt     same for anchor 30,335,857 (j = 3610)
evidence/window_p2000.txt  same for a mid-region anchor (j = 3949, registers rotate: S25 / E3949)
evidence/window_plast.txt  last anchor (block falls past region B)
evidence/dump_kernel.log   kernel log: sha256, counts, anchor/CCX/CCZ numbers, signature groups
evidence/dump_error.txt    the traceback of the crashed aggregate section (§6)
RESULT.md                  this file
```

## 9. Honest limits of this record

* The semantic *identity* of `S54`/`S57` inside the block (which polynomial the Chien step is
  evaluating, and why the tested value is the specific one-hot pattern) was **not** reconstructed
  from the tape. What is proven from the dump is the *role* split: 10 CCX build a conjunction over
  quantum register bits, 1 CCZ phases on that conjunction plus two more qubits, the `M_j` bits and
  the `is_error` flag enter only as classical conditions, and the whole conjunction is uncomputed
  by `HMR` + CZ corrections at 0 Toffoli.
* That is sufficient to close the lever: the rewrite this line was asked to test needs a
  computational-basis register holding `e_j` and the `M_j` bits available as conditions at the
  phase point. The first does not exist anywhere in the block, and the second is already fully
  exploited for the mask.
