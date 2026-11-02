# Track B 离散优化线：invsqrt 新基线四实验记录

日期 2026-11-02。分支 `invsqrt-generator-rebuild`。基线
`artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb`
（SHA-256=`bce2948f…`，62Q，47258 ops）。本轮不提交 Kaggle、不改官方
verifier、未运行官方 200M-shot 验证；所有成本对比均为 verifier 单位
（C = executed Toffoli-like + T/4，score = Q·C；CX/X/CZ/NEG Clifford-free；
无条件 CCX = 1 C）。阈值线（README 权威）：62Q/81.10、63Q/105.56、64Q/129.26 C。
基线已含 temporary-AND、HMR 清理、Ahmed 缓存、Ehan 合并（R1–R6 六处 CCX 节省），
本轮任何实验均不重复计入这些收益；R1–R6 区候选一律先排除再计分。

> 否决范围声明：下表每个 verdict 只针对所测链 / 实例集 / 窗口规则，
> 不是全局否定。未测的窗口、未测的链、未测的算术结构仍 open，见 §下一步。

## 实验总表

| # | 脚本 / 产物 | 方法与范围 | verdict（ scoped ） |
|---|---|---|---|
| 1 | `cone_scan62.py` → `cone_scan62.json` | CCX 中心 2 积对合并（恒等式 `t^a&b^a&c=t^a&(b^c)`，真值表 4 变量 16 行 EQUIVALENT）+ 3–4 积 fanout；全电路 1153 CCX，同目标对 gap≤200 值级匹配；7 重窗口屏（共享值、条件环境、合并点线可用、非退化、目标未触、无测量、无目标相位）+ 改写后全电路重解释 62/62 线 + 条件环境一致 | `pair_candidates=0`、`fanout=0`、`reinterpret_verified=0`。排除主因 `value_no_shared=2208`；其余 `no_wires_at_merge=203`、`window_target_touched=180`、`cond_env_differ=1`。小锥（2–4 AND）仅 3 个且全在头部 `unknown` 区（op27–29），B/inverse 区无。结论：该窗口规则下无可合并对——不否定更大 gap、跨目标、非 CCX 中心改写 |
| 2 | `retain_chain62.py` → `retain_chain62.json` | 保留 vs 重算：链 src=[25562,25576]（B 尾）→copy=[28787,28801]（inverse_B 头），15-op 精确文本重复，3 个 flanked temporary-AND（前沿 [21,28,40]，切片各 3 ops/1 CCX、零重叠）；span 3210 ops、48 HMR/R 屏障；零线借用检查；相干保留（+Q、Bennett 反算）与测量保留（62Q、HMR+经典+Clifford 修正 TO-PROVE）分别计分；全 sig-equal+zero 池上界 11 C / 9 parts | 最大毛收益 −3 C（62Q 测量版，修正覆盖 TO-PROVE 未证）；相干选项净正数千（+1559.07/+3116.15）；无借用零线；任一选项距阈值线两个量级。结论：该链否决——不否定其他链（见实验 4）与非 TO-PROVE 的确定性修正 |
| 3 | `joint_phase62.py` → `joint_phase62.json` | 联合测量-相位修正 + 小窗口算术首探：(a) 全电路条件 op census，非 Clifford 修正仅 20 个条件 Z_POW（b414×15 分 3 块 + b308×5，T 类 12 个），实例输入值 id 两两不同；(b) CSWAP census（201 个，top q27×44/q18×39），同选择邻接对 gap≤40 共 705、同值 0、可消 0；假设行合并 extras 表逐项计分 | `joint_cleanup=INAPPLICABLE`（实例作用于不同数据）；条件 T 池期望全电路仅 ~1.5 C；CSWAP 零可消；行合并 extras（空间 +3Q≈+4866、进位 13 CCX 零共享、逐实例 T 不可上提）超任何节省。结论：该实例集无联合清理——不否定其他条件位组与非查表行合并 |
| 4 | `retain_chain2_62.py` → `retain_chain2_62.json` | 换链重跑保留分析（本轮“做深一个”，选(a)）：全电路精确重复扫描（长≥10、间隔≥500）取复制代价最大链 src=[25599,25644]（B 尾）→copy=[28838,28883]（inverse_B 头），46 ops 精确文本重复、copy 13 CCX（实验 2 的 3 CCX 的 4 倍多）；不断言语义，先机检值（CCX 值签名、零前置、寿命）与相位/测量（copy 内 HMR、条件相位、条件栈平衡、条件环境），booleq62 值证明探针（48 自由变量→deferred=未证→不改写），再比幻想上界成本；显式断言与 R6（止于 25534）无交叠 | 三重锁否决该链：值 FAIL（首个 CCX 签名即分叉，控制 13619/12846 vs 18173/18146；q40/q57 拷贝前非零；3 条寿命全失败）；相位/测量 FAIL（copy 内 2×HMR→b341、3×条件 CZ、首条裸 POP_CONDITION 致栈 −1、条件环境 b457 vs b458）；成本 FAIL（幻想删 13 CCX 零清理仅 −806 分，62Q 5% 线需 −5028.43 分，差 6.2×；逐切片毛收益仅 1 CCX vs +1Q≈+1622 分）。零改写、零收益申报 |

