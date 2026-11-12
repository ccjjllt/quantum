"""Build the public 889Q decoder and log the ancilla allocation timeline.

Peak is counted over allocations made after the 70 syndrome registers, so it is
the true ancilla high-water mark.
"""
from __future__ import annotations
import importlib.util
import inspect
import json
from collections import Counter
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
        self.allocs: list[dict] = []
        self.frees: list[dict] = []
        self.phase = "start"

    def alloc_qubits(self, n):
        qubits = self.inner.alloc_qubits(n)
        frame = inspect.stack()[1]
        rec = dict(id=self.next_id, n=n, caller=frame.function, line=frame.lineno,
                   phase=self.phase, event=len(self.allocs) + len(self.frees))
        self.next_id += 1
        self.active[rec["id"]] = rec
        self.allocs.append(rec)
        for q in qubits:
            self.qid_to_alloc[int(q.id)] = rec
        live = sum(r["n"] for r in self.active.values() if r["id"] >= 70)
        if live > self.peak:
            self.peak = live
            self.peak_snapshot = [dict(r) for r in self.active.values() if r["id"] >= 70]
        return qubits

    def free(self, qubits):
        items = []

        def flatten(obj):
            if isinstance(obj, km.q):
                items.append(obj)
                return
            try:
                for part in obj:
                    flatten(part)
            except TypeError:
                pass

        flatten(qubits)
        for q in items:
            if not isinstance(q, km.q):
                continue
            rec = self.qid_to_alloc.pop(int(q.id), None)
            if rec is not None:
                self.active.pop(rec["id"], None)
                self.frees.append(dict(id=rec["id"], n=rec["n"], phase=self.phase,
                                       event=len(self.allocs) + len(self.frees)))
        return self.inner.free(qubits)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "decoder_under_test", SOURCE / "exp/r-main/narrow240/decode_retimed.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["decoder_under_test"] = module
    spec.loader.exec_module(module)
    inner = km.CircuitBuilder()
    b = LoggingBuilder(inner)
    S = [b.alloc_qubits(12) for _ in range(70)]
    E = [b.alloc_bits(12) for _ in range(4095)]
    # mark stages by scanning the source? simpler: monkeypatch nothing; use wall time
    start = time.time()
    module.decode(b, S, E)
    c = inner.finish_circuit()
    print(json.dumps(dict(seconds=round(time.time() - start, 1), Q=c.num_qubits,
                          T=c.operation_statistics().num_toffoli_like,
                          allocs=len(b.allocs), peak_ancilla=b.peak)))
    print("peak snapshot by caller/size:")
    for key, cnt in Counter((r["caller"], r["n"]) for r in b.peak_snapshot).most_common():
        print(f"  {key[0]:32s} n={key[1]:<3d} x{cnt}")
    # allocations never freed
    freed = {r["id"] for r in b.frees}
    never = [r for r in b.allocs if r["id"] >= 70 and r["id"] not in freed]
    print("never freed (ancilla):")
    for r in never:
        print("  ", r)
    (OUT / "alloc_timeline.json").write_text(json.dumps(dict(
        peak_ancilla=b.peak, peak_snapshot=b.peak_snapshot,
        allocs=b.allocs, frees=b.frees, never_freed=never), indent=1) + "\n")


if __name__ == "__main__":
    main()
