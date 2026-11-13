"""Census of the AND terms inside the prefix arithmetic block.

For [650:7031) the circuit is a pure permutation, so:
  * every CCX is "compute one AND of two current qubit values into a fresh
    target, then fan it out with CX" -- count the terms, their fan-out and
    whether any control pair repeats (a repeated pair would be mergeable);
  * deleting a CCX changes the block's function on the reachable domain iff the
    term is load-bearing.
Reachable domain = outputs of ops [0:650) for a sample of x.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from qsim import Sim, op_table, run  # noqa: E402

MAX_X = 3 * (2**10 - 2) ** 2


def block_out(table, nq, lo, hi, states, skip=None):
    sim = Sim(len(states), n_qubits=nq)
    sim.v = states.astype(np.uint64).copy()
    for idx in range(lo, hi):
        if idx == skip:
            continue
        run(sim, table[idx:idx + 1])
    return sim.v


def main() -> None:
    path = Path(sys.argv[1])
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    table, nq = op_table(path)
    rng = np.random.default_rng(21)
    xs = np.unique(np.concatenate([np.arange(1, 1501, dtype=np.uint64),
                                   rng.integers(1501, MAX_X, size=500, dtype=np.uint64)]))

    pre = Sim(len(xs), n_qubits=nq)
    pre.v = xs.copy()
    run(pre, table, limit=lo)
    states = pre.v.copy()

    ccx = [(i, table[i]) for i in range(lo, hi) if table[i][0] == "CCX"]
    print(f"block [{lo}:{hi}) CCX count = {len(ccx)}")
    terms = []
    for i, (kind, args, conds) in ccx:
        q = [int(a[1:]) for a in args if a.startswith("q")]
        terms.append((i, q[0], q[1], q[2]))
    pairs = Counter((a, b) for _, a, b, _ in terms)
    dup = {k: v for k, v in pairs.items() if v > 1}
    print(f"distinct control pairs = {len(pairs)}; repeated pairs = {len(dup)} {list(dup.items())[:6]}")
    print(f"distinct targets = {len({t for *_, t in terms})}")
    print("control-pair repeat histogram:", Counter(pairs.values()))

    # fan-out: CX's between this CCX and the next CCX that read the target
    bounds = [t[0] for t in terms] + [hi]
    fan = []
    for k, (i, a, b, t) in enumerate(terms):
        n = 0
        ctrls = set()
        for j in range(i + 1, bounds[k + 1]):
            kind, args, conds = table[j]
            if kind in ("CX", "CCX", "CSWAP", "SWAP"):
                q = [int(x[1:]) for x in args if x.startswith("q")]
                if q and q[0] == t:
                    n += 1
                    ctrls.update(q[1:])
        fan.append((n, len(ctrls)))
    print("fan-out per AND: min/median/max =",
          min(f for f, _ in fan), sorted(f for f, _ in fan)[len(fan) // 2], max(f for f, _ in fan))
    print("total CX fan-out ops =", sum(f for f, _ in fan))

    # load-bearing: delete each CCX, compare block output
    base = block_out(table, nq, lo, hi, states)
    dead = []
    for i, a, b, t in terms:
        alt = block_out(table, nq, lo, hi, states, skip=i)
        if np.array_equal(alt, base):
            dead.append(i)
    print(f"CCX that are no-ops on the reachable domain: {len(dead)} {dead[:10]}")


if __name__ == "__main__":
    main()
