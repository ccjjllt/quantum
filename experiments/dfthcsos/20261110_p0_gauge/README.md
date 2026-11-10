# P0：gengsr 规范翻转搬运到 b9eced3e（2026-11-10）— 成功

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
本轮不重复 W-only/LSB/训练（见 `CLOSED_RESEARCH.md` 与 `20261109_*` README），只做 gengsr 规范变换搬运。
**结果：成功。官方 78,080-shot 本地验证 PASS，score 299,497,670.48（−160,180.60 vs b9eced3e）。**

起点：
- `artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz`（b9eced3e，λeff 46.891275349493，T/Q=14966/427，score 299,657,851.08）
- 主仓库 `artifacts/20261110_gengsr_252268/release/dfthcsos/`（gengsr 字表+loader，只读引用；`references/public-baseline.json` v1）
- 基线 `artifacts/20261108_public_frontier/release/dfthcsos/submission.npz`（c1321df2，gengsr 的对照基线）

约束遵守：只写 `experiments/dfthcsos/20261110_p0_gauge/` + `artifacts/20261110_p0_gauge/`；
验证器只在候选组装后手动运行了一次；官方 data 未修改；未提交 Kaggle、未推送。

## 1. 翻转模式提取（精确算术，非 shots）

脚本 `extract_flips.py`：`reconstruct_u_vectors(words / 2**(brot-1), tree_edges)`（官方
`dfthc_math` 同款解码），行归一后内积。
- c1321 vs gengsr：917 行 +1，**303 行 −1**，偏差 ≤ 8.9e-16（复现 arch_review 的 303 翻转）。
- b9 与 c1321 的 `angle_words`/`U`/`tree_edges` 逐字节一致（已验证），同一 303 模式可原样搬运。
- 翻转行：one-body 18 行，two-body 285 行（`artifacts/20261110_p0_gauge/flip_rows.json`）。
  two-body 翻转行 gengsr `U` = −c1321 `U` 精确成立；非翻转 two-body 行 `U` 逐字节一致。
- 新字表 = gengsr `angle_words` 全表拷贝（= b9 字表 + 303 翻转行 + 382 行 don't-care 字变化；
  后者解码向量逐位一致，hybrid-vs-full 最大向量差 6.7e-16，属同一规范类）。
- 新 `U` = gengsr `U` 全表拷贝（= b9 `U` + 285 翻转行取反），`new_U.npy` 与 gengsr `U` 逐字节一致。

## 2. 新字表 metrics（官方 `evaluate_words`，精确数，非 shots）

`evaluate_words(b9_inputs, new_words, tree, brot=8)`（`word_metrics.json`）：

| 指标 | b9 基线 (b9w) | 新字表 (b9 权重 + 翻转字) | 门 |
|---|---|---|---|
| error_1 | 0.019999999974995186 | 0.01999999997499504 | ≤ 0.020 ✓ |
| error_2 | 0.019999999974999995 | 0.01999999997500000 | ≤ 0.020 ✓ |
| Lambda | 282.78107504162944 | 282.78107504162944（逐位一致） | > 49 ✓ |
| E_gap | 3.914898000028188 | 3.914898000028188（逐位一致） | > 3.914898 ✓ |
| λeff | 46.89127534949298 | 46.89127534949298（逐位一致） | — |

结论：规范对称预期成立，λeff 一字未动，门内。

## 3. Loader（关键偏离记录：未用 tensorqrom 重建，复用同字表 loader 并独立实测）

- 按任务字面用 `tensorqrom.build_family` 重建**失败**：当前字表是 unsigned 规范
  （761 行 `bit7≠bit6`），而 `tensorqrom.build_circuit` 断言 signed 规范
  （`rebuild_loaders.py` 运行留证：`AssertionError: signed gauge violated`）。
- 适配尝试（signed 重编码：`signed_words(new_U)` + one-body 刷新）同样失败：
  解码向量虽正确（1144/1144 行 |dot|>0.999），但破坏了精细误差抵消，
  `evaluate_words` 得 error_1 = 65.8 mHa、error_2 = **318.5 mHa**、λeff = 72.70，
  远出门（证据字表 `new_angle_words_signed.npy` 保留）。说明 refined unsigned 字
  不能经 naive signed 重编码保持门内——需重做 refine（属已 closed 的训练/量化轴，不做）。
- 处理：新字表与 gengsr 字表**逐字节一致**（已验证），故 gengsr 已发布的 15 个 loader
  即为该精确字表的正确 loader（loader 只与字表有关，与权重无关）。
  从主仓库只读拷贝字节至 `candidate/angle_k_*.kmb`（SHA 见 `candidate_manifest.json`），
  并用官方 `recover_words_from_circuits` 独立实测（shots=2/地址，固定种子）：
  **words_match=True，angles 8296.0（= 8296，−8 vs 8304，复现 −8T），static 4148，
  qubits_max 128**。`assemble.py` 输出 pred_score 299,497,670.48。

## 4. 组装与官方验证（一次 78,080-shot 本地验证）

- `candidate/submission.npz`：`W`/`H2_I`/`H1_I`/`Hsym_lower`/`tree_edges` 沿用 b9eced3e；
  `U`/`angle_words` 换成翻转表；15 loader 如上。npz SHA `79f790fab93c81ed…`（全值见 manifest）。
- `scripts/manual_verify.py dfthcsos artifacts/20261110_p0_gauge/candidate --salt p0-gauge-b9-20261110`
  输出见 `artifacts/20261110_p0_gauge/verify.log`：**PASS**，78,080 shots，
  submission_sha256 `103c790a…`：
  score **299,497,670.4814**，λeff 46.891275349493，T = 14958（angles 8296 + heuristic 6662），
  Q = 427。vs b9eced3e 299,657,851.0780：**−160,180.60**（= 8×427×46.891275349493，纯 T−8，
  λeff 未动）。与任务预期 ≈299,497,670 一致。

## 5. 交付物

- `artifacts/20261110_p0_gauge/`：`flip_rows.json`、`new_angle_words.npy`、`new_U.npy`、
  `word_metrics.json`、`new_angle_words_signed.npy`（失败路径证据）、
  `candidate/`（15 kmb + submission.npz）、`candidate_manifest.json`、`verify.log`。
- `experiments/dfthcsos/20261110_p0_gauge/`：本 README、`extract_flips.py`、
  `rebuild_loaders.py`（ gauge 失败留证脚本）、`assemble.py`。

## 验证范围声明

- 步骤 1–2 为精确算术（numpy Givens 解码 + 官方 `evaluate_words`），无 shots、无 `verify.py` 调用。
- 步骤 3 loader 计量为 shots=2/地址的 `recover_words_from_circuits`（纯成本计量，非 PASS）。
- 官方 78,080-shot 本地验证仅运行一次（salt `p0-gauge-b9-20261110`，`verify.log`），结论为 PASS；
  未在其他 salt/seed 下复核，未提交 Kaggle，未推送，未改官方验证器/数据与共享环境。
