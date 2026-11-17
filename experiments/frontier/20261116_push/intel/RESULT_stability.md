# DQI draw-stability analysis — 2026-11-17

Scope: NO new verification, NO simulation, NO downloads. Local work limited to
reading already-verified JSONs + GM arithmetic. Sources:
`intel/RESULT_verify_new.md` §0/§3–§4, `intel/RESULT_verify_new2.md` §0/§3–§5,
`intel/RESULT_verify_new3.md` §0/§3–§5, `pipeline/RESULT_2813137.md`,
`pipeline/RESULT_2814703.md`, plus cited prior receipts for single-draw legs.
Refs throughout: 2076774.233715 / 24439463583672.93 / 3355599588.3155375.
Fixed combo legs: invsqrt `0af21cb8` 74797.36535717871, chem `93326853`
294762512.64351326 (salt-invariant, verify_new2 §0/§3).

## 0. Verdict

1. **A 3/3-clean DQI leg exists: `b0983d55`** — 3/3 full-shot (102,400) official-verifier
   draws PASS 0 value / 0 phase errors (verify_new2 §0/§3). It is the ONLY leg clean
   under the full default+2-salt protocol. (`66b4f18b` is 2/2 clean but across mixed
   shot counts: lab default 102,400 + dataset 409,600 census, RESULT8 §1/§5.)
2. **Expected-public maximizer: `0af21cb8` + `b0983d55` + `93326853`**,
   E[GM] ≈ **28.12994** (mean-cost GM 28.12993954; worst-verified draw 28.12993 —
   tightest spread of any leg). Runner-up: `66b4f18b` (28.12770, 2/2 clean).
3. **Public-board confirmation of draw risk:** `f425ea20`-combo ref 58451475
   (local default 28.13137, 0/0) read back at **public 28.08843** (reported LB
   readback, not re-checked here). That equals the lab lost-shot draw to display
   precision: worst-verified-draw GM **28.08843972**; implied public DQI cost
   348586162329.19 (×1.004593) vs lab lost/default ×1.004592 (§4). The public
   resample drew the lost shot.
4. **Recommendation: SUBMIT the `b0983d55` combo; HOLD the rest** (pipeline owns
   slots; no submission by this task). Rationale: highest expected public score,
   sole 3/3-clean record, worst-verified floor (28.12993) still above every other
   leg's expectation except `66b4f18b`'s point estimate. HOLD `61c8348d` (ceiling
   28.14703 but E ≈ 28.118 at 1/3 clean; already shipped as 28.10407 in 58452435),
   HOLD `f425ea20` re-ship (public lost-shot already demonstrated in 58451475),
   HOLD `957d6733` (1/3 clean, E ≈ 28.112).

## 1. Per-leg draw table (DQI; already-verified JSONs only)

Clean = 0 value AND 0 phase errors at full 102,400 shots, unchanged official verifier.

| leg | default (score / errors) | salt-8ad413d9 (score / errors) | salt-3b61c944 (score / errors) | clean rate | worst-draw score | worst-draw GM* |
|---|---|---|---|---|---|---|
| `b0983d55` | 347045216047.3212 / 0/0 | 347044985354.3402 / 0/0 | 347045638537.53455 / 0/0 | **3/3 (100%)** | 347045638537.53455 | **28.12992985** |
| `66b4f18b` | 347128304010.81165 / 0/0 | — (no lab extra-salt draw) | — | 2/2† (100%) | 347128304010.81165 | 28.12769671 |
| `f425ea20` | 346992317312.81555 / 0/0 | 348585800615.90533 / **1**/0 | 346992211342.40283 / 0/0 | 2/3 (67%) | 348585800615.90533 | 28.08843972 |
| `61c8348d` | 348004440260.464 / **1**/0 | 346413579540.4963 / 0/0 | 348004496006.9543 / **1**/0 | 1/3 (33%) | 348004496006.9543 | 28.10407060 |
| `957d6733` | 348246849661.4793 / **1**/0 | 348246840728.34033 / **1**/0 | 346654523463.49384 / 0/0 | 1/3 (33%) | 348246849661.4793 | 28.09754965 |
| `00ac37d4` | 347357914646.9683 / 0/0 | — | — | 1/1 | 347357914646.9683 | 28.12149768 |
| `ccc2ab84` | 347375470571.73334 / 0/0 | — | — | 1/1 lab‡ | 347375470571.73334 | 28.12102393 |

\* Full combo `0af21cb8` + DQI + `93326853`, refs above.
† `66b4f18b` second clean draw is the dataset 409,600-shot census PASS 0/0
(RESULT8 §1/§5; score class 347128304010.81 per dataset JSON, corroborated to the
digit by k18 at 102,400) — mixed shot counts, not the 3-salt protocol.
‡ `ccc2ab84` lab evidence is a single default draw; third-party kernels report lost
shots on other salts (boristown `notebook-verification` 1 value error, RESULT.md
§6; neoluxlee 2 extra salts 0-error + 1 public salt 1 value error, RESULT.md §2.1) —
kernel-reported, not lab-verified JSONs. Draw-sensitive, rate unquantified.

Draw sources: `f425ea20`/`b0983d55` verify_new2 §0/§3 (+ pipeline RESULT_2813137 §Exact
for the f425 default JSON); `61c8348d`/`957d6733` verify_new3 §0/§3 (+ pipeline
RESULT_2814703 §Exact for the 61c default lost-shot JSON); `66b4f18b`/`00ac37d4`
RESULT7 §0/§3 (k18 defaults 0/0, exact claimed scores); `ccc2ab84` pipeline
RESULT.md §Exact (v3 default 0/0) / RESULT_bdae.md §Official.

## 2. Fixed legs (not ranked; for the record)

