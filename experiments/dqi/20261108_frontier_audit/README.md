# Public Frontier DQI (`4432ec5f`)：阶段级精确差分、演化谱系与下一步降本方向

日期：2026-11-08（北京时间）；分支 `codex/dqi-research`。
固定输入为主仓库下载的 Public Frontier 25.14222 `dqi.kmb`（SHA-256 `4432ec5fd63d7d70aab92d32f719d47539d0ff66ae0cb0b964c914e01fece431`，892Q，58,287,028 操作，395,641 静态 Toffoli-like，默认 salt 官方验证成本 `374,735,446,628.53`），本工作区只读链接 `artifacts/20261108_public_frontier/release/dqi.kmb`。

## 1. 相比 Syed V9 (`1ab3ac53`) 的精确阶段统计与 −38 门演化拆解

在 [`audit_frontier_4432ec5f.py`](audit_frontier_4432ec5f.py) 中，我们对 Syed V9（`1ab3ac53`）与 Public Frontier（`4432ec5f`）的全部 5,828 万条指令按原生 `SEMANTIC` 阶段标记进行了精确逐门统计（结果保存在 `artifacts/20261108_public_frontier/audit_summary.json`）：

| 阶段 (`SEMANTIC`) | Syed V9 静态 Toffoli-like | Public Frontier (`4432ec5f`) | $\Delta\text{Toffoli-like}$ | 门类细分变化 ($\Delta\text{CCX} / \Delta\text{CCZ} / \Delta\text{CSWAP}$) |
|---|---:|---:|---:|---|
| `convert` | 60,687 | 60,687 | 0 | $0 / 0 / 0$（56,095 CCX, 4,592 CSWAP） |
| `extract` | 59,169 | 59,169 | 0 | $0 / 0 / 0$（58,977 CCX, 192 CSWAP） |
| `scan` | 44,275 | 44,275 | 0 | $0 / 0 / 0$（44,275 CCX） |
| `synthesis` | 31,635 | 31,635 | 0 | $0 / 0 / 0$（31,611 CCX, 24 CSWAP） |
| `unconvert` | 62,558 | 62,558 | 0 | $0 / 0 / 0$（56,794 CCX, 72 CCZ, 5,692 CSWAP） |
| `unextract` | 96,903 | **96,888** | **−15** | **−15 CCX** $/ 0 / 0$（94,309 CCX, 1,043 CCZ, 1,536 CSWAP） |
| `unsynthesis` | 40,452 | **40,429** | **−23** | **−21 CCX, −2 CCZ** $/ 0$（40,143 CCX, 262 CCZ, 24 CSWAP） |
| **总计 (892Q)** | **395,679** | **395,641** | **−38** | **−36 CCX, −2 CCZ, 0 CSWAP** |

结合公开前沿源码链（保存在 `artifacts/20261108_public_frontier/source/`），这 **−38 个静态 Toffoli-like 门**完整由以下三步改写构成：

1. **Ozer V5 (`77bace9d`, −21 门)**：
   - 合并 Atakan 发现的 17 处保留乘积复用（retained-product reuses）与 MAIDANG 在 `unextract` / `unsynthesis` 中重建的 4 条算术链，静态付费门从 `395,679` 降至 `395,658`。
2. **Kirill V21 (`337cb049`, −14 门)**：
   - 应用测量顺序窥孔恒等式 `CCX a b t; HMR t m` $\Longleftrightarrow$ `HMR t m; CZ a b if m`。
   - 我们的全电路逆向活度扫描验证：Syed V9 中恰好存在 **14 处**紧邻 `HMR/R` 且目标线未被读取的无条件 `CCX`（`unread_ccx_before_hmr = 14`），而在 `4432ec5f` 中已全部消除为 **0 处**（`unread_ccx_before_hmr = 0`），静态付费门降至 `395,644`。
3. **Isabe11aM00re V12 (`4432ec5f`, −3 门)**：
   - 在 `unsynthesis` 与 `unextract` 的 6 个局部窗口中，将 3 处重复计算的二次布尔乘积缓存到整个窗口周期内闲置且已通过 `HMR` 清零的辅助线上，静态付费门降至 `395,641`（默认 salt 官方成本 `374,735,446,628.53`）。

## 2. 平行公开前沿分支：Syed V10/V11 与 Prvsiyan V32 的关键启示

