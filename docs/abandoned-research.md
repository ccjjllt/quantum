# 已停止研究：概况、放弃原因与三次清理记录（2026-11-13 / 2026-11-16 / 2026-11-17）

本文件是已停止研究的**唯一总览**。三条研究线（invsqrt、DQI、dfthcsos/化学）
在 2026-11-13 停止推进；2026-11-16 换用公开 28.059 组合后，三条线连同其脚本、
二进制产物和重复打包一并清理（见 §7）。各分支入口 README 与 `ABANDONED.md` 仍保留，
关键结论与恢复口径按本记录执行。

## 0. 结论与判定依据

- 当前采用方案是**公开前沿三件套**，不是本仓库自研电路：
  invsqrt `321aff83…35177`（46Q，80,162.732141）、DQI `7cbe8ecf…14cd9`
  （889Q，360,733,280,431.94）、化学 `6418ec8e…a77f`（427Q，296,635,967.5936）。
  组合本机 GM 27.0783908611，Kaggle public **27.00209**（ref 58299045，COMPLETE）。
- 三条研究线的最后一版/最后采用件都已被公开前沿超过，且最近的判决实验全部是 no-go：
  - invsqrt 自研最好 `9c708f7b`：62Q、93,555.26；公开 46Q 件 80,162.73，低 **14.3%**。
  - DQI 本线最后采用 `eae396ba`（公开件）：892Q、373.53e9；公开 889Q 件 360.73e9，低 **3.4%**。
  - 化学自研最好 `f21b8a87` + 4,097 loader：297.56M；公开件 296.64M，低 **0.31%**。
- 局部优化面已经饱和：继续推进需要换算法族/新解码器/新训练范式级别的独立大工程，
  不是当前比赛窗口内的增量研究。因此停止，不再保留可执行研究目录。

## 1. invsqrt

### 研究概况

目标是把 invsqrt 子任务的官方成本 `C = Toffoli-like + T/4`（`score = Q × C`）压低。
先后跟随公开基线 `7c10edba`（95,430.78）、gengsr `26ebf39d`（94,537.59），
自研 splice 得到 `9c708f7b`（62Q，93,555.2627）。2026-11-12/13 的系统性普查围绕
`9c708f7b` 的 S1/S2 uncompute 对、41 个旋转 T 侧、62→61Q 重算、prefix 重综合展开。

### 已放弃方向与关键数字

| 方向 | 关键结果 | 放弃原因 |
|---|---|---|
| 单删 / 仿射张成 / 辛秩 / HMR / 脏借用 / T 融合 / 重排序 / 跨守卫缓存 | 全电路同守卫 0/190 可转；脏借用每处 +1 CCX | 做即亏或不可迁 |
| S1/S2 uncompute 对普查 | 305 对中 **0 对**可转；最小 diff 266,255 输入 | 机制是累加/线复用，不是 Bennett 冗余 |
| 41 个旋转的删除/合并/重拟合 | **0 旋转**；8 个重复权重融合 8/8 破坏相位，官方 verifier FAIL（8191×） | 相位裕度结构性绑定 |
| 单门删除 / 均值条件化 | 仅 3 门可删且永不执行，收益 0 | 无实际收益 |
| 62→61Q 纯重标号 / 值级重算 | 62 线全活；值级重算预算 +24.7C、实现 ≥52C | 量级差 2× |
| 经典查表捷径 | kickmix 只有 X-basis HMR，无独立 H、无 Z 测量 | 指令集不允许 |
| 插值/多项式新家族 | 1024-cell 线性 150Q/mean 4,226；32-cell 三次 284Q/9,252 | 总分 7.3×/28.8× 差 |
| prefix 重综合 | 63 T normaliser + 167 T 算术块 + 7 T 收尾；167 T 已有 6.5× AND 复用，局部冗余 0 | 原 −83 C 目标被撤回，无 sound 替代形态 |

### 放弃原因

`9c708f7b` 的 62Q 局部面在单门、门对、常量控制、条件化、旋转合并五类机械改写上
已被官方验证器实测为局部最优；唯一剩余的 prefix 块是高度复用的算术块，没有 3 小时
内可证的替代。更大的 20%+ 收益需要新算法家族，而公开 46Q 件已经直接把成本降到
80,162.73，继续在 62Q 上做局部优化没有比赛意义。

