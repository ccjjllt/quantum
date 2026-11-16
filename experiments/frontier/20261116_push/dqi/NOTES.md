# working notes (superseded by RESULT.md)

See `RESULT.md` for the finished record. Kept only for the target table.

## Target table (given invsqrt 75,006.38 and chemistry 294,762,697.44 fixed)

| overall GM | DQI needed | at Q=840 | Q=850 | Q=860 | Q=870 | Q=880 | Q=890 |
|---|---|---|---|---|---|---|---|
| 30.285 | 277.33e9 | T 330.3k | 322.6k | 315.1k | 307.9k | 300.9k | 294.2k |
| 29.98 | — | 340.5k | — | — | — | — | 303.3k |
| 29.57 | — | 354.7k | — | — | — | — | 316.0k |
| 29.01 | — | 375.8k | — | — | — | — | 334.7k |

Q-only sensitivities at T = 368,139 and the 28.0909 baseline: Q 890→884 +0.127 GM,
→880 +0.22, →876 ≈ +0.28, →870 +0.43, →860 +0.65, →850 +0.88, →840 +1.11.

T budget for a Q reduction, T_max = 368,139·(890/Q)²: Q=884 +6,900 T; 880 +12,300;
870 +34,100; 860 +56,900; 850 +80,700; 840 +105,500.

Re-draw threshold for any DQI circuit change: cost must fall by ≳0.09 % (≈320 T) before the new
salt draw is worth it.
