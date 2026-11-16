# 2026-11-16 bdae chemistry verification — HOLD (not submitted)

## Verdict

**Verified, not submitted.** The bdae candidate is real and passes all three unchanged official
verifiers, but its measured GM is **28.0948753565**, below the only worth-submitting gate
**28.09490**. The 28.09486 plateau has grown to 185 teams (ranks 93-277); submitting another
28.09486-28.09487 entry later than our 09:06 submission would replace our tie entry with a later
timestamp and worsen our in-tie rank. **No bdae submission was made.**

## Candidate

| Task | File | SHA-256 | Q | Cost |
|---|---|---|---:|---:|
| invsqrt | `invsqrt.kmb` | `f2cdab0b7afc…b48726` | 44 | 75,006.37653863191 |
| DQI | `dqi.kmb` | `ccc2ab84ed71…d6c8d` | 890 | 347,375,470,571.73334 |
| chemistry | `dfthcsos/submission.npz` | `bdae290f5d6b…d935b` | 427 | 294,762,632.0817748 |
| chemistry loaders | `dfthcsos/angle_k_0..14.kmb` | same 15 hashes as sub1/frontier | — | T=14,712 |

`bdae290f` was extracted from the real boristown 18-member output
(`boristown/qcc-gap-3-residue-repair-and-c43-native-compiler`, 51,854,649 B), hash-asserted, and
mirrored privately as `qingyu1232/qcc-chem-bdae-weights` for the CPU kernel. Only `W` and `H2_I`
differ from the frontier `f6e12f02` npz.

## Official verifier results (default salt)

| Task | Status | Score | Q | T | Other |
|---|---|---:|---:|---:|---|
| chemistry | **PASS** | 294,762,632.0817748 | 427 | 14,712 | lambda_eff 46.92160235009843; error_1 0.019999998499997933; error_2 0.019999998500000022; E_gap 3.9148980015015695 |
| DQI | **PASS** | 347,375,470,571.73334 | 890 | 368,139.48973632813 | 102,400 shots; 0 value / 0 phase errors |
| invsqrt | **PASS** | 75,006.37653863191 | 44 | 1,464.1250896974009 | 200,540,928 shots; worst/tol 0.9995605646154175 |

**Measured GM: 28.0948753565** (still below 28.09490).

## Verification package

- Kernel: `qingyu1232/qcc-frontier-28094-verify` **v4**
- Status: **COMPLETE** (2026-11-16 09:56 UTC)
- Output `submission.zip`: **51,854,649 bytes**, SHA-256
  **`34b5f3c84125fe31e4261c2baa934a0b9ad12f32e4a690ae2afa1fdb9e562c28`**
- Exactly 18 members, no `._` / `__MACOSX`; every member hash re-read and asserted
- Local copy: `/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/pipeline_out_v4/submission.zip`
- Kernel receipt: `receipt_bdae_v4.json`; summary: `RUN_SUMMARY_bdae_v4.json`
- Machine-readable hold record: `submission_receipt_bdae_hold.json`

**Important:** v4's `receipt.json` says `decision=SUBMIT` because it was generated with the
temporary `>= 28.094870` exception for this attempt. That threshold is **superseded**. The current
pipeline gate is `>= 28.09490`; `receipt_bdae_v4.json` is verification evidence only and must not
be used to submit.

## Submission state

- No bdae submission ref exists.
- Latest actual submission remains **58424363, COMPLETE, public 28.09486** (sub1).
- Slots remaining: **2**.
- Do not spend another slot on a 28.09486-28.09487 package.

## Next gate

A later candidate must measure **GM >= 28.09490**. That requires roughly a chemistry
`lambda_eff` refit at cost **<= 294,762,300**, or a DQI/invsqrt improvement, not another
65-cost weight tweak. `main.py` now enforces the 28.09490 gate and writes `HOLD_TIE` below it.

## Attribution

bdae chemistry: boristown (team 暗黑AGI) Schur-nullspace reduced-gradient L-BFGS refit of the
marculera/Lera DF-THC (8,143,44) table and 15 XOR-of-five-word loaders (Apache-2.0), with upstream
maoxin123 chemistry. invsqrt: Syed Asad Ali generator line, Ali Haydar Özdağ 64-row table,
maoxin123 44Q schedule, Ertuğrul Özer and prior phase lineage. DQI: Syed Asad Ali decoder line,
Hayato Hikawa C8 retention, boristown/Kirill Tymchishin/Md. Hamid Hosen/James Barlow merge and
measurement work. Official `kickmix` and verifiers: Google Quantum AI / Qualtran.
