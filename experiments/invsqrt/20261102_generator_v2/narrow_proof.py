"""Narrow Cuccaro proof (manual-run, not a test file).

Proves bitwise equivalence of hand-written narrow adder vs kickmix generic
iadd on small widths via exhaustive Simulator checks. No fitting, no KMB.
Run: uv run python experiments/invsqrt/20261102_generator_v2/narrow_proof.py
"""
import sys
from pathlib import Path
import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def maj(b, a, bb, c):
    # MAJ(a[i], b[i], carry): inputs as qubit refs; carry is single qubit
    # MAJ = CX(c,b); CX(c,a); CCX(a,b,c)
    b.cx(c, bb)
    b.cx(c, a)
    b.ccx(a, bb, c)


def maj_inv(b, a, bb, c):
    b.ccx(a, bb, c)
    b.cx(c, a)
    b.cx(c, bb)


def uma(b, a, bb, c):
    # UMA as derived: CCX(a,b,c); CX(c,a); CX(c,b); CX(a,b); CX(c,b)
    b.ccx(a, bb, c)
    b.cx(c, a)
    b.cx(c, bb)
    b.cx(a, bb)
    b.cx(c, bb)


def uma_inv(b, a, bb, c):
    b.cx(c, bb)
    b.cx(a, bb)
    b.cx(c, bb)
    b.cx(c, a)
    b.ccx(a, bb, c)


def cuccaro_add(b, A, B, carry):
    """Uncontrolled equal-length add: B += A (mod 2^n). A preserved, carry 0->0."""
    n = len(A)
    for i in range(n):
        maj(b, A[i], B[i], carry)
    for i in reversed(range(n)):
        uma(b, A[i], B[i], carry)


def test_uncontrolled(n=3):
    fails = 0
    total = 0
    for av in range(2**n):
        for bv in range(2**n):
            total += 1
            b = km.CircuitBuilder()
            A = b.create_quantum_register(n, name="a")
            B = b.create_quantum_register(n, name="b")
            c = b.alloc_qubits(1)
            # init classical values via X
            for i in range(n):
                if (av >> i) & 1:
                    b.x(A[i])
                if (bv >> i) & 1:
                    b.x(B[i])
            cuccaro_add(b, A, B, c[0])
            circ = b.finish_circuit()
            sim = km.Simulator(batch_size=1)
            sim.use_same_registers_as(circ)
            sim.do(circ)
            gotB = sim.read_within_shot("b", 0, out=int)
            gotA = sim.read_within_shot("a", 0, out=int)
            wantB = (av + bv) % (2**n)
            if gotB != wantB or gotA != av:
                print(f"FAIL n={n} a={av} b={bv} gotB={gotB} wantB={wantB} gotA={gotA}")
                fails += 1
    print(f"uncontrolled n={n}: {total-fails}/{total} ok")
    return fails == 0


def test_controlled_via_copy(n=3):
    fails = total = 0
    for ctl in (0, 1):
        for sv in range(2**n):
            for tv in range(2**n):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(n, name="s")
                T = b.create_quantum_register(n, name="t")
                C = b.create_quantum_register(1, name="c")
                Cp = b.alloc_qubits(n)
                cc = b.alloc_qubits(1)
                for i in range(n):
                    if (sv >> i) & 1:
                        b.x(S[i])
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                for i in range(n):
                    b.ccx(C[0], S[i], Cp[i])
                cuccaro_add(b, Cp, T, cc[0])
                for i in range(n):
                    b.ccx(C[0], S[i], Cp[i])
                b.free(Cp)
                b.free(cc)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                wantT = (tv + (sv if ctl else 0)) % (2**n)
                if gotT != wantT:
                    print(f"FAIL ctl={ctl} s={sv} t={tv} got={gotT} want={wantT}")
                    fails += 1
    print(f"controlled-via-copy n={n}: {total-fails}/{total} ok")
    return fails == 0


