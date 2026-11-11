"""差分窗口精查：读 paid_diff.json（含同步锚点），打印完整新旧窗口对照。"""
from __future__ import annotations

import json
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff")
F_KMX = TMP / "dqi.kmx"
E_KMX = TMP / "e9.kmx"


def win(kmx: Path, lo: int, hi: int):
    out = []
    with kmx.open("r", encoding="utf-8", errors="replace") as f:
        for n, l in enumerate(f, start=1):
            if n < lo:
                continue
            if n > hi:
                break
            out.append((n, l.rstrip("\n")))
    return out


def main() -> None:
    diff = json.loads(Path("artifacts/20261110_e9diff/paid_diff.json").read_text())
    for h in diff["hunks"]:
        print(f"===== [{h['stage']}/{h['label']}] del={h['n_del']} add={h['n_add']} "
              f"F{h['f_range']} E{h['e_range']} a_idx={h.get('a_start_idx')} b_idx={h.get('b_start_idx')}")
        print(f"  del: {h['del_texts']}")
        print(f"  add: {h['add_texts']}")
        if h["f_range"]:
            for n, t in win(F_KMX, h["f_range"][0], h["f_range"][1]):
                print(f"  F:{n} {t}")
        if h["e_range"]:
            for n, t in win(E_KMX, h["e_range"][0], h["e_range"][1]):
                print(f"  E:{n} {t}")


if __name__ == "__main__":
    main()
