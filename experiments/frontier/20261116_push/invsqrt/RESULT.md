# invsqrt 2026-11-16 push: Q-reduction study of f2cdab0b (44Q, 75,006.38)

Branch: `main` (read-only reuse of competition data and public artifacts); all work in
`experiments/frontier/20261116_push/invsqrt/`.
**All circuit simulation and verification ran on Kaggle CPU kernels.**  Locally only static
`.kmb`/`.kmx` parsing with the native macOS `kickmix` (no simulation).

## 0. Verdict

**Q = 44 is a hard floor for `f2cdab0b` as emitted.  Q 44 -> 42/40 is not reachable on this
file by wire retirement, and no exact Toffoli cut exists either.**

Three independent, full-domain-checked facts close the width line on this file:

1. **5,790 ops (of 20,758) need all 44 wires at once**, in 445 disjoint runs spread over the
   whole circuit (19 of those runs are >= 20 ops long and cover 3,166 ops; the longest are
   `[18003,18984]`, `[13296,14255]`, `[1712,1962]`) — there is no local hot spot to
   reschedule.  At every one of those ops the split is exactly *22 x-register wires +
   22 scratch wires*.
2. The **only** wires idle across the two long high-occupancy regions are the four flags
   `q22..q25`.  They are not reconstructible from the other 40 wires: no affine relation at
   19 cut points (all 44 wires tested), and no relation with 1, 2 or 3 pairwise ANDs at 5
   cut points with the exact retired-source sets (full-domain-verified values).
3. **`q24` and `q25` are rare flags**: their full-domain popcounts are 16,320 and **63** of
   3,133,452 inputs, constant at every cut.  Any sampled identity search (including the
   2,500-point probes in this session) is blind to them and will produce false "dead wire"
   readings; the search must be full domain.

Also closed here (so nobody re-spends the quota):

4. **No dead Toffoli.**  A 256-sample activation scan flagged 54 Toffoli-like ops that never
   fired; the full domain shows all 54 do fire.  The normalization ladder fires
   4095/2047/1023/.../3/1 times (a clean binary threshold ladder), and the twelve
   `q25`-controlled `CCX` fire 21-36 times each.  Static Toffoli-like = 1,559 is tight
   against the official input domain.

Positive, reusable finding: **the 33-rotation phase-endpoint stage `[6617,7346]` needs only
34 wires** (10 wires are pure ballast there).  The width is set by the
normalization / table-loader / divider-product stages, not by the phase stage.

## 1. Hypothesis and the arithmetic that motivated it

`score = Q * (mean Toffoli + T/4)`.  At the 28.09090 baseline, Q 44->42 is +0.44 GM and
Q 44->40 is +0.91 GM, while 1% of C is only +0.0034 GM.  Q44->42 tolerates +4.8% C
(C 1,704.69 -> 1,786.5, i.e. +81 Toffoli-equivalents) and Q44->40 tolerates +10.0%
(-> 1,875.2, +170).  So a retire-and-rebuild schedule costing a few dozen Toffolis would
have been a clean win **if** a reconstruction identity existed.

## 2. Baseline receipt (official verifier, unchanged, Kaggle CPU, default salt, full shots)

Kernel `jiyujia/qcc-invsqrt44q-actscan`, file
`f2cdab0b7afc2e76aca12451113ef618e6f7e575a35a29f58264602dafb48726` (179,768 B):

```
status PASS   score 75006.37653863191   num_qubits 44   verified_shots 200540928
toffoli_count (mean) 1464.1250896974009   max_toffoli_count 1559
toffoli_equivalent 1704.6903758779981   t_count 2.5000790611680026
rotation_count 33   rotation_eps 1.6406054738480745e-13
worst_error_over_tolerance 0.9995605646154175   worst_x 231
```

Cost decomposition (recomputed): `1464.125 + 2.5001/4 + 239.94 = 1704.690`; the 33 rotations
cost **7.27 Toffoli-equivalents each** (`0.56 log2(1/eps) + 5.3` with `eps = 1.64e-13`), i.e.
239.94 of the 1704.69.  The phase margin is 4.4e-4 of tolerance — a rotation may not be
removed (the smallest angle, 2^-35 turns, is 2.3x the margin), and adding rotations to buy a
larger `eps` is net negative (one rotation costs 7.27 C, and halving the worst error only
saves 4.6 C).  T axis: closed, consistent with the 2026-11-15 analysis.

## 3. Static structure

```
Q 44  num_bits 377  ops 20,758
CCX 1530  CCZ 29  -> static Toffoli-like 1,559
CX 12,312  CZ 2,100  HMR 1,262  Z 1,037  X 953  Z_POW 43  SWAP 12
PUSH_CONDITION / POP_CONDITION 680 / 680   (153 CCX + 29 CCZ inside condition blocks)
```

## 4. Occupancy model and the peak ledger

