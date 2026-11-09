# DQI 深度修复（`20261109_dqi_deepfix`）：分阶段仿射修复＋深非线性值等价普查＋字面缓存剩余空间

日期：2026-11-09；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
固定基线：主仓库 Public Frontier 25.14222 `dqi.kmb`
（SHA-256 `4432ec5fd63d7d70aab92d32f719d47539d0ff66ae0cb0b964c914e01fece431`，
892Q，58,287,028 ops，395,641 静态 Toffoli-like，默认 salt 官方成本
`374,735,446,628.53`），只读链接 `artifacts/20261108_public_frontier/release/dqi.kmb`。
kmx 解析缓存：`/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx`
（58,341,173 行；阶段顺序 `... → unconvert → unsynthesis → unextract → uninitial`；
注意 `unsynthesis` 在 `unextract` 之前）。

## 结论（先行）：三项全部 closed，无净收益

1. **分阶段仿射修复完成，strict/mask 重复仍为 0。**确证 `affine_clean.py`
的跨阶段污染机制（见 §2），精确规则＋每阶段入口重置后的权威数字：
`unsynthesis` 141 clean / `unextract` 1030 clean（与 probe 一致），
strict 与 mask-only 重复组均为 **0**（`distinct 141→141、1030→1030`）。
`unextract` 的 2399 是 SWAP 精确跟踪变体（见 §2），同样 0 重复。
2. **深非线性位点的值等价普查完成：字面不同但函数相同的对存在（368 组 / 778 位点），
但全部不可缓存。**精确原子-掩码结构哈希（§3，无仿真、构造性精确）在
135,369 个无条件 `CCX`/`CCZ` 位点中找到 1618 个函数重复组（3500 位点），
其中 368 组（778 位点）字面不同。8 对抽查（含 4 对字面不同）经官方
`km.Simulator` 阶段切片 4-shot 验证全部值相等。载体分析（全跨度持有
0/1618，连续子间隔 0/1882，400 线内小间隔宽池 0/40）→ 可行组 0，净省 0。
3. **Isabe V12 式字面缓存剩余空间为 0。**统一口径字面统计（§4）：
`unextract` 9679 distinct / 7398 repkeys / 91675 occ；
`unsynthesis` 2048 / 1687 / 39782。按跨度排序 top-20（40 组）逐组检查：
跨度内闲置线多为 0（个别 1），HMR 归零可用线 **0/40**，pristine 可用线 **0/40**；
全部 run-split（按 a/b 写切分）无 k≥2 稳定 run。可行组 0，净省 0（k−1 规则）。
4. **计数口径统一**（§5）：`unextract` 条件 `CCX` 353 全部来自 `PUSH_CONDITION`
栈深度，内联 `if` 为 0；`probe_affine.py` 的 `' if '` 子串检查漏掉全部 353 个
（显示 cond 0），`affine_clean.py` 的口径（栈深或内联）正确。另 `CCZ` 条件位点
35 个（栈），与审计一致。

无候选产出，基线字节哈希不变，无需重跑验证器（验证范围见 §6）。

## 1. 方法与脚本（本实验新增，全部只读、可复跑）

| 脚本 | 内容 |
|---|---|
| `step1_census.py` | 统一口径普查（阶段+栈深+内联条件、每阶段重置基）：bothclean、strict/mask、literal、200k 窗口载体压力 |
| `step1b_fixed_affine.py` | **权威修复**：`affine_clean.py` 逐条规则原样（含 compute/uncompute 配对、`a==b` 退化、常量积、保守 SWAP），唯一改动＝目标阶段块入口重置 892 符号基 |
| `step1c_swapcheck.py` | 1030 vs 2399 差异根因验证（保守 SWAP 即复现 1030） |
| `step2a_struct.py` | 精确原子-掩码结构哈希分组（阶段内前向，X/CX/SWAP/HMR 精确仿射，CCX 积记忆化原子，CSWAP 精确 mux，条件写唯一脏原子） |
| `step2b_verify.py` | 阶段切片＋官方 `km.Simulator` 4-shot 随机输入值相等抽查（8 对）＋确定性自检 |
| `step3_cache.py` | 字面 top-20（跨度排序）载体检查＋run-split＋结构组全跨度贪心载体分配 |
| `step3b_diag.py` | 载体查找器 sanity（已知易区间）＋top 组 idle/zeroed 诊断 |
| `step3c_carriers.py` | 全文件 occ＋pristine 规则重跑（修正 `repocc` 聚合笔误，见下） |
| `step3d_subgap.py` | 连续子间隔（1882 对）逐对载体贪心＋全组诊断分布 |
| `step3e_widepool.py` | ≤200 行小间隔 892 线宽池检查（40 对） |