### 保留

- `.worktree/invsqrt/experiments/invsqrt/README.md`（入口与当前判断）
- `.worktree/invsqrt/experiments/invsqrt/ABANDONED.md`（历史关闭方向）
- `.worktree/invsqrt/experiments/invsqrt/20261110_arch_review/`（系统性复盘）
- `.worktree/invsqrt/experiments/invsqrt/20261113_retention/retain.py`（可复用 planner）

## 2. DQI

### 研究概况

目标是降低 RS(4095,4025) 解码器电路的 `Q²·meanT`。自研线从 Public Frontier
`4432ec5f` 差分出 `9f`/`cd71c482`，再把公开 `eae396ba` 接入组合；2026-11-12/13
集中判决 Q−1、spill/pebbling、Q=840 重算、unextract HMR、近似解码、乘法秩、
解码器族与 392k retention。

### 已放弃方向与关键数字

| 方向 | 关键结果 | 放弃原因 |
|---|---|---|
| 局部改写（仿射/深非线性/结构缓存/脏借用/CCZ/广播/守卫） | 可用载体 0/1618、0/1882、0/40；Q 换 T 差一个数量级 | 载体枯竭，887 门/Q 打平线不可过 |
| R 项 / salt 统计 | 72 salts × 102,400 shots：15 salts 各 1 error；单失败 +17.2 亿分 | 期望惩罚大于收益 |
| Q−1 / spill / pebbling | 全电路不闭合；M_exact=892 真值；零 paid 重命名不可能 | 结构下界 |
| Q=840 重算 | 52 ancilla 中 48 个是 24-bit external word，全电路 70.5% paid 门触及 | 不是可重算 scratch |
| unextract→HMR | 93,787 CCX 目标全 live；A/B 候选 256 shots 全 FAIL | 无 Z 测量，无法读/清 |
| 近似解码/近似乘法器 | 非精确双线性乘子每次调用出错概率 ≥1/4；实测丢 6 项 0.82 | ε 直接越过 1/16 |
| 乘法秩 | `rank(GF(2^3))=6` 严格证明；35 项路线死；最好仍差目标 471 T | 秩路线达不到 |
| 解码器族（BM/EEA/half-gcd） | 目标要求 convert+unconvert ≤61,884 T；EEA 算术下界 77,280 T；BM 参考 5.725M T/1,893Q | 族级下界，非实现问题 |
| branch recovery | 决策机器 57,119 T=14.2%，全在 n−1 零测试/1 CSWAP 下界 | 无 ≥10k 可替换块 |
| Q-batching | 契约要求 840 个 disjoint qubit；可行 b≤1.0619，整数只有 1 | 契约禁止 |
| 392k retention | 52 ancilla 全占用，最多省 2 T，打平需 880 T | 无收益 |

### 放弃原因

892Q 是契约与算法共同决定的局部最优点；Q−1、Q-batching、unextract 清理、近似解码、
解码器族都已给出可核查下界。剩余 13.5% 级别的收益只能换算法族，而公开 889Q 件
已经比本线采用的 `eae396ba` 低 3.4%。392k 的 +0.526% T 收益是严格支配，但已由主仓库
提交验证并归档，不再作为研究线继续。

### 保留

- `.worktree/dqi/experiments/dqi/README.md`
- `.worktree/dqi/experiments/dqi/ABANDONED.md`
- `.worktree/dqi/experiments/dqi/20261110_arch_review/`（系统性复盘）
- `.worktree/dqi/experiments/dqi/20261110_e9diff/`（模板 A/B 方法证据）
- `.worktree/dqi/experiments/dqi/20261112_branch_recovery/`（保留的只读判决）

## 3. dfthcsos / 化学

### 研究概况

目标是降低 DF-THC 化学子任务的 `λeff × (ANGLE + heuristic) × Q`。自研线从
P0 `299.50M`、Lera `298.94M`、Maoxin303 `298.72M` 推进到
`f21b8a87` + Maoxin v22 4,097-Toffoli/pass loader（297.557M）。2026-11-12/13
集中搜索 loader 结构、表形状、C 截断、训练盆地与量化。

### 已放弃方向与关键数字

