# DQI Q=840：external word「按需重算」判决（`20261112_q840`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**只读 `.kmx` 逐门流式扫描（61,514,188 行，6 遍）+ T/Q 账本算术**。
未构建候选 `.kmb`，未跑 102,400-shot 官方验证器，未提交 Kaggle，未 push。
判决见 §0：**no-go，且前提「48 个 24-bit external word 是可重算的存储」被实测证伪。**

---

## 0. 结论先行

**no-go。** 四条硬数：

1. **52 个 ancilla 不是「48 个 24-bit 存储 + 4 flag」的静态缓存，而是贯穿全电路的活工作寄存器。**
   - `282,744 / 401,313 = 70.5%` 的 paid 门（CCX/CCZ/CSWAP）至少有一个操作数落在这 52 个 qubit 上；
   - 其中 **134,459 次**它们作为 paid 门的**控制位**（值被读去参与运算），148,285 次作为目标位（值被写；CCX 目标 143,237）；
   - 仅 `extract` 一个阶段，52 个 qubit 合计被写入 **1,959,999** 次操作数（平均每 qubit ≈ 37,700 次）。
   全部 386,058 个 CCX 里，**121,602 个是 `bank×syndrome → syndrome`**（bank 字当乘数、
   乘积直接累加回 840 条 syndrome 线），bank 出现在控制位的 CCX 共 212,847 个。
   缓存不会被写 3.8 万次、当乘数消费 12 万次。它们是 `rankone_xor` 风格的单比特累加器
   （`fan-out → CCX 乘积 → fan-in`，见 §2.1 的实测门串）。
2. **没有空闲线可以「重算到别处」。** 840 个 syndrome qubit 在**每一个**阶段都全部在用
   （`extract/synthesis/convert/unconvert/unsynthesis/unextract` 每阶段 `distinct_S = 840`，
   每阶段触及 syndrome 的操作 255,667–22,751,549 次）；52 个 ancilla 也在同一个
   200 步窗口内**全部**出现（行 58,714,748）。两区同时满负荷。
3. **Q=840 的成本中性 T 预算 = mean 444,391 / static 452,537**，比 eae 多
   **50,302 mean T (+12.76%)** 的余量。把 134,459 次「bank 作控制位」的读折成
   **1,358 次 24-bit 乘法读**后，**每次重算只能花 37.7 T**；本族最便宜的 24-bit
   原语是 99 T（`mul24_xor99`）、190 T（`inverse24_forward190`）→ **至少超支 2.6×**，
   实际口径（+18.4% 成本）见 §4。
4. **结构上自相矛盾**：重算出来的 24-bit word 需要 24 条线去装载，Q 立刻回到 ≥864；
   而满载重算（整段 extract）= 58,742 T/次，做 2 次就把 Q=840 的 −11.3% 全部吃掉
   （+14.6%，见 §4 表）。Q=840 与「按需重算」不能同时成立。

**可留下的量级**：只有 Q=888（去掉 4 个 flag）的 **−0.89%**；而 flag 的 `[word==0]`
零测试重算 ≥11 T/次（`slice_zero_flag.py` 实测 gadget）× 约 1,000 次/flag，远超
Q=888 买到的 3,623 static 预算 → 这条也是 no-go。**当前最优仍是 `eae396ba`（3.7353e11）。**

---

## 1. 前提核对：两份 README 的说法 vs 实测

`20261112_next_decoder` §0.2 与 `20261112_low_ancilla` §4.2 的表述是：
「48 = 两个 24-bit external jet word + 4 flags，从 extract 一直活到 unextract；
峰值 52 = 全部 ancilla，slack 0」，并把它当成「贯穿保留的数据」。
本轮把这句拆成三个可测命题，逐一核对：

| 命题 | 实测 | 判定 |
|---|---|---|
| 52 个 ancilla 从 extract 活到 unextract | `q840..q887` first 2,698,652 / last 61.16M；flags first 2.90M / last 61.15M | ✅ 区间对 |
| 「live」= 值被保留（存储） | 每 qubit 使用 155,501–411,283 次；extract 内平均被写 37,700 次；70.5% 的 T 触及它们 | ❌ **是活工作寄存器，不是存储** |
| 峰值 52 = 真实同时存活数 | 同一 200 步窗口内 52 个全部在用；但 `ancilla_live.py` 的 `peak_live` 是 **first..last 区间重叠**，对复用型 scratch 只是平凡上界 | ⚠️ 方法学问题：slack=0 的论证不成立（结论恰好仍成立，见 §2.3） |
| 分组 = 两个 24-bit word | 行为上 A=`q840..863`、B=`q864..887`、flag=`q888..891`；但 **A→B 有 792,322 条 CX、A→syndrome 904,555 条**，两组不做干净隔离 | ⚠️ 是「一个 48-bit 纠缠工作区」，不是两个独立字 |

