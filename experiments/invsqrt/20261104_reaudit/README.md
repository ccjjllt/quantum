# 2026-11-04 复核与跨 HMR 合并

本记录基于 HEAD `80d4aad` 的实际 KMB。跨 HMR 组合候选已完成两次完整官方本地验证；
该研究候选没有提交 Kaggle。用户另行授权的原始公开组合提交单独记录。

## 旧轮不是整体零收益

`public62_nofallback.kmb` SHA
`5541151cdeea9bd0729c1e09715af3737c4d7d1c95da913b3b976485e766ff38`
相对 Kirill V5 精确省 `262143/262144 C`。重新读取实际电路运行独立审计，
65 项前缀条件全 UNSAT、3 分支值/相位、覆盖证明及计费再次 PASS。
新报告在 `artifacts/20261104_reaudit/migration/audit_migrated.json`。
原双 seed 官方日志确实存在并绑定相同 SHA，成本分别为
98247.13887582964 / 98247.10733802804；本次未重跑全量验证。

## 结构负结论的边界和实现缺口

- Route A 把 HMR 当绝对屏障，因此只能得出无测量窗口模板的限定负结果。
  本次增加 CCX 控制交换对称的拓扑普查，仍没有其无测量 3-CCX 骨架。
  但 `scout_routeA.py` 的 matcher 是贪心而非注释所称 backtracking；
  计费读取最终经典表、不跟踪 HMR 写入版本，并把活动条件右端写成了
  `const` 而非 `1 XOR const`。此前无候选，未污染已有迁移收益；后续不得复用此计费。
- Route B 从已有 HMR 向前固定截取 64 门，要求整段无屏障，而非枚举长度不超过 64
  的实际清理窗口；也未搜索原电路中没有 HMR 的 CCX 清理目标。
  其 10 个保留点支持线数为 26..39，不能作为穷尽 8 线模板的证据。
- 补充 427 个输入轨迹检查没有发现非平凡单 CCX 清零，不据此声称有遗漏收益。
  归一化尾部 19 个 CCZ 的 24537 输入二次相位空间筛查仅存活两个低触发样本模板；
  完整前缀 Z3 均 SAT 驳回（op49703 的 Z q32 模板 x=15；op49774 删除模板 x=1）。
  这些不是新候选，不继续扩同类搜索。

## 真正新增的 2C：公开跨测量恒等式的组合

