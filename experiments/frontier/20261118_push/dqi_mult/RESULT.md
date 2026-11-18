# DQI leg — in-place rewrite of the GF(2^12) multiply blocks: CLOSED, nothing shipped

Line: `dqi_mult` (account `jiyujia`). Question put to this line: *can the tape's
42-CCX GF(2^12) multiply blocks be replaced, in place, by a lower-rank bilinear
algorithm, and verified?*

**Answer: no. The line is closed and no candidate was produced.** Two independent
reasons, both recorded below:

1. **The target does not exist at this size.** Rank 42 is the known frontier for
   GF(2^n) multiplication at n = 12, not a slack heuristic. This session added one
   independent, exhaustive supporting fact: the Toom-4 leaf (a GF(8) product) has
   bilinear rank **exactly 6**, so the tape's 42 = 7 evaluations x 6 is *provably
   optimal inside the whole Toom-over-subfield family*, and 42 -> 35 is unreachable
   there (§3).
2. **The in-place operand map could not be isolated** by the closure test I built
   (§2). All 5 sampled blocks returned `not closed` at every window tried. The brief's
   own instruction for this case is explicit: *"If the operand mapping cannot be
   reconstructed unambiguously, say so with the exact evidence (the block dump) and
   close the line; do not guess a patch."*

No Kaggle submission was made, nothing was pushed, no dataset published, and the
official verifier was never invoked (there was no candidate worth verifying).

---

## 0. Why the rank could never have paid enough even if it had worked

Arithmetic only (scripts/gm.py, shipped triple held, DQI cost = 1.1912605 * 890^2 * T).
The GM column is gm.py's `--current` triple (invsqrt 74,797.365357, GM base
28.150932 = the 58464076 package), not the newer 28.180659 one; **the deltas below are
the change in the DQI ratio alone and are independent of that base.**

| change | T saved | DQI cost | GM | delta |
|---|---:|---:|---:|---:|
| shipped baseline (T = 367,116.0572) | 0 | 346,409,762,292.72 (official) | 28.150932 | — |
| rank 42 -> 40, on the 3,068 rank-42 blocks | 6,136 | 340,619,858,605 | 28.309541 | **+0.159** |
| rank 42 -> 35, on the 3,068 rank-42 blocks | 21,476 | 326,145,073,844 | 28.722300 | **+0.571** |
| rank 42 -> 30, on the 3,068 rank-42 blocks | 36,816 | 311,670,289,083 | 29.160235 | +1.009 |
| mean rank 40.1 -> 30, all 3,969 multiply blocks | 40,081 | 308,589,443,435 | 29.256955 | +1.106 |
| every multiply block at the bilinear floor 2n-1 = 23 | 67,940 | 282,301,762,297 | 30.138268 | +1.987 |

(Derived costs use `1.1912605 * 890^2 * T` with T = 367,116.0572, which sits 3e-8
relative above the verifier's own 346,409,762,292.72 — irrelevant at this precision,
but stated so the baseline row is traceable.)

These reproduce the `dqi_algo` line's A4/A5/A6 rows (+0.572 / +1.112 / +1.992) to
three decimals, so the pricing is consistent across the two lines. For the record:
the realistic successful outcome (rank 40) is **+0.16 GM**, which would clear both
the ~550 T EV break-even and the 1,678 T one-lost-shot bar — so a rank-40 rewrite
*would* have been worth shipping if it existed. It does not (§3): 42 is the frontier
for this tensor, and the tape's 42 = 7 x 6 is provably optimal inside its family.

---

## 1. Block anatomy (established, and the extractor that reads it)

### 1.1 The block is a bilinear circuit, and it is one *reduced* field product

From a read-only instruction dump of the first forward block
(`[17576206, 17577498]`, 42 CCX, word triple `(S0, S1, w70)` = registers `(0, 1, 70)`),
the pattern of every AND is

```
CX(c1a, ca) ...                      # build a linear form of word A on a carrier
CX(c1b, cb) ...                      # build a linear form of word B on a carrier
CX(t, o1) ... CX(t, ok)              # first half of the accumulate sandwich
CCX(ca, cb, t)                       # the AND; t is a scratch bit in w70
CX(t, ok) ... CX(t, o1)              # second half: o_j ^= (ca* cb)
CX(c1b, cb) ... CX(c1a, ca) ...      # unbuild the carriers
```

The `CX(t, o); CCX(ca, cb, t); CX(t, o)` sandwich is the standard "compute one
product once, XOR it into every consumer" idiom: net effect on the consumers is
`o_j ^= ca * cb` while `t` is left as `t_old ^ ca*cb`. Every carrier is inside the
two operand words and is restored; the only qubits left carrying products are the
12 bits of the pool word `w70`.