另外澄清一个命名来源：`.kmx` 里的 `REGISTER r70 "E0"` 等 **E0..E3 是经典 b 寄存器
（`APPEND_TO_REGISTER b9 r70`），不是 qubit**；`q840..q891` 是未命名的裸 qubit。
所以「external jet word」是一个语义标签，不是电路里的物理寄存器边界。

---

## 2. 52 个 ancilla 到底是什么（逐门实测）

### 2.1 门串形态：单比特累加器

`extract` 行 2,698,652 起，`q840` 的第一次出现就是标准 `rankone_xor` 形态：

```
CX q840 q841     # fan-out：把累加器旧值铺到向量的其余位
CX q840 q843
...  (10 条 CX)
CCX q28 q29 q840 # 真正的乘积项：q840 ^= q28·q29
CX q840 q858     # fan-in：把新值 XOR 回向量各位、复原
...
CX q840 q841
```

即：**一个比特当乘积累加器，一次 CCX 算一个秩一项，扇出/扇入把它广播进 12/24-bit 向量。**
`q840..q887` 是这些累加器向量，`q888..q891` 是零标志位。
这类结构在整件电路里连续复用，不存在「算完就搁置等 unextract」的空窗。

### 2.2 触及 52 个 ancilla 的 paid 门（按阶段，实测）

| stage | stage 总 paid | 触及 bank 的 paid | 占比 | 其中 bank 作控制位 |
|---|---:|---:|---:|---:|
| extract | 58,742 | 57,204 | **97.4%** | 44,086 |
| synthesis | 31,635 | 16,767 | 53.0% | 1,788 |
| convert | 60,663 | 22,811 | 37.6% | 5,141 |
| scan | 44,275 | 44,275 | **100%** | 0 |
| unconvert | 62,534 | 26,155 | 41.8% | 6,366 |
| unsynthesis | 40,429 | 14,035 | 34.7% | 2,598 |
| unextract | 103,035 | 101,497 | **98.5%** | 74,480 |
| **合计** | **401,313** | **282,744 (70.5%)** | | **134,459** |

（`scan` 的 44,275 = 11 个 bank 位 × 4,025 个点，且**全部**带经典条件
`PUSH_CONDITION`；`scan` 的 88,550 条受条件 CZ 以 bank 位为源。
口径：paid 门按「门」计一次，故合计 = 282,744；「作控制位」列按**操作数**计，
同一门两个 bank 控制位计两次。§0 的「写入 1,959,999」指 `extract` 内任一门
（含 CX/SWAP/Z）以这 52 个 qubit 为目标操作数的次数。）

### 2.2b 全部 386,058 个 CCX 的角色签名（最直接的一条证据）

把每个 CCX 的两个控制位/一个目标位按「bank（q≥840）/ syndrome（q<840）」分类：

| 签名（控制1,控制2 → 目标） | 个数 | 含义 |
|---|---:|---|
| `S,B → S` | **121,602** | **bank 位当乘数、syndrome 位当乘数，乘积累加回 syndrome 寄存器** |
| `S,S → S` | 113,125 | 完全不碰 bank 的乘法（29.3%） |
| `S,S → B` | 60,086 | 乘积累加进 bank |
| `B,S → B` | 43,672 | bank × syndrome → bank |
| `B,B → B` | 22,886 | bank × bank → bank |
| `S,B → B` | 16,593 | bank × syndrome → bank |
| `B,S → S` | 6,328 | bank × syndrome → syndrome |
| `B,B → S` | 1,766 | bank × bank → syndrome |

检查：合计 386,058；bank 相关 CCX = 272,933（与 `ancilla_role.txt` 一致）；
bank 出现在**控制位**的 CCX = 212,847。

读法：**bank 字在 12 万+ 个 CCX 里当乘数被消费**，而不是「被读一次就完事」；
而且乘积直接写回 syndrome 寄存器（`S,B → S`），说明 bank 与 840 条 syndrome 线
是**同一张融合工作区**，不存在「bank 是旁挂缓存」的读法。

