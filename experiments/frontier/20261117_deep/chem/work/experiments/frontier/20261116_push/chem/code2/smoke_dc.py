"""Single-loader correctness smoke test for emit_delta circuits (LOCAL, light).

For loader k and a handful of addresses: set selection + word registers to the
prev-batch words, run the .kmx forward, compare word registers to cur-batch
words, and check workspace-clean + selection-preserved.

Light: a few addresses only (classical-reversible sim). Full 1232-address
sweep runs on Kaggle CPU.
"""
import sys
import numpy as np
import kickmix as km
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORDS = np.load('/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds/submission.npz',
                allow_pickle=False)['angle_words'].astype(np.uint8)


def complete(W):
    a = np.zeros((1232, 75), dtype=np.uint8)
    a[:1220] = W
    f = a.reshape(77, 16, 75)
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    for b in range(7):
        for h in range(77):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    f[76, 4:] = 0
    for b in range(7):
        for h in range(77):
            if h & (1 << b):
                f[h] ^= f[h ^ (1 << b)]
    for b in range(4):
        for l in range(16):
            if l & (1 << b):
                f[:, l] ^= f[:, l ^ (1 << b)]
    return a


Wc = complete(WORDS)


def test_loader(k, kmx, addresses):
    circ = km.Circuit.from_file(str(kmx))
    nq = circ.num_qubits
    prev = Wc[:, 5 * k - 5:5 * k]
    cur = Wc[:, 5 * k:5 * k + 5]
    ok = True
    for a in addresses:
        sim = km.Simulator(batch_size=1)
        sim.write_within_shot(km.r('r0'), 0, int(a))
        for j in range(5):
            v = int(prev[a, j])
            sim.write_within_shot(km.r(f'r{j + 1}'), 0, v)
        sim.do(circ)
        for j in range(5):
            got = int(sim.read_within_shot(km.r(f'r{j + 1}'), 0))
            if got != int(cur[a, j]):
                print(f'k={k} addr={a} word{j}: got {got:#x} want {int(cur[a, j]):#x}')
                ok = False
        sel = int(sim.read_within_shot(km.r('r0'), 0))
        if sel != int(a):
            print(f'k={k} addr={a}: selection not preserved ({sel} != {a})')
            ok = False
        # workspace clean: qubits 51..nq-1 must be 0
        for q in range(51, nq):
            if bool(sim.read_within_shot(km.q(q), 0)):
                print(f'k={k} addr={a}: workspace q{q} dirty')
                ok = False
                break
        # phase: HMR-based uncompute must not flip phase; check via read_shot_phase?
    print(f'k={k}: {"PASS" if ok else "FAIL"} on {len(addresses)} addresses '
          f'({circ.operation_statistics()})')
    return ok


if __name__ == '__main__':
    k = int(sys.argv[1])
    kmx = DIR / 'build_dc' / f'angle_k_{k}.kmx'
    # spread across low/high blocks + the off-domain slice
    addrs = [0, 1, 15, 16, 100, 511, 512, 1000, 1219, 1220, 1231]
    sys.exit(0 if test_loader(k, kmx, addrs) else 1)
