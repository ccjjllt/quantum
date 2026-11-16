# 2026-11-16 sub1 verification and intermediate submission

> **Later update (2026-11-16 10:00 UTC):** the bdae chemistry variant
> (`bdae290f`, cost 294,762,632.0817748) was independently verified in kernel v4:
> all three official verifiers PASS, 18/18 hashes, GM **28.0948753565**. It is
> **HELD, not submitted**, because it is still below the **>= 28.09490** gate and a
> later tie entry would worsen our in-plateau rank. See `RESULT_bdae.md` and
> `submission_receipt_bdae_hold.json`. The submission below (ref 58424363,
> 28.09486) remains our latest actual submission; two slots remain.


## Decision

The candidate is fully verified but sits **inside the 28.09486 plateau** (143 teams / ranks 88-230 at 09:06; now 185 teams / ranks 93-277), not above it.
The corrected 2026-11-16 rule is:

- silver cutoff rank 156 is inside the ranks 93-277 tie at public 28.09486;
- a new entry at 28.09486 is ordered last in the tie (~rank 278);
- submit only at expected GM **>= 28.09490**; the single 28.09487 entry at rank 92 is still below that gate, and the next score is 28.09498.

The pipeline correctly marked this candidate `HOLD_TIE`. Per the later user revision, **one**
intermediate submission slot was used for the verified package; it scored exactly **28.09486**,
confirming the tie placement, and the remaining daily slots are held for a later **>28.09490**
candidate.

## Exact verified result

| Task | Status | Official cost | Q | T | Other |
|---|---|---:|---:|---:|---|
| chemistry (`sub1`) | **PASS** | 294,762,697.43843937 | 427 | 14,712 | lambda_eff 46.92161275385757; error_1/error_2 0.0199999985; E_gap 3.9148980015 |
| DQI (`ccc2ab84`) | **PASS** | 347,375,470,571.73334 | 890 | 368,139.48973632813 | 102,400 shots; value_errors 0; phase_errors 0 |
| invsqrt (`f2cdab0b`) | **PASS** | 75,006.37653863191 | 44 | 1,464.1250896974009 | 200,540,928 shots; worst/tol 0.9995605646 |

Ratios: invsqrt 27.6879690708, DQI 70.3546037475, chemistry 11.3840713817.

**Geometric mean (default salt, this run): 28.094873280048187.**

This is below the required 28.09490 and is not a silver-crossing candidate on its own.

## Submission

| Item | Value |
|---|---|
| Competition | `google-verifiable-quantum-circuit-compilation` |
| Path | code competition: kernel `qingyu1232/qcc-frontier-28094-verify`, version **3**, output `submission.zip` |
| Ref | **58424363** |
| Submitted | 2026-11-16 09:06:57 UTC |
| Status | **COMPLETE** (09:34 UTC) |
| Public score | **28.09486** (exactly the plateau; bottom of the 143-team tie, not silver) |
| Previous best | ref 58420406, COMPLETE, public **28.09090** |
| Slots | `2 submissions remaining today` after this one |
| Readback | `kaggle competitions submission 58424363` -> COMPLETE, public 28.09486 |

The local `kaggle competitions submit -f submission.zip` upload path hangs on GCS for this
environment; the code-competition form `-k <kernel> -v 3 -f submission.zip` returns immediately
and uses the already-verified kernel output.

## Kaggle kernel history

| Version | Result | Notes |
|---|---|---|
| v1 | verifiers PASS, kernel ERROR | Post-verification receipt bug: `KeyError: 'dfthcsos'` while mapping scores; no zip. Exact JSON survived in `logs/`. |
| v2 | COMPLETE | Fixed mapping; all PASS; 18-file zip SHA-256 `0c07463c96b4e45b5ff9411416a097fd9c7e9c9f0afa580a2ffd98fcbe90f9cc`; receipt decision `SUBMIT` under the old 28.0930 threshold — **superseded**. |
| v3 | COMPLETE | Corrected tie policy; all PASS; 18-file zip SHA-256 `906f7d1f3c7d9cebeb5213d21ad49da1bd5e8bd5d0ff769ddd1649a1e94912d6`; receipt decision **HOLD_TIE**. This is the submitted kernel version. |

