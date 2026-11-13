# 20261113 27.078 public-frontier trio

Sources: `ozertuu/quantum-sim-linalg-cache` v25 (2026-11-12 21:57 UTC),
from Syed Asad Ali's Apache-2.0 v12 own-circuit portfolio and the
`ozertuu/quantum-ai-27-083-vqcc-dqi-cutoff-17` notebook.

## Members (all independently re-verified with the unchanged official verifiers)

| Task | Circuit | Q | Official full verification | Cost |
|---|---|---:|---|---:|
| invsqrt | `321aff83…35177` | **46** | **PASS**, 200,540,928 shots, worst/tol 0.9735759969 | **80,162.732141** |
| DQI | `7cbe8ecf…14cd9` | **889** | **PASS**, 102,400 shots, 0 value / 0 phase, R=1.1912604648 | **360,733,280,431.94** |
| chemistry | `6418ec8e…a77f` | **427** | **PASS**, 78,080 shots, error_1=0.0196103713, error_2=0.0199987799 | **296,635,967.5936** |

- invsqrt: `toffoli_count=1511.5700`, `toffoli_equivalent=1742.6681`, 33 rotations,
  `rotation_eps=6.4185e-13`.
- DQI: `toffoli_count=383,156.2909`, `max_toffoli_count=384,003`.
- chem: `T=14,810` (4,074 T/pass loaders), `lambda_eff=46.907347493481`.

## Score

GM = `(2076774.2337/80162.7321 × 24439463583672.93/360733280431.94 ×
3355599588.3155/296635967.5936)^(1/3)` = **27.0783908611**.

DQI is the cutoff-17 variant: it excludes weights 15–16 with additional
probability ≈1.525e-7/shot (expected 0.0156 errors per 102,400-shot draw).
The official default-salt run had 0 value / 0 phase errors; a 1-error draw
would raise DQI cost by 0.46% and still leave GM ≈27.03.

## Package

- ZIP SHA-256: `63c5a0776bb1d91490c2e50e4c04607c78b91472f9da45247901ea4af314657c`
- 18 files; 463,378,740 bytes uncompressed; 47 MB compressed.
- Previous submission 58290992 completed at **25.44039** (392k DQI swap);
  this package supersedes it.
- **Submission ref**: 58299045 (2026-11-13 06:40 UTC), status PENDING at submission time.
