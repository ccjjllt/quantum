# Can the ANGLE loader's data layer be rewritten with 0 extra Toffoli? — NO (measured)

Date 2026-11-17. Follow-up to `RESULT.md` (same directory). Question: the chemistry
`W` (`H2_I`, 352 values) lever changes the 8-bit angle words of **rows 0..75**
(= addresses 0..79 = the first 5 blocks of 16) and needs λ_eff 46.92 → 36–39.
Since no public emitter can rebuild these loaders at 268 Toffoli/circuit, can the
existing `.kmb` be patched surgically with **no (or tiny) Toffoli change**?

**Answer: NO — the data is not delivered by a CX fanout from a data-independent
product basis; 212 of the 292 Toffolis are data-chosen CCX whose operand pairs move
with the table.** A CX-only patch can therefore not reach an arbitrary new table,
and a block-local patch needs **new block-confined products**, estimated
**+40..+200 CCX per circuit** (see §4 for the derivation and the pass/fail budget).

All numbers below are read statically from the shipped `angle_k_0.kmb`
(sha `ed648708…`, Q 128, 19,957 ops, static T 292) on Kaggle CPU
(`zhuating/qcc-chem-angle-patchtest`). No simulation, no verifier run.

## 0. Verdict

| question | measured answer |
|---|---|
| (a) Toffoli decomposition | **292 = 80 address/product CCX + 212 data CCX** (27 % / 73 %) |
| (b) are the product ancillas data-independent? | **YES** — all 77 are monomials of selection bits **4..10 only** (the block index): pair products `(4,5)(4,6)(5,6)(4,7)…`, then higher `4·(5·6)`. 74 written once, 3 twice. Data-independent. |
| (c) is a block's data a CX fanout from a *fixed* product set? | **NO** — inside a block the 77 products are constants, so the intra-block variation must come from the low bits 0..3, and it is carried by the **212 data CCX**, e.g. `CCX(100,105→13)`, `CCX(104,9→38)`, `CCX(77,73→19)`, `CCX(51,81→20)`: products of *two ancillas*, or of an ancilla with a **low address bit** (9, 1, 10, …). Those operand pairs are chosen to fit the table. |
| (d) can a CX-only edit reach a new table? | **NO** by construction: the CX layer only *accumulates* (`3,249` CX into the 40 word bits, `14,325` CX into ancillas, `1,596` CX into the **selection register** itself, and `2,569` CX have a word bit as control, i.e. the layer feeds back). The reachable set is not a free re-wiring of a fixed basis. |
| (e) patch cost for blocks 0..4 | **+40…+200 CCX per circuit** (§4), i.e. **+1,200…+6,000 T per pass** |

## 1. The 292-Toffoli decomposition (exact)

`angle_k_0`, 292 CCX total; classification by target wire:

| class | count | targets | operands (examples) | data dependence |
|---|---:|---|---|---|
| product / address CCX | **80** | wires 51..127 (all 77 ancillas; 74 written once, 3 twice) | `(4,5→51) (4,6→52) (5,6→53) (4,7→54) (5,7→55) (6,7→56) (4,8→57) … (4,53→70)` | **none** — pure monomials of selection bits 4..10 |
| data CCX | **212** | the 35 word bits that take CCX (11..49, skipping some) | `(100,105→13) (104,9→38) (77,73→19) (51,81→20) (85,66→24) (107,91→32) (76,120→12) (63,1→40) (65,96→44) (111,126→17) (56,53→45) (98,10→48)` | **yes** — the control pairs are table-specific |

Note the second class mixes (i) ancilla∧ancilla = a product of two high-bit monomials
(still block-level), and (ii) ancilla∧low-bit — which is the *only* way the 4 low
address bits can enter nonlinearly, and therefore the mechanism that carries the
intra-block data.

## 2. Why there is no "fixed product basis + CX fanout"

The hypothesis was: block b's 16 addresses share one product-ancilla set and differ
only by CX connectivity. What the tape actually shows:

* The 77 product ancillas depend on **selection bits 4..10 only**. So inside one
  block (fixed bits 4..10) every ancilla is a **constant**, and no CX from an
  ancilla can vary across the 16 addresses of the block. All intra-block variation
  must come from the low bits 0..3, which are only 4 wires.
* 4 linear terms can produce at most 16 affine patterns per word bit — and the
  measured data is **not affine within blocks** (`RESULT.md` §2: ~24,300 value runs
  over 1,220 addresses ≈ one run every two addresses). So the intra-block data
  **must** be produced by the 212 data CCX, i.e. by products of a block monomial
  with a low bit (or with another monomial).
* Therefore the data is a **(block × bit) coefficient matrix over a small basis of
  low-bit functions**, and the coefficients are realised by *which CCX exist*.
  Changing a coefficient = changing a CCX.
* Additional evidence that this is not a clean fanout layer: the tape also
  **writes the selection register** (1,596 CX into wires 0..10, restored by the end
  — the verifier checks the selection is unchanged), and **uses word bits as CX
  controls** (2,569 CX). Both make the layer non-local.

