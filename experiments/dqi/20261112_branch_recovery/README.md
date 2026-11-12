# DQI branch-recovery 实验（`20261112_branch_recovery`）

日期：2026-11-12；分支 `codex/dqi-research`；工作区 `.worktree/dqi/`。
性质：**只读 `.kmx` 的门级/标签级分析 + 一个 toy 切片证明**。
未构建候选 `.kmb`，未运行官方验证器。判决见 §9。

## 0. 结论先行

- **no-go**：eae396ba 里不存在「≥10k 静态 T 的、因存储分支决定而产生的块」。
  分支决定在两个层面都已经是 0-T 形态：**活量子 flag**（1 qubit，取出即用）
  和 **HMR 经典 mask**（0 T、0 Q）。剩下的 T 是乘法与 Chien 搜索本身。
- **决策机器总 T = 57,119 / 401,313 = 14.2%**（routing CSWAP 12,012 +
  zero-test ladder 45,107），且每一项都已在 **n−1 CCX / n-bit 零测试** 的
  信息下界上（§6）。即使把全部决策机器变成 0 T 也只能到 ~344k static
  （~338k mean），而这在原理上不可能：判断 12-bit 量子寄存器是否为零至少
  要 11 个 Toffoli。
- 全电路 **45.3% 的 T 是 GF(2^12)/GF(2^24) 乘法块**（42 T / 99 T 各一块，
  来自显式 tensor decomposition；§7）。要 −13.5%（−54k）必须把乘法次数或
  乘法秩砍掉 ~30%，那是换算法族，不是 branch recovery。
- paper 自己的 DQI 电路是 **~4.4e5 T / 1,837 Q**（Table 1），比 eae
  （401,313 T / 892 Q）**T 更高、Q²T 差 2.3 倍**；直接套 paper 架构不能达到
  341k。

## 1. 假设与目标

按 arXiv:2610.22367（Gu–Kemeny–Yelin–Lukin）的三个原则：

- (a) uncompute 时**从当前状态恢复**分支决定，而不是重算/存储；
- (b) **conditional routing**：用便宜的 controlled swap 把分支差异吸收进
  共享算术，只 control routing；
- (c) 失败预算裁剪罕见输入。

目标：把 eae396ba 从 mean 394,089 / static 401,313 压到 **≤341k mean（−13.5%）**。
本实验只检验 (a)/(b) 在 eae 上的**剩余空间**，并给出精确的 T 归因。

## 2. 输入与方法

输入：`artifacts/20261112_eae_candidate/dqi.kmb`
（SHA `eae396baf0fa52952e07d891237e271257e35bc0483afe57abd17c77857785bd`，
892 Q，151,525 classical bits，static 401,313 T，102,400-shot mean 394,089.27）。

```bash
# 1) kmb -> kmx（835,537,319 bytes / 61,514,188 lines）
.venv/bin/python experiments/dqi/20261112_branch_recovery/dump_kmx.py

# 2) INFO_TAG 标签树：每个 block 实例的 paid 门数、行号
.venv/bin/python experiments/dqi/20261112_branch_recovery/scan_tags.py
.venv/bin/python experiments/dqi/20261112_branch_recovery/stage_tags.py

# 3) gadget 切分（廉价门间隙 gap=50/200/800）与 stage 间差分
.venv/bin/python experiments/dqi/20261112_branch_recovery/blocks.py unextract 200
.venv/bin/python experiments/dqi/20261112_branch_recovery/hist_diff.py
.venv/bin/python experiments/dqi/20261112_branch_recovery/all_hist.py

# 4) 分支位/flag 普查
.venv/bin/python experiments/dqi/20261112_branch_recovery/branch_bits.py
.venv/bin/python experiments/dqi/20261112_branch_recovery/flags.py
.venv/bin/python experiments/dqi/20261112_branch_recovery/flag_cost.py

# 5) 切片证明
.venv/bin/python experiments/dqi/20261112_branch_recovery/slice_zero_flag.py
```

产物：`artifacts/20261112_branch_recovery/{tag_census.json, stage_tags.log,
hist_diff.json, all_hist.json, summary.json}`。
`.kmx` 放在系统临时目录（835 MB，不进 Git）。

