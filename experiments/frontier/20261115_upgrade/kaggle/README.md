# Kaggle 运行记录

本目录保存 2026-11-15 公开前沿升级的 Kaggle 组装入口。

- `assembler/main.py`：从 `/kaggle/input` 读取公开数据集并打包 18 文件的标准脚本。
  `kernel-metadata.json` 声明了 `heliosli/qcc-circuits-live`、
  `maoxin123/qcc-chemistry-4033-toffoli-loaders`、`ahoirg/qcc-portfolio-gm-27-28999`
  和 competition source。
- MCP `save_notebook` 未能把 dataset/competition source 附加到私有 notebook，
  实际运行使用同一逻辑，但在 notebook 内用 Kaggle 数据集签名 URL 下载文件；
  签名 URL 已过期，不作为记录保存。公开数据集名和 SHA-256 见
  `frontier_scan.md` / `SUMMARY.md`。
- 实际成功的 Kaggle notebook：
  - `qingyu1232/qcc-27-312-frontier-assembler`：HW-26 + DQI + 4033 chem，输出
    `submission.zip`（SHA-256 `46d53bde…c933`）。
  - `qingyu1232/qcc-hw-26-invsqrt-verify`：HW-26 官方 invsqrt 全量 200,540,928 shots PASS。
  - `qingyu1232/qcc-dqi-retention-hops`：cutoff-18 + retention `max_hops=0/1/2` 复核，
    输出逐字节等于 `821bf8d1`。
- 未在本机运行官方全量 verifier 或大电路模拟；上述运行均在 Kaggle 上完成。
