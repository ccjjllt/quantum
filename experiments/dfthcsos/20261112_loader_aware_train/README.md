# 化学 loader-aware 训练/重构：no-go（2026-11-12）

目标：把化学 ANGLE loader 从 **4,097 T/pass**（8,194 total，Maoxin v22）降到
**≤3,278 T/pass（−20%）**，同时 e1/e2 ≤ 0.02、Λ>49、E_gap>3.914898。

结论：**达不到**。三条独立证据一致指向同一个结构性障碍：

1. loader 成本是表字的**精确位级退化**（16 地址块内若干 bit 完全相同）的阶梯函数，
   与"接近/聚类"无关；
2. 最强的位级重构（16 块内 a↔a+8 的 bit 配对，含完整连续角+权重自由度）
   只买到 **−1.2%~−2.7%** proxy，却把 e2 推到 **0.22–0.35 Ha（门限的 11–17 倍）**；
3. 8-bit 舍入本身已占掉 20 mHa 门限的 15.1 mHa（Lera 实测正交分解），
   任何 ≥1 LSB 的附加结构化噪声都必然越门。

没有候选通过指标门，因此**未构建 15 个 ANGLE 电路、未跑 78,080-shot verifier**
（构造和全量验证都无意义）。本记录只含本地指标与静态 loader 代理。

## 1. 先搞清楚 loader 到底按什么计费

直接把当前提交的 15 个 `angle_k_*.kmb`（Maoxin v22）读成 kmx 统计：

| 量 | 值 |
|---|---|
| 15 电路总 CCX | **4,097**（294/289×3/268×5/265/266×4/267） |
| 每电路结构 | `80 个缓存 AND`（两级 q51–q90 / q91–q127 各 40）+ `214 个 product CCX` |
| 每电路其余 | ~44k CNOT、80 H/R/HMR（测量擦除）、16 X |
| 寄存器 | selection(11) + 5×word(8)，128 qubits |

即真 loader 成本 = **两级 monomial 缓存（80/电路）+ product Toffoli（214/电路）**，
不是"行数 × 位宽"。两个代理都**高估**真值（保守筛选方向）：

| 代理 | 基线 | 与真值 4,097 的偏差 |
|---|---|---|
| tensorqrom `per_output`（unsigned 表，上一轮口径） | 5,120 | +25.0% |
| 同上，signed 表（tensorqrom 用的规范） | 5,266 | +28.5% |
| tensorqrom `shared`（trials=6, groups=low_groups(4)）+ 全缓存 80/电路 | 4,875 | +19.0% |

主代理取 `shared`+全缓存（4,875，15 电路 terms 3,675）；`per_output` 作历史可比口径。
目标 3,278 对应 shared 代理 ≤3,900、`per_output`(signed) ≤4,213、`per_output`(unsigned) ≤4,096。
口径说明：公共 Maoxin loader 载 8 bit/word（40 输出），tensorqrom 用 signed gauge 的 7 bit
（35 输出）；两种口径都是 rank 15 主导（unsigned 470/525、signed 450/525），结论不受影响。

## 2. 为什么"聚类/重复行"在原理上不成立

- 当前 8 组 two-body 行两两 Hamming 距离中位数 **255–260/600 bit**，最近邻也有 198–239：
  表里没有任何天然近似重复。
- 成本由每输出 bit 的 mixed ANF 张量 `C[1:,1:,o]`（15 个低地址 monomial × 127 个高
  monomial）的 **GF(2) 秩**决定：秩 15（=上限）时 8 product/输出，当前 **525 个输出里
  450 个秩恰为 15**，即表字处在"最泛型"一端。
- 秩只有在整块 16 行的某个 word bit **完全相等**时才下降；"更接近"不改变秩。
  16 行全等的极端（two-body 行 blockify k=16）只把 per_output 从 5,120 降到 3,005；
  k=4（4 行全等）proxy 3,227 时 e2 已经 **12.0 Ha**；k=2（成对全等）proxy 4,174，
  e2 **7.48 Ha**——比门限大 374 倍。
- 76 个 one-body 行（h1′ 的本征矢，error_1 锁死）占 5 个 16-块且无法配对，
  因此任何低 bit 结构化的秩下限是 **15→12**（配对后 bit0 输出实测秩 8–13，
  示例 12 = 7 个未含 l3 的 monomial + 5 个未配对块的列），单 bit 最多省 25% 的 product，
  而这只覆盖 1/7 的输出 bit。

