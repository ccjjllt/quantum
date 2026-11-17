# Sweep 01:01 UTC → 02:31 UTC + new-byte verdicts — 2026-11-17

Method: `kaggle kernels list -s {qcc,quantum} --sort-by dateRun` +
`kaggle datasets list -s {qcc,vqcc,quantum-circuit} --sort-by updated` at ~02:19 UTC;
downloaded every in-window kernel output (all <200 MB; sole exception is none —
largest zip 51.8 MB, members hashed in place). `sha256` every `.kmb`/`.npz` against
the known set `f2cdab0b`/`ccc2ab84`/`66b4f18b`/`00ac37d4`/`0af21cb8`/`5eeea23b`/`f425ea20`/
`b0983d55`/`61c8348d`/`957d6733`/`eea2d627`/`bdae290f`/`sub1`/`f6e12f02`/`703843d3`/
`0bd9c68f`/`a970f175`/`93326853`/`f05297b4`. Local work limited to sha256 + zip-listing +
log/audit reads, no simulation, no verifier runs. Nothing submitted.

## 1. Sweep table (window 2026-11-17 01:01 UTC → 02:31 UTC)

Byte-new files (not in the known set):

| file | kind | sha256 (full) | size | claimed score | source | verify status |
|---|---|---|---|---|---|
| `a73b25d2` | chem npz | `a73b25d27caec65dba2b0ad6c49b34afbdb234f4ef94f3b4ad0536dee0077f3` | 1,847,552 B | **294,643,137.73357135** (kernel-embedded official-verifier PASS, T 14706.0, lambda_eff 46.92171681802857, E_gap 3.9148980002646567); kernel-claimed GM **28.10134** w/ 0af21cb8+957d6733-1err | maoxin123 v27 kernel (02:04) + loaders kernel (02:16→~02:30, byte-identical sibling zip) | kernel-claim only (own official-verifier JSON in both logs); needs independent official-verifier run |
| 15 loaders `ed648708`…`b4a2d0ce` | chem angle kmb x15 | `ed6487084d30b0c772e8bd1109b56b501945d2bc708a343fd8bdf3551f3b7538` (k0, 180,436 B); `8e3a04e0e0450dbaa4725dc421708291ad4cec1522611e363936c90121885fbd` (k1, 151,084 B); `41069152b81cbd62f0f00d24990d69db58a5ef2bcee099c078c811b1ed4286a6` (k10, 131,074 B); `76c24260f8ec945e01de34ab8185f2ce0d7608f45da6f05101a47fb7136a9aca` (k11, 130,646 B); `e8ed58a46db6500c0b0f0b2d5b8dd674d965de268683343ab942e6235b672f7f` (k12, 130,613 B); `9e415e21dacce531c03d5c9322b5aa57f641ae7990b3426ad5574a6c1f9d93d8` (k13, 130,455 B); `fe94999841456f828d26c6b375d632f3b28f0f64def2a3bfffdc79873e3a928f` (k14, 130,774 B); `e620e957a4942bb9ddb1b246519d177f9de104ae27c95261a88bd9e7ed99303f` (k2, 135,545 B); `b1f4286282ab66463a4b7bd4513a7b3ecf67cdd8ede1bd86293169aa17cce76e` (k3, 134,697 B); `ee54d6f926f72276cd28439352b0d994bb77a3ed91b9d915291293192ceca07d` (k4, 130,825 B); `21b49673d23b09dbd3ad45e620cb799d54c64ebe5b4850bd17ac163a9b2a2856` (k5, 130,454 B); `1ae55a71e6877ce23c671df157a532b594694001a9623cc7315cc332306973e1` (k6, 129,631 B); `8ccf17b0113fb5451f64bd1df02dd8de262c7976f98fc8f621551a0430fbe8f0` (k7, 130,875 B); `0ace34e6eab90c9f2a0165671cca4dd1f4cc94e18f7d517a39c3156629234563` (k8, 130,222 B); `b4a2d0ce4bc3c5fa8055a4f386507bc7d35dccdcb68f5545cc7970843c85da71` (k9, 130,054 B) | 129,631–180,436 B each | same chem PASS as above (T 14706.0 vs standard 14712 — smaller loader family) | same two maoxin123 kernels (both zips byte-identical members) | kernel-claim only; needs independent official-verifier run |
| `4b350932` | DQI | `4b350932b03931af6040c871209da62aa0ebc74cfac3e77efcb6384e027285cc` | 486,993,377 B | **~3.4776e11** cost-model re-derived (static 369,418 toffoli-like, T_bar 368,540 recorded, R 1.191260, eps_plus floor 8.66e-4, 0 failures; contribution 70.2768; bundle GM **28.075**, LB 28.07504) | varianceofx cost-models bundle (01:08, `submission.zip` sha `82c037e3…`, 18 members) | model arithmetic only, NOT a verifier run; needs official-verifier run |
| `2c125b39` | invsqrt | `2c125b395e67dee4dcf9885f3817ff041571c234cb75e89d93eabb2f638ff` | 200,383 B | **75,082.09** re-derived (44Q, static 1531 toffoli-like, mean T 1456.26, contribution 27.6601) | same varianceofx bundle | model arithmetic only; needs official-verifier run |
| `6aa80150` | chem npz | `6aa80150cb568aa559ac2005da2d17cb443bcf1b844f8e45209b3a022a715` | 1,847,692 B | **294,762,980.62601334** re-derived (T 14712, contribution 11.3841) | same varianceofx bundle | model arithmetic only; needs official-verifier run |