paid 口径与 `20261112_direct_phase` 一致：`CCX + CCZ + CSWAP + CCX_CARRY`。

## 3. Stage 表（static paid，精确）

| stage | paid | CCX | CSWAP | CCZ |
|---|---:|---:|---:|---:|
| extract | 58,742 | 58,550 | 192 | 0 |
| synthesis | 31,635 | 31,611 | 24 | 0 |
| convert | 60,663 | 56,095 | 4,568 | 0 |
| scan | 44,275 | 44,275 | 0 | 0 |
| unconvert | 62,534 | 56,794 | 5,668 | 72 |
| unsynthesis | 40,429 | 40,146 | 24 | 259 |
| unextract | **103,035** | 98,587 | 1,536 | 2,912 |
| total | **401,313** | 386,058 | 12,012 | 3,243 |

uncompute 三段 = 205,998 / 401,313 = **51.3%**（与 `direct_phase` 一致）。

unextract 的 CCX 目标分布（本次实测，精确）：**S 寄存器 75,472 /
ancilla 23,115**。

## 4. unextract 的内部结构

`unextract` 没有 paid 子标签（只有末尾 2 组 `inverse12`，共 116 T），是一个
7,709,059 行的平坦门流。按 gap=200 切分得到 2,943 段，主要形状：

| 形状（paid/CCX/CSWAP/CCZ） | 实例数 | T |
|---|---:|---:|
| 99/99/0/0（GF(2^24) `mul24_xor99`） | 311 | 30,789 |
| 186/186/0/0 + 178/178/0/0（external corrected product 对） | 105 + 91 | 35,728 |
| 4/3/0/1（3 CCX + 1 CCZ 的 GF(64) phase 项） | 1,736 | 6,944 |
| 284/277/6/1、419/340/78/1、414/335/78/1（inverse24_reverse209 + routing） | 14 / 7 / 7 | 9,807 |
| 42/42/0/0（GF(2^12) `mul_xor0`） | 244 | 10,248 |
| 其余 <100 T 的小段 | — | ~9,500 |

开头的 119 行（L53,455,037–53,455,155）是一个标准 MBU 零测试 gadget：

```
X q768..q791                          # 24-bit word = S64|S65
R q843; CCX q768 q769 q843            # 11 级 AND ladder ...
...
CCX q862 q791 q857
CCX q857 q887 q847                    # copy-out: q847 ^= [word==0] & q887
HMR q857 b99126; CZ q862 q791 if b    # MBU 还原，0 T
... (逐级 HMR + CZ)
X q768..q791
```

代价 **24 CCX**，相位 0，ladder 全部回 0，`q847` 是一个**活量子 flag**。

## 5. 识别出的分支位与状态寄存器

### 5.1 活量子 flag（1 qubit；计算一次，之后 0 T 使用）

| 位置 | flag | 语义 | 计算代价 | 使用 |
|---|---|---|---:|---|
| unextract L53,455,108 | `q847` | `[S64‖S65 == 0] & q887` | 24 T | L54,245,832–855 的 **24 个 CSWAP**（跨 790,747 行） |
| extract | 8 个不同 ancilla | pole / zero flags | 24 T/个 | 192 CSWAP |
| convert | 6 个控制位：q17/q18/q23（chart 字单 bit）、q864/q879/q889（ancilla flag） | 分支谓词 | — | 4,568 CSWAP |
| unconvert | 15 个 | 同上 + `return_mask` 重建 | — | 5,668 CSWAP |
| unextract | 41 个（全部 ancilla ≥840） | 各 group 的 pole / `Z` / `Zq` | — | 1,536 CSWAP |

`flags.py` 实测：12,012 个 CSWAP 中 **11,964 个由单个 1-bit 活谓词控制**
（专用 flag ancilla，或 chart 字的单个 bit），只有 synthesis/unsynthesis 各
24 个是数据位 SWAP。控制位要么是 1 qubit、要么是数据字的 1 bit——**没有任何
CSWAP 由多 bit 存储的历史控制**。这正是 paper 原则 (b) 的形态。

