# `dqi_surgery` — interface map + replacement spec for tape `575b043f`

Round: 2026-11-18, time-boxed to 90 min. **No implementation, no verifier run, no submission, no
edit to `data/competition/` or `submissions/`, no write to any existing tape.** Two Kaggle CPU
kernels read the tape; both delete it before exiting.

## Files

```
INTERFACE.md   the measured EEA -> Chien -> rev interface (deliverable 1)
SPEC.md        the normalized-divstep replacement spec + T budget (deliverable 2)
VERIFY.md      k_patch usage, 3 salts, the gate, rollback (deliverable 3)
RISKS.md       R1..R8, priced (deliverable 4)
k_map/main.py  survey pass 1  (anchors, Chien trace, censuses, block ladder, cut liveness)
k_map2/main.py survey pass 2  (the real cut, the 183,995-op realignment sweep, block templates)
out/           every JSON / listing the two kernels produced, plus both kernel logs
```

Kernels: `zhuating/qcc-dqi-surgery-map` (107 s, COMPLETE), `zhuating/qcc-dqi-surgery-map2`
(COMPLETE). CPU only, GPU/TPU false, internet off, tape deleted at exit.

## The five results that change the plan

1. **The real forward cut is 30,151,421, not 30,335,416.** The tape's last EEA multiplication
   `CCX` is at 30,151,420 (`S1[0] × S3[0] → Q868`). The anchor at 30,335,416 sits *inside* the first
   Chien position (its 10-CCX chain runs 30,335,009…30,335,027). Splicing at the anchor ships half a
   position. All six candidate cuts are depth 0, so `splice.py` cannot catch this on its own.
2. **There is a 183,995-op, 11-Toffoli realignment stage between the EEA and the Chien**
   (183,037 `CX`, 479 `SWAP`, all 71 words 0…71 touched, hot word sweeping monotonically). That is
   the reference's `_initial_shift_loop` living *between* the two, and it means the new EEA only has
   to reproduce the **pre-sweep** layout, not the Chien's. Cost 0 T ⇒ keep it.
3. **No `S*` word is in flight across either Chien boundary.** The Chien is a pure phase stage at
   word level; the only quantum state carried across is 10 pool qubits (`Q864…Q889` subset) + the
   mask register + 13 flags. That is what makes "keep Chien, replace both EEA passes" sound.
4. **The forward EEA's Toffoli stream has zero conditioned `CCX`** (153,185 total, 153,175 of them
   = 3,647 complete 42-CCX multiplies). Fixed, unrolled schedule ⇒ a 69-step divstep needs no
   counter. The reverse pass is *not* a mirror: 6,441,970 `BIT_INVERT_IF` and 226,522 `SWAP` against
   3,527 and 58,470 going out.
5. **The Chien tests words that pair up two apart, four apart across pairs** — `(8,9), (12,13), …,
   (64,65)` plus `69, 71`; 32 distinct words, 4,024 positions, and the tested word is a
   *function of the position index `j` with no exceptions*. Combined with the EEA's stride-2
   operand ladder (first multiply `word 0 × word 1`; control ladder `0,2,…,44`) this reads as the
   70-word array being two interleaved 35-word polynomials.

## Cost consequence (exact closure)

```
static Toffoli 367,989 = EEA 321,762 (= 7,661 × 42, exact) + Chien 44,275 (4,025 × 11) + 1,952 CCZ
```

Replacing the EEA with 69 divsteps × 35 effective words × 42 T per scalar row, twice:

| | T |
|---|---:|
| new EEA, both passes | 202,860 |
| Chien/Forney, kept | 46,227 |
| **new mean T** | **249,087** |
| GM | **32.07** |
| gate | meanT ≤ 264,700 ⇒ GM 31.43 ⇒ **15,613 T of slack = 113 T per step for normalization** |

## TODO (explicitly not done this round)

* **TODO-1** coefficient orientation (is `word 0` the leading or the constant coefficient) and which
  word holds ω. One dump of the first three EEA multiply blocks with the `CX` fan-out resolved.
* **TODO-2** does a 42-CCX block multiply two words of the same half (Bezout row free) or one of
  each half (a second row — the budget doubles, GM 26.3)? Same dump settles it. **This is the one
  that decides whether the round is worth running.**
* **TODO-3** the mirror cut on the reverse side (the first EEA `CCX` on the way back); by symmetry
  it is P2's mirror, not measured.
* **TODO-4** small-parameter end-to-end (`m=63, n=6, degree=4`) proving the projective/divstep form
  at 0/0 on three salts — the precondition for the 202,860 budget.

## Commands used (reproducible)

```bash
# pass 1 — anchors, Chien trace, censuses, cut liveness, block ladder
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_surgery/k_map \
      --slug qcc-dqi-surgery-map --account zhuating \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings --competition
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_surgery/k_map --account zhuating
python scripts/kgpu.py logs --kernel zhuating/qcc-dqi-surgery-map --account zhuating -n 40

# pass 2 — the real cut, the realignment sweep, block templates, tape head/tail
python scripts/kgpu.py new  --dir experiments/frontier/20261118_push/dqi_surgery/k_map2 \
      --slug qcc-dqi-surgery-map2 --account zhuating \
      --dataset grantprater/vqcc-dqi-61c8348d-merged-closings --competition
python scripts/kgpu.py push --dir experiments/frontier/20261118_push/dqi_surgery/k_map2 --account zhuating
python scripts/kgpu.py logs --kernel zhuating/qcc-dqi-surgery-map2 --account zhuating -n 40

# outputs land in /tmp/kgpu_logs_*/out -> copied to dqi_surgery/out/
```

## Honest limits

* Two measurements in `INTERFACE.md` §3 were taken with a ±3,000-op window and one attempt at a
  precise per-qubit handoff had an inverted comparison (`handoff_*` in `survey2.json` is
  meaningless; do not use it). The live-across sets quoted are the pass-1 numbers and are correct
  as window statistics, not as exact last-touch/first-touch tables.
* The Chien's *semantic* identity (which polynomial each word holds, why the tested word is a
  function of `j`) is not reconstructed — only the traversal, the pairing, the template and the
  liveness. That is enough to fix the splice points and the T budget, not enough to reimplement the
  Chien (which this design does not do).
* The `46,217` figure in the brief and the `46,227` here differ by exactly the 10 `CCX` of the
  straddling Chien position; both close to 367,989. `SPEC.md` §1 states which one it uses and why.
