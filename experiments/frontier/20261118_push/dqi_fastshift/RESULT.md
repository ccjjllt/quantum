# DQI leg — reference shift pricing + the 12×12 multiply-block replacement interface

Line: `dqi_fastshift` (account `zhuating`). Date 2026-11-18.
**Kaggle CPU only** (`enable_gpu=false`, `enable_tpu=false`, private): kernel
`zhuating/qcc-dqi-blocks-1118` **v5, COMPLETE in 59 s**, tape deleted from
`/kaggle/working` before exit. The official verifier was **not** run; nothing was
submitted, published or pushed. Evidence: `evidence_kaggle.json` (the kernel's own
output, 70 KB compact / 174 KB indented), kernel source `k_run/main.py`, kernel log
`k_run/kernel_log_v5.txt`.

The barrel-shifter replacement of `_initial_shift_loop` was **stopped** on the
coordinator's instruction after the premise was refuted; its design was never written.
This file delivers the two remaining items.

---

## 0. Verdicts

| item | verdict | decisive measured number |
|---|---|---|
| reference `_initial_shift_loop` price (n=70, m=73, deg=12) | **30,912 Toffoli per direction**, 61,824 both | CSWAP 28,980 + CCX 1,932; 58,546 CX if CSWAPs are expanded |
| are the two big tape clusters that loop? | **No.** Magnitudes coincide forward (29,543 vs 30,912, −4.4 %), the CX/CCX idiom does not | CSWAP-expanded reference has **30.3 CX per CCX**; tape fwd **61.84**, tape rev **67.51** (2.0–2.2×) |
| is a 42-CCX block `C ^= A·B` over GF(2^12)? | **Yes for the window that closes the interpolation** (`rev0`: tensor == `km.GF2Field(12).mul` bit-for-bit), **no** for windows that stop at the evaluation layer (`c132_0`, `c132_1`: closed but different full-rank tensors) | `rev0` 363 nonzero tensor entries = field product exactly; `c132_0` 628, `c132_1` 954; `fwd0`/`fwd1` not closed (linear part 59+70 bits) |
| can 42 → 33/40 land? | **Not from this tape's block boundary, and not with one gadget.** The block's tensor is already realized by exactly 42 ANDs; a reduction needs a lower-rank decomposition of *that* tensor, and the tensor is not uniform across windows | per-block tensors differ (363 / 397 / 628 / 954 entries); 42 distinct `(u,v)` rank-1 carrier pairs per block; A- and B-span ranks both 12 |

---

## 1. Reference `_initial_shift_loop` — exact static price

