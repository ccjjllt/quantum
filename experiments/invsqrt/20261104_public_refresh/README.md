# 62Q invsqrt 研究价值与公开前沿复核

> 本文是固定公开输入及其当时比较结果的历史记录；当前候选与成本见[invsqrt入口](../README.md)。

本次通过 Kaggle MCP 读取比赛信息、排行榜、公开 notebook/source/output、讨论帖与自己的提交状态。
没有提交 Kaggle、发布或运行远程 notebook，没有修改现有候选和官方验证器。
公开源、版本快照及验证产物在 `artifacts/20261104_public_refresh/`。

## 本地现状

检查 HEAD `9567664`。Stage1 `80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3`
仍是既有本地最佳：62Q，两次完整官方 PASS，成本 100494.89112607106 / 100494.89685789104。
累计比旧公开 bce 精确省 1.1874961853 C。shortcache `97e639…` 是已证明的0C诊断电路。
最新代码已经补入真实缓存、29个测量源和g*u：固定g的256表达残差秩25，8g×32u最小23–25；没有新正收益电路。
这些是限定模板的负结果，不能当62Q的全局下界；继续同分布随机扩u的价值很低。

只读补查已保存矩阵：线性空间残差秩25；加入全部ab·wire/abc·wire后仍25；
完整1954个NEG/Z/CZ列空间秩1770，29源联合残差秩23。仅补免费列也未显示高把握机会。

## 新公开方案及实际复核

| 公开来源 | 固定版本 | invsqrt成本 | 说明 |
|---|---|---:|---|
| Syed Asad Ali / VQCC 24.43 Portfolio | v3 / 365359337 | 作者约98409.91 | deferred fan-in、测量清理、7处3→2窗口 |
| SomeJoint / Split Carries | v31 / 365412815 | 作者98309.13430978914 | 归一化标志退休、4处按相位位切换carry实现 |
| Kirill Tymchishin / Four Loaders, Eight Toffolis | v5 / 365421181 | 作者98309.06190122575 | 公开七线恒等式与前述改写的可读组合 |

来源：
- https://www.kaggle.com/code/syed3000/vqcc-24-43-portfolio?scriptVersionId=365359337
- https://www.kaggle.com/code/somejoint/quantum-circuits-24-50-local-gm-split-carries?scriptVersionId=365412815
- https://www.kaggle.com/code/kirilltym/quantum-circuits-four-loaders-eight-toffolis?scriptVersionId=365421181

已保存上述三个notebook源码；没有执行外部Python代码。
下载Kirill公开的factored_inverse.kmx，使用本机kickmix转换为KMB，所得SHA精确匹配其公开报告：
`ed77292a0e4a267e62235055cc2ab7faaa30b15d8a150bab79f34e5c1b8f172b`。
62Q、48088条操作；41个一般旋转角与本地Stage1逐项同序。
各21760输入×101/202/303三seed的native比较没有恢复/scratch/相位差。

手动运行未修改官方验证器，seed20261031、max_workers4、200540928 shots：PASS，
成本 **98309.13505417833**。相对同seed Stage1下降约 **2.175%**，观测约 **35.254 C**。
误差比仍0.9993237694056958、最坏x161、rotation_eps不变。
这是本地一个seed的完整复核，不是新的排行榜成绩；没有重复运行全部三任务。
原始日志 `kirill_verify_seed20261031.log` 与比较 `local_comparison.json` 保存命令、环境和哈希。

## 已确认的迁移机会与限制

旧joint原窗口[27775,28783)在新公开电路[27745,28753)逐项相同。
因此本地无回退选择器的迁移值得优先验证，但还需证明新前缀契约、生成实际候选并复核成本。
新公开电路已使用本地补丁的经典位b42002；迁移应分配未占用的位名，不能直接粘贴原补丁。
旧tail缓存窗口没有完整匹配，新公开方案已经重写归一化恢复；不得直接叠加0.1875C。
本次没有生成迁移后的优化候选，文本匹配不代表已取得额外收益。详见 `local_patch_match.json`。

## 比赛和讨论

MCP确认提交57876561为COMPLETE，真实Public Score **23.83790**；查询时账号排名863/2196。
排行榜第一 **28.82853**，但其全部实现是否公开不能由榜分推断。
SomeJoint公开组合summary的本地GM **24.5042915**，不同于其队伍排行榜成绩。
规则为三个任务reference/cost比的几何平均。比赛metadata截止2027-01-20 23:59 UTC。

已实际阅读：
- https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/755495
  11月3日公开前沿汇总：近期收益来自测量清理、乘积复用、精确窗口重综合与化学结构更新。
- https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/755303
  提醒区分一个实现失败和整个方向失败，建议以不同结构路线组织探索；属于讨论建议。
- https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/753185
  旧负结果帖曾否决63→62，后续评论给出了真实62Q结果，是限定结论不能升级为全局不可能的实例。
- https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/discussion/755488
  关于公开编译电路作为生成器输入是否满足生成要求的询问，读取时没有官方答复。

## 建议

继续62Q invsqrt有实证收益空间，但先吸收约98309成本的公开版本，再验证自己的选择器迁移。
优先复现与学习dirty-wire三乘积到两乘积、归一化标志退休、按经典相位位选择carry实现。
当前3C选择器窗即使全部免费，总榜GM也最多增加约0.0618%；连5C整窗都消去也约0.103%。
用新公开invsqrt替换Stage1、其他任务不变，预计GM增加约0.736%；这是静态公式估算而非新LB。
旧ab/abc随机模板应封存为有界负结果，其他结构实验先证明足够的收益上界再投入全量验证。
