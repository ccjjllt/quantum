# DQI 公开实现与生成链重新核查

访问日期：2026-11-06（北京时间）。范围：当前 Syed 基线、主要公开组合、SomeJoint 源码链、ahoirg 重建包及 Gu 等人的 `uncompute`。仅联网只读、下载小型源码和静态解析；没有导入/执行下载代码、构建候选或运行官方验证。证据位于本工作区 `artifacts/20261106_high_return_research/public/`。

## 关键修正

此前“公开实现没有可用生成器”的表述范围过宽。**当前 Syed V9 的精确生成器仍未找到，但同源 Schur 解码器的旧版、带明确构建入口的源码包已实际下载。** 因而下一步可以研究真实生成器中的算术、测量纠相和生命周期，而不必从 58M 行电路完全逆向。

此前 `20261106_closed` 的“SomeJoint q26 仅有三个 Python 文件”不成立。本轮指定 `pageSize=100` 重新读取完整列表，得到 **25 个 Python 文件，177,453 bytes**。元数据进一步把构建源码指向 `somejoint/qcc-dqi-898`，后者 V1 有 **42 个小型 Python/JSON 文件，804,491 bytes**。列表本身并不证明完整依赖闭包。

25 个 q26 原文件已全部保存到 `public/somejoint_q26/`，名称、大小、SHA 与逐文件 import 清单见 `somejoint_q26_source_audit.json`。它们还引用例如 `homogeneous_pivot`、`homogeneous_update`、`pivot_bridge`、`pivot_rotate` 和 `exp.decoder.common` 等外部层，不能当成独立构建包。`qcc-dqi-898` 本轮只取 metadata 和列表；完整构建链取证以另行下载的248条 ahoirg 包为准。

旧合并候选 `b99bf23306f6` 已在 **manwithacat 的 HW-22（2026-11-05，notebook V24；当前 V26 仍保留条目）**公开，其默认官方成本同为 375,320,367,805.64。它是 fd0ef unsynthesis 与 Leo/Alex 版本其余阶段的合并；作者报告 48 个固定抽样的预期成本改善。我们此前 −42 相对 fd0ef 的结果应描述为复现/独立重现已有公开组合，不能主张首次原创。HW-22 相对 Leo 少 14 门与相对 fd0ef 少 42 门使用了不同起点，不矛盾。本轮未对本机大电路重新做全 SHA 比较；此归属识别基于已有产物标识与完全相同的公开成本。[HW notebook V26](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook/version/26)

## 当前公开比较基线

| 来源和本轮固定版本 | 读到的 DQI 状态 | 源码可用性与判断 |
|---|---|---|
| Syed notebook V9 / dataset V9 | 892Q，约395.4k mean Toffolis；V8/V9 的 DQI 沿用 V7 CH3 | notebook 仅方法说明和打包，dataset 18 个编译产物，无生成器；本轮确认仍为 V9 |
| Heliosli notebook V11 | 明确 byte-for-byte 采用 Syed V7 DQI | 新版总分变化主要不能推断为新 DQI 方法 |
| SomeJoint notebook V36 | 891Q，396,918.5 mean Toffolis，约3.75373e11；采用 yoyobar 对 Syed 旧线的改写 | 当前 notebook 是组合与打包，旧源要追踪独立 dataset |
| manwithacat HW V26 | 保留 HW-22 `b99bf23306f6`；自述按48抽样预期成本排序 | 公开提供电路/说明；48抽样 engine 未公开，数字是作者证据 |
| ahoirg notebook V2 | 使用旧 Syed 891Q 电路；正文明确本版不重建该 decoder | 同一资产集保留 release-1 的893Q源码重建包，不能只看最新 notebook 标题 |

