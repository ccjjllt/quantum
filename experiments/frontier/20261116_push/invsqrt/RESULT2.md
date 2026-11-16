# invsqrt RESULT2: v12 generator width census for a NEW 42Q body

Work in `experiments/frontier/20261116_push/invsqrt/`.
Source: `syed3000/vqcc-own-circuit-portfolio` `invsqrt_source_zip`, sha256
`7d9801ae20e942dba2211a656bba6014a0a16d57da534c0b60328d1c5d9d8254` (2,563,106 B, 561 files,
unpacked 18.6 MB).  Uploaded as the private dataset
`jiyujia/qcc-invsqrt-v12-generator-source` (the public portfolio dataset no longer carries the
`*_source_zip` files as of its 2026-11-15 revision) and attached to the kernels below.
**All builds, circuit emissions and any simulation ran on Kaggle CPU kernels** (Python 3.13.18,
numpy 2.1.3, competition `kickmix.so`); local work was static source reading only.

## 0. Verdict

**No sub-46 body was emitted.**  The v12 source is a *width-specialised* body: its emitter is
guarded by `assert builder.max_qubits in (46, 47, 48)` and every one of the 13 shipped patches
was hand-derived to win exactly those two qubits (48 -> 46).  After relaxing that guard the
body really runs, and the census says precisely how far it is from 44 and 42:

| target | first block that overflows | demand | shortfall |
|---|---|---:|---:|
| Q=45 (`PACK=True`, `A6_EARLY=True`) | `product_forward` (the `_compute_carry` allocation) | 45 + 1 = 46 | **1** |
| Q=44 | `load_joint16` (first table loader) | 25 owners + 20 work cap = 45 | **1** |
| Q=42 | `load_joint16` (same site) | 25 + 20 = 45 | 3 |

The Q=46 census (§2) shows which blocks sit at 46, and §3 shows that **the body's liveness
bound is 41** — i.e. Q=42 is *not* an information-theoretic barrier; the 46 peaks are
allocation discipline (dead wires kept allocated), which converts the problem from "find new
arithmetic identities" to "free dead wires, one-time zeroing only".

Cost arithmetic that decides what is worth doing (§5): the v12 body carries ~47 more
Toffoli-equivalents than the shipped `f2cdab0b` (C = 1751.4 raw / 1742.7 after the pipeline vs
1704.69), so **Q=44 and Q=43 would not beat the current best; only Q=42 does** (73,193 modelled,
GM ≈ 28.44 vs 28.09).

## 1. Toolchain gate (unchanged `build.sh`, Kaggle CPU)

```
python 3.13.18 (linux x86_64), numpy 2.1.3
build: s15k7a at Q46, 26 patch args
generator done (17 s)   pipeline done (113 s)   post pass done (150 s)
proof: PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS
wall time 151 s
BUILT invsqrt.kmb 321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177
GATE_PASS True
```

Kernel `jiyujia/qcc-v12-width-census` (v6).  The tree reproduces the published 46Q body
bit-for-bit, so every number below is from the real pinned generator, not a re-implementation.

## 2. Per-block allocation census of the shipped 46Q body

Instrumentation (kernel `jiyujia/qcc-v12-width-census`, and `jiyujia/qcc-v12-block-ledger`):
a census-only patch replaces `km.CircuitBuilder` with a subclass that logs
`(block label, num_allocated, count)` for every `alloc_qubits`.  Block labels come from wrapping
the live component functions (`normalization.forward/inverse`, `root.forward/inverse`,
`tables.load_joint16`, `divider.compute_phase_cleanup` and the twelve `baseline.*` emitters) —
the same objects the shipped patches monkeypatch, so the labels describe the *patched* build.

Peak `allocated + requested` per block, Q=46 body, no `PACK`:

```
46  load_joint16            (both table loaders)
46  coefficient_forward     (both coefficient stages)
46  product_forward
46  divider_cleanup         (phase endpoint + divider inverse cleanup)
46  coefficient_inverse
46  init                    (restore_input_layout, end of build)
45  seed_forward
44  prepare_H3_initial
44  prepare_H4
43  seed_cleanup
39  root.forward / root.inverse
37  normalization.forward
30  normalization.inverse
```

