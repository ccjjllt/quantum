import base64
import pathlib
import sys

ROOT = pathlib.Path("/Users/zhaohuaxiang/ccjjllt/quantum")
B64 = ROOT / "experiments/frontier/20261116_push/pipeline/invsqrt_563d0583.kmb.b64"
BODY = ROOT / "experiments/frontier/20261118_push/invsqrt/k1_rotlp/body.py"
OUT = BODY.parent / "main.py"

b64 = B64.read_text().strip()
body = BODY.read_text()
assert body.count("@@B64@@") == 1
OUT.write_text(body.replace("@@B64@@", b64))
print("wrote", OUT, OUT.stat().st_size, "chars; b64 len", len(b64))
