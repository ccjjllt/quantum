# Chemistry ANGLE loaders — opcode census, table algebra, and why the 8,044 is already compressed

Date 2026-11-17. Line: `zhuating`. Target: `angles_toffoli = 8,044` of the shipped
`a73b25d2` (T = 14,706, Q = 427, λ_eff = 46.921716818, cost
**294,643,137.73357135**). All numbers read from the shipped bytes on Kaggle CPU
kernels; **no simulation, no verifier run, no candidate, no submission**.

## 0. Verdict

| question | answer | decisive number |
|---|---|---|
| is there mean-T / conditioning headroom in the loaders? | **NO** | all 15 circuits contain **0 PUSH/POP, 0 CCZ, 0 CSWAP, 0 classical conditions on any Toffoli** — `mean T = static T = 268.1`, so the brief's "per-shot mean" is not a conditioning surface |
| can MBU remove any Toffoli? | **NO** | every one of the 292 Toffolis is a plain unconditional `CCX`; there is no AND-ancilla compute/uncompute pair to measure out (the 77 ancillas are each written **once** and undone by `HMR`, already free) |
| does the table have structure to exploit? | **NO** | all 1,220 rows active, 50.0 % bit density, ~24,300 value runs, and the ANF is **full support: 2,048 of 2,048 monomials, 953 per output bit** (571,570 monomials/pass) |
| how good is the shipped loader? | **4.6× below the published construction** | 4,022/pass vs the reference segment-tree QROM's `15 × (rows−2) = 18,270`; **0.220 T per active row**, 0.011 T per table bit, ~7 ANF monomials per Toffoli |
| what would gold need? | **−10.0 % angles** | T ≤ 13,899 ⇒ angles ≤ **7,237** (−804 T = **−21 % per circuit**, 212 instead of 265–292) |

**Bottom line: the loader is not an under-optimised QROM — it is a shared-product
ANF-evaluation network that is already 4.6× cheaper than the only published
construction, on a table that is provably dense in both the value and the
algebraic basis. There is no conditioning or MBU lever. A −10 % (gold) cut needs
a better product-evaluation scheme, i.e. new synthesis, and nothing in the
measured structure says one exists.**

## 1. Census of the 15 shipped loaders (kernel k1)

`zhuating/qcc-chem-angle-census` (CPU, private; mounts
`maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`, reads
`dfthcsos/angle_k_*.kmb` out of its `submission.zip`). Raw `evidence/k1_census.txt`.

| circuit | bytes | Q | nregs | ops | static T | CX | R | HMR | CZ | Z |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| angle_k_0 | 180,436 | 128 | 6 | 19,957 | **292** | 19,170 | 80 | 80 | 80 | 255 |
| angle_k_1 | 151,084 | 128 | 6 | 16,661 | **287** | 15,977 | 75 | 75 | 75 | 172 |
| angle_k_2 | 135,545 | 128 | 6 | 14,918 | 269 | 14,310 | 74 | 74 | 74 | 117 |
| angle_k_3 | 134,697 | 128 | 6 | 14,830 | 269 | 14,208 | 74 | 74 | 74 | 131 |
| angle_k_4 | 130,825 | 128 | 6 | 14,398 | 263 | 13,792 | 74 | 74 | 74 | 121 |
| angle_k_5 | 130,454 | 128 | 6 | 14,359 | 263 | 13,748 | 74 | 74 | 74 | 126 |
| angle_k_6 | 129,631 | 128 | 6 | 14,264 | 263 | 13,661 | 74 | 74 | 74 | 118 |
| angle_k_7 | 130,875 | 128 | 6 | 14,404 | 263 | 13,797 | 74 | 74 | 74 | 122 |
| angle_k_8 | 130,222 | 128 | 6 | 14,335 | 263 | 13,720 | 74 | 74 | 74 | 130 |
| angle_k_9 | 130,054 | 128 | 6 | 14,315 | 264 | 13,698 | 75 | 75 | 75 | 128 |
| angle_k_10 | 131,074 | 128 | 6 | 14,427 | 265 | 13,808 | 76 | 76 | 76 | 126 |
| angle_k_11 | 130,646 | 128 | 6 | 14,375 | 265 | 13,766 | 76 | 76 | 76 | 116 |
| angle_k_12 | 129,613 | 128 | 6 | 14,266 | 265 | 13,644 | 76 | 76 | 76 | 129 |
| angle_k_13 | 130,455 | 128 | 6 | 14,356 | 265 | 13,742 | 76 | 76 | 76 | 121 |
| angle_k_14 | 130,774 | 128 | 6 | 14,391 | 266 | 13,773 | 77 | 77 | 77 | 121 |
| **sum** | | | | | **4,022** | | | | | |

* `4,022` reproduces `angles_toffoli_per_pass` **exactly**, and `2 × 4,022 = 8,044`
  reproduces `angles_toffoli` exactly. **Every Toffoli is unconditional**, so the
  simulator's mean equals the static count: there is no shot-dependent Toffoli in
  the loaders at all.
