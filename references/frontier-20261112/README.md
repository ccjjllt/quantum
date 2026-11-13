# 27.078 public-frontier 来源清单（2026-11-12/13）

本目录保留当前最佳提交（`submissions/20261113_27_078/`，Kaggle ref 58299045，
public 27.00209）的公开源清单，供重新下载和审计。原始 `.kmb`、解包目录和大型
artifacts 已于 2026-11-13 清理，完整候选固定在：

```text
submissions/20261113_27_078/submission.zip
SHA-256 63c5a0776bb1d91490c2e50e4c04607c78b91472f9da45247901ea4af314657c
18 files, 463,378,740 bytes uncompressed
```

## 内容

- `frontier/manifest.csv`、`frontier/chem14840_urls.json`、`frontier/part_urls.json`：
  公开 frontier 的源清单（2026-11-12 抓取）。
- `frontier/release_source.xz`：公开源压缩快照。
- `frontier/chem14840_README.md`：化学 14,840 表的来源说明。
- `frontier/*.csv`：parts 兼容性、word table、factorization 清单。
- `rescan-meta/`：2026-11-12 公开 rescan 的 circuits/families/sources CSV、
  SHA256SUMS 和 README。

这些文件只用于来源追踪，不是可直接提交的电路。当前三件电路的 SHA-256、成本和
官方验证范围见 `submissions/20261113_27_078/README.md`。
