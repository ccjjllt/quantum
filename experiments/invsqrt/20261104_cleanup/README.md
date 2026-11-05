# 2026-11-04 研究清理记录

按用户要求，将提交回执移到 `submissions/`，从 invsqrt 研究目录删除无新增竞争收益的
已收官实验与缓存，保留有效改写、当前复现依赖及仍开放的联合研究方向。
本次清理以 62Q、SHA `aac6ce…61c3`、完整官方本地成本约98123.14为当前比较基准。

## 移动与删除范围

- `experiments/submissions/20261104_heliosli_v5/README.md` 原文移至
  `submissions/20261104_heliosli_v5/README.md`，与已提交的原始 `submission.zip` 放在一起。
  回执与ZIP内容哈希保持一致；README可进入Git，ZIP继续忽略。
- 删除124个研究源码/笔记/小型结果文件、32个缓存文件和1个过时的空目录占位文件。
  删除前共1,967,100 bytes。逐文件路径、大小、SHA-256、原因及Git状态见
  [deleted_files.json](deleted_files.json)。
- 候选KMB、官方日志、公开原始输入和提交ZIP保留在原有 `artifacts/`、`data/`、
  `submissions/` 路径，保证有效研究可复现；本次不是大型产物清理。

## 删除实验的结论

| 原目录或文件组 | 已核实结论与删除原因 | 证据位置/范围 |
|---|---|---|
| `20261030_public_audit` | 旧62Q版本恢复段约526.54 Toffoli-like、占39.5%；41角误差余量紧。只有审计，没有新候选。数字仅适用于旧版本。 | `artifacts/20261030_public_audit/invsqrt/` |
| `20261031_invsqrt62_replay` | 复现公开历史缓存和哈希链；新retention无收益，A/B/Lphase仍是replay。LB=18被x=128反例否决，物理线不连续。公开已吸收的历史1门收益不重复计账。 | `artifacts/20261031_invsqrt62_replay/`；原Git记录 |
| `20261102_generator_v2` | 独立生成器**曾完整官方PASS并有架构内部改善**：160Q/1847344.58降到132Q/1240824.53，但仍约为当前基线12.65倍；该架构已收官，无当前竞争优势。不能记为从未生成成功。 | `artifacts/20261102_generator_v2/`；原`joint_decode.md`、`hmr_full_veto.md` |
| `20261102_hw06_opt` | R1–R6/+57、输入往返和坐标诊断完成；拟合误差比0.58/0.61只有数值候选与假设计费，离散路线无真实降本。旧基线已含6 CCX收益。 | `artifacts/20261102_hw06_opt/`；本组旧工具无活跃导入者 |
| `20261102_baseline_patch` | 4窗、12片段筛查，0/8新候选；UNKNOWN/超时不等于全局不可能。 | 原`round1_closing.md`和对应artifacts |
| `20261103_baseline_patch_round2` | W1/W2的16模板无收益，额外恢复/修正抵消节省；仅限定模板负结果。 | 原`templates.md`和对应artifacts |
| `20261103_one_ccx`的4个无收益探针 | 删除`approx_window.py`、`idle_cache_probe.py`、`search_window.py`、`phase_quadratic_probe.py`；未形成有效新候选。真实尾缓存和相位选择器的生成/证明模块保留。 | 同轮有效收益及证据仍在保留README |
| `20261104_stage1_nofallback/STAGE2.md` | 副线缓存/共享模板未产生第二阶段收益；后续复核已修正旧“严格零上界”等表述。Stage1的0.125C有效增量保留。 | `artifacts/20261104_stage1_nofallback/` |
| `20261104_public62_optimization`的4个A/B脚本 | A限定模板没有候选；B仅查已有HMR前固定64门，覆盖不足；A计费与匹配亦有缺陷。删除旧scout/diag/record脚本，保留有效迁移、审计、样本及模板来源。 | 对应`routeA_scout.json`、`routeB_survey.json`；后续reaudit |
| `20261105_shortcache` | 真实短缓存诊断电路为0C；正确缓存快照、29真实测量源、g*u模板下残差秩23–25，有限分支预算没有正收益；不能外推为全局无解。 | `artifacts/20261105_shortcache/invsqrt/`及原`SECTION4_VERDICT.md` |
| `20261105_crosshmr_synth` | 0 PROVEN/28，全部在剪枝退出。原剪枝及命中产物路径有缺陷；独立ANF证实28段秩2，仅否定独立段压缩。不能否定HMR两侧联合改写。 | `artifacts/20261105_crosshmr_synth/invsqrt/review_*.json`及独立复算脚本 |

研究教训保留：输入坐标必须包含bit20并支持非连续线；数值拟合、静态门数下降不等于
实际执行成本下降；整数负数舍入、HMR相位修正和清理成本必须一起核算；一类模板的
失败不能否定整个算法方向。28窗应为20个纯CCX窗与8个含CSWAP窗；守卫取活动分支后，
独立段的非线性秩仍为2。已有两处正收益在HMR前后通过copy补偿，原独立段模型不覆盖它们。

## 保留的研究

- `20261103_one_ccx`：真实尾部AND缓存、有限域相位压缩、自适应联合选择器，以及
  对应生成/审计/成本/样本模块。`affine_probe.py`为样本输入依赖，`audit_phase_cache.py`
  同时供当前迁移审计使用，不能随旧探针删除。
- `20261104_stage1_nofallback`：三分支无回退的有效历史改写和独立证明；删除无收益副线笔记。
- `20261104_public_refresh`：公开输入的固定版本、来源、哈希和本地验证记录。
- `20261104_public62_optimization`：当前公开基线迁移生成器、独立审计、样本比较；
  `routeA_templates.json`和`extract_templates.py`保留给来源复现与新窗口普查。
- `20261104_reaudit`：当前最佳62Q电路的跨HMR生成、对最新公开的证明、研究记录及
  28个未完成两侧联合综合的候选窗口普查。

后续开放方向是保持测量输入函数和最终相位/输出一致的跨HMR联合改写，先处理24个
无条件窗口，再处理4个固定外层守卫窗口。这28窗尚无额外已证收益，不使用已删除的
错误独立段综合器作为基线。

## 可追溯与恢复

清理前Git HEAD为 `80d4aadca7ba3fee5995f9a75957ef7900d7d9bf`。已跟踪的删除文件可从该提交
读取原文；3个未提交的crosshmr_synth源码/记录另存于
`artifacts/20261104_cleanup/removed_untracked_sources.tar.gz`，哈希在删除清单中。
这是可回溯副本，不作为活跃研究。旧审计产物中的脚本路径属于历史执行记录，允许指向已删除文件。

## 清理后验证：PASS

实际结果记录在 `artifacts/20261104_cleanup/verification.json`：

- 临时目录重生成迁移候选与当前最佳候选，SHA分别仍为`5541151c…`、`aac6ce…`。
- 迁移独立审计PASS（65项前缀条件，精确收益`262143/262144 C`）；对公开版本的5组miter通过。
- 开放研究的28窗逐项不变；保留的Python/JSON实现文件字节未改。
- 研究侧导入、58处可静态解析的运行输入路径、15处本地README链接检查通过。
- 提交README原文移动，ZIP、候选、官方日志与官方验证器哈希不变；README可进入Git而ZIP仍被忽略。
- 缓存清零；未提交源码副本的3个成员与删除前哈希一致。未运行新的完整官方评分。

最初验证命令曾误加`audit_migrated.py`不支持的`--prove`参数，被参数解析拒绝；
核对实际CLI后移除该参数重跑，上述PASS均来自修正后的真实执行。