* Registers (decoded from the payloads: `u32 kind, u32 count, name, u32 ids` with
  bit 31 tagging qubits) — exactly **6**: `selection` = **11 qubits (0..10)**,
  `word_0..word_4` = **5 × 8 = 40 qubits (11..50)**. Hence
  `Q 128 = 11 selection + 40 persistent + 77 temporary` ✓ (`angles_selection_qubits
  = 11`, `angles_persistent_qubits = 40`, `angles_temporary_qubits = 77`).
* Each circuit is the XOR oracle `|a>|z> → |a>|z ⊕ delta[k,a]>` with
  `delta[0] = batch[0]`, `delta[k] = batch[k] ⊕ batch[k−1]`, `J = 5` words per
  circuit, 15 circuits → 75 words = `N−1` with `N = 76` one-body rows.
  The verifier (`scoreinfra/circuits.py:433 recover_words_from_circuits`)
  simulates **every** address `a` on `shots_per_address` shots, requires the word
  registers to hold batch `k` of row `a`, requires the selection unchanged,
  workspace clean and phase unflipped — **there are no untested addresses to
  exploit**, and the 828 addresses above `num_vectors = 1,220` are legal
  don't-cares.

## 2. The table is dense in the value domain (kernel k2)

`zhuating/qcc-chem-angle-table`; raw `evidence/k2_table.txt`. `angle_words` out of
the shipped `submission.npz` (1,220 × 75 int64, 0..255), brot = 8.

| circuit | words | out bits | active rows | nonzero bits | value runs | tree nodes needed |
|---|---|---:|---:|---:|---:|---:|
| k=0 | 0–4 | 40 | **1,220 / 1,220** | 24,407 | 24,390 | 2,444 / 2,444 |
| k=1 | 5–9 | 40 | 1,220 | 24,324 | 24,532 | 2,444 |
| … | | 40 | all 1,220 | 24,027–24,575 | 24,051–24,616 | 2,444 |
| k=14 | 70–74 | 40 | 1,220 | 24,050 | 24,314 | 2,444 |
| **total** | 75 | 600 | **18,300** | **364,925** | **365,181** | **36,660** |

* **Every row of every circuit is active**, so the "77 high values / cuts" in the
  loader plan cannot come from zero rows.
* Bit density **50.0 %** (364,925 / 730,000), value runs ≈ 24,300 against 24,400
  nonzero bits → **no constant stretches**; each word column has 125–246 distinct
  values of 256; consecutive-word XOR is 98.8 % nonzero.
* Consequence: the pruned segment tree needs **all 2,444 nodes**, i.e. the full
  unary iteration — the reference construction's `rows−2 = 1,218` CCX per circuit.

## 3. The table is dense in the algebraic domain too (kernel k4)

`zhuating/qcc-chem-angle-anf`; raw `evidence/k4_anf.txt`. Exact Möbius transform
over the 2^11 address space per output bit (828 don't-cares set to 0, then a
40-sweep greedy search over them).

| quantity | per circuit | per pass (×15) |
|---|---:|---:|
| ANF monomials, summed over the 40 bits | 37,290–40,908 | **571,570** |
| ANF monomials, **union** over the 40 bits | **2,048 (= 2^11, full support)** | — |
| degree histogram (all circuits) | deg1 3,238 · deg2 16,194 · deg3 48,003 · deg4 94,114 · deg5 128,940 · deg6 126,703 · deg7 90,455 · deg8 45,219 · deg9 15,186 · deg10 2,979 · deg11 245 | | |
| shipped static Toffoli | 263–292 | 4,022 |

* **The table uses every one of the 2,048 monomials of the 11-bit address space,
  ~953 of them per output bit.** There is no monomial sparsity to exploit: no
  "compute the table from a few products", no low-rank/QROAM structure.
* Degree is spread over 1..11 with the mass at 5–8, exactly as a random function
  would be.

## 4. What the shipped circuit actually is (kernel k3)

`zhuating/qcc-chem-angle-gatedump`; raw `evidence/k3_gatedump.txt`.

* The first CCX of `angle_k_0` are `4,5→51`, `4,6→52`, `5,6→53`, `4,7→54`, … —
  **pairwise products of the high selection bits (4..10)**, then higher products
  (`4,53→70` = `a4·(a5·a6)`), i.e. an explicit **subset-product tree over the 7
  high address bits**.
* **Targets of every CCX are wires 11..127** — the selection register (0..10) is
  never a CCX target, so the address is untouched. 292 CCX over **112 distinct
  targets**: the 40 word bits (3–8 CCX each, 225 gates) and ~72 ancillas that are
  CCX targets **exactly once** each (67 gates on wires ≥ 64).
* Each one-shot ancilla is then a **CX control for ~210 CX gates** (19,170 CX
  total, ~88 distinct controls including anti-controls, tagged by bit 8 in the
  operand field). The 80 `HMR` + 80 `CZ if b` are the measurement-based undo of
  those 77 ancillas — already 0 T.
* So: **T = the number of product generators (292)**, and the fan-out of those
  products into the 40 output bits is free. The circuit realises **7 ANF
  monomials per Toffoli** by sharing each product across the 40 output bits.

## 5. Floor analysis

