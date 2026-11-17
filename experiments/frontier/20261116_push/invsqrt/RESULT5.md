# invsqrt RESULT5: structural diff f2cdab0b → 0af21cb8, mechanism and headroom

Work in `experiments/frontier/20261116_push/invsqrt/`. Account `jiyujia` Kaggle CPU only
for grading; local work below is hash + 88-byte-header + native-macOS-`kickmix`
**static parse only** (`analyze_live.py` `load_ops`, no simulation, no local verifier).
No new candidate was built, no verifier was run, nothing submitted.

## 0. Verdict

**The ~4.75 mean-Toffoli saving is a generator re-emission that converts unconditional
ripple-carry Toffolis into X-basis-measured, classically-conditioned dual branches —
the "classically conditional" direction flagged in `RESULT.md` §7, worked around the
missing Z-basis measurement with a both-branches-emitted construction.** Static
decomposition is exact: **8 fewer unconditional Toffoli-likes (−8.0 mean) against
+9 conditional Toffoli-likes (+3.25 mean) = −4.75 mean.** Phase/rotation side is
untouched (same `worst_x 231`, same ratio 0.9995606 → no rotation headroom by the
`RESULT.md` §2 argument). T side untouched (2.500079 → 2.499900, no T opcodes exist).

**Mechanism is NOT spent, but NOT hand-applicable either.** Same-class headroom is
precisely located: **4 unconverted ripple-staircase triples** (new-file indices
12139, 12138→12144 block, 12596, 13037 — the retained heads of the three converted
ripples). Converting them needs the generator's branch construction (measured-carry
+ complementary conditional branches + wire relabel), which cannot be made
correct-by-construction by hand-editing 20k-op text. **Blocker: generator access
(maoxin v27 flow). No concrete hand edit exists → no candidate built, no Kaggle
verifier run.**

## 1. Identity (local hash + header only)

| file | sha256 | size | header note |
|---|---|---:|---|
| OLD `f2cdab0b…` (`artifacts/20261116_intel/ds/jn/invsqrt.kmb`) | `f2cdab0b7afc…b48726` | 179,768 | `…ff50…1706…` |
| NEW `0af21cb8…` (`/tmp/.../qcc_verify_new/dataset_flat/invsqrt_0af21cb8.kmb`) | `0af21cb82332…a8856b1b` | 180,382 (+614 B) | `…6151…1806…` (differs) |

`5eeea23b` (179,768 B) is header-identical to `f2cdab0b` (same size class).

## 2. Official numbers before → after (both UNCHANGED-verifier PASS, full 200,540,928 shots)

| metric | OLD f2cdab0b (`RESULT.md` §2) | NEW 0af21cb8 (verify_new §3) | Δ |
|---|---|---:|---:|
| score | 75006.37653863191 | 74797.36535717871 | **−209.01118 (−0.2787%)** |
| mean Toffoli | 1464.1250896974009 | 1459.3748802688297 | **−4.75021** |
| max Toffoli-like | 1559 | 1560 | +1 (static) |
| T | 2.5000790611680026 | 2.499900279707492 | −0.00018 (≈0) |
| C = mean+T/4 (+239.94 rot) | 1704.6903758779981 | 1699.9401217540617 | −4.75025 |
| rotations / eps | 33 / 1.64e-13 | 33 / 1.64e-13 (same) | 0 |
| depth | (1244 inferred¹) | 1233 | −11 |
| num_ops | (20735 inferred²) | 20833 | +98 |
| worst / worst_x | 0.9995605646154175 / 231 | identical | 0 |
| qubits | 44 | 44 | 0 |
| GM (w/ `66b4f18b`+`bdae290f`) | 28.10154193 | 28.12769291 | +0.02615 |

¹ Depth 1244 is `5eeea23b`'s official number; `f2cdab0b` receipt (`RESULT.md` §2) did not
quote depth, but it is header-identical to `5eeea23b` (verify_new §1), same size class.
² 20735 = static text ops 20758 − 23 directives (22 `APPEND_TO_REGISTER` + 1 `REGISTER`);
same arithmetic gives exactly the official 20833 for the new file (20856 − 23). Consistent.

Score check: 44 × ΔC = 44 × (−4.7502541) = −209.01118 ✓ (ΔC = ΔmeanT + ΔT/4).

## 3. Static opcode diff (parse only; totals 20758 → 20856, +98)

| op | OLD → NEW | Δ | | op | OLD → NEW | Δ |
|---|---|---:|---|---|---:|
| CCX | 1530 → 1526 | −4 | | CCZ | 29 → 34 | +5 |
| CX | 12312 → 12316 | +4 | | CZ | 2100 → 2136 | +36 |
| HMR | 1262 → 1276 | +14 | | X | 953 → 964 | +11 |
| Z | 1037 → 1045 | +8 | | PUSH/POP_CONDITION | 680/680 → 697/697 | +17/+17 |
| BIT_STORE1 | 6 → 0 | −6 | | BIT_STORE0 4→3, BIT_INVERT 53→54, NEG 34→30 | | small |
| Z_POW 43, SWAP 12, APPEND/REGISTER 23 | | 0 | | | | |

Toffoli-like inside vs outside conditions:

| | OLD | NEW | Δ |
|---|---|---:|---:|
| CCX outside (always fires) | 1377 | 1369 | **−8** |
| CCX inside | 153 | 157 | +4 |
| CCZ inside (none outside either file) | 29 | 34 | +5 |
| implied inside firing contribution (mean − outside) | 87.125 / 182 gates | 90.375 / 191 gates | **+3.25** |

−8.0 + 3.25 = −4.75 ✓. Max static 1559 → 1560 matches official.