`extract` / `unextract` 两段几乎是 100% bank 工作 —— 也就是说，**「产生这两个字」的
那段电路本身，就是在这两个字的线上算出来的**（§5.1 的自指）。

### 2.3 并发度：两区都满

| 测量 | 值 |
|---|---|
| 同一 200 步窗口内出现的 bank qubit 数 | **52（全部）**，行 58,714,748 |
| 每阶段 distinct syndrome qubit | **840（全部）**，7 个算术阶段无一例外 |
| 每阶段触及 syndrome 的操作数 | 255,757（initial）– 22,751,549（scan） |
| 从未被触及的 syndrome qubit | **0**；最少者 `q23` 也有 31,565 次 |

`.kmx` 总计 61,514,188 行；52 个 ancilla 的 per-qubit `uses` 为 155,501–411,283。

### 2.4 分组用量（paid 门操作数计，同一门多操作数会重复计）

| 组 | qubit | bank 相关 paid 操作数 | 份额 |
|---|---|---:|---:|
| A（24-bit） | q840..q863 | 200,650 | 50.3% |
| B（24-bit） | q864..q887 | 167,861 | 42.1% |
| flags | q888..q891 | 30,642 | 7.7% |

---

## 3. Q=840 的 T 预算（本任务要求的硬账本）

`cost = R · Q² · meanT`，`R = 1.19126046`，eae `mean/static = 0.98200`，
eae = Q 892 / static 401,313 / mean 394,089 / cost **3.7353e11**。

| Q | 成本中性 `meanT_max` | 折 static | 相对 eae mean 的余量 | T 不变时的 cost |
|---:|---:|---:|---:|---:|
| 892 | 394,089 | 401,313 | 0 | 3.7353e11 (+0.00%) |
| 888 | 397,647 | 404,937 | +3,558 | 3.7019e11 (−0.89%) |
| 868 | 416,183 | 423,812 | +22,094 | 3.5370e11 (−5.31%) |
| 864 | 420,046 | 427,746 | +25,957 | 3.5045e11 (−6.18%) |
| 852 | 431,961 | 439,880 | +37,872 | 3.4078e11 (−8.77%) |
| 844 | 440,189 | 448,258 | +46,100 | 3.3442e11 (−10.47%) |
| **840** | **444,391** | **452,537** | **+50,302 (+12.76%)** | **3.3125e11 (−11.32%)** |

**Q=840 允许的 T 上限 = 444,391 mean / 452,537 static**（任务书用当前 R 的公式，
本表按 `mean/static=0.982` 把 mean 上限折成 static）。若 T 一点不增，cost = 3.3125e11
（**−11.32%**），与父会话的 −11.3% 一致。

即：**整个「按需重算」方案能花的钱只有 50,302 mean T = 51,224 static T**，
超出这个数就从赚变亏。下面所有账都用这 51,224 T 结账。

---

## 4. 重算代价账本

### 4.1 单次重算的最小原语

| 原语 | T | 来源 |
|---|---:|---|
| `mul24_xor99`（一次 24-bit 乘，零 scratch） | **99** | `exp/mul99/kernels.py`，v21/eae 共用族 |
| `inverse24_forward190`（一次 24-bit 求逆，正向） | **190** | `exp/inverse12_escape/joint.py`，`confluent_extract` 直接注入 |
| `jet_forward`（一次 jet 合并，正向） | **269–290** | `exp/jet24/pro_jet.py` docstring：269 fwd + 389 rev = 658；`decode.py` docstring：290 + 393 = 683（两处自报不一致，取区间） |

### 4.2 需要重算多少次

| 口径 | 次数 | 说明 |
|---|---:|---|
| bank 位作为 paid 门控制位被「读」 | **134,459** | 实测（§2.2 末列合计） |
| 折成 24-bit 乘法读（99 个控制位/次） | **1,358** | `134,459 / 99` |
| 折成 12-bit 乘法读（42 个控制位/次） | **3,201** | `134,459 / 42` |

**每个「24-bit 乘法读」可花的钱 = 51,224 / 1,358 = 37.7 T。**
最便宜的 24-bit 原语 99 T ⇒ **超支 2.6×**；用 inverse24 口径 190 T ⇒ 超支 5.0×。
若按最严口径（每次「读」都要重算）则每次只有 0.38 T，连一个 CCX 都不够。

