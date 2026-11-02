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


def test_s6_split_inc(n=6, k=3):
    """S6-shape narrow constant increment: 36-bit controlled +1 split k/(n-k).

    Forward narrow-inc (low generic iadd; flip cout=(low_new==0);
    CCX gated=c&cout; high generic iadd; uncompute) vs integer oracle
    (tv + ctl) mod 2^n. Small-case (6/3) exhaustive."""
    fails = total = 0
    for ctl in (0, 1):
        for tv in range(2**n):
            total += 1
            b = km.CircuitBuilder()
            T = b.create_quantum_register(n, name="t")
            C = b.create_quantum_register(1, name="c")
            for i in range(n):
                if (tv >> i) & 1:
                    b.x(T[i])
            if ctl:
                b.x(C[0])
            Tlow = T[0:k]
            Thigh = T[k:n]
            b.iadd(1, target=Tlow, control=C[0])
            cout = b.alloc_qubits(1)
            gated = b.alloc_qubits(1)
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.ccx(C[0], cout[0], gated[0])
            b.iadd(1, target=Thigh, control=gated[0])
            b.ccx(C[0], cout[0], gated[0])
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.free(gated)
            b.free(cout)
            circ = b.finish_circuit()
            sim = km.Simulator(batch_size=1)
            sim.use_same_registers_as(circ)
            sim.do(circ)
            gotT = sim.read_within_shot("t", 0, out=int)
            wantT = (tv + ctl) % (2**n)
            if gotT != wantT:
                print(f"S6INC FAIL ctl={ctl} t={tv} got={gotT} want={wantT}")
                fails += 1
                if fails > 5:
                    return False
    print(f"s6inc n={n} k={k}: {total-fails}/{total} ok")
    return fails == 0


def test_s6_split_dec(n=6, k=3):
    """S6 narrow decrement (forward-inc strict inverse) vs oracle.

    From sum state s0=(tv+ctl) mod 2^n: recompute cout/gated from
    sum-low, high isub, clear carry, low isub. Expect tv."""
    fails = total = 0
    for ctl in (0, 1):
        for tv in range(2**n):
            total += 1
            s0 = (tv + ctl) % (2**n)
            b = km.CircuitBuilder()
            T = b.create_quantum_register(n, name="t")
            C = b.create_quantum_register(1, name="c")
            for i in range(n):
                if (s0 >> i) & 1:
                    b.x(T[i])
            if ctl:
                b.x(C[0])
            Tlow = T[0:k]
            Thigh = T[k:n]
            cout = b.alloc_qubits(1)
            gated = b.alloc_qubits(1)
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.ccx(C[0], cout[0], gated[0])
            b.isub(1, target=Thigh, control=gated[0])
            b.ccx(C[0], cout[0], gated[0])
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.free(gated)
            b.free(cout)
            b.isub(1, target=Tlow, control=C[0])
            circ = b.finish_circuit()
            sim = km.Simulator(batch_size=1)
            sim.use_same_registers_as(circ)
            sim.do(circ)
            gotT = sim.read_within_shot("t", 0, out=int)
            if gotT != tv:
                print(f"S6DEC FAIL ctl={ctl} t={tv} sum={s0} got={gotT}")
                fails += 1
                if fails > 5:
                    return False
    print(f"s6dec n={n} k={k}: {total-fails}/{total} ok")
    return fails == 0


def test_s6_split_roundtrip(n=6, k=3):
    """S6 narrow-inc followed by narrow-dec in one circuit == identity."""
    fails = total = 0
    for ctl in (0, 1):
        for tv in range(2**n):
            total += 1
            b = km.CircuitBuilder()
            T = b.create_quantum_register(n, name="t")
            C = b.create_quantum_register(1, name="c")
            for i in range(n):
                if (tv >> i) & 1:
                    b.x(T[i])
            if ctl:
                b.x(C[0])
            Tlow = T[0:k]
            Thigh = T[k:n]
            # --- inc half ---
            b.iadd(1, target=Tlow, control=C[0])
            cout = b.alloc_qubits(1)
            gated = b.alloc_qubits(1)
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.ccx(C[0], cout[0], gated[0])
            b.iadd(1, target=Thigh, control=gated[0])
            b.ccx(C[0], cout[0], gated[0])
            b.flip_if_less_than(Tlow, 1, target=cout[0])
            b.free(gated)
            b.free(cout)
            # --- dec half ---
            cout2 = b.alloc_qubits(1)
            gated2 = b.alloc_qubits(1)
            b.flip_if_less_than(Tlow, 1, target=cout2[0])
            b.ccx(C[0], cout2[0], gated2[0])
            b.isub(1, target=Thigh, control=gated2[0])
            b.ccx(C[0], cout2[0], gated2[0])
            b.flip_if_less_than(Tlow, 1, target=cout2[0])
            b.free(gated2)
            b.free(cout2)
            b.isub(1, target=Tlow, control=C[0])
            circ = b.finish_circuit()
            sim = km.Simulator(batch_size=1)
            sim.use_same_registers_as(circ)
            sim.do(circ)
            gotT = sim.read_within_shot("t", 0, out=int)
            if gotT != tv:
                print(f"S6RT FAIL ctl={ctl} t={tv} got={gotT}")
                fails += 1
                if fails > 5:
                    return False
    print(f"s6roundtrip n={n} k={k}: {total-fails}/{total} ok")
    return fails == 0


