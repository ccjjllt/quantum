# Stage-bulk语义复用：SAT证明的等式 + 不可货币化结论（2026-11-06，DQI worktree）

本轮建成“仿真过滤 + 全锥CP-SAT证明”管线（R43复刻），在 fd0ef 上证明
**6个新的跨线语义乘积等式**（Busy管线遗漏的R43式link）。但逐一验证：
二进制层面**无可用载体**（carrier）将其货币化为门数——需生成器级载体
分配。本目录保留产出等式的管线脚本；已关闭的单点脚本已按约定删除，
结论与证据数字记于下。

## 关键修正（前置，影响既往结论）

- kickmix `R` 经实测是 **reset-to-0**（`X;R→0`，`R→0`），不是相位门。
  旧版 sim/prover 忽略 R（当作无操作）是错的；本轮全部按 reset 建模，
  旧的 4 个 PROVEN 作废并已用修正后 prover 重证（见下）。
- 输入分布：综合症寄存器 q0..q839 + mbuc 位 b0..b49139（寄存器表实测；
  nS=70, degree=12），仿真按稀疏/稠密/零综合症三分布过滤。

## 6个SAT-PROVEN等式（全锥、unfrozen、CP-SAT INFEASIBLE，genuine）

| # | L1 | product@L1 | L2 | product@L2 | span | 阶段 |
|---|---|---|---|---|---|---|
| 1 | 45443495 | q849&q852 | 45546777 | q15&q859 | 103282 | unconvert |
| 2 | 45443474 | q846&q852 | 45546756 | q850&q859 | 103282 | unconvert |
| 3 | 45443430 | q846&q849 | 45546712 | q850&q15 | 103282 | unconvert |
| 4 | 50917113 | q841&q885 | 51027504 | q884&q886 | 110391 | unsynthesis尾 |
| 5 | 50227238 | q882&q840 | 50387364 | q846&q851 | 160126 | unsynthesis |
| 6 | 46945987 | q853&q855 | 47313278 | q863&q875 | 367291 | unsynthesis（R41-k0邻域）|

- 同一等式在三分布（稠密/稀疏/零综合症，各2000 shots）掩码一致 +
  CP-SAT 全锥（8.6万~38.7万相关门）INFEASIBLE，求解 6~55 秒/个。
  REFUTED对照存在（同管线判出 genuine SAT），证明器具区分度。
- #6 与 R41-kernel0（compute@46945900）相邻 88 行，但乘积不同，
  不能共享载体。

## 不可货币化（逐项证据）

- 直接载体：跨度内写闲置+HMR-clean 的 ancilla，#6 跨度 0 个；
  #1–3 跨度 25 个闲置 ancilla，但逐一查 next-touch 全部是
  value-dependent 写/读（`CX q870 q845` 类 consume 或后读），
  无 value-dead（HMR/R-kill 前无读）者。
- 双相 SWAP 链：carrier_enum v3 全文件仅 23 moves（14=R41自身+9=数据
  SWAP），目标跨度内无可用 hop；#6 额外 9 moves 经查是数据shuffle
  （新家 0 control-read 即被杀），非缓存脚手架。
- 死线载体：#1–3 跨度 362 闲置线中 L1 后零读者为 0；#6 跨度 26 闲置线
  q24–35 下一触碰是 52.2M 的 value-dependent `CX`（需 preserve），
  q36–47/q864/q887 皆后读 → preserve 舞蹈无死线 d 可用。
- 结论：6 等式需生成器级载体分配；二进制补丁路关闭。

## 同轮关闭的方向（证据，无需重做）
- R=reset 语义探针：`X;R→0`，`R|0>→0`（kickmix Simulator 实测）。
- clean-control 门：HMR-clean 控制的 CCX/CSWAP/CCZ，全文件 0。
- 首触控制门：ancilla 首触即作控制（初态|0>恒等删除），0。
- 镜像对消：convert/unconvert、synthesis/unsynthesis、extract/unextract
  的 CCX multiset 根本不同程序（各向差异 13k~76k 门），非镜像，
  无对消。
