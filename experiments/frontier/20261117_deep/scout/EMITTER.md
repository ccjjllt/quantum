# ANGLE-loader emitter: what is public, and can it rebuild the 15 loaders?

Scope: 20-minute source hunt. Read-only Kaggle MCP + `kaggle kernels pull` +
dataset member downloads. Nothing generated, nothing simulated, nothing submitted.

## Verdict (3 lines)

1. **No public emitter exists for the shipped 15-loader family.** Every maoxin123
   chemistry kernel is a *packaging* kernel with the circuits embedded as zlib/base64
   blobs; `marculera/dfthc-c44-build` ships only the 15 `.kmb` + `submission.npz` and its
   NOTICE says outright "Our planner and circuit builder are our own code".
2. **A public generic emitter does exist** (`taylorclark637/dfthcsos-generator`), and it
   accepts an arbitrary `(num_vectors, 75)` word table, but it costs **N−2 Toffolis per
   circuit**, i.e. 1,218 × 15 = **18,270 per pass** vs our 4,022 → T 43,202 vs 14,706 →
   **cost 865.6 M (×2.94)**, so it cannot rebuild at equal cost.
3. **The 8,044 is a property of the *words*, not of the emitter**: our loaders average
   268 Toffolis per circuit because the word bits are low-degree Boolean functions of
   4 address bits inside blocks of 16 (coded words, XOR-of-five-word codes, π-gauge,
   banked QROM). A new 76-row one-body table can keep the cost only if it keeps that
   block-wise code structure; otherwise the cheapest public route is a surgical patch of
   the 5 affected 16-address blocks in the `.kmb` (public `vqcc_ir.py`), not a re-emit.

## 1. What was checked (kernel / dataset → files → finding)

| source | version / run | files inspected | finding |
|---|---|---|---|
| `maoxin123/qcc-28-14-4-022-toffoli-chemistry-loaders` | 2026-11-17 02:16, v3 | 12-cell 805 KB source + 10-cell 45 KB source (both pulled) | **blobs only** (`CHEM = {'weights': …, 'blob': '/Td6WFo…'}`); code cells are `import io, lzma` + `base64.b64decode` + sha256 pins + official verifier calls. No builder |
| `maoxin123/qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` | 2026-11-17 02:04 | same | invsqrt blob + DQI/chem **pinned from datasets**, no chemistry builder |
| `maoxin123/qcc-v27-4028-toffoli-coded-word-chemistry` | 2026-11-14 08:17, v1 | full source (45.6 KB) | `def walk/sha_stream/candidates/run` only — packaging |
| `marculera/df-thc-11-38x-codes-on-the-xor-of-five-words` | 2026-11-15 12:45 | 12 cells (analysis) | measures `evaluate_words`, sign mixing, block degrees, runs the official verifier. **No emitter**; "The build rests on public work, credited in full in NOTICE" |
| `marculera/dfthc-c44-build` (dataset) | v6, 2026-11-15 | 18 members | `angle_k_0..14.kmb` (350,614–421,737 B) + `submission.npz` + `LICENSE` + `NOTICE`. **No source.** NOTICE: "Our planner and circuit builder are our own code, run on our own words"; credits the *design* to mrmeows, kozykappa, syed3000, gengsr, heliosli, maoxin123 |
| `mrmeows/qcc-14-50-everything-i-learned-open-circuits` | 2026-10-26 | 10.2 KB source | write-up only (`def sha`), no builder |
| `mrmeows/21-0-circuits-let-s-all-reach-the-plateau` | 2026-10-27 | — | same class, no builder |
| `manwithacat/vqcc-agent-toolkit` | v4 | file list (60+) | kickmix viewer / bilinear-synth debugging tools, **no chemistry ANGLE emitter** |
| **`taylorclark637/dfthcsos-generator`** | v2, 2026-11-16 | `dfthcsos_gen.py` 12,124 B, `dfthcsos-generator-design.md` 14,939 B, `manifest.json` | **the only public working emitter** (see §2) |

