# 2026-11-17 第二轮（并行五线）：所有可动轴的实测结论

本文件只记录**已实测**的结论。GM 口径与 `scripts/gm.py` 一致；金线 28.71339，榜首 31.01379，
当前提交 `58464076` = 28.15094。

## 0. 本轮交付的精确目标（复算过）

DQI 成本 ∝ `Q²·T`，每减 1 条 wire = **+0.0211 GM**；chem 每减 1 个 Q = +0.0220 GM；
chem 每减 1 T = +0.00064 GM；invsqrt 每减 1 C = +0.0055 GM。

| DQI Q | DQI 单独 | + chem −20 T | 说明 |
|---:|---:|---:|---|
| 890 | 28.15093 | 28.16370 | 现状 |
| 878 | 28.40685 | 28.41974 | 3nb+2 wires（文献方案） |
| 874 | 28.49346 | 28.50639 | |
| 866 | 28.66867 | 28.68168 | 2nb+2 wires |
| **864** | **28.71289** | **28.72592** | **单独差 0.0005，加 chem 载荷即过金线** |
| 850 | 29.02731 | 29.04048 | |

**结论：金线 = DQI 864Q（−26 wires）且 chem loader −20 T。** 两者缺一不过。

## 1. invsqrt：42Q / 40Q 压缩 —— 关闭（已实测）

- 声明宽度 44，**实测 liveness 峰值 = 44**（op 1689 `CCX q16 q17 q43`）。
- 三种独立模型（区间、常量性/MBU、区间图着色）都给 44；**C(44,2)=946 对 wire 中 0 对 live range 不相交**
  → 重命名搜索空间为空，不是没搜到。
- 需要"退休+重算"才能到 42Q：最便宜一对 ≥132 C，而打平滑余只有 80.95 C（1.63×）。
- **口径纠正**：42Q 即便零代价也只有 **28.5909 < 28.71339**；42×1,699.94 不是金线。
  纯宽度要 **≤41Q**，需 3 次退休 ≥293 C 对 +19.25 C 余量。`docs/ceiling-20261117.md` §2.1 的
  1,781.06 是打平点，不是金线点。

## 2. chemistry

### 2.1 Q 轴 —— 关闭（已实测，精确公式）

```
b2 = ceil(log2 B) + 11
inner_temp = max(0, ceil(log2(B+1)) − 2) + ceil(log2(RC·ceil((B+1)/2^k2))) + (2^k2 − 1)·b2
Q = 84 + J·brot + max(outer_temp, inner_temp, angles_temp)
```

`k2` 由"从大到小、首个体积 < brot·(N−1) 就接受"选出 → 它**最大化** inner_temp，不是最小化。
`brot ≥ 8` 是硬门（error 与角度栅格同阶）。k2=3 需要 k2=4 分支先失败：

| brot | 8 |
|---|---|
| 使 k2=3 的最小 B | **67,108,865**（rows 5.4e8, T≈3.5e9） |

→ **k2=3 在物理上不可达**。20,400 点扫描 + 3.8M 形状精确扫描：**gate-legal Q_min = 427**，
B ≥ 129 时 Q ∈ [427, 437]；B ≤ 128 时 Q ≥ 695。金线在 T=14,706 下需要 Q ≤ 402.39。

### 2.2 SPRINT 相邻旋转合并 —— 关闭（已实测）

1,144 条 two-body 行：**0 重复、0 相邻相同、0 相邻 255−x**；每个 rho 的 71 对也全无配对。
没有可合并结构，压缩收益恰好 0。

### 2.3 公开形状全部更贵（本轮实测，之前未做）

| 来源 | 形状 | rows | Q | 成本 | vs 我们 294.64M |
|---|---|---:|---:|---:|---:|
| 我们 | (8,143,44) b8 | 1,220 | 427 | **294.64M** | — |
| `femoco_r4_b333` | (4,333,44) | 1,408 | 443 | 342M | +16% |
| `femoco_r4_b303` | (4,303,44) | 1,288 | 443 | 318M | +8% |
| `open_circuits/dfthcsos`（完整公开提交） | (4,303,**128**) b8 | 1,288 | 445 | **462.5M** | +57% |
| `chemistry_r5.py` 家族（R1/B496, b11,J10） | (1,496,44) | 572 | 831 | ~357M | +21% |
| 官方 starter 基线（atlas 实测） | (65,60,60) | — | 634 | λ 49.30 | 更差 |

