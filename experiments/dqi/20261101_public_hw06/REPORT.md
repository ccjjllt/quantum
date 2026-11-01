# DQI：采用 Hedge Wizardry HW-06

日期：2026-11-01（北京时间）。按用户明确指令，作为公开组合的一部分提交一次，未修改电路。

## 来源与身份

- 来源：[Hedge Wizardry notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook)，版本 5，公开输出 `submission.zip`。
- DQI 为 HW-06：在 yoyobar 的 892Q 电路上，将 12 处借用线三输入 AND 的反计算替换为测量清零及条件 CCZ 相位修正。上游为 SomeJoint 的 flag-carry 解码器。本次直接复用二进制，没有重新运行生成器。
- 成员 SHA-256：`c253111974fcd36937d3fa6eb480a573e4d2455d3f50054befcbe4675b4a9234`。
- ZIP：`submissions/20261101_public_hw06/submission.zip`；SHA-256 `43c0f1e42acec0ddd02191c037ceb00f94ce4deb4a8cadb64a9fedb39cfda673`。

## 验证与成本

作者在 Kaggle 上使用未修改的官方 verifier、kickmix fork 0.3.1 / Python 3.13，默认空 salt，完整 102,400 shots PASS：0 value errors、0 phase errors；892Q，平均 Toffoli 403587.38180664065，R=1.1912604648115832，单项成本 **382537501561.75616**。这是该次抽样结果，不是无失败的普遍保证，也不是我们的本机验证结果。

本机只手动核对 ZIP CRC、18 个成员集及全部 SHA-256；没有运行电路模拟或官方 verifier。不能将新旧记录间的成本差全归因于电路优化，因为 DQI 抽样不同。

## 线上提交

北京时间 2026-11-01 23:41:09，组合提交编号 **57876561**；平台已接受，评分尚未返回。本次只提交一次。作者三项本地 GM **23.837909266369813** 与线上成绩分开记录。

证据在 `artifacts/20261101_public_hw06/`，包含源 notebook、作者完整验证 `check.json`、`receipt.json`、本机 `package_check.json` / `upload_check.json`，以及 `submission_request.json` / `kaggle_submission.json`。未保存下载签名链接或上传凭据。

下一步：记录本次线上最终结果；后续研究需另行恢复 SomeJoint 源码及 yoyobar/HW-06 增量，比较预先选定的相同输入抽样。