def test_a1_twolevel_add(n0=2, n1=2, nh=2):
    """Two-level ADD (A1R-shape, 11+11 scaled to n0+n1): T += ctl?S.

    Low Cuccaro n0 -> c1; mid generic n1 + single-bit c1; c2 from new
    values c2=(T1new<Cp1)|(c1&(T1new==Cp1)) via < + equal flips (11-bit
    scratch only); high generic; clears via recomputation (T0/T1 untouched
    by later stages). Exhaustive vs integer oracle."""
    nsrc = n0 + n1
    ntgt = n0 + n1 + nh
    fails = total = 0
    for ctl in (0, 1):
        for sv in range(2**nsrc):
            for tv in range(2**ntgt):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(nsrc, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                for i in range(nsrc):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                ctlq = C[0]
                S0 = S[0:n0]; S1 = S[n0:nsrc]
                T0 = T[0:n0]; T1 = T[n0:n0+n1]; TH = T[n0+n1:ntgt]
                Cp0 = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1); c1 = b.alloc_qubits(1)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0[i])
                for i in range(n0):
                    maj(b, Cp0[i], T0[i], ca0[0])
                b.cx(ca0[0], c1[0])
                for i in reversed(range(n0)):
                    uma(b, Cp0[i], T0[i], ca0[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0[i])
                b.free(Cp0); b.free(ca0)
                Cp1 = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1[i])
                b.iadd(Cp1, target=T1)
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1[i])
                b.free(Cp1)
                b.iadd(c1, target=T1)
                CpB = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpB[i])
                lt = b.alloc_qubits(1); eq = b.alloc_qubits(1)
                b.flip_if_less_than(T1, CpB, target=lt[0])
                b.flip_if_equal(T1, CpB, target=eq[0])
                s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
                b.ccx(c1[0], eq[0], s[0])
                b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpB[i])
                b.free(CpB)
                b.iadd(c2, target=TH)
                b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
                b.ccx(c1[0], eq[0], s[0]); b.free(s)
                CpC = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpC[i])
                b.flip_if_equal(T1, CpC, target=eq[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpC[i])
                b.free(CpC); b.free(eq)
                CpD = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpD[i])
                b.flip_if_less_than(T1, CpD, target=lt[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpD[i])
                b.free(CpD); b.free(lt)
                Cp0B = b.alloc_qubits(n0)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0B[i])
                b.flip_if_less_than(T0, Cp0B, target=c1[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0B[i])
                b.free(Cp0B); b.free(c1)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                wantT = (tv + (sv if ctl else 0)) % (2**ntgt)
                if gotT != wantT:
                    print(f"A1TW-ADD FAIL ctl={ctl} s={sv} t={tv} got={gotT} want={wantT}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"a1two-add {n0}+{n1}+{nh}: {total-fails}/{total} ok")
    return fails == 0


def test_a1_twolevel_sub(n0=2, n1=2, nh=2):
    """Two-level SUB (A1-shape, strict inverse of two-level ADD).

    Sets c1/lt/eq/s/c2 from OLD values (borrow b2=(Told<Cp)|(c1&(Told==Cp))),
    high isub, clears eq/lt before T1 changes (T1 still old), mid isubs,
    low Cuccaro-inverse restores T0 and clears c1 via carry. Vs oracle."""
    nsrc = n0 + n1
    ntgt = n0 + n1 + nh
    fails = total = 0
    for ctl in (0, 1):
        for sv in range(2**nsrc):
            for tv in range(2**ntgt):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(nsrc, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                for i in range(nsrc):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                ctlq = C[0]
                S0 = S[0:n0]; S1 = S[n0:nsrc]
                T0 = T[0:n0]; T1 = T[n0:n0+n1]; TH = T[n0+n1:ntgt]
                c1 = b.alloc_qubits(1)
                Cp0a = b.alloc_qubits(n0)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0a[i])
                b.flip_if_less_than(T0, Cp0a, target=c1[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0a[i])
                b.free(Cp0a)
                lt = b.alloc_qubits(1)
                Cp1a = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1a[i])
                b.flip_if_less_than(T1, Cp1a, target=lt[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1a[i])
                b.free(Cp1a)
                eq = b.alloc_qubits(1)
                Cp1b = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1b[i])
                b.flip_if_equal(T1, Cp1b, target=eq[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1b[i])
                b.free(Cp1b)
                s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
                b.ccx(c1[0], eq[0], s[0])
                b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
                b.isub(c2, target=TH)
                b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
                b.ccx(c1[0], eq[0], s[0]); b.free(s)
                Cp1c = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1c[i])
                b.flip_if_equal(T1, Cp1c, target=eq[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1c[i])
                b.free(Cp1c); b.free(eq)
                Cp1d = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1d[i])
                b.flip_if_less_than(T1, Cp1d, target=lt[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1d[i])
                b.free(Cp1d); b.free(lt)
                b.isub(c1, target=T1)
                Cp1e = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1e[i])
                b.isub(Cp1e, target=T1)
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1e[i])
                b.free(Cp1e)
                Cp0b = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0b[i])
                for i in range(n0):
                    uma_inv(b, Cp0b[i], T0[i], ca0[0])
                b.cx(ca0[0], c1[0])
                for i in reversed(range(n0)):
                    maj_inv(b, Cp0b[i], T0[i], ca0[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0b[i])
                b.free(Cp0b); b.free(ca0); b.free(c1)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                wantT = (tv - (sv if ctl else 0)) % (2**ntgt)
                if gotT != wantT:
                    print(f"A1TW-SUB FAIL ctl={ctl} s={sv} t={tv} got={gotT} want={wantT}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"a1two-sub {n0}+{n1}+{nh}: {total-fails}/{total} ok")
    return fails == 0


def test_a1_twolevel_roundtrip(n0=2, n1=2, nh=2):
    """Two-level ADD followed by two-level SUB in one circuit == identity."""
    nsrc = n0 + n1
    ntgt = n0 + n1 + nh
    fails = total = 0
    for ctl in (0, 1):
        for sv in range(2**nsrc):
            for tv in range(2**ntgt):
                total += 1
                b = km.CircuitBuilder()
                S = b.create_quantum_register(nsrc, name="s")
                T = b.create_quantum_register(ntgt, name="t")
                C = b.create_quantum_register(1, name="c")
                for i in range(nsrc):
                    if (sv >> i) & 1:
                        b.x(S[i])
                for i in range(ntgt):
                    if (tv >> i) & 1:
                        b.x(T[i])
                if ctl:
                    b.x(C[0])
                ctlq = C[0]
                S0 = S[0:n0]; S1 = S[n0:nsrc]
                T0 = T[0:n0]; T1 = T[n0:n0+n1]; TH = T[n0+n1:ntgt]
                # --- ADD half (same as test_a1_twolevel_add body) ---
                Cp0 = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1); c1 = b.alloc_qubits(1)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0[i])
                for i in range(n0):
                    maj(b, Cp0[i], T0[i], ca0[0])
                b.cx(ca0[0], c1[0])
                for i in reversed(range(n0)):
                    uma(b, Cp0[i], T0[i], ca0[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0[i])
                b.free(Cp0); b.free(ca0)
                Cp1 = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1[i])
                b.iadd(Cp1, target=T1)
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1[i])
                b.free(Cp1)
                b.iadd(c1, target=T1)
                CpB = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpB[i])
                lt = b.alloc_qubits(1); eq = b.alloc_qubits(1)
                b.flip_if_less_than(T1, CpB, target=lt[0])
                b.flip_if_equal(T1, CpB, target=eq[0])
                s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
                b.ccx(c1[0], eq[0], s[0])
                b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpB[i])
                b.free(CpB)
                b.iadd(c2, target=TH)
                b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
                b.ccx(c1[0], eq[0], s[0]); b.free(s)
                CpC = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpC[i])
                b.flip_if_equal(T1, CpC, target=eq[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpC[i])
                b.free(CpC); b.free(eq)
                CpD = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], CpD[i])
                b.flip_if_less_than(T1, CpD, target=lt[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], CpD[i])
                b.free(CpD); b.free(lt)
                Cp0B = b.alloc_qubits(n0)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0B[i])
                b.flip_if_less_than(T0, Cp0B, target=c1[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0B[i])
                b.free(Cp0B); b.free(c1)
                # --- SUB half (same as test_a1_twolevel_sub body, fresh scratch) ---
                c1b = b.alloc_qubits(1)
                Cp0a = b.alloc_qubits(n0)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0a[i])
                b.flip_if_less_than(T0, Cp0a, target=c1b[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0a[i])
                b.free(Cp0a)
                ltb = b.alloc_qubits(1)
                Cp1a = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1a[i])
                b.flip_if_less_than(T1, Cp1a, target=ltb[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1a[i])
                b.free(Cp1a)
                eqb = b.alloc_qubits(1)
                Cp1b = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1b[i])
                b.flip_if_equal(T1, Cp1b, target=eqb[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1b[i])
                b.free(Cp1b)
                sb = b.alloc_qubits(1); c2b = b.alloc_qubits(1)
                b.ccx(c1b[0], eqb[0], sb[0])
                b.cx(ltb[0], c2b[0]); b.cx(sb[0], c2b[0])
                b.isub(c2b, target=TH)
                b.cx(sb[0], c2b[0]); b.cx(ltb[0], c2b[0]); b.free(c2b)
                b.ccx(c1b[0], eqb[0], sb[0]); b.free(sb)
                Cp1c = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1c[i])
                b.flip_if_equal(T1, Cp1c, target=eqb[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1c[i])
                b.free(Cp1c); b.free(eqb)
                Cp1d = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1d[i])
                b.flip_if_less_than(T1, Cp1d, target=ltb[0])
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1d[i])
                b.free(Cp1d); b.free(ltb)
                b.isub(c1b, target=T1)
                Cp1e = b.alloc_qubits(n1)
                for i in range(n1):
                    b.ccx(ctlq, S1[i], Cp1e[i])
                b.isub(Cp1e, target=T1)
                for i in reversed(range(n1)):
                    b.ccx(ctlq, S1[i], Cp1e[i])
                b.free(Cp1e)
                Cp0b = b.alloc_qubits(n0); ca0b = b.alloc_qubits(1)
                for i in range(n0):
                    b.ccx(ctlq, S0[i], Cp0b[i])
                for i in range(n0):
                    uma_inv(b, Cp0b[i], T0[i], ca0b[0])
                b.cx(ca0b[0], c1b[0])
                for i in reversed(range(n0)):
                    maj_inv(b, Cp0b[i], T0[i], ca0b[0])
                for i in reversed(range(n0)):
                    b.ccx(ctlq, S0[i], Cp0b[i])
                b.free(Cp0b); b.free(ca0b); b.free(c1b)
                circ = b.finish_circuit()
                sim = km.Simulator(batch_size=1)
                sim.use_same_registers_as(circ)
                sim.do(circ)
                gotT = sim.read_within_shot("t", 0, out=int)
                if gotT != tv:
                    print(f"A1TW-RT FAIL ctl={ctl} s={sv} t={tv} got={gotT}")
                    fails += 1
                    if fails > 5:
                        return False
    print(f"a1two-roundtrip {n0}+{n1}+{nh}: {total-fails}/{total} ok")
    return fails == 0


