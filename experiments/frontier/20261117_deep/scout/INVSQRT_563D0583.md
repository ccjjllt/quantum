# invsqrt `563d0583` — 提取与出处（2026-11-17）

## 数字

| 件 | Q | C = Toffoli + T/4 + 旋转 | 官方 cost | 对 `0af21cb8` |
|---|---:|---:|---:|---:|
| `0af21cb8`（当前出货） | 44 | 1,699.9401 | 74,797.365357 | — |
| **`563d0583`（新）** | **44** | **1,694.5661** | **74,560.91** | **−0.3160%** |

GM 影响：28.150932 → **28.180659**（**+0.0297**）。差值是纯结构性的：
ΔC = 5.374 = ΔToffoli（1,459.375 → 1,454.0），33 个旋转/T 部分不变（T-eq 240.565 相同），
所以相位余量与 salt 暴露面跟 `0af21cb8` 一致（后者已过 8/8 salts）。

## 出处

- 载体：`maoxin123/qcc-28-17-4-022-toffoli-chemistry-loaders`（2026-11-17 12:16 UTC），
  `kaggle kernels pull` 得到的 `.ipynb` 第 5 个 code cell 里的 `INV = "..."`（zlib+base64）。
- 该 notebook 自述：*"Version 2 adds our newer 44-qubit invsqrt `563d0583` (74,560.91, was 74,797.37)"*，
  并给出 local GM **28.17402**。
- 独立复现：`ahoirg/qcc-reproducible-circuit-portfolio` 在默认 salt、全量 200,540,928 shots 下复验。
- 我们这边只做了**字节级**校验，尚未跑官方 verifier（等最终 integrator 端到端跑）。

## 提取验证（本地，纯解码）

```
.ipynb cell5  INV  ->  base64 34,780 chars  ->  zlib  ->  179,308 bytes
sha256 = 563d0583f736afc2d8111f376bc1bd5ce6aef686525b0dd281fc1f2b4eb09321   ← 与 notebook 标注一致
已存：experiments/frontier/20261116_push/pipeline/invsqrt_563d0583.kmb.b64
```

## 注意

同一 notebook 里的 DQI 是 `957d6733`，按 GM 28.17402 反解它约 **346.5e9**，
**比我们的 `575b043f`（346.4098e9）略差**。所以组合时应保留我们的 DQI：
`563d0583` + `575b043f` + chem ⇒ GM ≈ **28.181**。
