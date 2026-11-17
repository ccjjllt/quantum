# 2026-11-18 push — master record

Round 2 of parallel research after the 2026-11-17 deep pass. All numbers below are
measured unless marked **[model]** (pure arithmetic from the official cost code).

## 0. Starting point

Shipped triple (verified, 28.1806 local): invsqrt `563d0583` 74,560.90687 /
DQI `575b043f` 346,409,762,292.72 / chem `a73b25d2` 294,643,137.73.
LB 28.15094 (rank 156), gold 28.71339, top 31.42723.
Submission quota: 5/5 used on 2026-11-17; resets UTC 00:00 = Beijing 08:00 on 11-18.

## 1. probe791 (chem, reduced rows) — COMPLETE, negative

Kernel `qingyu1232/qcc-chem-probe791` (2026-11-17 15:15–15:51). Truncated the
shipped 1,220-row table to 791 rows and asked the emitter to plan loaders for
k=2 and k=4 with a 900 s budget each, 4–5 seeds each.

```
k2: target len 50 (hmax 49); seeds 11/7/9/8: no rank-74 basis found
k4: target len 50 (hmax 49); seeds 11/7/9/8: no rank-74 basis found
SUMMARY {"2": null, "4": null}
```

So a 791-row table cannot even be planned at rank 74 within 4 × 15 min per k.
The rows axis is closed on the *loader-planning* side as well as the accuracy
side (RESULT2: (5,143,88) is 136.76 mHa continuous, gate 20).

## 2. R=5 / R=4 shapes — closed with exact model values

Subagent result (2026-11-18 ~00:20), exact full-space objective:

| shape | rows | best continuous error_2 | exact-model Q | T_h |
|---|---:|---:|---:|---:|
| (5,143,88) | 791 | 136.76 mHa | 429 | 7,539 |
| (5,136,96) | 756 | 135.20 mHa | 430 | 7,916 |
| (4,143,128) | 648 | 176.76 mHa | 429 | 8,243 |
| (6,136,72) | 892 | 127.69 mHa | 427 | 7,433 |

The gate is 20 mHa — 6.5–6.8× away. The one shape that clears continuous 20 mHa,
(8,143,55) at 18.05, fails on quantisation (error_1 50 mHa) and lambda_eff
(63.90 vs 46.92), cost 313.8 M. Closed. Full record:
`experiments/frontier/20261117_deep/chem/R5_SHAPE/RESULT.md`.

## 3. New lever: `brot` is submission-controlled (chem) **[model]**

`verifiers/dfthcsos/verify.py` reads `brot` and `J` from the width/number of the
`word_j` registers of the submitted angle circuits, then uses `beta = brot` in
`SpinFreeData_V1`. Exact values for the shipped shape (R=8,B=143,C=44,N=76,
chi=10 fixed, J=5):

| brot | givens `2*(N-1)*(2*brot-1)` | T_h | Q_total |
|---:|---:|---:|---:|
| 8 (shipped) | 2,250 | 6,662 | 427 |
| 7 | 1,950 | 6,362 | 422 |
| 6 | 1,650 | 6,062 | 417 |
| 5 | 1,350 | 5,762 | 412 |
| 4 | 1,050 | 5,462 | 407 |

`theta/pi = word / 2**(brot-1)`. The shipped `angle_words` (1220, 75) uint8 uses
all 256 values (odd count 45,088), so 7-bit is **not** free: it needs a refit at
7-bit word quantisation that keeps `error_1, error_2 <= 0.020`, `Lambda >= 49`.
If it works: brot 8→7 is `(422/427)*(14412/14706) = 0.9685` on chem cost
(**+0.30 GM**), brot 8→6 would be 0.9307 (**+0.72 GM**) but 6-bit quantisation is
much coarser. Assigned to the chem research line.

A second free knob in the same formula: `Q_total = 84 + J*brot + max(...)`.
J=5 is shipped; smaller J lowers Q but multiplies the number of loader circuits.
Assigned to the chem line (J sweep).

## 4. Parallel research lines opened (2026-11-18 00:40 Beijing)

Brief: `experiments/frontier/20261118_push/BRIEF.md`.

| line | account | target |
|---|---|---|
| dqi | zhuating | verify new public DQI set; product-cache finder inside condition blocks; Q<=866 feasibility |
| chem | qingyu1232 | brot 8→7 (and 6), 4,022 public loaders, J sweep |
| invsqrt | jiyujia | fresh 42Q synthesis / lower C |
| harvest | ccjjllt_check | new public components + top-team intel + papers |
| model | zhuating | full audit of submission-controlled parameters in all three verifiers |

## 4b. Packaging bug found and corrected (2026-11-18 00:55)

The "28.1806" package built by `qingyu1232/qcc-integrator-inv563d0583` v2 is **wrong**:
its `receipt.json` shows `dqi.kmb` sha `957d6733…` with **value_errors 1** on the default
salt, cost 348,246,849,661.48, GM **28.1310187** — below the current LB 28.15094.
`members_2818066.json` itself carries the wrong DQI sha; the "salt false alarm" note in
SUMMARY2 §17 was masking a manifest error.

Corrected manifest `integration/members_281806_correct.json`: same invsqrt (`563d0583`)
and same chem 18-member set, DQI replaced by `575b043f`
(sha `575b043f4fee…`, 479,128,738 B) from
`grantprater/vqcc-dqi-61c8348d-merged-closings : dqi_575b043f.kmb.xz`.
New integrator `qingyu1232/qcc-integrator-281806` v1 (expected GM 28.180659; the kernel
extracts the `.xz` and matches the sha). The LB draw for `575b043f` is already known clean
from submission 58464076, so the expected LB score is 28.18 if the salt is per-file.

## 5. Submission plan

Quota resets 2026-11-18 08:00 Beijing. Submit the best verified package then and
record the public score + submission ref here and in `submissions/`.
