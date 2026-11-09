# DQI 解码器结构切口（`20261109_dqi_decoder_struct`）：阶段划分对比＋广播扇出

日期：2026-11-09；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
固定基线：Public Frontier `4432ec5f`（`dqi.kmb` SHA-256
`4432ec5f…`，892Q，395,641 静态 Toffoli-like，默认 salt 官方成本
`374735446628.53`，`R=1.19126046`，`T_mean=395356.94`，`Q²=795664`，
每静态门 `≈947843` 分，Q+1 边际 `≈8.41e8` 分）。
只读输入：`artifacts/20261108_public_frontier/release/dqi.kmb` 的 kmx 解析缓存
（58,341,173 行）＋`artifacts/20261109_dqi_dirtyk2/a_groups.json`（结构分组）。
不重复既有路线：仿射 clean / 结构哈希 / 字面 top 缓存 / 脏线 k>2 / CCZ
（见 `20261109_dqi_deepfix`、`20261109_dqi_dirtyk2`，可行组 0）。

## 0. 结论（先行）

1. **阶段划分对比完成，Syed V10/V11 解码器特征在 frontier 中的落地核对完成。**
   narrow return、flag carry、测量擦除、conditionally-clean AND ladder、
   scan 掩码守卫、one-qubit trade（892Q）**全部已存在**；唯一缺席的是
   V11 的 weight-17 极点保留（node-9 pole flag＋fold-18 zero flag，+175 门）。
   可整体替换的子结构：multiply v×6 前向链（6×99 CCX，6 体各异，
   unextract 无对应逆块——窄返回已擦除）**无可换对象，closed**；
   scan 掩码守卫块（4025×105 行）**已是 V11 形态，守卫机制经切片验证透明**。
2. **`(120,859):234` 全跨度广播不可行（0/233 对控制稳定）**，跨度内
   q120/q859 被写 182,106 次，每一对之间控制必变。诚实记录为一次失败的尝试。
3. **退路：全电路稳定对普查 84/1524 可行（全在 unextract，gap≤10），配额
   −84 CCX（≈−7.96e7 分），但 Q+1（新 ancilla q892＋scratch bit）边际
   +8.41e8，净 +7.61e8（+0.203%），负收益。** 盈亏平衡需 887 对。
4. **产出 1 个改写片段的 kmx diff**（unextract `52710777–52710779`，
   3 CCX→2 CCX，净 −1）：前缀切片（header＋unextract 入口..清理点，
   52.7M 行，4-shot，种子 99）**892 qubit＋99,567 bit 全等**（scratch 除外），
   确定性重跑一致（证据 `s7_broadcast.json`）。tail-8k 下游切片验证进行中，
   预期仅 HMR 随机结局 bit 漂移（RNG 移位伪影，见 §4）。
5. 无候选 kmb、无官方验证器运行（基线字节未动；验证范围见 §6）。

## 1. 阶段划分对比：Syed V10/V11 描述 vs frontier 实测

frontier 顶层阶段（kmx `INFO_TAG`，0-based 行号）：
`extract [2698118,6591538]`、`scan [17698662,41252601]`、
`unextract [52196517,57991316]`（`unsynthesis` 在 `unextract` 之前，
与 deepfix 一致）。

| 阶段 | paid | 组成（实测） |
|---|---|---|
| extract | 59,169 | depth-1 主体 54,357 CCX＋192 CSWAP；69×inverse24（3,910 CCX，均 56.7，[42,70]）；**6×multiply v（594 CCX，每块恰 99，6 体各不相同）**；6×inverse12 标签（=2 逻辑逆，116 CCX） |
| scan | 44,275 | 44,275  rung（每 rung `R+CCX+HMR`，conditionally-clean AND）；**4025 个位置 ×11 rung，每位置 105 行，被 scratch 位 b101254 守卫**（`PUSH_CONDITION if b101254`，b101254=12 个掩码位的 OR）；gf_iadd 标签只包 X-run |
| unextract | 96,888 | depth-1 主体 94,193 CCX＋1,043 CCZ＋1,536 CSWAP；140×gf_iadd X-run；6×inverse12 标签；**50 个 PUSH 守卫区（flag-carry 重建段：8/34/62/138/26 行）**；353 栈条件 CCX（口径与 deepfix 一致） |
| convert/unconvert | 60,687/62,558 | 对称：inverse12 各 147＋aligned_route 各 26＋head product/pivot/phase |
| unsynthesis/synthesis | 40,429/31,635 | 主体＋inverse12（108/6 标签） |