Kernel: <https://www.kaggle.com/code/qingyu1232/qcc-frontier-28094-verify>

## Package

`submission.zip` (v3, submitted):

- size **51,855,472 bytes**
- SHA-256 **906f7d1f3c7d9cebeb5213d21ad49da1bd5e8bd5d0ff769ddd1649a1e94912d6**
- exactly **18** members, no `._` / `__MACOSX` junk
- every member re-read from the zip and matched to its pinned SHA-256

The independent publisher rerun
`drpatrickchan/qcc-chem-refit-sub1-on-the-28-09-frontier` produced a real 18-member
51,855,472-byte zip (`29ea84185ad95a1b727fb70fcb6ac17e65f06e5ab84c45106e06c8c6559ce3c8`) whose
member content hashes are identical to this package. It reported the same three PASS results and
GM 28.09487. Our v1/v2/v3 kernels re-ran the unchanged official verifiers independently.

## Exact official JSON receipts

### chemistry

```json
{
  "status": "PASS",
  "score": 294762697.43843937,
  "lambda_eff": 46.92161275385757,
  "toffoli_count": 14712.0,
  "num_qubits": 427,
  "brot": 8,
  "batch_size": 5,
  "num_circuits": 15,
  "reaction_depth": 176,
  "num_ops": 606711,
  "verified_shots": 78080,
  "submission_sha256": "df130f1460df2779ab7d964f6ec76fb63e7e77bb34dfed1b8eb61570871e30a5",
  "resources": {
    "brot": 8,
    "keep_bits": 10,
    "angles_toffoli_per_pass": 4025.0,
    "angles_toffoli": 8050.0,
    "angles_qubits": 128,
    "angles_selection_qubits": 11,
    "angles_persistent_qubits": 40,
    "angles_temporary_qubits": 77,
    "outer_state_prep_toffoli": 317,
    "inner_state_prep_toffoli": 4095,
    "givens_rotations_toffoli": 2250,
    "outer_state_prep_persistent_qubits": 40,
    "outer_state_prep_temporary_qubits": 90,
    "outer_state_prep_qubits": 130,
    "inner_state_prep_persistent_qubits": 44,
    "inner_state_prep_temporary_qubits": 303,
    "inner_state_prep_qubits": 347,
    "heuristic_persistent_qubits": 84,
    "heuristic_temporary_qubits": 303,
    "heuristic_toffoli": 6662,
    "heuristic_qubits": 387,
    "persistent_qubits": 124,
    "temporary_qubits": 303,
    "toffoli": 14712.0,
    "qubits": 427,
    "angles_within_cap": true
  },
  "metrics": {
    "error_1": 0.01999999849999842,
    "error_2": 0.019999998500000008,
    "Lambda": 283.1445632727606,
    "E_SOS": -22144.1882480015,
    "E_gap": 3.9148980015015695,
    "lambda_eff": 46.92161275385757,
    "gap_in_domain": true
  }
}
```

### DQI

```json
{
  "status": "PASS",
  "score": 347375470571.73334,
  "m": 4095,
  "n": 70,
  "degree": 12,
  "r": 2016,
  "verified_shots": 102400,
  "value_errors": 0,
  "phase_errors": 0,
  "empirical_error_rate": 0.0,
  "effective_error_rate": 0.0008660587301657926,
  "log2_delta": -128.0,
  "repetition_factor": 1.1912604648115832,
  "mean_error_weight": 31.046737331746634,
  "toffoli_count": 368139.48973632813,
  "max_toffoli_count": 369010,
  "reaction_depth": 40597,
  "num_ops": 58416320,
  "shot_operation_counts": {
    "NEG": 101843,
    "BIT_INVERT": 597625417578,
    "BIT_STORE0": 287618328974,
    "BIT_STORE1": 3012327517,
    "X": 10998058392,
    "Z": 2393552455,
    "R": 4880335802,
    "HMR": 7321526052,
    "CX": 3082105368912,
    "CZ": 27334230150,
    "SWAP": 26694683833,
    "CCX": 37082916759,
    "CCZ": 614566990,
    "POP_CONDITION": 263798067200,
    "PUSH_CONDITION": 263798067200
  },
  "num_qubits": 890,
  "num_bits": 54075,
  "circuit_sha256": "ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d"
}
```

