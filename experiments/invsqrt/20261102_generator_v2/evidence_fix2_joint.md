# Fix2: joint_phase62 联合修正撤回 + 重算（invsqrt §2-2）

范围：只重做 `joint_phase62.py` 第 (a) 部分的条件修正 census
（完整条件栈 + BIT_*/版本化测量变量解析），兼查计算基输出与总相位；
(b) CSWAP/行合并屏的 `value_signature_unequal` 引用改记 TO-PROVE
（见 evidence_fix1 R4），数字本身（201 CSWAP、705/0/0）不动。
不跑官方验证，不改 verifier，不动旧脚本文件（冻结为证据）。

复现（2026-11-02 实测，均为只读 census）：

```
uv run python -c "<Fix2-census 段：inline-if 计数 vs 栈感知 gated 计数；Z_POW 68 分类>"
uv run python -c "<Fix2-BIT 段：b414/b308/b341/b457/b458 writers；PUSH 按位计数；HMR 按位计数>"
```

机器可读重算表：`artifacts/20261102_generator_v2/invsqrt/fix2_census.json`。

## 1. 撤回声明

`joint_phase62.json` 的 verdict——“conditional-T pool is ~1.5 C expected
circuit-wide and instances differ”（及 `trackB_discrete.md` 实验 3 的
“条件 T 池期望全电路仅 ~1.5 C”）——正式撤回。撤回理由（三条独立，每条
都足以推翻原计算）：

1. 条件 census 只计了行内 `if`（`if "if" in p`），漏掉全部 PUSH_CONDITION
   栈门控操作：栈感知 gated 比 inline 多出 CX +1591、CCZ +134、X +394、
   CCX +80、C Z +393、Z +55、NEG +53、HMR +84、R +19（见 §2 表）。
   其中 80 个条件 CCX 与 1591 个栈门控 CX 直接改变计算基输出，
   原结论的“修正只影响相位”框架不成立。
2. 版本化测量变量未解析。`b341` 有 66 次 HMR 写（同 bit 索引，
   last-write-wins，无版本区分）；`b308` 有 2 次写（30200、31030），
   31122 块读到的是第 2 版。`if b341` 在不同位置看到的是不同测量结果，
   原 census 把它们当同一比特统计，期望成本 `0.5·3/4` 的独立同分布
   假设无依据（P(结果=1) 与输入有关，未知）。
3. `b414` 的 15 个条件 Z_POW（9 个 T-class）共享同一次 HMR 结果
   （28934 单 writer），3 个块不是独立试验；“删 2 个块省
   2×0.375 C”的上界算法把一次抛硬币算了三次。

## 2. 重算表（新基线 47258 ops，PUSH/POP 全局 360/360、min_depth 0）

| op | inline-if（旧口径） | 栈感知 gated（新） | 漏计 |
|---|---|---|---|
| CZ | 10418 | 10811 | +393 |
| CX | 1494 | 3085 | +1591 |
| CCZ | 7 | 141 | +134 |
| X | 0 | 394 | +394 |
| CCX | 0 | 80 | +80 |
| Z | 1559 | 1614 | +55 |
| NEG | 44 | 97 | +53 |
| HMR | 0 | 84 | +84 |
| R | 0 | 19 | +19 |
| Z_POW | 20 | 20 | 0（20 个全是行内 if、depth 0，见下） |
| BIT_* | 512（495 INV+7 S0+10 S1） | 708（495+107+106） | 196 个无条件经典位操作 |

Z_POW 68 分开计数（一般旋转 / T / Clifford）：

| | Clifford（半圈 1/2 倍数） | T（1/4 非 1/2） | 一般旋转（41 条，条件栈全空，`rotation_map` 41 行） |
|---|---|---|---|
| 条件 20 | 8（b414×6 + b308×2：每块 1.5/0.5 Clifford + 1.75×2/0.25 T） | 12（b414×9 + b308×3） | 0 |
| 无条件 48 | 6 | 1 | 41 |
| 合计 68 | 14 | 13 | 41 |