链接：[Syed V9](https://www.kaggle.com/datasets/syed3000/vqcc-own-circuit-portfolio/versions/9)、[Heliosli](https://www.kaggle.com/code/heliosli/the-dataset-is-public-now-enjoy)、[SomeJoint](https://www.kaggle.com/code/somejoint/quantum-circuits-24-65-local-gm-chem-refit)、[ahoirg](https://www.kaggle.com/code/ahoirg/qcc-reproducible-circuit-portfolio)。原始 MCP metadata/source 快照已保存。此次还查了 competition+DQi 按 DateRun 的前30条及 isabe11am00re V11 源码；没有由这些读取得到可确认优于 Syed 的独立新 DQI 实现。该结论限定此次读取范围，不能称完整排行榜审计。

## 真正已取回的 Schur 生成器

固定来源：[ahoirg/qcc-reproducible-circuit-assets dataset V2](https://www.kaggle.com/datasets/ahoirg/qcc-reproducible-circuit-assets/versions/2)，目录 `qcc-reproducible-circuit-assets-v2/` 内保留的 release-1 文件。

- `dqi-source-bundle.json`：1,462,938 bytes，SHA-256 `a7f22360aa7d1f5137b8cd2c6525e7eb05f826a031fcd751ce56f388aee5fafe`。
- `build_dqi.py`：5,835 bytes，SHA-256 `80c39449bff91743b43d63e46e39a6e39ca40b46e252b9fff2f52acc56cacd8a`。
- bundle 248 条：218 个上游源码、26 个输入、4 个 helper/credit 文件。所有条目的长度和 SHA 与包内清单一致，所有 Python 文本能被 AST 解析。这是静态完整性检查，不是执行成功。
- 生成入口：`blocks/dqi/pro-q18-900/source/decode_best.py` → `exp/new/root/decode_norm5log7.py`；`portable_builder/transform.py` 在构建时安装显式 P6、carry7..16 的转换。
- 上游：SomeJoint notebook V23 / run364288111 与 `qcc-dqi-900-undo` V1；carry 归属 yoyobar。目标名 `hybrid6-guard893`，声明生成 **893Q / 63,176,209 operations**，预期 native KMB SHA `fb2da4f299c4d41e421e5e57d07915599617291ab1c41d4e0fcefa6db1f2079c`。
- builder 显式分配 70×12 个量子 syndrome 和 4095×12 个经典 mask，登记 `S0...S69`、`E0...E4094`。这与比赛输入接口相容，而非固定 mask 的论文问题。**它不是 Syed V9，尚未本机运行重建，尚未证实当前 native kickmix 能给出预期字节，更未复跑官方全量验证。**
- `CREDITS.md`、`LICENSE-SomeJoint.txt`、`NOTICE.md`、`README.md`、资产清单原文同目录保存。资产集与 SomeJoint 当前发布均标 Apache-2.0；NOTICE 保留 jday96314 历史来源许可证未能确定的声明，不应删掉历史归属或重新声称全部历史源的许可已经查清。

静态依赖审计 `ahoirg_release1/static_dependency_audit.json` 发现四个无同名文件的 import：`lowclean_shared` 被入口前置模块通过 `sys.modules` 显式注入；`decode_partial` 所在文件在当前 owner 中以 AST 抽取函数，并不直接 import 文件；`gap_zero`、`descending_overlap` 位于历史函数内。是否每个动态分派都闭合仍须真正构建确认。缺少的若干 literal JSON 是输出路径、诊断 fixture 或动态文件名片段，不能一律认定构建缺件。源码大量使用 `sys.path` 修改、动态函数克隆和代码替换，静态 basename 命中不是运行时闭包证明。

再生成入口（记录，不代表已执行）：

```sh
python build_dqi.py --bundle dqi-source-bundle.json \
  --bundle-sha256 a7f22360aa7d1f5137b8cd2c6525e7eb05f826a031fcd751ce56f388aee5fafe \
  --work <new-artifact-directory>
```

原脚本末尾无条件读 `psutil.Process.cpu_affinity()`，macOS 通常没有该方法；本机重建应在实验副本里把这条**回执字段**改为可选并记录差异，不能修改共享环境或以此误判电路算法缺件。本轮未修改原脚本。

本轮手动运行 `.venv/bin/python experiments/dqi/20261106_high_return_research/audit_public_sources.py`：248条bundle哈希失配0、Python语法错误0；已下载且列入manifest的6个源码/许可文件长度与SHA全部吻合；q26的25个源码全部能解析且大小与Kaggle目录一致。此脚本只读取字节与AST，没有导入下载源码，也不启动任何验证器。

## 70 点 mask 投影已经有源码

bundle 内 `playbook/kit/decoder/exp/mask_projection/kernel.py` 明确 `SELECTED=tuple(range(70))`。它在 trace-dual basis 中插值次数≤70且 F(0)=0 的多项式，将 syndrome 的线性相位直接支付，再用 classical additive FFT 减去 mask 上的多项式值。选定70个扫描位置的残余 mask 恒零，扫描可跳过这70点；该变换本身不收 Toffoli。`exp/scan/scan.py` 提供 `skip_points`，每个剩余点的量子零测试需要11个Toffoli，因此 4025×11=44275 与现有基线相符。

这是**已存在的上游方法与源码**，不是待发现的新增 770 门收益。本轮源码解释仅证明旧生成器具备此能力；当前 Syed 二进制是否沿用相同映射，应由其实际静态结构另行确认。相关两个原文件已从bundle按原文单独保存到 `ahoirg_release1/selected_source/` 便于阅读。

## 前沿可重现库：uncompute

[andigu/uncompute](https://github.com/andigu/uncompute) 的当前 main 固定为 **`64b5a13aa249f1360846657392e6c66817b26d0f`**，GitHub commit 时间2026-10-16T02:06:21Z；许可证文件为 Apache-2.0。与论文页面日期的差异不作推断，直接固定源代码 revision。

递归 Git tree 实际含 `tasks/dqi-reed-solomon/circuits/discovered/circuit.py`（84,230 bytes）、`gen_constants.py`、`constants.json`、`search.c`、grader、reference、contract 和 results；这是生成程序及参数搜索链，不是只有预编译电路。树与revision存档在 `uncompute_tree.json`、`uncompute_revision.json`。本轮没有运行其生成器或下载15MB编译op流。其认证值442,397T/1,837Q及固定mask、TQ评估与比赛契约不同，不能直接用论文12倍改善代替对当前892Q基线的比较。适宜提取共享更新、反向分支恢复、测量纠相等方法，不能作为直接更优候选。

`jday96314/QuantumAI` 直接 GitHub 页面本轮仍返回404；这只说明该URL当前不可访问，并不能推出该谱系全部源码不可得。

## 对高收益研究主线的影响

1. **优先研究源码层的逆运算/表示/恢复联合优化。** 用已取回的 Schur 内核建立明确局部输入输出、零/非零前提和 phase契约，才可能比较宽算术、缓存、重算、phase-only恢复的 Pareto 点。无需先完整复原 Syed 58M 行文本。
2. **重建旧源是研究工具恢复，不是成本改善。** 必须把893Q旧结果与当前892Q基线区分，不能由于源码可得就切换到更差提交。可先用旧源解释目标核并把合法改写映射到新基线；最终收益要按实际Q²×meanT×R核算。
3. **公开变体组合只作有界筛查。** 当前 Syed 层已重排；HW-22已经公开。下一轮候选必须证明新旧内核的ABI和相位协议兼容，而非依赖文本区间不重叠。
4. **不要把既有mask投影、通用BM或最新组合总分当新增高收益。** 当前最值得投入的瓶颈是可验证内核与调度变体，而非继续重复旧局部模板搜索。
