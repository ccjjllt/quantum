# DQI 66b4 norm-preserving tower census — 2026-11-16 (part 8)

Mandate: unpack/document the `balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings`
gadget + tools + `results/RESULT_dqi_66b4f18b.json`, census the NEW tape
`66b4f18b85273bdc0b325500c43a810aba2772275b977f371731cfc400a315c2`
(890Q, static 368750, mean 367877.549, score 347128304010.81, k18 PASS 0/0) for
remaining nested-norm closing sites of the same class, and if any convertible
site exists build the converted candidate and run the UNCHANGED official DQI
verifier full 102400 shots default + 2 salts. Local work limited to sha256/GM
arithmetic; no local simulation, no local verifier runs. Nothing submitted.

## 0. Outcome

**No convertible site remains. No candidate built, no verifier run from this part.**

* Gadget unpacked and documented (§1): 24-bit nested-norm closing replaced by
  norm-preserving tower closing, **20 static T saved per site**
  (suffix 360→340; full micro 459→439 incl 99T prefix), Q unchanged,
  `patch_q ⊆ orig_q`, no fresh qubits, no fresh classical bits beyond
  pre∪orig. Semantics via `N^-1 = conj(N)·C^-1`, `C = N_6(N)`; every HMR mask
  repaid once; verified 0/0 by k18 + dataset census.
* Census of the NEW tape (§2, k19 exact operand-verified search over the full
  57,666,786-op tape): **41/41 PATCH sites verified, 0/0 ORIG sites** —
  opcode-level `bytes.find` 41 vs 0, operand-mapping verification 41/41 vs 0/0.
  All 41 unguarded `gf24_nested_norm.emit_closing` sites claimed in
  `SOURCE_CREDITS.md` are present as PATCH; **zero sites of the same class
  remain unconverted**.
* Per-site static T for a hypothetical further conversion: 20 T; live-set/Q
  impact 0 (§2). Remaining opportunity `0×20 = 0` static T.
* Blocker (§3): nothing to convert. The patch itself refuses `record.guarded`
  (`return _orig…`), and no `G0` pattern remains on tape, so there is no
  guarded-or-unguarded instance of this class left. Other closing classes
  (synthesis pair-closings, narrow 12/6-bit closes) are different gadgets and
  need a separate re-derivation, not this transplant.

## 1. Gadget doc

Source: dataset `balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings`
(55.4 MB, updated 15:16 UTC). Members relevant here:

| file | bytes | role |
|---|---|---|
| `gadget/m_pre.kmx` | 67,624 | `emit_prefix` only (24-bit input-scale products) |
| `gadget/m_orig.kmx` | 708,254 | prefix + original `emit_closing` |
| `gadget/m_patch.kmx` | 354,626 | prefix + norm-preserving tower closing |
| `tools/closing_norm_preserving_body.py` | 4,816 (101 lines) | patch body, exec'd by `make_micro.py` |
| `tools/make_micro.py` | 1,963 | builds the three micros from Syed v12 src |
| `tools/transplant.py` | 4,322 | kmb→kmx opcode-sequence transplant on same wires |
| `results/RESULT_dqi_66b4f18b.json` | 1,032 | claim: PASS 890Q 367877.55T score 347128304010.81 |
| `SOURCE_CREDITS.md` | 2,048 | "v13 decoder (46446af1) with all 41 unguarded GF(2^24) nested-norm closing gadgets replaced" |

What it replaces: `gf24_nested_norm.emit_closing(builder, source, value, record)`
in Syed Asad Ali's v12/v13 builder (`source`/`value` 24 qubits, `record` with
`builder_id`, `closed`, `guarded`, `delta`, `tensor`). Guarded records fall back
to orig (`if record.guarded: return _orig_a24_emit_closing…`); only unguarded
sites are patched.

Micro measurements (k19, kickmix `operation_statistics` + numeric kmb header):

| micro | Q | kmx ops | static T | CCX | CCZ | CX | CZ | SWAP | HMR | BIT_INVERT | PUSH/POP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pre | 72 | 6,295 | 99 | 99 | 0 | 6,098 | 0 | 24 | 24 | 0 | 0/0 |
| orig full | 72 | 48,585 | 459 | 458 | 1 | 30,550 | 2,333 | 441 | 135 | 13,134 | 421/421 |
| patch full | 72 | 30,307 | 439 | 439 | 0 | 25,900 | 2,172 | 273 | 133 | 932 | 61/61 |
| **suffix G0 (orig−pre)** | — | 42,290 | **360** | 359 | 1 | — | — | — | — | — | — |
| **suffix G1 (patch−pre)** | — | 24,012 | **340** | 340 | 0 | — | — | — | — | — | — |
| **save/site** | 0 | −18,278 ops | **20** | 19 | 1 | −4,650 | −161 | −168 | −2 | −12,202 | −360/−360 |

