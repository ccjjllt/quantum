# brot=6 预算-门衔接训练可行性（2026-11-10）— closed

分支 `codex/dfthcsos-research`，工作区 `.worktree/dfthcsos/`。
本轮不重复 J/装配扫描的数字罗列（见 `20261110_shapes/README.md`：brot=6 tensor
T×Q −16%∼−19%，但 e1/e2 出门）；只回答"**训练能不能把门拉回 20 mHa**"。

结论先行（closed，无候选，无训练处方，只有缺口量化）：

1. **不能。e1 是纯字宽量化地板，与训练正交**：同 U/W 在 brot=8 下 e1=2309.54 mHa、
   brot=6 下 e1=9640.34 mHa；300 步连续训练（cont e2 793.56→248.56）后两档 e1
   **逐位不变**（9 位小数一致）。300 步的训练梯度在 e1 上恒为零，缺口 9620 mHa
   没有训练旋钮可拧——除非加回 brot（即放弃预算），否则此路不通。
2. **e2 同样到不了**：连续最优（brot=8，2000 步）85.31 mHa、渐近 63.3；
   brot=6 量化把连续增益吃掉大半（seed→300 步：连续 −545 mHa 只换来量化 −284 mHa，
   边际 0.52；放大倍数从 2.93× 恶化到 8.21×，线性外推量化地板 ≈1912 mHa）。
   按种子放大倍数算门内需要连续 ≤6.8 mHa，而渐近线是 63.3——无限步也到不了。
3. **盆地对比一致**：本轮 300 步三点（411.29/314.32/248.56）与 longloss 基线逐位
   重合（同一盆地）；结合扰动重启（181.28 vs 182.00）、rand/dft/R4-eigrr
   （渐近全 >130）、分阶段 null，判断为形状/字宽限制，不是种子运气。
   GPU 只加速同一盆地的下滑，不改变两道地板（e1 量化地板 + 连续渐近线）。

## 1. 门失败分解（精确数，无 shots）

方法：固定 b9eced3e log-depth 树，对同一份连续 U/W 做 signed 规范重编码
（`scan_j_brot.py` 的 `encode_all` 同款逻辑：two-body 行直接量化；
one-body 行 = 解码 X 重建 h1_prime 后取精确本征向量再量化），
调官方 `evaluate_words` 精确门数。按验证器定义，e1 只衡量 one-body 行对
h1_prime 的编码（two-body 传播被一致性构造抵消），e2 只衡量 two-body 行
舍入 + 连续失配——两者正交，可分别归因。

| U/W | 连续 e2 (mHa) | brot=8 e1 | brot=8 e2 | brot=6 e1 | brot=6 e2 |
|---|---|---:|---:|---:|---:|
| seed（未训练） | 793.56 | 2309.54 | 924.27 | 9640.34 | 2325.55 |
| 300 步探针 | 248.56 | **2309.54（逐位不变）** | 498.37 | **9640.34（逐位不变）** | 2041.28 |

（单位 mHa；`artifacts/20261110_brot6/decompose.json`；300 步轨迹见 `probe_300.log`：
100 步 411.29、200 步 314.32、300 步 248.56，与 longloss 基线逐位一致。）

解读：

- **e1：one-body Givens 量化地板，占 brot 退化的主导。**
  brot 8→6 的增量 e1 +7330 mHa（×4.17，与量化步长 π/128→π/32 的 4 倍粗化一致），
  e2 增量 +1401 mHa（×2.52）。e1 绝对值与相对退化都占优——brot=6 的门失败
  **主要是 one-body 字宽问题**，不是共享 U 基容量问题。
  且 300 步训练后 e1 两档逐位不变：U/W 的 L-BFGS 梯度完全不作用于 e1
  （one-body 行每次都是精确本征向量的重编码，量化误差只与字宽/N 有关）。
  附带：训练后 Λ 1366→1552（h1_prime 变了）而 e1 一字不动，佐证 e1 是纯分辨率地板。
- **e2：two-body 容量 + 量化放大。**
  连续 −545 mHa（−69%）只换来 brot=6 量化 −284 mHa（−12%）、brot=8 量化 −426 mHa
  （−46%）。放大倍数（量化/连续）：brot=8 从 1.16×→2.01×，brot=6 从 2.93×→8.21×——
  连续越好，6-bit 舍入吃掉的比例越大（训练在过拟合连续度量下对量化不可见的方向）。
  边际效率 0.52（brot=6）且随训练递减（brot=8 的 300→500 段边际已从 0.78 掉到 0.56），
  后续只会更差。
- 门状态：Λ（1366/1552 > 49）、E_gap（957 > 3.91）本来就过；只有 e1/e2 出门，
  且 e1 一票否决（482× 超门，零训练响应）。

## 2. 外推判断（brot=8 的 2000 步曲线作尺子）

连续尾律（longloss L2：`e = 63.33 + 148.2·0.909^k`，k 单位 100 步）：