A wire is **occupied** at op *t* if it is *live* (its value is read later before being
overwritten) or *dirty* (last write not followed by a reset, so a XOR-shaped write would leak
it).  Two logical wires can share a physical wire only when their occupied intervals are
disjoint, so `max_t |occupied|` is the exact lower bound for any pure re-labelling
(`analyze_live.py`, `plan_q.py`).

```
peak occupied = 44 at 5,790 ops (445 runs); at every peak op: 22 x wires + 22 scratch wires
44-runs: [1712,2537] (793 ops), a 5-op-periodic divider series [2590,6563],
         [13296,14255] (960), [18003,18984] (982), plus ~425 shorter runs
```

The previously suspected phase-endpoint peak (`[7785,7788]`, live 43) is *not* binding.

## 5. Idle-wire census (retirement candidates)

| window | length | fully idle wires |
|---|---:|---|
| `[424, 6616]` | 12,193 | `q22, q23, q25` (`q24` written, read-idle) |
| `[7347, 20500]` | 13,154 | `q22, q23, q24, q25` |
| `[6617, 7346]` | 730 | `q10..q17, q19, q43` (10 wires; stage needs 34) |

Flag clusters (line numbers): `241-423` (computed), `6617-7346` (phase-endpoint decode
lines), `20508-20702` (x-restoration decode lines).

## 6. Reconstruction search (the decisive negative)

Method: the competition's own `kickmix` Simulator on Kaggle CPU, prefix simulations reading
all 44 wires.  Three guards on the method:
(i) a cut-0 assertion (`x` register must equal the input) — it caught a transposed
`read_across_shots` (shape `(wires, batch)`) early, and every number below is from
axis-checked runs;
(ii) determinism across simulator seeds (no nondeterministic wire found);
(iii) **value continuity** across every retirement window — the flag value at the zero site
is bit-identical to the value at the rebuild site for all samples (18/18 pairs `True`).

### 6.1 Affine (pure XOR) reconstruction — 0 hits

Full relation table for all 44 wires at cuts `0, 430, 6610, 6616, 6731, 6732, 6843, 6844,
6845, 6856, 6857, 6975, 6976, 6977, 7232, 7233, 7305, 7347, 20500`
(`jiyujia/qcc-invsqrt44q-relate` -> `evidence/relations.json`), then re-solved with the
exact retired-source exclusions (`jiyujia/qcc-invsqrt44q-plan` -> `evidence/plan_result.json`).

All 30 requested `(cut, flag, retired-set)` combinations returned `NO RELATION`
(`evidence/plan_result.json`).  No wire at those cuts is a 1- or 2-source copy either.

### 6.2 XOR of <= 3 pairwise ANDs — 0 hits

For each flag at cuts `430, 6610, 7305, 7350, 20500`, with all four flags excluded from the
source set, searched `V_f = affine(non-flag wires) + (a1&b1) + ... + (ak&bk)`, k = 1, 2, 3
(k=3 by linear-fingerprint meet-in-the-middle over all 780 control pairs;
`jiyujia/qcc-invsqrt44q-andsearch` -> `evidence/and_result.json`): **20/20 combinations
"none up to k=3"**.  Consistent with the 2026-11-15 exhaustive 0-6 AND result on the 46Q
line.  Cost was never the obstacle: even a 2-AND identity costs 2 CCX per window
(~16 Toffolis total) against a +170 budget.

### 6.3 Full-domain check (the reason sampled probes are not enough)

`jiyujia/qcc-invsqrt44q-deadops`: full-domain (3,133,452 inputs) popcounts, accumulated over
48 chunks of 65,536 shots with the official simulator:

```
cut 1750  q22 838,860  q23 246,723  q24 16,320  q25 63
cut 3000  q22 838,860  q23 246,723  q24 16,320  q25 63
cut 6000  q22 838,860  q23 246,723  q24 16,320  q25 63
cut 13350 q22 838,860  q23 246,723  q24 16,320  q25 63
cut 18500 q22 838,860  q23 246,723  q24 16,320  q25 63
cut 20500 q22 838,860  q23 246,723  q24 16,320  q25 63
```

`q25` is 1 for exactly 63 inputs; `q24` for 16,320.  A 2,500-sample probe sees `q25` as
identically zero (this session briefly concluded it was a dead wire) — it is not.  **Any
future identity search on this circuit must run on the full domain.**

## 7. No dead Toffoli (full-domain activation scan)

A 256-sample activation scan (`jiyujia/qcc-invsqrt44q-actscan`, 1,559 Toffoli-like ops)
flagged **54** ops that never fired: the twelve normalization `CCX` at ops
109/123/131/145/153/167/175/189/197/211/219/234, the 24 `q25`-controlled `CCX`
(6656-6689, 7270-7303), and 8 phase-stage ops.  Full-domain activation counts
(`jiyujia/qcc-invsqrt44q-deadops`):

```
normalization ladder: 4095, 2047, 1023, 511, 255, 127, 63, 31, 15, 7, 3, 1
q25-controlled CCX:   21..36 each
phase-stage 8:        963, 54, 192, 21, 3075, 3371, 960, 841
=> TRULY DEAD: 0
```

