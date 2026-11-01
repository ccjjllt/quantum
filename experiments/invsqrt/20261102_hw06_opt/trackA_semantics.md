# Track A 语义恢复：invsqrt 新基线对齐记录

日期 2026-11-02。分支 `invsqrt-generator-rebuild`。本轮只做只读分析与 directed-sample
对照，不提交 Kaggle，不改官方 verifier，未运行官方 200,540,928-shot 验证。
最终独立生成器入口不得读 KMB/tray/嵌入指令串；本轮脚本明确标出 replay 对照区间（见 §7）。

基线：`artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb`，
SHA-256=`bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47`，
62Q，47258 ops。作者完整验证成本 100568.4992（沿用作者数字，本轮未重跑官方验证）。

## 1. 公开材料（Tangfastic v1）获取失败

`webfetch https://www.kaggle.com/code/manwithacat/tangfastic-learning-the-62-qubit-invsqrroot`
两次返回空正文（markdown 格式）/ 仅标题（text 格式）；html 格式返回 Kaggle JS 外壳，
无 notebook 源码。结论：该页内容需 JS 渲染，webfetch 无法提取 256 项系数表、
R/B0、M 与舍入递推的公开解读。已转用本地 `dataflow62.py` / `model62.py` 逆向结果继续，
见 §5。失败证据：text 抓取正文仅一行标题
`Tangfastic | Learning the 62-qubit invsqrroot`。

## 2. 输入坐标（全域验证通过）

脚本 `input_coords.py`，产物 `input_coords.json`
（SHA-256=`75a0bd599b28b3b2ce5e209964150bc6c9922a68d7304e025468fb735ea8c843`）。
规范：`lz=22-bitlen(x)`，`m=x<<lz`，`parity=lz&1`，`s=lz>>1`，
`a=(parity<<7)|((m>>14)&127)`，`delta=m&16383`。
重建：`m=(1<<21)|((a&127)<<14)|delta`（bit21 为归一化隐含前导 1；
a 覆盖 m 的 bit14..bit20，含 bit20；delta 覆盖 bit0..bit13），`x=m>>lz`。

| 检查 | 范围 | 结果 |
| --- | --- | --- |
| 往返一致 `(lz,a,delta)->(m,x)` | 全部 1…3,133,452 | 失败 0，去重全键 3,133,452 |
| `(a,delta)` 单独碰撞 | 全域 | 783,363 个（预期内，见下） |
| x=2/3 碰撞检查 | — | 不是碰撞：`(0,0)` vs `(64,0)` |

碰撞是跨尺度共享尾数的设计行为：x=2/8/32 同为 `(a,delta)=(0,0)`（lz=20/18/16），
x=3/12 同为 `(64,0)`，x=1/4/16 同为 `(128,0)`，靠 lz/s 区分。
旧 `model62.py` 用 shift-13  conventions（7 位地址 +13 位 delta）；
本轮 shift-14（7 位地址 +14 位 delta）以任务书为准，电路侧差异见 §6。

## 3. 新旧基线 diff（静态）

新基线相对 ahmed（`6dbb98b…`，47201 ops）：净 +57 ops，
CCX 1159→1153（-6），CX 29271→29334（+63），其余门类（HMR/R/CZ/CSWAP/Z_POW=68 等）全同。
20 个 diff hunk 全部落在旧 B 区 `[21333,25477)` 内：
第一改写组旧 `[21333,21588)`→新 `[21333,21641)`（+53），
第二改写组旧 `[25458,25477)`→新 `[25511,25534)`（+4）。
改写模式：`CCX c1 c2 t_old` → `CX t_new t_old; CCX c1 c2 t_new; CX t_new t_old`
再加 CNOT 梯子（ancilla 重映射 q16/q20/q40），另有 8 处纯删除的冗余 CCX。
Hphase/A/Lphase 下游无语义改动，只有整体 +57 平移。

## 4. 分阶段对齐（脚本 `align_baseline.py`，产物 `stage_align.json`）

旧边界（REPORT）→ 新边界（+53/+57 两段偏移推导，逐边界 opcode 文本校验全等）：

| 阶段 | 旧区间 | 新区间 | 边界文本一致 | directed 快照旧/新一致 |
| --- | --- | --- | --- | --- |
| 归一化+输入补码 | 3:23（X q21…X q2，逐字核对） | 同（diff 起点 21333 之后） | 是 | —（静态文本等同） |
| Hphase（粗相位，15×q28） | 15244:16127 | 15244:16127 | 起/止是 | — |
| A（编码查表） | 16127:20738 | 16127:20738 | 起/止是 | — |
| B（两级 Horner，改写区） | 20738:25630 | 20738:25687 | 起/止是 | Lphase 入口快照一致 |
| Lphase（细相位，26 条） | 25630:28726 | 25687:28783 | 起/止是 | 入口/出口一致 |
| inverse_B | 28726:32226 | 28783:32283 | 起/止是 | 入口/出口一致 |
| inverse_A | 32226:43870 | 32283:43927 | 起/止是 | 入口/出口一致 |
| unlookup | 43870:46706 | 43927:46763 | 起/止是 | 入口/出口一致 |
| tail | 46706:47201 | 46763:47258 | 起/止是 | 入口/出口一致 |

