# Verification protocol for a spliced DQI tape

This is the gate the surgery must pass before any packaging. It uses the **unmodified official
verifier** (`data/competition/verifiers/dqi/verify_submission_dqi.py`, read-only) and the existing
harness `experiments/frontier/20261118_push/dqi_patch/k_patch/`. Nothing here was executed this
round.

## 0. Why `/usr/bin/python3` and why the salt loop matters

The verifier needs `kickmix`; on a Kaggle script kernel `sys.executable` is Python 3.13 without
`km.Circuit`, while `/usr/bin/python3` carries it. `k_patch/main.py` already hard-codes

```python
VERIFIER_PY = "/usr/bin/python3"
```

The verifier's seed is `sha256(circuit_sha256 + salt)` and it also seeds `HMR`/`R` outcomes, so
**the Toffoli count is deterministic per (file, salt)** but differs between salts because the
measured `HMR` outcomes change which `CZ_IF`/`Z_IF` corrections fire. A candidate that passes one
salt can still lose a shot on another (this happened twice on `575b043f`'s neighbourhood — see
`RECORD.md` lines 269–271 and 301–302). Hence: three salts, and the gate is the worst one.

## 1. Salts

Use exactly three, in this order, and stop at the first failure:

```
salt 1: ""            (default; the reference number to compare against 367,116.06)
salt 2: "s1"
salt 3: "s2"
```

Budget: ~160 s per salt on a CPU kernel (measured on `575b043f` at 102,400 shots), so ~9 minutes of
verifier time plus ~2 minutes for decompress/read/splice/write. One kernel run, one report.

## 2. Procedure

1. Put the replacement into `dqi_patch/k_patch/main.py:SPEC` as
   `{"range": [a, b], "ops": [[name, qubits, bits], ...], "salts": ["", "s1", "s2"]}`.
   For the three-range splice of `SPEC.md` §5, either run `k_patch` once per range in sequence
   (each run takes the previous output as its input tape) or extend `SPEC` to a list of ranges —
   the first is safer, and the middle range must be re-read each time.
2. Splice with `dqi_patch/splice.py` semantics (already inlined in `k_patch`): it checks
   `depth(a) + depth(new) == depth(b)`, that the replacement never pops below depth 0, that no
   qubit/bit id exceeds the tape's width, and re-runs `Circuit._check()` after concatenation.
3. Write, sha256, then run the verifier once per salt, capturing `value_errors`, `phase_errors`,
   `toffoli_count` (mean T), `qubits_used`, `qubit_gaps`.
4. Emit `dqi_patched.kmb.xz` **only if every salt is `0/0` and the sha changed**.

## 3. Acceptance gate

```
value_errors == 0            for every salt
phase_errors == 0            for every salt
meanT        <= 264,700      (report the value at salt 1; record all three)
qubits_used  == 890          and qubit_gaps == 0
num_ops, num_bits unchanged in width (bits <= 66,726; no new register names)
```

`meanT <= 264,700` ⇒ `GM >= 31.42`, i.e. `c_dqi <= 1.1912605 · 890² · 264,700 = 249.9e9`
(tape today 346.41e9). The target is 249,087 T ⇒ GM 32.07; the gate is 15,613 T of slack, which is
exactly the normalization budget of `SPEC.md` §1.3.

Report, per salt, in `patch_report.json`: `rc`, `seconds`, `value_errors`, `phase_errors`,
`toffoli_count`, `expected_gm`. Add `delta_T = meanT − 367,116.06`.

## 4. Rollback

The tape in `submissions/` and the dataset are read-only for this work. Rollback is therefore
purely local:

* `k_patch` writes `dqi_patched.kmb.xz` **only** when all salts are 0/0, so a failing candidate
  leaves no artifact that could be confused with a good one;
* the source tape is re-fetched from the dataset into `/kaggle/working` on every run and deleted
  before exit — never copy a patched tape into `submissions/` or into the dataset;
* if a splice succeeds but the GM comes out above 264,700 T, keep the report and discard the `.xz`;
  do not "improve" it in the same kernel;
* if a later range's splice fails after an earlier one succeeded, discard the whole chain and
  re-run from the original tape — do not stack partial splices.

## 5. Ordering of cheap checks before the 9-minute verifier run

Run these inside the same kernel, in this order, so a structural error costs seconds instead of
9 minutes:

1. `Circuit._check()` after every splice (inside `splice()`), and `num_qubits == 890`,
   `num_bits == 66,726`.
2. `static_counts()['CCX'] + ['CCZ']` against the predicted number from `SPEC.md` §1.3
   (202,860 + 138·n + 46,217 for the full replacement) — a mismatch of a few units is a real bug,
   not noise, because the tape's Toffoli budget is 100 % closed.
3. `depth(P1) == depth(P2) == depth(P3) == 0` on the *spliced* tape, and the replacement's own
   `PUSH/POP` balance.
4. `liveness()`-based wire check: `qubit_gaps == 0` (a new ancilla must reuse an existing pool
   qubit, not extend the wire range — Q is squared in the score).

## 6. Small-parameter oracle (do this before the 4095/70/12 tape)

The official verifier CLI accepts `--m --n --degree`, so the same generator can be run at
`m=63, n=6, degree=4` and verified end-to-end in seconds. Use it to decide `SPEC.md` §3 case A vs B:
if a projective (un-normalized) divstep passes 0/0 at `n=6, degree=4` on three salts, the
scale-invariance argument holds and the 202,860 T budget is safe. If it fails, the design must pay
for normalization and the gate in §3 cannot be met — stop before touching the real tape.