产物：`artifacts/20261109_dqi_deepfix/step*.json`（`step3_cache.json` 的
`literal.*.repocc` 聚合字段有笔误——对 `(k,v)` 元组取 `len` 得 2×repkeys；
以 `step1_census.json` 的 repocc 为准：unextract 91675、unsynthesis 39782；
各行 k/span/idle 均正确）。

## 2. 跨阶段污染：机制、修复与 1030/2399 双数字

- 机制：文件顺序 `unsynthesis → unextract`（§头 bounds 实测），`affine_clean.py`
只在文件头设一次 892 基。`unsynthesis` 先用新鲜基得 141（与其 per-stage 数一致），
脏状态带入 `unextract` → `unextract` clean 恒 0。`artifacts/20261109_affine_cache/
affine_groups.json`（n_sites=141）即此污染产物。
- 修复（`step1b`，规则与 `affine_clean.py` 逐条一致＋阶段入口重置）：
`unsynthesis` sites=141（CCX 141、CCZ 0），`unextract` sites=1030（CCX 1030、CCZ 0），
`pairings=0 constprod=0`，`cond_ccx={unextract:353}`，
strict distinct 141/1030、repkeys **0/0**；mask-only distinct 141/1030、repkeys **0/0**。
- 1030 vs 2399：唯一差异是 SWAP 脏规则。`affine_clean.py` 保守规则
（任一脏则双脏）→ 1030（`step1c` 复现，`unextract` 41,606 SWAP，`a==b` 数为 0）；
精确值跟踪（脏随值交换）→ 2399（`step1`）。两种语义下 strict/mask 重复均为 0，
故“仿射干净乘积无重复”结论与 SWAP 精度选择无关。
（`step1_census.json` 内 `old_single_basis_bothclean` 1611/3887 为 step1 自带
SWAP 未传播脏的复现 bug，不引用；权威旧数以已提交的 `affine_groups.json` 141 为准。）

## 3. 深非线性位点值等价普查（精确结构哈希＋Simulator 抽查）

动机：135,369 个无条件位点中仅 1171（~0.9%）仿射干净，99% 深 GF 非线性位点
从未被普查；前人 `fingerprint_products.py` 值仿真有系统 bug（HMR 结果被随机化，
而基态下真实模拟器确定——188/384 shots 出现 S 残留 vs 官方模拟器同电路 4-shot
零失败；根因定位到此，不再依赖全电路 Python 仿真）。

方法（`step2a`，构造性精确、无采样、无仿真）：
- 每线持 `(mask, const)`，mask 为原子空间上的 Python int 位集；
原子：阶段入口 892 基 → CCX 积记忆化原子（`a==b` 退化为仿射自举）→
CSWAP 精确 mux 原子 → 条件写唯一脏原子（只漏检、不误报）；
HMR/R 无条件归零共享。
- 位点键＝规范积 `sorted(((ma,ca),(mb,cb)))`；等键 ⟹ 同一基函数的同一仿射组合
⟹ 布尔函数全等（仿射关系经 mask xor 自动坍缩）。op 全集已核对
（CX 52,073,358、SWAP 1,583,100、CSWAP 12,060、CCZ 1,377、HMR 78,990、R 56,223、
X 250,136，余为相位/经典位操作），无未处理值操作。
- 验算：`step2b` 对 8 对（4 同字面＋4 字面不同，unsynthesis/unextract 各半）
做阶段切片（文件头声明＋阶段入口..位点）＋官方 `km.Simulator`（batch=4，
seed=99，全部 892 qubit＋全部位随机输入，`use_same_registers_as`）：
**8/8 四 shot 值全等**（含非平凡模式 `[0,1,0,0]`、`[1,0,1,0]`、`[0,0,1,1]`），
确定性重跑 8/8 一致。

数字（`step2a_struct.json`）：
- `unsynthesis`：sites 40405（40143 CCX＋262 CCZ），cond 0，dirtyops 11016，
distinct 39746，**repkeys 659（全 k=2）**，repocc 1318；
**字面不同组 298（596 位点）**。
- `unextract`：sites 94964（93956 CCX＋1008 CCZ），cond 388（=353 CCX＋35 CCZ，
与审计“353+35”一致），distinct 93741，
**repkeys 959（767×k2＋150×k3＋12×k4＋30×k5）**，repocc 2182；
**字面不同组 70（182 位点）**。top 为 `(108,84)×5` 等，span 167300。
- 毛空间上限（k−1 求和）：659＋1223＝**1882**；连续子间隔对数同样 1882。

