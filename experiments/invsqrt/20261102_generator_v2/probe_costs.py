"""Primitive cost probes for generator v2 design (manual-run only).

Measures kickmix CircuitBuilder primitive costs used by the estimates in
``primitives.md``. NOT a test file, NOT a verifier run, does NOT read any
baseline KMB. Run manually::

    uv run python experiments/invsqrt/20261102_generator_v2/probe_costs.py

Writes artifacts/20261102_generator_v2/invsqrt/primitive_probes.json.
"""

import hashlib
import json
from pathlib import Path

import kickmix as km

OUT = Path("artifacts/20261102_generator_v2/invsqrt/primitive_probes.json")


def stat(circuit):
    s = circuit.operation_statistics()
    return {"ops": dict(s), "toffoli_like": s.num_toffoli_like}


def probe_unary_seq():
    b = km.CircuitBuilder()
    addr = b.create_quantum_register(8, name="a")
    tgt = b.create_quantum_register(1, name="t")
    with b.unary_iteration(addr, range(256)) as it:
        for _v, m in it:
            b.cx(m, tgt[0])
    return stat(b.finish_circuit())


def probe_init_lookup(width, seed=1):
    import random

    rng = random.Random(seed)
    b = km.CircuitBuilder()
    addr = b.create_quantum_register(8, name="a")
    tgt = b.create_quantum_register(width, name="t")
    table = [rng.getrandbits(width) for _ in range(256)]
    b.init_lookup(table=table, address=addr, target=tgt)
    return stat(b.finish_circuit())


def probe_iadd(width, controlled=False):
    b = km.CircuitBuilder()
    tgt = b.create_quantum_register(width, name="t")
    src = b.create_quantum_register(width, name="s")
    if controlled:
        ctl = b.create_quantum_register(1, name="c")[0]
        b.iadd(src, target=tgt, control=ctl)
    else:
        b.iadd(src, target=tgt)
    return stat(b.finish_circuit())


def probe_isub(width):
    b = km.CircuitBuilder()
    tgt = b.create_quantum_register(width, name="t")
    src = b.create_quantum_register(width, name="s")
    b.isub(src, target=tgt)
    return stat(b.finish_circuit())


def probe_rot(n_target, n_shift):
    b = km.CircuitBuilder()
    tgt = b.create_quantum_register(n_target, name="v")
    sh = b.create_quantum_register(n_shift, name="sh")
    b.right_rotate(tgt, sh)
    return stat(b.finish_circuit())


def probe_unary_temp():
    b = km.CircuitBuilder()
    addr = b.create_quantum_register(8, name="a")
    before = b.num_allocated_qubits
    with b.unary_iteration(addr, range(256)):
        inside = b.num_allocated_qubits
    after = b.num_allocated_qubits
    return {"before": before, "inside": inside, "after": after}


def probe_zpow_fraction():
    from fractions import Fraction

    b = km.CircuitBuilder()
    q = b.create_quantum_register(2, name="p")
    b.z_pow(q[0], Fraction(1, 2**36))
    b.z_pow(q[1], 0.25)
    c = b.finish_circuit()
    return {"text": str(c)}


def probe_determinism():
    def build_once():
        b = km.CircuitBuilder()
        addr = b.create_quantum_register(8, name="a")
        tgt = b.create_quantum_register(33, name="t")
        table = [(k * 0x9E3779B1) & ((1 << 33) - 1) for k in range(256)]
        with b.unary_iteration(addr, range(256)) as it:
            for v, m in it:
                vv = table[v]
                for j in range(33):
                    if (vv >> j) & 1:
                        b.cx(m, tgt[j])
        return b.finish_circuit()

    c1, c2 = build_once(), build_once()
    t1, t2 = str(c1), str(c2)
    return {
        "equal": t1 == t2,
        "sha256": hashlib.sha256(t1.encode()).hexdigest(),
        "num_qubits": c1.num_qubits,
    }


def main():
    res = {
        "kickmix_has_h": hasattr(km.CircuitBuilder(), "h"),
        "unary8_seq_1cx": probe_unary_seq(),
        "init_lookup_rand": {
            f"w{w}": probe_init_lookup(w) for w in (12, 22, 33)
        },
        "iadd_qq": {f"w{w}": probe_iadd(w) for w in (5, 14, 22, 33, 36, 55)},
        "iadd_qq_controlled": {
            f"w{w}": probe_iadd(w, controlled=True) for w in (14, 18, 36)
        },
        "isub_qq": {f"w{w}": probe_isub(w) for w in (5, 36, 55)},
        "rot55_by_4q": probe_rot(55, 4),
        "rot22_by_5q": probe_rot(22, 5),
        "unary_temp_qubits": probe_unary_temp(),
        "zpow_fraction": probe_zpow_fraction(),
        "determinism": probe_determinism(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps(res, indent=2, sort_keys=True)[:3000])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