Syed V11 方法映射（`syed_v11_info.json` cell-1 DQI 节）：
- narrow return（单遍逆节点）✓＝unextract 的 gf_iadd 梯＋无 inverse24/multiply 逆块；
- flag carry（前向 X-测极点旗，逆向 flag-AND＋zero-test 重建＋CZ 偿还）✓＝50 个 unextract PUSH 重建段（例：62 行段含 9 CCX＋1 CCZ，`HMR q864 b99437` 开头，重建＋HMR 擦除＋CZ 偿还，见 §2 样例行）；
- 测量擦除 / conditionally-clean AND（Khattar–Gidney）✓＝scan rung；
- scan 掩码守卫（"test runs only when mask nonzero"）✓＝4025 守卫区（§3 验证）；
- one-qubit trade ✓（892Q）；functional product caching（−48）＝前人已证在 frontier 上无干净载体（0 可行）；
- **缺席：w17 保留（+175 门）**——frontier 无 node-9/fold-18 保留；按 Syed 数据 72 draws 失败 27→21，属 R 项改进，需 +175 T，两工作区此前无人构造（手工插入 175 门极点逻辑不可靠，不构造，只记录）。

## 2. 可整体替换子结构 S1：multiply v×6（closed）

6 块 paid 均为 99（`s2_dupscan.json`：`multiply_paid=[99]*6`，
`multiply_distinct_bodies=6`，跨度各约 6400 行，见 `multiply_spans`）。
6 体两两不同（不同操作数——6 次不同的乘法，非重复计算），故不存在
"复用一次"替换；unextract 侧无 multiply 逆块（窄返回擦除），也不存在
"前后对称互换"。结论：该子结构无整体替换对象，closed（数字见
`artifacts/20261109_dqi_decoder_struct/s2_dupscan.json`）。

## 3. 可整体替换子结构 S2：scan 掩码守卫块（验证通过）

替换单元＝`PUSH_CONDITION if b101254 … POP`（105 行：11 CCX＋11 R＋11 HMR＋
12 条件 CZ＋X-run；静态 paid 差 0，mean-T 差＝11×skip）。
切片＝header＋[17974728,17974954]（掩码序言＋守卫块，227 行），4-shot，
种子 99，输入种子 0xD91（`s6_guard_verify.py`）：
- G1≡U1（守卫位=1 时守卫透明，pass-through）✓；
- G0≡输入全等（守卫位=0 真跳过；零输入强制掩码全 0，守卫位 4/4 为 0）✓；
- U0 数据线 q0..q11≡输入（裸块在掩码全 0 时数据通路恒等——V11 "identity otherwise"
  在本工作区的实证形态；注意早先误数 X-run 为 3，实际 4 次，X⁴=I）✓；
  U0 仅 scratch ancilla（R- provision/HMR-测量线）＋结局位 b99126 与输入不同
  （属逐位置重算量， конструкive 精确）；
- 确定性重跑一致 ✓。
证据：`artifacts/20261109_dqi_decoder_struct/s6_guard.json`
（`G1_eq_U1_passthrough=true`，`G0_eq_input=true`，`U0 data identity=true`）。
含义：V11 的 headline 守卫在 frontier scan 已足额存在（4025/4025 位置），
scan 无剩余可移植空间；unextract 主体梯无此类守卫且段非恒等（控制 churn），
移植需逐段恒等定理（不成立，见 §4），故不构造，只记录。

## 4. 任务 2：`(120,859):234` 广播尝试 → 不可行；退路 84 稳定对（净负）

`(120,859)` 普查（`s3_broadcast.json`）：k=234，L1=53262188，Lk=57814851，
跨度 4,552,663 行，45 个不同 target，top 为 t720×42、t432×32；
**跨度内 q120/q859 被写 182,106 次，连续 233 对稳定 0 对**（`s4_stable.json`
扩展到全部字面组同样 0）。结论：单计算广播在该段语义错误（每处乘积值都不同），
尝试关闭。

退路（`s5_fullstable.json`，结构组全部 1524 个贪心非交叠连续对，
要求 L1 字面控制在 (L1,Lj] 无写＋Lj 自身读＋depth 0）：
**稳定 84/1524（全 unextract，gap≤10；unsynthesis 0/523），逐对 −1 CCX，
合计 −84（−7.962e7 分）**。载体为 1 根新 ancilla q892（R 配给，段间串行复用）
＋1 个 scratch bit b300000（>max 200002，自动扩展已用 toy 验证）；
Q 892→893 边际 +8.407e8。**净 +7.611e8（+0.203%），负收益；盈亏平衡 887 对。**
单片段净：−1 门（−9.5e5）＋Q+1（+8.41e8）≈ +8.40e8。

