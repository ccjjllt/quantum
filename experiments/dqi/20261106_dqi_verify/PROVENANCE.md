# DQI 提交电路的真实来源与"稀有错误类"声明（2026-11-06，公开数据实证）

## 获取的公开证据

- 数据集 `busyaprime/33-qcc-v8-members`（公开，www API 直接下载，39.7MB）：
  含 dqi.kmb（hash fd0ef09e = 我们验证的电路）、15 个 angle、invsqrt、provenance.json、README。
- README/provenance 给出的 DQI 链条：
  - 提交电路 = **yoyobar V28 的 993c7038 基座 + busyaprime R41 精确乘积缓存**
    （-13.816 Toffolis/shot）；
  - 基座 = **Syed Asad Ali 的 891-qubit C1 解码器**（建立在 SomeJoint 的 kit 上），
    不是官方参考 EEA 解码器的编译产物；
  - 解码器算法 = **Schur 连分数解码器**（jday96314, GitHub QuantumAI, round 6）；
    官方参考实现则是 Proos-Zalka 同步 EEA——两者是**不同算法**，
    这解释了 CCX 密度差 16 倍（397k vs 5.73M）。
- **作者明确声明（Alex Chilton 公开 notebook 的 provenance 文本，原文）**：
  "syed3000 note that one rare error class is handled approximately, so the cost can
  rise a little under another salt (0 errors at the default salt here; 1 error in
  1 of 3 more salts we tried)"。
  ⇒ 我们在 shot 30178 上找到的 k=35 失败，正是这条**已知的"稀有错误类近似处理"**。

## 对既有结论的修正

- 之前把这归为"提交电路重综合 bug"不准确：它是**另一套算法（Schur）的已知近似分支**。
- 修复它不是打补丁，而是替换/改进 Syed 的 Schur 解码器——生成器不在公开 notebook 中
  （已拉取 SomeJoint chem-refit V34、yoyobar V28、syed3000×2、Alex Chilton 24-80 共 5 份
  公开源码，均无该解码器生成器；jday96314 的 GitHub 仓库已不可访问）。

## 尝试过的取证路径（均无效）

| 路径 | 结果 |
|---|---|
| 数据集 | 仅编译产物 + provenance，无生成器 |
| 5 份公开 notebook 源码 | invsqrt / chemistry 生成器有；DQI 解码器生成器无 |
| jday96314/QuantumAI GitHub | "Repository not found" |
| SomeJoint DQI notebook slugs | 404（已改名） |

## 判定

- DQI 精度路径的失败已**由其作者文档明确解释**（稀有错误类近似），不是未发现的 bug；
  修复需重写 Schur 解码器（算法级，无可及生成器）。
- 该近似最多值 ~0.41% 的分数（R 1.1967→1.1918），且作者已在多个 salt 上权衡过。
- 证据：
  - 公开数据集 `/T/qcc8/{README.md, provenance.json}`（含 "C1 decoder at 891 qubits" 链条）；
  - Alex Chilton 公开 notebook（`kaggle.com/code/alexchilton/24-80-lb-verified-three-task-portfolio`）
    的 provenance 文本，原文含 "one rare error class is handled approximately, so the cost
    can rise a little under another salt (0 errors at the default salt here; 1 error in 1 of
    3 more salts we tried)"，以及 Schur 解码器设计链条。
  - 我们复现的失败（shot 30178，k=35，确定性 256/256）与该声明一致。