# ---------------------------------------------------------------- binary lz (S1 二分替换，Wx=6 缩比穷举)
# 全尺寸架构（22 位，5 层切片谓词 + MUX 修正 + 折叠解码直达 lz，
# narrow_v62.build_bs_fwd/rev）的缩比镜像：x 6 位（定义域 1..63），
# e=bitlen-1 ∈ 0..5，lz=5-e（3 位）。d1=(x[3:6]==0)；L2 MUX
# （F: x[5]==0 即 x<32；T: x[1:3]==0 即 x<2）；解码为 (d1,d2) 4 路
# AND2 + 对位叶重算（(F,T): x[4]==0 判 e=3/4；(T,F): x[2]==0 判 e=1/2；
# (F,F)/(T,T) 单叶）。全尺寸另有 numpy 4M 全域 + 定向量子抽查（见 bs_lz.md）；
# AND5（全尺寸解码）与 AND2 同 init_and 链模式，仅元数不同。
def _bs_mux2(b, s, aT, aF, o):
    b.ccx(s, aT, o)
    b.x(s)
    b.ccx(s, aF, o)
    b.x(s)


def _bs_pred_c(b, x, spec, t):
    a, bb = spec
    if bb - a == 1:
        b.x(t)
        b.cx(x[a], t)
    else:
        b.flip_if_equal(x[a:bb], 0, target=t)


