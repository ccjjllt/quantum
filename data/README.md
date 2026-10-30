# 本地数据

`competition/` 保存通过 Kaggle MCP 获取的官方比赛数据，包括完整参考提交、验证器、FeMoCo 输入和论文。数据不纳入 Git；文件来源及 SHA-256 记录在 `references/competition-manifest.json`。

比赛来源：https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/data

重新获取时，使用已参赛账号通过 Kaggle MCP 下载比赛完整数据包，并解压至本目录下的 `competition/`。目录内应直接包含 `verifiers/`、`sample_submission/`、`kickmix/` 等内容。

本地 Python 环境使用 PyPI 的 macOS 原生 `kickmix`；包内的 `kickmix/kickmix.so` 保留为官方原始文件，不添加到本地 Python 搜索路径。

化学任务的独立 Starter Kit 暂不下载；需要训练分解时再引入：
https://www.kaggle.com/datasets/sohier/verifiable-circuit-compilation-starter-kit