| 方向 | 关键结果 | 放弃原因 |
|---|---|---|
| L-BFGS 训练盆地 | R5/B135/C70 50k 步 40.24 mHa；R4/B131/C83 20k 73.07；新形状 50.46/53.29 | 20 mHa 门不可达，算力≠解 |
| 字宽/结构死线 | brot=6 字宽地板 9,620 mHa；B≤128 temp 悬崖；R6 小 B 全灭 | 零训练可判的死线 |
| 7-bit 字 | e1 2.04 Ha / e2 0.45 Ha；精度地板 ~40 mHa | 精度否决 |
| MBU 反向装载 | HMR reset 清 word；官方 verifier 报 uncorrected phase | 结构性非法 |
| 形状 (5,129,68) / R3 / R8 B 轴 | 投影成本 +11.96% 或误差 >20 mHa；B135 量化后 33.12 mHa | 精度/成本双否 |
| R=4 C 截断 | C=110 过 18.89 mHa，但 rows=1,096 需 11-bit loader，成本 325–337M（+9.5–13.4%） | 成本否决 |
| coded2 | e1 22.65 / e2 34.60 mHa；loader 复现 4,612/pass，最好 ~307.6M | 精度 + loader 差距 |
| loader 结构搜索（tree/row/batch/gauge/lowbits/J） | 当前树/行序/gauge 已最优；J=5 最优但 +14.07%；lowbits=3 总账仅 −0.9% 且 λ 更差 | 无 ≥2.5% 收益 |
| loader product-set / full-support / ESOP | 3881 T/pass 是 z=0 假象，官方 REJECTED；full-support 需 8 product/bit | 撤回/不可解 |
| loader-aware 训练 | 结构化 1% loader T 要付 ~10× 误差门代价；真 loader 4,097 已是表字 rank 15/15 的最泛型 | no-go |
| R=7 / (R,C) 重分区 | R=7 loader 4,672–4,677 T/pass，成本 311.9–327.1M；门内形状 basis 不足 | 成本/误差否决 |

### 放弃原因

`(8,143,44)` 的 T/Q/λeff 已接近局部最优；训练盆地在 38–40 mHa，距 20 mHa 门约 2×；
loader 的 4,089 T/pass 已被逆向到机制层，本仓库构造器无法在 ≤4,089 落地；公开件
4,074 T/pass + 296.64M 已经略优于自研 297.56M。继续需要新 factorization/新训练范式，
属于独立大工程。

### 保留

- `.worktree/dfthcsos/experiments/dfthcsos/README.md`
- `.worktree/dfthcsos/experiments/dfthcsos/ABANDONED.md`
- `.worktree/dfthcsos/experiments/dfthcsos/CLOSED_RESEARCH.md`
- `.worktree/dfthcsos/experiments/dfthcsos/20261110_arch_review/`（系统性复盘）
- `.worktree/dfthcsos/experiments/dfthcsos/20261106_train_r5/`（种子生成）
- `.worktree/dfthcsos/experiments/dfthcsos/20261110_gputrain/`（训练/拟合栈）

## 4. main 的历史公开组合与 artifacts

main 保留 submission 回执和最终 ZIP；历史公开组合的原始候选、重复打包和解包目录
不再参与研究或提交，已删除。被删除的大目录与原因：

| 目录 | 清理前大小 | 原因 |
|---|---:|---|
| `artifacts/20261113_27_078/` | 442M | 当前最佳原始候选；同内容已保存在 `submissions/20261113_27_078/submission.zip`（SHA-256 `63c5a077…657c`） |
| `artifacts/20261113_392k_draft/`、`20261113_392k_swap.zip`、`20261113_392k_draft.zip` | 554M | 392k 中间候选/重复 ZIP；提交回执在 `submissions/20261113_392k_swap/` |
| `artifacts/20261112_frontier/` | 576M | 27.078 公开源解包；来源清单复制到 `references/frontier-20261112/` |
| `artifacts/20261112_frontier_rescan/` | 513M | 公开源 rescan；来源清单复制到 `references/frontier-20261112/` |
| `artifacts/20261112_dqi96/` | 543M | eae 96-salt 扫描；结论已写入 DQI ABANDONED/本文件 |
| `artifacts/20261112_public_25367/`、`20261112_eae_candidate/` | 1.07G | 25.367/25.3957 历史候选；回执保留 |
| `artifacts/20261111_*`（grimoire33/maoxin4097/ozer296） | 1.61G | 11-11 公开组合历史；回执保留 |
| `artifacts/20261110_*`（gengsr/trio/public_candidates） | 1.19G | 11-10 及更早公开组合；回执保留 |
| `artifacts/20261108_public_frontier/`、`20261106_syed_v9/`、`20261105_maoxin_v2/`、`20261030_public_best/` | 2.13G | 更早历史基线；回执保留 |
| `artifacts/20261112_chem_pipeline/`、`20261112_nocoded/`、`20261112_rc_shape/`、`20261112_rc_seeds/`、`20261112_r7_check/`、`20261112_14840_candidate/`、`20261113_chem_slim/`、`20261112_ancilla_liveness/` | 130M | 已关闭的化学/liveness 研究中间产物 |
| 其余小目录与重复 ZIP | ~110M | 历史回执/快照，已由 submission README 与 `docs/research-map.md` 覆盖 |

