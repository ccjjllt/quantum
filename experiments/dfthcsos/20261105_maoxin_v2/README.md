# Maoxin V2 化学研究：方法、当前成本与后续方向

日期：2026-11-05（北京时间）。分支 `codex/dfthcsos-research`。
基线是已下载 Maoxin V2 / run365853243 原始包中的 `dfthcsos/`，
只读路径 `artifacts/20261105_maoxin_v2/release/dfthcsos/`。

## 结论

本版本把三种互补的改进组合到同一化学方案：Syed 的 (8,143,45) 量化表、
Atakan 的物理 π-gauge 编码与 tensor/QROM loader、Busy 的固定角度权重重拟合。
Maoxin 的新贡献是发现 **Busy 的 W/H2_I 可以直接迁移到 Atakan 的新 gauge**；
并没有新综合十五个电路。

本地已用实际电路恢复的角度字重算成本为 **304,305,834.2401413**，
`lambda_eff=46.944208770784336, T=15,181, Q=427`。
这是 **1 shot/address 的局部电路诊断＋原版数学/成本函数计算**，不是默认
78,080 shots 的完整官方验证，不是本账号榜分。没有生成新优化候选。

首要实验是固定字 tensor kernel / padding 重新规划，其次是沿活动约束面的权重下降。
固定四个 quadratic helper 的单独 gauge 微调已经接近这一模板的上限；
更大的 gauge 基或角度/分解联合优化仍开放，但不能由简单资源表承诺收益。

## 实际检查与当前资源

手动执行：

```sh
.venv/bin/python experiments/dfthcsos/20261105_maoxin_v2/analyze.py
.venv/bin/python experiments/dfthcsos/20261105_maoxin_v2/parameter_probes.py
```

- Python 3.12 环境、PyPI 原生 kickmix；没有加载比赛包的 Linux `kickmix.so`。
- 十五个实际 loader，1,220 个地址，每地址 1 shot，seed=20261105，完整 forward/reverse 遍历。
  恢复出的 91,500 个字与 NPZ 的 `angle_words` 相同；过程中未出现值、地址、workspace、相位检查异常。
  这不覆盖所有独立 HMR 结果，也不构成任意输入目标寄存器的 XOR 证明。
- 使用恢复出的字和 NPZ tree 计算原版 `evaluate_words`、`resource_costs`。
  从原始 FCIDUMP/固定 shifts 文件直接读取数据；为遵守用户跳过哈希的要求，
  没有调用会计算哈希的 `load_inputs/check_fcidump/load_fixed_shifts` 包装器。
  原始官方文件与函数均未修改；没有调用完整 `verify`。
- `analyze.py` 本次耗时约 4.52 秒，参数探针约 7.24 秒；不是优化器运行耗时。

| 项目 | 实际读数 |
|---|---:|
| R / B / C / N | 8 / 143 / 45 / 76 |
| brot / J / loader 数 | 8 / 5 / 15 |
| ANGLE 单遍 / 双遍 Toffoli | 4,220 / 8,440 |
| outer state preparation | 320 T |
| inner state preparation | 4,171 T |
| Givens rotations | 2,250 T |
| 总成本宽度 | 427 Q |
| loader 最大宽度 | 128 Q |
| loader 临时 workspace | 77 Q |
| 总成本临时 workspace 主导项 | inner preparation 的 303 Q |

ANGLE 占 **55.596%** 总 T；inner preparation 占27.475%，Givens占14.821%。
单独减小 loader scratch 不降低总 Q，因为303仍大于77；
它的意义是腾出128Q上限内的空间以减少真正付费的非线性门。

实际每个 loader 的 (T/单遍, Q)：

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T | 297 | 295 | 294 | 294 | 276 | 276 | 276 | 276 | 277 | 276 | 276 | 277 | 277 | 276 | 277 |
| Q | 128 | 127 | 128 | 128 | 127 | 126 | 126 | 126 | 126 | 126 | 126 | 126 | 126 | 126 | 127 |

本地实际文本未见带经典条件的 CCX/CCZ/CSWAP，所以本表的付费门计数与此次
执行成本相符。**k0、k2、k3 没有空余 qubit；k1 有1根，k5–13 有2根。**

数学指标为 `error_1=0.019999799800011403` Ha、
`error_2=0.01999979979997796` Ha、`E_gap=3.914898200200696` Ha。
三条活动门的余量分别仅 **0.20019999 / 0.20020002 / 0.20020070 μHa**。
原始 Lambda=283.41543656，远高于49下限，当前紧约束是两项误差和gap。

## 方法拆解与独立复核

### 1. Maoxin：跨 gauge 迁移已有重拟合权重

若每一行分子向量改变为 `u'_b=s_b u_b, s_b∈{−1,+1}`，则
`u'_b u'_bᵀ=u_b u_bᵀ`。在相同分组/索引下，同一 w/W 和固定 shifts
产生相同 X、Hamiltonian 及计分指标；因此无需再训练一次权重。

