# invsqrt prefix 成本归因审计：−83 C 的目标被误算（2026-11-13）

基线：`artifacts/20261112_newfamily_census/invsqrt.kmb`，SHA `9c708f7b…ef20d1`，
62Q，官方 score **93,555.2627**。本审计只做只读 op 计数和算术块代数次数检查；
**没有生成候选，没有跑官方验证器，没有跑全量 shots**。

## 1. 精确拆分

用 `kmx_parse.py` 按 op 区间统计（`audit.py`，结果在 `audit.json`）：

| 区间 | 内容 | CCX | CSWAP | HMR | T |
|---|---|---:|---:|---:|---:|
| 0–649 | 前导位检测 + 44-CSWAP normaliser | 19 | 44 | 25 | **63** |
| 650–7030 | 纯经典算术块（无 CSWAP/HMR） | **167** | 0 | 0 | **167** |
| 7031–8545 | 收尾 | 7 | 0 | 7 | **7** |
| 合计 | | **193** | **44** | 32 | **237** |

上一轮 `20261112_small_opt` 把 0–8545 整体称为“前导位检测 + 44-CSWAP 归一化”，
并用 `193 CCX / 22 bit = 8.8 AND/bit，naive 下界 5/bit ≈ 110` 推出“省 83 C”。
**这个归因不成立**：真正的 normaliser 只有 63 T（19 CCX + 44 CSWAP），
已经低于那个“110 下界”；167 个 CCX 属于 650–7030 的算术块，不是 normaliser。

## 2. 167-CCX 块不是可线性化的簿记

把 650–7030 抽成 62Q 独立经典子电路（6,381 ops，无 HMR、无条件），
在随机 62-bit 输入上测 2–6 阶布尔导数（每阶 16 个随机样本）：

```
degree 2: 16/16 nonzero
degree 3: 16/16 nonzero
degree 4: 16/16 nonzero
degree 5: 16/16 nonzero
degree 6: 16/16 nonzero
```

即它不是 affine/quadratic，不能靠 `CCX→CX` 或低成本 ESOP 消掉；
它与“多项式/乘法算术块”的形态一致。167 T 已经比论文 reference 的
Horner（1,071 T）、squaring（442 T）、mantissa multiply（1,043 T）、
final NR multiply（867 T）低 6–20 倍，属于高度截断的 62Q 实现。

## 3. 对目标的影响

- 若只重综合 0–649 的 normaliser：当前 63 T；一个“二进制 LZD + barrel shifter”
  的粗算是 5 CCX + 约 110 CSWAP = 115 T，反而更贵。没有 ≥83 C 的空间。
- 若重综合 650–7030 的算术块：需要把 167 T 砍到 ~84 T（−50%），
  即对高次非线性多项式/乘法做全新构造；这不是“prefix normaliser 重综合”，
  而是整套算术重写。
- 当前 `error_1` 恰好是 **19.99998 mHa**（阈值 20），prefix 的任何改动都必须
  逐位保持 62Q 输出状态和相位，不能用近似或 z=0 检查。

## 4. 验证范围

- 做了：op 区间精确计数；650–7030 块的 2–6 阶布尔导数（16 样本/阶）；
  与论文 reference 的成本对比。
- 没做：没有候选 `.kmb`；没有官方 `verify_submission_invsqrt.py`；没有 200,540,928 shots；
  没有 Kaggle 提交/push。

## 5. 下一步

真正可试的只剩 650–7030 算术块的全新构造（Horner/Estrin/Karatsuba/截断乘法），
目标是把 167 T 降到 <143 T（Q 不变时净赚 >24 C 才值得，若加 1 Q 需 >24 C；
若目标 −83 C 则需 <84 T）。在 62Q、error_1 恰好卡门的约束下，这属于研究级重写；
若 3 小时盒内没有可官方 PASS 的候选，prefix 线应记为 no-go，而不是继续在
normaliser 上找不存在的 83 C。
