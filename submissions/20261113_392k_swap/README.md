# 20261113 392k DQI swap

- **Change**: DQI `eae396ba` → public `maoxin123/qcc-dqi-392k-toffoli-decoder`
  (`4c81b726…01e5d9`). invsqrt `9c708f7b` and chem `5d5007a75784` unchanged.
- **Why**: 392k has mean T 392,016.12 vs eae 394,089.46 (−0.5261%); paired-seed
  test shows the **same failure pattern on 8/8 seeds**, so it is a strict per-draw
  dominance, not a new approximation.
- **DQI verification**: 16 salts + 8 paired seeds × 102,400 shots = 2,457,600
  official shots, all PASS; 7 errors / 1,638,400 shots (16-salt), λ=0.4375/draw.
- **invsqrt**: unchanged `9c708f7b`; previous full official PASS 200,540,928 shots.
- **chem**: unchanged `5d5007a75784`; previous official PASS 78,080 shots.
- **Expected GM**: 25.4329 (eae expected 25.3882; current public 25.40482 is eae's
  0-failure draw). 392k 0-failure 25.4495; 1 failure 25.4107; 2+ failures 25.3778.
- **ZIP SHA-256**: `818057cdb455c4653d5944e9fd82afef2a74996f454b257ffbc6e6a2b0e58fd6`
- **Files**: 18 (invsqrt.kmb, dqi.kmb, dfthcsos/submission.npz + 15 angle loaders).
- **Submission ref**: 58290992 (2026-11-13 01:26 UTC), status PENDING at submission time.
