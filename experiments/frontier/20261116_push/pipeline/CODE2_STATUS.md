# CODE2 chemistry loader handoff status

Last checked: **2026-11-16 12:00 UTC**.

## Verdict: no candidate; do not submit

`experiments/frontier/20261116_push/chem/CODE2.md` appeared at 11:56 UTC. Its conclusion is that
the code/gauge axis on the 4,025-Toffoli loader set is closed. The hoped-for "190 products vs 193,
~3 gates/loader" is **not** a win on this table:

- shipped products per loader are already 189 (k4-9), 190 (k10), 191 (k11-14), with the expensive
  k0/k1 at 217/213;
- the new 145-cut basis states give 190 products = **T 265**, versus shipped k9 T 264, k10 T 265,
  k12 T 265, k14 T 266. That is a tie for k10/k12, a loss for k9, and only a 1-gate win for k14;
- the k14 1-gate win is **not emittable** with the shipped emitter: batches 9, 10 and 14 have a
  different `bit7 XOR bit6` helper convention, and batches 11-13 fail the six-AND low-cache
  independence assertion. The last six loaders need a different emitter that is not in the tree;
- the mixed package `zhuating/qcc-chem-code2-mix-c44` was an intentional **negative control**
  built from syed plans for a different word table. It FAILED the official verifier exactly as
  predicted:

```text
AssertionError: error_1 = 61130.5490 mHa > 20 mHa;
                error_2 = 11659.1079 mHa > 20 mHa
```

It is not a candidate and was not submitted.

## What this means for the silver attempt

- There is **no verified chemistry package at T < 14,712** from CODE2.
- The current best real chemistry remains `bdae290f` at 294,762,632.0818, GM 28.0948754, which is
  below the **28.09490** gate. It is already verified and held (`RESULT_bdae.md`).
- No CODE2 submission was made. Latest actual submission remains ref **58424363**, COMPLETE,
  public **28.09486**. **2 slots remain.**
- The pipeline (`pipeline/main.py`, kernel `qingyu1232/qcc-frontier-28094-verify`) remains ready:
  it locates all 18 members by SHA-256, runs the unchanged official verifiers, packages 18 files,
  and enforces the **GM >= 28.09490** submit gate. A 28.09486-28.09489 result is held.

## If a new candidate appears

A real candidate needs at least a chemistry cost **<= 294,762,300** at the same T/Q, or a
DQI/invsqrt improvement, and must pass the chemistry verifier at default + two fresh salts
(78,080 shots each) plus the unchanged DQI/invsqrt checks. The pipeline can run that immediately;
update the member hashes and attach the candidate dataset, then push a new kernel version.
