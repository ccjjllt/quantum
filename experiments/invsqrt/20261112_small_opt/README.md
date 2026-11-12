# `9c708f7b` 小优化落地尝试：8 权重融合 + 条件化 + 常量控制扫描（`20261112_small_opt`）

日期：2026-11-12/13；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：`9c708f7b…ef20d1`，62Q，C=1,508.9567，score 93,555.2627。
本实验**没有产出可提交候选**：两个指定方向都在官方验证器下 FAIL，且失败是结构性的。
未提交 Kaggle，未 push，无残留进程。

## 0. 结论

| 尝试 | 预期 | 实测 | 判定 |
|---|---:|---|---|
| 8 个“重复权重”旋转融合（+8→33 旋转） | −57.1 C（−3,540 分，→90,015） | 8/8 对全部破坏相位，ratio 4.0e3–5.1e5；官方 verifier `x=1` FAIL（4.883e-4 vs 5.96e-8，**8191×**） | **不可行** |
| 6 门“移到 flag 后”（均执行条件化） | ≤−3.00 mean gates（−186 分，→93,369） | 官方 verifier **FAIL `x was not restored`**；单 seed 扫描 x≤4096 失败点 179/204/266/314/315/582 | **不可行** |
| 常量控制降级（CCX→CX / CCZ→CZ / CSWAP→SWAP） | 每门 −62 分 | **0 个**（全电路无 state-independent 常量控制） | 空 |
| prefix 重综合（193→~110 CCX） | −83 C（−5,145 分，→88,410） | 未尝试：需重写前导位检测 + 移位网络并重建 digit 列，估 3–5 h | 超时盒 |

**结论：`9c708f7b` 在“单门删除 / 门对 / 常量控制 / 均执行条件化 / 旋转合并”这五类
机械改写上已是**实测**局部最优。** 唯一还剩的是 prefix 精确重综合（≥3 h），
以及换算法（前序报告已算过，无 62Q 可行形态）。

## 1. 8 个重复权重的融合：不可行（角度可合并 ≠ 相位可合并）

### 1.1 对象

41 个一般旋转覆盖 33 个二进制权重，其中 8 个权重（2^-10…2^-17）各出现两次：
ladder 1（op 8560–8662，k=0..7）与 ladder 2（op 16727–16780，k=33..40），
全部作用在同一 digit ancilla `q28` 上。

### 1.2 融合测试

对每一对：删除 ladder 2 的旋转，把它的角**精确**加到 ladder 1 的同权重旋转上
（用 dyadic 精确十进制写入，非 float），然后与基线逐 x 比相位
（x=1..4000，1 shot/x，seed 12345）：

| 权重 | 差异 x / 4000 | 最大 error/tol |
|---|---:|---:|
| 2^-17 | 1,979 | 4.05e3 |
| 2^-16 | 1,959 | 8.09e3 |
| 2^-15 | 2,007 | 1.62e4 |
| 2^-14 | 1,983 | 3.23e4 |
| 2^-13 | 2,016 | 6.48e4 |
| 2^-12 | 2,008 | 1.30e5 |
| 2^-11 | 2,083 | 2.58e5 |
| 2^-10 | 1,988 | 5.08e5 |

官方验证器（`cand_fuse_k7.kmx`，2^-10 对，40 旋转，max-x 4096、8 shots/x）：

```
status FAIL: x=1: phase error -4.883e-04 turns exceeds tolerance 5.960e-08
```

### 1.3 原因

同权重 ≠ 同列。`20261112_newfamily_census` §4.1 已证明 41 个旋转的 digit 列
`b_k(x)` 两两不同且 GF(2) 秩 41；两个旋转的相位是 `θ1·b1(x) + θ2·b2(x)`，
合并成单旋转要求 `b1 ≡ b2`。实测差异率 ≈ 50% 正是 `b1⊕b2` 的占比。

**结构性障碍**：两个旋转相隔 ~7,000 op，中间的 mid 段对同一 `q28` 做 46 次
HMR（测-复位）；要把两个 digit 同时保活到一次旋转，需要 1 个空闲量子比特——
而 peak liveness 62/62。**在 62Q 下不存在这个空间。**

## 2. 均执行条件化：pool 是假阳性（不是“收益太小”）

### 2.1 普查（本电路重跑，模型对官方吻合到 5e-4）

`scripts/census_mean_tof.py`（只读，N=400k）：

```
ops=36965 static_tof=1375 mean_exec=1213.865372     (官方 1213.8659)
P=1: 1127 gates / 1127.000        P≈0.5: 138 / 68.998
其它: 110 / 9.9                   合计 1375 / 1213.865
unconditional target gates: 1124, target never used again: 17
ALL later uses conditional (P<=0.55): 6 gates; upper-bound mean saving 3.00 gates
```

6 个候选（`scripts/pool_detail.py`）：op 18911/19049/19711/20496（单条件，P≈0.499）
与 24499/24729（两个不同条件 b140/b495，只能取 OR）。

### 2.2 官方验证器否决

`cand_cond_18911.kmx`：把 `CCX q50 q45 q51`（op 18911）移到它自己的 flag 之后
（`BIT_STORE1 b380; BIT_INVERT b380 if b379`），并用 `if b380` 包住：

```
status FAIL: x was not restored.        (max-x 4096, 8 shots/x, 32768 shots)
```

单 seed（12345）逐 x 扫描 x≤4096：x = **179, 204, 266, 314, 315, 582** 起 x 不复原。
对照：只移动、不加条件的同一改写 **x 全部复原** → 编辑本身合法，**是“条件化”破坏语义**。

### 2.3 两个独立机制（都与普查的“后续使用”判据冲突）