Numeric prefix check: `orig[:6245]==pre` True, `patch[:6245]==pre` True.
`patch_q (72) ⊆ orig_q (72)` True, extra `[]`; `patch_b 164` vs `orig_b 354`,
new bits outside pre∪orig **0**. So same-wire transplant needs no new qubits
and no fresh classical bits.

Patch body (10 steps, T annotations from source comments; linear basis maps 0T):

1. 24-bit adjoint product `value ← conj(source)·value = N·v_orig` (99T, 24 helpers).
2. 12-bit norm `N = N_12(source)` (42T, 12 helpers).
3. Conjugate norm to `N_bar` in tower basis (0T), multiply value halves by
   `N_bar` (84T, 24 helpers). Now `value = C·v_orig`, `C = N_6(N)` in GF(2⁶).
4. Un-conjugate norm back (0T).
5. 6-bit child `C = N_6(N)` (15T) + invert to `C⁻¹` (21T, peak 24 helpers).
6. Multiply all four 6-bit quarters of value by `C⁻¹` (4×15=60T, peak 24).
7. Measure/free child in tower basis (0T).
8. Recompute `C` (15T), pay `child_mask` via `Narrow.phase_inverse_six`
   (4T static), pay four quarter masks via `phase_product` at 0T.
9. Switch norm back to polynomial basis (0T), pay scaled masks at 0T,
   `erase_norm` vs source (0T).
10. Pay `old_target_mask` (`cz`) + `old_product_mask` (`phase_product`) at 0T.

Why semantics/phase-repayment preserved: the tower identity
`N⁻¹ = conj(N)·C⁻¹` with `C = N_6(N)` is exact in the `quadratic_basis`
tower; `conj` is `cx(h,l)` sandwich + basis maps (all 0T linear). Every HMR
mask created (`old_product` 24b, two `scaled` 12b, four quarter 6b, `child` 6b)
is consumed exactly once by its conjugate repayment (`phase_product` /
`phase_inverse_six` / `erase_norm` / `cz`+`free`), same repayment shape as orig
but through the 12→6 tower instead of nested 24-bit norms. Peak helpers stay
12+12/12+6+6 = 24, inside the orig 24-word budget, hence Q-neutral. Empirics:
k18 UNCHANGED verifier default salt PASS 0/0 exact claimed score; dataset
census 409,600 shots `seed_20261114` PASS 0/0 (see `RESULT_dqi_66b4f18b.json`).

## 2. Census of the NEW tape (k19, exact)

Target header (direct `.kmb` numpy unpack, no kmx round-trip):
`Q 890, n 57,666,786, staticT 368,750, nbits 59,814`.
Opcodes: CCX 362,765 + CCZ 5,985 (=368,750) + CX 30,135,508 + CZ 534k-class +
SWAP 375,203 + HMR 71,817 + R 48,043 + BIT ops 20.9M + PUSH/POP 5.12M each.

Method: micro circuits round-tripped to kmb, unpacked to numeric `ops`
(`ops&127` + cond `ops&128`), `G0 = orig[len(pre):]` (42,290 ops),
`G1 = patch[len(pre):]` (24,012 ops). `bytes.find` non-overlapping scan
(transplant semantics) on the 57.6 MB opcode stream, then per-hit
operand-mapping verification (qubit maps + bit/cond maps, positional,
bijective via forward/reverse dicts) using `A/B/C/BIT/COND` arrays (k15 layout).

| pattern | opcode-level hits | operand-verified | first op indices |
|---|---:|---:|---|
| G0 orig suffix (42,290 ops, 360T) | **0** | **0/0** | — |
| G1 patch suffix (24,012 ops, 340T) | **41** | **41/41** | 35763525, 35796971, 35830399, 35863599, 35896799 |

Site table of **remaining** convertible sites: empty (0 rows).