公开 DF-THC 生态（`victorzhong0110` atlas、`marculera` compact pipeline、`michaelrustad` R10/B129）
的真实 frontier 都在 λ≈49.3 / Q≈634 一侧；**没有任何公开件比 (8,143,44) 更便宜**。

### 2.4 唯一活口：loader −20 T（kernels 在跑）

`k2b` / `k3b` 两个内核各自把一条 loader 从 269 做到 264 Toffoli（T = 2×Toffoli），
合计 −20 T → chem 294.64M → 294.24M → **GM 28.16370**。
v2 的失败已定位为**打包 bug**：`emit_from_basis.py` 硬编码了造机路径
`/private/var/folders/.../qcc_push/marculera_ds`，`np.load(BUILD/'submission.npz')` 在镜像里必然 FileNotFound。
seed 11 在 v2 里**已经找到合法 plan**（"perfect at sum c 133 → products 196; padding ok"）。
修法：`import emit_from_basis as _EFB; _EFB.BUILD = npz.parent`。

## 3. DQI：本轮唯一有量级的轴

- 成本 `R·Q²·T`，R = 1.1912605 为常数税，T = 367,116 已饱和（条件执行只省 873 T）。
- 890 = 840（70 个 syndrome × 12 bit）+ 50（4×12 bit EEA 工作字 + 2 flag）。
  **840 是算法固有量**，能动的只有 50-wire 池。
- 文献（Proos–Zalka / Kaye–Zalka 3nb、Khattar arXiv:2510.10967 2nb+O(log n)）：
  池 50 → 38（3nb+2）→ Q 878 → **28.4069**；→ 26（2nb+2）→ Q 866 → **28.6687**。
  最优点 Q=864 恰好金线。前提未验证：tape 的 4×12-bit 必须真的是 EEA 的 (r0,r1,u0,u1)。
- 本轮从公开包取到 DQI 生成器源码（`circuit_sources/dqi/compact_euclid.py`、`narrow.py`、
  `common.py`）：它们是 **syndrome 表述**（70×12 + 36×12 = 1,272+ wires），比我们的 890 更宽，
  **不是** 890Q tape 的来源，也不能直接产出 3nb 版本。

## 4. 结论

**本代电路（公开件 + 全轴实测下限）的天花板 = 28.1635**（chem loader −20 T）。
金线需要 DQI 换一代（≤864Q），这是 3–6 周的电路生成工作，不是重排字节能做到的。

## 5. loader 程序（本代唯一可交付的增量）

15 条 loader 的 Toffoli：`[294, 288, 269, 269, 263×5, 264, 265×4, 266]`，合计 **4,025**，
而实测 `T_angles = 8,044 = 2 × 4,025`（compute + uncompute 各一遍，误差 6 T 来自
非 Toffoli 的 T 门）。所以 **−1 Toffoli = −2 T**，chem 每 −1 T = **+0.00064 GM**。

| 内核 | 索引 | 现状 | 目标 | ΔT | ΔGM |
|---|---:|---:|---:|---:|---:|
| `qcc-chem-emit-k0b` | 0 | 294 | 264 | −60 | +0.038 |
| `qcc-chem-emit-k1b` | 1 | 288 | 264 | −48 | +0.031 |
| `qcc-chem-emit-k2b` | 2 | 269 | 264 | −10 | +0.006 |
| `qcc-chem-emit-k3b` | 3 | 269 | 264 | −10 | +0.006 |
| 合计 | | | | **−128** | **+0.082** |

叠加上 scout 找到的 λ refit（`ratnachand/vqcc-verified-public-floor : dfthcsos/submission.npz`，
λ 46.92158337，`angle_words`/`tree_edges` **与本仓库逐字节相同**，`|U|` 相同到 1e-16、
仅每行符号规范不同 → 可与我们的 loader 任意组合）：+0.00003。

**最好情况 GM ≈ 28.2331。** k9–k14 还有 −12 Toffoli（−24 T，+0.015），优先级低。

### 收尾步骤（UTC 00:00 名额重置后）

1. `kaggle kernels output` 取 4 个内核的 `run/dfthcsos/angle_k_{0,1,2,3}.kmb`（各自已跑过官方 verifier）。
2. 组装：`ratnachand` 的 `submission.npz` + 我方另外 11 条 loader + 4 条新 loader。
3. `integration/make_members.py` → `make_main.py`（invsqrt `0af21cb8`、DQI `575b043f`）→ 推 integrator，端到端官方验证。
4. 提交并记回执。

## 6. 为什么金线在本代不可达（结构性，不是没找到）