Static Toffoli-like 1,559 is therefore tight against the official input domain, and no
"1-2 Toffoli cut" exists in this direction either.

**Lead worth recording for a future session**: the 27 `q25` Toffoli-like gates (26 `CCX` +
1 `CCZ`) each activate on 21-36 of the 3,133,452 official inputs, yet every one is charged a
full Toffoli per shot.  The same holds, less extremely, for the tail of the normalization
ladder (activations 1, 3, 7, 15, ...).  If a way were found to make the `q25` group
*classically conditional* (a classical bit that is 1 only on those x), it would be worth
-27 mean Toffolis = -1,188 cost, about +0.15 GM.  The obstacle is that conditioning on `q25`
needs its basis value in a classical bit, and `kickmix` offers only `HMR` (X-basis
measurement), which destroys a basis value and returns a random bit.

## 8. Why Q=42/40 is blocked, precisely

1. Width is set by `normalization + first loader` (`[1712,2537]`), and the `divider` series
   (`[2590,6563]`, `[13296,14255]`, `[18003,18984]`): at every peak op exactly 22 x bits
   **plus** all 22 scratch wires are simultaneously occupied.
2. The only wires idle in those regions are `q22..q25`; retiring any of them needs an exact
   identity at both window ends.
3. No identity exists with <= 3 ANDs at 5 cuts covering both ends of both regions, and none
   is affine; the 46Q line already proved the analogous search negative to 6 ANDs.
4. Remaining routes are generator-level, not file-level: a >= 4-AND / SAT-synthesised
   identity for `q22..q25`, or re-synthesising normalization/divider so the 22 scratch
   values fit in 20 — i.e. exactly the hand work that produced 46 -> 44.

## 9. Files

Local analysis and generators (`experiments/frontier/20261116_push/invsqrt/`):

| file | purpose |
|---|---|
| `analyze_live.py` | kmx parser, liveness, per-op live mask |
| `occupancy.py` | dirty-interval occupancy model |
| `schedule.py` | window / peak reporting |
| `access_map.py` | per-wire access map over a window |
| `who.py` | occupied set at one op |
| `plan_q.py` | retire spec + interval colouring / physical width |
| `build_candidate.py` | zero/rebuild insertion (CX + `R`) and renumbering |
| `prune.py` | delete chosen op lines |
| `gen_probe.py`, `gen_relate.py`, `gen_plan.py`, `gen_andsearch.py` | relation-search kernel generators |
| `gen_actscan.py` | activation scan + full official verification |
| `gen_constscan.py`, `gen_ones.py` | constant-wire / ones-count scans |
| `gen_deadops.py` | full-domain activation counting |
| `gen_verify.py` | generic candidate verifier kernel (full or `--shots-per-x` / `--salt`) |
| `evidence/` | small JSON outputs kept for audit |

Kaggle kernels (account `jiyujia`, CPU, no internet, competition data only):

| kernel | purpose |
|---|---|
| `qcc-invsqrt44q-wire-probe` | determinism + first relation attempts |
| `qcc-invsqrt44q-relate` | affine relation table, 19 cuts, all wires |
| `qcc-invsqrt44q-plan` | relations with exact retired-source sets + continuity |
| `qcc-invsqrt44q-andsearch` | <= 3-AND reconstruction search |
| `qcc-invsqrt44q-actscan` | activation scan + full official verification (baseline PASS) |
| `qcc-invsqrt44q-constscan` | constant-wire scan at 13 peak ops |
| `qcc-invsqrt44q-ones` | sampled ones-count, 16 cuts, two seeds |
| `qcc-invsqrt44q-deadops` | full-domain activation counts + full-domain popcounts |

## 10. Verification scope (explicit)

- **Full official verification, default salt, 200,540,928 shots**: `f2cdab0b` only
  (`PASS`, 75,006.37653863191).  This is a baseline receipt, not a new candidate.
- **Full-domain value simulation** (3,133,452 inputs, official `kickmix`): wire popcounts and
  per-op activation counts as quoted above.
- **Sampled** (2,500 / 1,500 / 999 / 500 / 256 inputs, seeds checked): identity searches,
  determinism, continuity.
- **Static, local, no simulation**: peak ledger, idle census, colouring, cost arithmetic.
- **No new candidate was built and nothing was submitted.**  No claim of a Q or T reduction.

## 11. Next step

Nothing on this file.  The `q25`/normalization "rare gate" lead (§7) is the only remaining
T-side idea and it needs a Z-basis measurement primitive that the instruction set does not
have.  Width work must go back to the generator: either a SAT search for the four flags
(full domain, >= 4 ANDs) or a hand re-synthesis of normalization/divider to 20 scratch wires.
Both are multi-session projects.  The cheap certain move remains the one already delivered on
2026-11-15 (HW-26 `1ba197b0`, one Toffoli below the then-frontier).
