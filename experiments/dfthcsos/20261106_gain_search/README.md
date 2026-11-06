# dfthcsos 收益搜索：已验证的 λ 微增益与新的 R4/R5 结构预算

2026-11-06（北京时间），分支 `codex/dfthcsos-research`。
固定输入为 Syed V9 / run366109544、dataset V9；本工作区只读链接主仓库
`artifacts/20261106_syed_v9/release/dfthcsos/`。

本轮目标：把已有的物理等价自由度落到实际门数，并重新核对 R/B/C
结构预算。结果分成两类，不混写：

- **已实现并本地官方验证 PASS 的收益**：C44 固定字权重 refit，分数
  299,672,935.08，比 Syed V9 的 299,673,103.43 低 168.35（0.000056%）。
  收益很小，但它是真实的、可复现的、78,080-shot 本地验证结果，不是预算。
- **尚未训练的新结构预算**：R4/B131/C82 与 R5/B135/C70 的官方成本模型
  预算分别约 8.8% / 5.3% 的 T×Q 下降，λ 允许分别上升约 9.6% / 5.6%。
  这不是已实现收益；它修正了此前把 R7/B135/C50 当作主攻的判断。

## 1. 已实现：C44 固定字 refit

对原 15 个 loader 和原 `submission.npz` 只改 `W`/`H2_I`，角度字、
`tree_edges`、`U` 和电路均不变。使用公开 `dfthc_refit 1.7.0`
的约束 refit + gauge；refit 在 1,200 evals 内从
λ_eff 46.8936620787 降到 46.8936357356，随后 4 轮 gauge/refit
低于 `min_gain=1e-7`，停止。

| 指标 | Syed V9 | 本轮 refit |
|---|---:|---:|
| error_1 | 19.999989995 mHa | 19.998999999 mHa |
| error_2 | 19.999989995 mHa | 19.999989995 mHa |
| Lambda | 282.809656049 | 282.809340504 |
| E_gap | 3.91489810005078 | 3.91489810005078 |
| lambda_eff | 46.8936620787 | 46.8936357356 |
| T / Q | 14,966 / 427 | 14,966 / 427 |
| 官方本地 score | 299,673,103.4280 | **299,672,935.0826** |

两者都在同一本地 salt 下实际跑了 78,080 shots 并 PASS；delta 为
**168.3454**（相对 5.617e-7，即 0.000056%）。baseline 的 submission
SHA 为 `c76d568c...e573`，refit 为 `0f6fa5bc...e658`；T/Q 完全不变，
收益只来自 λ_eff。

验证命令（未改官方验证器；使用本地 salt，不是排行榜 salt）：

```sh
.venv/bin/python scripts/manual_verify.py dfthcsos \
  artifacts/20261106_high_yield/c44_refit/family \
  --salt local-c44-refit-20261106
```

实际输出：`status: PASS`，`verified_shots: 78080`，
`score: 299672935.0825918`，候选 SHA-256
`0f6fa5bc423bcc7c888be1ecb3db8188f228ddeec7be22239883a0cc11a2e658`。
完整输出在 `artifacts/20261106_high_yield/c44_refit/verify.log`；baseline
在同一 salt 下的对照 PASS 在
`artifacts/20261106_high_yield/c44_refit/verify_baseline.log`；候选 NPZ 在
`artifacts/20261106_high_yield/c44_refit/probe/submission_best.npz`。

这不是排行榜成绩；没有提交 Kaggle。相对 baseline 的 168.35 分改进
较小，只作为“当前表已接近局部最优”的边界证据，不作为主攻方向。

## 2. 新结构预算：R4/R5 比 R7 更值得做

官方成本模型（`SpinFreeData_V1`，`chi=10`，`brot=8`，`J=5`，
`N=76`）对 `T_prep`、`Q` 和地址数 `A=76+R*B` 的计算是精确的。
下表把 **ANGLE products 固定为当前 3,010/遍**、低地址 cache 取完整
11（实际当前槽的低 cache 为 6–11，所以新形状的 T 还会再低最多约
150），只是预算比较，不是已训练分解的断言。