DQI 合同下限 **Q = 840 = 70 × 12**（70 个 syndrome 寄存器 × 12 bit，GF(2^12)）。
成本 ∝ `Q²·T`，所以：

- `Q = 866`（已发表 2nb+2 方案）即使 T 不变也只到 **28.6687**；加 chem −128 T 到 **28.682**。
- 金线要 `Q ≤ 864`（2nb 且几乎没有 flag wire）或 `Q = 840` 且 `T ≤ +5.8%`。
  两者都需要重写 EEA 工作集（3–6 周），不是重排 tap e 能做到的。

chem 侧同理：`rows = 76 + R·B`，而精度按 **B/C 比**标定（实测锚点 3.25→20 mHa、
2.93→19.83(量化后 FAIL)、1.93→40.24、1.58→73.07），所以 `rows ≈ 76 + 3.25·K`，
**与 R 的拆分无关**；K=352 是精度所需 → rows 钉在 1,220。这条轴在数学上被关死。

## 7. loader 的真实自由度：cut 数（本轮新发现）

发射价格是 `Toffoli = products + 75`，`products = (525 − sum_cuts)/2`，即 **+2 cuts = −1 Toffoli**
（`code2/climb_cuts.py` 的 docstring 写明）。把出厂 15 条 loader 反解成 cut 数：

| k | 0 | 1 | 2 | 3 | 4–8 | 9 | 10–13 | 14 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 出厂 Toffoli | 294 | 288 | 269 | 269 | 263 | 264 | 265 | 266 |
| ⇒ sum_cuts | **87** | **99** | 137 | 137 | 149 | 147 | 145 | 143 |

关键事实：**k0/k1 只有 87/99 cuts，而 k4–k8 已达 149**。也就是说 k0/k1 离"最好已观测的
149 cuts"分别差 62 / 50 cuts（= −31 / −25 Toffoli，−62 / −50 T）。
而 `basis_plan_k2.json`（本仓库自己的搜索结果）是 `sum_cuts 133 → products 196 → 271`，
**比出厂的 269 还差** —— 所以 k2/k3 这两条几乎没有空间，k0/k1 才是真正的余量所在。
这也解释了为什么把预算压在 k0/k1（`-k0b` / `-k1b`）是对的。

若 k0/k1 都能到 271（本仓库对 k2 已达到的水平）：−40 Toffoli = −80 T → **GM +0.051 → 28.202**。
若冲到 149 cuts（263）：−80 Toffoli = −160 T → GM +0.103 → 28.254。

### 已验证的收尾工具
`experiments/frontier/20261117_deep/chem/assemble_final.py`（本轮写好并干跑通过）：
给 `--orig`（出厂 `dfthcsos/`）、若干 `--kernels` 输出目录、`--npz`，自动取每条 loader
的最小者并组装到 `--out/dfthcsos/`，打印 Toffoli 表与 T 账。干跑结果与出厂 16 成员一致。

## 8. 两个"看起来免费"的口子，实测都关闭

### 8.1 loader 用更多 qubit 换更少 Toffoli？——不行

chem 成本只按 **loader 的 Toffoli** 计（`T = 2·ΣToffoli + T_h`），loader 自身的 qubit 数
*不进* Q，理论上可以拿 qubit 换 Toffoli。但 `code2/calib_emit.json` 实测：

```
k=0: product_count 213, toffoli_count 293, num_qubits 128
```

**loader 已经用满 128 qubit 上限**（`angles_qubits = 11 + J·brot + ANG_TEMP = 11+40+77 = 128`，
其中 77 就是临时/scratch）。没有余量可换。**关闭。**

### 8.2 DQI 的 Q 是"声明宽度" —— 但会计入全部 ancilla

`dqi/verify_submission_dqi.py:417-420`：

```python
num_qubits = circuit.num_qubits
'score': rep_factor * (num_qubits ** 2) * toffolis
```

- Q 取 **circuit.num_qubits（声明值）**，不是最高用到的 wire → 理论上"分配但不用"的 wire 可以免费压掉。
- 但同一文件 226–230 行把**所有非 syndrome 的 qubit 都当 ancilla**，384–385 行
  `sim.read_across_shots(ancilla_qubits)` 要求它们逐 shot 回到 `|0>` → 每条 ancilla 都真的被用到。
- `rep_factor = repetition_overhead(eps_plus)`，`eps_plus` 是 0 错误 / 102,400 shots 的
  Clopper–Pearson 上界（8.6606e-4）→ **R 是常数，无杠杆**（与 §3 一致）。