Maoxin 在两个来源 NPZ 的 U 上检查这一关系，再把 Busy 的 W/H2_I 替换到 gauge 表中。
本轮没有把名义 U 比较当作电路证明：先恢复实际字，再依据公开 design
去掉其最高位 π-gauge，分别按实际 tree 重建全部1,220个向量。
结果仅有整体符号差，最大绝对偏差 **5.55e−16**；两体1,144行中 **286行翻转**。
实际加载向量与 NPZ U 的绝对值最大差也为5.55e−16。
这是浮点重建证据；精确代数依据是上面的外积恒等式和路径奇偶约束。

相同 T/Q 下，Busy 的权重令 lambda_eff 从原 Atakan 表约47.019778
降至46.944209，化学成本降低约 **0.16072%**。新 T=15,181 来自已有 gauge loader，
不能再归为 Maoxin 的新电路收益。

### 2. Atakan：让物理等价的最高位携带可复用乘积

`brot=8` 时角度为 `π*word/128`。翻转 bit7 等价于加π，同时改变该Givens
旋转的 sine/cosine 符号。对每条最终分量路径施加相同奇偶，整行向量只整体翻转。

本版本用低4位地址的四个二次单项式 `masks=(3,5,6,9)`
编码75个角度的gauge。先把 bit6 从 bit7 中消去，再用可逆线性解码抽出
forward/reverse 两个合法端点都相同的 helper；其余最高位保持 dirty。
随后更新低7位字、更新dirty gauge坐标并完整清理 HMR 相位。
只有互不作用的Givens旋转被换序，前20列保持原序。

本地独立GF(2)计算复核十五批公共helper秩为
`[0,2,3,3,4,4,4,4,4,4,4,4,4,4,3]`，和为 **51**。
源码计划包含3,071个tensor乘积/单遍，计费式为
`T_k = 80 + product_count_k - common_helper_rank_k`，
`Q_k = 126 + dirty_rank_k`；全部与当前实际电路静态资源相同。

**限定上界：**保留四个helper函数、15批、第一批输入全零时，最多
`0+14×4=56` 个公共helper；相对51最多再省5 AND/单遍，即总计10T。
即使全部实现，也仅约 **0.06587% 化学成本 / 0.02197% 总GM**。
这不是整个gauge方法或全电路的上界。本轮实际树的物理π-gauge约束零空间
维数是 **32**；扩大helper基、更换非线性函数或联合改tensor计划仍是不同的开放问题。

### 3. Tensor kernel 与未访问地址自由度

Atakan公开 plans 的前4批各217个tensor乘积；后段多数200个，
k8/k11/k12为201个。八个后段计划记录了 HW18/HW19 的padding completion，
k8/k11/k12没有该字段；这些信息不证明三个点必定能再省1门。

当前字去掉gauge后的低位结构也已重新计算：k4–14在76个完整16地址块中
bit0的delta全部仿射，前4批基本不具备这一性质；bit1并没有旧C60表中
隔批仿射的优势。最后4个地址未计入这一ANF统计。
因此不能直接搬用10月30日旧方案的结构结论或随意改变J。

padding是对从不访问的表值赋值，不改变要求的1,220个地址。
必须在当前新表上重做张量规划，再由实际电路证明可达forward/reverse的字、地址、
scratch及全部HMR相位正确；低位ANF系数少不等于已省Toffoli。

### 4. Busy：在活动约束面上继续降低 lambda_eff

Busy V18 将其 R53/R55 描述为固定字和loader下的约束面下降：
同时约束error_1、error_2和E_gap，下降后精确恢复到离门2.002e−7 Ha的位置；
跟踪活动的特征子空间，处理大量接近零的权重。其叙述中普通增广拉格朗日
曾停在更差点，约束面方法才获得改进。Maoxin只迁移了R55 D的结果。

本轮5个简单联合缩放探针说明不能用整体缩放替代受约束优化：
native w/W放大 **1e−8** 虽降低lambda，但E_gap变为3.9148853374，已越界；
缩小1e−8或1e−7保持可行，lambda却上升。只调某一门的余量容易损失收益或违反另一门。

Busy V18 另报告未提交的 **R55 E：lambda_eff≈46.912384**，
若可合法迁移到同一字表，相对当前约有0.06779%化学/0.02261%总GM空间。
这只是作者报告：本轮列出的dataset V11仅有编译电路、D权重NPZ及说明，
没有refitter源文件或可辨识的E权重产物；未下载、复现或验证E，不能作为已获候选。

## 后续实验排序

1. **固定字 tensor/padding重综合：先k8、k11、k12，再选一个前段高成本loader。**
   先复核原规划是否已尝试过相应padding自由度；在相同1,220地址字表上调整
   分组次序、kernel关系和未访问行完成。后段各有2根qubit余量，当前201乘积；
   若仅三批各省1 AND/单遍，也只有6T总、约0.01318%总GM，适合短预算实验。
   更有意义的目标是让全体ANGLE成本下降1%以上：对应约0.556%化学/0.186%总GM，
   但当前没有这样的候选。需要保留生成代码并证明HMR相位/清理，不能只报计划乘积数。