### 4.3 净成本（Q=840，逐场景）

| 场景 | static | mean | cost | vs eae |
|---|---:|---:|---:|---:|
| Q=840，bank 免费消失（**理论上界**） | 401,313 | 394,089 | 3.3125e11 | **−11.32%** |
| 每次读重算 @99 T × 1,358 | 535,772 | 526,128 | 4.4224e11 | +18.39% |
| 每次读重算 @190 T × 1,358 | 659,366 | 647,496 | 5.4426e11 | +45.70% |
| 每次读重算 @290 T × 1,358 | 795,183 | 780,869 | 6.5636e11 | +75.72% |
| 每 stage 每字重算 1 次（14 次）@99 T | 402,699 | 395,450 | 3.3240e11 | −11.01% |
| 整段 extract 重算 1 次（58,742 T） | 460,055 | 451,774 | 3.7974e11 | **+1.66%** |
| 整段 extract 重算 2 次（前后各一） | 518,797 | 509,458 | 4.2823e11 | **+14.64%** |

读法：

- 「每 stage 重算 1 次」这一行看起来还能 −11%，但它对应「bank 的值只是 stage 边界上
  的纯函数」——**这是被 §2 证伪的前提**：bank 在 stage 内部被读 1,358 次、写 3.8 万次，
  不是 stage 边界上的快照。
- 只要真按实测粒度重算（≥1,358 次），**最便宜的 99 T 口径也 +18.4%**。
- 只要重算需要「重新跑一遍产生它的电路」（extract 58,742 T），**1 次就 +1.66%，
  2 次 +14.6%**，Q=840 的收益全部吃掉。

### 4.4 go/no-go 判据（留给后续）

要在这条路上翻盘，必须同时满足：

1. 24-bit word 的重算成本 **≤ 37.7 T**（且是真正的整字重算，不是一次乘法）；
2. 重算过程 **不引入任何额外 qubit**（否则 Q>840）；
3. 重算次数 ≤ 517（= 51,224 / 99）。

本族最便宜的 24-bit 乘法是 99 T，且 12-bit 乘法的数学下界是 rank 23 ⇒ 23 T
（`20261112_mulrank`），**单次 24-bit 乘法就已经用掉 61% 的预算**；而「整字重算」
的成本是累加全部秩一项，远高于一次乘法。故 (1) 在本族内无解。

---

## 5. 为什么这条路线在结构上关闭（不只是贵）

### 5.1 自指：重算 bank 的电路需要 bank 当 workspace

`extract` 的 58,742 T 里 **57,204 T (97.4%)** 直接就是这 52 个 qubit 上的运算。
「产生两个字」的那段电路，正是用这两个字当累加器算出来的。
去掉这 48 条线，就没有地方算它 —— 这不是「重算更贵」，而是**重算不可定义**。

### 5.2 不能把值搬到经典比特（0 Q、0 T 的捷径不存在）

唯一的 0 成本存储是经典 b 寄存器（`BIT_STORE0/1`、`BIT_INVERT b if b`），
但写入 b 只能来自 `HMR`，而 `HMR` 是 **X-basis 测量**（`next_decoder` §2.3 已由
builder 文档确认）。计算基里的值读不出来 —— 这条捷径在门集层面就封死。
实测佐证：触及 bank 的 `HMR` 在 `extract` 有 2,267 次、`unextract` 13,807 次；这些是相位测量，
且 `unextract` 里有 401,296 条 **带经典条件的 CX 写回 bank** —— 即「用测量记录
回放分支」，不是「把值存成经典比特」。

### 5.3 没有空闲线

§2.3：840 条 syndrome 线在 7 个算术阶段全部在用（每阶段 distinct_S = 840），
bank 也 52 条全在用。Q=892 不是「840 数据 + 52 闲置」，而是**一张 892 线的
统一工作区**（§2.2b：121,602 个 `CCX bank×syndrome → syndrome`，乘积直接累加回
syndrome 寄存器）。

---

## 6. 如果仍要 Q=840：唯一形态（不是本任务的重算）

Q=840 ⇔ **零 workspace**。任何算术中间量都必须留在 840 条 syndrome 线上，
且最终把 S 复原 ⇒ 解码器必须写成**纯相位（phase-only）电路**：用 syndrome 位
直接控制 CZ/CCZ，不落任何中间态。

