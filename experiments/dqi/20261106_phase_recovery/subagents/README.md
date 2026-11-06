# subagents: lower-CCX DQI kernels

Main report: [`REPORT.md`](REPORT.md).

One-line result: no lower-CCX equivalent was found; the baseline remains best.
The proven lower bounds are 11/12/21/24/24 CCX for
`inverse12 norm` / `inverse12 products` / `inverse24 norm` /
`inverse24 products` / `multiply v` (baseline 15/25/42/70/99), and the
five-kernel full-circuit saving ceiling is **4,762 T** (4,925 T under the weaker
span-rank bound), below the 5,000 T target.

Verification performed: exact symbolic ANF for all five windows; exhaustive
classical simulation of `inverse12 norm` (4096/4096) and `inverse12 products`
(262144/262144), 0 mismatches. No official verifier run; no KMB modification;
no commit/push.

Scripts: `kernel_anf.py`, `export_kernel.py`, `rank1_span.py`,
`symmetric_span.py`, `ccx_profile.py`, `window_context.py`,
`wire_first_touch.py`, `verify_window.py`, `cp_sat.py`, `run_cp2.py`.

Generated data: `artifacts/20261106_phase_recovery/subagents/`.
