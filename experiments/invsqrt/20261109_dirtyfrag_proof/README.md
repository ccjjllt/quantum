# 脏借用四门恒等式实测仲裁（`q21,q25→q28` k=2 组）

日期：2026-11-09；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
基线：Public Frontier `7c10edba`（62Q / 53,686 ops / 1403 Toffoli-like）。

## 对象
- 同守卫（`guard []`，depth 0、无 `if`）True 组：`CCX q21 q25 q28 @15987` 与 `@16262`
 （全定义域字全等，`prod_pop 0`），跨度 275 ops。
- 借用线 `q4`：跨度内零触碰（`mid-touch 0`），起点脏（13 根未触碰线全脏，`clean []`）。

## 构造（逐处四门恒等式，每处）
- `CCX q21 q25 q28` → `CCX q21 q25 q4; CX q4 q28; CCX q21 q25 q4; CX q4 q28`
 （`q4` 在相邻 4 门内值稳定恒成立；目标得精确值，`q4` 复原）。
- 切片 `[0..16262]`（16,263 ops）基线 vs 改写，用 `km.Simulator` 对比。

## 实测
- 静态：切片基线 295 → 改写 297 Toffoli-like，**净 +2 CCX（+1/处）**；
  旧脚本 `net=+(k-1)=+1` 少计 1，此处纠正为 `+k=+2`（k=2）。
- 语义：8 x × 2 seeds = 16 格，全 62-qubit 向量 0 差异
 （`cells 16, mismatches 0`；HMR 流对齐，因未新增测量）。
- 脚本：`experiments/invsqrt/20261109_dirtyfrag_proof/check_fragment.py`；
  结果：`artifacts/20261109_dirtyfrag_proof/result.json`。

## 结论
恒等式值正确（`q4` 复原、目标正确），但每处 +1 CCX；无干净线时 k=2 净 +2（+124 分 @62Q），
做即亏。本组 closed。未构建全电路候选，未跑官方验证器（语义已由切片 Simulator 仲裁；
全量验证器只会复述 +2 静态增量），无提交/推送。
