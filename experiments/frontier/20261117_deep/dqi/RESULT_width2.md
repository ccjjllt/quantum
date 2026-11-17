# DQI width, second pass: full-tape liveness, per-episode spill/refill, and the EEA / 3nb overlap lead

Date 2026-11-17. Line `zhuating`. Subject tape **`575b043f`** (the shipped 890-qubit DQI
leg), sha256 `575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155`,
479,128,738 B, `nops 57,520,821`, static T **367,989**, official mean T **367,116.0572168**,
official clean cost **346,409,762,292.7187**.

Every number below is read from that tape on a **Kaggle CPU kernel**
(`enable_gpu=false`, `enable_tpu=false`, dataset
`grantprater/vqcc-dqi-61c8348d-merged-closings`). **No simulation, no local tape load, no
verifier run, no candidate, no submission, no git push.** Kernels:

| kernel | what it measured | log |
|---|---|---|
| `zhuating/qcc-dqi-gaps-575b` (v1) | gap family + first cover (found the mechanism, crashed in a per-wire helper) | — |
| `zhuating/qcc-dqi-restore-575b` | restorability, take 1 (roles buggy, superseded) | `evidence/k24_restore.txt` |
| `zhuating/qcc-dqi-eea-restore-575b` | pool structure + restorability (roles buggy, superseded) | `evidence/k26_eea.txt` |
| `zhuating/qcc-dqi-fixed-575b` | **corrected roles**: gap chain, restorability, k-fold cover, dead-tail | `evidence/k27_fixed.txt` |
| `zhuating/qcc-dqi-liveness-575b` | **full-tape liveness**, 3 models, occupancy | `evidence/k28_liveness.txt` |

Arithmetic helper: `dqi/budget2.py` (pure arithmetic, reproduces the official cost to
`+3e-8` relative, i.e. the rounding of `R = 1.1912605`).

---

## 0. Verdicts

| question | verdict | decisive measured number |
|---|---|---|
| **(1) Is Q = 890 tight?** Can a pure wire renumbering buy a free qubit? | **NO — closed by measurement** | peak simultaneous liveness = **890** in all three models (per-wire first/last-use; reset-delimited windows; windows + dead-tail trim). At the peak ops the split is **exactly 840 syndrome + 50 pool**, `min = max`, and the dead-tail trim deletes **0** Toffoli. Nothing to renumber, nothing to verify. |
| **(2) Per-episode spill/refill (recompute a wire only where needed)** | **NO-GO, but the reason is not cost** | the exact minimum cover for 1 qubit is **28 refills / 49 T** — **17× under** the 826 T allowance — and **0 of 28 refills can restore the value**. Gaps whose first replay operand still holds its value cover only **51.6 %** of the plateau, so **no restorable cover exists at any k**. |
| **(2b) k-fold: is any k profitable?** | **NO** | k = 1 would be profitable (+0.020 GM) but is not restorable; **k = 3 already costs 51,410 T = −1.14 GM**; gold needs k ≥ 27 at ≤ 30.8 T/qubit and the measured rate is ≈ 17,000 T/qubit. |
| **(3) EEA / Proos–Zalka variable-length overlap (3nb + O(log n))** | **NOT APPLICABLE** | the decoder has no `(u0, u1)` pair at all (non-extended, synchronized EEA over two *position-indexed* arrays of `m = n+3 = 73` words); on the tape the maximum merge saving for every pair of 12-bit words is **0 wires** (all 48 bits + 2 flags are live at every plateau op). |

Q = 890, T = 367,116.0572168, gold 28.71339 needs this leg ≤ 326,448,778,537
(factor 0.942378, −5.762 %).

---

## 1. (1) Full-tape liveness: Q = 890 is exactly optimal for this schedule

The prior width notes measured the **pool's** peak (50). This is the whole-tape test —
the same sweep-line liveness that was run on `invsqrt` and never on DQI. Three models,
all exact over the 57,520,821 ops:

| model | interval per wire | peak live | ops at peak | span |
|---|---|---:|---:|---|
| M0 | `[first touch, last touch]`, one per wire, reset-blind | **890** | 31,172,095 | whole tape |
| M1 | reset-delimited: `[first touch after a reset, last touch before the next reset]` | **890** | **2,760,430** | 21,603,819 – 52,638,306 |
| M2 | M1, with a window ended at its last *consumer* (dead tail dropped) | **890** | 2,685,724 | 21,603,819 – 46,209,336 |

* M1 is the sound model for this tape: the gate set has no `H`, the input is a
  computational-basis state, so every touch except `R`/`HMR` consumes the previous value
  and a reset is the only point at which a wire becomes reusable. M2 is the most
  aggressive model a *pure renumbering* could use.
* **At the 2,760,430 M1 peak ops the split is `pool 50/50, syndrome 840/840,
  total 890/890`** — all 840 syndrome registers are simultaneously live there, as they must
  be if they hold the syndrome vector. Wires 0–803 have **0 resets** over the whole tape
  (one window each, spanning it); wires 804–839 are the three borrowed syndrome registers
  used as scratch (2/4/4 resets) and are live again at the peak. Measured, not assumed.
* **Dead-tail trim: 0 windows are dead and 0 Toffoli are dead** (`k27` F0: pool peak
  stays **50**, dead Toffoli **0**). So the tape carries no deletable tail at all.
* Dead/never-used wires: **none**. The single zero-touch entry in `k28` is the
  `tlo` sentinel at index 890, i.e. one past the last wire (Q = 890 → wires 0–889); it is
  not a wire. All 890 wires are touched.
* Distinct ops at the top of the occupancy profile (M1): `890: 2,760,430`, `889:
  5,785,765`, `888: 626,427`, `887: 356,511`, `886: 153,842`, `885: 29,998`, `884:
  198,037`, `883: 166,587`, `882: 62,388`, `881: 26,449`, `880: 473,737`. So the tape runs
  at full width for **4.80 %** of its ops and at ≥ 889 for **14.86 %**.

**Verdict: the peak is exactly 890.** A renumbering with the identical gate multiset
cannot reduce Q below the max simultaneous liveness, so there is no free qubit, and there
is nothing to build or verify. `840 + 50` is now a *measured* decomposition, not a
hypothesis. The width axis is closed by measurement, not by assumption.

> The only way below 890 is to change the schedule so that fewer values are live
> simultaneously. That is exactly what §2 tests, and §2 is where the axis really dies.

---

## 2. (2) Per-episode spill/refill

### 2.1 The reformulation that makes this measurable

A wire can only be *absent* at an op where it is not touched, so a wire is free only
inside a **gap between two consecutive touches of the same reset-delimited window** (a gap
that straddles a reset is already free in the M1 model). Shedding `k` qubits therefore
requires, at every one of the 2,760,430 plateau ops, at least `k` of the 50 pool wires to
be inside one of their gaps. That is a **k-fold interval cover** of the plateau point set
by the gap family, one refill per interval, and greedy on intervals is exactly optimal for
a point set. This supersedes "one rebuild per window" (`net1`/`netC`) and "one CCX per
plateau episode" (the old 925 T/qubit), both of which charge refills that are not needed.

Measured gap family for the 50 pool wires: **11,873,498** gaps, lengths p50 **5**,
p90 **93**, p99 **958**, max **24,975,433**. Every plateau op lies inside ≥ 1 gap.

### 2.2 The count is trivial, and that is the trap

| k | Q | exact min refills | replay T | T/qubit | break-even to tie 28.150932 | verdict |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 889 | **28** | **49** | **49.0** | 826 | count **PASS ×0.06** — restorability FAIL |
| 2 | 888 | 204 | 36,560 | 18,280 | 828 | **FAIL ×22** |
| 3 | 887 | 382 | 51,410 | 17,137 | 829 | **FAIL ×21** |
| 4 | 886 | 560 | 68,331 | 17,083 | 830 | **FAIL ×21** |
| 5 | 885 | 738 | 99,902 | 19,980 | 832 | **FAIL ×24** |
| 6 | 884 | 916 | 112,454 | 18,742 | 833 | **FAIL ×22** |
| 7 | 883 | 1,094 | 144,779 | 20,683 | 835 | **FAIL ×25** |
| 8 | 882 | 1,272 | 147,506 | 18,438 | 836 | **FAIL ×22** |
| 9 | 881 | 1,450 | 152,711 | 16,968 | 838 | **FAIL ×20** |
| 10 | 880 | 1,628 | 168,953 | 16,895 | 839 | **FAIL ×20** |
| 25 | 865 | 11,178 (count from the earlier gap family; ±0.6 %) | — | — | 861 | **FAIL** |
| 50 | 840 | **impossible**: `k ≤ 47` | — | — | 900 | infeasible |