| R/B/C | A / 地址位 | RC | PSD 下界 (mHa) | Q | T（全 cache） | T×Q 改善 | λ 允许上升 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8/143/44 当前 | 1220 / 11 | 352 | 7.361 | 427 | 14,966（实测） | — | — |
| **4/131/82** | **600 / 10** | **328** | **10.267** | **426** | **13,683** | **8.79%** | **+9.63%** |
| 4/131/83 | 600 / 10 | 332 | 9.687 | 426 | 13,722 | 8.53% | +9.32% |
| **5/135/70** | **751 / 10** | **350** | **7.552** | **427** | **14,177** | **5.27%** | **+5.57%** |
| 5/135/69 | 751 / 10 | 345 | 8.062 | 427 | 14,129 | 5.59% | +5.92% |
| 7/135/50（旧主攻） | 1021 / 10 | 350 | 7.552 | 427 | 14,687 | 1.86% | +1.90% |
| 6/143/59 | 934 / 10 | 354 | 7.2 | 427 | 14,767 | 1.33% | +1.35% |

关键点：

- 旧扫描限制 `750 <= R*B`，把 A=600–751 的 R4/R5 形状排除了；
  `R5/B135` 的 RB=675 正好落在限制外。放开后 R5 明显优于 R7：
  R=5 同时减少地址数、prepare 和 cache，而 R7/C50 为保持 RC=350
  需要更多列，抵消了大部分收益。
- `R4/B131/C82` 的 RC=328，PSD 松弛下界 10.267 mHa；当前总 error_2
  为 20 mHa，PSD 下界 7.361 mHa，说明非 PSD 部分（拟合/量化）约
  18.6 mHa。若新形状的拟合质量相近，10.267 与 18.6 的平方和约
  21.3 mHa，**略高于 20 mHa 门限**。所以 C82 是激进目标，C83
  （PSD 9.687）更稳；C84（RC=336，PSD 9.130）还可再退一步。
- `R5/B135/C70` 的 RC=350，PSD 7.552，与当前 7.361 几乎相同，
  是**风险最低的中等收益目标**；若 R4 训练不上，R5 是首选。
- λ 允许上升的幅度按“其余项不变、只比较 T×Q”计算：
  `λ_max = 46.893662 * (14966*427)/(T_new*Q_new)`。R5 可容忍
  λ 上升 5.6%，R4 可容忍 9.6%；这比 C43/C42 的 0.5%/1.0% 宽得多。

PSD 下界来自已保存的 2,926 个特征值
`artifacts/20261106_high_yield/numerical/shifted_target_eigenvalues.npy`；
它是所有 PSD rank-k 近似的最小 Frobenius 误差，**必要但不充分**：
忽略共享 U 基、L1、SOS gap、one-body、量化和电路综合。

## 3. 为什么不能直接压缩当前分解

本轮用固定字、固定 `U`、只改 `W`/`H2_I` 的数值探针检查“删一点”
是否可行；结论是当前分解的每个向量/列/组都参与一个精细抵消，
不能靠权重 refit 吸收：

| 操作 | error_1 | error_2 | 结论 |
|---|---:|---:|---|
| 删 1 个最弱 B 向量/组（B=142） | 0.342 Ha | 0.055 Ha | 远超门限 |
| 删 8 个 B 向量/组（B=135） | 1.246 Ha | 0.236 Ha | 更差 |
| 删 1 个 rho 组 | 13.7–26.9 mHa* | 2.90–4.52 Ha | 不可行 |
| C43 谱删除（最弱方向） | 20.407 mHa | 21.958 mHa | 差 1.96 mHa |
| C43 + gauge | 20.407 mHa | 21.958 mHa | λ=47.0405，仍不过门 |
| C43 + refit | — | — | `RETRACTION_FAILED` |
| R4 精确合并后 B131/C82 | 14.9 Ha | 4.79 Ha | 不可行 |
| R4 精确合并后 B180/C82 | 9.98 Ha | 2.99 Ha | 不可行 |

\* 删组时 error_1 的数值在 13.7–26.9 mHa 之间有组间差异，但 error_2
都是 Ha 量级，已足以否定该方向。

C43 的 λ 在 gauge 后确实降到 47.0405，低于“C43 打平线”约 47.14
（按 `T=14888, Q=427` 算），若误差能过门约有 0.21% 收益；但
error_1/error_2 仍是 20.407/21.958 mHa，`dfthc_refit` 的 retraction
无法在不放宽约束的情况下继续下降。这个负结果比此前只报
“C43 谱裁剪失败”更具体：失败发生在约束面，而不是 L1 目标；
即使未来重训练修好这约 2 mHa，C43 也只是约 0.2% 的小步，
不应作为主攻。

## 4. 编译搜索的负结果

1. **公开 shared planner 重规划**：`plan --planner shared --pad-rows
   --exchange --seeds 0,1,2,3` 在 k4–k8 得到 196–197 products，
   当前是 195；k0–k3 没有返回计划（generic/block 类）。没有严格
   收益；运行在确认没有槽位低于 195 后停止。日志在
   `artifacts/20261106_high_yield/replan_search/shared_pad.log`，
   计划 JSON 在 `.../work/plans/`。
