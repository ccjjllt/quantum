"""Build a decoder variant with kickmix and print Q / static T.

usage: build_variant.py <package_root> <module_path> <output.kmb>
  package_root: directory holding `decode.py` (or the module itself) and `exp/`
  module_path : python file exposing decode(b, S, E)
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import kickmix as km

sys.modules["circ"] = km


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    module_path = Path(sys.argv[2]).resolve()
    out = Path(sys.argv[3])
    sys.path[:0] = [str(root), str(root.parent)]
    spec = importlib.util.spec_from_file_location("decoder_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["decoder_under_test"] = module
    spec.loader.exec_module(module)
    b = km.CircuitBuilder()
    S = [b.alloc_qubits(12) for _ in range(70)]
    E = [b.alloc_bits(12) for _ in range(4095)]
    start = time.time()
    module.decode(b, S, E)
    metadata = []
    for i in range(70):
        metadata.append(f'REGISTER r{i} "S{i}"')
        metadata.extend(f'APPEND_TO_REGISTER q{12 * i + k} r{i}' for k in range(12))
    for j in range(4095):
        metadata.append(f'REGISTER r{70 + j} "E{j}"')
        metadata.extend(f'APPEND_TO_REGISTER b{12 * j + k} r{70 + j}' for k in range(12))
    c = km.Circuit("\n".join(metadata)) + b.finish_circuit()
    c.to_file(str(out), format="kmb")
    stats = c.operation_statistics()
    record = dict(sha256=hashlib.file_digest(open(out, "rb"), "sha256").hexdigest(),
                  Q=c.num_qubits, T_static=stats.num_toffoli_like,
                  num_ops=len(c), num_bits=c.num_bits,
                  seconds=round(time.time() - start, 1))
    print(json.dumps(record), flush=True)
    out.with_suffix(".build.json").write_text(json.dumps(record, indent=1) + "\n")


if __name__ == "__main__":
    main()
