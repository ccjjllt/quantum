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

## 4. Source mapping (arXiv:2610.22367, `andigu/uncompute`)

The cited claim is in `tasks/coulomb-potential/circuits/discovered/README.md`
(Apache-2.0), "Measurement-based unlookup (un-qrom)":

> Instead, the circuit measures each looked-up bit in the X basis and resets
> its wire to zero... The measurement clears the data wires; only this Boolean
> phase function needs repair. ... The complete repair therefore costs 17
> Toffolis instead of the 126 ANDs required by a second full tree walk.

So the andigu construction is a **phase gadget**, not a value uncompute:
X-basis measurement + reset zeros the data wires and leaves a random Boolean
phase function of the address, which is repaired by 17 Toffolis of ANDs plus
free phase gates.  The looked-up values are consumed before the measurement;
the circuit does not need them afterwards.

Mapping to our loaders: the prefix/setup ancillas (69 unary-iteration + 6
setup = 75 per loader; k0: 69 + 11 = 80) are scratch selectors.  They are
already cleared by 75 HMR + 75 CZ with **0 CCX** (k0: 80 + 80): the same
phase-gadget mechanism, with a repair cheaper than 17 Toffolis.  The 215
loads are direct CCX into the word registers (targets q11/q23/q25/q44/q24/q16
in k1), not a table-word compute/uncompute pair; there is no 126-CCX reverse
lookup in these loaders.

## 5. Bounded test: MBU on the word registers fails the official check

We built one variant: k0 with `HMR q11 … q50` appended (40 X-basis
measure+reset gates on word_0..word_4), as a temporary `/tmp/k0_word_mbu.kmx`.
`recover_words_from_circuits` (one loader, 5 angles, 2 shots/address) raises
(reproduced by `parse_loaders.py`, output
`artifacts/20261111_mbu_probe_output.txt`):

```text
InvalidCircuits: ANGLE_0: uncorrected phase (measurement kickback)
```

That is the exact failing check.  Even with a 17-Toffoli phase repair, the
HMR resets the word registers to `|0>`, so the forward `read_words` would not
equal batch 0; the verifier requires the word registers to hold batch k after
the forward pass and batch k-1 after the reverse pass.  MBU cannot clear or
replace a register whose value must persist.  The public loader's HMR block
passes because it acts on scratch prefix/setup ancillas, not on the word
registers.

## 6. Why there is no further MBU headroom

The 215 loads (k1) / 217 (k0) are the XOR oracle output: they write the lookup
result into the word registers.  They are not ancillas and cannot be measured
away.  The verifier applies the same circuit twice by contract, so the 4,123
forward CCX are charged as 8,246; that is structural, not an uncomputed reverse
lookup.  The claimed 126→17 repair would apply to a loader that still carries a
126-CCX reverse lookup; these loaders carry 75 (k0: 80) prefix/setup CCX and
**zero** reverse-lookup CCX.  The 2,284 T that a coherent prefix/setup
uncompute would add are already banked.

## 7. Verdict

**Closed as already exploited.**  A rebuild would reproduce the existing MBU
block, not add a saving.  The remaining angle-T levers are the load count
itself (synth line closed: k0 0 candidates, Maoxin 215 is the public best) and
the word width (7-bit: see `20261111_7bit_probe/`, accuracy fails).

## 8. Verification scope

- Parse + official `recover_words_from_circuits` at 2 shots/address only.
- The word-register MBU variant was a temporary `/tmp` kmx; it failed with the
  exact `uncorrected phase (measurement kickback)` check above.  It was not
  saved to `artifacts/` and is not a candidate.
- The full baseline PASS was run once this session via `manual_verify.py`
  (salt `recon-baseline-20261111`, 78,080 shots, exit 0, 298,600,061.555139);
  it is the baseline, not a new MBU candidate.