所以 DQI 的唯一下降通道仍是"少 ancilla"，只能靠 liveness 实测（子代理在做）或换一代电路。

## 9. cut 搜索的天花板（本轮算出，决定要不要继续投算力）

`physical_cuts` 把每条 cut 看成 15×35 = 525 bit 空间上的一个 functional，5 个 part 各覆盖
3 坐标 × 35 输出 = 105 bit。实测每个 part 的 determined slice 的 GF(2) 秩恒为 **30**（15 个 k 全都一样），
所以**代数上限 = 5 × (105 − 30) = 375 cuts ⇒ products 75 ⇒ Toffoli 150**。

| k | 代数最小 Toffoli | 出厂 Toffoli | 出厂 cuts |
|---|---:|---:|---:|
| 0 | 150 | 294 | 87 |
| 1 | 150 | 288 | 99 |
| 2,3 | 150 | 269 | 137 |
| 4–8 | 150 | 263 | **149** |
| 9 | 150 | 264 | 147 |
| 10–13 | 150 | 265 | 145 |
| 14 | 150 | 266 | 143 |

注意 375 是**松上界**：真正的约束是 `solve_padding` 要求所有 cut 同时对 *同一个* F 成立
（F 只有 12×35 = 420 个自由 bit），所以可达值远低于 375。出厂在 k4–k8 已达 149，
**149 就是目前已知的可达水平**；k0/k1 的 87/99 说明这两条离已知可达水平最远。

结论：继续投算力只在 **k0/k1**（可能还有 k2/k3）上有意义，单条最多 −31 / −25 Toffoli。
把 k0/k1 都推到 149 cuts（263）＝ **−80 Toffoli = −160 T ⇒ GM +0.103 → 28.254**。
这就是本代 loader 轴的全部剩余空间，不可能靠它到金线。

## 10. DQI 宽度：按实测关闭（不是推测）

子代理对 `575b043f` 跑了三种 liveness 模型：

| 模型 | 峰值 | 峰值处 ops |
|---|---:|---:|
| M0 区间 [first,last] | **890** | 31,172,095 |
| M1 reset 分段（可靠） | **890** | 2,760,430 |
| M2 = M1 + dead-tail 裁剪（重编号的上限） | **890** | 2,685,724 |

峰值处 `pool 50/50, syndrome 840/840, total 890/890`，min = max。**dead wire 0 条，
dead-tail 能删的 Toffoli 也是 0**。满宽只占 4.80% 的 op。

逐 k 重算（把"重填次数"和"可恢复性"分开）：

| k | Q | 精确重填数 | 重放 T | T/qubit | 结论 |
|---:|---:|---:|---:|---:|---|
| 1 | 889 | 28 | 49 | 49 | 计数 PASS 17×，**可恢复性 FAIL** |
| 3 | 887 | 382 | 51,410 | 17,137 | FAIL 21× |
| 5 | 885 | 738 | 99,902 | 19,980 | FAIL 24× |
| 10 | 880 | 1,628 | 168,953 | 16,895 | FAIL 20× |
| 50 | 840 | k ≤ 47 时不可行 | — | — | infeasible |

**关键纠正**：重填计数比旧的 925 T/qubit 便宜 19×，所以"重填太贵"从来不是阻塞点；
**阻塞点是可恢复性**——12 个抽样重填里 0 个能重建自身值；必要条件下只有 2.22% 的 gap 满足，
而 1,222 个 >100k op 的 gap 里 **0 个**满足 → 任何 k 都不存在可恢复覆盖。
金线需要 k ≥ 27 且 ≤30.8 T/qubit。

**3nb/2nb 文献方案不适用**：`dqi_reference_circuit.py` 是非扩展、*同步* EEA，用两条
按位置索引的 `reg_a`/`reg_b`（m = n+3 = 73 字），没有 (u0,u1) 系数对；`2nb = 1,680` 是
两条 n 字数组，不是 4 个角色字。tape 的 pool 也不是 4 个等宽字：840-863 各只有 14–16 次复位
（长期持有），864-887 + flag 是 387–9,760 次（回收 scratch），而且它们是**乘积累加器**
（`CCX(syn,syn,W840-851)` 57,774 次）。每个 12-bit 组峰值都 12 live、每个字对都到 24 live
→ **合并省 0 条 wire**。barrel shift 确实 0 T，但禁止它的是 liveness 不是 T。

**DQI 宽度轴关闭。金线在本代不可达，已由三轮独立实测确认。**