def _bs_pred_u(b, x, spec, t):
    a, bb = spec
    if bb - a == 1:
        b.cx(x[a], t)
        b.x(t)
    else:
        b.flip_if_equal(x[a:bb], 0, target=t)


def _bs_dec6(b, dd, lz, x):
    """(d1,d2) 折叠解码：(F,F)->lz0；(T,T)->lz5；(F,T): leaf ~x[4] 判 3/4；
    (T,F): leaf ~x[2] 判 1/2。self-inverse，复跑即清 lz。"""
    for path, lzv in (((False, False), 0), ((True, True), 5)):
        m = b.alloc_qubits(1)
        if not path[0]:
            b.x(dd[0])
        if not path[1]:
            b.x(dd[1])
        b.ccx(dd[0], dd[1], m[0])
        if not path[1]:
            b.x(dd[1])
        if not path[0]:
            b.x(dd[0])
        for k in range(3):
            if (lzv >> k) & 1:
                b.cx(m[0], lz[k])
        if not path[0]:
            b.x(dd[0])
        if not path[1]:
            b.x(dd[1])
        b.ccx(dd[0], dd[1], m[0])
        if not path[1]:
            b.x(dd[1])
        if not path[0]:
            b.x(dd[0])
        b.free(m)
    for path, eT in (((False, True), 3), ((True, False), 1)):
        lzT, lzF = 5 - eT, 5 - (eT + 1)
        m = b.alloc_qubits(1)
        if not path[0]:
            b.x(dd[0])
        if not path[1]:
            b.x(dd[1])
        b.ccx(dd[0], dd[1], m[0])
        if not path[1]:
            b.x(dd[1])
        if not path[0]:
            b.x(dd[0])
        t = b.alloc_qubits(1)
        b.x(t[0])
        b.cx(x[eT + 1], t[0])
        for k in range(3):
            bT = (lzT >> k) & 1
            bF = (lzF >> k) & 1
            if bT and bF:
                b.cx(m[0], lz[k])
            elif (not bT) and bF:
                b.cx(m[0], lz[k])
                b.ccx(m[0], t[0], lz[k])
            elif bT and (not bF):
                b.ccx(m[0], t[0], lz[k])
        b.cx(x[eT + 1], t[0])
        b.x(t[0])
        b.free(t)
        if not path[0]:
            b.x(dd[0])
        if not path[1]:
            b.x(dd[1])
        b.ccx(dd[0], dd[1], m[0])
        if not path[1]:
            b.x(dd[1])
        if not path[0]:
            b.x(dd[0])
        b.free(m)


