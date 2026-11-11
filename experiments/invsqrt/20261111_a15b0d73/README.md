# invsqrt `a15b0d73`（Ozer 25.296 包）确权与新 family 第一轮审计

日期：2026-11-11；分支 `codex/invsqrt-research`；
工作区 `.worktree/invsqrt/`。输入：main 仓 `artifacts/20261111_ozer296/`（外层 zip SHA
`0309dde8…`，内 `invsqrt.kmb` SHA `a15b0d73f720ec75cc7f5bfe1aac96902df241a3035302db74a8d4cf22ed3668`）。
本地复算 SHA 一致（`artifacts/a15b0d73_invsqrt.kmb`，gitignored）。

## 1. 静态先行结论（未跑验证器前不声称分数——已兑现，见 §2）

`kickmix` 直读 + `kmx` 文本逐行 diff（`ozer.kmx` 36800 行 / `gengsr.kmx` 36709 行）：

| 门 | ozer `a15b0d73` | gengsr `26ebf39d` | Δ |
|---|---|---:|---:|
| Q / ops | 62 / 36777 | 62 / 36686 | +91 |
| CCX | 1289 | 1095 | **+194** |
| CCZ | 92 | 93 | −1 |
| CSWAP | **0** | 204 | **−204** |
| Z_POW | 44 | 45 | −1（全部 Clifford，见下） |
| HMR | 864 | 868 | −4 |
| PUSH/POP_CONDITION | 290/290 | 294/294 | −4/−4 |
| 静态 Toffoli-like | **1381** | 1392 | **−11** |

- 最大结构特征：**全局 CSWAP 消除**（204 → 0）。每个 `CSWAP a b c` 被改写为
  `CX b c; CCX a c b; CX b c`（标准 Fredkin→Toffoli 分解，逐处 `d(tof)=0`，
  全尾部/A3 区 40+ 处 hunks 全部中性）。代价是 +2 免费 CX/处，不计分。
  该改写本身**不省分**，只是换基底。
- 真省钱点（per-hunk tof 账本，总 −11）：
  1. **S0 头部重写（gengsr 行 93–500 → ozer 行 93–352）：净 +1。**
     gengsr 用 46 CSWAP + 330 CX 的移位路由；ozer 改用 47 CCX + 177 CX +
     HMR/CZ 条件修复（`HMR q49/q50` + `CZ … if`）。Toffoli-like 反而 +1，
     但引入了"测 + 条件修复"形态——这是全电路唯一新增的 Hosen 式结构。
  2. **S1 新路由循环（ozer 行 ~8413–8830）：约 −10（全电路省分主体）。**
     gengsr 每步 `CCX q21 q<aux> q28 + 2×CSWAP 路由`（aux ∈ {51,40,57,41,25,26}…）；
     ozer 改为全 CCX 路由三元组 + `CCX q21 q<small> q28`（small ∈ 4–11）+
     新增 `CCX q23 q{4–7} q28` 分支，**丢掉 aux ∈ {51,57,25,26…} 的大 aux-CCX**，
     每步省 ~1 门。剩余大 aux-CCX：`q41×2, q50×2, q40×2, q53×1, q17×1`（见 §4 下一刀）。
  3. **S2 相位窗合并（gengsr 行 18229–18379 → ozer 行 18316–18345）：静态 +1，
     执行侧省免费门。**150 行条件 CX 梯子折叠为 `BIT_STORE1 b64003` 合并条件
     （+66 BIT_STORE1 全电路与此同源）+ 1 无条件 `CCX q18 q21 q50` + CZ 扇。
     省的是免费 CX，不计分；+1 CCX 是合并税。
  4. 零散：S1b/S2 头小删（−2/−1 若干）、CCZ −1（S0 区 `g[123:125]` hunk）、
     Z_POW −1 系 Clifford（`Z_POW q47 0.5` 删除 + `q0→q4` 搬移，0.5/1.5 均为 Clifford）。
- **q28 微角梯 42 级逐字相同**（排序后集合全等）；非梯 Z_POW 全为 Clifford。
  A3  ladder 在新电路上一比特未动——T 侧 landscape 与 gengsr 同构（但敏感度结论重跑，见 §3）。

## 2. 验证（官方验证器，只在工作区跑，未动 `data/competition`）

| 范围 | 结果 |
|---|---|
| 烟雾 `--max-x 256 --shots-per-x 256`（65,536 shots） | **PASS**，score 93925.5169，worst 0.99932@x=161 |
| 计时 `--max-x 1024 --shots-per-x 1024`（1,048,576 shots） | **PASS**，score 93925.6213，~20s → 外推全量 <10min（远 <6h，无需报备） |
| **全量默认参数（200,540,928 shots，salt 为空）** | **PASS，score 93925.34907144618**，102s wall。`toffoli_count`（执行均值）1219.834 vs 静态 1381；`t_count` 1.0，`rotation_count` 41，`eps` 2.43404148e-13，`worst` 0.9993237694@x=161，`reaction_depth` 723，`num_ops` 36777，sha `a15b0d73…` |
| L1 掩码探针（Z_POW 最小角 2.886e-11 置零→`eedd33d29a848`，`--max-x 1024 --shots-per-x 64`） | **FAIL**：`x=644: phase error -2.360e-09 turns exceeds tolerance 2.349e-09`（见 §3） |