- invsqrt `0af21cb8`: 74797.36535717871 / 74797.36796904955 / 74797.38784421439
  (default + 2 salts, all PASS; worst/tol 0.9995605646154175, worst_x 231) —
  salt spread moves the combo GM by ~3e-7 (28.12994127 → 28.12993845 on fixed
  b098/933 legs). Negligible for slot decisions. (verify_new §0/§3.)
- invsqrt `5eeea23b`: 75006.40286232081 + 2 salts (75006.30286552115 =
  aditya draw-1 to the digit; 75006.37662063513 vs their published
  75006.38432087375, Δ 1.0e-7 relative — flagged, tie-band only). Not in combos.
- invsqrt `f2cdab0b`: single lab draw 75006.37653863191 (pipeline RESULT.md §Exact).
- chems `703843d3` / `0bd9c68f` / `93326853` / `a970f175`: salt-invariant, identical
  to all digits across all 3 salts (verify_new §0, verify_new2 §0/§3).
  `93326853` (294762512.64351326) is the cheapest verified chem (−0.2161 vs
  `703843d3`; combo-GM delta ~7e-9, sign real, magnitude negligible).

## 3. Combo rankings (`0af21cb8` + DQI + `93326853`)

### (a) By default-draw GM

| rank | DQI | default-draw GM |
|---|---|---|
| 1 | `f425ea20` (0/0) | 28.13137066 |
| 2 | `b0983d55` (0/0) | 28.12994127 |
| 3 | `66b4f18b` (0/0) | 28.12769671 |
| 4 | `00ac37d4` (0/0) | 28.12149768 |
| 5 | `ccc2ab84` (0/0) | 28.12102393 |
| 6 | `61c8348d` (**1/0**) | 28.10407210 |
| 7 | `957d6733` (**1/0**) | 28.09754965 |

(Best-clean (non-default) draws for reference: `61c8348d` salt-clean 28.14702788,
claim-clean 28.14703578; `957d6733` salt-clean 28.14050513; `f425ea20` salt-s2
28.13137352; `b0983d55` salt-s1 28.12994750.)

### (b) By worst-verified-draw GM (floor)

| rank | DQI | worst-draw GM |
|---|---|---|
| 1 | `b0983d55` | **28.12992985** |
| 2 | `66b4f18b` | 28.12769671 |
| 3 | `00ac37d4` (single draw) | 28.12149768 |
| 4 | `ccc2ab84` (single lab draw) | 28.12102393 |
| 5 | `61c8348d` | 28.10407060 |
| 6 | `957d6733` | 28.09754965 |
| 7 | `f425ea20` | 28.08843972 |

### (c) By clean-draw rate

`b0983d55` 3/3 > `66b4f18b` 2/2† > `f425ea20` 2/3 > `61c8348d` = `957d6733` 1/3 >
`00ac37d4` = `ccc2ab84` 1/1 (insufficient + third-party lost-shot reports for ccc).

### (d) By expected GM (mean verified cost; local arithmetic)

| rank | DQI | mean cost | E[GM] |
|---|---|---|---|
| 1 | `b0983d55` | 347045279979.732 | **28.12993954** |
| 2 | `66b4f18b` | 347128304010.812 | 28.12769671 |
| 3 | `00ac37d4`* | 347357914646.968 | 28.12149768 |
| 4 | `ccc2ab84`* | 347375470571.733 | 28.12102393 |
| 5 | `61c8348d` | 347474171935.971 | 28.11836105 |
| 6 | `f425ea20` | 347523443090.375 | 28.11703214 |
| 7 | `957d6733` | 347716071284.438 | 28.11183907 |

\* Single-draw legs: point estimate only, no resampling mean; ccc has documented
third-party lost-shot draws, so its true E is below the point estimate.

## 4. Public-board cross-check (local arithmetic only)

- Ref 58451475 (`0af` + `f425ea20` + `93326853`): local default GM 28.13137066
  (pipeline RESULT_2813137 RUN_SUMMARY 28.131370655928556) → reported public
  **28.08843**.
- Lab worst-draw GM for the same legs: **28.08843972** (salt-8ad413d9 lost-shot
  348585800615.90533). Match to display precision.
- Inversion: public 28.08843 implies DQI cost 348586162329.19, i.e. ×**1.004593**
  over the clean default; lab lost/default ratio ×**1.004592**. Match.
- Conclusion: the public resample drew the lost-shot outcome (≈+0.46% DQI cost,
  R 1.19673 vs 1.19126). Default-draw GM overstates this leg's public expectation
  by ~0.043 (≈28.13137 → E 28.11703).

## 5. Recommendation

- **SUBMIT: `0af21cb8` + `b0983d55` + `93326853`** (default-draw GM 28.12994127,
  worst-verified 28.12992985, E ≈ 28.12994, 3/3 clean). Maximizes expected public
  score among all verified legs; only leg whose floor survives resampling intact.
- **HOLD `61c8348d`** (ceiling 28.14703, but 1/3 clean, E ≈ 28.118, 2/3 of draws
  land at ~28.104 — below the 28.12769 public cluster; already shipped as
  28.10407 in ref 58452435, awaiting readback).
- **HOLD `f425ea20` re-ship** (default 28.13137 flatters a 2/3-clean leg; public
  already demonstrated the failure mode at 28.08843 in ref 58451475).
- **HOLD `957d6733`** (1/3 clean, E ≈ 28.112, worst 28.09755).
- **HOLD `66b4f18b` re-ship** unless a slot must be spent conservatively: solid
  second choice (28.12770, 2/2 clean incl. census) but strictly below `b0983d55`
  on default, worst, and expected — it only wins on evidence volume (census at a
  second shot count).
- No package built, no submission made by this task; pipeline owns slot decisions.