2. **固定实际字与tree的约束面refit。**
   以当前W/H2_I为warm start，目标lambda_eff，在原版固定shifts下显式保持
   两项误差、E_gap和域约束；梯度/近似Hessian必须处理绝对值与特征空间活动集。
   先做短步长下降和恢复，不改loader；数值成功后再手动完整官方验证。
   目标按真实lambda下降量判断，不把R55 E作者数字当作本地成绩。

3. **扩大gauge/helper基与commuting schedule的联合搜索。**
   32维物理gauge零空间是可用结构，不是32个免费qubit。
   固定四QUADS模板只剩最多10T，不值得无界随机扩样；
   新模型应明确helper计算/保留/恢复的成本，并尊重k0/k2/k3已达128Q。
   先证明最终分量路径符号一致与双方向公共helper，再综合一个实际窗口。

4. **C44/C43的固定字系数秩压缩，或结构约束的重新分解。**
   保持R8/B143/brot8/J5和loader成本时，C44可省79T，
   允许lambda最多上升约0.5231%仍打平；C43省157T，允许约1.0450%。
   这些只是成本预算，不证明能在20mHa内拟合。可先对每rho的X因子做
   低秩/列混合初始化，再约束重拟合；直接删列没有已证可行性。
   固定角度字的C方向优先于破坏地址结构的B方向。

## 不宜直接推进的参数改动

以下都是保持lambda与loader T不变的成本情景，除注明的数值探针外没有新电路：

| 改动 | 数值/资源结果 | 判断 |
|---|---|---|
| J5→J4 | Q427→419；ANGLE双遍T最多8,729.85才打平，允许约+3.43% | 新19-loader家族必须实测；当前J5 helper/低位结构会变 |
| J5→J6 | Q435；ANGLE T须低于8,160.81，至少省约3.31% | 不是免费合并 |
| brot8→9 | Q427→735；假设ANGLE不变成本×1.6265 | 官方QROAM阶梯使提精度很贵 |
| brot8→7，原权重简单舍入 | floor：error_1≈2.157Ha/error_2≈0.476Ha；nearest-even：2.022Ha/0.421Ha | 两个局部数值探针均失败，不能直接降位宽；不否定重新训练 |
| B143→144 | 多362T，假设不变成本+2.3846% | 正跨成本阶梯 |
| B143→128 | Q698，假设不变成本×1.5056 | 更小B不保证更便宜 |
| 单独减loader scratch | 总Q仍由inner303临时位主导 | 用于换更少T，不直接计Q收益 |

## 证据、来源与生成链

本轮结果在 `artifacts/20261105_maoxin_v2/dfthcsos/`：

- `analysis.json / analysis.log / recovered_words.npy`：实际字恢复、资源、数学指标、GF(2)与成本情景。
- `parameter_probes.json / parameter_probes.log`：5个联合权重缩放＋2个7bit舍入探针。
- `sources/`：下列公开notebook源码快照及Busy dataset V11文件列表。
- `sources/atakan_static/datasets/qcc-pi-gauge-carry-padding-v3/`：
  静态提取的 `emitter.py`、`rebuild.py`、`design.json`、15个plans及原始NOTICE。
  原外部生成器未执行；分子训练/原始tensor计划搜索未复现，
  `rebuild.py`仍要求其固定上游source_factor。当前报告不宣称已完成全源重建。

公开方法归属：

- [Maoxin V2 / 365853243](https://www.kaggle.com/code/maoxin123/lb-24-786-pi-gauge-loaders-transferred-weights?scriptVersionId=365853243)：符号不变的权重迁移与组合。
- [Kirill Q19 V7 / 365875650](https://www.kaggle.com/code/kirilltym/quantum-compilation-19?scriptVersionId=365875650)：独立迁移检查、已有可达相位审计、作者单次完整官方化学PASS。本轮未重跑这些证明。
- [Atakan V8 / 365784558](https://www.kaggle.com/code/atakanaldemir/qcc-gap-3-residue-repair-and-c43-native-compiler?scriptVersionId=365784558)：所采用π-gauge/公共decoder/loader方法。
  本轮MCP实际源码快照为当前V9，保留了这套化学生成代码；新增DQI内容不属于本化学实验。
- [Busy V18 / 365807681](https://www.kaggle.com/code/busyaprime/lb-24-73387-top-30-qcc-notebooks-re-verified?scriptVersionId=365807681)：R55 D权重与约束面方法说明。
- [Syed V3 / 365752919](https://www.kaggle.com/code/syed3000/vqcc-own-circuit-portfolio-notebook?scriptVersionId=365752919)：(8,143,45)表及前4批计划；
  Lera为compact-group/emitter上游，qwertykeypadapple为kernel搜索上游，
  [HW19 V23 / 365772080](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook?scriptVersionId=365772080)为padding自由度方法。

未运行完整官方验证、未查询本账号提交分数、未提交Kaggle、未计算或匹配SHA。
上游源码中自带的哈希字符串仅作为原始材料保存，没有用来执行匹配。