Z_POW 多重集新/旧全等（68 条）；41 条一般旋转逐条比对
（wire、half_turns 分数、条件栈）全等，且条件栈全部为空——
41 个旋转都是无条件 `Z_POW`，控制信息在目标线计算基值里（见 §5）。
Directed 等价：xs=`[1,2,3,8,128,161,888,3133452]`，
Lphase/inverse_B/inverse_A/unlookup/tail 的入口与出口全 qubit 快照旧/新全等，
B 区改写功能恒等（directed 范围，非官方验证）。

## 5. 缺口状态（脚本 `gap_probe.py`，产物 `gap_probe.json`）

- coarse 控制字：基本解决。15 条 Hphase 旋转（目标全 q28）在 128 地址样本上
  全变、在 22 个 s 样本上全变、在 delta 样本上全不变——coarse 控制是
  `(address, s)` 的纯函数，与 delta 无关、与测量分支无关（旋转在任何 HMR 之前）。
  显式布尔函数形式待写（下一步：用快照真值表拟合）。
- fine 最低残留位：部分平移，未判定。fine 切片新 `[25679,25687)` 与旧
  `[25622,25630)` 文本逐字一致（含 `CX q23 q21` 对 q21 的额外实写），故旧
  `dataflow62` local（128/128 一致）与 prefix（公式 value-id ≠ 捕获 value-id，
  最低失败 op 为该 CCX）结论可平移；旋转后首条测量 op 为新 25688（`HMR`）。
  残留位是否依赖测量分支：计算基值在 HMR 之前与分支无关，但相位修正语义仍需
  full-prefix value-id 重证——本轮未重跑，标为 open。
- LUT_c：open。仅有 address-only 线集候选（op1200 处 21 条、B 入口 16 条、
  A 出口 19 条、Lphase 入口 3 条），256 项系数表的值级解码未做（下一步）。
- 两级 Horner 递推：open。B 区两处改写组位置与两级结构相符，但旧
  `horner_trace` 未确认宽度 19 的 T，本轮仍未把递推套到任何寄存器上。
- M 解码（8 位 M）：open。候选：A 出口 delta-only 8 线 `[0,1,7,8,9,10,11,12]`，
  需值级验证。

## 6. 物理线路地址编码（脚本 `physaddr.py`，产物 `physaddr.json`）

三组单坐标样本（§见脚本 docstring），5 个切点，62 线变化类。
结论：地址编码是非连续的，不可假设连续 19 位 T。

- op1200：address-only 21 线
  `[14,15,16,17,18,19,20,22,25,27,29,31,33,36,37,38,40,41,42,44,46]`，
  delta-only 6 线 `[7,8,9,10,11,12]`，s-only 无纯类（s 经 parity/混合线散布）。
  旧 `packed_words` 的 8 线 `[13..19,21]` 是 shift-13 口径子集，不应直接套用于 shift-14。
- A 出口 address-only 19 线，B 入口 16 线，Lphase 入口仅 3 线 `[15,43,44]`
  （系数经 Horner 与 delta 混合后 address-only 收缩，符合预期）。
- R/B0 17 位与 8 位 M 的公开定义因 §1 缺失，暂以变化类候选代替，不做断言。

## 7. Replay 区间声明（本轮对照，非生成器）

`align_baseline.py` / `gap_probe.py` / `physaddr.py` 读了旧 ahmed KMB 与
`yoyobar_tray.kmx` 派生对照（边界文本、快照等价），且 `generate62.py` 的
A/B/Lphase 整段 replay 状态（REPORT §已证实）仍然有效：
归一化、编码查表、M 解码、两级 Horner、粗/细相位、恢复过程的**生成语义**全部仍是 replay。唯一 semantic 增量是本轮的只读对齐证据（边界映射、控制字
变化类、切片文本恒等），不是生成代码。独立生成器入口（禁读 KMB/tray/嵌入
指令串）尚未开工。

## 下一步

1. 拟合 coarse 控制字显式函数（真值表→布尔式），先判断是否纯查表再写生成式。
2. 在新索引上重跑 full-prefix value-id，判定 fine 残留位与测量分支关系。
3. LUT_c 值级解码：固定 (s,delta) 扫 256 地址，在 A 出口读候选线集的字。
4. M 解码 8 线候选的值级验证；Horner 递推寄存器重找（允许非连续）。
5. 上述语义全部落地后，再写独立生成器并做 directed 差分；官方 200M-shot 验证
   只在有低成本候选或完整语义生成器时手动跑。

## 复现

```
uv run python experiments/invsqrt/20261102_hw06_opt/input_coords.py
uv run python experiments/invsqrt/20261102_hw06_opt/align_baseline.py
uv run python experiments/invsqrt/20261102_hw06_opt/physaddr.py
uv run python experiments/invsqrt/20261102_hw06_opt/gap_probe.py
```

产物（`artifacts/20261102_hw06_opt/invsqrt/`）：
`input_coords.json`（`75a0bd59…`）、`stage_align.json`（`a9b6179b…`）、
`physaddr.json`（`ff4d89a0…`）、`gap_probe.json`（`7d4b3fa6…`）。
官方验证：0 shots（未运行）。Kaggle 提交：无。
