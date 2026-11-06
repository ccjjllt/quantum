# 2026-11-06：invsqrt 替换为 nofallback 候选（待授权提交）

## 改动

- 以 Maoxin V2（submission 58014726，Public 24.78590）的包为底，**只替换 invsqrt.kmb**：
  - 原：`0104d1b4…`（release 家族，静态 Toffoli 1537）
  - 新：`49009f89…`（`maoxin_v2_nofallback.kmb`，静态 Toffoli 1502，
    即已完成的"无回退选择器"迁移，省一个执行等效 Toffoli）
- DQI（`fd0ef09e…`）与化学（`dfthcsos/submission.npz` = `6c07f68a…`）字节不动。
- 包：`submission.zip`（28,305,830 bytes，18 成员）。

## 同 salt 官方验证（salt `nofb-a`，三任务完整 200M/102400/78080 shots）

| 任务 | 状态 | score |
|---|---|---|
| invsqrt（新） | **PASS** | **97,859.62870812711** |
| dqi | PASS | 375,360,087,497.74945（0 phase error，本 salt 抽到 0 错误） |
| dfthcsos | PASS | 304,305,834.2401413 |

同 salt 原 invsqrt（`0104d1b4`）：**PASS 97,921.61869825274**。
DQI/化学两包字节相同，同 salt 分数必然一致。

## 候选多 salt 复验（invsqrt nofallback）

| salt | score | 状态 |
|---|---|---|
| harv-a | 97,859.60266432124 | PASS |
| harv-b | 97,859.56542569333 | PASS |
| nofb-a | 97,859.62870812711 | PASS |
| nofb-b | 97,859.58092747658 | PASS |
| nofb-c | 97,859.59681579191 | PASS |

5 个 salt 全部 PASS，分数带宽 0.063；原电路在两个 salt 下 97,921.6156/97,921.6187。
差值稳定 **-62.0 分（-0.0633%）**，`toffoli_equivalent` 1578.38 vs 1579.38 =
**结构性少 1.0 个等效 Toffoli**（62×1），不是 seed 噪声。

## 预期 GM

- 单组件 -0.0633% ⇒ 三项几何均值约 **+0.0211%**：
  24.78590 → 约 **24.7911**（估计，按几何均值口径）。
- 实际以 Kaggle 评测为准；本记录不把估计写成实测。

## 状态

- **未提交**（按 AGENTS.md，Kaggle 提交需用户明确授权）。
- 证据：`verify_all.log`（三任务完整 JSON）、上述多 salt 输出、两电路 SHA-256。
