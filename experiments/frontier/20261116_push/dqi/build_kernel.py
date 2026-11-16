#!/usr/bin/env python3
"""Build a self-contained Kaggle script kernel: inline the qccscope zip as base64."""
import base64
import io
import pathlib
import sys
import zipfile

PKG = pathlib.Path("/tmp/qccscope_pkg/qccscope")
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(PKG.glob("*.py")):
        z.write(p, f"qccscope/{p.name}")
b64 = base64.b64encode(buf.getvalue()).decode()

for name in sys.argv[1:]:
    here = pathlib.Path(name)
    src = (here / "main.py").read_text()
    if "QQB64" in src:
        src = src.replace("QQB64", repr(b64))
    out = here / "main_built.py"
    out.write_text(src)
    print(name, "->", out, len(out.read_text()))
