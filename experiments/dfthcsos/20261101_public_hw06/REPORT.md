# dfthcsos：采用公开 C40 混合加载器组合

日期：2026-11-01（北京时间）。按用户明确指令，作为 Hedge Wizardry v5 公开组合的一部分提交一次；没有重新拟合权重或改写加载器。

## 来源与身份

- 来源：[Hedge Wizardry notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook)，版本 5。
- 分解/角度字基于 Lera 的 R=9、B=143、C=40 公开方案；权重采用 Heliosli v36，加载器 0 和 14 来自 Dmitrii v44，其余来自 Lera。完整逐文件来源和哈希见作者 `check.json` 的 `chemistry_assembly`。
- NPZ SHA-256：`2d471d92bf2c2a69a0165c4f09b1890e02abfe4ecaa3f8e4b6f5045777eb1f79`。
- 官方化学 submission hash：`4efe4b1d34bbb749fda0232de078e1297b5fc09bc90eb15425f84fee349ab532`，与作者自定义 family hash 是不同口径。
- ZIP：`submissions/20261101_public_hw06/submission.zip`；SHA-256 `43c0f1e42acec0ddd02191c037ceb00f94ce4deb4a8cadb64a9fedb39cfda673`。本次原样采用公开 ZIP，没有自行混搭。

## 验证与成本

作者在 Kaggle 上使用未修改的官方 verifier、kickmix fork 0.3.1 / Python 3.13，默认空 salt，完整 **87,232 shots PASS**。lambda_eff=47.040080661235564，T_total=16233，Q_total=428，8-bit 角度、J=5、15 个加载器，单项成本 **326821497.3720022**。

本机只手动核对 ZIP CRC、18 个成员集和全部文件哈希（包括 NPZ 与 15 个加载器）；没有运行本机化学验证。这一新组合不能沿用旧 C60 组合的本机 PASS。

## 线上提交

北京时间 2026-11-01 23:41:09，组合提交编号 **57876561**；平台已接受，评分尚未返回。作者三项本地 GM **23.837909266369813** 与线上成绩分开记录。

证据在 `artifacts/20261101_public_hw06/`：源 notebook、`check.json`、`receipt.json`、本机 `package_check.json` / `upload_check.json`、提交请求与平台返回记录。原官方数据和验证器未修改；没有保存签名链接或上传凭据。

下一步：记录本次线上最终结果；若开展 C40 自研实验，应以其真实加载角度字和新成本分解为起点。