| remaining site | per-site static T | live-set/Q to convert | verdict |
|---|---:|---|---|
| (none — 0 G0 matches) | 20 (would-be) | 0 qubits (`patch_q⊆orig_q`, micro Q 72=72); 0 fresh bits | nothing to convert |

 Converted-site summary (for the record): 41 G1 sites, each −20 static T,
 total −820 static T, Q +0, all verified. Positions cluster ops
 ~35.76M→~37M+ (converter/synthesis closing band), spacing ~33k ops, consistent
 with per-node pair-closes.

T/Q/cost before→after for this gadget (static exact; mean/cost verified after):

|  | Q | static T | mean T | cost |
|---|---:|---:|---:|---:|
| v13 parent `46446af1` (inferred: new + 41×20) | 890 | 369,570 | — (not re-verified here) | — |
| **66b4 NEW (verified)** | **890** | **368,750** | **367,877.549** | **347,128,304,010.81** |
| delta | 0 | **−820 (−0.222%)** | — | −0.071% vs `ccc2ab84` 347,375,470,571.73 |

`old_static = 368750+820 = 369570` is arithmetic (allowed locally), not a
re-verification; the parent bytes were not re-built here. The after row is
k18-measured (UNCHANGED verifier, default salt, 102400 shots, 0/0).

## 3. Blocker (no candidate → no verifier runs from this part)

No remaining `G0` instance exists, so `transplant.py [max_sites]` has zero
targets and no converted candidate was built. Per mandate the 3-salt full
verifier run only triggers on a built candidate, so none was run here; the
evidence for the after-state remains k18 (default salt PASS 0/0 exact score)
plus the dataset's 409,600-shot census PASS 0/0.

Why no further conversion of this class is possible:

* All 41 unguarded sites are already PATCH (41/41 verified). The patch source
  explicitly refuses guarded sites, and zero ORIG-pattern spans remain, so
  there is neither an unguarded nor a guarded instance of
  `gf24_nested_norm.emit_closing` left in this tape.
* Neighbor closing families (synthesis `Σ(r+2)·42` prefixes / `Σr·42` returns /
  34×363 pair-closes per RESULT5 §2; narrow 12/6-bit `phase_quotients`/
  `erase_norm` sites) use different tensors/bases and do not match `G0`; they
  need a separate gadget + re-derivation, not this transplant.
* Closed-on-old-tape levers stay closed and were not repeated: peephole
  0 cancel/0 dead (RESULT7 §0), decision-machine <1T (RESULT5 §3), retain
  +2.37% (RESULT5 §4), out-of-place patch-impossible (RESULT6 §2), v13
  backport delta 0 (RESULT6 §1–3), ladder irreducible (RESULT6 §4).

## 4. Receipts

| kernel | ref | purpose | outcome |
|---|---|---|---|
| k18 | `zhuating/qcc-dqi-verifynew-66b4-00ac` | UNCHANGED DQI verifier, default salt, 102400 shots on 66b4 + 00ac | 66b4 PASS 0/0 367877.549 exact score; sha MATCH |
| k19 | `zhuating/qcc-dqi-66b4-gadgetcensus` | micro doc + exact G0/G1 opcode+operand census on 66b4 | micros 459→439 (−20/site); G0 0/0, G1 41/41; report.txt |
| dataset claim | `balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings` `results/RESULT_dqi_66b4f18b.json` | 41 closings, 890Q/367877.55T, GM 28.10154 | corroborated by k18 + k19 (counts + score to the digit) |

All runs Kaggle CPU (`enable_gpu:false`, no internet, competition data
attached); local work limited to hash/GM arithmetic and doc writes. No package
built, no submission made.

## 5. Verification scope, stated honestly

* Scores/costs quoted are the UNCHANGED official DQI verifier on Kaggle CPU.
  k19 built no candidate so it ran no verifier; the PASS numbers are k18 +
  dataset JSON, both default-salt full-shot PASS 0/0.
* Static counts (micro T 459/439/99, target 368750, Q 890, opcode census,
  41 vs 0 site counts) are measured by exact numpy unpack + kickmix
  `operation_statistics` + byte-exact prefix checks, not modelled. Operand
  verification is positional and bijective (forward+reverse maps for qubits
  and bits/conds), strictly stronger than opcode-only search.
* `old_static 369570` is `new_static + 41×20` arithmetic from the measured
  per-site saving; the v13 parent bytes were not rebuilt or re-verified here.
* Guarded-site reasoning rests on the patch source's explicit
  `if record.guarded: return orig` plus the measured absence of any G0 span;
  other closing classes were not pattern-searched here beyond the G0/G1 test.
* No leaderboard number was produced by this work.
