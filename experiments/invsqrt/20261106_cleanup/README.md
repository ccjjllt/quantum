# invsqrt 无收益研究归档（2026-11-06）

按用户要求：只保留有收益的研究方案、文档、脚本与 artifacts；其余无收益研究在
本文件汇总后删除相关文件。**本文件是删除内容的唯一权威记录**，逐文件清单位于
[`deleted_files.json`](deleted_files.json)（路径、字节数、SHA-256、原因、Git 状态）。

- 当前分支：`codex/invsqrt-research`（worktree `.worktree/invsqrt`），HEAD `60ee044`。
- 清理前工作区有 18 个未跟踪实验目录；`experiments/`、`artifacts/`、`submissions/`
  由 `.gitignore` 排除，删除不影响 Git 历史，但删除清单可追溯。
- 本轮**没有**任何候选通过完整验证并降低分数，因此保留的只有 2026-11-04/05 已确立的
  收益链，以及本次汇总文档本身。

## 1. 保留的收益链（唯一保留的研究方案）

| 阶段 | 相对上一阶段 | 完整验证 | 证据 |
|---|---|---|---|
| 公开 Kirill V5 基线 | — | 作者报告约 98,309.14 | `experiments/invsqrt/20261104_public_refresh/` |
| 无回退选择器迁移 | 精确 `262143/262144 C`（期望 −61.99976） | 作者报告约 98,247.14 | `experiments/invsqrt/20261104_public62_optimization/` |
| 跨 HMR 联合改写 | −2 C | 本机 PASS 98,123.1389 / 98,123.1073 | `experiments/invsqrt/20261104_reaudit/` |
| **Maoxin V2 + nofallback（当前最佳）** | 结构性 −1 等效 Toffoli（−62.0） | **本机 PASS 97,859.54615721264**；5 salt 复验 −62.0 稳定 | `experiments/invsqrt/20261105_maoxin_v2/` |

当前最佳电路：`artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb`
（SHA `49009f8930542d3bd120ee44b55c206126a7674ad4daf4937c0cbcac3d33b2e6`）。

基线完整验证（本机，`salt baseline-check`）：

```
score 97859.54615721264   toffoli_count 1280.6641365696682
t_count 11.499265082686762  rotation_count 41.0
rotation_eps 2.434041480874084e-13
worst_error_over_tolerance 0.9993237694056958 @ x=161
verified_shots 200540928  用时 95 s
```

该结果的收益已由 main 的 `submissions/20261106_nofallback_invsqrt/` 固化
（5 salt 全部 PASS，带宽 0.063，差值稳定 −62.0，不是 seed 噪声）。

## 2. 已关闭方向总表（本轮及此前，全部有验证或证明）

### 2.1 旋转层（有最优性证书）

| 方向 | 规模 | 结果 |
|---|---|---|
| 角度重调（LP） | 41 变量 × 全部 3,133,452 个 x，覆盖 55k 最紧约束 | LP 最优余量 = 基线余量（**1.00×**），无收益 |
| 删除任一旋转 | 41 个逐个固定 angle=0，其余自由 | 41/41 不可行；最接近 op 25823 仍差 0.07% 容差 |
| 新增 1 个旋转 | 22 个 x 比特模式 + 7 个梯形位置 × 62 条线，θ 精细扫描 | 最优 θ=0，余量 1.00×（回本线 2.35×），0 个候选 |
| 旋转合并/角度搬移 | 41 系数掩码两两比较（双 seed 验证分支无关） | 41/41 互不相同，0 重复组；`proto_anglemove` FAIL（x=1 −θ₂） |
| T 同线合并 | 93 个 Z_POW 全掩码分组 | 唯一重复组为 6 个 b418 恒零死门（零收益） |

### 2.2 Toffoli 层

| 方向 | 候选数 | 结果 |
|---|---|---|
| b25012 四门窗 | 9×span113 同构（4→3 穷举）+ 9×span128 | 8,160,768 候选 0 命中；span128 秩下界 LB=4 已证最优 |
| 主导块 16000–25800 同骨架 3→2 | 221 窗：21,249（删/换目标） | 1 幸存者，完整验证 FAIL（x=4，0.5 turns） |
| 同上：控制替换 | 219 窗：41,217 | **0 幸存者** |
| 同上：3→1 双删 | 669 | **0 幸存者** |
| 同上：混合三连（CCZ/CSWAP） | 8 窗：1,518 | 493 幸存 → 176 结构非法 / 284 对角 / 33 有效；5 代表 + 33/33 全部 FAIL |
| 尾区 `[48100,50077)` 单删 | 96 | **96/96 FAIL**（±0.5 turns） |
| 全电路剩余计费门单删 | 941（CCX 718 / CSWAP 141 / CCZ 82） | FAIL 903 / PASS 38；38 个 PASS **全部从不执行**（3 分支 × 256 x 计数验证） |
| 自逆计费门对 | 706 同门同守卫；1,115 对精确 `U·M·U = M` 检验 | **0 对可对消** |
| compute/uncompute（目标仅相位使用） | 全部 CCX 对 | **0 对** |
| 常量控制门删除 | 零分支 116，16 分支后 88 | 88 全删 FAIL；死帧 34 门删除 PASS 但本不计费（score 反升） |
| 共享部分积（CCX 乘积 = 已有线） | 16 | 16/16 FAIL（依赖测量分支） |
| 「算完即被 HMR/R 丢弃」的 CCX | 19 | 全部在丢弃前有相位用途，不可删 |
| 对角门等效掩码分组 | 15,107 个 CCZ/CZ/Z | 39 组 SAFE 全是免费门（18 CZ + 21 Z），0 个 CCZ；代表原型 FAIL |