在本次 MCP 调研中，我们同时获取了 `syed3000/vqcc-own-circuit-portfolio-notebook` (V11) 与 `prvsiyan/25-076-lb-verified-three-task-portfolio` (V32) 的完整技术报告（见 `artifacts/20261108_public_frontier/source/syed_v11_info.json` 与 `prvsiyan_v32_info.json`），揭示了两个重要事实：

1. **仿射规范化函数级乘积缓存（Functional Product Caching）在 `unextract` / `unsynthesis` 仍未枯竭**：
   - `Isabe11aM00re V12` 只匹配了字面控制线对 $(a, b)$ 相同的 `CCX`，仅找到 3 处缓存（−3 门）。
   - 而 Syed V10 在同源 892Q 解码器上，通过追踪每段无测量区间内各量子线关于段入口基的**精确仿射布尔表达式**，将“同一布尔乘积被计算 $\ge 2$ 次”且区间内存在空闲 `HMR` 归零线的位点全部替换为 `CX` 拷贝 + 测量前 `HMR` + 条件 `CZ` 相位纠错，一次性消除了 **48 个 Toffoli 门**（加上 14 处测量窥孔共 **−62 门**，空 salt 成本达 `374,712,921,286`）。
2. **Weight-17 极点修复与 Private LB 独立抽样对冲（Shot-Noise Hedging）**：
   - DQI 官方评分使用 102,400 shots，每次失败 shot 对惩罚因子 $R$ 的边际成本约为总分 $+0.038\%$，折合 **约 1,808 个平均 Toffoli 门**（远大于几十个门的静态窥孔收益）。
   - Syed V11 通过保留极点阶数标志并在反向清理段对称反计算（净增 `+175` 个 Toffoli，静态 `395,792` 门），消除了 `weight-17` 解码退化，在 72 组随机种子（共 $7.37 \times 10^6$ shots）中将失败次数从 27 次降至 21 次，跨种子几何平均优于未修复版本。
   - 同时，由于 `verify.py` 的测量与输入抽样种子由 `SHA256(dqi.kmb) + salt` 决定，不同队伍若提交字节完全相同的 `dqi.kmb`，在 Private LB 上将共享完全相同的随机抽样轨迹。

## 3. 下一步降低 DQI 成本与提高分数的具体方向

1. **在 `4432ec5f` 上实施全电路仿射规范化乘积缓存（预计净省 35–45 个静态 Toffoli，即约 $2.8 \times 10^7 \sim 3.6 \times 10^7$ 成本）**：
   - 编写流式 $\mathbb{F}_2$ 仿射符号追踪器扫描 `4432ec5f` 的 `unextract`（96,888 门）与 `unsynthesis`（40,429 门）：对每个 `CCX a b t`，用段内 `X/CX/SWAP` 历史将控制线 $(q_a, q_b)$ 还原为段入口规范基下的无序对 $\{\ell_1, \ell_2\}$；当同一规范对在同一空闲辅助线（由前序 `HMR` 清零、直至下次写入前未引用）生命周期内重复出现时，在首次计算后 `CX` 备份至该空闲线，后续出现直接用 `CX` 异或替代 `CCX`，并在释放该空闲线时用 `HMR` + 条件 `CZ` 归零。
2. **定位并按概率定价修复 `w=17` 极点标志退化**：
   - 对照 Syed V9/Frontier 的 `extract`/`unextract` 第 16–17 步极点更新核，定位未保留的 pole-17 标志位，评估能否复用 `unextract` 现有的闲置区间载体线在不增加 892Q 峰值宽度的前提下完成对称反计算。
3. **最终双提交的 DQI 字节哈希分散化（Private LB 对冲策略）**：
   - 在比赛最终选择的两个 Submission 中，确保两份提交包使用**不同字节哈希**的优质 `dqi.kmb`（例如一份使用经仿射乘积缓存优化的候选，另一份使用不同零代价门序或带 `w17` 保护的候选），从而在 Private LB 上获得两次独立的 102,400-shot 伯努利抽样机会，对冲单次稀有错误波动（单次 shot 波动价值 $\approx 1,808$ Toffolis）。

## 4. 手动复现命令

```bash
/Users/zhaohuaxiang/ccjjllt/quantum/.venv/bin/python \
  experiments/dqi/20261108_frontier_audit/audit_frontier_4432ec5f.py
```