| model | per circuit | per pass | vs shipped |
|---|---:|---:|---:|
| reference segment-tree QROM (`rows−2`) | 1,218 | 18,270 | 4.54× more |
| pruned-tree nodes needed (measured) | 2,443 | 36,645 | 9.1× more |
| ANF monomials per circuit (summed over bits) | ~38,105 | 571,570 | 142× more |
| **shipped (measured)** | **263–292** | **4,022** | 1.0 |
| distinct product generators (measured, 112 targets) | 112 | 1,680 | 0.42× |
| information bound (11 address bits / 40 word bits) | ~11–40 | — | 0.05× |

* The shipped loader is **4.6× below the only published construction** and 7×
  below the ANF monomial count; it is *not* an under-optimised QROM.
* A *provable* lower bound for a dense random table is not available: the only
  rigorous statements are the information bound (`≈ 11–40`, useless) and the
  fact that the ANF has full support (so no algebraic shortcut exists). Between
  those and 292 there is no published bound, and the shipped design's own
  sharing factor (~7 monomials per Toffoli) is already aggressive.
* **Therefore the "80 T of remaining headroom" in the team record cannot be a
  loader-structure statement**: it was measured against their own emitter at a
  different geometry, not against any floor.

## 6. Consequence for the score

`cost = λ_eff · T · Q`, λ_eff = 46.921716818, Q = 427, T = 14,706 today.

| angles change | angles T | T_total | cost | ΔGM |
|---|---:|---:|---:|---:|
| today | 8,044 | 14,706 | **294.643 M** | — |
| −10 % (−804) | 7,240 | 13,902 | 278.46 M | **+0.37** |
| −20 % (−1,609) | 6,435 | 13,097 | 262.35 M | +0.75 |
| −40 % | 4,826 | 11,488 | 230.13 M | +1.55 |
| **gold needs (single leg −5.496 %)** | ≤ 7,237 | **≤ 13,899** | ≤ 278.45 M | ⇒ **−10.0 %** |

So one leg of gold needs **−804 Toffolis = −53.6 per circuit**, i.e. **212 instead
of 265–292 (−21 % per circuit)**. For calibration: that is *more* than the entire
`HMR`+`CZ`+`R`+`Z` overhead of a circuit (≈ 220 Clifford gates, 0 T), so it can
only come from the 292-Toffoli product network itself.

## 7. What would have to be true

1. **A cheaper product-evaluation scheme.** The load's ANF needs all 2,048
   monomials at ~953 per bit; the shipped generates them with 292 shared
   generators (7 monomials per Toffoli). A −21 % cut means **8.8 monomials per
   Toffoli**, i.e. a subset-product tree that shares ~25 % better. Whether that
   exists is a circuit-synthesis question on *this* table, and the table has no
   structure (full-support ANF) to make it likely.
2. **A row-count reduction is worth more but is closed elsewhere**: `rows = 76 +
   B·R` and the precision gate pins `B = 143` (§`chem/RESULT.md`); each 1 % of
   rows is ~40 T/pass = 0.5 % of angles.
3. **A different address decomposition** (e.g. a 2-level QROM/QROAM) is 4.5×
   *worse* here, because it costs `O(2^{n/2})` per output word while this load
   costs one generator per shared product.

## 8. Status, honestly

* Complete and reproducible from the shipped bytes: the opcode census (§1), the
  value-domain density (§2), the ANF census (§3), the gate-level architecture
  (§4), and the score arithmetic (§6).
* **No candidate circuit, no verifier run, no submission.** No mechanism was
  found that is even *plausibly* worth building: there is nothing conditional,
  nothing MBU-able, no sparse structure, and the shipped design is already 4.6×
  below the published construction.
* Not established: a *provable* lower bound for a dense-random 1,220 × 40-bit XOR
  oracle. What is established is that the two obvious floors (segment-tree
  1,218; ANF-monomial count 38,105) are both far *above* the shipped 292, so a
  new bound would have to come from the shipped architecture itself, which is
  not public (`planner.py` / `emit_plan.py` are hardcoded to this geometry and
  were not available in the mounts read here).
* Local work: text reads and arithmetic only. Two kernel bugs were hit and fixed
  (register payloads are not a flat `uint32` array — they are
  `kind, count, name, ids` with bit 31 tagging qubits; and the 2-operand control
  field tags anti-controls with bit 8). Both are recorded so they are not
  repeated.

## 9. Kernel refs (all CPU-only, private, `enable_gpu=false`, `enable_tpu=false`)

| kernel | purpose | outcome |
|---|---|---|
| `zhuating/qcc-chem-angle-census` | find + opcode-census the 15 loaders, decode registers, per-wire Toffoli roles | COMPLETE (§1) |
| `zhuating/qcc-chem-angle-table` | rebuild the 15 delta tables, count active rows / bits / runs / pruned tree | COMPLETE (§2) |
| `zhuating/qcc-chem-angle-gatedump` | dump every CCX operand + CX control histogram + the first 60 ops | COMPLETE (§4) |
| `zhuating/qcc-chem-angle-anf` | exact Möbius/ANF census over the 2^11 address space, 40 bits × 15 circuits | COMPLETE (§3) |