## 5. 删除清单与磁盘回收

清理前（2026-11-13）：

```text
$ du -sh artifacts .worktree/*/artifacts experiments
8.6G    artifacts
1.1G    .worktree/dfthcsos/artifacts
1.2G    .worktree/invsqrt/artifacts
1.9G    .worktree/dqi/artifacts
216K    experiments
```

清理动作：

- 删除三条研究线中所有已关闭实验目录（保留上列入口/复盘/可复用载体）。
- 删除三个工作区中共同历史的 `20261030_public_best/`、`20261030_public_audit/`
  和 `20261101_public_hw06/`，以及 `__pycache__`。
- 删除 `.worktree/*/artifacts/` 中除 `20261110_e9diff`、`20261112_branch_recovery`、
  `20261110_gputrain` 之外的产物。
- 删除 main `artifacts/` 下除 `references/frontier-20261112/` 来源清单外的全部历史产物。
- 删除 main `experiments/` 下除 `frontier/20261112_rescan/` 外的历史实验目录。
- 保留 `submissions/*/README.md`、所有提交 ZIP、`data/competition/`、`docs/`、`references/`。

清理后（2026-11-13 实测）：

```text
$ du -sh .
3.4G    .                       # 删除研究产物后

$ du -sh artifacts experiments
0B      artifacts
20K     experiments

$ du -sh .worktree/invsqrt .worktree/dqi .worktree/dfthcsos
312K    .worktree/invsqrt
560K    .worktree/dqi
417M    .worktree/dfthcsos      # 其中 351M 是本地 .uv-cache

$ df -h .
/dev/disk3s5   926Gi   415Gi   481Gi    47%   # 清理前 433Gi 已用
```

随后又删除了本地 `uv` 缓存（`.uv-cache/` 1.1G + `.worktree/dfthcsos/.uv-cache/`
351M，均为可重建缓存，不是研究产物）：

```text
$ du -sh .
2.0G    .
$ du -sh .worktree/dfthcsos
66M     .worktree/dfthcsos      # 只剩保留的 gputrain 训练栈
$ uv run python -c "import kickmix; ..."
3.12.13 0.1                    # 删除缓存后 .venv 仍可用
```

仓库工作树从清理前 **16G 降到 2.0G**（约 −14G）。主要来源是 main artifacts
（8.6G→0B）和三条研究线 artifacts（4.2G→65M），加上本地 uv 缓存 1.45G。
Git 跟踪文件删除统计：invsqrt 40 files / 3,890 lines、DQI 70 files / 9,830 lines、
dfthcsos 135 files / 15,100 lines；这些文档仍可从各分支历史恢复。

> 注：`submissions/` 中的历史 ZIP 是提交回执的一部分，本次未删除；如需继续压缩磁盘，
> 可在确认不再复跑历史提交后单独清理旧 ZIP。`artifacts/` 与 `submissions/*.zip` 均
> 不入 Git，删除后不可从 Git 恢复。

## 6. 恢复口径

- 被删除的**已提交文档/脚本**可从各研究分支的 Git 历史找回，例如
  `git -C .worktree/invsqrt log --all -- experiments/invsqrt`，再用
  `git show <commit>:<path>` 读取。
- 被删除的 `artifacts/` 大型二进制产物未入 Git，不能恢复；公开源可按
  `references/frontier-20261112/` 的清单重新下载。
