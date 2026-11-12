"""Write a .kmb as .kmx in a temp directory for streaming tag/interval scans."""
from __future__ import annotations
import os
import sys
from pathlib import Path

import kickmix as km

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_low_ancilla")


def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else TMP / (src.stem + ".kmx")
    out.parent.mkdir(parents=True, exist_ok=True)
    circuit = km.Circuit.from_file(str(src), format="kmb")
    print("loaded", src, "qubits", int(circuit.num_qubits), flush=True)
    circuit.to_file(str(out), format="kmx")
    print("wrote", out, os.path.getsize(out), flush=True)


if __name__ == "__main__":
    main()
