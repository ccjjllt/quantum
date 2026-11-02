# hmr_full_veto.md：全反算 HMR 化 —— 结构性否决（多消费者 carry）

分支 `invsqrt-generator-rebuild`。`uncompute_upside.md` 给出全改上限 2.1x；
本文件论证该上限不可达（HMR 路径），无需写码，用已提交代码为证据。
无电路改动，无新运行（静态结构论证 + 已有预筛证据引用）。

## 1. HMR temporary-AND 的适用前提（`hmr_cleanup.md` §2 已立）

1. 被清理的 AND 结果是**单消费者**（算出、用一次、即清）；
2. 控制线在清理时**保持原值**（修正可只依赖测量结果 + 守恒量）；
3. 修正函数便宜（二次型 CZ 覆盖；高次多项式有 ANF 下界——square 已否决）。

copy 行三条全满足，故落地（−2846 toff）。

## 2. ripple-carry 逐条违反（`width_opt62.py:506-531` 已提交代码）

Cuccaro MAJ `(c,a,bb)`：`CX(c,bb); CX(c,a); CCX(a,bb,c)` ——
控制线 a、bb 被**修改**（a^=c，bb^=c），违反前提 2。
新 carry c' 的消费者：(a) 同 bit UMA（恢复 a、bb 用），(b) 下一 bit MAJ 的 carry-in
（行内核 carry[0] 跨 bit 线程化，`_narrow_r1_row_fwd` 等）——**双消费者**，
违反前提 1。UMA 本身就是该 carry 的 Bennett 配对，改测量即重演 square 困境
（进位链是逐 bit 复合的多项式，ANF 下界那一套同样适用）。

## 3. 覆盖面清点

- A1/R1/square/lz 行内 MAJ/UMA carry：全部多消费者 + 控制被改 → 不适用。
- QROM decode match 扇出：多消费者（`window_qrom.md` T1 否决已记）。
- square 进位多项式：ANF 下界 654 > 302（`hmr_square.md` 已记）。
- 适用且已落地：copy 组 single-consumer AND（−2846，已兑现）。
结论：相干反算 bulk（6782，53%）**结构性锁定**，2.1x 上限不可达；
HMR 路线实际兑现即 copy 组的 −15.8%，无残余。

## 4. 终局含义

5% 目标（16x）在本架构内：增量已收敛（最佳 1240824），结构杠杆 2.1x 不可达，
模型族参数化全关（S/r0/R/分段/函数形式）。缺口无覆盖路径——换模型族是新研究计划，
非本计划范围。本计划在此 closing 记录，后续只有维护性复核，不再开新线。