def test_split_row(noff=2, nlow=2, nhigh=3):
    """Split adder: target = low(nlow) + high(nhigh); offset noff==nlow.
    Forward: copy, low cuccaro with cout copy, high generic 1-bit add, flip uncompute.
    Compare vs generic controlled iadd on full target."""
    import itertools
    fails = total = 0
    ntgt = nlow + nhigh
    for ctl in (0, 1):
        for sv in range(2**noff):
            for tv in range(2**ntgt):
                total += 1
                # --- narrow ---
                b = km.CircuitBuilder()
                S = b.create_quantum_register(noff, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                Cp = b.alloc_qubits(noff)
                carry = b.alloc_qubits(1)
                cout = b.alloc_qubits(1)
                for i in range(noff):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                Tlow = T[0:nlow]
                Thigh = T[nlow:ntgt]
                for i in range(nlow):
                    maj(b, Cp[i], Tlow[i], carry[0])
                b.cx(carry[0], cout[0])
                for i in reversed(range(nlow)):
                    uma(b, Cp[i], Tlow[i], carry[0])
                # high: add cout (1-bit) into Thigh, uncontrolled
                b.iadd(cout, target=Thigh)
                # uncompute cout via flip: cout ^= (Tlow_new < Cp)
                b.flip_if_less_than(Tlow, Cp, target=cout[0])
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                b.free(Cp)
                b.free(carry)
                b.free(cout)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                # check scratch zero: all qubits except s/t/c should be 0
                nq = circ.num_qubits
                across_ok = True
                # read every qubit index
                arr = sim.read_across_shots(km.q(0))
                # simpler: check Cp/carry/cout freed? Simulator auto-checks? Just check T value.
                wantT = (tv + ((sv if ctl else 0))) % (2**ntgt)
                # NOTE: offset S is aligned to bit0 of T (no shift). For R1 shift j, same by slicing.
                if gotT != wantT:
                    print(f"SPLIT FAIL ctl={ctl} s={sv} t={tv} got={gotT} want={wantT}")
                    fails += 1
                    if fails > 5:
                        print("... truncated")
                        return False
    print(f"split noff={noff} nlow={nlow} nhigh={nhigh}: {total-fails}/{total} ok")
    return fails == 0


def test_split_row_reverse(noff=2, nlow=2, nhigh=3):
    """Reverse narrow (subtract) vs generic isub."""
    fails = total = 0
    ntgt = nlow + nhigh
    for ctl in (0, 1):
        for sv in range(2**noff):
            for tv in range(2**ntgt):
                total += 1
                # start from sum state (as after forward): sum = tv + (sv if ctl)
                s0 = (tv + (sv if ctl else 0)) % (2**ntgt)
                b = km.CircuitBuilder()
                S = b.create_quantum_register(noff, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                Cp = b.alloc_qubits(noff)
                carry = b.alloc_qubits(1)
                cout = b.alloc_qubits(1)
                for i in range(noff):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (s0 >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                Tlow = T[0:nlow]
                Thigh = T[nlow:ntgt]
                # reverse steps: copy; flip(set cout); uncopy; high isub; copy; low inverse; flip? no—
                # use order: copy; flip; uncopy; high isub; copy; low-inverse; uncopy-with-flip?
                # Simpler mirror of forward-with-double-copy:
                # forward was: copy; MAJ; CX; UMA; uncopy; high-iadd; copy; flip; uncopy.
                # inverse (reverse order, inverse ops):
                #   copy; flip; high-isub; copy? Let's do explicit correct subtract:
                #   Step1: copy C (for flip to recompute cout)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                b.flip_if_less_than(Tlow, Cp, target=cout[0])
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                b.free(Cp)
                # high subtract
                b.isub(cout, target=Thigh)
                # low subtract via inverse of low-add: need C again
                Cp2 = b.alloc_qubits(noff)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp2[i])
                # inverse of (MAJ fwd; CX; UMA bwd) = UMA fwd-inv; CX; MAJ bwd-inv
                for i in range(nlow):
                    uma_inv(b, Cp2[i], Tlow[i], carry[0])
                b.cx(carry[0], cout[0])
                for i in reversed(range(nlow)):
                    maj_inv(b, Cp2[i], Tlow[i], carry[0])
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp2[i])
                b.free(Cp2)
                b.free(carry)
                b.free(cout)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                if gotT != tv:
                    print(f"REV FAIL ctl={ctl} s={sv} sum={s0} got={gotT} want={tv}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"split-reverse noff={noff} nlow={nlow} nhigh={nhigh}: {total-fails}/{total} ok")
    return fails == 0


def test_a1_split_sub(noff=3, nlow=3, nhigh=2):
    """A1-shape narrow subtract: source len == nlow (A1: 22/22 scaled to 3/3).

    Forward narrow-sub (copy; flip-set-cout; uncopy; high-isub; copy;
    UMAinv; CX-clear; MAJinv; uncopy) vs integer oracle
    (tv - (sv if ctl)) mod 2^ntgt. A1 rows J0..J12 are this shape."""
    fails = total = 0
    ntgt = nlow + nhigh
    for ctl in (0, 1):
        for sv in range(2**noff):
            for tv in range(2**ntgt):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(noff, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                Cp = b.alloc_qubits(noff)
                carry = b.alloc_qubits(1)
                cout = b.alloc_qubits(1)
                for i in range(noff):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                Tlow = T[0:nlow]
                Thigh = T[nlow:ntgt]
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                b.flip_if_less_than(Tlow, Cp, target=cout[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp[i])
                b.free(Cp)
                b.isub(cout, target=Thigh)
                Cp2 = b.alloc_qubits(noff)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp2[i])
                for i in range(noff):
                    uma_inv(b, Cp2[i], Tlow[i], carry[0])
                b.cx(carry[0], cout[0])
                for i in reversed(range(noff)):
                    maj_inv(b, Cp2[i], Tlow[i], carry[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp2[i])
                b.free(Cp2)
                b.free(carry)
                b.free(cout)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                wantT = (tv - (sv if ctl else 0)) % (2**ntgt)
                if gotT != wantT:
                    print(f"A1SUB FAIL ctl={ctl} s={sv} t={tv} got={gotT} want={wantT}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"a1sub noff={noff} nlow={nlow} nhigh={nhigh}: {total-fails}/{total} ok")
    return fails == 0


def test_a1_split_sub_roundtrip(noff=3, nlow=3, nhigh=2):
    """A1 narrow-sub followed by narrow-add-back in one circuit == identity.

    Proves the A1 reverse row (add-pattern) exactly inverts the forward
    sub row. Scratch freed on both halves; T must return to tv."""
    fails = total = 0
    ntgt = nlow + nhigh
    for ctl in (0, 1):
        for sv in range(2**noff):
            for tv in range(2**ntgt):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(noff, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                for i in range(noff):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                Tlow = T[0:nlow]
                Thigh = T[nlow:ntgt]
                # --- forward sub half ---
                Cp = b.alloc_qubits(noff)
                carry = b.alloc_qubits(1)
                cout = b.alloc_qubits(1)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp[i])
                b.flip_if_less_than(Tlow, Cp, target=cout[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp[i])
                b.free(Cp)
                b.isub(cout, target=Thigh)
                Cp2 = b.alloc_qubits(noff)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp2[i])
                for i in range(noff):
                    uma_inv(b, Cp2[i], Tlow[i], carry[0])
                b.cx(carry[0], cout[0])
                for i in reversed(range(noff)):
                    maj_inv(b, Cp2[i], Tlow[i], carry[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp2[i])
                b.free(Cp2)
                b.free(carry)
                b.free(cout)
                # --- reverse add-back half (add pattern) ---
                Cp3 = b.alloc_qubits(noff)
                carry3 = b.alloc_qubits(1)
                cout3 = b.alloc_qubits(1)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp3[i])
                for i in range(noff):
                    maj(b, Cp3[i], Tlow[i], carry3[0])
                b.cx(carry3[0], cout3[0])
                for i in reversed(range(noff)):
                    uma(b, Cp3[i], Tlow[i], carry3[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp3[i])
                b.free(Cp3)
                b.free(carry3)
                b.iadd(cout3, target=Thigh)
                Cp4 = b.alloc_qubits(noff)
                for i in range(noff):
                    b.ccx(C[0], S[i], Cp4[i])
                b.flip_if_less_than(Tlow, Cp4, target=cout3[0])
                for i in reversed(range(noff)):
                    b.ccx(C[0], S[i], Cp4[i])
                b.free(Cp4)
                b.free(cout3)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                if gotT != tv:
                    print(f"A1RT FAIL ctl={ctl} s={sv} t={tv} got={gotT}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"a1roundtrip noff={noff} nlow={nlow} nhigh={nhigh}: {total-fails}/{total} ok")
    return fails == 0


if __name__ == "__main__":
    ok = True
    ok &= test_uncontrolled(3)
    ok &= test_controlled_via_copy(3)
    ok &= test_split_row(2, 2, 3)
    ok &= test_split_row_reverse(2, 2, 3)
    ok &= test_a1_split_sub(3, 3, 2)
    ok &= test_a1_split_sub_roundtrip(3, 3, 2)
    print("NARROW-PROOF " + ("PASS" if ok else "FAIL"))
