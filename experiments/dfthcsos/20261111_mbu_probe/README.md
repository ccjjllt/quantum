# Measurement-based uncompute in the ANGLE loaders (2026-11-11): already exploited

Branch `codex/dfthcsos-research`, worktree `.worktree/dfthcsos/`.
Read-only probe of the baseline loaders; no circuit was edited, no new
candidate was verified, no Kaggle submission/push.

Question: the verifier charges the 15 loaders twice (8,246 of 14,908 T).  Can a
forward+MBU loader replace a reverse lookup (claim: 126 → 17 Toffolis) and
lower that charge?  Answer: the public loaders **already are** forward+MBU;
the remaining 4,123 CCX/pass is the forward oracle, and the 1,142
prefix/setup ancillas are uncomputed by measurement at zero Toffoli cost.

## 1. Exact parse (all 15 loaders, baseline `8afd4c67`)

Script: `experiments/dfthcsos/20261111_mbu_probe/parse_loaders.py`.
Output: `artifacts/20261111_mbu_probe_output.txt`.

| loader | CCX/pass | HMR | CZ | CCX after last HMR |
|---|---:|---:|---:|---:|
| k0 | 297 | 80 | 80 | 0 |
| k1–k3 | 290 | 75 | 75 | 0 |
| k4 | 270 | 75 | 75 | 0 |
| k5–k6 | 269 | 75 | 75 | 0 |
| k7–k8 | 270 | 75 | 75 | 0 |
| k9 | 267 | 76 | 76 | 0 |
| k10–k13 | 268 | 77 | 77 | 0 |
| k14 | 269 | 78 | 78 | 0 |
| **total** | **4,123** | **1,142** | **1,142** | **0** |

Every CCX precedes the first HMR block; after the last CCX the tail is only
CX / HMR / CZ / X.  The HMR count equals the prefix+setup CCX count per loader
(k1: 69 prefix + 6 setup = 75; k0: 69 + 11 = 80).  The MBU block is an
X-basis measurement of each ancilla followed by a conditional CZ phase repair,
with **0 CCX**.  A coherent uncompute would add 1,142 CCX/pass = **2,284
T_total** (15.32 % of 14,908; 27.70 % of the 8,246 angle T).  That saving is
already in the baseline.

## 2. Official self-inverse / reverse-clear test

`recover_words_from_circuits` (the verifier's own function) applies the same
circuit forward and in reverse order; it raises unless the words are
deterministic on repeated shots, the reverse traversal clears to the previous
batch, the selection is unchanged, the workspace is clean and the phase is
unflipped.

- One loader (k0, batch 0, `num_angles=5`, `shots_per_address=2`):
  `words_match=True`, `toffoli_fwd_rev=594.0` = 2 × 297.  Forward loads batch 0;
  reverse clears.
- Full family (15 loaders, 1,220 vectors, 75 angles, 2 shots/address):
  `words_match=True`, `toffoli_fwd_rev=8,246.0` = 2 × 4,123.

So the forward+MBU design passes the self-inverse check; it does not fail.
The full 78,080-shot PASS is the fresh salt `recon-baseline-20261111` log
`artifacts/20261111_recon_verify/baseline_full.log` (and the earlier
`artifacts/20261111_grimoire33/verify_chem.log`).

## 3. Why there is no further MBU headroom

The 215 loads (k1) / 217 (k0) are the XOR oracle output: they write the lookup
result into the word registers.  They are not ancillas and cannot be measured
away.  The verifier applies the same circuit twice by contract, so the 4,123
forward CCX are charged as 8,246; that is structural, not an uncomputed reverse
lookup.  The claimed 126→17 repair would apply to a loader that still carries a
126-CCX reverse lookup; these loaders carry 75 (k0: 80) prefix/setup CCX and
**zero** reverse-lookup CCX.

## 4. Verdict

**Closed as already exploited.**  A rebuild would reproduce the existing MBU
block, not add a saving.  The remaining angle-T levers are the load count
itself (synth line closed: k0 0 candidates, Maoxin 215 is the public best) and
the word width (7-bit: see `20261111_7bit_probe/`, accuracy fails).

## 5. Verification scope

- Parse + official `recover_words_from_circuits` at 2 shots/address only.
- The full baseline PASS was run once this session via `manual_verify.py`
  (salt `recon-baseline-20261111`, 78,080 shots, exit 0, 298,600,061.555139);
  it is the baseline, not a new MBU candidate.
- No circuit file was written to `artifacts/`; the kmx exports were temporary.
