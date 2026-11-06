# Q889 六峰宽度审计：全电路后向存活分析（2026-11-06）

## 假设

若存在 ≥2 个从不参与任何可观测行为（HMR coin、CZ/Z/R 相位/旋转、
经可逆门传导到上述者）的 qubit，则可删除其全部写入门并缩减分配，
Q 891→889，T 不变 → 约 +0.15% GM（确定性增益，无需改算法）。

## 改动

- 58208707 ops 单遍后向扫描（int bitmask 实现，C 速度），
  修正版条件 USE 规则：
  CCX(a,b,t)：t live 才加 {a,b}；CX：b live 才加 a；
  X：恒等（不增不减）；HMR：恒加（coin 恒为输出）；
  SWAP/CSWAP：条件添加；CZ/Z/R/CCZ/未知：恒加涉及线（保守，保正确性）；
  BIT/NEG/PUSH/POP/INFO：忽略。
- 旧版（无条件 USE）有两个 bug，已废弃，以本版为准。

## 观察（2026-11-06已执行）

- `true_peak_live = 891`（58M 中的 op 52139640 处首次达到），
  `n_ever_live = 891`，`never_live_wires = []`。
- 首末触及区间：最小跨度 55M/58M ops，中位数 ~全电路，born-late 和
  die-early（按中点计）均为 0——没有任何线可被复用槽容纳。
  （`artifacts/20261106_eeakernel_rewrite/intervals.json`）
- 结论：无可证明死线。Q889 不能靠删线/重排实现；
  需要算法级改动（不同分解/编码）或重综合。
- 附带：全操作类型普查确认分析无遗漏
  （CX 52M/CCX 382636/CZ 812714/HMR 79416/R 55876/X 250k/
  SWAP 1.6M/CSWAP 13064/CCZ 1477/NEG 554/BIT/PUSH/POP）。

## 证据

- `artifacts/20261106_eeakernel_rewrite/liveness3.json`
  （peak/ever-live/never-live 列表 + 方法注记）。
- 脚本 `liveness3.py`（条件 USE；旧版 `liveness*.py` 已废弃，
  勿用——首版 R/W 语义错误，曾给出相同的 891 数值但理由错误）。

## 下一步

- DQI 可证明方向已穷尽（peephole 零对消 / 模板删1删2全零 /
  QQ 移植三重证伪 / 融合对偶实例证伪 / 死线零 / 峰值=分配）。
  剩余全部需要：(a) 上游 refitter/源生成器（缺失），
  (b) scalar 量子感知重写 + 官方验证循环（大投入），
  (c) 接受当前最优，转向 invsqrt/dfthcsos 或提交。