## 成本对比总表（dscore 相对 62Q 基线 100568.4992，负=省）

| 选项 | dC | Q | dscore | 证明状态 |
|---|---|---|---|---|
| Exp2 retain=1 相干 | −1.0 | 63 | +1559.07 | boolean-exact，但净正否决 |
| Exp2 retain=1 测量 | −1.0 | 62 | −62.00 | TO-PROVE（修正覆盖未证） |
| Exp2 retain=2 相干 | −2.0 | 64 | +3116.15 | boolean-exact，但净正否决 |
| Exp2 retain=3 测量 | −3.0 | 62 | −186.00 | TO-PROVE，毛收益上限 |
| Exp4 fantasy-删13 | −13.0 | 62 | −806.00 | INAPPLICABLE（值/相位先失败，仅上界） |
| Exp4 retain=1 相干/切片 | −1.0 | 63 | +1559.07 | INAPPLICABLE（同上，仅量级示意） |
| 62Q 5% 线要求 | −81.10 | 62 | ≤−5028.43 | 权威阈值 |
| sig-equal+zero 全池上界（Exp2） | ≤−11 | 62 | ≤−682 | 清理前毛上界，仍差 7.4× |

## 方法纪律（四实验通用）

- 先证值与相位一致再比成本：实验 1（恒等式真值表 + 逐候选 62/62 重解释）、实验 2（签名/零前置/寿命屏 + 修正覆盖标 TO-PROVE 不冒充）、实验 3（实例输入两两不同即判 INAPPLICABLE）、实验 4（签名分叉 + HMR/条件相位/栈失衡即停，只报幻想上界）。
- 只许确定性修正覆盖全部测量结果：凡涉测量分支的节省（Exp2/4 测量版、Exp3 联合清理）一律标 TO-PROVE 或 INAPPLICABLE，不申报。
- 基线已有不重复计分：R1–R6（Ehan/Ahmed/temporary-AND/HMR）收益不计；实验 4 显式断言链与 R6 无交叠（25599 > 25534）。

## 复现（2026-11-02 实测全 PASS，exit 0）

```
uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/cone_scan62.py
# pair-merge identity equivalent(4 vars/16)；pair exclusion value_no_shared=2208…；candidates 0；small cones 3 all unknown
uv run python experiments/invsqrt/20261102_hw06_opt/retain_chain62.py
# chain 15 ops exact repeat；copy 3 CCX；pool bound 9 parts ≤11 C；coherent +1559.07/+3116.15
uv run python experiments/invsqrt/20261102_hw06_opt/joint_phase62.py
# cond Z_POW b414×15+b308×5；inputs pairwise distinct；same-select pairs 705 identical 0 cancellable 0
uv run python experiments/invsqrt/20261102_hw06_opt/retain_chain2_62.py
# chain 46 ops exact repeat；copy 13 CCX；sig diff @25605/28844；fantasy −806 vs −5028.43 (6.2x short)
```

产物（`experiments/invsqrt/20261102_hw06_opt/`）：`cone_scan62.json`、
`retain_chain62.json`、`joint_phase62.json`、`retain_chain2_62.json`。
注意 `cone_scan62.py` 工作区有未提交修改（GAP_LIMIT 500→200 + 排除计数），
JSON 与新脚本对应——沿用工作区版本，不要回退。
官方验证：0 shots（未运行）。Kaggle 提交：无。

## 下一步（仍按“确定性修正覆盖全部测量结果”纪律）

1. 小窗口算术首实验（任务选项 b，未做）：合并相邻 2–3 个 signed-digit 行或共享相邻查表地址展开/清理（参考 arXiv:1905.07682v1），逐项计入查表/进位/空间成本；需先过 Track A 的 LUT_c/M 值级解码，否则值证明无从谈起。
2. B 区改写组 R1–R5 附近 ancilla 中转链：本轮全电路扫描显示除实验 4 外的最大精确重复仅 4-CCX 级（含 HMR/条件 CZ），可按实验 4 模板逐条机检，但预期同样受“窗内测量 + 签名分叉”锁死，优先级低于 1。
3. inverse_A/unlookup 大跨度链：扫描中间隔≥500 的精确重复多为 B↔inverse_A 镜像对（4-CCX、窗内 HMR），同上模板可批量否决；若发现无 HMR 纯布尔长链则升级为保留候选。
4. 语义落地后（coarse 控制字显式函数、LUT_c/M 解码）再回看实验 1 的 `value_no_shared=2208` 主因：算术级恒等（如 Horner 递推移位）可能把“异值”对重新解释为同一切片的不同阶段，届时重开窗口规则才有意义；此前不再放宽 gap。
