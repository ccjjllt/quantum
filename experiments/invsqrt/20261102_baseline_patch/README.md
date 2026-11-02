# 62Q 基线补丁 Round 1：工具与筛选现状（2026-11-03 实测）

分支 `invsqrt-generator-rebuild`（未推送）。基线哈希已钉死
`bce2948f…`（`patch62.py --crosscheck` 每次加载断言）。

## 1. 筛选工具（§2，新建 `patch62.py`，CROSSCHECK PASS）

- 单一符号输入环境：前缀跑一次，fork（deepcopy）出原块/候选块；
  跨对象整数 ID 永不直接比较（同对象内 same-id 才作等价）。
- 条件栈 + BIT_* + 版本化测量叶全跟踪（与 `retain62.interpret`
  全基线 62/62 逐位一致）；CX/CCX 写入含目标旧值。
- 证明比较：全部输出线（未触碰线记 untouched-identical，触碰线切 entry 切片证明）、
  窗后使用的经典位、条件环境、精确总相位（含数据线相位账本 + 条件证明；
  XOR-merge 只认对角 π 门分支精确对）。
- ≤12 符号穷举，否则 Z3（离线 `uv run --offline --with z3-solver`，z3 5.3.3，
  单证明 60s；超时/缺求解器记 UNKNOWN）。
- Round-1 门禁：HMR/R/Z_POW 序列必须逐项一致；条件栈平衡；不跨一般旋转。
- 途中修掉两个真 bug：测量叶键用绝对序号（候选移位即错位→改序列号键）；
  align 把多原子 vid 内 qubit 误判 fresh（→按原子号 0..61 判定）。

## 2. FAIL 路径验证（工具自证有效）

- 片段 `[35331,35379)` 去第二 CCX：sliced-z3 `not-equivalent`（q18，70 vars）。
- 三组 same-op-twice 对照：控制全不稳定 → 均为 Bennett 对，无冗余。

## 3. A 窗口普查（指令锚点已确认，`patch_census.json`）

- invB1/invB2/tail1：重复相位目标 0 组 → 条件合并无目标。
- tail2：7 组重复 CZ 对，但全是“无条件计算 + 条件修正”配对；
  CZ 系 Clifford，合并零 C 收益；CCZ 无重复目标。
- 全窗口/CCX 因式 exact screen：0 命中（`factor_screen.json`）。

## 4. B 片段（20 个 2–4 CCX 已挖，取前 12）

- 共享控制对 3 组（[35331]/[35485]/[35557]）+ tail2 5 组；
  已验三组全是 Bennett 对；其余待下一轮逐一切片证明。
- 下一步：线性基变换后的因式共享（B 指定的第二改写），逐片段证明。

## 5. 候选计数

- 已生成候选：0（8 个上限未动）。证明通过才计数；UNKNOWN/FAIL 不计数。
- 本轮结论 tendency：A 窗口 C 杠杆稀薄（条件 CCZ 无重复目标）；
  B 是剩余希望，需逐片段证明说话。