`k ≤ 47` is exact: at some plateau op 3 pool wires are touched, and a touched wire cannot
be absent, so at most 47 can be dropped. **Q ≥ 843 by any shedding mechanism**, and the
840 contract floor is unreachable this way.

The k = 1 number is **19× cheaper in T** than the previously recorded best
(49 T vs 925 T/qubit). It is
also **one interval**: `q882` is untouched over `[21,382,768, 46,358,201)` — 24.98 M ops,
i.e. **80 %** of the plateau span — so a single refill buys the whole first half of the
peak. The remaining 27 intervals cover the tail with lengths 29,577–198,857.

### 2.3 Why the count is worthless: the refill cannot restore the value

A refill at a gap's right end must rebuild the wire's value, and the value is the
XOR-accumulation of every value-changing write since the window's reset. The replay is
exact only if every replayed write's operands still hold the values they held. Measured
(replay chains: p50 **12,173** value-changing writes, p90 143,208, p99 281,331; the
Toffoli part is only p50 **7**, p90 2,913 — most of a chain is `CX`, which is 0 T):

* **0 of the 12 sampled k = 1 refills are restorable.** `q882`'s 25 M-op held value is
  the XOR of just **2** products, and both operands are stale at the refill point.
  `q889`'s intervals need **3** writes (2 T, 0 CX) and 2 of them are stale.
