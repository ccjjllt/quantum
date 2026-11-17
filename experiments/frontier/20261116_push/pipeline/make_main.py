"""Generate the self-contained Kaggle script from the template plus the embedded invsqrt.

Usage:
    python make_main.py

The only large payload is invsqrt_0af21cb8.kmb.b64, which is zlib-compressed and base64
encoded. Its decoded SHA-256 is asserted inside main.py before use.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
template = (HERE / "main_template.py").read_text()
b64 = "".join((HERE / "invsqrt_0af21cb8.kmb.b64").read_text().split())
assert b64 and '"' not in b64
# Guard against transcribed-hash typos (e.g. a 63-char sha): every pinned
# member hash must be 64 lowercase hex chars.
import re
for m in re.finditer(r'"sha256": "([0-9a-f]+)"', template):
    assert len(m.group(1)) == 64, m.group(1)
out = template.replace("__INV_B64__", b64)
assert "__INV_B64__" not in out
(HERE / "main.py").write_text(out)
print(f"wrote {HERE / 'main.py'} ({len(out)} bytes, embedded b64 {len(b64)} chars)")