## 4. Where it changed (difflib on op-name streams; indices = OLD → NEW)

Three **repeated conversion sites** (identical edit shape; divider/coefficient ripple region):

- OLD `CCX → HMR+PUSH_CONDITION+4CX` at old 12125 / 12491 / 12854 (each a ripple
  staircase tail, e.g. old `[12119..12128]`: four unconditional
  `CCX+2CX` staircases `[31,15,16],[29,14,15],[26,13,14],[27,42,13]`), replaced by:
  `HMR qX[bit]` + conditional compute block (**34 ops**: CX 17, X 8, **CCX 2**,
  PUSH, Z 2, CZ 2, **CCZ 1**, POP) + conditional phase block
  (**28 ops**: 4×PUSH/POP, Z 6, CZ 11, HMR 2, BIT_INVERT) + `BIT_INVERT` +
  re-application under the inverted bit (dual branch — exactly one branch's
  Toffolis fire per shot). Cf. NEW `[12145..12262]`, `[12599..12707]`, `[13040..13147]`.
- Surrounding each: CX bookkeeping inserts/deletes (±2..6 CX), `CCX→CZ+CZ+POP`
  fold-downs (old 11898, 12350, 12778), NEG/Z/CZ substitution of deleted
  `CX/CCX` runs (old `[12699..12723]`: −CX 14 −CCX 2 +NEG/Z/CZ).
- Scattered unconditional-CCX deletions with conditional replacement:
  old `[14374..14410]` (−CX 35 −CCX 1), `[17753..17754]` + `[17856..17924]`
  (−CX 62 −CCX 1, −CX 5), tail x-restoration rewrite old `[20432..20504]` →
  NEW `[20493..20602]` (−CCX 5 +CCX 4 +CCZ 1 +PUSH/POP+HMR; `RESULT.md` §5 flag
  cluster `[20508..20702]`), BIT_STORE1 eliminated (6 → 0) in readout rewrite
  old `[19406..19583]` → NEW `[19501..19583]`.
- **Phase-block rewrite** in the `[18003,18984]` peak run: old `[18102..18398]`
  (−Z 102 −CZ 161 −14 PUSH/POP) replaced by larger redistributed Z/CZ/PUSH/POP
  blocks (NEW `[18188..19501]`; net CZ +36, Z +8 — Clifford-only, cost-neutral,
  correctness scaffolding for the moved Toffolis).
- **Global wire relabeling** (generator re-emission signature): outside-CCX targets
  migrate `q41: 281→230, q42: 242→305, q36: 53→27, q34: 27→53, q20: 82→52,
  q21: 63→80, q9: 83→66, q32: 21→50` — role swaps, not local patches.
- No adjacent self-inverse duplicate pairs and no adjacent CCX duplicates in either
  file (0/0): no free cancellation headroom.

## 5. Headroom analysis

- **Same-class convertible (located, not hand-buildable): 4 staircase triples**
  `CCX+CX+CX` still unconditional in NEW at **12139 `[31,15,16]`**,
  **12142 `[29,41,15]`**, **12596 `[31,21,15]`**, **13037 `[8,41,15]`** — the
  retained ripple heads immediately before the three converted tails (HMR at NEW
  12145, 12599, 13040). Each converted tail saved ~1–1.5 mean Toffolis (3 sites ≈
  half the −4.75); heads are worth comparable amounts *if* the measured-carry +
  dual-branch construction applies recursively (head target feeds the tail, so the
  branch redesign must be redone, not copied). Expected value ≈ −2 to −4 further
  mean Toffolis (≈ −90 to −180 score, +0.01 to +0.02 GM) — generator work.
- **Other unconditional CCX: 1369 remain.** Convertibility is semantic (needs a
  measurable ancilla + cheap condition per site); static census alone cannot
  promote any of them to "concrete edit". A generator-level gadget census of the
  author's construction (à la dqi k19) over all 1369 is the follow-up, not file work.
- **Rotation/angle: none.** Same binding `worst_x 231`, same ratio 0.9995606; smallest
  angle 2^-35 turns is 2.3× the 4.4e-4 margin (`RESULT.md` §2) — removal still
  invalid, adding rotations still net-negative. Phase stage untouched by the author.
- **T: none.** No T/TDG opcodes in either file; t_count ≈ 2.5 both.
- **Q: none.** Peak-live-43 run `[7785,7788]` unchanged; occupancy floor 44
  (`RESULT.md` §4) unaffected — new file keeps 44 wires with same first/last touches
  on all flags (q22..q25 first-touch 240/250/255/257 both files).
- **Depth −11**: side effect of deleted CX chains (−61/−35/−20 runs); no cost lever.

## 6. Blocker / next step

No concrete hand edit exists: the conversion is a semantic branch redesign +
global relabel, and hand-replicating it at the 4 leftover sites cannot be made
correct-by-construction (local simulation forbidden; a blind guess would burn
~3 × 600 s full-shot Kaggle verifications at near-zero PASS probability).
**Nothing built, no verifier run, no submission.** Hand to generator owner:
apply the §4 dual-branch construction to NEW 12139/12142, 12596, 13037 and
re-emit; expected ≈ −2..−4 mean Toffolis if firing rates match the converted tails.

## 7. Kernel refs (this session: static only; grading runs cited, not repeated)

- `zhuating/qcc-verify-new-4-files` v1 (unchanged verifiers, full shots default + 2
  salts): NEW file **PASS 74797.36535717871 / 74797.36796904955 / 74797.38784421439**
  (verify_new §0–§3). Not re-run here per mandate (fresh file, already verified).
- Local scripts reused read-only: `analyze_live.py` (parse), difflib region map and
  inside/outside counters (one-off `uv run` snippets, no files written).