## 4. 字面缓存剩余空间（Isabe V12 式，k−1 规则）

- 统一口径字面统计（`step1`，条件＝栈深或内联）：
`unextract` distinct 9679 / repkeys 7398 / occ 91675；
`unsynthesis` 2048 / 1687 / 39782；合计 distinct 11002 / repkeys 8612 / occ 131709。
与 probe 数字（9708/7424/92025）之差＝ 353 个栈条件 CCX 被 probe 计入无条件所致。
- `unextract` top-k 参考：`(120,859):234`、`（168,859):225` 等（span 均百万行级）。
`unsynthesis` top-k：`(24,48):856`（span 354180）等——均为高频复用数据线。
- 按跨度 top-20（`step3c`，40 组）：跨度 5.0M–5.7M 线；跨度内 840..891 闲置线
38/40 组为 0、2 组为 1；**HMR 归零可用 0/40，pristine 可用 0/40**。
全部 occurrence 间隔内 a/b 均有写（run-split 无 k≥2 run）。
- 200k 窗口压力重跑（`step1`，ancilla 任一触碰即忙）：29 窗口中 23 个 52/52 全忙
（分布 24×3、51×3、52×23；README 旧数 26 个全忙，方法细节不同，结论一致：极端拥挤）。

## 5. 载体可行性总账（结构组，Isabe 模板，贪心 k 大 span 小优先）

载体规则：w∈840..891、非成员线、[L1,Lk] 无触碰、L1 前最后触碰为无条件 HMR/R
归零或全文件 pristine、预约区间不交叠；每组净 −(k−1)，子间隔对每对净 −1。
- 全跨度持有：**0/1618 组可行，净 0**（`step3c`；诊断：292 组跨度内 0 闲置，
629 组 1 闲置，余 12–39 闲置但可用 0——约束卡在“最近一次触碰非归零”，非跨度触碰）。
- 连续子间隔：**0/1882 对可行，净 0**（`step3d`；gap 最小 2、中位 13557、最大 367389）。
- ≤200 行小间隔宽池（892 线，`step3e`，147/1882 对符合，抽查 40 对）：
2 行间隔组 ancilla 闲置达 47、数据线闲置 840，但可用（归零/pristine）**0/40**。
- 查找器 sanity：10k 易区间返回 idle 14（`step3b`），证明 0 结果非查找器恒空。

## 6. 验证范围声明（诚实区分）

- **静态精确**：§2（规则级精确）、§3（公式恒等精确，op 全集已核对）、§4–§5
（occ/zero 表为解析层事实；`step3b` sanity 通过）。
- **官方模拟器**：`step2b` 8 对阶段切片 4-shot 值相等＋确定性自检（输入随机种子
`0xD91`、仿真种子 99；切片构造＝文件头＋阶段入口..位点，寄存器沿用原电路）。
**未做**：全电路 2048-shot（无候选、无字节变化；基线沿用已记录的
`artifacts/20261109_affine_cache/baseline_2048shot.json` PASS，
value=0/phase=0，平均 T=395,356.94，`reaction_depth=45619`）。
- **候选/提交**：无候选电路，无提交，无推送；验证器未改动。
- 引用：Ozer V5（−21）、Kirill V21（−14）、Isabe11aM00re V12（−3）谱系见
`experiments/dqi/20261108_frontier_audit/README.md` §1；
Syed V10（−62）/V11（+175，w=17）见 `artifacts/20261108_public_frontier/source/
syed_v11_info.json`；kickmix 语义 Qualtran `kickmix_format.md`＋本地 `km.Simulator`
实测；计分公式 `data/competition/verifiers/dqi/verify_submission_dqi.py`。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix；未用数据包内 Linux 编译 `kickmix.so`）。

## 7. 过程记录

- `probe_affine.py`（已验证复跑）：unextract 94309/1030/cond 0，unsynthesis 40143/141；
cond 0 为口径 bug（栈条件全漏），bothclean 1030 在统一口径下仍成立（`step1b`）。
- `fingerprint_products.py` 自仿真 bug 根因：HMR 结局随机化；基态 HMR 确定，
自仿真与官方模拟器分叉。残留 bug 不影响本报告（本报告仅依赖解析层＋官方模拟器切片）。
- 本实验新增文件：`experiments/dqi/20261109_dqi_deepfix/step{1,1b,1c,2a,2b,3,3b,3c,3d,3e}_*.py`；
产物：`artifacts/20261109_dqi_deepfix/*.json`＋`lit_*.pkl`。未建测试/CI。
