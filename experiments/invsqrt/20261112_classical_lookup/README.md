# invsqrt 经典查表捷径：判定为不可行（2026-11-12）

## 假设

invsqrt verifier 对每个 x 从计算基 |x>|0> 出发，检查 x 恢复、scratch 清空和相位。
若能把 x 读入 classical bits，再按 x 条件施加一个 `Z_POW`，成本会从 62Q/1,214 Toffoli
降到约 45Q/1 个旋转（score ~300），是数量级提升。

## 关键检查

- `kickmix` 的测量只有 `HMR`：**H**adamard + **M**easure + **R**eset，即 X-basis
  demolition measurement。指令集（`kickmix_instructions.md`）没有独立 `H`，也没有
  Z-basis measurement。
- 要在 Z basis 读 x，需要先对 copy 施加 H 再 `HMR`；但 H 不是可选 gate，无法在
  `HMR` 之外单独使用。
- 直接对 |x> copy 做 `HMR` 得到的是随机 X-basis 结果，不携带 x 的 Z 值；phase
  kickback 也不能替代读值。
- 因此“copy x → classical bits → 条件 Z_POW”的路径被 gate set 封死；不是成本或
  精度问题，是原语缺失。

## 结论

不构建候选。invsqrt 仍只能在相干 gate set 内做多项式/移位/splice；62Q 局部面饱和的
结论不受影响。该检查只读文档 + 小电路 API，未跑 200M verifier。
