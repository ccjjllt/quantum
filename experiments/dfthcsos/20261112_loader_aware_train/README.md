# 化学 loader-aware 训练（`20261112_loader_aware_train`）

日期：2026-11-12；分支 `codex/dfthcsos-research`；工作区 `.worktree/dfthcsos/`。
性质：在 `refined_845`（R8/B143/C45，当前表同族）上把 loader 代理成本加入训练目标，
检验能否在误差门内把 loader 从 4,097 T/pass 降下来。

## 假设

当前 Maoxin v22 loader 4,097 T/pass 已近构造最优，但训练目标只最小化系数误差，
不看 loader 成本。若在损失里加入 loader 代理项（λ·proxy），可能找到一张
误差仍 ≤20 mHa、但角度字更“好压缩”的表，从而降低 tensorqrom 成本。

## 方法

- 起点：`refined_845` 同族模型，`loadertrain.py` 在 E2 误差上加入 `lam * proxy`。
- λ ∈ {0, 1e-4, 3e-4, 1e-3, 3e-4…1e2}，同一 seed，输出 `train_lam*.npz`。
- 评估：`eval_candidates.py` 用当前 loader 管线重算 e1/e2、Λ、E_gap、λeff、proxy。

## 结果（实测）

| λ | e1 (mHa) | e2 (mHa) | λeff | proxy | 备注 |
|---:|---:|---:|---:|---:|---|
| 0 | 19.99998 | 19.99998 | 46.907 | 5,266 | 误差门边缘；proxy 比当前 5,237 差 |
| 1e-4 | 1,617.1 | 324.9 | 66.312 | 5,327 | 退化 |
| 3e-4 … 1e2 | 1,617.1 | 324.9 | 66.312 | 5,327 | 同上，λ 已无区分度 |

- 当前生产件（`f21b8a87`）的同口径 proxy = 5,237（loader 4,097 + cache 1,140），
  λ=0 训练件 5,266 **更差**；λ>0 全部落入误差 1,600+ mHa 的退化解。
- 结论：在该参数化/损失下，loader-aware 训练不能产生可用表；误差约束与
  loader 代理项没有形成有效前沿。

## 判决

**no-go**：不构建候选、不跑官方验证器。当前表（`refined_845` 系，λeff 46.907）
保持；loader T 的进一步下降不再走“训练目标加正则”这条路。

## 验证范围

- 全部数字来自本地 `.npz` 重算（`train_lam*.npz` + `eval_candidates.py`），
  不是官方验证器；没有 PASS/FAIL 可报。
- 未修改 `artifacts/20261112_eae_candidate/dfthcsos/` 的生产件。
