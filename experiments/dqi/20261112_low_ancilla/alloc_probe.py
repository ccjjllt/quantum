"""Build the public 889Q decoder while logging every qubit allocation/free.

Read-only on the source tree: the builder is wrapped in a logging proxy.
"""
from __future__ import annotations
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import time

import kickmix as km

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "artifacts/20261112_low_ancilla"
SOURCE = OUT / "source"
sys.modules["circ"] = km


class LoggingBuilder:
    def __init__(self, inner):
        self.inner = inner
        self.qid_to_alloc: dict[int, dict] = {}
        self.active: dict[int, dict] = {}
        self.next_id = 0
        self.peak = 0
        self.peak_snapshot: list[dict] = []
        self.peak_alloc = None
        self.allocs = 0

    def alloc_qubits(self, n):
        qubits = self.inner.alloc_qubits(n)
        frame = inspect.stack()[1]
        rec = dict(id=self.next_id, n=n, caller=frame.function, line=frame.lineno)
        self.next_id += 1
        self.allocs += 1
        self.active[rec["id"]] = rec
        for q in qubits:
            self.qid_to_alloc[int(q.id)] = rec
        live = sum(r["n"] for r in self.active.values())
        if live > self.peak:
            self.peak = live
            self.peak_snapshot = [dict(r) for r in self.active.values()]
            self.peak_alloc = rec
        return qubits

    def free(self, qubits):
        try:
            items = list(qubits)
        except TypeError:
            items = [qubits]
        for q in items:
            if not isinstance(q, km.q):
                continue
            rec = self.qid_to_alloc.pop(int(q.id), None)
            if rec is not None:
                self.active.pop(rec["id"], None)
        return self.inner.free(qubits)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "public_logged.kmb"
    spec = importlib.util.spec_from_file_location(
        "decoder_under_test", SOURCE / "exp/r-main/narrow240/decode_retimed.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["decoder_under_test"] = module
    spec.loader.exec_module(module)
    inner = km.CircuitBuilder()
    b = LoggingBuilder(inner)
    S = [b.alloc_qubits(12) for _ in range(70)]
    E = [b.alloc_bits(12) for _ in range(4095)]
    start = time.time()
    module.decode(b, S, E)
    c = inner.finish_circuit()
    print(json.dumps(dict(seconds=round(time.time() - start, 1), Q=c.num_qubits,
                          T=c.operation_statistics().num_toffoli_like,
                          allocs=b.allocs, peak=b.peak)))
    (OUT / "alloc_peak.json").write_text(json.dumps(dict(
        peak=b.peak, peak_alloc=b.peak_alloc, peak_snapshot=b.peak_snapshot,
        allocs=b.allocs), indent=1) + "\n")
    from collections import Counter
    print("peak snapshot by caller:")
    for name, cnt in Counter(r["caller"] for r in b.peak_snapshot).most_common():
        sizes = Counter(r["n"] for r in b.peak_snapshot if r["caller"] == name)
        print(f"  {name:32s} x{cnt:<4d} sizes={dict(sizes)}")
    if "--write" in sys.argv:
        c.to_file(str(target), format="kmb")


if __name__ == "__main__":
    main()
