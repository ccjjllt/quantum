"""Print circuit resources without simulating or verifying the circuit."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("circuit", type=Path, help="A kickmix .kmb or .kmx file.")
    parser.add_argument("--all-registers", action="store_true", help="List every register instead of the first 16.")
    args = parser.parse_args()

    import kickmix

    circuit = kickmix.Circuit.from_file(args.circuit, format="auto")
    stats = circuit.operation_statistics()
    registers = list(circuit.register_data.items())
    shown = registers if args.all_registers else registers[:16]
    print(json.dumps({
        "path": str(args.circuit.resolve()),
        "num_qubits": circuit.num_qubits,
        "num_bits": circuit.num_bits,
        "num_registers": circuit.num_registers,
        "registers": [{"name": name, "width": len(values)} for name, values in shown],
        "omitted_registers": len(registers) - len(shown),
        "operations": dict(stats),
        "static_toffoli_like": stats.num_toffoli_like,
        "note": "Static counts only; the official verifier measures executed gates and correctness.",
    }, indent=2))


if __name__ == "__main__":
    main()
