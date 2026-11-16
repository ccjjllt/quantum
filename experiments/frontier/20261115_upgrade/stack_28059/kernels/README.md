# 当前最佳的组装/复核脚本（28.05896）

这两个脚本是 Kaggle kernel 的本地副本，保留用于逐字节重建提交包和独立复核。
2026-11-16 清理时从临时工作区收回仓库（原临时目录已删除）。

| 文件 | 对应 Kaggle kernel | 作用 |
|---|---|---|
| `assemble_28059.py` | `qingyu1232/qcc-assemble-28059` v1 | 按 18 个 SHA-256 在 `/kaggle/input` 定位成员，断言哈希后打包 `submission.zip` |
| `verify_28059.py` | `jiyujia/qcc-verify-28059` v1 | 用未修改的官方 verifier 依次复核化学 / invsqrt / DQI |
| `assemble_metadata.json` / `verify_metadata.json` | — | 对应的 kernel metadata（CPU、无 TPU、挂载两个公开 dataset + 比赛数据） |

## 已记录的结果

```text
assemble: found 18 of 18 members
          submission.zip 51,858,038 B
          sha256 87703019f2a950341201f4cc69420761464fd17365b448c7808ece0bbac30800
submit:   ref 58392219  COMPLETE  28.05896  rank 91/3114
verify:   chem     PASS 294,800,582.44      Q=427  T=14,712  λ_eff 46.9276   (28 s)
          invsqrt  PASS 75,170.62           Q=44   T=1,458.25  200,540,928 shots (630 s)
          DQI      PASS 347,904,227,555.54  Q=890  T=368,699.85  102,400 shots (162 s)
```

## 复现

把 `assemble_metadata.json` 的 `id` 改成自己的账号后 push，运行结束下载
`submission.zip`；或用 `verify_metadata.json` 在 CPU 上重跑三件复核。
两个脚本都只依赖 numpy / 比赛数据包，不需要 GPU，也不使用 TPU。
