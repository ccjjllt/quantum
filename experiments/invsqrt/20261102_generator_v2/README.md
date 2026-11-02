# 20261102_generator_v2：独立整数生成器路线（新计划）

分支 `invsqrt-generator-rebuild`。阶段顺序：修正证据 → 独立整数生成器 → 首次完整官方 PASS → 实测降宽降门 → 5% 候选。
数值拟合通过不再替代电路进展；拟合已暂停，此后每次拟合必须对应已实现的算术布局。

## 定点合同独立验证（主线程，PASS）

脚本 `contract62.py`：模型侧纯整数（CSD 精确分式 + `RH(z)=floor(z+1/2)`），目标/容差侧用官方 `reference_values`。
源表 `trackB_fit_7_8_16_5_trunc.json`（`fit_sha256=72154a80…4a1adc821`）。

- 整数表：`artifacts/20261102_generator_v2/invsqrt/int_tables_7_8_16_5_trunc.json`，
  `tables_sha256=65ae9946…176d8231`（格式 256×u64-B LE + 256×u32-A LE + 256×u16-R LE）。
  B∈[3039970672,6062172360]（<2^33），A∈[743632,2948520]（<2^22），R∈[273,2151]（<2^12）。
  计划预期哈希 `8d823a63…` 因序列化格式未指定而不同——已记录本格式，正确性以全域检查为准。
- 全域（`contract_full.log`，2026-11-02 实测）：3,133,452 输入失败 0，
  maxrel **0.6096375069**，最坏 x=**2506015**（ae 2.2954083078730037e-11 turns），
  最小余量 **271129065** ×2⁻⁶⁴ turns，V∈(12439556932177,24879107506176)⊂(0,2^45)。
- 与 `trackB_full_7_8_16_5_trunc.json`（0.6096375068545294、同 x、同 ae、同余量）逐位一致——
  整数合同与浮点模型+重拟合角度两条路径互相印证。
- 中途发现并修复 `RH` 负数 bug：初版对负数是向零截断，238/256 个 A 项差 1 ulp；
  修复后 maxrel 才与浮点路径对齐。教训已记。

这些仍是数值模型结果，不是电路验证。官方验证 0 shots。

## 并行子智能体（进行中）

- 证据修正五项（§2）：ses_e64d5f2b5ffeuYJ2iy6uplzAiR。
- 生成器原语与调度（§3–§4）：ses_e64d5f2b4ffep3Vg5jNCSwFqPa。

## 复现

```
uv run python experiments/invsqrt/20261102_generator_v2/contract62.py --tables-only
uv run python experiments/invsqrt/20261102_generator_v2/contract62.py --full
```
