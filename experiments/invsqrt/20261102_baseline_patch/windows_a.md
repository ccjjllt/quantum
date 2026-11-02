# A 类四窗口 verdict（2026-11-04 实测，逐窗定论）

## 改写一：相同相位函数条件合并

- 前提普查：四窗口无重复条件 CCZ 目标（invB1/B2/tail1 相位目标全 distinct；
  tail2 重复全系 CZ）。
- tail2 四组条件 CZ 对数据稳定性（`merge_stable.py`，离线 z3）：
  - q15q5：q15 已证不同 → 合并不能（已证不等）。
  - q17q61：q17 已证不同 → 合并不能（已证不等）。
  - q18q13（两对）：一线 identical、一线 UNKNOWN → 未证（UNKNOWN）。
  - q32q12：双 UNKNOWN → 未证（UNKNOWN）。
- 即使 UNKNOWN 组证出合并：CZ 系 Clifford，执行成本零收益
  （分支精确账本：2→0/1→1/0→0，省的是免费门）→ 成本不优。
  故本改写无候选（2 组已证不能，2 组 UNKNOWN 但零收益封顶）。
- invB fixup 对（31467/31495）：目标本就不同（q43q47 vs q42q30）→ 无目标。

## 改写二：因式分解共享已有线性组合

- exact 同值共享 screen：四窗口 0 命中（`factor_screen.json`）。
- 名义控制对复核：invB 无重复控制对；tail2 五组中三组控制已证不稳定
  （Bennett 对），两组函数 UNKNOWN——但同属“2 用共享净零 CCX”算术，
  且 tail2 CCX 多为条件链一环，借线横跨代价更高 → 成本不优。
- 本改写无候选。

## A 类计数

- invB1：无目标 / 无命中 → 无候选。
- invB2：同上（孪生结构）→ 无候选。
- tail1：5 条件 CCZ 全异目标 → 无候选。
- tail2：合并组或已证不能或零收益封顶 → 无候选。
- A 类证明通过候选：0。