Exactly the five blocks the task names, plus `restore_input_layout` at the very end.

## 3. The body's liveness bound is 41, not 46

Static live-wire analysis of the emitted 46Q text (34,801 ops, 46 qubits; `Z`/`CZ`/`CCZ`/
`Z_POW` count as reads, `X` as write-only, `HMR` as read+reset):

```
peak occupied (live + dirty) = 46      peak live = 41
```

So at the two largest 46-peaks only ~29 and ~15 values are actually *live*; the rest of the
width is dead wires the emitter keeps allocated.  Peak-46 runs by enclosing stage
(345 runs, 14,076 ops total):

| stage | ops at 46 | runs | span | live at run start | HELD (live, never read inside) |
|---|---:|---:|---|---:|---|
| `raw_root_restored_with_paid_R` (joint18 phase flush) | 5,632 | 1 | [26137,31768] | 29 | `q10 q12 q22 q23 q24 q25` |
| `divider_return` (phase endpoint + divider inverse) | 3,309 | 2 | [17978,21291] | 15 | `q10 q11 q12 q13 q22 q23 q24 q25 q36` |
| `body_entry` (first loader + first coefficient) | 2,501 | 4 | [2635,5159] | 26 | `q0..q8 q10 q11 q12 q13 q25` |
| `coefficient_retired_for_divider` (product forward + divider) | 1,293 | 193 | [6898,17074] | 21 | `q5 q6 q8 q10 q12 q14 q22 q23 q24 q25 q30` |
| `seed_ready` | 444 | 83 | [5737,6683] | — | — |
| `A_restored` | 378 | 1 | [25657,26034] | 30 | `q12 q22 q23 q24 q25` |
| `inverse_product_data` | 213 | 19 | [21857,23857] | 23 | 20 wires, incl. `q22..q25` |
| `first_table` / `second_a6_retired` | 117 / 117 | 17 / 17 | — | 26 / 19 | (see log) |
| `coefficient_sources_restored` | 54 | 6 | [24272,24709] | — | — |
| `first_coefficient` / `second_coefficient` | 9 / 9 | 1 / 1 | — | — | — |

The recurring `HELD` set is the **four flags `q22..q25`** plus a few `v` bits (`q10`, `q12`,
`q13`) — the same flags that are the only idle wires in the shipped 44Q file.  Everything else
at the peak is dead-but-allocated, not live.

## 4. Where the body actually stops at each target (measured, guard relaxed)

The guard is `patch_w47_body.py:210` `assert builder.max_qubits in (46, 47, 48)`.  With a
census patch whose `max_qubits` property still reports 46 (so the guard passes) but whose
enforced limit is the target, and `patch_w47_body.PACK` forced on *before* `apply()`:

```
Q=45  ValueError: Attempted to allocate more qubits than the maximum.
        allocated: 45   requested: 1   max: 45
      per-block demand: product_forward 46, load_joint16 45, coefficient_forward 45,
                        init 44, seed_forward 44, prepare_H3/H4 42
      last events: ['product_forward', 44, 1], ['product_forward', 45, 1]

Q=44  ValueError: allocated: 25  requested: 20  max: 44        <- first table loader
      last event: ['load_joint16', 25, 20]

Q=42  ValueError: allocated: 25  requested: 20  max: 42        <- same site
```

So:

* **Q=45 is exactly one wire short, in exactly one block**: `product_forward`, at the
  `engine/fusion/arithmetic.py` `_compute_carry` allocation (same site the 2026-11-15 INV-45
  session found).  With `PACK` on, the loaders (45), both coefficient forwards (45) and
  `seed_forward` (44) already fit; only the segmented carry needs a 46th wire.
* **Q=44's first blocker is the first table loader**, not the product: 25 body owners
  (`v[0..11]` + `h[1..9]` with `h[0]` packed + the 4 flags) + `work_cap 20 = 45`.
* Q=42 hits the same loader first, needing 3 fewer.

## 5. What it costs, and which target is worth building

Modelled from the generator's own exact gate expectation (no sampling):

