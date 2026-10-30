# 研究约定

本仓库用于 Kaggle Google Quantum AI – Verifiable Quantum Circuit Compilation 比赛。优先推进算法、量子电路和资源成本研究。

- 不创建测试文件、测试目录、CI、提交钩子或自动门控。需要检查时手动执行命令，并记录实际结果。
- 官方验证器是评估研究结果的工具。只在明确需要验证候选方案时手动运行；不要在导入、打包或一般编辑时自动触发全量验证。
- 尽量保持脚本简单，避免为实验建立复杂框架或通用基础设施。
- 将实验假设、关键改动、资源成本及验证范围记入 `experiments/log.csv`。区分局部检查、完整官方本地验证和 Kaggle 排行榜成绩，不把未执行的验证写成通过。
- 按 `invsqrt`、`dqi`、`dfthcsos` 分别开展实验。候选电路、日志和大型中间产物放在 `artifacts/`，最终压缩包放在 `submissions/`。
- 官方原始数据保留在 `data/competition/`，不要修改其中的验证器；实验性修改另存至实验目录并说明差异。
- 引用公开方法时记录来源、版本和生成方法，保留可复现电路的生成代码。
- 凭据、Kaggle token、下载签名链接及大体积数据不得进入 Git。
- 不自动提交 Kaggle、发布数据、推送代码或创建远程仓库。

## 环境

使用 Python 3.12 与 `uv`。依赖由 `pyproject.toml` 和 `uv.lock` 管理；环境初始化使用 `uv sync`。
macOS 使用 PyPI 的原生 `kickmix`，不要导入比赛数据包内为 Kaggle Linux 镜像编译的 `kickmix.so`。