2. **门级 implication 重写**：先用零初态字寄存器分析时，k1–k9
   各有 5 个 CCX、k10–k14 有 1–4 个 CCX 满足“一控制蕴含另一控制”，
   看似能省 56 T/遍。但把每个槽的**真实入批**（batch k-1）写入
   字寄存器后，所有槽的这类 CCX 都变成 0 个；naive 重写还会触发
   phase/word 检查失败。该“收益”是初始化伪影，已否定。脚本在
   `experiments/dfthcsos/20261106_gate_implications/rewrite.py`。
3. **低地址位宽 L=32**：cache 从 76 降到 58，但 shared planner 的
   products 从 195 涨到 419（一次 70 秒的实际规划），单遍成本
   477 对 271，明确变差。低地址位宽不能只看 cache。
4. **零幅值自由字**：6,925 个 bit1–5 自由位，清零改变 1,348 个词，
   解码向量最大差 1.756e-16，λ 不变；k11 的 mixed ANF 非零系数
   只从 17,910 降到 17,777（0.7%）。对零化表运行 shared planner：
   k10 得到 196 products、k11 得到 196 products，当前均为 195；
   没有下降（k12 仍在运行，但 k10/k11 已足以否定“直接零化”）。
   因此该自由度只能作为未来联合训练的 don't-care，而不是当前表的
   直接省门来源。日志与计划在
   `artifacts/20261106_high_yield/zeroed_plan/`。
5. **7-bit 直接舍入**：此前三种舍入均失败（nearest 的
   error_1=2.13 Ha，error_2=0.425 Ha）；7-bit 必须重训练，不能
   把 T/Q 预算当免费压缩。

## 5. 下一步

1. **R5/B135/C70 优先**：用 Lera V7 的 compact seed / merge-shrink
   或等价训练器，从官方 shift 直接训练 R=5、B=135、C=70（RC=350，
   PSD 7.55），再量化到 8-bit、重规划 loader，最后走官方本地
   78,080-shot 验证。打平线是 λ_eff ≤ 49.5 左右（比当前高 5.6%），
   比 C43/C42 宽得多。
2. **R4/B131/C83 作为激进目标**：RC=332，PSD 9.69，T×Q 预算
   8.53%；若连续拟合能达到约 10 mHa 且量化误差可控，再考虑 C82。
3. **不要继续**在当前表上做 B/R/C 删除、C43 谱裁剪、门级
   implication 或低地址位宽改动的局部搜索；本轮证据已把这些
   搜索类的边界测清楚。
4. 采用新结构时，先训练 U/W，再量化、再发射；不要用当前表的
   权重 refit 去吸收结构变化。

## 6. 复现与验证范围

环境：Python 3.12，NumPy/SciPy，native `kickmix`；refit 使用
`uv run --no-project --with torch --with numpy --with scipy --with
kickmix` 的临时环境（torch 2.15.0），未修改共享 `.venv`。

主要命令：

```sh
# C44 refit（固定字，只改 W/H2_I）
uv run --no-project --with torch --with numpy --with scipy --with kickmix \
  python experiments/dfthcsos/20261106_c43_refit/refit_probe.py \
  artifacts/20261106_high_yield/c44_refit/submission_c44_start.npz \
  artifacts/20261106_high_yield/c44_refit/probe --rounds 5 --max-evals 1200 --threads 6

# 官方本地 78,080-shot 验证
.venv/bin/python scripts/manual_verify.py dfthcsos \
  artifacts/20261106_high_yield/c44_refit/family --salt local-c44-refit-20261106

# 公开 shared planner（无发射，无官方验证）
.venv/bin/python artifacts/20261106_high_yield/public/dfthc_refit_1.7.0/dfthc_refit.py \
  plan /Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261106_syed_v9/release/dfthcsos \
  --planner shared --words artifacts/20261106_syed_v9/dfthcsos/recovered_words.npy \
  --lera-src artifacts/20261106_high_yield/public/lera_v7 --procs 6 \
  --pad-rows --exchange --seeds 0,1,2,3 --out artifacts/20261106_high_yield/replan_search/shared_pad
```

本文件中的“官方验证”只指 C44 refit 的本地 PASS；R4/R5 的 T/Q 是官方
成本模型的算术预算，不是已训练或已验证的收益。没有提交 Kaggle，
没有推送代码，没有修改官方验证器或共享环境。