1. **HMR 相位耦合**（`20261112_newfamily_census` §8 警告的同一类假阳性）：
   紧接的 `HMR q51 b182` 的相位是 `(-1)^{v·b182}`，而 `CZ q50 q45 if b182`
   施加 `(-1)^{b182·(q50∧q45)}`；二者相消**当且仅当 v = q50∧q45**。
   跳过 CCX 使 v 变成旧值 → 相位随 b182 随机化。
2. **x 复原数据流**：q51 的值还经后续 SWAP/重建网络进入 x 的复原路径，
   所以破坏是**值级**的，不只是相位级。普查的“目标后续只被条件使用”判据
   只跟踪到第一个 HMR，漏掉了这条链。

**因此那 3.00 mean gates（186 分）不是“低于立项线”，而是不可实现。**

## 3. 常量控制 / 常量目标扫描：0 个（这是唯一完全 sound 的机械类）

`scripts/const_sweep.py`：把每个量子比特的值精确跟踪为 {0,1,unknown}
（scratch 初值 0；HMR 复位为 0；条件可能为假时目标置 unknown；只报告
state-independent 的常量）。判据：

- 控制恒 0 → 该门对所有 x、所有测量结果都是 no-op → 可删；
- 控制恒 1 → `CCX→CX` / `CCZ→CZ` / `CSWAP→SWAP`（省 1 C）。

结果：`findings: {}`，**0 个**。健全性自检：末态 38 个 scratch 全部被跟踪为 0
（与“scratch 必须复原”一致），说明跟踪不是空转。

这与 Zenodo v0.3 对上一代 62/63Q 电路“1,501 个 Toffoli-class op 精确扫描无第二个
仿射恒等式”的结论一致。

## 4. 为什么这一类全部关闭（机制层面的解释）

该电路的相位之所以对 x 确定，是因为每个 HMR 的被测值 v 都被后续对角修正**精确复现**：
`(-1)^{v·b}` 与 `(-1)^{b·f(q)}` 相消要求 `v ≡ f(q)`。因此

- 任何改变“某个 HMR 时刻的值”的改写都会破坏相位（除非同时改修正项）；
- 任何“只值不变”的改写（no-op、常量控制、精确门对）才 sound——实测各为 0/0/0；
- 唯一不经过 HMR 的付费门池是 ladder 的 digit 计算（127 mean），但它的输出
  立刻被旋转消费，删/并都会改 digit 列。

这就是“社区两周补丁叠加后饱和”的可验证解释，也说明**只能换算法或精确重写 prefix**。

## 5. 账（供后续决策）

| 项 | 值 |
|---|---|
| 融合 8 旋转（若成立） | −57.1 C → 90,015（−3.79%） |
| 条件化 6 门（若成立） | −186 分 → 93,369（−0.20%） |
| 常量控制 | 0 |
| prefix 重综合（193 CCX → ~110 AND 下界） | 估 −83 C → 88,410（−5.5%），3–5 h，未做 |
| 三者全成立（现实中不可能） | ~83,000（−11%） |

要达 ≥20%（≤74,844）仍需 −302 C；本实验进一步确认：**62Q 架构内不存在
≥100 C 的机械收益**。

## 6. 验证范围（明确区分）

| 检查 | 范围 | 结果 |
|---|---|---|
| 基线小域官方验证（harness 自检） | x≤4096 × 8 shots = 32,768 shots | **PASS**，worst 0.9993237694@161（与全量一致） |
| `cand_fuse_k7.kmx` 官方验证 | x≤4096 × 8 shots | **FAIL**（x=1，相位 8191× tol） |
| `cand_cond_18911.kmx` 官方验证 | x≤4096 × 8 shots | **FAIL**（x 未复原） |
| 融合相位表 | x=1..4000，1 shot/x，seed 12345 | 8/8 对破坏，见 §1.2 |
| 条件化值级失败 | x≤4096，1 seed，读 x 寄存器 | 179/204/266/314/315/582 |
| 均值普查 | N=400k MC，模型 vs 官方 1213.8659 | 1,213.865372（Δ 5e-4） |
| 常量扫描 | 全电路 36,965 op | 0 findings |
| **全量 200,540,928 shots** | **未运行**（无候选；已知 FAIL 的变体不跑全量） | — |
| Kaggle 提交 / push | 无 | — |

## 7. 复现

```bash
cd .worktree/invsqrt
# 均值普查 + pool 细节
uv run python experiments/invsqrt/20261112_small_opt/scripts/census_mean_tof.py /tmp/base.kmx 400000
uv run python experiments/invsqrt/20261112_small_opt/scripts/pool_detail.py   /tmp/base.kmx 400000
# 常量控制扫描（sound；0 findings）
uv run python experiments/invsqrt/20261112_small_opt/scripts/const_sweep.py   /tmp/base.kmx
# 融合候选（2^-10 对）与条件化候选
uv run python experiments/invsqrt/20261112_small_opt/scripts/wrap_cond.py \
    artifacts/20261112_newfamily_census/invsqrt.kmb /tmp/cand.kmx 18911:b380
cd /Users/zhaohuaxiang/ccjjllt/quantum
uv run python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
    .worktree/invsqrt/artifacts/20261112_small_opt/cand_fuse_k7.kmx --max-x 4096 --shots-per-x 8
uv run python data/competition/verifiers/invsqrt/verify_submission_invsqrt.py \
    .worktree/invsqrt/artifacts/20261112_small_opt/cand_cond_18911.kmx --max-x 4096 --shots-per-x 8
```

候选（均 FAIL，不可提交）：`artifacts/20261112_small_opt/cand_fuse_k7.kmx`（40 旋转）、
`cand_cond_18911.kmx`、`cand_one.kmx`（错误地把条件加在 flag 计算之前，留作反例）。