- 作者声称 93925.35：**确权**，全量实测 93925.3491（小数点后两位一致）。
  vs gengsr 94537.5896：**−612.24（−0.648%）**，是 invsqrt 当前唯一已验证增益点。
- worst 裕度结构与 gengsr 同形（同为 0.9993@x=161，eps 同为 2.43e-13）。

## 3. 新 family 第一轮审计（方向一，全部在 `a15b0d73` 上重跑，不继承旧结论）

**(a) S1/S2 uncompute 对普查：0 可转（重跑证伪）。**
方法：kmx 文本 census，同三元组连续对 + 目标 qubit 间有无读写/HMR 触碰分类。
S1（含新路由循环行 8400–9100，28 对）+ S1 余部（25 对）+ S2（129 对）：
去除目标重写/目标被读（累加/线复用）后剩 7 对"无触碰"候选，
逐对检查发现**控制 parity 在两次计算之间都被 CX 扇重写**（不同的输入值，非冗余），
HMR-between 全部为 0。结论：**0 Hosen-可转对**，机制与 gengsr 同为累加/线复用
（独立重跑得出，非引用旧结论）。

**(b) A3 微角梯逐级敏感度：L1 单删 FAIL（重跑否决）。**
q28 梯 42 角与 gengsr 逐字相同（§1），但按要求重跑仲裁：
L1（2.886e-11）置零候选在小 domain FAIL（x=644，超差约 0.5%，与旧仲裁同 x）。
 worst 裕度 0.9993@x=161 与 gengsr 完全一致，说明裕度在最坏点同样耗尽。
 结论：T 侧剪枝在新电路上同样无空间（L1 探针已否决；42 级全扫未跑——梯子逐字相同
 且 worst 结构一致，全扫期望价值 ≈0，如立项 T 侧才补跑）。

## 4. 下一刀清单（按期望/成本排序，均为假设，需切片验证后才立项）

1. **S1 剩余大 aux-CCX（最高优，−6 量级）。**ozer 仍有
   `CCX q21 q41/q50/q40 q28 ×2各、q53×1、q17×1` + `CCX q21 q1 q28 ×4`。
   已省的 10 门是同形状（aux→small+`q23` 分支）；问题：剩余 6–10 门为何没转？
   若语义同构（支撑集 ≤ 已转步骤），复制该改写即 −6×62 ≈ **−370 分**。
   首实验：取一行 `CCX q21 q41 q28` 切片查其选择语义 vs 已转的 `q21 q51` 行。
2. **S0 头部 Hosen 化推广（中，−?）。**ozer S0 新引入测+条件修复（+1 tof 处）。
   若该形态可替代 S0 剩余 47 CCX 中的若干精确路由，每处 −1 tof。
   首实验：刻画 S0 新 HMR 对 `(q49/q50, b65001/b65002)` 的修复语义，看是否覆盖更多路由位。
3. **S2 合并税回吐（低，−1）。**合并引入的无条件 `CCX q18 q21 q50`（+1 静态）；
   若其功能可被已存在的 `b64003` 条件 CZ 扇吸收，则 −62 分。
   首实验：字仿真该 CCX 在 `b64003=0` 分支是否为恒等。
4. **T 侧：不做。**梯子逐字未动 + worst 0.9993 + L1 已 FAIL，三重证据关闭。
5. **61Q：探针性质。**活性剖面已变（条件门数 −4 对、HMR 分布变），旧 233→372 峰清单
   scoped 旧门序列，需重跑峰值扫描（零成本前置，方向一附带）。

## 5. 记录与范围声明

- 本目录 README 为唯一新增跟踪文件；候选 `a15b0d73_invsqrt.kmb` 与验证 log 在
  `artifacts/`（gitignored，大文件未进 Git；token 未进 Git）。
- 验证范围：invsqrt 全量官方本地 PASS（200,540,928 shots，默认 salt，102s）。
  DQI/chem 未动。无 Kaggle 提交动作。分数 93925.3491 为本地全量实测，
  作者 log（93925.35）仅作一致性对照。
- 旧 family（`7c10edba`）与 gengsr（`26ebf39d`）的 closed 结论（`ABANDONED.md`）
  仍 scoped 原电路，不自动延伸；本报告 §3 为 `a15b0d73` 上的独立重跑。