```
raw 46Q body      toffoli_like 1519.5703  T 4.0  33 rotations  charge 230.848
                  C = 1751.418   cost = 46 * C = 80,565.25
after pipeline    C = 1742.7     cost = 46 * C = 80,162.73  (published 321aff83)
shipped 44Q       C = 1704.69    cost = 75,006.38          (f2cdab0b)
```

| body | C | cost | GM vs 28.09090 |
|---|---:|---:|---:|
| 44Q from v12 (raw) | 1751.42 | 77,062 | **worse** than 75,006 |
| 44Q from v12 (pipeline) | 1742.7 | 76,679 | worse |
| 43Q from v12 (pipeline) | 1742.7 | 74,936 | +0.009 (noise) |
| **42Q from v12 (pipeline)** | 1742.7 | **73,193** | **+0.230** |
| 42Q at f2cdab0b's C | 1704.69 | 71,597 | +0.44 (the user's 28.53 reference) |

So the v12 line must reach **42** to be worth shipping, and its C budget is comfortable:
Q=42 allows C <= 1,786.5 (+4.8%) and the body is at 1,742.7, i.e. **43 Toffoli-equivalents of
headroom** before the trade becomes negative — and Q=40 would allow 1,875.2 (+170).

## 6. The first block that can be lowered, and its exact live set

**First table loader** (`tables.load_joint16`, `variant='first'`,
certificate `agents/loader2/certs/first_cap20_56b8.json`, sha
`f09657772c5fdba988c5dae5e599c003e635cc000d4aa53093362d0846332ec9`, 56 Toffolis,
`work_cap = work_peak = 20`).

Exact live set at the allocation (from the census and the `first_table` cut):

```
owners (25):  v[0..11] = q10..q21          (12 wires, the root)
              h[1..9]  = q0..q8            (9 wires, the residual with h0 packed into the flags)
              flags[0..3] = q22..q25       (4 wires, the exponent code)
work (20):    the certificate's scratch set, allocated in one alloc_qubits(20) call
=> 25 + 20 = 45   (one over the Q=44 cap, three over the Q=42 cap)
```

Why this is the cheapest block to lower: the certificate format already carries a
`reusable_input_slots` field, and **the second loader uses it** (`[0, 1, 2, 4]` — four address
slots whose values are dead during that load) and reaches `work_cap 19` at 70 Toffolis, while
the first loader pins `reusable_input_slots: []` at `work_cap 20` / 56 Toffolis.  The published
search therefore already contains the pattern needed for a cap-19 first loader.
Enabling reuse there (or re-running the loader search at `work_cap 19`) lowers the block by
1-2 wires **without any new arithmetic identity**, at a cost of a few Toffolis — the shipped
history shows cap 22 -> 20 cost 61 -> 56 Toffolis, so cap 19 should be ~+2..4.

The loader search machinery is in the tree (`work/c10/narrow/research/joint_loader/`:
`adaptive_loader_v2.py`, `bank_frontier.py`, `replay_loader_v2.py`, plus frozen candidates
`loader16_first60/61/62`, `loader16_second73/76/79/80` at caps 18-23) and its patches accept an
override via `LD_FIRST_JSON` / `LEAD_SECOND_JSON`, so a new certificate is a drop-in.

The other four 46-peak blocks are *not* certificate-level: `product_forward` needs the segmented
carry's 46th wire (INV-45 session: exhaustive 0-6 AND reconstruction over the 10 idle wires in
that window found none), and `divider_cleanup` / `coefficient_inverse` / both
`coefficient_forward`s each hold a `HELD` set dominated by the four flags.

## 7. The genuine new opening: the peak is allocation discipline

`peak live = 41 < 46 = peak occupied`.  The 46-peaks are 14,076 ops in which the emitter is
holding wires whose values are already dead:

* `raw_root_restored_with_paid_R` (5,632 ops): 29 live, 17 dirty/dead.
* `divider_return` (3,309 ops): 15 live at the run start.
* `body_entry` (2,501 ops): 26 live, the rest dead.

Freeing a dead wire is *strictly easier* than the f2cdab0b problem, because:

