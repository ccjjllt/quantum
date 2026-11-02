# trunc_a20r8.md：A20R8 行截断贪心 —— 全拒（0/22），方向关闭

分支 `invsqrt-generator-rebuild`。对象：A20R8-idesc 表（基线 maxrel 0.8945，
余量仅 0.105）。方法：加数幅度降序贪心，逐行舍入到 2^20，全域守门
（`trunc_subset.log`，EXIT=0；base 断言 0.894535/0 通过）。

结果：22 行**全部 reject**（首轮即败，无一接受；最轻 R7 亦 8 fails，
A0 109 fails）。最终集合为空。

结论：
- A20R8 在 k=20 无任何单行截断余量（BOTH 系在同 k 下曾有 8 行可过——
  头部 room 0.38 vs 0.105 的差别）。
- 窄 V 行截断内核（为 BOTH 头部 room 设计）不迁移到 A20R8；
  A20R8-narrow 组合维持否决（`narrow_v.md` §7）。
- 过程 bug 记录（三轮 65280 同根因）：per-row 框架把 J13 sign 行
  与 sub 行同作减法；sign 行必须加。表文件本身完好（factored 0.8945 逐位一致），
  教训：行框架改动必须过 base 断言（本次已立规矩并通过）。
- 未试的窄组合（容器窄 + 全行，理论可过）因维护三线 datapath
  与期望 −3% 不成比例，不启动。

A20R8 可用形态仅 R8I 宽 V 版（已验证 2133173.37）。行截断线在此关闭。