### invsqrt

```json
{
  "status": "PASS",
  "score": 75006.37653863191,
  "toffoli_equivalent": 1704.6903758779981,
  "toffoli_count": 1464.1250896974009,
  "max_toffoli_count": 1559,
  "t_count": 2.5000790611680026,
  "rotation_count": 33.0,
  "rotation_eps": 1.6406054738480745e-13,
  "num_qubits": 44,
  "reaction_depth": 1244,
  "num_ops": 20735,
  "verified_shots": 200540928,
  "worst_error_over_tolerance": 0.9995605646154175,
  "worst_x": 231,
  "circuit_sha256": "f2cdab0b7afc2e76aca12451113ef618e6f7e575a35a29f58264602dafb48726"
}
```

## Member SHA-256

The full 18-entry manifest is in `members.json` and `receipt_v3.json`. The three non-loader
members are:

| Member | SHA-256 | Bytes |
|---|---|---:|
| `invsqrt.kmb` | `f2cdab0b7afc2e76aca12451113ef618e6f7e575a35a29f58264602dafb48726` | 179,768 |
| `dqi.kmb` | `ccc2ab84ed713901c5642c58890fc664a16a4842c1ebdc80edb56b11c96d6c8d` | 486,988,897 |
| `dfthcsos/submission.npz` | `367d46e94230e1b7203ec975ec7583d02c3b5df83f9c185a9f8b4d82e1e145d2` | 1,847,692 |

The 15 `dfthcsos/angle_k_0..14.kmb` hashes are in the same two files. `sub1` differs from the
public frontier `f6e12f02` npz only in the `W` and `H2_I` arrays; all other arrays and all 15
loaders are byte-identical.

## Reusable command sequence

```bash
cd experiments/frontier/20261116_push/pipeline
python3 make_main.py

export KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token_qingyu1232)
~/.local/bin/kaggle kernels push -p .
~/.local/bin/kaggle kernels status qingyu1232/qcc-frontier-28094-verify

OUT=/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/pipeline_out
rm -rf "$OUT" && mkdir -p "$OUT"
~/.local/bin/kaggle kernels output qingyu1232/qcc-frontier-28094-verify -p "$OUT"
cat "$OUT/RUN_SUMMARY.json"
shasum -a 256 "$OUT/submission.zip"
```

Submit only if `RUN_SUMMARY.json` says `decision=SUBMIT` (all three PASS and GM >= 28.09490), then:

```bash
~/.local/bin/kaggle competitions submit \
  -c google-verifiable-quantum-circuit-compilation \
  -k qingyu1232/qcc-frontier-28094-verify -v <VERSION> \
  -f submission.zip -m "<description with Apache-2.0 credits>"
~/.local/bin/kaggle competitions submission <REF>
```

The pipeline refuses to create a submit-ready zip unless all three unchanged official verifiers
return PASS, and it writes `HOLD_TIE` rather than `SUBMIT` for 28.09486-28.09488.

## Next candidate gate

A later candidate must verify **GM >= 28.09490**. The best public chemistry in the 08:00-08:30
scan is boristown `bdae290f` at 294,762,632.08; with `f2cdab0b` + `ccc2ab84` that measured
**28.0948753565** in kernel v4. It is below the gate and may display 28.09486 or 28.09487; either
way it is not worth replacing our existing tie entry with a later submission. The next public
score is 28.09498; reaching it needs a component improvement (for example a chemistry lambda refit
at cost <= 294,762,300) not present in the public files scanned here. Do not spend another slot on
another 28.09486-28.09488 package.

## Attribution

Submission description and receipt preserve Apache-2.0 credits: Syed Asad Ali (original invsqrt and
DQI generator lines), Ali Haydar Özdağ (64-row table), Ertuğrul Özer, Asterios Panoras, James
Barlow, Leo Tang, Hayato Hikawa (C8 milestone), boristown (merge patches), Lera/marculera and the
c44 chemistry lineage, and Google Quantum AI / Qualtran (`kickmix`, official verifiers and task
definitions).