这正是 `20261112_direct_phase` 已判 no-go 的 family bet（reason：phase 在
unextract 内部逐点加载：125,333 CZ + 25,117 Z + 2,912 CCZ，没有可整体搬移的末端
phase 块）。本实验为该判决补上资源侧的一半：**Q=840 只值 11.3%，而零 workspace
要求的架构重写连 1% 的 phase 都还没搬动**。

---

## 7. 验证范围（严格区分）

- **本机实测（真数据，非估计）**：`artifacts/20261112_eae_candidate/dqi.kmb`（SHA
  `eae396ba…785bd`，557,739,238 B）经既有 `.kmx` 文本（835,537,319 B）流式扫描 6 遍，
  每遍 61,514,188 行：
  1. 每 qubit 的 first/last/uses 与 stage 集合（`ancilla_role.py`）；
  2. 每 (stage, qubit) 的 paid/控制/目标/CX 扇入扇出矩阵（`ancilla_matrix.py`）；
  3. 经典条件深度分离的读写（`cond_load.py`）；
  4. 200 步滑窗并发度与相邻使用间隔（`gap_profile.py`）；
  5. syndrome/bank 两区的阶段普查（`region_census.py`）；每 qubit paid 计数（`perq_paid.py`）；
  6. 全部 386,058 个 CCX 的角色签名普查（`results/ccx_roles.txt`）。
- **派生算术**：§3/§4 的 cost 由 `ledger.py` 计算（`R=1.19126046`、`mean/static=0.98200`、
  eae 的 401,313/394,089 均引用既有实测记录，本轮未重测 mean）。
- **未做**：未构建任何候选 `.kmb`；未跑 `verify_submission_dqi.py`（102,400 shot）；
  没有 PASS/FAIL；未提交 Kaggle；未 push；未改动 main 与其它实验目录。
- **不是源码级证明**：eae 的精确源码不在本仓库（`low_ancilla` §6），
  §2.1 的 `rankone_xor` 归属是**门串形态 + tag 词表**推断，不是源码比对。

---

## 8. 复现与文件

```bash
cd /Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dqi
KMX=/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx

.venv/bin/python experiments/dqi/20261112_q840/ancilla_role.py   $KMX 840 892   # ~38 s
.venv/bin/python experiments/dqi/20261112_q840/ancilla_matrix.py $KMX 840 892   # ~36 s
.venv/bin/python experiments/dqi/20261112_q840/cond_load.py      $KMX 840 892   # ~37 s
.venv/bin/python experiments/dqi/20261112_q840/gap_profile.py    $KMX 840 892 200  # ~62 s
.venv/bin/python experiments/dqi/20261112_q840/region_census.py  $KMX          # ~61 s
.venv/bin/python experiments/dqi/20261112_q840/perq_paid.py      $KMX 840 892   # ~35 s
.venv/bin/python experiments/dqi/20261112_q840/ledger.py                       # <1 s

# CCX 角色签名普查（§2.2b，~23 s）
awk '$1=="CCX"{c1=($2 ~ /q8[4-9][0-9]$/); c2=($3 ~ /q8[4-9][0-9]$/); t=($4 ~ /q8[4-9][0-9]$/);
     k=(c1?"B":"S") (c2?"B":"S") "->" (t?"B":"S"); n[k]++}
     END{for(k in n) printf "%-10s %8d\n", k, n[k]}' $KMX | sort -k2 -nr
```

| 文件 | 作用 |
|---|---|
| `ancilla_role.py` | 52 个 ancilla 的 first/last/stage、每阶段 op 计数、T 角色拆分 |
| `ancilla_matrix.py` | 每 (stage, qubit) 的 paid 控制/目标、CX 扇入扇出矩阵 |
| `cond_load.py` | 经典条件深度（`PUSH_CONDITION`）下的读写分离 |
| `gap_profile.py` | 200 步滑窗并发度、每 qubit 最大空档 |
| `region_census.py` | syndrome / bank 两区每阶段 distinct 与操作数 |
| `perq_paid.py` | 每 qubit paid 计数，A/B/flag 分组小计 |
| `ledger.py` | §3/§4 的 T/Q 账本，写 `results/ledger.json` |
| `results/*.txt` | 上述 6 个扫描的原始输出 + `ccx_roles.txt` 角色普查 |
| `results/ledger.json` | 入 Git 的数字汇总 |

（`.kmx` 在系统临时目录，835 MB，不进 Git；`.kmb` 在 `artifacts/20261112_eae_candidate/`，
main 只读引用。）
