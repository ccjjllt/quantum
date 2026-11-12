"""eae396ba：kmb -> kmx（835,537,319 bytes / 61,514,188 lines）。

输出放在系统临时目录（835 MB，不进 Git）。只读 kmb。
"""
import os
from pathlib import Path

import kickmix as km

SRC = Path("/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261112_eae_candidate/dqi.kmb")
OUT = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = km.Circuit.from_file(str(SRC))
    print("loaded", SRC, "qubits", int(c.num_qubits), flush=True)
    c.to_file(str(OUT), format="kmx")
    print("wrote", OUT, os.path.getsize(OUT), flush=True)


if __name__ == "__main__":
    main()
