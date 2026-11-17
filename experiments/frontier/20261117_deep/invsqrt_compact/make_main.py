"""Build the Kaggle CPU kernel folder: inline the pinned b64 into main.py."""
from __future__ import annotations

import base64
import hashlib
import pathlib
import zlib

HERE = pathlib.Path(__file__).resolve().parent
B64_SRC = pathlib.Path('experiments/frontier/20261116_push/pipeline/invsqrt_0af21cb8.kmb.b64')
WANT_SHA = '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b'


def main() -> None:
    root = pathlib.Path(__file__).resolve().parents[4]
    b64 = (root / B64_SRC).read_text().strip()
    raw = zlib.decompress(base64.b64decode(b64))
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == WANT_SHA, (sha, WANT_SHA)
    template = (HERE / 'main_template.py').read_text()
    out = template.replace('__B64__', b64)
    (HERE / 'k1_liveness' / 'main.py').write_text(out)
    print(f'wrote main.py  b64 chars {len(b64)}  kmb bytes {len(raw)}  sha {sha[:16]}')


if __name__ == '__main__':
    main()
