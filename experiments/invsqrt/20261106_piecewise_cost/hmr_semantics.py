"""Probe of HMR / classical-bit semantics used by the cost model.

Purpose: decide whether a classical bit produced by HMR carries information
about the measured qubit's Z value.  If it did, one could copy x out, measure
it, and compute the phase with free classical logic.  This probe shows it does
not: the HMR outcome is uniform and independent of the Z value, and the only
x-dependent effect is the (-1)^(b*f(x)) phase kickback that measurement-based
uncomputation corrects.

Run: .venv/bin/python experiments/invsqrt/20261106_piecewise_cost/hmr_semantics.py
"""
import kickmix as km
import numpy as np

SHOTS = 256


def run(x_value):
    b = km.CircuitBuilder()
    x = b.create_quantum_register(1, name='x')
    t = b.create_quantum_register(1, name='t')
    flag = b.create_quantum_register(1, name='flag')
    cb = b.create_classical_register(1, name='c')
    b.cx(x[0], t[0])      # copy x into scratch (free)
    b.hmr(t[0], cb[0])    # X-basis measure + reset
    b.cx(cb[0], flag[0])  # classically conditioned X: expose the outcome
    circuit = b.finish_circuit()
    sim = km.Simulator(batch_size=SHOTS, counting_operations=True)
    sim.use_same_registers_as(circuit)
    sim.write_across_shots(x, np.full((1, SHOTS), bool(x_value)))
    sim.do(circuit)
    out = np.asarray(sim.read_across_shots(flag)).ravel()
    phases = [sim.read_shot_phase(i) for i in range(SHOTS)]
    st = sim.operation_statistics()
    return dict(x=x_value, ones_in_outcome=int(out.sum()), shots=SHOTS,
                phase_values=sorted({str(p) for p in phases}),
                paid=st.num_toffoli_like, zpow=st.num_z_pow(min_clifford_hierarchy_level=4))


def main():
    print('HMR outcome is the classical bit exposed through a controlled X on flag.')
    for v in (0, 1):
        print(run(v))
    print('Interpretation: both input values give ~50% ones, so the bit is uniform and')
    print('independent of the measured Z value; only the tracked phase differs.')


if __name__ == '__main__':
    main()