版本化位（writers → readers）：

| 位 | writers | readers（inline-if + PUSH） |
|---|---|---|
| b414 | 1（28934 HMR q51） | 15 Z_POW + 11 PUSH + 10 Z + 2 CZ（3 块共享同一结果） |
| b308 | 2（30200 HMR q57；31030 HMR q61） | 5 Z_POW + 2 Z + 4 CZ（31122 块见第 2 版） |
| b341 | 66（全 HMR，如 25089/25094/25123…；copy 内 28865/28878 各一） | copy 内 `CZ if b341`×3 等（每次见当时最新版） |
| b457/b458 | 各 1（25597 / 28836） | 条件环境 src[b457] vs copy[b458]（Fix1 R3 链的环境差即此） |

经典位全景：402 个被测 bit、897 次 HMR；`b0` 被测 389 次；
273 个不同 bit 被 PUSH（top b413×16、b414×11）；inline-if top 位是
b12600×392、b0×388 等经典/常量位——条件 CX/CZ/X 的选择位大多不是
测量结果，原“单比特条件、双结果覆盖即完备”的论述只覆盖了
Z_POW 修正子集，不覆盖基输出改变。

## 3. 新 verdict（替代“~1.5C / INAPPLICABLE”）

- 条件 T 期望成本：UNKNOWN（P(比特=1) 输入相关且版本混杂，无 0.5 依据；
  b414 三块共享一次结果）。静态条件 T 池为 12（b414 9 + b308 3），
  执行成本记 TO-PROVE。
- 条件基输出操作（80 CCX + 3085 CX + 394 X gated，含栈门控部分）：
  TO-PROVE（执行与否依赖版本化测量结果；`C = executed Toffoli-like + T/4`
  的静态口径对它们不适用，旧成本行未计入此项）。
- 多比特联合修正：273 个 PUSH 位存在嵌套可能，全局首尾平衡
  （360/360）不代表局部块内外环境一致；“0 个多比特联合修正”改为
  TO-PROVE（未做版本化栈 AND 分析）。
- 仍不申报任何清理（方向不变）：无确定性修正覆盖全部（版本化）测量
  结果的证明；行合并 extras 表数字保留为假设，`carry 13 CCX 零共享`
  一条改记 TO-PROVE（引用 Fix1 R3）。

实际命令输出（粘贴，`tail` 段）：

```
INLINE-IF by kind: {'CZ': 10418, 'Z': 1559, 'NEG': 44, 'PUSH_CONDITION': 360, 'BIT_INVERT': 495, 'CX': 1494, 'BIT_STORE0': 7, 'Z_POW': 20, 'BIT_STORE1': 10, 'CCZ': 7}
PUSH= 360 POP= 360 mindepth= 0 neg-depth pops seen= 0
GATED (stack>0 OR inline-if) by kind: {'CZ': 10811, 'Z': 1614, 'NEG': 97, 'BIT_INVERT': 495, 'CX': 3085, 'CCZ': 141, 'BIT_STORE0': 7, 'X': 394, 'CCX': 80, 'HMR': 84, 'Z_POW': 20, 'BIT_STORE1': 11, 'R': 19}
Z_POW total 68
Z_POW classes (ALL): {'clifford': 14, 'rotation': 41, 't': 13}
```

```
b414 writers= 1 / b308 writers= 2 / b341 writers= 66 / b457 writers= 1 / b458 writers= 1
PUSH total 360 POP 360 distinct bits pushed: 273
b414 inline readers: {'Z': 10, 'PUSH_CONDITION': 11, 'CZ': 2, 'Z_POW': 15}
b308 inline readers: {'Z': 2, 'CZ': 4, 'Z_POW': 5}
distinct measured bits: 402 total HMR: 897
uncond Z_POW: {'clifford': 6, 'rotation': 41, 't': 1} cond Z_POW: {'clifford': 8, 't': 12}
```

官方验证：0 shots（未运行）。Kaggle 提交：无。
