
import json
import kickmix as km
from dqi.dqi_reference_circuit import build_reference_circuit
import dqi_fast
res = {}
for (m, n, d) in [(15, 6, 4), (63, 6, 6), (255, 10, 8)]:
    k = f"{m}_{n}_{d}"
    entry = {}
    ref = build_reference_circuit(m, n, d)
    ref.to_file(f"/kaggle/working/ref_{k}.kmb", format="kmb")
    st = ref.operation_statistics()
    entry["reference"] = {"Q": ref.num_qubits, "static_T": st.num_toffoli_like, "ops": len(ref)}
    fast = dqi_fast.build_fast_circuit(m, n, d)
    fast.to_file(f"/kaggle/working/fast_{k}.kmb", format="kmb")
    st = fast.operation_statistics()
    entry["fast"] = {"Q": fast.num_qubits, "static_T": st.num_toffoli_like,
                     "ops": len(fast), "n_iter": 2 * n + 3}
    res[k] = entry
    print(json.dumps({k: entry}), flush=True)
print("JSON " + json.dumps(res), flush=True)
