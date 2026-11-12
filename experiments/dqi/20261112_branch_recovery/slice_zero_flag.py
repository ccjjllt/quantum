"""切片证明：unextract 开头的 24-bit zero-flag gadget（X + AND ladder + copy-out + MBU 还原）
的语义 = out ^= [word==0] & ctl，相位 0，所有 ladder ancilla 回 0；代价 n-1 CCX。
用 n=12 的等价 toy（与 eae.kmx L53455037-53455178 同构）在 kickmix 上穷举 2^12 输入。
"""
from __future__ import annotations
import numpy as np
import kickmix as km

N = 12

def build():
    b = km.CircuitBuilder()
    q = b.create_quantum_register(N, "q")
    ctl = b.create_quantum_register(1, "ctl")
    out = b.create_quantum_register(1, "out")
    lad = b.create_quantum_register(N - 1, "lad")
    m = b.create_classical_register(1, "m")

    b.x(q)
    b.ccx(q[0], q[1], lad[0])
    for i in range(1, N - 1):
        b.ccx(lad[i - 1], q[i + 1], lad[i])
    # copy out the (complement) AND, exactly like  CCX q857 q887 q847
    b.ccx(lad[N - 2], ctl[0], out[0])
    # MBU unwind, top-down; one scratch classical bit reused, as in the .kmx
    b.hmr(lad[N - 2], m[0])
    for i in reversed(range(1, N - 1)):
        b.ccz(lad[i - 1], q[i + 1], m[0])
        b.hmr(lad[i - 1], m[0])
    b.ccz(q[0], q[1], m[0])
    b.x(q)
    return b.finish_circuit(), q, ctl, out, lad

def main():
    c, q, ctl, out, lad = build()
    nshots = 1 << N
    sim = km.Simulator(batch_size=nshots, debug_print=False, counting_operations=True, seed=12345)
    sim.use_same_registers_as(c)
    vals = np.arange(nshots, dtype=np.int64)
    bits = np.zeros((N, nshots), dtype=bool)
    for i in range(N):
        bits[i] = (vals >> i) & 1
    sim.write_across_shots(q, bits)
    sim.write_across_shots(ctl, np.ones((1, nshots), dtype=bool))
    sim.do(c)
    got_out = sim.read_across_shots(out)[0]
    got_q = sim.read_across_shots(q)
    got_lad = sim.read_across_shots(lad)
    phase = sim.read_phase_flipped_across_shots()
    want = (vals == 0)
    print("shots", nshots)
    print("out == [q==0]:", bool((got_out == want).all()))
    print("q restored   :", bool((got_q == bits).all()))
    print("ladder == 0  :", bool((~got_lad).all()))
    print("phase flips  :", int(phase.sum()))
    st = sim.operation_statistics()
    print("num_toffoli_like (per shot, static):", st.num_toffoli_like)
    print("expected n-1 =", N - 1)
    # 对照：朴素 zero_flag 代价 2n-3
    print("naive zero_flag cost 2n-3 =", 2 * N - 3)

if __name__ == "__main__":
    main()
