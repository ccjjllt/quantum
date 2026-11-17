# dfthcsos angle-circuit generator — design note

FeMoCo DFTHC block encoding (Benchmark III, N=76, eta=113). Workspace
`~/workspace/quantum-circuit-compilation/`. Authoritative spec:
`notes/dqi-dfthcsos-verifier-spec.md`. Hard lessons applied from
`notes/verifier-fix.md` (invsqrt).

## Baseline (official, full defaults — measured in the notebook)

| quantity | value |
|---|---|
| score S | 3,355,599,588.32 |
| lambda_eff | 49.301369250574396 |
| toffoli_count | 93,237 |
| num_qubits Q_total | 730 |
| brot / J / circuits | 12 / 8 / 10 |
| Lambda | 308.4559397330948 |
| E_gap | 3.965477244291833 Ha |
| error_1 / error_2 | 0.003185 / 0.018640 (thresholds 0.020 each) |
| LAMBDA_FLOOR / E_GAP_FLOOR | 49.0 / 3.914898 Ha |
| QUBIT_CAP / KEEP_BITS | 128 per angle circuit / 10 |
| reference angle circuit | 119 qubits, 3,974 Toffoli-like, reaction_depth 11 |
| state-prep anchor (derived) | outer+inner = 10,307 Toffolis; non-angles Q = 634 |
| Givens anchor (exact formula) | 2*(N-1)*(2*brot-1) = 3,450 at brot=12 |

Score: S = lambda_eff * T_total * Q_total.
T_total = angles_toffoli (fwd+rev, simulator mean per shot) + outer_state_prep
+ inner_state_prep + 2*(N-1)*(2*brot-1).
Q_total = outer_persistent + inner_persistent + J*brot
+ max(outer_temp, inner_temp, ang_temp).

## Architecture: delta-unary loader

Each angle_k circuit is a **delta loader**: for a 12-bit `selection`
address a (a DFTHC vector index, 0..num_vectors-1) it XORs a classical
table of deltas into the public word registers word_0..word_{J-1}:

    word_j ^= delta_k[a][j],   delta_k = batch_k XOR batch_{k-1}

where batch_k is columns [k*J, (k+1)*J) of the angle_words matrix
(num_vectors x (N-1)), batch_{-1} is all zeros, and columns past N-1 are
treated as zero (so the last circuit clears the padding words to zero,
as the verifier requires).

Why deltas, not absolute loads: the official verifier runs each circuit
forward (reads the words for batch k) and then runs the reverse pass,
which must restore the PREVIOUS circuit's words (k=0 must clear to
zero). A delta loader is an involution as a classical function
(word ^= delta twice = identity), so its reverse restores the previous
words exactly. A plain absolute loader (init_lookup from zero) would
clear to zero on the reverse pass and FAIL the reverse check for k>0.

Lookup structure: one unary-iteration pass over the addresses
(`km.CircuitBuilder.unary_iteration`), one CX per 1-bit of the delta
table into the word registers. Toffoli cost is N-2 per circuit
(N = num_vectors), INDEPENDENT of J and brot — the address decode
dominates, the output fanout is Clifford CX.

Registers: selection (sel_bits, km.q), word_0..word_{J-1} (brot, km.q
each). NO z_pow anywhere (the verifier rejects any Z_POW line). NO
measurement-based relation-clearing (invsqrt lesson: it injects
outcome-dependent pi phases).

Qubit-cap arithmetic (the binding constraint on J):

    qubits/circuit = sel_bits + J*brot + sel_bits (unary temp)

so at brot=12, sel_bits=12: J <= 8 (baseline). J=9 needs 132 qubits and
is rejected by the generator. Larger J (fewer circuits, lower total
angles Toffoli) requires smaller brot, which raises angle-quantization
error — a factorization-quality question, not a circuit question.

## Measured results — baseline config (J=8, brot=12)

Family `data/dfthcsos_synth/` (synthetic words, seed 7, 3976x75 — clearly
labeled synthetic; NOT a submission candidate).

