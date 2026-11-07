# dfthcsos 已关闭研究汇总

本文件是本分支**唯一保留**的无收益/已放弃研究概况与失败原因。
相关脚本、详细文档与中间产物已删除（见末尾清理记录）。
本分支保留的只有两项：`20261106_gain_search/`（C44微收益+结构预算）
与 `20261106_train_r5/`（在研的 R5/R6 训练）。

## 保留项（不在本文件展开）

- **C44固定字refit**：官方本地78,080-shot PASS，`299,672,935.08`
  vs baseline `299,673,103.43`，改进**168.35分（0.000056%）**。
  T/Q不变，收益只来自λ_eff。见`20261106_gain_search/`。
- **在研**：R5/B135/C70、R4/B131/C83、R6/B143/C59的U/W训练。
  见`20261106_train_r5/`。当前连续error_2仍在29–37 mHa，未过门。

## 已关闭的 null 研究（实测结论）

### A. 旧Maoxin基线时代（2026-11-06前，基线已被Syed V9超过）

1. **权重/C列refit**：H2/W/robust/joint/Lagrangian各向重拟合的λ增益均
   ≤1.5e-6；C44邻片平均与置零均失败 → C44是load-bearing，需分子级重训练。
2. **k8张量/填充重综合**：95k个2→1候选全null；"三批各省1 AND"仅~6T
   （0.013%总GM），无候选。
3. **结构余量**：Q=126+dirty_rank，上限128 → k0/k2/k3零余量；Givens固定
   （2250T，由N/brot锁定）；J5→J4/J6、brot改动均需重做loader且打平或更差。
4. **ANGLE装载器**：单项式在1220可达点满秩（1220/1220）→表示唯一；
   9种两级分段全不可分离；共享AND重写156个候选0个有效；
   前缀/Paar/奇偶覆盖构造全部劣于现电路297 CCX/遍。
   结论：该装载器在可实现构造中已是最优。
5. **公开候选对照**：当时公开组合均劣于已提交方案。

### B. Syed V9基线刻画（无新收益，属基线测量）

基线：化学成本299,673,103.43，λ_eff 46.8936620787，T/Q=14,966/427，
ANGLE双遍8,304，R/B/C=8/143/44。两误差余量各约0.010 μHa。

1. **五helper载体已达容量上界58**：同一树、同一高位模型下不能再加。
2. **7,568对列正交旋转无收益**：最大下降5.33e-15，属浮点舍入。
3. **C44→C43谱裁剪失败**：error_1=20.407 mHa、error_2=21.958 mHa、
   λ_eff=48.23。仅否定此次谱删除，不否定再训练C43。

### C. 当前表编译搜索（全部无收益，已停止）

1. **公开shared planner重规划**：k4–k8得196–197 products，当前195；
   k0–k3无计划返回。固定特征空间配对下界已饱和。
2. **零幅值自由字直接零化**：6,925个bit1–5自由位，λ不变；
   但k10/k11的planner仍为196 products（当前195）。只能作未来联合训练的
   don't-care，不能直接省门。
3. **低地址位宽L=32**：cache 76→58，但products 195→419，
   单遍成本271→477，明确变差。
4. **门级implication重写**：零初态分析似有56个可替换CCX；
   写入真实入批后全部归零，naive重写还触发phase/word检查失败。
   该"收益"是初始化伪影。
5. **7-bit直接舍入**：floor/nearest/ceil全失败
  （nearest的error_1=2.13 Ha、error_2=0.425 Ha）。7-bit必须重训练。
6. **公开seed不能直接迁移**：Lera `adam_8x143x45`缺one-body向量；
   `refit_845`（λ=47.27、C45）已劣于V9。

### D. C43约束refit（失败在约束面）

C43谱删除+gauge可把λ降到47.0405（低于约47.14的打平线），但
error_1/error_2仍为20.407/21.958 mHa，refit报RETRACTION_FAILED。
即使未来修好这约2 mHa，C43也只是约0.2%的小步，不作主攻。

### E. 当前分解的结构删除（Ha量级失败）

固定字、固定U、只改W/H2_I：删1个最弱B向量/组即error_1 0.342 Ha；
删1个rho组error_2达2.9–4.5 Ha；精确合并到R4/B131/C82仍error_2 4.79 Ha。
当前分解的每个向量/组都参与精细抵消，权重refit无法吸收。

### F. R7/R6训练Pareto（8-bit公开路线无交集，训练停止）

合法形状连续error_2：R7/B143/C50为29.36；R6/B143/C59为33.30
（eigen seed）、37.41（cluster seed）、34.14（compact seed 20k）；
grow到6x180x90再fit 50k到25.80，但该形状T比当前更大、无收益，
且shrink到170x85即跳到28.8–31.4 mHa。
20 mHa只在C≈90/B180附近接近（23.74），而该处T更差；
正收益区（R6/B≤144、C≤65）在30–37 mHa。
B160/C59（−3.46%）、C70（−1.82%）、B180/C59（−7.92%）本身是负收益，
不训练。结论：8-bit公开训练路线无法同时满足收益与门限，
需新方法或GPU/长时训练（见`20261106_train_r5/`）。

## 清理记录

- 2026-11-07：删除`20261106_syed_v9/`、`20261106_high_yield/`、
  `20261106_gate_implications/`全文，`20261106_c43_refit/`全文
  （其中`refit_probe.py`移入`20261106_gain_search/`，它是C44微收益的工具）。
- 同步删除对应artifacts：`c43_refit/`、`gate_implications/`、`public/`、
  `recovered_plans/`、`replan_search/`、`zeroed_plan/`、`word_freedom/`、
  `resources/`（含`resources_run.log`）、`literature/`、`jax_check.log`，
  以及`20261106_syed_v9/dfthcsos/`下除`recovered_words.npy`外的分析输出。
- 保留的artifacts：`c44_refit/`（微收益证据）、`numerical/`（PSD特征值）、
  `lera_data/`与`starter_kit/`（在研训练栈）、`train_r5/`与`train_r6/`
  （在研训练输出）、`recovered_words.npy`及`release`/`source`只读链接。
- 被删脚本/文档曾提交过，可用`git show <旧提交>:<路径>`找回；
  artifacts从未入Git（`.gitignore`），删除不可恢复。
- 本工作区`experiments/invsqrt/`、`experiments/dqi/`等属共同历史，
  不在本次清理范围。