## 3. 实验 A：loader-cost 正则化 fine-tune（按要求做的 L-BFGS）

- 变量：two-body Givens 角 φ（1,144×75，signed gauge 字单位）+ 权重 w（8×143×44）。
- 损失：`e2² + λ·R_pair`，其中

  ```
  R_pair = Σ_{16-地址块内行对 (a, a^8)} Σ_{75 个旋转}
           min_p∈{0,1} [ d_p(φ_a)² + d_p(φ_b)² ]
  d_p(φ) = φ 到最近的、bit0 奇偶性为 p 的整数字的距离
  ```

  这是"到配对约束集的距离"，梯度在格点附近非零（余弦型光滑代理在整数点梯度恒零，
  已弃用）。φ 配对 ⇒ 该 word bit 的 mixed ANF 失去全部含 l3 的 monomial ⇒ 秩减半。
- 优化器：numpy 解析梯度 + scipy L-BFGS-B，150 步（每步 ~0.17 s），从当前表 warm start。
- 注意：行对按**真实地址**对齐（two-body 行从地址 76 开始，块边界偏移 12），
  第一版按 two-body 局部下标对齐是错的，已修正后重跑。

| λ | 连续 e2 (mHa) | R_pair | 量化后 e1 (mHa) | 量化后 e2 (mHa) | Λ | E_gap | λeff | per_output proxy |
|---|---|---|---|---|---|---|---|---|
| 0（对照） | 19.870 | 21,243.98（未动） | 20.000 | **20.000** | 282.974 | 3.91490 | **46.907** | 5,266 |
| 1e-4 | 232.44 | 0.111 | 1630.5 | 333.31 | 286.903 | 7.8436 | 66.627 | 5,204 |
| 3e-4 | 225.63 | 0.240 | 1630.5 | 333.31 | 286.903 | 7.8436 | 66.627 | 5,204 |
| 1e-3 | 222.78 | 0.026 | 1630.5 | 333.31 | 286.903 | 7.8436 | 66.627 | 5,204 |

要点：

- λ=0 的对照把 e2 从 20.000 微调到 19.870（纯 w 重拟合），**proxy 不变**（5,266）。
- λ≥1e-4 时配对约束基本全部满足（R 从 21,244 降到 0.03–0.24），代价是 e2 直接跳到
  **0.22–0.33 Ha**；三个 λ 收敛到**同一张量化字表**——配对是离散吸引子，没有中间态。
- 该表在 `shared` 代理下反而更贵：3,695 terms（基线 3,675），主代理 4,895 vs 4,875。

## 4. 实验 B：最小翻转离散重构 sweep（不训练，只改字）

对当前 signed 表，把选定 (旋转 j, bit k) 的 16-块内 a↔a+8 配平，每次只翻转"角度代价最小"
的那一位（1 LSB），再算官方指标与 proxy：

| 约束 | 翻转位 | e1 (mHa) | e2 (mHa) | λeff | per_output proxy |
|---|---|---|---|---|---|
| 对照 | 0 | 20.0 | **20.0** | **46.907** | 5,240 |
| bit0 × 5 旋转 | 1,511 | 1013 | 230.7 | 60.63 | 5,220 (−0.4%) |
| bit0 × 15 旋转 | 4,532 | 1220 | 279.7 | 64.40 | 5,169 (−1.4%) |
| bit0 × 30 旋转 | 9,100 | 1302 | 297.6 | 65.68 | 5,156 (−1.6%) |
| bit0 × 75 旋转 | 22,784 | 1581 | 350.0 | 68.59 | 5,100 (−2.7%) |
| bit1 × 75 旋转 | 22,838 | 3338 | 693.7 | 95.85 | 4,940 (−5.7%) |
| bit2 × 75 旋转 | 22,660 | 6859 | 1372.0 | 142.46 | 4,940 (−5.7%) |

即使只动 5 个旋转的 1 个 bit（占表的 0.5%），e2 就已是门限的 11.5 倍、λeff 涨 29%
（λeff 本身直接乘分数）。测得的最便宜斜率（bit0 全表）约为 **每 1% loader T = 120 mHa
= 6 倍门限**；bit1 再省 3% 要再付 0.34 Ha，bit2 付 0.68 Ha 却不再降 proxy（收益饱和）。
全部点都远在门的错误一侧。

## 5. 精度墙（为什么连"温和结构化"都不可能）