| quantity | measured |
|---|---|
| circuits | 10 (angle_k_0..9.kmb, real binary .kmb) |
| qubits / circuit | 120 (12 sel + 96 words + 12 temp) |
| Toffoli-like / circuit | 3,978 (reference 3,974; +4, 0.1% — iteration-path detail) |
| instructions / circuit | ~226,300 |
| reaction_depth | 12 (reference 11) |
| k0 sha256 | f58683c128e35c2db55769849263ebbcbb05a7b12bb824788c2005caba5c8662 |
| local verifier | **PASS** — all 3,976 addresses, 2,544,640 shots, 0 failures |
| fwd Toffoli / circuit | 1,012,257,792 (= 3,978 x 254,464 shots, exact) |
| rev Toffoli / circuit | 1,012,257,792 (identical — involution confirmed) |
| angles mean/shot (fwd+rev) | 7,956.0 |
| full-verification runtime | 2m03s (optimized; was 4m46s before vectorized I/O) |
| projected score at baseline lambda_eff | 3,358,478,788 (Q=730) = **0.99914x**; 3,363,079,406 (Q=731) = 0.99778x |

The angle circuits are at parity with the reference (within 0.22%).
The 4-Toffoli/circuit gap and the 1-qubit temp gap (120 vs 119) are the
only circuit-side differences, and both are negligible. The real lever
is the factorization (lambda_eff), not the circuits.

### The 1-qubit temp gap

kickmix's `unary_iteration` allocates sel_bits (12) temp qubits for the
AND chain; the reference builder uses 11. Q_total impact: 0 if
state-prep temp already >= 12 (likely — SpinFreeData_V1 is the bigger
circuit), at most +1 qubit (0.14% on Q) if ang_temp binds. Hand-rolling
the decode to save 1 qubit was judged not worth the correctness risk.
Recorded here as a possible micro-optimization, not a blocker.

## Config table (all measured by running the generator + local verifier)

Projections hold lambda_eff at the baseline value (49.301369250574396)
and state-prep/Givens at the baseline anchors, so they isolate the
CIRCUIT-side effect only. They are upper bounds on the gain from a
config change, valid only if lambda_eff holds at that brot — which is a
factorization question needing the real data (see below).

| config | circuits | qubits | Toffoli/cct | angles fwd+rev | T_total | Q_total | projected S | ratio vs baseline |
|---|---|---|---|---|---|---|---|---|
| ref baseline J8/b12 | 10 | 119 | 3,974 | 79,480 | 93,237 | 730 | 3,355,599,588 | 1.0000x |
| **J8/b12 (mine)** | 10 | 120 | 3,978 | 79,560 | 93,317 | 730 | 3,358,478,788 | 0.99914x |
| J9/b10 | 9 | 114 | 3,978 | 71,604 | 85,361 | 724 | 3,046,890,836 | 1.1013x |
| J10/b8 | 8 | 104 | 3,978 | 63,648 | 77,405 | 714 | 2,724,745,330 | 1.2315x |
| J8/b10 | 10 | 104 | 3,978 | 79,560 | 93,317 | 714 | 3,284,867,562 | 1.0215x |
| J12/b8 | 7 | 120 | 3,978 | 55,692 | 69,449 | 730 | 2,499,469,730 | 1.3425x |
| J7/b14 | 11 | 122 | 3,978 | 87,516 | 101,273 | 732 | 3,654,800,964 | 0.9181x |

Verification status (local replica, 16 addresses each unless noted):
J8/b12 FULL 3,976-address PASS (2,544,640 shots); J9/b10 PASS; J10/b8
PASS; J8/b10 PASS; J12/b8 PASS; J7/b14 FULL 3,976-address PASS
(2,799,104 shots, 11 circuits, 2m23s).
Rejected by the generator (qubit cap): J9/b12 (132), J8/b14 (136),
J8/b16 (152).

Reading the table:
- Toffoli/circuit is 3,978 for EVERY config — it depends only on N
  (num_vectors), not on J or brot. The only way to cut angles Toffoli
  is fewer circuits (larger J), and J is capped by qubits.
- J8/b10 is a FREE Q win at fixed J (104 vs 120 qubits, same Toffoli)
  IF lambda_eff does not degrade at brot=10. The quantization cost at
  brot=10 is error_2 ~1.06e-03 (see metrics below) — small, but the
  factorization's lambda_eff at brot=10 is unknown without the real data.