1. the wire is **dead** — there is nothing to rebuild, so a one-time **zeroing** identity
   `V = XOR(other wires)` (2-11 CX, free) is enough; no reconstruction at a later point;
2. it does not have to hold at two distant cuts, only at the handoff;
3. the zeroing can be replaced by `del_and`-style measurement whenever `V` is a single AND,
   which is the dominant shape in this architecture.

The catch is the builder's invariant: `builder.free()` may only be called on a wire that is
`|0>` (every allocator user does `init_and` = HMR + CX/CX/CCX, and an HMR of a nonzero basis
value leaves an uncorrectable random phase).  So each reclaimed wire needs that zeroing
identity — but only one, and only for dead values.  The measured candidate pool is small: to
reach 42 from 46 the peak must drop by 4 wires at each of the five 46-peaks, and the dead-wire
count there is 17 / 31 / 20 / 25 / 25 respectively.

## 8. What was and was not executed

* **Executed**: 1 full `build.sh` gate (143 s, exact full-domain proof PASS, sha match);
  4 instrumented emissions (Q=46 census, Q=45/44/42 enforced-width runs); static live/dirty
  profiling of the emitted 46Q text (34,801 ops); per-block peak-run census with live sets.
* **Not executed**: no sub-46 circuit was emitted, therefore **no official verifier run and no
  candidate**.  Nothing submitted.  All cost numbers in §5 are the generator's *modelled*
  expectation (exactly the same formula the official cost model uses), not verifier output.

## 9. Next step (in cost order)

1. **First loader certificate at `work_cap 19` with `reusable_input_slots` enabled** — the only
   block that can be lowered without a new identity; worth 1-2 wires for ~2-4 Toffolis.  Use
  `LD_FIRST_JSON` + relax the `work_cap` assert in `patch_ld_first20_56b8.py`.
2. Then `product_forward`: its 46th wire is the segmented carry (`_compute_carry`).  A
   single-carry in-place adder variant (the architecture the public Q45 post-mortems price at
   +196..+257 Toffolis for the whole circuit) is affordable *inside* the Q=42 budget (+43
   headroom at C=1742.7, +81 at f2cdab0b's C) if applied to the product/divider carries only.
3. Then the dead-wire reclaim (§7) at `divider_return` and `raw_root_restored_with_paid_R`,
   which together are 8,941 of the 14,076 peak ops: each reclaimed dead wire needs a one-time
   XOR zeroing identity, and the full-domain tooling for that already exists
   (`gen_relate.py` / `gen_andsearch.py`, retargeted at this tree's cuts).
4. Q=45 is *one* wire away in *one* block (`product_forward`) — but it is worthless for the
   score (44 * and 43Q both lose to 75,006), so it is only a stepping stone to 42.

## 10. Files

| path | purpose |
|---|---|
| `gen_v12census.py` | kernel generator: gate + per-block allocation census (dataset-attached source) |
| `gen_v12blocks.py` | kernel generator: Q=45/44/42 enforced-width runs + per-block 46-peak live sets |
| `kaggle/v12census/` | pushed kernel `jiyujia/qcc-v12-width-census` |
| `kaggle/v12blocks/` | pushed kernel `jiyujia/qcc-v12-block-ledger` |
| `RESULT2.md` | this file |
| `RESULT.md` | the emitted-file study of `f2cdab0b` (Q=44 hard floor, flags not reconstructible) |

Reproduce:

```bash
cd experiments/frontier/20261116_push/invsqrt
python gen_v12blocks.py && (cd kaggle/v12blocks && kaggle kernels push -p .)
python gen_v12census.py && (cd kaggle/v12census && kaggle kernels push -p .)
```

Source pin: `invsqrt_source_zip` sha256 `7d9801ae20e942dba2211a656bba6014a0a16d57da534c0b60328d1c5d9d8254`,
dataset `jiyujia/qcc-invsqrt-v12-generator-source`; competition `kickmix.so` sha
`c66b3216c4029e0cdfd09054306aa0feadf53ab2f50c1164e37f752874e5005e` and verifier sha
`ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a` (both checked by `build.sh`).