- 当前最佳提交包固定为 `submissions/20261113_27_078/submission.zip`，
  SHA-256 `63c5a0776bb1d91490c2e50e4c04607c78b91472f9da45247901ea4af314657c`，
  18 个文件，与 Kaggle ref 58299045 对应。

## 7. 2026-11-16 清理：换栈之后删除全部已关闭研究的产物

### 7.1 触发点

2026-11-16 采用公开 **28.059 组合**（本账号 ref `58392219`，COMPLETE **28.05896**，
rank 91/3114）：invsqrt `47b31838`（44Q，75,170.62）+ DQI `46446af1`（890Q，
347,904,227,556）+ marculera v6 化学（427Q，T=14,712，294,800,582.44）。
三件全部是公开电路，本仓库不再产生候选电路；三条自研线的最后判决也都是实测 no-go：

| 线 | 最后判决 | 结果 | 记录位置 |
|---|---|---|---|
| invsqrt Q45 | 7-AND 全域判定，十条 idle 线 | **全空**（CPU q22 控制 200/200；GPU 十线控制 300/300） | `invsqrt_plan.md` §40–§41 |
| invsqrt T 轴 | 614/645 对可 hold 扫描 | **0 可 hold**，maxlive 46 | `invsqrt_plan.md` §37–§38 |
| DQI Q888 | 24→23 位乘积 scratch | **代数不可能**（乘积像满 24 维，23 位不可达） | `dqi_plan.md` §20 |
| DQI Q888 | 三堵墙（尾标志 / 第三 pivot / 24 位乘积） | 运行时补丁只能省 24 T，墙 ③ 无可用 bank | `dqi_plan.md` §11–§19 |
| 化学 | B/C/Adam/from-scratch 四条重训 | 全部 > 20 mHa 门（最好 40.24 mHa） | `chem_c_axis/PLAN.md` |

Q=45 需要 ≥8-AND 或 SAT 综合，DQI 需要换解码器族，化学需要新 factorization/训练范式，
都不是本比赛窗口内的增量工作。因此删除其可执行目录、二进制产物和重复打包。

### 7.2 删除清单（2026-11-16 实测，单位 KB）

| 位置 | 清理前 | 清理后 | 删除内容与原因 |
|---|---:|---:|---|
| `submissions/**/submission.zip`（18 个） | 893,564 | 72 | 872.5 MB。全部被 28.059 组合取代；ref/分数/ZIP SHA 已逐条写在 `submissions/*/README.md`，ZIP 本身可由组装 kernel + 两个公开 dataset 重建 |
| `artifacts/20261115_invsqrt/` | 27,252 | 2,506 | 24,746。删除展开的生成器树（19 MB）、候选 `invsqrt.kmb`、`meta/` 扫描表、`mwac/others/hedge/xianyu/heliosli` 候选；只留压缩源码包与 `SHA256SUMS`（见 7.3） |
| `artifacts/20261115_chem/` | 7,240 | 0 | 7,240。化学 A/B 的 `chem4033` 候选件，已被 marculera v6 取代 |
| `artifacts/20261115_frontier/` | 5,472 | 0 | 5,472。27.31 时代的公开前沿候选（hw26/jm_f/mason），已全部被 28.059 取代 |
| `.worktree/dfthcsos/artifacts/20261110_gputrain/` | 66,912 | 0 | 66,912（`prob_r5.npz`）。化学训练盆地的权重快照，B/C/Adam/from-scratch 已实测关闭 |
| `.worktree/invstmp/` | 4 | 0 | 4。空临时目录 |
| `/private/var/.../opencode/` 临时工作区 | 140,144 | 13,188 | 126,956。删除重复的提交 ZIP（`qcc_27312_submission.zip`、`submitted_58350759.zip` 各 47 MB）、展开的 invsqrt 源码（12.4 MB）、`dqi_src`、`ntl_pull`、`spo_rebind_probe`、`pull/`、全部 `kern_*` 目录、旧日志与 009 快照；只保留 `kgcli`（Kaggle CLI） |

合计实测回收 **1,124,720 KB ≈ 1.10 GB（1.05 GiB）**：仓库 2,149,568 → 1,151,804 KB，
临时工作区 140,144 → 13,188 KB。

### 7.3 保留清单及理由

