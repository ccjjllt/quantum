"""Build the narrow240 ('892-qubit line') decoder from the recovered kit."""
import importlib.util
import json
from pathlib import Path
import sys
import time

import kickmix as km

WORK = Path(__file__).resolve().parents[3] / 'artifacts/20261106_phase_recovery'
KIT = WORK / 'old_build/blocks/dqi/pro-q18-900/source/playbook/kit/decoder'
NARROW = WORK / 'old_build/blocks/dqi/pro-q18-900/source/exp/r-main/narrow240'
ENTRY = sys.argv[1] if len(sys.argv) > 1 else 'decode_combo.py'
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else WORK / 'narrow240/dqi.kmb'

sys.path.insert(0, str(NARROW))
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(WORK / 'kit_helpers'))
sys.modules['circ'] = km


def main():
    module_name = Path(ENTRY).stem
    spec = importlib.util.spec_from_file_location(module_name, NARROW / ENTRY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    start = time.time()
    builder = km.CircuitBuilder()
    syndromes = [builder.alloc_qubits(12) for _ in range(70)]
    masks = [builder.alloc_bits(12) for _ in range(4095)]
    module.decode(builder, syndromes, masks)
    metadata = []
    for i in range(70):
        metadata.append(f'REGISTER r{i} "S{i}"')
        metadata.extend(f'APPEND_TO_REGISTER q{12*i+k} r{i}' for k in range(12))
    for j in range(4095):
        metadata.append(f'REGISTER r{70+j} "E{j}"')
        metadata.extend(f'APPEND_TO_REGISTER b{12*j+k} r{70+j}' for k in range(12))
    circuit = km.Circuit('\n'.join(metadata)) + builder.finish_circuit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    circuit.to_file(str(OUT), format='kmb')
    record = {'entry': str(NARROW / ENTRY), 'Q': circuit.num_qubits,
              'T_static': circuit.operation_statistics().num_toffoli_like,
              'ops': len(circuit), 'bits': circuit.num_bits, 'seconds': round(time.time()-start, 1)}
    (OUT.parent / (OUT.stem + '.build.json')).write_text(json.dumps(record, indent=1))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
