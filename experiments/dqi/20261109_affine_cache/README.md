# DQI 仿射规范化乘积缓存（`4432ec5f` 降本实验）— closed，无收益

日期：2026-11-09；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
固定基线：主仓库 Public Frontier 25.14222 `dqi.kmb`
（SHA-256 `4432ec5fd63d7d70aab92d32f719d47539d0ff66ae0cb0b964c914e01fece431`，
892Q，58,287,028 ops，395,641 静态 Toffoli-like，默认 salt 官方成本
`374,735,446,628.53`），本工作区只读链接
`artifacts/20261108_public_frontier/release/dqi.kmb`。

## 结论（先行）

1. **仿射规范化乘积缓存：在 `4432ec5f` 上无净收益，closed。**
   精确 F2 仿射跟踪（段入口基 + 计算/反计算配对 + 常量乘积）显示，`unextract` +
   `unsynthesis` 的 135,369 个 `CCX`/`CCZ` 位点中，仅 **141 个**的双控制线保持仿射
   干净，且 **141 个规范键全部互不相同**（严格键与互补折叠 mask-only 键均为 141 distinct，
   0 重复）。前人（Ozer −21、Kirill −14、Isabe11a −3）已取尽字面复用；字面之外的规范对
   匹配空间为**空**。预测净省 **0 门**。未生成候选电路，未触碰基线字节哈希。
2. **`w=17` 极点修复：期望净收益为负，closed，不实施。**
   按官方计分公式重算：单失败 shot 边际成本为 **+1,722,266,847（+0.459%，≈1817 平均
   Toffoli 单位）**，不是此前记录的 +0.038%（百分率有误，Toffoli 单位数基本一致）。
   Syed V11 修复（保留 node-9 极点标志 + fold-18 零标志，+175 静态 Toffoli ≈ +1.659e8）
   的期望收益为 (27−21)/72 × 1.722e9 ≈ +1.435e8，**净 −2.2e7（≈ −24 Toffoli 单位），
   标准误 ±1.66e8（≈ ±175 单位）**——统计上与零无异、点估计为负。同时 `unextract`
   载体线压力为 52/52（29 个 200k 行窗口中 26 个全忙），对称反计算无闲置载体可用。
3. **Private LB 对冲**：本次无候选产出，字节哈希保持 `4432ec5f` 不变；对冲需等待未来
   成功降本的候选。

## 1. 假设与方法

沿 `experiments/dqi/20261108_frontier_audit/README.md` §3 的方向 1：
编写流式 F2 仿射符号追踪，扫描 `4432ec5f` 的 `unextract`（96,888 门）与 `unsynthesis`
（40,429 门）。对每个无条件 `CCX a b t`，用段内 `X/CX/SWAP` 历史把控制线还原为段入口
规范基下的无序对 `{l1, l2}`；同一规范对在同一空闲辅助线（前序 `HMR` 清零、窗口内无引用）
生命周期内重复出现时，首次计算后 `CX` 备份，后续用 `CX` 异或代替 `CCX`，释放时
`HMR` + 条件 `CZ` 归零。对照 Syed V10 一次 −62 门的思路（14 测量窥孔 + 48 函数级缓存），
但 basline 已含 −14 窥孔，本实验只做字面之外的规范对匹配。

实现：`experiments/dqi/20261109_affine_cache/affine_clean.py`
（单遍，~4 分钟），输出 `artifacts/20261109_affine_cache/affine_groups.json`。
跟踪规则（全部构造性精确，无采样）：

- 基：unsynthesis 入口 892 符号变量（Python int 位掩码）。
- `X/CX/SWAP`（无条件、无栈）：仿射更新；条件化（条件栈/内联 `if`）则脏化值目标。
- `HMR/R`（无条件、无栈）： καθαρός 0 并记录归零事件；否则脏化。
- `CCX`（无条件、无栈）：双控制干净才记录位点；目标按**精确计算/反计算配对**处理
  （同无序控制对 + 同目标、无中间值写 → 恢复配对前快照；`a==b` 退化为线性 `CX`；
  常量乘积保持仿射；其余脏化；`t∈{a,b}` 永不配对）。`CCZ/CZ/Z` 对角无值写；
  `CSWAP` 脏化被换线。
- 分组键：排序后的 `((mask_a,const_a),(mask_b,const_b))`（严格）与 mask-only（互补折叠）。
- 可行性：缓存线须在 `(L1,Lk)` 内零出现（occ 表）、`L1` 前最后一次触碰为无条件
  `HMR/R` 归零、与成员线相异、预留区间不交叠；贪心分配。

复用模板（与 frontier 内已验证的 Isabe11a/Kirill 改写同构）：
`L1: CCX a1 b1 t1 → CCX a1 b1 w; CX w t1`；
`Li: CCX ai bi ti → CX w ti`（每处 −1）；
末端 `HMR w m; CZ ak bk if m`。每组净 `−(k−1)`。

## 2. 阶段级门数差分表（基线 `4432ec5f` 自身普查，复用审计结论）

| 阶段 | 静态 Toffoli-like | CCX | CCZ | CSWAP |
|---|---|---|---|---|
| extract | 59,169 | 58,977 | 0 | 192 |
| synthesis | 31,635 | 31,611 | 0 | 24 |
| convert | 60,687 | 56,095 | 0 | 4,592 |
| scan | 44,275 | 44,275 | 0 | 0 |
| unconvert | 62,558 | 56,794 | 72 | 5,692 |
| unextract | 96,888 | 94,309 | 1,043 | 1,536 |
| unsynthesis | 40,429 | 40,143 | 262 | 24 |
| **总计** | **395,641** | **382,204** | **1,377** | **12,060** |