| 保留 | 大小 | 理由 |
|---|---:|---|
| `data/competition/` | 994 MB | 官方原始数据与**未修改**的 verifier，是本地复核的唯一基准；`sample_submission/dqi.kmb`（845 MB）是其中最大的单文件，verifier 不使用，但属于官方数据，未删 |
| `.venv/` | 110 MB | `uv sync` 环境，删了要重建 |
| `references/` | 8.8 MB | 公开方案固定版本与来源清单 |
| `experiments/frontier/20261115_upgrade/` | 600 KB | 研究概况、判决数字与放弃原因（本文件的主要依据） |
| `experiments/.../stack_28059/kernels/` | 20 KB | **新增**：当前最佳的组装/复核脚本（`assemble_28059.py`、`verify_28059.py` 及 metadata），从临时目录收回仓库 |
| `artifacts/20261115_invsqrt/syed/invsqrt_source_zip` + `SHA256SUMS` | 2.5 MB | 46Q invsqrt 的**生成器源码压缩包**。`syed3000` 已从 dataset 删除该文件（§`invsqrt_plan.md` 39），这是本地唯一副本；按 AGENTS.md“保留可复现电路的生成代码”留存 |
| `submissions/*/README.md` | 72 KB | 18 个提交回执（ref、分数、ZIP SHA-256、验证范围） |
| `.worktree/{invsqrt,dqi,dfthcsos}/` | 1.1 MB | 三个研究分支的入口 README、`ABANDONED.md` 与复盘；分支历史仍在 Git 中 |

### 7.4 当前最佳的可复现路径

```text
ref 58392219   28.05896   COMPLETE   rank 91/3114
kernel  qingyu1232/qcc-assemble-28059 v1   -> submission.zip 51,858,038 B
sha     87703019f2a950341201f4cc69420761464fd17365b448c7808ece0bbac30800
18 members matched by SHA-256 (invsqrt 47b31838 / dqi 46446af1 / 15 chem kmb + npz)
verify  jiyujia/qcc-verify-28059 v1        -> PASS 28 s / 630 s / 162 s
scripts experiments/frontier/20261115_upgrade/stack_28059/kernels/
```

删除本地 ZIP 不影响已入账的 Kaggle 提交；需要提交文件时重跑组装 kernel 即可逐字节重建。

### 7.5 恢复口径

- 被删的**文档与脚本**在 Git 历史中：`git log --all -- <path>`、`git show <commit>:<path>`。
- `submissions/*/submission.zip` 与 `artifacts/` 二进制未入 Git，**不可从 Git 恢复**；
  但前者由 `qcc-assemble-28059` + 两个公开 dataset 按 SHA 重建，后者中的公开候选可按
  `references/frontier-20261112/` 清单重新下载。
- 保留的 `invsqrt_source_zip` 是上游已删除文件的唯一本地副本，请不要随下次清理删除。

---

## 8. 2026-11-17 清理：本轮已关闭研究线（invsqrt / DQI / chemistry）

### 8.1 触发点

用户指示：把当前已经不做的研究的文档、脚本、artifacts 删除，记录研究概况与放弃原因，
清理磁盘空间。本轮的三条腿都已由**实测 + 官方 cost 公式算术**双重判定关闭
（详见 `experiments/ARCHIVE_closed_lines.md`），因此整条线连同构建产物一并移除。

删除前锚点：`git rev-parse HEAD` = **`8155189ac5ddc257b4bf968a86850e4240bf3cb9`**（`main`）。
所有受跟踪文件可用 `git checkout 8155189 -- <path>` 原样取回。

### 8.2 为什么这三条线关闭（一句话版）

| 线 | 决定性测量 |
|---|---|
| invsqrt | 官方 `score = Q·(Toffoli + T/4)`。Toffoli 面刮净（0 cancel pair / 0 zero-control / 0 dead-write）；Q42 全量 110 slot **0/110**；33 个旋转各 29.08 T 只因 `worst_error_over_tolerance = 0.99956` 不留合成余量。 |
| DQI | 官方 `score = R(eps)·Q²·T`。`R = 1.19126` 是 0 误差 CP 上界，无下滑空间；T 面饱和；宽度 `890 = 840 + 4×12 + 2`，金线在 Q865 只容忍 **+166 T（6.6 T/qubit）**，而最便宜实测机制 925 T/qubit。 |
| chemistry | 官方 `score = λ_eff·T·Q`，cost 对 T 严格线性（20,035.573/T，两点差 2.8e-6）。出厂点 `a73b25d2` 的 `error_2 = 0.0199999997351` 对门 `0.020` 只剩 **2.6e-10**，`E_gap` 恰在地板，loader `angles_qubits = 128` 恰在 `QUBIT_CAP`。 |