* A **necessary** condition for any refill (the window's oldest write keeps its operands)
  holds for only **2.22 %** of all gaps, and for **0 of the 1,222 gaps longer than
  100,000 ops**. Those first-operand-kept gaps cover **1,425,494 / 2,760,430 = 51.6 %** of
  the plateau — so **no restorable cover exists, at any k**.
* Exhaustive full-chain test over the filtered family (length ≥ 1000, chain ≤ 2/4/8):
  6,858 genuinely restorable gaps, plateau coverage **1,318,688 / 2,760,430 = 47.8 %**,
  cover greedy returns `status -1` (cannot even reach the first uncovered plateau op).

So the mechanism is not expensive — it is **unavailable**. The tape's pool liveness is
made of *held XOR accumulations*, and their inputs are long dead.

### 2.4 Why the tape is like this, and what that means

`q882` holding a 2-Toffoli value for 25 M ops is not an accident: the public lineage this
tape descends from (README of the dataset, §"What this file changes") explicitly holds
products on idle wires — *"49 measured uncomputations … `CCX(a,b,w) CX(w,t) … CX(w,t') HMR(w)`"*
and *"four more products held on idle wires, each proven before it was taken"*. **The 50
pool wires are a product cache, and 367,989 T is what the cache buys.** Width and T are in
direct tension: every cached product is a live wire, and a refill would have to re-derive
the product from inputs that no longer exist.

That is why the counting cost collapses at k = 2 (the long-held intervals are all consumed
by the first layer, and the marginal per layer becomes 178 short intervals with ~207 T of
replay each) and why the answer to "is any k profitable" is a clean no.

### 2.5 Money

| k | Q | T increase (measured) | cost | GM | Δ GM |
|---:|---:|---:|---:|---:|---:|
| 0 | 890 | — | 346,409,762,293 | **28.15093** | — |
| 1 | 889 | 49 (not realisable) | 345,677,893,360 | 28.17079 | +0.0199 |
| 3 | 887 | 51,410 | 392,262,221,372 | 27.00831 | **−1.1426** |
| 5 | 885 | 99,902 | 435,739,525,222 | 26.07837 | −2.0726 |
| 10 | 880 | 168,953 | 494,530,208,443 | 25.00107 | −3.1499 |

Budget per qubit: **826 T** (k = 1) … **900 T** (k = 50) to tie the current point, and
**gold's budget is negative for every k ≤ 26** — gold requires **k ≥ 27 (Q ≤ 863)** at
**≤ 30.8 T/qubit** (k = 47 needs ≤ 393.6, k = 50 ≤ 425 but k ≤ 47 is infeasible).

**Verdict: no k is profitable.** k = 1 is the only k whose *count* fits (49 T against 826)
and it would be worth +0.020 GM, but it is unimplementable; from k = 2 on the count alone
costs ≥ 16,895 T/qubit, i.e. 20× the break-even and 550× gold's k = 27 budget.

---

## 3. (3) The EEA / Proos–Zalka overlap lead: not applicable

The lead was: our pool is `4nb = 48` bits + 2 flags, i.e. the EEA working set
`(r0, r1, u0, u1)`, so a variable-length overlap (Proos–Zalka / Kaye–Zalka, `3nb + O(log n)`)
could merge two words for ~0 T because `SWAP`/`CX` are not T gates. **The premise fails on
both the algorithm and the tape.** Four independent checks:

**(a) The decoder has no `(u0, u1)` pair.** `data/competition/verifiers/dqi/dqi_reference_circuit.py`
(the compileable form of arXiv:2510.10967, class `ProosAndZalkaDecoder`) is a *non-extended*,
**synchronized** EEA over **two position-indexed arrays**:

```python
m = n + 3                                                    # 73
reg_a = [alloc_qubits(degree) if i < 3 else syndromes[i-3] for i in range(m)]
reg_b = [alloc_qubits(degree) for _ in range(m)]
...
self._multiply_and_add_or_sub(...)   # reg_b[i] ^= q_i * reg_a[i]   (division folded in)
self._shift_b_array_right(...)       # cswap(do_shift, reg_b[i-1], reg_b[i])   (positional)
self._swap_a_and_b(...)              # swap the two arrays
```

There is no coefficient array anywhere; the error values come from `_chien_search_and_forney_mbuc`.
The published `2nb = 1,680` is **two arrays of n words**, not 4 role words. The `4nb` /
`(r0,r1,u0,u1)` shape belongs to a single modular inverse, which is not this circuit.

**(b) On the tape the pool is not four equal words.** Reset counts per wire (measured):
`840-851` and `852-863` have **14–16 resets each** (held for millions of ops), while
`864-875`, `876-887` and the two flags `888/889` have **387–9,760 resets each** (recycled
scratch, ~5,000 windows per wire). A four-word EEA state would share one update cadence.

**(c) The words are product accumulators.** Group-resolved operand census (pool ops):
`CCX` `(syn,syn,W840-851) 57,774` — both controls in the syndrome array, target in
`840-851`; `CX` `(syn,syn,W840-851) 2,135,290`; and `840-851` is itself a *control* on
syndrome targets 24,360 times (`CCX (W840-851,syn,syn)`). That is a bit-sliced
multiply-accumulate against the syndrome array, not an `(r,u)` register pair.

**(d) SWAPs do not carry the positional-shift signature.** 208,531 SWAPs touch the pool:
**89,700 pool↔syndrome**, 54,282 two-word other-offset, **48,003 same-word other-offset**,
11,472 same-word *adjacent* bit (the bit-shift signature), and only **5,074 two-word
same-bit-offset** — the `cswap(reg_b[i-1], reg_b[i])` positional signature — i.e. **2.4 %**.
The dominant structure is cross-wire renaming, not a lane rotation.

**(e) The decisive width test: no complementarity to exploit.** For the overlap to be
free, two words must satisfy `live(A) + live(B) ≤ 12` at *every* op. Measured (window
model): every 12-bit group has live peak **12**, and for **every** pair of 12-bit words the
max simultaneous live is **24** → **merging saves 0 wires**. The most aggressive liveness
model (M2, dead tail dropped) also saves 0. (An earlier run reported 1 wire for one pair; that model
trimmed *reads* as if they were writes — the role bug of §4 — and it is withdrawn: the
corrected dead-tail trim deletes 0 gates and leaves the pool peak at 50.)

**Verdict: not EEA-shaped, so there is no overlap rewrite, and the 3nb figure does not
apply to this tape.** The barrel shift genuinely costs 0 T — the lead is right about that
— but it is not T that blocks it: at every plateau op all 48 bits + 2 flags are live, so an
overlap must first make ~12 bits *dead*, which is the recompute problem of §2, and §2 is
non-restorable. The tape also already beats the published space optimum by 1.9×
(890 vs 2nb = 1,680), because it is an in-place formulation that additionally borrows three
syndrome registers as scratch (`S67/S68/S69`, 36 bits) — effective scratch 86 wires for a
Q charge of 50.

---

## 4. Corrections to the record (so they are not repeated)

1. **Role bug in v1–v3 kernels.** The write/target mask was taken from the *opcode* alone,
   so a wire used as a `CCX`/`CX` **control** was counted as written. It inflated the
   "value-changing touches" from 31,369,849 (correct) to 61,444,929 and produced two
   artefacts that are herewith **withdrawn**:
   * "dead-tail trim → peak 49, 37,476 dead Toffoli" (v2 `E0`, v3 `F0`): the corrected run
     gives **peak 50, 0 dead Toffoli**;
   * "one pair of 12-bit words can be merged for 1 wire" (v3 `D2`): corrected, **0**.
   The corrected kernels are `qcc-dqi-fixed-575b` and `qcc-dqi-liveness-575b`; everything
   quoted above is from them.
2. **Window convention.** A window ends at the *last touch before* the next reset, so the
   stretch between a wire's last touch and its own reset is dead. This gives 2,760,430
   plateau ops / 965 episodes; the earlier note's 2,760,326 / 961 differs only by the
   window-boundary convention (104 ops), not in substance.
3. **The 925 T/qubit figure is superseded.** It charged one CCX per plateau *episode*.
   The exact interval cover needs **28** refills for k = 1 and 49 T of replay, so the
   counting cost was overstated by **19× in T** (33× in refill count). The real blocker is restorability, which the prior
   notes had only as a suspicion ("replay is not finite") — it is now a measured bound:
   restorable gaps cover at most 51.6 % of the plateau.

## 5. Verification scope, stated honestly

* **No candidate circuit was built, so no verifier ran and nothing was submitted.** This is
  correct for this study: §1 shows there is nothing to renumber (peak = 890), and §2–3
  show the mechanisms do not exist. There is no artifact to verify.
* All tape numbers are exact integer counts from `575b043f` on Kaggle CPU
  (`qcc-dqi-fixed-575b`, `qcc-dqi-liveness-575b`); the only official-verifier inputs used
  are the already-on-record Q 890 / mean T 367,116.0572168 / cost 346,409,762,292.7187.
* The GM column is arithmetic only (`scripts/gm.py` arithmetic: the cube root of the leg
  ratios) with the other two legs held at their shipped values.
* Not measured here: **value-level** redundancy (whether a held value on one wire equals a
  live value on another, which would make a refill a 0-T `CX`). That needs a 256-lane
  value scan and is the only remaining object that could produce a restorable refill. Note
  that §2 makes its target precise: it would have to cover the **48.4 %** of plateau ops
  that no first-operand-kept gap reaches.

## 6. What would have to be true for DQI width to pay

1. **Gold needs k ≥ 27** (Q ≤ 863) at **≤ 30.8 T/qubit**, or k = 47 (Q = 843, the
   shedding maximum) at ≤ 393.6 T/qubit. Any mechanism must therefore shed **at least 27
   of the 50 pool wires**, not one.
2. **The measured rate is 16,895–20,683 T/qubit from k = 2 on**, and the count is *not* the
   obstacle for k = 1 (49 T) — restorability is. So a new mechanism must supply a
   **value-restoration primitive**: a way to re-derive a held product at a later time from
   *live* data. On this tape that means finding products that are linear functions of
   values still live at the refill point (a 0-T `CX` chain), which is the value-level
   redundancy scan.
3. **Or a new schedule** in which the pool is not a product cache: that trades T for Q
   directly, and the exchange rate is measured above — it costs ≈ 17,000 T per qubit
   against a 826–900 T budget, i.e. a 20× miss at every k.
