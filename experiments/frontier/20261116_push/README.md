# 2026-11-16 大幅提分推进

目标：在公开 28.09 组合之上做原创改进，优先攻击单项大杠杆，全部电路实验在 Kaggle CPU 上执行。

## 实时基线

- 本账号 public **28.10154 COMPLETE**，ref **58436763**（f2cdab0b + 66b4f18b + bdae290f，GM 28.10154193）；已提交 **28.12769** ref **58442668 PENDING**（0af21cb8 + 66b4f18b + bdae290f，GM 28.12769291）。今日额度已用完。
- 已提交三件：invsqrt `f2cdab0b`（44Q，75,006.38）、DQI `ccc2ab84`（890Q，347,375,470,572）、
  chemistry `sub1`（427Q，T=14,712，294,762,697.44）。三件均用未修改官方 verifier 全量 PASS。
- 公开最佳三件：同一 invsqrt/DQI + chemistry `bdae290f`（294,762,632.08），本地 GM 28.0948754；
  正在按同一 CPU 管线复核并做一次银牌尝试（榜上 rank 92 恰有一个 28.09487）。
- 银线 rank 156 = 28.09486；金线 rank 16 = 28.65386；榜首 30.28512。
- 公开前沿在 2026-11-16 02:52 UTC 已到 **28.09486**：`f2cdab0b` invsqrt + `ccc2ab84` DQI +
  chemistry npz `bdae290f`（294,762,632.08）。这是一个 **143 队并列（rank 88–230）**，
  银线 rank 156 在并列内部；晚提交的同一分数会落在并列末尾（约 rank 231），**不保证银牌**。
  下一档公开分是 28.09498（rank 87），所以短期目标应是 **>=28.09490**。
- 当前最近公开 refit：chemistry `sub1` 294,762,697.44，组合 GM 28.094873（仍落在并列内，
  不足以单独拿银）；boristown `bdae290f` 更便宜 65，是公开 chemistry 最好件。

## 并行研究线

| 目录 | 负责 | 目标 |
|---|---|---|
| `intel/` | 公开前沿侦察 | 11-16 19:27→23:27 UTC 扫到 4 新字节：DQI `f425ea20`（kernel 内嵌官方 JSON 346,992,317,312.82，组 0af+chem 可达 GM 28.13137，待独立验证）、`b0983d55`（engine claim）、chem `a970f175`（未评分）、`93326853`（隐含 ~294,762,409）。chem swap：`703843d3` 比 bdae 高 +3.79e-06 GM，不值 slot。见 `intel/RESULT_sweep2.md` |
| `invsqrt/` | invsqrt Q/T | f2cdab0b Q44 硬地板；**0af21cb8 新机制已探明**：3 tail 转 HMR 双分支 −4.75 mean T；剩余 4 head（12139/12142/12596/13037，−2…−4 mean T / +0.01…+0.02 GM）但 v27 emitter 私有无公开重发点（R6 已证），手工不可构造。见 `invsqrt/RESULT5.md`、`RESULT6.md` |
| `dqi/` | DQI Q/T | **Q/T peephole、v15 调度、decoder-level、structural、66b4 gadget 全部关闭**：RESULT5 exact T=384,003，decision <1T，retain +2.369%；RESULT6 out-of-place/v13/ladder 不可；RESULT8：66b4 gadget 每 site −20T 共 −820T，k19 全磁带普查 G1 41/41、G0 0/0，无剩余可转。见 `dqi/RESULT5.md`–`RESULT8.md` |
| `chem/` | chemistry T | **R=8/R=5/λ/code/新words/C轴/emitter/新R=7,9,10,12 均已关闭**：RESULT4 re-code floor 36.16/63.24 mHa，C=43/42 floor 21.23/23.26 mHa；RESULT5 emitter k9 +2/k10 +3/k12 +4/k14 +4；RESULT6 R7 cont 53.35/quant 66.16，R9 40.84/53.31，R10 41.46/56.21 + Q697，R12 47.30/61.75 + Q697。冻结 294,762,632.08。见 `chem/RESULT4.md`–`RESULT6.md` |
| `chem/CODE2` | loader code search | **已关闭（2026-11-16）**：k=9/10/12/14 的 145-cut basis 并没有比 shipped 更好——shipped products 是 189/190/191（不是 193）；k9 亏、k10/k12 平、k14 −1 不可发射（bit7 XOR bit6 helper / six-AND 独立性失败）。混合包作为负控制 e1=61,130 mHa、e2=11,659 mHa。4,025 保持。见 `pipeline/CODE2_STATUS.md` |
| `pipeline/` | CPU 复核/打包/提交 | 先复核公开 28.09486 件；只有 **>=28.09490** 才提交，避免落在 143 队并列末尾 |

## 计算约束

- 只用 Kaggle CPU kernel（`enable_gpu=false`、`enable_tpu=false`），不在本机跑模拟/验证。
- 三个研究账号：invsqrt=jiyujia，DQI=zhuating，chem/pipeline=qingyu1232。
- 每个候选必须用未修改官方 verifier 全 shots 复核；invsqrt 另加 salt，DQI 另加 salt。
- 不把大 ZIP、权重和日志写入 Git；候选文件留在 Kaggle/`artifacts/`。

## 目标表

见 [TARGETS.md](TARGETS.md)。关键：DQI Q=840 单项 +1.11 GM；invsqrt Q=40 单项 +0.91 GM；
chemistry T=13,000 单项 +1.19 GM。小 refit 只值 +0.001–0.01，不作为主攻。