Known-bytes-only (all members hashed, no new bytes):

| candidate | verdict |
|---|---|
| alexchilton `28-12-lb-which-circuits-survive-private-salt` (01:26 COMPLETE) | **No new bytes.** Salt-robustness study: invsqrt `0af21cb8` + DQI `f425ea20` + chem `93326853` + known 15 loaders. Kernel-embedded verifier PASSes: invsqrt 74797.36535717871, DQI 346992317312.81555 (= independently verified f425ea20 score), chem 294762512.64351326 (= verified 93326853), GM 28.1314. Circuits labeled boristown 28.13137 / yorixum 28.12102 in-log |
| asteriospanoras finer-chemistry-refit rerun (01:23 COMPLETE) | **No new bytes — but now downloadable.** Unlike the 23:41 run (receipt only), this run wrote `submission.zip` (51,158,866 B) to `/kaggle/working`. Members: `61c8348d` + `0af21cb8` + `f05297b4` + known 15 loaders. Kernel-embedded official-verifier JSONs all PASS (dqi **348004440260.464** 1/0 — the same lost-shot number as verify_new3's default-salt draw; chem 294762512.8596263; invsqrt 74797.36535717871; GM 28.10407). Refit converged to no-change again (`lambda_eff … -> …` identical) |
| maoxin123 `qcc-28-14-4-022-toffoli-chemistry-loaders` (02:16 RUNNING → COMPLETE ~02:30) | **No new bytes beyond the v27 sibling.** Output zip (51,101,767 B) is member-identical to the v27 zip: `957d6733` + `0af21cb8` + `a73b25d2` + the 15 new small loaders; same kernel-embedded PASS lines and GM 28.10134 |
| datasets `qcc`/`vqcc`/`quantum-circuit` | **No in-window datasets.** Newest are ratnachand `vqcc-verified-public-floor` (00:58:41) and medal-line tracker (00:30) — both pre-window |

Boundary note (outside mandate, for next sweep): `ratnachand/vqcc-verified-floor-and-circuit-anatomy`
kernel (COMPLETE 00:59:48) + dataset `ratnachand/vqcc-verified-public-floor` (updated 00:58:41)
fell in sweep3's window but after its ~00:53 listing, and are not covered in `RESULT_sweep3.md`.
Not downloaded/hashed here per the window mandate.

## 2. GM cross-checks (local arithmetic only; refs 2076774.233715 / 24439463583672.93 / 3355599588.3155375)

| combo | GM | vs claim |
|---|---|---|
| maoxin kernel claim (0af + 957d6733-1err + a73b25d2) | **28.10134372** (27.76534 / 70.17856 / 11.38869) | exact match to log `28.10134` |
| varianceofx recorded (75082.09 + 3.4776e11 + 294762980.63) | **28.07506193** (27.66005 / 70.27681 / 11.38406) | matches log `28.075` / LB 28.07504 |
| best-mix w/ new chem (0af + 61c8348d-clean + a73b25d2) | **28.15082863** (27.76534 / 70.54996 / 11.38869) | +0.00038 over the 28.14703 claim that used the 703843d3 leg |
| same legs w/ 703843d3 chem (ref) | 28.14702788 (27.76534 / 70.54996 / 11.38408) | = verify_new3 gate combo |

**Ranking notes:** the new maoxin chem `a73b25d2` (294,643,137.73, T 14706) beats `703843d3`
(294,762,512.86, T 14712) by ~119k (~0.04%) on kernel-embedded score; paired with the verified
`61c8348d` clean draw it gives GM 28.15083 on paper. The varianceofx triple (28.075) trails the
frontier. All four new files are claim-only (kernel-embedded PASS or cost-model arithmetic) —
verification is a separate task. No submission by this task.