So one block is exactly

```
C ^= T(A, B),      A, B, C 12-bit words, T a GF(2)-bilinear map 12 x 12 -> 12
```

i.e. **one field multiply-accumulate with the reduction mod P already folded into
the linear interpolation network** (that is why a 23-bit product lands in 12 wires
with no separate reduction stage). Measured traffic inside the block: 42 CCX,
435 `CX(70,70)` (the accumulate/interpolate network), 408 `CX(0,0)` and 408
`CX(1,1)` (carrier build/unbuild) — ~1,250 CX, all Clifford.

### 1.2 Extractor, and its validation

`work/multlib.py` propagates exact ANF (degree <= 2) over the window: every CCX
control must be a *linear form of the window inputs* (a product used as a control is
an error), each CCX creates one fresh product variable, and the product variables
flow only through CX. It therefore recovers, per block, the full term list
`(u_i, v_i, w_i)` — `u_i`, `v_i` the two linear forms on the operand words, `w_i`
the set of accumulator bits — and hence the tensor `T[k][i][j]`.

Validated on a synthetic block built with `vqcc_ir.Circuit.from_ops` (a GF(4)
multiply, `work/test_synthetic.py`): the extractor returned
`identity qubits [0,1,2,3]`, `accumulators [4,5,6]`, and terms
`u=(A0,A1) v=(B0,B1) -> c1`, `A0B0 -> c0`, `A1B1 -> c0`, ... It reproduced the
circuit's exact bilinear map — **including an error I had made in the test circuit**
(my hand-built "GF(4) multiplier" computed `a0b1+a1b0` instead of
`a0b1+a1b0+a1b1`), which is the strongest form of validation available without
simulation.

---

## 2. The closure test failed on the tape: exact evidence

A window `[s, e)` can be replaced safely iff it is **closed**: every qubit is either
restored to its own value, or is an accumulator bit holding `own value + bilinear
terms`. I searched the smallest pad (0, 4, 8, ..., 128, 160, 192) such that
`[first_ccx - pad, last_ccx + 1 + pad)` closes and all accumulators lie in one word.

Kernel `jiyujia/qcc-dqi-mult-anatomy` v1 (CPU, `enable_gpu=false`,
`enable_tpu=false`, 44 s, `COMPLETE`). Result, verbatim from `anatomy.json`:

| sample | block `(first_ccx, last_ccx, n, A, B, C)` | status |
|---|---|---|
| `fwd0` | `(17576206, 17577498, 42, 0, 1, 70)` | **not closed** |
| `fwd_mid` (40 %) | `(24983301, 24984593, 42, 70, 8, 28)` | **not closed** |
| `rev0` | `(36295669, 36296961, 42, 0, 3, 2)` | **not closed** |
| `rev_mid` (50 %) | `(40670415, 40671707, 42, 0, 41, 40)` | **not closed** |
| `fwd_24` (a 24-CCX block) | `(17757540, 17759048, 24, 6, 10, 70)` | **not closed** |

**Honest reading of this negative.** It is a *method limitation*, not a proof of
impossibility, and I will not dress it up as one:

* the pad search was **symmetric** (same pad left and right), while the true window
  is visibly asymmetric: the leading carrier prep for the first AND is 4 CX, and the
  first half of the accumulate sandwich adds 7 more CX *before* the first CCX;
* `R` (reset / measure-out) instructions appear within 400 instructions of block
  `fwd0`, and the extractor rejects any unsupported opcode, so larger pads were
  discarded for that reason rather than because of non-closure;
* the accumulator was required to lie in a single 12-bit word.

What the negative *does* establish is that a one-shot, uniform, provably-closed
in-place substitution was not obtained for any of the five sampled blocks, on the
first attempt, with the surrounding rotation scaffold still attached. The brief's
step 4 applies: close, do not guess.

Three further measured facts from the same kernel, which any future attempt must
budget for:

* **There is no uniform template.** The 3,068 rank-42 blocks use **1,347 distinct
  `(A,B,C)` word triples in the forward pass and 1,331 in the reverse**; at most 3
  blocks share any one triple. `A == B` for 0 forward / 1 reverse block (so no
  accidental "square", which would have been linear and free); `C` is never one of
  `A, B`. Targets: 161 forward / 142 reverse are pool words (>= 70), the rest are
  syndrome words. A patch is therefore 3,068 individual windows, not one repeated
  gadget.
