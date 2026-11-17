# Assembly runbook — how to ship a new member fast

Everything here is CPU-only Kaggle. No local simulation.

## 1. Staging layout (18 members)

```
stage/
  invsqrt.kmb
  dqi.kmb
  dfthcsos/
    submission.npz            # U, W, H2_I, H1_I, Hsym_lower, tree_edges, angle_words
    angle_k_0.kmb .. angle_k_{K-1}.kmb
```

K must equal `ceil(num_angles / J)` = `ceil(75 / J)`; the verifier reads `J`
(number of `word_j` registers) and `brot` (their width) from the circuits.

## 2. Manifest + integrator

```
cd experiments/frontier/20261117_deep/integration
python3 make_members.py --stage /tmp/stage_new --out members_NEW.json --label "..." \
        --source "..."
python3 make_main.py --members members_NEW.json --out /tmp/kint_new \
        [--invsqrt-b64 invsqrt_563d0583.kmb.b64] --label "..." --expected-gm <g>
```

`make_main.py --invsqrt-b64` expects **zlib-compressed base64**. DQI/chem bytes can
be embedded the same way or located by (size, sha256) under `/kaggle/input`.
Then `python scripts/kgpu.py push --dir /tmp/kint_new --account <acct>`; the kernel
runs the three unmodified official verifiers, prints per-leg cost + GM, and writes
`/kaggle/working/submission.zip`.

Fetch the zip from the kernel output, record its sha256 and size in
`submissions/<date>_<label>/README.md`, then submit with
`kaggle competitions submit -c google-verifiable-quantum-circuit-compilation -k <kernel> -v <v> -f submission.zip`.
**Submission is manual and only after UTC 00:00 quota reset.**

## 3. Per-member swap recipes

* **invsqrt**: replace `invsqrt.kmb`; cost = Q*(Toffoli+T/4). Official verifier:
  `verifiers/invsqrt/verify_submission_invsqrt.py` (200,540,928 shots).
* **DQI**: replace `dqi.kmb`; cost = 1.1912605 * Q^2 * mean_toffoli. Official
  verifier: `verifiers/dqi/verify_submission_dqi.py` (102,400 shots). Always
  check >=3 salts; the LB draw uses a secret salt.
* **chem**: replace `dfthcsos/submission.npz` and any subset of loaders (the
  assembler keeps the cheapest verified loader per k). Cost =
  `lambda_eff * T * Q` with `T = 2*sum(loader Toffoli) + T_h` and
  `Q = 84 + J*brot + max(outer_temp, inner_temp, 77)` (shipped family).
  Official verifier: `verifiers/dfthcsos/verify.py <stage>`.

## 4. Known-good numbers (for regression)

| member | sha | official cost |
|---|---|---|
| invsqrt `563d0583` | 563d0583f736… | 74,560.90687312803 |
| dqi `575b043f` | 575b043f4fee… | 346,409,762,292.7187 |
| chem `a73b25d2` | a73b25d27cae… | 294,643,137.73 (lambda_eff 46.92158337, T 14,706, Q 427) |

Current expected GM: 28.180659. Zip of the verified triple: 85,200,406 B,
sha256 `cd24b38a5a022dbe7db5e4d8498c0480e93fbbe9de5f1ea109405d65f1ebc992`.

## 5. Checks to run before submitting

1. All three official verifier JSONs say PASS with 0 value/phase errors (DQI/chem)
   and 0 mismatch (invsqrt).
2. The GM from `scripts/gm.py` matches the integrator's printed GM.
3. 18 members exactly, names and shas listed in the receipt.
4. `submissions/<date>_<label>/README.md` records zip sha/size, per-leg costs,
   kernel ref + version, and the submit command.
