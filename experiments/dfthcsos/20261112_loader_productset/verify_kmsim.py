"""Real kickmix simulation (stateful, 1,220 addresses, no symbolic model) of the slimmed
loaders: the words must equal the originals on every real address, the selection must be
unchanged and every workspace qubit must end at 0.

Usage: python verify_kmsim.py [k ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import kickmix as km

sys.path.insert(0, str(Path(__file__).parent))

ORIG = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
            '20261112_loader_re/kmx_maoxin')
SLIM = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/dfthcsos/artifacts/'
            '20261112_loader_productset/kmx_slim')
N = 1220
NALL = 2048
SEL = [km.q(i) for i in range(11)]
WORD = [km.q(i) for i in range(11, 51)]
WS = [km.q(i) for i in range(51, 128)]


def run(circ: km.Circuit, seed: int = 20261112):
    sim = km.Simulator(batch_size=NALL, debug_print=False, seed=seed, counting_operations=True)
    sim.use_same_registers_as(circ)
    addr = np.arange(NALL, dtype=np.int64)
    selbits = ((addr[None, :] >> np.arange(11)[:, None]) & 1).astype(bool)
    sim.write_across_shots(km.array(SEL), selbits)
    sim.do(circ)
    w = sim.read_across_shots(km.array(WORD))[:, :N].astype(np.uint8)
    s = sim.read_across_shots(km.array(SEL))[:, :N].astype(np.uint8)
    ws = sim.read_across_shots(km.array(WS))[:, :N].astype(np.uint8)
    return w, s, ws, circ.operation_statistics().num_toffoli_like


def main() -> None:
    ks = [int(x) for x in sys.argv[1:]] or list(range(15))
    all_ok = True
    tots = [0, 0]
    for k in ks:
        co = km.Circuit.from_file(ORIG / f'angle_k_{k}.kmx', format='kmx')
        cs = km.Circuit.from_file(SLIM / f'angle_k_{k}.kmx', format='kmx')
        wo, so, wso, to = run(co)
        ws_, ss, wss, ts = run(cs)
        eq = np.array_equal(wo, ws_)
        clean_orig = not wso.any()
        clean_slim = not wss.any()
        ok = eq and np.array_equal(so, ss) and clean_slim
        all_ok &= bool(ok)
        tots[0] += to
        tots[1] += ts
        print(f'k={k:2d}: CCX {to:4d} -> {ts:4d} | words_equal={eq} selection_unchanged='
              f'{np.array_equal(so, ss)} workspace_clean orig={clean_orig} slim={clean_slim}'
              f' | {"OK" if ok else "FAIL"}')
    print(f'\n{"ALL OK" if all_ok else "FAILURES"}   T {tots[0]} -> {tots[1]}')
    lam = 46.9074
    for T in tots:
        print(f'  T={T:5d} -> T_total={2 * T + 6662:6d} -> cost={lam * (2 * T + 6662) * 427 / 1e6:.2f}M')


if __name__ == '__main__':
    main()
