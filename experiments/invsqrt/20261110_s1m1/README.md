# S1 重算链 M1 降级试点（`20261110_s1m1`）：closed，无候选、无验证器运行

日期：2026-11-10；分支 `codex/invsqrt-research`；工作区 `.worktree/invsqrt/`。
本轮是新 family（`26ebf39d`）上的结构性改写试点，不重复已 closed 的六方向与
Hosen/微角工作（`experiments/invsqrt/README.md`、
`20261110_hosen_sens/README.md`：S1/S2 普查 0 候选、A3 微角 FAIL）。

固定输入（只读）：主仓库 `artifacts/20261110_gengsr_252268/release/invsqrt.kmb`
（实测 SHA-256 `26ebf39d…5cc9bc` 全文见 `evidence.json`，62Q / 36,686 ops；
S1=`[8893:16329)`，365 无条件 CCX，见
`experiments/invsqrt/20261110_gengsr_audit/README.md` §2）。
注意：`20261110_gengsr_audit/evidence.json` 记的 `new_sha256` 有一 nibble 笔误
（`…efc3cc…`），实际文件与主仓库提交回执
（`submissions/20261110_gengsr_252268/README.md`）均为 `…efc5cc…`，
已用 `sha256sum` + 脚本内断言复核（本目录脚本断言通过的是 `c5` 版）。
不影响审计的门数/分区结论（ops 数 36,686 一致），此处如实记录差异。

## 1. 试点单元

S1 内无序控制+目标相同的 k=2 对共 **13 对**（`s1m1_pilot.py::k2_pairs`，
CCX 控制对称口径；S1 内 k=3 同三元组另有 `(q40,q47)->q51` 一组，
见下）。按任务取跨度最短者为试点：

- 试点：`(q21,q25)->q50` @ `[10746, 10757)`，span **11**（13 对中最短）。
  形态：`10738 HMR q50` 清零 → `10746 CCX q21 q25 q50`（q50=p1）→ 10 条 CX/X →
  `10757 CCX q21 q25 q50`（q50^=p2）。两 CCX 之间 **0 HMR**，且其间
  `CX q40 q25 / CX q59 q21 / CX q40 q21 / CX q51 q21…` 改写了输入线。
- 最短的“夹 HMR”对（ Span 92，`(q28,q38)->q40` @ `[12605,12697)` +
  `(q39,q40)->q61` @ `[12606,12698)`，其间各 10 HMR，含 `HMR q40`）同步核查，
  结论相同（见 §2）。

拟议 M1 改写（试点）：删第二次重算 `@10757 CCX`，
换成保留首次乘积 + CX 重装（save/reload/clean 共 3 条免费 CX，需 1 根零线；
`q57` 在 `[10797:14430)` 全程为零但覆盖不了本窗——即使假设理想零线，
下述等价性已先失败，故闲线分析止于此）。
假设等价成立时的门数差：**CCX −1，CX +3（免费），score ≈ −62 分**；
未成立，故未构建候选。

## 2. 等价证据（全定义域字比较 + 穷举切片，二者一致，取“失败”侧）

1. **全定义域字比较**（`run_bit_parallel_audit` 同口径，全部 3,133,452 输入，
   无条件经典骨架 X/CX/CCX/SWAP/CSWAP/HMR 位追踪；对角门不影响比特）：
   试点对两次乘积值 `p1=q21&q25@10746` vs `p2=q21&q25@10757` 在可达状态上
   **diff = 1,391,290 输入（~44%）**，pop1=1,228,802 / pop2=992,610。
   原电路出口 `q50=p1^p2`，理想保留改写出口 `q50=0`，差 `p1^p2≠0` ——
   即使给完美零线，改写仍错 ~44% 输入。**等价不成立。**
2. **Simulator 切片穷举**（`exhaustive_slice_check` 同方法，切片
   `new[10746:10758)`，12 相关线 → 4096 入口基态全枚举）：
   `p1` vs `p2` diff **1536/4096（37.5%）** ——作为独立函数亦不等，
   与可达态结论同向。
3. 普查扩展（试点失败后仅作总量证伪，不作候选扩展）：
   13 对 k=2 的可达 diff 最小 **266,255**（span-92 `q39,q40->q61`），
   其余 42 万~140 万；span-92 `q28,q38->q40` diff 495,655；
   k=3 组 `(q40,q47)->q51` 两段 diff 819,320 / 414,771。
   **13/13 均为“同文本、不同值”的累加/线复用**（无复位累加或 HMR 复位后算新值），
   没有一对是可保留复用的真重算。`convertible_pairs = 0`。

机制解释：S1 的 +53 CCX 是实质算术累加（不同输入值的 AND 先后 XOR 进同一
累加器，如 q50=p1^p2），或 HMR 回收线复用后的新计算（p1≠p2 已实测），
不是 Bennett 式冗余重算。M1“保留+重装”模板在此无着陆点。

## 3. 总量估算

arch review（`20261110_arch_review/README.md` §2）设想“S1 池 10% 转化 ≈
−2000 分（~32 CCX）”。本轮普查证伪其前提：S1 内全部 13 个 k=2 同文本对
+ 1 个 k=3 组的可达值均不相等，可转对 **0**，故 M1 在 S1 重算链上的总量级为
**0 CCX / 0 分**。按任务门控（首个单元成功后才扩展），不做全 S1 改写设计。

## 验证范围声明（必须如实区分）

- **官方验证器运行 0 次**：无净负候选，未构建任何 `.kmb`，未运行验证器。
  引用的 PASS（94537.59）为主仓库提交回执与作者日志，既有证据。
- 本轮执行：只读普查脚本 1 个（`s1m1_pilot.py`，macOS PyPI kickmix，
  `.venv/bin/python`），输出 `evidence.json`（13 对 span/HMR/pop/diff +
  试点 4096 态切片 + 假设门数差）；另有 3 次同口径手工核查
  （q40/q57 零线生命期、span-92 窗、k=3 组），数字已并入上文。
- 复现：`.venv/bin/python experiments/invsqrt/20261110_s1m1/s1m1_pilot.py
  --out-json experiments/invsqrt/20261110_s1m1/evidence.json`
  （只读主仓库 KMB；分钟级，含 3.1M 输入位并行追踪）。
- 未打包、未提交、未推送；只写本目录（无候选 `.kmb` 写入 `artifacts/`）。

## 引用

- 分区/S1 描述：`20261110_gengsr_audit/README.md` §2 与 `evidence.json`。
- 位并行/切片方法：`20261110_gengsr_audit/audit_gengsr.py`
  （`run_bit_parallel_audit`、`exhaustive_slice_check`）。
- HMR 口径与“脏借用即亏”：`20261109_dirtyfrag_proof`、
  `20261110_hosen_sens/README.md` §1。
- 上游 family 来源：`gengsr/lb-25-2268-shifter-46-own-chemistry-loaders` v1
  （交叉对照 Özer v91、Maoxin 25.218，见审计 README §0）。
