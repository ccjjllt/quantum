# Lera (8,143,44) build 对照验证（2026-11-11）— PASS，建议替换 P0

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
只报实测；未提交 Kaggle、未推送、未改官方验证器/数据。

## 1. 来源与版本

- Kernel：`marculera/df-thc-11-2x-codes-on-the-xor-of-five-words`
  （"DF-THC 11.2x: Codes on the XOR of Five Words"，Lera，最后运行 2026-11-10 21:46:48 UTC）。
  `kernels output` 仅返回运行日志（`artifacts/20261111_lera11x/kernel.log`），无 build 文件。
- Dataset：`marculera/dfthc-c44-build`（"DF-THC 11.2x: (8, 143, 44) table and loaders"，
  apache-2.0，更新于 2026-11-10 21:46:25 UTC，与 kernel 运行时间吻合），
  `datasets download --unzip` 取到 `submission.npz` + 15 个 `angle_k_*.kmb`，
  字节原样落 `artifacts/20261111_lera11x/`（大文件不进 Git，SHA 见 §5）。
- 宣称（kernel 日志原文）：`(R,B,C)=(8,143,44)`，1220 words × 75 angles，8 bits；
  `error_1 11.258 mHa, error_2 19.9943 mHa`；`Lambda 283.1600, E_gap 3.915005, lambda_eff 46.9235`；
  `Toffolis per loader [297,292,292,292,270,269,269,270,270,267,268,268,268,268,269]`；
  `PASS: lambda_eff 46.9235 x Toffolis 14920 x qubits 427 = 2.989423e+08, 11.2249x`（78080 shots）。
- 与 P0 关系：独立分解。`U/W/H2_I/tree_edges/angle_words` 全部与 P0
 （`artifacts/20261110_p0_gauge/candidate/submission.npz`）逐字节不同；
  仅标量 `H1_I` 与 `Hsym_lower` 一致。不是 P0 的微调。

## 2. 静态复算（`static_check.py`，精确数 + shots=2/地址计量，未调 verify.py）

官方 `evaluate_words` / `recover_words_from_circuits` / `circuit_costs` /
`heuristic_costs(76, 8, 143, 44, 8)`，与 P0 `assemble.py` 同口径。
输出 `artifacts/20261111_lera11x/static_metrics.json`。

| 项 | P0（已验证） | Lera（本轮实测） | 说明 |
|---|---|---|---|
| error_1 | 0.02000000 Ha（门内余量 ~2.5e-11 Ha） | **0.011258105711178738 Ha = 11.258106 mHa** | 与宣称 11.258 一致；余量 8.74 mHa，宽松 |
| error_2 | 0.02000000 Ha（门内） | **0.01999434554579782 Ha = 19.994346 mHa** | 与宣称 19.9943 一致；门 0.02 Ha，余量 **5.65 μHa**，贴门但同口径下过门 |
| Lambda | 282.78107504162944 | **283.15998513444737** | 与宣称 283.16 一致 |
| E_gap | 3.914898000028188 | **3.9150047934163013** | > floor 3.914898，与宣称一致 |
| λeff | 46.891275349493 | **46.923534987015074** | 与宣称 46.9235 一致（+0.03226，不利项） |
| angles 单遍 static | 4148 | **4129** | per-loader 与宣称表逐项一致 |
| angles 双遍 sim_toffoli | 8296 | **8258** | −38 |
| heuristic Toffoli | 6662 | **6662** | 一致（317+4095+2250） |
| T | 14958 | **14920** | −38，全是 angles −38 |
| Q | 427（qmax 128, sel 11） | **427（qmax 128, sel 11）** | qubits_max/selection 一致 |
| words_match | True | **True** | loader 与字表匹配 |
| pred_score | 299497670.4814 | **298942333.6367** | **Δ = −555336.84（−0.185%）** |

口径结论：e1/e2 均为官方 `evaluate_words` 的 Ha 单位输出（×1000 即 mHa），
与 kernel 日志的 mHa 读数逐位吻合；e2 余量 5.65 μHa 是确定性算术余量
（shots 只检验 loader 字恢复，不参与误差门），P0 同口径下余量更小
（~2.5e-11 Ha）同样 PASS。贴门不构成否决项。

## 3. 官方验证范围（`scripts/manual_verify.py dfthcsos`，未改验证器）