## 5. 任务 3 产出：片段 diff＋切片证据

`artifacts/20261109_dqi_decoder_struct/s7_broadcast.diff`（unified，对应
0-based 行号±3 上下文）：
`CCX q887 q874 q846 / CCX q891 q846 q864 / CCX q887 q874 q846` →
`R q892 / CCX q887 q874 q892 / CX q892 q846 / CCX q891 q846 q864 / CX q892 q846 / HMR q892 b300000 / CZ q887 q874 if b300000`
（3 CCX→2 CCX；+R/+2CX/+HMR/+CZ 免费；depth 0 已核；mid 行读写 t1 不影响，
compute 后紧跟 CX  placement 规则，见脚本注释）。

验证（`s7_broadcast.py`，前缀切片 header＋[52196517,52710780]，随机初态，
种子 99，4-shot）：
- **TAIL=0（结束于清理点）：892 qubit 全等＋99,567 bit 全等（scratch b300000
  除外，结局 [T,F,T,F] 随机符合预期），确定性重跑一致**（`s7_broadcast.json`：
  `qubits_equal=true, bit_mismatches=[]`）。
- TAIL=8000 下游对照（`s7_broadcast_tail8k.json`）：**892 qubit 全等
  （确定性重跑一致），99,467 bit 中仅 11 个差异，且全部是 tail 内 HMR
  随机结局位**（b99126/b99438/b99458–b99466，`HMR=H+测量` 对经典值产生
  50/50 随机结局；重写多一次 HMR 抽取致 RNG 流移位，属预期伪影）。
  下游数据线零扰动，相位偿还与下游确定性读数一致。
- 相位说明：HMR+CZ 偿还是 Kirill 恒等式（静态精确，`CCX a b w; HMR w`
  → `HMR w; CZ a b if m` 在 w 被 CX 读后依然成立——CX 读的是经典值，
  HMR 消耗 w，CZ 修相位）；toy 相位对照（`s7c_phase.py`，64-shot）显示
  经典控制下 fixup 为全局相位（with/without CZ 分布全同），故相位正确性
  依静态恒等式＋下游确定性读数佐证（诚实边界，见 §6）。

## 6. 验证范围声明（诚实区分）

- **官方模拟器**：s6（227 行窗，4-shot×5 变体＋确定性重跑）与 s7 TAIL=0
  （52.7M 行前缀 ×3 次：orig/rewritten/rewritten-repeat，4-shot，
  892Q＋99,567b 全等）为片段级功能等价证据；输入随机种子 0xD91、
  仿真种子 99；s7c toy 64-shot。
- **静态精确**：§1 阶段表（解析层行号级事实）、§2/§4 门数与稳定性
  （写追踪，条件/无条件写一律按脏处理，只漏检不误报）、diff 构造规则。
- **未做**：全电路候选 kmb（58M 行内存/格式链不可行，未构造）、官方验证器
  （基线字节未动；沿用 `baseline_2048shot.json` PASS）、w17 保留构造、
  multiply 重综合、私有榜 R 影响实测。
- **候选/提交/推送**：无。验证器未改动。凭据无。
- 环境：本工作区 `.venv`（Python 3.12，PyPI 原生 kickmix； toy 已验
  新 qubit/bit 自动扩展；macOS 未用数据包内 Linux `kickmix.so`）。

## 7. 过程文件

- 脚本：`experiments/dqi/20261109_dqi_decoder_struct/s{1,2,3,4,5,6,7,7c}_*.py`
  （只读扫描＋toy＋切片验证，无测试/CI）。
- 产物：`artifacts/20261109_dqi_decoder_struct/` 内
  `s1_blocks.json`、`s2_dupscan.json`、`s3_broadcast.json`、`s4_stable.json`、
  `s5_fullstable.json`、`s6_guard.json`、`s7_broadcast.json`、
  `s7_broadcast_tail8k.json`、`s7_broadcast(diff＋tail8k.diff)`、
  `s7c_phase.json`。
- 引用：Syed V11 方法（cell-1 DQI 节）见
  `artifacts/20261108_public_frontier/source/syed_v11_info.json`；
  计分 `R·Q²·T` 与门数口径见 dqi verifier；Kirill 测量窥孔谱系见
  `20261108_frontier_audit/README.md` §1。