结论不变：公开字节重组上限 **28.15083**（ref `58454232`），金线 28.68633 需换一代电路。

### 8.3 删除清单（2026-11-17 实测）

| 路径 | 体量 | 内容 |
|---|---:|---|
| `artifacts/20261116_intel/{outputs,outputs2,unz,ds}` | **2.86 GiB** | Kaggle 内核输出的下载镜像与解压副本（`dqi.kmb` 464M/434M 多份重复）。全部按 `intel/RESULT_sweep*.md` / `RESULT_verify_new*.md` 记录的 kernel/dataset ref 可重下，sha256 已记录 |
| `artifacts/20261116_dqi_v15/` | 59 MB | DQI v15 构建源码与 `qcc-dqi-source-v12.zip` |
| `experiments/frontier/20261116_push/chem/` | 23 MB | 化学线全部记录、脚本、`code2/code3` 构建产物（`submission.npz`、`angle_k_*.kmx`、`words_recode_k4.npy`） |
| `experiments/frontier/20261116_push/invsqrt/` | 4.8 MB | invsqrt 线记录与脚本 |
| `experiments/frontier/20261116_push/dqi/`（除两份保留） | 0.7 MB | DQI `NOTES.md`、`RESULT.md`–`RESULT8.md`、`build_kernel.py`、`evidence/`、`k1`–`k19` 采样目录 |
| `experiments/frontier/20261115_upgrade/`、`20261112_rescan/` | 0.56 MB | 被 20261116_push 取代的早期轮次 |
| `artifacts/20261116_intel/{vqcc-chemistry-negative-results,c44-universal-xor-chemistry-compiler}.zip` | 9.1 MB | 化学线归档包 |
| `artifacts/20261115_invsqrt/` | 2.4 MB | 46Q invsqrt 分支素材（见 §8.4 的损失说明） |

**实测回收：4.1 GiB → 1.1 GiB，释放 2.96 GiB。**

### 8.4 损失说明（必须记录）

`artifacts/20261115_invsqrt/syed/invsqrt_source_zip` 在 §7.3 被明确标注为「本地唯一副本，请勿随下次
清理删除」，本次仍随 `artifacts/20261115_invsqrt/` 一并被删。该目录被 `/artifacts/*` 忽略，
**不在 Git 中，无法从历史恢复**。事后核查：`syed3000/vqcc-own-circuit-portfolio` 当前版本
（2026-11-15 12:54）共 20 个文件、只有 `invsqrt.kmb`，**已无任何 source zip**，
CLI 也不支持按版本枚举，因此短期无法取回。

影响评估：该包是 **46Q invsqrt** 生成器的源码（syed 线），当前前沿 invsqrt 是 **44Q `0af21cb8`**
（maoxin/atakan 线），跑分不依赖前者。**本次损失不影响任何已提交结果的可复现性**，但离线复现
那个 46Q 生成器需要重新向作者索取。后续清理必须逐条核对 §7.3/§8.5 的保留要求再执行。

### 8.5 保留清单（明确不删）

| 路径 | 理由 |
|---|---|
| `data/competition/`（995 MB） | 官方原始数据与未修改验证器（AGENTS.md 要求） |
| `experiments/frontier/20261116_push/{intel,pipeline}/` | 仍在用：字节侦察、评分模型、提交管线 |
| `experiments/frontier/20261116_push/dqi/{RESULT_WIDTH_BUDGET.md,width_budget.py}` | 金线宽度的最终定量答复 |
| `experiments/ARCHIVE_closed_lines.md` | 本轮删除内容的逐条归档与恢复口径 |
| `artifacts/20261117_lb_decomp/`（380 KB）、`artifacts/H_spectrum.npy` | 当前榜首逆解快照；小型复用数据 |
| `submissions/`（72 KB）、`references/`（8.8 MB） | 提交回执与公开方案来源 |