| 总量步数 | 连续 e2 外推 (mHa) | 距门 |
|---:|---:|---:|
| 2000（实测） | 85.31 | +65.31 |
| 3000 | 71.8 | +51.8 |
| 5000 | 64.6 | +44.6 |
| ∞（渐近） | 63.3 | +43.3 |

- **按种子放大倍数**：brot=6 门内要求连续 ≤ 20/2.93 ≈ **6.8 mHa**，
  渐近线 63.3 高出 56.5 mHa——**无限步不可达**，与步数/硬件无关。
- **按实测量化边际**：边际 0.52 从 300 步外推，量化地板 ≈ **1912 mHa**
  （2041 − 0.52×248），缺口 ≈1900 mHa；即使边际不衰减，走到连续渐近线
  （248→63）也只能再降 ~96 mHa，量化仍 ≈1945 mHa。
  线性"−0.022/步再跑 3000 步"的算法忽略渐近线，不采信（longloss §3 同结论）。
- **e1 无外推可做**：三点训练导数恒零，外推步数 = ∞。
- **盆地对比**：本轮 300 步与基线逐位重合 + 扰动重启 1 mHa 内会合（同一盆地）；
  rand 373/dft 593/R4-eigrr 180 的 500 步值与渐近全 >130（换基/换形不换盆）；
  brot=6 在此之上再加 ~1900 mHa 量化地板 + 9620 mHa e1 地板。
  **结论：连续轴已在盆地天花板下，量化轴另有两道独立地板；GPU 加速不改变任一结论。**
  （CPU 也不慢：300 步 23.6 s；5000 步 ≈4 分钟也到不了 64.6 以下，跑了也白跑。）

## 3. 处方或缺口量化 → closed，无待执行处方

任一外推（e1 地板 / e2 地板 / 连续渐近）都不显示可达，故**不给训练处方**，
按任务要求 closed，缺口量化如下：

- **门缺口**：e1 差 **+9620 mHa**（9640 vs 20，482×，训练响应恒零）；
  e2 差 seed +2306、300 步 +2021、外推地板约 **+1890**（1912 vs 20，95×）。
- **成本侧 foregone**：J=5/brot=6 tensor 的 T×Q 5201241（−18.61%，省 1189241；
  T 14966→12473 省 1493，其中 Givens −600；Q 427→417 省 10）因 conjunction
  门侧失败而不可兑现。不进入 refit/验证讨论（与 shapes §3 同标准）。
- 唯一能动 e1 的旋钮是把 brot 加回去（brot=6→8 即 −600T 让出 + e1 9640→2310，
  但 2310 仍出门 115×，且 T×Q 回到 −0.39%）：**预算与门在两个字宽下同时不成立**，
  不是"多训一点"的量级。

## 4. 交付物与复现

- `experiments/dfthcsos/20261110_brot6/decompose.py`（重编码 + `evaluate_words` 分解脚本）
- `experiments/dfthcsos/20261110_brot6/README.md`（本文件）
- `artifacts/20261110_brot6/train_r5_300.npz`（300 步连续探针，U/W/H2_I，非候选）
- `artifacts/20261110_brot6/probe_300.log`（300 步逐 100 步 e2/s 真实日志，23.6 s CPU）
- `artifacts/20261110_brot6/decompose.json`（seed/300步 × brot8/6 四组精确门数）

```bash
# 300 步探针（CPU ~25 s，已跑过，结果确定性复现）
uv run --no-project --with jax --with optax --with numpy --with scipy --with h5py --with kickmix \
  python experiments/dfthcsos/20261106_train_r5/fit_probe.py \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261110_brot6/train_r5_300.npz --iters 300 --chunk 100
# 四组重编码 + 精确门数（CPU ~2 s，无 shots）
.venv/bin/python experiments/dfthcsos/20261110_brot6/decompose.py \
  artifacts/20261108_public_frontier/dfthcsos_refit/submission.npz \
  artifacts/20261110_brot6/decompose.json \
  artifacts/20261106_high_yield/train_r5/seed_5x135x70_cluster_chol.npz \
  artifacts/20261110_brot6/train_r5_300.npz --brots 8 6
```

## 5. 验证范围声明

- **无官方 78,080-shot 运行，无 `verify.py`/`manual_verify.py` 调用，无训练之外的验证。**
  本轮新增计算只有：连续 L-BFGS 300 步探针（JAX CPU，`fastfit.error2` 曲线值，
  非候选）+ signed 重编码 + 官方 `evaluate_words` 精确门数（无 shots）。
- 连续 e2 数（793.56/411.29/314.32/248.56）为 float64 探针值；量化 e1/e2
  （2309.54/924.27/9640.34/2325.55 等）为 `evaluate_words` 精确数；
  外推渐近 63.3/地板 1912 为模型数，非实测。
- 2000 步 85.31/渐近 63.3、多 basin 曲线引自 `20261109_longloss` 与
  `20261109_ubasis_retrain`；500 步 182.00/461 mHa 引自 `20261109_angles_r5` §2。
- 只写本工作区 `experiments/dfthcsos/20261110_brot6/` + `artifacts/20261110_brot6/`；
  未改官方验证器/数据与共享环境；未提交 Kaggle，未推送。