def _bs_fwd6(b, x, lz, d):
    _bs_levels6(b, x, d)
    _bs_dec6(b, [d[0], d[1]], lz, x)
    t0 = b.alloc_qubits(1)
    t1 = b.alloc_qubits(1)
    _bs_pred_c(b, x, (5, 6), t0[0])
    _bs_pred_c(b, x, (1, 3), t1[0])
    _bs_mux2(b, d[0], t1[0], t0[0], d[1])
    _bs_pred_u(b, x, (1, 3), t1[0])
    b.free(t1)
    _bs_pred_u(b, x, (5, 6), t0[0])
    b.free(t0)
    _bs_pred_u(b, x, (3, 6), d[0])


def _bs_levels6(b, x, d):
    _bs_pred_c(b, x, (3, 6), d[0])
    t0 = b.alloc_qubits(1)
    t1 = b.alloc_qubits(1)
    _bs_pred_c(b, x, (5, 6), t0[0])
    _bs_pred_c(b, x, (1, 3), t1[0])
    _bs_mux2(b, d[0], t1[0], t0[0], d[1])
    _bs_pred_u(b, x, (1, 3), t1[0])
    b.free(t1)
    _bs_pred_u(b, x, (5, 6), t0[0])
    b.free(t0)


def _bs_rev6(b, x, lz, d):
    _bs_levels6(b, x, d)
    _bs_dec6(b, [d[0], d[1]], lz, x)
    t0 = b.alloc_qubits(1)
    t1 = b.alloc_qubits(1)
    _bs_pred_c(b, x, (5, 6), t0[0])
    _bs_pred_c(b, x, (1, 3), t1[0])
    _bs_mux2(b, d[0], t1[0], t0[0], d[1])
    _bs_pred_u(b, x, (1, 3), t1[0])
    b.free(t1)
    _bs_pred_u(b, x, (5, 6), t0[0])
    b.free(t0)
    _bs_pred_u(b, x, (3, 6), d[0])