### 5.2 HMR 经典 mask（0 T、0 Q）

| 量 | 数值 |
|---|---:|
| 全电路 HMR 站点 | 87,382 |
| 其中 ancilla（q≥840） | 73,932 |
| 其中 S 寄存器（q<840） | 13,450 |
| unextract / unconvert / convert | 16,051 / 11,141 / 6,377 |

每个 HMR 把中间值变成 1 个 classical bit（`b*`），之后用 `CZ/CCZ ... if b`
回放相位——在 kickmix 里是 **0 T**。`14.2%` 的决策机器里，相位回放部分全部
是 0 T；付 T 的只有零测试 ladder 本身。

### 5.3 状态寄存器

- `S0..S69` = q0..q839（70 × 12-bit）。`initial`/`extract` 之后它们被复用为
  转换后的 chart 字（N/L/D/A/B/heads），所以 unextract 的 75,472 个 CCX 目标
  是 S 寄存器而不是 ancilla。
- ancilla = q840..q891（52 个），是 ladder / inverse / routing 的 scratch。
- 分支位依赖的状态：24-bit 字 `S64‖S65`（pole）、12-bit 除数 D（`[D==0]`）、
  12/24-bit 归一化字（`normalization`/`gauge`/`chart_inverse` mask）。

## 6. 决策机器的 T 上界：57,119（14.2%），且已在下界

`flag_cost.py` 用「X 前缀 + AND ladder + HMR/CCZ」形态精确匹配：

| 来源 | 站点 | 宽度 | 每个 T | 合计 |
|---|---:|---:|---:|---:|
| **scan** | 4,025 | 12 | 11 | **44,275** |
| extract zero ladder | 7 | 24 | 23 | 161 |
| synthesis zero ladder | 15 | 24 | 23 | 345 |
| unextract zero ladder | 7 | 24 | 23 | 161 |
| unsynthesis zero ladder | 15 | 12 | 11 | 165 |
| routing CSWAP | 12,012 | — | 1 | 12,012 |
| **合计** | | | | **57,119 = 14.2%** |

关键事实：**scan 的 44,275 个 CCX 恰好 = 4,025 × 11**，一个不多一个不少
（`flag_cost.py` 匹配到的 ladder CCX 总数 44,275 = scan 的全部 CCX）。
每个 scan 位置就是一个 12-bit 零测试 + 经典 mask 相位：

```
PUSH_CONDITION if b<is_error>       # 经典 1-bit 条件（0 T）
X q0..q11; 11×CCX ladder -> q878    # [word==0]，11 T
X q0..q11
CZ q878 q48 if b… (×12)             # Forney 相位，0 T
X q0..q11; 11×(HMR+CZ)              # MBU 还原，0 T
X q0..q11
POP_CONDITION
```

n-bit 零测试至少需要 n−1 个 Toffoli（每个输入 bit 都必须进入某个 AND），
所以 **scan 已在信息下界**。这不是「存储的分支决定」，而是 Chien 搜索本身。

## 7. unextract 的 +44,293 定位（精确差分）

`hist_diff.py`（gap=200，同一形状逐桶差分）：

| 形状 | extract | unextract | ΔT |
|---|---:|---:|---:|
| 99/99/0/0（GF(2^24) mul） | 76 | 311 | **+23,265** |
| 4/3/0/1（GF(64) phase gadget） | 0 | 1,736 | +6,944 |
| inverse24_reverse / normalizer 系列（284/419/414/162/158/106/75/67/74/…） | 0 | — | +16,421 |
| extract-only（245/10/104/198/…） | 有 | 0 | −2,337 |
| 合计 | 58,742 | 103,035 | **+44,293** |

+235 个 99-T 乘法块与源码结构吻合：`external_node_chain`（9 个 homogeneous
group，gi=8..16）在 reverse 里跑**两条** scalar chain（重建 N 再撤销），
2·Σ2gi = 432 个 mul24 vs forward 216 个 → +216；再加每个 group 2 个
normalizer 乘法 = +18；合计 234 ≈ 实测 235。

