"""Build a self-contained Kaggle integrator script from main_template.py + a manifest.

    python3 make_main.py --members members_2815083.json \
        --label "28.15083 shipped triple" --expected-gm 28.15082863 \
        --min-gm 28.15082863 --invsqrt-b64 ../20261116_push/pipeline/invsqrt_0af21cb8.kmb.b64

`members_2815083.json` is the pinned 18-member manifest of the shipped 28.15083 candidate
(sha256 + size + human source note for each member). The invsqrt bytes are the only
member embedded in the script; everything else is located by (size, sha256) under
/kaggle/input after any archive is unpacked.
"""
from __future__ import annotations

import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--expected-gm", type=float, required=True)
    ap.add_argument("--min-gm", type=float, required=True)
    ap.add_argument("--invsqrt-b64", required=True)
    ap.add_argument("--out", default=str(HERE / "main.py"))
    a = ap.parse_args()

    manifest = json.loads(pathlib.Path(a.members).read_text())["members"]
    b64 = "".join(pathlib.Path(a.invsqrt_b64).read_text().split())

    legs = {"invsqrt": {}, "dqi": {}, "chem": {}}
    for name, meta in manifest.items():
        if name == "invsqrt.kmb":
            legs["invsqrt"][name] = {"sha256": meta["sha256"], "size": meta["size"], "b64": b64}
        elif name == "dqi.kmb":
            legs["dqi"][name] = {"sha256": meta["sha256"], "size": meta["size"], "src": meta.get("source", "")}
        else:
            legs["chem"][name] = {"sha256": meta["sha256"], "size": meta["size"], "src": meta.get("source", "")}

    template = (HERE / "main_template.py").read_text()
    assert "__LEGS__" in template
    out = (
        template.replace("__LEGS__", json.dumps(legs, indent=1))
        .replace("__EXPECTED_GM__", repr(float(a.expected_gm)))
        .replace("__MIN_GM__", repr(float(a.min_gm)))
        .replace("__LABEL__", json.dumps(a.label))
    )
    pathlib.Path(a.out).write_text(out)
    print(f"wrote {a.out} ({len(out)} bytes, {len(manifest)} members)")


if __name__ == "__main__":
    main()