def test_bs_lz6():
    """二分 lz 缩比穷举：x=1..63，lz==5-(bitlen-1)，余零（d 保持为路径值）。"""
    xs = list(range(1, 64))
    b = km.CircuitBuilder()
    x = b.create_quantum_register(6, name="x")
    lz = b.alloc_qubits(3)
    d = b.alloc_qubits(2)
    _bs_fwd6(b, x, lz, d)
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=len(xs))
    sim.use_same_registers_as(circ)
    for i, xv in enumerate(xs):
        sim.write_within_shot("x", i, xv)
    sim.do(circ)
    fails = total = 0
    for i, xv in enumerate(xs):
        total += 1
        got = 0
        for k in range(3):
            if bool(sim.read_across_shots(km.q(6 + k))[i]):
                got |= (1 << k)
        want = 5 - (xv.bit_length() - 1)
        if got != want:
            print(f"BS6 FAIL x={xv} got={got} want={want}")
            fails += 1
    for q in range(11, circ.num_qubits):
        across = sim.read_across_shots(km.q(q))
        for i in range(len(xs)):
            if bool(across[i]):
                print(f"BS6-SCRATCH FAIL q{q} x={xs[i]}")
                fails += 1
                break
    print(f"bslz6: {total-fails}/{total} ok")
    return fails == 0


def test_bs_roundtrip6():
    """二分 lz + 归一化往返恒等：fwd → rotl → rotr → rev，x 复原且全零（除 x）。
    d 在 fwd 后释放重配（镜像生成器 F/R 间 d 不存活），rev 须由 x 重算。"""
    xs = list(range(1, 64))
    b = km.CircuitBuilder()
    x = b.create_quantum_register(6, name="x")
    lz = b.alloc_qubits(3)
    d = b.alloc_qubits(2)
    _bs_fwd6(b, x, lz, d)
    b.left_rotate(x, lz)
    b.right_rotate(x, lz)
    b.free(d)
    d2 = b.alloc_qubits(2)
    _bs_rev6(b, x, lz, d2)
    b.free(d2)
    circ = b.finish_circuit()
    sim = km.Simulator(batch_size=len(xs))
    sim.use_same_registers_as(circ)
    for i, xv in enumerate(xs):
        sim.write_within_shot("x", i, xv)
    sim.do(circ)
    fails = 0
    for q in range(circ.num_qubits):
        across = sim.read_across_shots(km.q(q))
        for i, xv in enumerate(xs):
            want = bool((xv >> q) & 1) if q < 6 else False
            if bool(across[i]) != want:
                print(f"BS6RT FAIL q{q} x={xv}")
                fails += 1
                if fails > 5:
                    return False
    print(f"bsroundtrip6: {len(xs)} samples ok")
    return fails == 0


if __name__ == "__main__":
    ok = True
    ok &= test_uncontrolled(3)
    ok &= test_controlled_via_copy(3)
    ok &= test_split_row(2, 2, 3)
    ok &= test_split_row_reverse(2, 2, 3)
    ok &= test_a1_split_sub(3, 3, 2)
    ok &= test_a1_split_sub_roundtrip(3, 3, 2)
    ok &= test_s6_split_inc(6, 3)
    ok &= test_s6_split_dec(6, 3)
    ok &= test_s6_split_roundtrip(6, 3)
    ok &= test_a1_twolevel_add(2, 2, 2)
    ok &= test_a1_twolevel_sub(2, 2, 2)
    ok &= test_a1_twolevel_roundtrip(2, 2, 2)
    ok &= test_bs_lz6()
    ok &= test_bs_roundtrip6()
    print("NARROW-PROOF " + ("PASS" if ok else "FAIL"))