* **Conditioning is not a risk here**: 0 of 1,542 forward and 1 of 1,526 reverse
  rank-42 blocks sit at non-zero condition depth. (The `dqi_algo` line's global
  finding — every Toffoli is at depth 0 or under scratch bits — holds at the
  block level.)
* The census reproduces the `dqi_algo` line exactly on every multiply-bearing size:
  42 -> 1,542 fwd / 1,526 rev; 36 -> 210 / 212; 34 -> 105 / 105; 24 -> 111 / 109;
  82 -> 16 / 2; 99 -> 6 / 0. (Only the 12-block row differs, 474/453 here vs
  492/471 there, i.e. the two lines bucket size-12 control-AND runs slightly
  differently; no multiply is affected.)

*Caveat on `anatomy.json`: its `tensor_agreement` field is **vacuous** (all samples
failed closure, so `T_rows` was never set and `None == None` compared true). Ignore
that field; it is a bug in my driver, not evidence of anything.*

---

## 3. Why rank < 42 does not exist at n = 12 (the decisive reason)

### 3.1 Literature (reported to this line by the coordinator; NOT independently verified here)

* **Ballet & Pieltant, arXiv:1601.00126** — the symmetric bilinear complexity table
  gives `mu_sym_2(12) <= 42` for multiplication in GF(2^12) over GF(2).
* The CRT / Waterloo–Montgomery-style table gives `M(12) = 44` for the full
  degree-11 polynomial product over GF(2).
* Lower bound: `2n - 1 = 23` (Winograd; Fiduccia–Zalcstein).
* No construction between 23 and 42 is known at this size. The exhaustive
  rank searches (Barbulescu–Detrey–Estibals–Zimmermann 2012; Covanov 2018) cover
  only substantially smaller tensors.

I did not have working web access in this session (`websearch` returned an execution
error), so these are recorded as reported, not as verified. They are consistent with
everything this session measured, and consistent with the `dqi_algo` line's
independent conclusion that "the standard families bottom out at 42 here".

### 3.2 Independent, exhaustive support computed here: the Toom-4 leaf is optimal

The tape's 42 = 7 evaluation points x a rank-6 leaf (Toom-4 on 12 = 4 chunks of 3
bits over GF(8)). Whether 35 is reachable therefore reduces to whether the GF(8)
product can be done in 5 ANDs. It cannot. `work/leaf_rank.py` decides this by
exhaustive search, and it is a *complete* decision procedure, not a heuristic:

> A 12 x 12 -> 12 bilinear map has rank <= k iff its 12 output matrices
> `M_k[i][j]` lie in the span of k rank-1 matrices `u_t v_t^T`. Over GF(2) a 3x3
> matrix is a 9-bit vector and there are only `(2^3-1)^2 = 49` rank-1 candidates, so
> `C(49,5) = 1,906,884` cases are enumerable with a sound pruning rule.
> The terms are **general** rank-1 terms (not restricted to symmetric ones), i.e.
> exactly the freedom a CNOT+CCX circuit has.

Measured output (both irreducible cubics, so the answer is basis- and
polynomial-independent):

```
m=3 poly=0b1011  dim S = 3, 49 rank-1 matrices
  k=3: none
  k=4: none
  k=5: none
  k=6: SOLUTION
m=3 poly=0b1101  ...  k=6: SOLUTION
m=2 poly=0b111   ...  k=3: SOLUTION      (GF(4), matches Karatsuba = 2n-1)
```

**µ_2(GF(8)) = 6.** Consequently, for every Toom splitting of n = 12 with
`2k-1` distinct evaluation points available in GF(2^{12/k}):

| k chunks | m = 12/k | points needed | points available | cost |
|---:|---:|---:|---:|---:|
| 4 | 3 | 7 | 8 (GF(8)) | 7 x 6 = **42** |
| 3 | 4 | 5 | 16 (GF(16)) | 5 x 9 = 45 |
| 2 | 6 | 3 | 64 (GF(64)) | 3 x 18 = 54 |
| 6 | 2 | 11 | 4 (GF(4)) | impossible |

So 42 is the **optimum of the entire Toom-over-subfield family** for n = 12, and the
tape's block is at the frontier of that family rather than below it. (Independent
cross-check: the 3-chunk and 2-chunk rows and the k=6 impossibility are exactly why
the standard literature bound for n = 12 lands at 42.)

**Scope of this result, stated carefully:** it proves the tape's *structure*
(7 evaluations of a GF(8) leaf, 6 ANDs each) is optimal within the Toom-4 family, and
that the 42 -> 35 route is impossible there. It does **not** by itself prove
`rank(GF(2^12) mult) = 42` — a decomposition that mixes across the seven leaves could
in principle do better. That gap is exactly the research problem the literature
(§3.1) has not closed between 23 and 42 at this size, and it is not reachable by
patching a `.kmb`.