### 2.3 T 成本侧

- 计费口径实测：执行的 CCX/CCZ/CSWAP = 4.0 C；T 类 Z_POW = 1.0 C；HMR/R/X/CX/CZ/
  Clifford-Z_POW 免费。基线 `t_base = 11.499` ≈ 每 shot 2.87 个 T 门。
- 28 个 T 类 Z_POW 逐个删除：**22 FAIL**（干净 ±0.125 turns 签名）、6 PASS 全为 b418
  恒零死门（零收益）。

### 2.4 Q（比特数）

- 62 个比特全部被门触及，无「只作控制从不被写」的比特。
- 保守区间模型峰值 = 62；按 HMR 切分（950 段，659 个 scratch 段）峰值仍 = 62
  （op 3428 处 62 线同时活跃）。Q 无法通过并线降低。

### 2.5 替代算术重设计（预算证伪）

- 成本规则：`score = Q × (toffoli + t/4)`，基线 `C = 1578.380`。
- R=24 个旋转时 toffoli 预算仅 **1405.8**；即使按 5.3 T/rot 下限也只有 1546.6。
- n=24 Newton（每轮 3 次乘法）3–4 轮：schoolbook 5,284–7,012 ANDs；
  Karatsuba 3 层 2,287–3,016 ANDs（均未含反计算、LUT、修正网络）。
- 结论：该家族在门数量级上不可能低于 1,280.66，不是实现工作量问题。

### 2.6 并行会话遗留的其他批次（2026-11-06，全部 null）

| 实验 | 规模 | 结果 |
|---|---|---|
| 5 线小窗批量（`20261106_batch_small`） | 10 窗，同骨架 + 全 `+1CX` | 全 null |
| 5 线 CSWAP + 7 线批量（`batch_cswap` / `batch_cswap2`） | 13 + 5 + 3 窗 | 全 null |
| 9–10 线（`batch_910`） | 10 窗 | 约 1,200 万候选，全 null |
| 11–12 线 + 大窗（`batch_big`） | 4 + 6 窗 | 25,722,840 + 3,989,184，全 null |
| 大窗链式受限 `+1CX`（`batch_chainbig`） | 6 窗（14–26 线） | 68,225,184，全 null |
| `[21764]` +1CX / Z3 | 2 对 + Z3 秩证明 | 约 253 万 null；Z3 UNKNOWN（记 NOT_PROVEN） |
| `[25495]` / `[25750]` / `[25779]` / `[38187]` | 7 线全量 + 链式受限 | 约 48 万 / 128 万 / 750 万，全 null |
| 块级精确重综合（`block_resynth`） | 三类 coin 无关改写 | 全部关闭；同签名门对 1,206 对，严格对易后 0 对可用 |
| T 类单删收割（`tclass_harvest`） | 6 PASS 复核 | 全部零收益（恒零帧） |
| 收益方向复核（`gain_review`） | 只读成本结构分析 | 确认 81.15% Toffoli / 18.67% 旋转 / 0.18% T |

累计窗口级候选（可复算部分）：约 **1.35 亿**，零可通过候选。

## 3. 四条可复用判据（本次研究最有价值的产出）

1. **score 噪声地板 ≈ 0.05 C**。同一候选电路换 salt：`32060` 删除得
   97859.57599933 / 97859.60281125 / 97859.62075852；`32041` 删除得
   97859.58781750 / 97859.64466059 / 97859.59141400；基线单次 97859.54615721264。
   → 任何 `|Δscore| < 0.1 C` 的「改善」都是读数噪声；真实收益下限 = 1 个计费门（4 C）
   或 1 个旋转（7.19 C）。
2. **coin 分支依赖**。HMR 含 Hadamard，是真随机测量；`salt` 改变硬币位，后续条件门
   使总相位确定。零分支/固定 seed 的经典仿真**不等于**验证器分支：
   `seed 101/303/404` 的 `b7917` 分别为 `[F,T,T,F,T,F,F]`、`[F,T,F,F,T,F,F]`、
   `[T,F,T,T,T,F,F]`，而 `phase@x5` 逐位相同。
   → 任何「掩码相等」类静态结论必须用完整验证器仲裁；旋转系数掩码是例外
   （41×5164 在 seed 101/202 下 0 差异，且与 verifier worst@x161 逐位一致）。