The shipped 15 loaders themselves are `marculera/dfthc-c44-build`'s
(`angle_k_0` = `aed6aa7c…`, `angle_k_14` = `ab06b98f…` — identical to the standard family
in our pipeline for the 415,169/362,314 B set; our run uses the *small* 129–180 KB set
from maoxin's v27, same codes on a different loader build).

## 2. The public emitter and why it cannot match 8,044

`taylorclark637/dfthcsos-generator/dfthcsos_gen.py` builds a **delta-unary loader**: for a
`sel_bits` selection address it XORs a classical delta table into `word_0..word_{J-1}`,
`delta_k = batch_k XOR batch_{k-1}`.

Design note's measured facts:
- `num_toffoli_like = N − 2` per circuit, **independent of J and brot** ("the address
  decode dominates, the output fanout is Clifford CX"); measured N=3,976, J=8, brot=12 →
  3,978 Toffoli-like, 120 qubits, depth 12.
- qubit check: `sel_bits + J*brot + sel_bits ≤ 128`.
- rejects Z_POW, writes real binary `.kmb`, emits `manifest.json` with per-circuit stats
  and `angles_toffoli_forward_plus_reverse = 2 × Σ per-circuit`.

For **our** table (`rows = 76 + 8·143 = 1,220`, `J=5`, `brot=8`, `K=15`):

| quantity | our shipped loaders | generic emitter |
|---|---:|---:|
| Toffoli per circuit (per pass) | **268.1** (4,022 / 15) | **1,218** (N−2) |
| angle Toffolis per pass | **4,022** | **18,270** |
| `T_total` (`6,662 + 2×`) | **14,706** | **43,202** |
| `Q_total` (angle temp 11 < inner 303) | 427 | 427 |
| chem cost (λ_eff 46.9217) | **294.64 M** | **865.58 M (×2.94)** |

So the generic emitter is a correct, verifier-grade emitter but 4.5× worse per pass; it
would turn a +0.6…+2 GM lever into a −0.8 GM regression. `J=8, brot=8` would give 10
circuits × 1,218 = 12,180/pass → T 31,022 (×2.1), still far worse.

Why ours is 268 and not 1,218: the word table is **coded**. Per `marculera`'s NOTICE and
notebook: addresses come in blocks of 16; each word bit is a Boolean function of the 4
block-address bits of low algebraic degree; the codes live on the XOR of the five words of
a batch (bits 1–2), plus a signed-Givens π-gauge (top bit = bit below), a banked QROM of
ANF deltas, and a five-block low-monomial plan. That structure is what turns an 11-bit
1,220-row lookup into ~3.5 Toffolis per block. It is **not implemented in any public
file**; the emitter that produces it is marculera's private code (and maoxin123's variant).

## 3. What this means for "replace the 76 one-body rows, keep 1,144 rows"

Rows 0…75 are addresses 0…75 = **5 blocks of 16** (block 4 = addresses 64–79, 12 real +
4 padding). Only those 5 blocks can change. Three routes:

1. **Re-emit with the same codes (needs the private planner).** If the new one-body words
   are constrained to the same block-wise low-degree codes and the same XOR-of-five-word
   relation, the loader cost is identical (the planner's cost is a function of the code
   degrees, not of the values). This is the only route that *provably* keeps 8,044.
2. **Surgical patch of the 5 blocks in the `.kmb`** — public tooling exists:
   `grantprater/vqcc-dqi-61c8348d-merged-closings` ships `vqcc_ir.py` (read/write `.kmb`
   as numpy arrays), `vqcc_measure_out.py` (product/measure-out rewrite), `vqcc_pair_window.py`
   (exact window prover) and `vqcc_bitsim.py` (bit-parallel basis simulator). Cost delta is
   bounded by 5 blocks × 5 words × 8 bits: worst case an arbitrary 4-bit function ≈ 14
   Toffolis/bit → **+2,800** (T +19%); degree-2 ≈ 2–3 ANDs/bit → **+400–600** (T +3–4%).
   The patch must be re-verified by the official verifier on several salts.
3. **Generic re-emit** — rejected by the arithmetic in §2.

Practical instruction for the chemistry line: when producing the new `(1220, 75)` words,
**keep the block-of-16 code constraints on rows 0–75** (degree ≤ 2 in the 4 address bits,
XOR-of-five-word relation on bits 1–2, π-gauge top bit) so that route 1 or 2 stays at
constant cost; an unconstrained 8-bit re-rounding of the one-body rows can cost +19% of T
even in the best public route.

## 4. Minimal usage of the public emitter (for reference / fallback only)

Files copied to `experiments/frontier/20261117_deep/scout/emitter/`:
`dfthcsos_gen.py`, `dfthcsos-generator-design.md`, `dqi-dfthcsos-verifier-spec.md`,
`manifest.json` (all text; no circuits, no logs).

Input: an integer array `angle_words` of shape `(num_vectors, 75)` with values in
`[0, 2**brot)`, saved as `.npy` or as `.npz` with key `angle_words`.
Output: `angle_k_<k>.kmb` (real binary kickmix, no Z_POW) + `manifest.json`.

```bash
# epoch-appropriate interpreter with kickmix (qualitatively Qualtran's kickmix wheel)
python dfthcsos_gen.py --words-npz words.npz --out-dir out/ --brot 8 --J 5
# or: --words-npy words.npy ; --strategy delta-unary (default) | init-lookup (2**sel_bits-2, dearer)
# it self-checks: J*brot + 2*sel_bits <= 128, no Z_POW, per-circuit qubit cap
```

For our table: `num_vectors = 1220`, `sel_bits = 11`, `J=5` → 11+40+11 = 62 qubits per
circuit; 15 circuits; **18,270 angle Toffolis per pass** (not 4,022).

`verify_dfthcsos_local.py` (35.5 KB, not copied) is a local re-implementation of the
verifier — do **not** use it for grading; grade with the competition's unchanged
`verifiers/dfthcsos/verify.py` in a Kaggle CPU kernel.

## 5. Bottom line for the decision

- **No public emitter can rebuild the shipped 15 loaders at 8,044.**
- The lever is still reachable, but only as a **patch of 5 blocks** (public `vqcc_ir.py`
  route) on words that keep the block-of-16 codes; budget **T +400…+600** (patch of a
  degree-2 re-encode) and treat +2,800 as the worst case if the codes are broken.
- If the new one-body words cannot be made code-compatible, the lever must stop at the
  continuous point — a generic re-emit costs ×2.9.