来源为 [SomeJoint 的 Window Merges notebook](https://www.kaggle.com/code/somejoint/quantum-circuits-24-53-local-gm-window-merges)，
固定版本 V32，本地源码 SHA `01c42e4d403ffa5143a947d4c90402b351999d635f61c4b45c523b966d34b7cd`。
这是公开作者的方法复现与本地 nofallback 组合，不能计为原创恒等式。

在本地父电路找到两处 19 门窗口 `[21488,21507)`、`[25503,25522)`。
它们都位于 nofallback 替换窗口之前。令加法为 XOR：

`a*m + c*(m+u+a+v) = (a+c)*(m+c) + c + c*(u+v)`。

保持 a 在 HMR 前的原值以及既有 HMR/纠相序列，用重建后留在 a 上的
`c*(u+v)` 向目标复制，3 CCX 改为 2 CCX。两个窗口每 shot 都执行，因此精确省 2C。

生成器：`cross_hmr_merge.py`。它只从固定父 SHA 构造两个明确窗口；
完整保留 HMR 和 Z_POW 序列；不导入或运行外部 notebook Python。

真实候选：
`artifacts/20261104_reaudit/cross_hmr/public62_nofallback_cross_hmr.kmb`
SHA `aac6ce1048f55ec961329f44082d88f4afa11d013ca13f062f5cac23b4c861c3`，
62Q，49910 ops。相对父电路精确少 2C、少 124 成本。

- 每个窗口所有 10 根 dirty 线 × 2 个 HMR 结果，共 2048 个值/相位条件全部相同。
  删除最终 copy 的负控被拒绝。两处共 4096 个穷举条件。
- native kickmix：21760 输入 × seeds101/202/303，恢复、scratch、相位差与容差失败均为0；
  各 seed 恰好少 2.0 Toffoli/shot，T 和一般旋转数量相同，最坏 x161 / 误差比不变。
- `cross_hmr_proof.json` 和 `native_sample.json` 是局部证明与样本证据。
- 原始官方验证器、native kickmix 1.0.0、Python 3.12.13，手动运行两个完整 seed：
  - 20261031：PASS，200540928 shots，成本 **98123.13887582964**；
  - 20261101：PASS，200540928 shots，成本 **98123.10733802804**。
  两次同 seed 对父电路均精确减少 124 成本；62Q、41 个一般旋转、rotation_eps、
  最坏 x161 与误差比完全不变。实际日志及环境、命令、父/子 SHA 绑定记录在
  `artifacts/20261104_reaudit/cross_hmr/official_comparison.json`。
  这是完整官方本地验证，不是本候选的 Kaggle 榜分。

当前可用的本地研究基线为 `aac6ce…61c3` 跨 HMR + nofallback 组合。
本轮新增加的两处恒等式来自公开作者；我们的工作是独立复现、证明及与既有选择器组合。

## 与最新公开 inverse 的独立比较

Heliosli V5 / run365542459 的原始 ZIP 内 inverse 为
`15118bfa94a4084cd853c752100442ec41d8a80bae0f483af98a0cac2677e64c`，
即 SomeJoint 的两处跨 HMR 改写版。`compare_public.py` 读取该实际字节与本地候选：
先仅在内存把 nofallback 换回原选择器，再对剩余 5 组全部差异逐组证明。
任意量子输入、自由 HMR 结果下的输出、相位、经典结果 miter 全部 UNSAT，
每组无条件 CCX 数相同；窗口外指令一致。
两处跨 HMR 的具体 CX 写法不同，但语义和成本相同，不重复算作相对新公开的收益。

因此本地候选相对最新公开的独立优势为 `262143/262144 C`，
固定 62Q 下精确少 **61.99976348876953** 成本。
额外 21760 输入 × 3 seed 的 native 比较也全部通过。
证据：`comparison_to_latest_public.json`、`native_sample_vs_latest_public.json`。

手动复现生成与局部证明：

```sh
uv run python experiments/invsqrt/20261104_reaudit/cross_hmr_merge.py
```

后续最值得研究的是把 HMR 作为带符号相位的操作纳入小窗口综合，
并保持测量点的输入函数；这两处正收益直接说明“禁止跨 HMR”会漏掉实际可兑现的结构。
先验证和保留此次 2C，再对同一新语义作有界普查，不能把公开已找到的两处重复计为未来收益。

## 下一轮的有界候选集合（尚无新收益）

`census_cross_hmr.py` 已对最终 `aac6ce…` 做一次有限普查：1503 个连续三付费门跨度中，
38 个满足恰有一次 HMR、最多 10 线、无旋转与条件栈切换。排除已吸收区域后剩 33 个，
共有 14 种付费门/HMR 拓扑，均不匹配刚使用过的原始三门模板。
选择 28 个互不重叠窗口，其中 24 个付费门完全无条件，4 个有固定外层守卫。
每窗的实际指令和条件栈存于 `remaining_cross_hmr_census.json`。

下一轮优先研究 24 个无条件窗口，以“全部输出＋全部 HMR 相位系数相同，3付费门降至2”
为目标；再处理4个带守卫窗口。每窗最多60秒综合＋60秒独立等价检查，UNKNOWN保留未证，
不临时扩展支持集或随机种子。只有实际生成且证明严格正收益的窗口才进入组合。
若28窗都成功，模板集合的静态收益上界是28C（1736成本），守卫仅以概率≤1计；
这是极乐观的有限研究上界，**并非预期收益，也不是全电路下界/上界**。
本次该普查没有生成额外候选、没有获得新的已证收益；当前已兑现增量仍为前述2C。