- J12/b8 has the best circuit-side projection (1.34x) but the coarsest
  quantization (brot=8, error_2 ~3.5e-03) and the fewest circuits —
  the factorization must still hit its lambda_eff at brot=8.
- J7/b14 is DOMINATED: more circuits (11) hurts T, and brot=14 costs Q,
  for a quantization gain that is irrelevant (the baseline's error_2 is
  factorization-dominated, not quantization-dominated). Do not pursue.

## Metrics evaluator (Part C) — quantization vs brot

Synthetic small case (N=6, R=3, B=2, C=2; ERI generated FROM the exact
factorization, so only quantization error shows). Errors shrink ~2x per
added brot bit:

| brot | error_1 | error_2 | Lambda | E_gap | lambda_eff |
|---|---|---|---|---|---|
| 4 | 3.95e-02 | 6.16e-02 | — | — | — |
| 6 | 9.14e-03 | 1.46e-02 | — | — | — |
| 8 | 2.385e-03 | 3.547e-03 | 10.2403 | 2.9994 | 7.2411 |
| 10 | 8.08e-04 | 1.06e-03 | — | — | — |
| 12 | 1.925e-04 | 2.643e-04 | 10.2409 | 3.0000 | 7.2419 |
| 14 | 4.29e-05 | 6.27e-05 | — | — | — |
| 20 | 3.20e-07 | 4.68e-07 | — | — | — |

Implication: at brot=12 quantization contributes only ~2.6e-04 to
error_2 (1.3% of the 0.020 budget), so the baseline's 0.0186 is
dominated by factorization (rank) error, not quantization. Dropping to
brot=10 costs ~1.06e-03 (5% of budget); brot=8 costs ~3.5e-03 (18% of
budget) — still under the threshold, but no longer negligible, and the
factorization optimizer must still reach its lambda_eff at that brot.
The metrics evaluator's assumptions C1–C8 (angle convention
theta = word*pi/2^(brot-1), X^(rho,c) form, lambda_h1 = sum|lambda_j|,
etc.) are documented in `code/verify_dfthcsos_local.py` and need
official-source confirmation in the notebook before absolute numbers
are trusted.

## Cost-model probes (measured in the local venv)

- `init_lookup`: N-2 Toffolis, independent of output width (2->2,
  16->14, 64->62, 256->254; 12-bit address random 96-bit table: 4,094
  Toffolis, 242,072 instructions, 120 qubits). Instruction count
  depends on table 1-bit density, Toffoli does not.
- Gray-code unary-iteration ordering: NO help — cost is N-2 regardless
  of order (addr_bits 4/6/8, natural vs Gray, identical).
- The angle QROM is at its floor (N-2 Toffolis/circuit) given the
  qubit cap. Real gains are factorization-side (R/B/C, brot, J joint
  optimization), which needs the real data in the notebook.

## Killed ideas

| idea | why it died |
|---|---|
| SelectSwapQROM | Needs B*b ancillas (B=8, b=96 -> 768 qubits) vs the 128-qubit cap (~9 spare). Dead on arrival. |
| QROAM | Needs (x-1)*b clean ancillas — same blowup. Dead. |
| Gray-code iteration ordering | Measured: identical Toffoli (N-2) for natural vs Gray at addr_bits 4/6/8. No saving. |
| Sparse lookup | Toffoli is N-2 regardless of table density; only instruction count varies. No saving. |
| init-lookup strategy | Cannot share one address decode across J words in kickmix (one init_lookup per word would cost J*(2^sel_bits-2) Toffolis). Generator refuses it. |
| Relation-clearing / measurement-based uncompute | Invsqrt lesson: injects outcome-dependent pi phases. Not used; the delta loader is a pure unitary involution. |
| Hand-rolled unary iteration (save 1 temp qubit) | <=0.14% on Q, and 0 if state-prep temp binds. Not worth the correctness risk. |
| J7/b14 (finer brot, more circuits) | Dominated: 0.9181x at fixed lambda_eff. More circuits hurt T, brot=14 costs Q, quantization gain is irrelevant. |
| J9/b12, J8/b14, J8/b16 | Rejected by the qubit cap (132/136/152 > 128). |

## Local verifier replica — what it checks, and its fidelity

`code/verify_dfthcsos_local.py` (subcommands: verify / score / metrics).