3. **LP 最优性证书**。旋转层已用覆盖全部 3,133,452 个 x 的 LP 证明最大余量最优，
   且删/增/合并均不可行——该层不必再试。
4. **单删全覆盖**。1,502/1,502 个计费门已逐个删除并用完整验证器仲裁；
   今后若再出现「某个门可能多余」的猜测，直接引用本结论，不重复测试。

## 4. 保留与删除的边界

保留（有收益或为收益链复现所必需）：

- `experiments/invsqrt/20261105_maoxin_v2/`、`20261104_reaudit/`、
  `20261104_public62_optimization/`、`20261104_public_refresh/`、
  `20261103_one_ccx/`、`20261104_stage1_nofallback/`、`20261104_cleanup/`、
  `experiments/invsqrt/README.md`；
- `artifacts/20261105_maoxin_v2/`（基线 + nofallback KMB + 审计）、
  `artifacts/20261104_reaudit/`、`artifacts/20261104_public62_optimization/`、
  `artifacts/20261104_stage1_nofallback/`、`artifacts/20261103_one_ccx/`、
  `artifacts/20261102_hw06_opt/`（`baseline_hw06.kmb` 被保留文档引用）、
  `artifacts/20261104_cleanup/`；
- `scripts/manual_verify.py`、`scripts/inspect_circuit.py`、`scripts/package_submission.py`；
- main 的 `submissions/` 回执与提交包。

删除（无收益；结论全部在本文件与附录中）：

- 实验目录：`20261105_rotlp`、`20261105_shared_target`、`20261105_w15395`、
  `20261105_gain_review`、`20261106_*`（13 个批量/窗口/普查/重综合目录）；
- artifacts：`20261105_rotlp`（96 MB）、`20261105_w15395`（4.8 MB）、
  `20261106_*`、`20261105_shortcache`、`20261105_crosshmr_synth`、
  `20261031_invsqrt62_replay`、`20261102_generator_v2`、
  `20261102_baseline_patch`、`20261103_baseline_patch_round2`、
  空目录 `20261030_public_audit`/`20261030_public_best`/`20261101_public_hw06`/
  `20261104_public_refresh`/`20261104_submission_refresh`。

附录（保留在本目录）：

- `DETAILED_rotation_lp_and_full_single_delete.md`：旋转 LP 证书、全域相位模型、
  全电路单删的完整证据（原 `20261105_rotlp/README.md`，23 KB）。
- `TESTED_WINDOWS.md`：已测窗口登记表（原 `20261105_shared_target/TESTED_WINDOWS.md`），
  防止未来重复测试同一窗口。
- `evidence/`（284 KB）：搜索/仲裁脚本与结果 JSON（`skel_search2/3/4.py`、`scan_all.py`、
  `arb_mixed.py`、`arb_compute.py`、`diag_groups.py`、`test_tail.py`、
  `scan_results.json`（941 单删）、`tail_results.json`（96 单删）、
  `tclass_results.json`、两份 sweep 日志）。这些是本文档结论的复现路径；
  原始 96 MB 掩码/相位数组已删除，结论与参数在 DETAILED 文档中。
- `run_cleanup.py`：本次删除脚本（保留以便审计与复用）。
- `deleted_files.json`：删除账本。

## 5. 删除账本与可追溯性（诚实说明）

- 删除 **42 个目录、约 124 MB**（`du -sh` 删除前测量，逐目录大小见账本
  `deleted_total_bytes_approx = 129,901,361` 字节）。
- **一个限制**：`run_cleanup.py` 在删完目录、遍历到 main 自有的符号链接
  （`artifacts/20261030_*` 等）时中止，账本未能在删除前落盘。因此被删目录的
  **逐文件 SHA-256 未能记录**；账本中以 `bytes_observed_before_deletion` 和
  `size_text` 保留删除前的目录大小，并明确标注
  `per_file_sha256 = "not captured (...)"`。这是一次性操作失误，已在账本和此处写明，
  不假装拥有不存在的哈希。
- 仍可校验的内容：保留的收益链 artifacts（含 `maoxin_v2_nofallback.kmb`）与
  `evidence/` 全部 18 个文件已在账本中记录 SHA-256。
- main 自有的 5 个符号链接（`20261030_public_audit`、`20261030_public_best`、
  `20261101_public_hw06`、`20261104_public_refresh`、`20261104_submission_refresh`）
  **未删除**：它们指向 main 的 artifacts，属于 main 治理范围，删除会连带 main；
  在本 worktree 中它们只占 0 字节。
- 同目录的 `experiments/invsqrt/CLOSED_RESEARCH.md`（2026-11-06 08:54，由并行会话写入）
  未改动，作为简版索引保留；本目录 README 是本次清理的权威记录。