Built with the **competition's own** kickmix
(`/kaggle/input/competitions/.../kickmix/kickmix.so`) and the competition's own
`verifiers/dqi/dqi_reference_circuit.py`
(sha256 `2b8e1b80a806157c333a7e308eaf2499ee09de499efbc05875202c327959959e`), calling
`ProosAndZalkaDecoder(70, km.GF2Field(12))._initial_shift_loop(b, reg_a, n_A, is_adjoint=…)`
on `reg_a` = 3 scratch words + 70 syndrome words and `n_A = alloc(8)` initialised to 70
(the state the tape's shift actually sees).

| build | toffoli_like | CSWAP | CCX | native CX | CX if CSWAP→CCX+2CX | num_qubits |
|---|---:|---:|---:|---:|---:|---:|
| forward, `logm = 8` | **30,912** | 28,980 | 1,932 | 586 | **58,546** | 897 |
| adjoint, `logm = 8` | **30,912** | 28,980 | 1,932 | 586 | **58,546** | 897 |
| forward, `logm = 7` | 30,774 | 28,980 | 1,794 | 517 | 58,477 | 896 |

Decomposition of the 30,912: 69 steps × 12 lanes × (69, …, 1) CSWAPs = **28,980**, plus
69 × (12 CCX `flip_if_equal` + 9 CCX `isub(1,·,ctrl)` + 7 CCX `flip_if_less_than`) =
**1,932**. Both directions together: **61,824 Toffoli**. `_initial_shift_loop` is line
140–164 of the reference; the price is invariant to the `logm` choice to 0.45 %.

### 1.1 Side by side with the tape's two clusters (measured in the same kernel)

| object | ops | toffoli_like | CX | CX/CCX | T if CSWAP-expanded |
|---|---:|---:|---:|---:|---:|
| reference shift loop, forward (above) | 46,270 | 30,912 | 586 | **30.30** | 30,912 with 58,546 CX |
| tape cluster A `[19,508,954, 21,385,877)` | 1,876,923 | 29,543 | 1,826,827 | **61.84** | — |
| tape cluster B `[46,230,185, 52,842,219)` | 6,612,034 | 64,050 | 4,323,967 | **67.51** | — |

**The hypothesis is dead, and the reason is the CX/CCX ratio, not the T total.**
A `left_rotate(lane, 1, control=ctrl)` is `L−1` CSWAPs and nothing else; the tape has
`CSWAP = 0` (opcode absent), so in the tape's idiom each would have to become
`CX; CCX; CX` — 2 CX per CCX, 30.3 per CCX for the whole loop. The clusters carry
**61.8** and **67.5** CX per CCX, i.e. ≈ 2× more free work per Toffoli, and cluster B is
2.1× the loop's Toffoli count. The forward coincidence (29,543 vs 30,912, −4.4 %) is
exactly that — a coincidence: the tape's forward cluster instead fits its own multiply
ladder, `T(w) = 109.3 + 41.0 w` with r² = 0.9985 over 28 rounds (dqi_bm line), and the
`CX; CCX; CX` CSWAP idiom occurs **0 times** in either cluster (dqi_refshift line,
`reference_shift.json: comparison.tape_cswap_idiom_triples_fwd = 0`,
`…_rev = 0`). Two independent signatures, same conclusion: **the two big T clusters are
the multiply flow, not a shift loop**, so `_initial_shift_loop` cannot be replaced in
place in `575b043f` — there is nothing there to replace.

---

## 2. The 12×12 multiply block — replacement interface

All numbers below are from the same Kaggle run, on the unmodified tape
sha256 `575b043f4fee91a0…`, 57,520,821 ops, 890 qubits.

### 2.1 Physical layout (confirms the parent's rule)

* `S_i = qubits 12i … 12i+11`, i.e. **`word = q // 12` holds exactly**. Checked against
  the tape's own register table in the same kernel run: 4,165 registers, 70 named
  `S0…S69`, and **0 exceptions** to `S_i = 12i…12i+11`; no named register lives at
  q ≥ 840, so words 70…74 are pool/scratch (24 product wires + 2 persistent EEA words +
  flags per the dqi line's census). Verified on every block below: the touched set is
  **exactly 36 qubits = 3 words**, nothing outside `{A,B,C}` (zero exceptions in the 6
  sampled windows).
* **No separate scratch word.** The carriers of the linear forms are built **in place
  inside the two operand words**, and the product scratch bits are **inside the third
  (accumulator) word** — the CCX targets. The replacement therefore needs no borrowed
  qubit at all.

### 2.2 What a block is, exactly

Per block (window closed, see §2.3):

```
C ^= T(A, B)          A, B, C  12-bit words; T a GF(2)-bilinear form 12x12 -> 12
```

realised as 42 ANDs on **multi-bit** carriers:

```
build carrier  u = linear form of A   (CX network inside word A)
build carrier  v = linear form of B   (CX network inside word B)
CX(t, o1) … CX(t, ok)                 # first half of the accumulate sandwich
CCX(u, v, t)                          # t = a bit of word C (the product scratch)
CX(t, ok) … CX(t, o1)                 # o_j ^= u·v
unbuild u, v                          # every carrier restored
```

Measured per block: **42 CCX, 42 distinct `(u,v)` carrier pairs, 42 distinct `w`
masks**, carrier weights 2–10 bits in the closed windows (1–10 including the open one),
`u`-span rank 12, `v`-span rank 12, ~1,280–1,460 CX (all Clifford, 0 T). The CCX target
qubits are **5 bits of word C**; the products are fanned out to 2–10 bits of the same
word. So the Toffoli cost of a block is exactly **42**, and the entire non-multiply part
is free.

### 2.3 How to find the exact op interval (mechanical, no guessing)

Two conditions, both checkable in one pass:

1. **word closure** — extend `[first_ccx, last_ccx]` while every op's operands stay
   inside the block's three words `{A,B,C}`;
2. **ANF closure** — propagate exact degree-≤2 ANF over the window and require
   * every qubit of words A and B ends as **the identity***,
   * every touched qubit of word C ends as **itself + degree-2 terms**,
   * nothing outside the three words is touched.

Then the block's tensor is `T`. Bit-sliced simulation of the 144 basis inputs and the
ANF term extraction **agree bit-for-bit on all 6 sampled blocks** (`anf.agrees_with_bitslice
= true`, 6/6) — they are independent methods (gate-level simulation vs. polynomial
propagation), so the extraction is cross-validated.

**Scratch-bit liveness alone is too coarse** (measured; the parent's proposed rule was
tested first). Taking the 5 CCX-target bits of word C as "the scratch" and using
`[first op touching any of them, last such op]`:

| block | scratch bits | liveness interval | width | closed window | width | ratio |
|---|---|---:|---:|---|---:|---:|
| `fwd0` | q840…q844 | [17576193, 17579092) | 2,900 | [17576193, 17577670) | 1,477 | 1.96× |
| `fwd1` | q840…q844 | [17583904, 17588801) | 4,898 | [17585904, 17587379) | 1,475 | 3.32× |
| `c132_0` | q804…q808 | [21384275, 21389273) | 4,999 | [21385761, 21387283) | 1,522 | 3.29× |
| `c132_1` | q804…q808 | [21433044, 21438567) | 5,524 | [21435041, 21436572) | 1,531 | 3.61× |
| `rev0` | q24…q28 | [36295662, 36298975) | 3,314 | [36295658, 36296976) | 1,318 | 2.51× |
| `rev_mid` | q480…q484 | [40670408, 40671713) | 1,306 | [40670400, 40671724) | 1,324 | 0.99× |

The liveness interval is **2.0–3.6× wider** than the closed window in 5 of 6 blocks (the
pool bits stay live across the neighbouring blocks), and in 2 of 6 (`rev0`, `rev_mid`) the
carrier build starts a few ops *before* the first touch of a product scratch bit, so a
liveness window both over-reaches and clips. The word-closure + ANF-closure rule is the one
that actually closes (it is the only one under which the extracted map is exactly
`C ^= T(A,B)`).

| block | CCX start | words (A,B,C) | window | ops / CCX | A,B restored | C = self+deg2 | linear part | T entries | = GF(2^12) mult? |
|---|---|---:|---|---:|---|---|---|---:|---|
| `fwd0` | 17,576,206 | (0,1,70) | `[17576193,17577670)` | 1,477 / 42 | **yes** | no (12 bad) | **A→C 59, B→C 70 bits** | 821 | no (bilinearity fails 64/64) |
| `fwd1` | 17,585,915 | (2,3,70) | `[17585904,17587379)` | 1,475 / 42 | **yes** | no (12 bad) | **A→C 59, B→C 70 bits** | 821 | no (64/64) |
| `c132_0` | 21,385,877 | (66,1,67) | `[21385761,21387283)` | 1,522 / 42 | **yes** | **yes** | 0 | 628 | **no** (non-commutative) |
| `c132_1` | 21,435,178 | (66,33,67) | `[21435041,21436572)` | 1,531 / 42 | **yes** | **yes** | 0 | 954 | **no** (non-commutative) |
| `rev0` | 36,295,669 | (0,3,2) | `[36295658,36296976)` | 1,318 / 42 | **yes** | **yes** | 0 | **363** | **yes, bit-for-bit** |
| `rev_mid` | 40,670,415 | (0,41,40) | `[40670400,40671724)` | 1,324 / 42 | no (2 bad in word 0) | yes | 0 | 397 | no |

Concrete interval examples (the two usable classes):
* **clean, self-contained**: `rev0` = `[36295658, 36296976)`, 1,318 ops = 42 CCX +
  1,276 CX. Words: `A = word 0 = q0…q11`, `B = word 3 = q36…q47`,
  `C = word 2 = q24…q35`; product scratch (the 42 CCX targets) = **q24…q28**; the
  products are fanned out over all of q24…q35.
  `c132_0` = `[21385761, 21387283)`, 1,522 ops: `A = word 66 = q792…q803`,
  `B = word 1 = q12…q23`, `C = word 67 = q804…q815`, scratch = **q804…q808**.
* **carriers restored but the accumulator word also takes linear work**: `fwd0` =
  `[17576193, 17577670)`, 1,477 ops: `A = word 0 = q0…q11`, `B = word 1 = q12…q23`,
  `C = word 70 = q840…q851`, scratch = **q840…q844**. Here word 70 receives an extra
  **linear** map from A and B (59 + 70 nonzero entries), so the window is *not* a pure
  multiply; the forward pass feeds the pool word from several places.
* **not closable at the 42-CCX boundary**: `rev_mid` = `[40670400, 40671724)`,
  words `A = 0`, `B = 41 (q492…q503)`, `C = 40 (q480…q491)`, scratch q480…q484 — it
  leaves 2 qubits of word A dirty (the carrier unbuild of that block continues past the
  word-closure boundary).

### 2.4 Is the tensor the GF(2^12) field product?

`rev0`'s extracted tensor equals `km.GF2Field(12).mul` **on all 1,728 coefficients**
(363 ones; no bit differs), and satisfies every field axiom measured directly from the
tensor:

```
commutative            yes
associative            yes
identity element       1 (i.e. bit 0)
every nonzero a has M_a of rank 12   (min nonzero rank = 12)
flattening ranks       A|BC 12, B|AC 12, C|AB 12
companion basis element  bit 1 acts as the shift  ->  polynomial basis
modulus                0x1053 = x^12 + x^6 + x^4 + x + 1  (= km.GF2Field(12).modulus 4179)
matches "polynomial mult + reduction mod 0x1053"   yes (bit-for-bit)
```

So the tape's decoder multiplies in **GF(2^12) with the competition library's own
modulus, in the natural polynomial basis** — for the windows where the interpolation is
inside the window. `c132_0`/`c132_1` are *also* perfectly closed `C ^= T(A,B)` units but
their tensors are **different** (628 / 954 entries, non-commutative, no identity), i.e.
those windows carry a sub-layer (consistent with the evaluation layer of a Toom-style
7-point scheme — 42 = 7 × 6 — but that grouping is a hypothesis, not proven here).

### 2.5 What a replacement block must generate

Interface (identical for every block, only the tensor changes):

* consume/produce exactly the three words `A = 12a…12a+11`, `B = 12b…12b+11`,
  `C = 12c…12c+11`; **no other qubit may be touched**, and no borrowed ancilla is
  needed — the block already uses only these 36 wires;
* leave words A and B **restored** (every linear form built in them must be unbuilt);
* leave `C` = `C_in ^ T(A,B)`, using `C`'s own bits as the product scratch (the
  original uses 5 of them as CCX targets; any set of ≥1 free bits of C works as long as
  the net map is the same);
* all conditioning is at depth 0: **0 of the 42 CCX in all six blocks carry a condition
  bit** (`ccx_cond_depth = {None}`), so the block is unconditioned and a replacement can
  be too.

For a rank-`r` replacement (`r < 42 ANDs`) the data to generate is:

* `r` pairs of 12-bit linear forms `(u_i, v_i)` on A and B — each is a CX network
  inside its own operand word (T-free), exactly like the tape's carriers;
* `r` output masks `w_i ⊆ 12 bits of C` — each applied with the `CX(t,o) … CCX … CX(t,o)`
  sandwich (T-free);
* `r` CCX. Cost = `r` Toffoli, 0 extra qubits, 0 extra T.

The 42 `(u, v, w)` triples of each sampled block are in `evidence_kaggle.json`
(`blocks[i].terms`), so a like-for-like 42-AND re-implementation can be generated
today; a cheaper one needs a decomposition with fewer than 42 terms of *the same*
tensor.

### 2.6 Why 42 → 33/40 does not follow from this

* For the field-multiply windows the tensor is **exactly** GF(2^12) multiplication.
  Its bilinear rank is the number the literature bounds: `2n−1 = 23` lower bound,
  `μ_sym(12) ≤ 42` (Ballet–Pieltant; reported by the dqi_mult line, **not** re-verified
  here); the tape's 42 ANDs are precisely a 42-term decomposition. A 33- or 40-term
  circuit would be a **new decomposition of the same tensor**, i.e. a mathematical
  result, not a tape rewrite — and the WCC-2022 rank figures would have to be checked
  against *this* tensor (same field, same polynomial basis, symmetric vs general rank)
  before they can be used as a target.
* The tensors are **not uniform**: 363 / 397 / 628 / 954 nonzero coefficients in the six
  sampled windows, two of them non-commutative. A single replacement gadget cannot be
  dropped into the 3,068 rank-42 blocks; at best each of the 1,347 distinct `(A,B,C)`
  triples (dqi_mult line) needs its own decomposition, and the classes that are
  sub-layers would need their tensor identified first.
* The 42 CCX are already the *whole* Toffoli cost of a block: everything else in the
  window (~1,250–1,460 CX) is Clifford. So the maximum saving from a rank-`r` rewrite is
  exactly `42 − r` per block, and the T is only paid once per block, not per CX.

### 2.7 One correction to the earlier extraction (for the record)

`dqi_mult/work/multlib.py` recorded, per CCX, only **one monomial per control ANF**
(`[next(iter(m)) for m in val[c1]]`) and then mapped *variable indices* where qubit ids
were expected. Both are wrong for the tape's multi-bit carriers: every one of the six
blocks here has carrier weights 2–10 bits, so the earlier term list would have silently
dropped most of each linear form (and its `terms_from_tensor` lookup mostly returned
nothing). The extractor used here keeps every monomial and maps indices → qubit ids
explicitly; its tensor agrees with an independent bit-sliced simulation on 6/6 blocks,
which is the check the earlier code never had.

---

## 3. What this means for the 890-qubit target

* The `-102,425 T` that the 31.427 tier needs cannot come from an
  `_initial_shift_loop` rewrite: the loop is not in the tape (§1.1), and the two
  clusters are the multiply flow.
* Inside those clusters the only T is one CCX per AND; the replacement interface is
  clean (3 words, 42 ANDs, no scratch, no conditions), but the price is `r` per block
  with `r ≥` the tensor rank of *that* block. The two clusters hold **93,593 CCX**
  (29,543 + 64,050) + 1,724 CCZ; even if every one of those CCX sat in a 42-CCX block
  (2,228 blocks) and every block went 42 → 33, the saving would be **−20,056 T =
  +0.53 GM** (GM 28.18 → 28.71) — and that needs a rank-33 decomposition of the exact
  tensor to exist. Nothing measured here suggests one, and the sampled tensors are not
  even all the same tensor. For scale: the refuted hypothesis was worth +2.97 GM
  (GM 31.15), which is exactly the "28.18 → 31.1" figure; the multiply flow can only
  give a fraction of that, and only through a new rank result.
* Everything else in this leg remains where the earlier lines left it: no
  tape-level T lever, and Q is its own problem.

## 4. Reproduction

```
# one Kaggle CPU kernel (v5), 59 s, private, no internet, no GPU/TPU
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_fastshift/k_run --account zhuating
python scripts/kgpu.py logs --kernel zhuating/qcc-dqi-blocks-1118 --account zhuating
```
`k_run/main.py` is self-contained: it locates the competition kickmix + reference
generator and the tape dataset, prices the reference loop, reads the tape through
`vqcc_ir`, and does all block measurements. It deletes the 479 MB decompressed tape
before exiting. Local work in this line was limited to reading the tape (mmap, windowed
`decode`) and small-numpy development of the two extractors; every number quoted above
is from the Kaggle run in `evidence_kaggle.json`.