这 216 个乘法是为了**重建 head 值以重放 `gauge` phase 和 `[N==0]`**，不是
存储分支决定；N 是数据（24-bit 字），取出即用没有替代品。

## 8. 切片证明（toy，穷举）

`slice_zero_flag.py`：把 §4 的 119 行 gadget 同构缩到 n=12，用 kickmix
`Simulator` 穷举 2^12 = 4,096 个输入（seed 12345）：

```
shots 4096
out == [q==0]: True
q restored   : True
ladder == 0  : True
phase flips  : 0
T/shot       : 12   (= 11 ladder + 1 copy-out)
```

结论：分支谓词 `[x==0]` **确实是从当前状态解出来的**，代价 n−1，且没有历史
栈。这正是 paper 原则 (a) 的形态——**而 eae 已经这么做了**。

## 9. 判决：no-go（不构建候选、不跑验证器）

不满足「≥10k 静态 T 的块可被替换」：

1. **决策机器总量只有 57,119 T（14.2%）**，其中 44,275 是 scan（Chien 搜索，
   不是分支存储）；可归因于「存储/重算分支决定」的部分 ≤ 832 T。
2. 每个零测试都已在 **n−1 CCX** 下界；每个 routing 已是 1 CSWAP/T。
3. **45.3% 的 T 是乘法块**（42-T GF(2^12) ×3,406 = 143,052 T；99-T
   GF(2^24) ×390 = 38,610 T）。rank 42 / 99 来自显式 tensor decomposition，
   不由分支决定；要 −54k 必须把乘法数或秩砍 ~30%。
4. paper 自己的 DQI 电路 ~4.4e5 T / 1,837 Q 比 eae 更差（T +10%，
   Q²T +127%），说明这些原则在本电路里**已经被吸收**，不是尚未利用的空间。
5. 历史局部改写尺度（−3…−62 门，见 `ABANDONED.md`）与本电路 Δ 的构成一致：
   单点模板的收益被乘法项数量级压制。

因此 `verify_submission_dqi.py` **未运行**：没有可构造的候选，跑 102,400-shot
只会得到一个与 eae 同 SHA 的结果，不构成证据。

## 10. 下一步（若要真的 −13.5%）

只有换算法族，且必须同时重写 generator：

1. **BM + retain/replace rescaling + 常数项恢复 δ**（paper §I.1 的
   σ←σ−ατ / τ−α⁻¹σ 共享路径，`δ_old = σ0·τ0⁻¹·δ_new`）。本电路的
   `synthesis/convert` 是 EEA/Hankel 路线；换 BM 需要新的
   `synthesis/convert/scan`，并用本电路的 MBU + mask 风格重写。
   注意 paper 的 BM 电路实测 T 仍高于 eae，必须在本电路的其他阶段
   （scan 44,275、convert/unconvert 123,197）上同时取回 ~20%。
2. **更低秩乘法**：GF(2^12) 42→36 只能省 ~6×3,406 ≈ 20k（5%），
   GF(2^24) 99→90 再省 ~4k；合计 <6%，不够 13.5%，且需逐块等价证明。
3. **换参数/族**（Hermitian/HOPI 或不同 (m,n,b)）不在本任务范围。

在上述任一路线做出 ≥10k 的**可验证**替换之前，本方向保持 closed。

## 11. 复现用 dump 脚本

见 `dump_kmx.py`（同一命令在 §2 第 1 步）。kmx 与实验脚本都已实际执行；
`artifacts/20261112_branch_recovery/` 下的 JSON/log 是当次输出。

## 12. 验证范围

- 本实验只读 `.kmb`/`.kmx` 与公开源码（`artifacts/20261030_public_audit/
  dqi/somejoint_v21_source/.../final_decoder/{decode,synthesis,conversion}.py`
  作为同族架构的旁证，**eae 的 generator 不在仓库内**）。
- stage 表、CCX 目标分布、CSWAP/HMR/flag 计数是 `.kmx` 逐行实测，精确。
- 切片证明是 toy（n=12）在 kickmix 上的穷举，不是官方验证器。
- **未构建候选、未跑 102,400-shot 官方验证器、无 PASS/FAIL 可报。**