- 小 shot：`--salt lera11x-small-20261111 -- --shots-per-address 2`（2440 shots），
  ~5 s，exit=0，**PASS**，score 298942333.6367（= 静态预测到小数点后 4 位）。
  日志 `artifacts/20261111_lera11x/verify_small.log`。
- 全量：`--salt lera11x-full-20261111`（默认 64/地址，`verified_shots=78080`），
  ~7 s，exit=0，**PASS**，score **298942333.6367**，
  `submission_sha256 590a27bc…be4b07c`，T=14920.0 / Q=427 / λeff=46.923534987015074。
  日志 `artifacts/20261111_lera11x/verify_full.log`。
- 未在其他 salt 下复核；排行榜 salt 与本地不同，但化学门部分是确定性计算，
  shots 只覆盖 loader 字恢复（已在 78080 shots 下通过）。

## 4. 是否建议替换 P0

**建议替换。** Lera build 经官方 78,080-shot 本地验证 PASS，
score 298,942,333.64，比 P0（299,497,670.48）低 555,336.84。
T −38 是纯 angles 收益（−38×427×46.9235 ≈ −761.7k），
被 λeff +0.0323 部分抵消（≈ +206.4k），净 −555k。
e1 反而比 P0 宽松得多（11.26 vs 20.00 mHa）；e2 余量 5.65 μHa，
确定性口径下过门，无采样噪声风险。

采用前置条件（main 仓治理侧执行，不在本工作区做）：
main 仓独立重跑一次全量验证并核对 `submission_sha256 590a27bc…` 后，
即可把 Lera build 定为新基线，P0 保留作回退。本工作区不组装 submission 包。

## 5. 文件与 SHA（`artifacts/20261111_lera11x/`，未进 Git）

- `submission.npz`: `79bc97e7da4e37ee196b6db6034faeffbbed0317adff098456fee784293d580b`
- `angle_k_0.kmb`: `37fef3606166dc3198ffc492cb80afc4bd9f1b3e6f94d3ee76cd6dd02208ff49`
- `angle_k_1.kmb`: `ece608d4e43aa284efe5d6e3e449ac434f94cdb714723d37e61f57d21264424b`
- `angle_k_2.kmb`: `5c4dbb1341e85dfc37f729dab24d2fb218c8066f16604ccf197f7c9d6bf9df3d`
- `angle_k_3.kmb`: `79fe9344c7844f83b5ed86ed4d4d3c5d66647b9fae15e01e74ff7f6cac676791`
- `angle_k_4.kmb`: `b7aa0974e9a0a99ec6dd4e2c6872e7ce3d02be0ebfb72dc6534f44e85b3e2764`
- `angle_k_5.kmb`: `0addeda1a53df66e10a8ca88cc9a8fb47b31993bf5a33cd55b40a3f7ac21c9c2`
- `angle_k_6.kmb`: `f908225069e7eca6d891570dfffc3321ededeb7b483fd70746e873a07a3d2a7f`
- `angle_k_7.kmb`: `302b9f2df17a8a63dbb7e909f586e9c24c1205d657f7c92327e79271f7a19d27`
- `angle_k_8.kmb`: `74b40540e01cb64259addd82affa4290d936c82e727e2319e56db3a27e5dcfa0`
- `angle_k_9.kmb`: `c9d692b4525d3d88eb7d99ee062d1d84bbc5785ca4b6dcf63df5bacd18f04452`
- `angle_k_10.kmb`: `dbe953792cfb4785c88ff72127a923d2bf68c6f3d041beb4853126e7ea18c89b`
- `angle_k_11.kmb`: `9cee6618570dddba72b58ef90fc8d42692dd3a9a9ec0fe742675c2c71d314957`
- `angle_k_12.kmb`: `d83cf4680008a3800f77064cd02da7ea254646ac793b63996e399fbfcc148e7b`
- `angle_k_13.kmb`: `4e78549ecca1a8c215c790f325931924bd3cb10f85f79ab4d5481b0ad0375ebe`
- `angle_k_14.kmb`: `72e5a8df32a8706219f6a4bdc01763338f6a5c492f50215a263d40540718c7b8`
- `kernel.log`: kernel 运行日志（宣称来源）；`static_metrics.json`: §2 全量实测；
  `verify_small.log` / `verify_full.log`: §3 两次官方验证原始输出。
- 本目录脚本：`static_check.py`（静态复算，可重跑）。