- 分支稀有度：56 个 PUSH  guarded 区在稀疏输入下全部 ~50% 触发
  （947~985/2000），无稀有分支；R50式近似剪枝在本文件无对象。
- triple-zero（4495 候选）：抽查 7 个 SAT 全 FIRES（ genuinely 会触发，
  属稀有分支类）；(q11,q882)×1050 簇首例亦 FIRES。
- R41 形状复刻验证：carrier_enum v3 精确复现 14/14 computes+moves
  （analysis.json 行号为0-based，实际+1），除R41外无长跨度载体脚手架。

## 管线脚本（保留，产出等式用）

- `sim2.py`/`sim3.py`：2000-shot bitwise 仿真（~20秒/58M行），
  稠密/稀疏/零综合症三分布；HMR=随机+reset，R=reset，条件=逐shot掩码。
- `miter.py`：后向价值锥 + CNF/Tseitin（含条件enable、HMR/R reset）。
- `fullcone.py`：锥→OR-Tools CP-SAT（AddAllowedAssignments精确门编码），
  INFEASIBLE=PROVEN。
- `zeroprove.py`：`P==0`永零证明（R47式）。
- `batch_prove.py`/`batch_zero.py`：子进程隔离批量驱动。
- `selftest.py`：TRUE/FALSE/COND/R-kill 四用例（Glucose验证编码正确性）。

## 原始证据位置（仓库外，不进 git）

- kmx 转储：`$TMPDIR/dqi.kmx`（792MB，58390266行）。
- masks：`simB2/simZ2/simS2_prod.pkl`；候选：`cross2.json`（731 cross-pair），
  `ds2.json`，`zero3.json`（4495）。
- 独立 env：`$TMPDIR/satenv`（uv venv，python-sat + ortools）。

## 追补（同分支后续推进，所有二进制变现路已穷尽）

- 活线替换（`CCX c d u`→`CX w u`，w为终点时刻持有该乘积的线）：
  全文件流式掩码匹配找到 4833 候选 + 25 跨对终点候选；
  SAT逐一证伪 55 个（8+17+10+20，皆DIFF，锥unfrozen，0.0~95秒），
  含1799 unique-mask与20跨阶段 diverse 样本。循环行进结构导致
  系统性假阳性；已证6等式的终点均无活线持有（6/6零匹配）。方向关闭。
- MBU（uncompute-form `CCX a b t,t==a*b`→`HMR+CZ`）：10693候选中
  经R-reset语义过滤，真uncompute（product!=0）为 0——全部是
  `R t`清零+Rare不触发乘积的假象。方向关闭。
- scan尾剪枝：loop体每22 CCX含124 X翻转+R/HMR，状态恒变，
  无收敛可能；以22为精确周期（44275=2012×22+11，无break）。
  方向关闭（推理+体组成证据）。
- 宽度：891 qubit全被使用（最闲q23也有32248触碰）；降宽需重调度，
  ablokced（并行线程方向，不重复）。
- R-clean控制：reset语义修正后重查（HMR/R-clean+SWAP传播），全文件0。
- 常1控制：675终点快照无恒1线；全1乘积0。方向关闭。
- 官方验证器本地可跑：ProblemSpecDQI(m=4095,n=70,degree=12,r=2016)，
  基准电路512 shots得value 0/512 phase 0/512（assertion系shot数不足
  致bound不达标，非电路问题）；后续补丁用同命令+小shot数做
  differential gate（以0/0为通过标准），再跑全量102400。
- R语义补记：`R`除reset-to-0外还带随机outcome（影响phase_flipped，
  不影响值逻辑）；`HMR`/`R` outcome由seed确定，验证器可复现。
  本管线的值证明不受影响；补丁必须走官方验证器（已就绪）。