`unextract` + `unsynthesis` 候选位点：`CCX` 94,309 + 40,143（无内联条件），
`CCZ` 1,043 + 262；其中条件栈下 353 `CCX` + 35 `CCZ`（仅 unextract，需条件化缓存，
本次排除）。

## 3. 静态统计（本实验新测）

- 目标阶段 `CCX`/`CCZ` 位点总数：**135,369**；无条件栈外干净双控制位点：**141**；
  其余 135k+ 位点至少一控制为非线性（深度 GF 算术）。
- 严格规范键 distinct：**141**；重复组：**0**。mask-only distinct：**141**；重复组：**0**。
- unextract 末仍仿射线：39/892。计算/反计算精确配对触发 **0**（两阶段内无反向 CCX 对，
  擦除全系测量式——与 Kirill/Isabe11a 改写形态一致），常量乘积 **0**。
- 141 个干净位点明细：`artifacts/20261109_affine_cache/affine_clean_sites.json`。
- 可行缓存组：**0**；预测净省：**0 门**。
- 载体线压力（独立 200k 行窗口普查）：unextract 29 窗口中 26 个 52/52 全忙，
  仅 3 个早期窗口各有 28 条闲置线——与“前人仅找到 ~6 个窗口”的事实一致，
  说明瓶颈在载体线而非匹配。

## 4. 默认 salt 下的成本评估

- 无候选 → 静态 395,641 不变；默认 salt 官方成本保持 `374,735,446,628.53`（未重跑，
  无变化故无需重跑）。
- 参考：2048-shot 本地基线（`artifacts/20261109_affine_cache/baseline_2048shot.json`，
  官方验证器手动运行）：PASS，value=0/phase=0，平均执行 T=395,356.94（静态 395,641，
  差 284 来自条件跳过），`reaction_depth=45619`。
- 单失败 shot 边际成本（n=102400, δ=2^-128，按官方 `R(eps)`/`clopper_pearson_upper_bound`
  重算）：eps+(0)=8.6606e-4→R=1.19126046；eps+(1)=9.1042e-4→R=1.19673150；
  **Δ=+1,722,266,847 = +0.459% ≈ 1817 平均 Toffoli 单位**（纠正审计 README 的 +0.038%；
  原 1808 单位数基本一致）。

## 5. w=17 极点分析

- 结构：extract 含 inverse12×25 + inverse24×23 + multiply v×6 的前向链，
  4331 处 pole-flag 式 `HMR`（flag carry：前向 X-测量、后向重建、CZ 偿还）；
  unextract 为窄返回（inverse12×2 + gf_iadd×140），不与前向逐节点镜像——前沿已做
  激进 flag 消除（Syed：902→891 宽，node-3 无 flag 保留链）。
- Syed V11 参考修复：保留 chain node-9 pole flag + fold-18 zero flag，
  静态 **+175 Toffoli**（395,792），72 配对种子（7.37M shots）失败 27→21。
- 定价：成本 +175×947,843 ≈ **+1.659e8（+0.044%）**确定支出；
  期望收益 (6/72)×1.722e9 ≈ **+1.435e8**；净 **−2.2e7 ≈ −24 单位 ±175**。
  差异 <1σ，点估计为负 → **不实施**。
- 载体复用评估：对称反计算需在反向窗口全程持有 flag 载体；unextract 52/52 压力下
  无可行闲置区间（§3），加线则 Q=893，单 qubit 边际 ≈2QT≈7.05e8（≈744 单位），更差。

## 6. 验证范围声明（诚实区分）

- **静态**：基线普查复用审计脚本结果；本实验仿射分组为构造性精确（规则逐条精确，
  无采样），产物 `affine_groups.json`（n_sites=141，multi=0）。
- **解析正确性**：HMR-free 前缀 2,698,118 行与官方 `km.Simulator` 逐位比对
  （892 qubit + 98,292 bit 零失配，`compare_prefix.py`）；occ/zero 表与独立值仿真
  pass 交叉一致（13525/13525，occ 全等）。
- **局部抽样**：2048-shot 官方验证器基线 PASS（上文）；**无候选故无候选验证**。
- **全量 PASS**：未执行（无候选需要）。
- Kaggle 排行榜：未提交。
- 引用：Syed V10/V11 方法描述取自本工作区已存 `artifacts/20261108_public_frontier/source/
  syed_v11_info.json`（MCP 公开作品读写，版本 V11）；kickmix 语义取自 Qualtran 官方
  `kickmix_format.md` + 本地 `km.Simulator` 小电路实测；计分公式取自
  `data/competition/verifiers/dqi/verify_submission_dqi.py`（未修改验证器）。

## 7. 过程教训（值仿真 bug 未根除）

- `fingerprint_products.py`（全电路经典比特仿真，batch=384）在 188/384 shots 出现
  S 残留（含 k=0 shot），而官方模拟器同电路 4-shot/2048-shot 零失败 → 自仿真有系统 bug。
- 已排除：小电路语义（条件 HMR/R/CCX、PUSH 极性、CSWAP、BIT、掩码 SWAP 逐项与真值一致）、
  PUSH 深度（≤1）、栈位混叠（0）、行 arity、多目标指令、校验子生成数学。
- 前缀 2.7M 行逐位一致把 bug 锁定在条件区，但 44k+ 条件 CCX/HMR/R 的组合行为仍未定位。
  结论：58M 门 Python 值仿真脆弱，转向精确仿射后不再依赖它。残留 bug 不影响本报告结论
  （结论仅依赖解析层，而解析层已被前缀比对验证）。