## 3. What the self-check said (honest)

I replayed the tape symbolically over all 2^11 addresses (X/CX/CCX/SWAP/R/HMR as
value transforms) and compared the word registers with the shipped delta table. It
**does not reproduce at any setting tried**: 12 variants (anti-control flag
0x100/0x200/0x400 × reversed address bit order × HMR resets or not) all land at
**50.05–50.17 % agreement**, uniformly over all 40 bits (46.6–53.6 % each) and
uniformly over rows 0..75 (50.2 %) and rows 80..1219 (50.2 %). Chance level
everywhere means the two tables are *unrelated*, i.e. the shipped circuit does not
implement `delta[k]` under the identity row→address map I assumed (the reference
`angle_k_reference_circuit.py` documents delta, but these are different bytes).
**Open item**, and it is recorded as such: every structural claim in §1–§2 rests on
the *operand census*, which is exact and independent of the replay — it does not
depend on knowing which table the circuit loads.

## 4. Cost of a block-local patch (the number that decides the lever)

* Cells to change: rows 0..75 = **5 blocks × 40 bits = 200 (bit, block) cells**
  (plus the 4 don't-care rows 76..79).
* The 212 data CCX serve 40 bits × 77 blocks = 3,080 cells → **14.5 cells per CCX**,
  because each block monomial (a product of 4–5 of the 7 high bits) is true on
  8–32 blocks. **Sharing is what makes them cheap, and it is exactly what forbids a
  local edit**: any CCX that is changed also changes every other block in its support.
* A *new* product confined to blocks 0..4 must be a monomial of the high bits with
  negations (anti-controls exist), so it covers **at most the 5 blocks** — i.e. at
  most 5 cells (one per block, one bit) per CCX. Two bounds:
  * lower: 200 cells / 5 cells-per-CCX = **+40 CCX per circuit**
  * upper (cells not aligned across blocks): 200 cells / 1 = **+200 CCX per circuit**
  * This is a *bracket*, not a measurement: the exact number needs the new table.

| patch cost | Δangles (15 circuits × 2 passes) | ΔT_total | cost with λ 46.92→36 (×0.767) | verdict |
|---|---:|---:|---|---|
| +0 (the hope) | 0 | 0 | **−23 %** → GM +2.0 | not available |
| +40/circuit | +1,200 | 15,906 | 0.767 × 1.082 = **0.830** → GM **+0.6** | pays |
| +100/circuit | +3,000 | 17,706 | 0.767 × 1.204 = **0.924** → GM **+0.25** | marginal |
| +200/circuit | +6,000 | 20,706 | 0.767 × 1.408 = **1.080** → GM **−0.26** | loses |

**Break-even: the patch must stay below ≈ +120 CCX per circuit** (≈ +3,600 T per
pass) for the λ 46.92→36 lever to be positive, and below ≈ +170 per circuit for
λ 46.92→39. Since the measured structural estimate straddles that line
(+40…+200), **this lever is a coin flip on the patch cost, not a free win** — and
the only way to settle it is to synthesise the new table and count.

## 5. Recommendation

1. **Do not assume a 0-cost patch.** The data is 73 % of the Toffolis and it is
   carried by table-specific CCX operands; the CX layer is an accumulator with
   word-bit feedback, not a rewiring layer.
2. The decisive next step is **not** more tape forensics: it is to hand the new
   `angle_words` (for the new `W`) to the *team's own* planner (`planner.py` /
   `emit_plan.py`, the emitter that produced 268) and read off `angles_toffoli`.
   That emitter already exists in the pipeline that produced `a73b25d2`; the
   scout's "no public emitter" only rules out third-party generators.
3. If the planner is unavailable, the fallback is a **cell-local re-synthesis** of
   the 5 changed blocks: keep the 80 product CCX and the 212−k data CCX that are
   already block-confined, and add new confined products only for the changed
   cells, then count. That is a bounded job (200 cells) and would give the exact
   patch cost.

## 6. Kernel ref and scope

| kernel | purpose | outcome |
|---|---|---|
| `zhuating/qcc-chem-angle-patchtest` | parse `angle_k_0`, symbolic replay self-check, exact Toffoli decomposition by target class, product-ancilla operands, CX layer census (targets/controls, selection writes, word-bit feedback) | COMPLETE — all of §1–§2 is from this run; the replay self-check failed (50 % mismatch, §3) and is recorded as open |

* Exactly what is verified: the operand census (292 CCX classified 80/212, every
  operand pair printed), the product-ancilla set (77, monomials of bits 4..10),
  and the CX layer totals (3,249 / 14,325 / 1,596 / 2,569).
* Exactly what is *not* verified: the symbolic-replay model (§3) and therefore any
  statement of the form "the circuit computes exactly table X". Consequently no
  patched circuit was built and the official `recover_words_from_circuits` check
  was not run — the 0-cost route was refuted structurally before it could be tested.
* No simulation, no verifier, no submission, all kernels CPU-only and private.