Lera 管线实测（`dfthc_refit/README.md` Findings）：这一族表的 8-bit 舍入噪声
**15.1–15.6 mHa**，与 float 拟合误差正交相加（√(19.55²−12.38²)）。当前表
e1=e2=19.99998 恰好压在门上，意味着：

- float 拟合 ≈ 13.1 mHa，舍入 ≈ 15.1 mHa，合计 20.0；
- 允许的额外方差为 **0**（√(20²−13.1²)=15.1，恰好等于现有舍入噪声）；
- 任何让全部 75 个角各多 1 LSB 的结构化（配对的最小代价）都把舍入噪声翻倍 → ~30 mHa，
  再加 float 项 → 33 mHa，越门 65%。

这与实验 A/B 的实测完全一致：配对全表得到 0.33 Ha，而不是 0.03 Ha。

## 6. 判定与后续

**no-go。** 目标 ≤3,278/pass 要求每电路 product 从 214 降到 ~159（−26%）且缓存不变，
即平均秩从 15 降到 ~10（例如消掉全部 degree-3/4 低 monomial），并且要对约 40–45% 的输出
bit 同时成立。实测能做到的结构族最多换来 per_output −5.7%（且 shared 代理为 0 或更差），
代价是 e2 0.23–1.37 Ha（门的 11–69 倍）；再叠加 76 个 one-body 行把单 bit 的秩下限卡在 12。

- 表侧（正则化训练、聚类、bit 结构化、低成本行序）到此关闭。
- loader 侧残余理论空间很小：per-output 独立秩 5,266 已被 Maoxin 的共享做到 4,097（−22%），
  同一张表的更好 GF(2) 张量秩搜索乐观估计再省 5–10%，到不了 20%，且需重写 loader 并用
  **自己构建**的电路跑分（现有 4,097 是 Maoxin 的固定公共电路，无法对表改动重算）。
- 若要继续追 loader，建议改口径为"重写 loader 构造（稀疏缓存 + 更强共享）"，
  而不是继续改表。

## 7. 复现命令

```bash
cd .worktree/dfthcsos
export DFTHC_DATA=/Users/zhaohuaxiang/ccjjllt/quantum/data/competition
UV="uv run --project /Users/zhaohuaxiang/ccjjllt/quantum python"
$UV experiments/dfthcsos/20261112_loader_aware_train/probe_structure.py     # 结构敏感性
$UV experiments/dfthcsos/20261112_loader_aware_train/probe_accuracy.py      # 行聚类精度代价
$UV experiments/dfthcsos/20261112_loader_aware_train/anf_stats.py           # ANF 支撑/秩
$UV experiments/dfthcsos/20261112_loader_aware_train/restructure_sweep.py   # 实验 B
$UV experiments/dfthcsos/20261112_loader_aware_train/loadertrain.py \
    --lam 1e-3 --iters 150 --out artifacts/20261112_loader_aware_train/train_lam0.001.npz
$UV experiments/dfthcsos/20261112_loader_aware_train/eval_candidates.py     # 量化+官方指标
$UV experiments/dfthcsos/20261112_loader_aware_train/shared_proxy.py        # shared 代理
```

`tensorqrom`/`encode` 直接只读引用 `artifacts/20261112_chem_pipeline/dfthc_refit/`，
未改动官方验证器与公共管线。

## 8. 产物

`artifacts/20261112_loader_aware_train/`：

- `train_lam{0,0.0001,0.0003,0.001}.npz`：fine-tune checkpoint（U、w、φ、words、hist）
- `candidates.json`：量化后官方指标 + proxy
- `restructure_sweep.json`：实验 B 全表
- `shared_proxy.json`：shared 代理（基线 3,675 terms → 4,875；配对 3,695 → 4,895）
- `circuit/angle_k_0.kmx`：Maoxin v22 电路 0 的可读导出（成本结构证据）

## 9. 验证范围

- 全部为**本地指标**（`dfthcsos.verify.evaluate_words`，精确等价于 verifier 的
  error/Lambda/E_gap/lambda_eff）与**静态 loader 代理**（真实电路解析 + tensorqrom）。
- **未构建** 15 个 ANGLE 电路，**未跑** 78,080-shot 官方 verifier：没有候选能过
  e1/e2 门（最好也是 0.33 Ha / 1.6 Ha），verifier 会在第一个门直接拒绝。
- 未提交 Kaggle、未推送代码。