Circuit side (Part A), in the official order:
1. Register contract: exactly one `selection` (bit_length(num_vectors-1)
   qubits, 12 for 3976) + word_0..word_{J-1} (numbered 0..J-1, no gaps,
   all same width brot, all km.q, disjoint, identical across circuits);
   any Z_POW line rejected (grep over the kmx serialization).
2. Word recovery over all addresses, 64 shots each, addresses tiled
   64x into selection little-endian; all 64 shots per address must
   agree; padding words beyond N-1 must be zero (zero-padded columns).
3. Reverse pass: circuit k's forward pass starts with word registers
   pre-loaded with batch k-1's words (delta is XORed onto them); the
   reverse pass (second run on the same simulator — an exact proxy for
   the official reverse because the delta loader is a classical
   reversible involution) must restore the previous batch's words
   (k=0 must clear to zero).
4. Selection unchanged, workspace |0>, phase clean (0 mod 1 turn) after
   BOTH passes.
5. Toffoli counting from cumulative `sim.operation_statistics()`,
   batches padded to 256 shots so totals are exact.

Seed fidelity (invsqrt lesson): batches use SHA-256-seeded sequences
derived from the circuit's canonical .kmb bytes, the same convention
as `code/verify_invsqrt_local.py`. The circuits here are classical
(no HMR), so the seed does not change outcomes — but the convention is
kept so the harness is identical in form to the official verifier.

Score projection (Part B): angles (fwd+rev) + Givens exact;
state-prep held at the baseline anchor (outer+inner = 10,307 Toffolis,
derived as 93,237 - 79,480 - 3,450); non-angles Q = 634. Exact for
J-only comparisons at fixed brot; approximate for brot comparisons
(beta=brot also enters SpinFreeData_V1).

### Verifier bugs found and fixed during this task

Two lexicographic-sort bugs, both in the verifier (the generator and
circuits were correct in both cases):
1. **Word-register sort** (`check_register_contract`): `sorted()` on
   names put `word_10`/`word_11` before `word_2`, so any J>=10 family
   (J=12/b8) crashed the contract check. Fixed with a numeric sort key.
2. **Circuit-file sort** (`verify_family`): `sorted()` on filenames put
   `angle_k_10.kmb` before `angle_k_2.kmb`, so any family with >=11
   circuits (J=7, 11 circuits) ran the circuits in the wrong order and
   "failed" at k=2 with word_mismatch — the circuits were always
   correct; the verifier was loading circuit 10 in slot 2. Fixed with
   a numeric sort key. This was diagnosed by isolating circuit k=2 and
   showing it passes with every seed, including the verifier's exact
   SHA-256-derived seed.

### Verifier performance

Vectorized I/O (write_across_shots for pre-loads, read_across_shots
for word/selection reads, read_phase_flipped_across_shots for the phase
check — validated to agree exactly with per-shot read_shot_phase on a
probe circuit) cut the full 3,976-address verification from 4m46s to
2m03s, with byte-identical results. The remaining cost is the circuit
simulation itself, not the Python I/O.

## Files

- `code/dfthcsos_gen.py` — generator. CLI: `--synthetic` / `--words-npz` /
  `--words-npy`, `--brot`, `--J`, `--strategy delta-unary|init-lookup`,
  `--out-dir`, `--prefix`. Writes real binary .kmb + manifest.json
  (sha256 + stats). Rejects J/brot combos over the 128-qubit cap.
- `code/verify_dfthcsos_local.py` — local verifier replica (verify /
  score / metrics).
- `data/dfthcsos_synth/` — candidate family on synthetic words
  (10 circuits, manifest.json). Full local PASS (see above).
- Synthetic words: `/tmp/synth_words.npy` (3976x75, seed 7) — ephemeral;
  regenerate with `--synthetic --seed 7` if needed.

## What is NOT claimed

No improvement factor is claimed. The projected ratios in the config
table hold lambda_eff at the baseline value; the real lambda_eff at
each (R, B, C, brot, J) needs the REAL factorization, which lives only
in the Kaggle dataset. The official verifier must pass a family on the
real factorization in the notebook before any improvement is real —
that run is done by the parent, not here. The factorization lever
(LBFGS over R/B/C + orthogonal-gauge optimization, per the public
frontier) is the next work, in the notebook, on the real data.
