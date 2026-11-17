# DQI `575b043f`：grantprater 自己的 finder 跑完，closings 已到顶（0 个新增）

日期 2026-11-17。目的：按「−122 DQI Toffoli ≈ +0.011 GM」的汇率，在已提交的 `575b043f`
上继续找 **product-retention pairs** 与 **free Toffoli**。全部在 Kaggle CPU
（kernel `zhuating/qcc-dqi-mine-575b043f`），使用 grantprater 数据集里**他自己的工具**
（`vqcc_measure_out.py` / `vqcc_ir.py` / `vqcc_bitsim.py`，按数据集 README 的包布局摆放）。

## 0. v2 结果（决定性）

```
free  : Toffoli-likes 367,989; free gates by class: {}      ← 0 个「不需要 Toffoli 也不需要 wire」的门
count : 1,498 unconditioned duplicate-product pairs, 0 served (no free wire over the span)
count --retain          : 3,978 pairs, 0 served
count --retain --symclean: 3,978 pairs, 0 served
rewrite --retain --symclean: 0 measure-outs applied
   → sha 575b043f4fee 不变, Toffoli-likes 367,989 不变, qubits 890 不变
```

**结论：`575b043f` 在「保留乘积（measure-out）」这条机制上已经完全饱和。**
3,978 个重复乘积对里**没有一个**在跨度内拥有干净 wire，`free` 类也是 0。
这解释了为什么 grantprater 只拿到 4 个（那 4 个已在 `575b043f` 里，`pairs_4_on_61c8348d.json`）；
它也是本轮 +0.00011 那一步的全部剩余空间。

附带的两个计数（同样有用）：
- `miss: a control written between, its function changed: 236,504`
- `miss: another condition context: 41,456`
- `of the pairs, a control written between and restored (equal symbols): 1,402`

## 1. 正在测的唯一剩余方向：**加 wire 买 retention**

`--retain` 的 3,978 对全部因为「跨度内没有干净 wire」而不可用 —— 也就是说，如果**多加几条 wire**，
它们就可用。而 DQI 的 cost 是 `R·Q²·T`，所以这是一个可以做算术的交换：

```
cost ∝ Q² · T
Q → Q+k :  +2k/Q  (k=1: +0.225%, 预算 +826 T)
T → T−K :  −K/T
盈亏：K > 826·k   (k=1 需 >826 次保留；k=4 需 >3,304)
```

### 实测（kernel v3，COMPLETE）

```
extra  1 : 162 served     预算 826        → 5.1× 亏
extra  2 : 324 served     预算 1,652      → 5.1× 亏
extra  4 : 648 served     预算 3,304      → 5.1× 亏
extra  8 : 1,296 served   预算 6,608      → 5.1× 亏
extra 12 : 1,942 served   预算 9,912      → 5.1× 亏
extra 16 : 2,264 served   预算 13,216     → 5.8× 亏
```

每条额外 wire 只买到约 **162** 次保留，而盈亏需要 **826** 次 —— 差 **5.1×**，且随 k 变差。
逐 k 的 cost 比值（`(Q+k)²/Q² × (T−K)/T`）：k=1 → **1.00181（+0.18%）**，k=16 → **1.02988（+3.0%）**。
**所以「加 wire 买 retention」在每一个 k 上都是净亏，DQI 的 retention 轴彻底关闭。**

## 2. 复现

```bash
# 本机只读小文件（工具的源码），不跑仿真
cd /private/var/.../gp && kaggle datasets download grantprater/vqcc-dqi-61c8348d-merged-closings -f vqcc_measure_out.py --unzip
# Kaggle CPU
python3 scripts/kgpu.py push --dir experiments/frontier/20261117_deep/dqi_mine --account zhuating
```

工具包布局（数据集 README 要求）：`tools/qc/__init__.py`、`tools/qc/passes/__init__.py` 空；
`vqcc_ir.py → qc/ir.py`；`vqcc_bitsim.py → qc/bitsim.py`；`vqcc_measure_out.py → qc/passes/measure_out.py`。

## 3. 结论（两条都关闭）

1. **`575b043f` 的 retention 机制已饱和**：`free` 0 个；3,978 个重复乘积对**全部**因跨度内无干净 wire
   而不可用；`--retain --symclean` 重写 0 次（sha/Toffoli/Q 全不变）。
2. **「加 wire 买 retention」在每一个 k 上净亏**：每加 1 条 wire 只买到 **162** 次保留，
   盈亏需要 **826** 次（**5.1× 亏**）；k=16 时 2,264 vs 13,216（5.8× 亏）。
   逐 k 的 cost 比值 k=1 = **1.00181（+0.18%）**，k=16 = **1.02988（+3.0%）**。

所以本轮 +0.00011（4 个 closings）就是 DQI closing 轴的全部剩余空间；
按「−122 DQI Toffoli ≈ +0.011 GM」的汇率，**DQI 这边再无可挖项**。