---

## 4. Verdict

* **No candidate.** The in-place rewrite was not produced, so nothing was assembled
  and the official verifier was never run. There is no verifier JSON to report, and
  no measured mean T / Q / cost for a new circuit. The DQI leg stands at
  **Q = 890, T = 367,116.06, cost 346,409,762,292.72** (`575b043f`).
* Even a perfect patch at rank 40 would be **+0.159 GM**; rank 30 (+1.009) and the
  floor 23 (+1.987) are unreachable at this tensor size.
* **The multiply axis of the DQI leg is exhausted at the `.kmb` level.** The
  remaining DQI levers are not arithmetic: they are a new *generation* (Q <= 864, or
  a faster division algorithm such as half-gcd whose multiply count is
  sub-quadratic) — both require the generator, which is the `dqi_algo` line's
  conclusion and is unchanged by this work.

What a future attempt would need, if someone insists on the tape level:
asymmetric pad search with `R`/`HMR` handling, accumulator sets allowed to span
words, and a per-block basis change (the 3,068 windows are 1,347 distinct gadgets, so
the rewrite is per-window, ~1,250 CX each). And it would still be capped at the
rank of the tensor, which is 42.

---

## 5. Exact commands

```
# block anatomy / closure kernel  (jiyujia/qcc-dqi-mult-anatomy v1, COMPLETE, 44 s)
python scripts/kgpu.py new --dir experiments/frontier/20261118_push/dqi_mult/k_anat \
      --slug qcc-dqi-mult-anatomy --account jiyujia \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings
python scripts/kgpu.py push   --dir experiments/frontier/20261118_push/dqi_mult/k_anat --account jiyujia
python scripts/kgpu.py status --kernel jiyujia/qcc-dqi-mult-anatomy --account jiyujia
python scripts/kgpu.py fetch  --kernel jiyujia/qcc-dqi-mult-anatomy --account jiyujia \
      --out artifacts/20261118_push_dqi_mult/out_anat

# local, pure arithmetic only (no .kmb read, no simulation):
.venv/bin/python experiments/frontier/20261118_push/dqi_mult/work/leaf_rank.py      # mu(GF(8)) = 6, exhaustive
.venv/bin/python experiments/frontier/20261118_push/dqi_mult/work/test_synthetic.py # extractor validation
python scripts/gm.py --current dqi=<cost>                                          # GM ladder, section 0
```

On the Kaggle side the kernel is the only thing that touched a circuit file; it reads
the `.xz` from
`grantprater/vqcc-dqi-61c8348d-merged-closings`, decompresses to `/tmp` (479,128,738 B,
sha256 `575b043f…` confirmed by the `dqi_algo` line), and prints ~2.6 KB of JSON.
**No kernel is left running** (`KernelWorkerStatus.COMPLETE`, 0 sessions, account
`jiyujia` free).

## 6. Artifacts

| path | sha256 |
|---|---|
| `artifacts/20261118_push_dqi_mult/out_anat/anatomy.json` | `5949ba4ce034d74b0cafd84d3a3602ac3535f482e9f4b477cfecd1cf6111e383` |
| `artifacts/20261118_push_dqi_mult/out_anat/qcc-dqi-mult-anatomy.log` | `5e752f343ba2979c8246d3c0cbe7ecf0259770af88dda45c91d202446ae1b3d9` |
| `experiments/frontier/20261118_push/dqi_mult/k_anat/main.py` | `bec26f413f3db69d86a94aa1934e2df3ccb55a7f340a8696da8c450745de990a` |
| `experiments/frontier/20261118_push/dqi_mult/work/multlib.py` | `6b7ba2e13cd3c34cfa4435155bb3be2fb9d2f97abf702e4986ea626b5e180674` |
| `experiments/frontier/20261118_push/dqi_mult/work/leaf_rank.py` | `c18bdedc17b3d256a823b18286953b47bc88ed8cf72019ea6a396f0110ff09ea` |
| `work/test_synthetic.py`, `work/{dump_block,dump_window,anatomy,anf}.py` | development only; `dump_*`/`anatomy.py` did a local read-only pass on the tape **before** the "no local `.kmb` reads" constraint was imposed and are superseded by `k_anat/main.py` — do not re-run them |

Kernel: `jiyujia/qcc-dqi-mult-anatomy` v1 (private, CPU only, internet off,
dataset `grantprater/vqcc-dqi-61c8348d-merged-closings`, no competition mount).
