# invsqrt：采用 Hedge Wizardry v5 公开组合

日期：2026-11-01（北京时间）。本次按用户明确指令提交一次公开组合，不涉及自研电路优化。

## 来源与身份

- 来源：[Hedge Wizardry notebook](https://www.kaggle.com/code/manwithacat/vqcc-hedge-wizardry-notebook)，版本 5。下载其原始 `submission.zip`，未重打包或修改成员。
- invsqrt 为 Ehan Mallick 在 yoyobar 62Q 电路上的两次 3→2 AND 合并版本；本次没有重建其独立生成器。
- 成员 SHA-256：`bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47`。
- ZIP：`submissions/20261101_public_hw06/submission.zip`，30,970,103 bytes；SHA-256 `43c0f1e42acec0ddd02191c037ceb00f94ce4deb4a8cadb64a9fedb39cfda673`。

## 验证与成本

作者在 Kaggle 上使用未修改的官方 verifier、kickmix fork 0.3.1 / Python 3.13，默认空 salt，完整 200,540,928 shots PASS。62Q，平均 Toffoli 1325.481775804887，41 次一般旋转，等价门成本 1622.0725676541888，单项成本 **100568.4991945597**。

本机仅手动核对 ZIP CRC、18 个成员集及全部 SHA-256；没有运行本地电路模拟或官方 verifier。不能把作者运行写成本机 PASS。原官方数据及验证器未改。

## 线上提交

北京时间 2026-11-01 23:41:09，提交编号 **57876561**；平台已接受，评分尚未返回。本次只调用一次提交接口。作者三项本地 GM **23.837909266369813** 与线上成绩分开记录。

证据位于 `artifacts/20261101_public_hw06/`：`hedge_wizardry_v5.ipynb`、`notebook_metadata.json`、`session_log.json`、`check.json`、`receipt.json`、`package_check.json`、`upload_check.json`、`submission_request.json`、`kaggle_submission.json`。下载签名链接和上传凭据没有写入研究记录。

下一步：记录本次线上最终结果；现有 62Q 逆向研究继续独立保存，不把复用公开电路称为自研降本。
