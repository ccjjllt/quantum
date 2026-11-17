"""Final tables for the chem shape note: precision-feasible cost frontier,
inner-temp pocket census, and the exact walls.  Pure formulas (see shape_arith.py).
"""
from __future__ import annotations

import sys

sys.path.insert(0, "experiments/frontier/20261117_deep/chem")
import shape_arith as S  # noqa: E402

GRID = []
for R in range(4, 17):
    for B in range(32, 385):
        for C in range(24, 129):
            try:
                s = S.shape(R, B, C)
            except Exception:
                continue
            if not s["cap_ok"]:
                continue
            s["floor"] = S.floor_mha(s["K"])
            s["gate"] = S.gate_c(s["rows"])
            s["rho"] = S.rho_law(s["b_over_c"])
            s["e2"] = s["rho"] * s["floor"]
            GRID.append(s)
print(f"grid: {len(GRID)} cap-legal shapes")


def rank(feas, model, n=16):
    out = []
    for s in feas:
        L = S.loaders(s["rows"], model)
        T = 2 * L + s["T_h"]
        out.append((S.cost(T, s["Q"]), T, L, s))
    out.sort(key=lambda t: t[0])
    return out[:n]


print("\n### A1. precision-feasible frontier (rho law), ranked by cost\n")
feas = [s for s in GRID if s["e2"] <= s["gate"]]
print(f"feasible shapes: {len(feas)}")
hdr = (f"{'#':>2} {'costM':>7} {'dGM':>6} {'R':>2} {'B':>3} {'C':>3} {'rows':>4} {'K':>3} "
       f"{'B/C':>5} {'Th':>5} {'Q':>4} {'floor':>5} {'e2p':>5} {'gate':>5} "
       f"{'Lcut':>5} {'Tcut':>6} {'costCut':>7} {'costCons':>8} {'costLin':>7}")
print(hdr)
for i, (cc, T, L, s) in enumerate(rank(feas, "cut")):
    Tc = 2 * S.loaders(s["rows"], "cons") + s["T_h"]
    Tl = 2 * S.loaders(s["rows"], "lin") + s["T_h"]
    print(f"{i:2d} {cc/1e6:7.2f} {S.dgm(cc):+6.2f} {s['R']:2d} {s['B']:3d} {s['C']:3d} "
          f"{s['rows']:4d} {s['K']:3d} {s['b_over_c']:5.2f} {s['T_h']:5d} {s['Q']:4d} "
          f"{s['floor']:5.2f} {s['e2']:5.1f} {s['gate']:5.2f} {L:5.0f} {T:6.0f} "
          f"{cc/1e6:7.2f} {S.cost(Tc, s['Q'])/1e6:8.2f} {S.cost(Tl, s['Q'])/1e6:7.2f}")

print("\n### A1b. same, restricted to B >= 129 (the Q pocket) and to B/C >= 2.0\n")
feas2 = [s for s in feas if s["B"] >= 129]
print(f"feasible with B>=129: {len(feas2)}")
print(hdr)
for i, (cc, T, L, s) in enumerate(rank(feas2, "cut")):
    Tc = 2 * S.loaders(s["rows"], "cons") + s["T_h"]
    Tl = 2 * S.loaders(s["rows"], "lin") + s["T_h"]
    print(f"{i:2d} {cc/1e6:7.2f} {S.dgm(cc):+6.2f} {s['R']:2d} {s['B']:3d} {s['C']:3d} "
          f"{s['rows']:4d} {s['K']:3d} {s['b_over_c']:5.2f} {s['T_h']:5d} {s['Q']:4d} "
          f"{s['floor']:5.2f} {s['e2']:5.1f} {s['gate']:5.2f} {L:5.0f} {T:6.0f} "
          f"{cc/1e6:7.2f} {S.cost(Tc, s['Q'])/1e6:8.2f} {S.cost(Tl, s['Q'])/1e6:7.2f}")

print("\n### A2. inner-temp pockets over the grid (B axis)\n")
pock: dict[int, dict] = {}
for s in GRID:
    p = pock.setdefault(s["inner_temp"], {"B": set(), "k2": set(), "n": 0, "Q": set(),
                                          "RC": set()})
    p["B"].add(s["B"])
    p["k2"].add(s["k2"])
    p["Q"].add(s["Q"])
    p["RC"].add(s["R"] * s["C"])
    p["n"] += 1
print(f"{'inner_temp':>10} {'B range':>9} {'k2':>6} {'#shapes':>7} {'Q':>9} {'R*C range':>12}")
for t in sorted(pock):
    p = pock[t]
    print(f"{t:10d} {min(p['B']):4d}-{max(p['B']):<4d} {str(sorted(p['k2'])):>6} {p['n']:7d} "
          f"{min(p['Q']):4d}-{max(p['Q']):<4d} {min(p['RC']):5d}-{max(p['RC']):<5d}")

print("\n### A3. the 'B>=129' rule: cheapest Q for B<129 vs B>=129\n")
for name, sel in (("B<129", lambda s: s["B"] < 129), ("B>=129", lambda s: s["B"] >= 129)):
    sub = [s for s in GRID if sel(s)]
    print(f"  {name}: min Q {min(s['Q'] for s in sub)}, "
          f"min inner_temp {min(s['inner_temp'] for s in sub)}, "
          f"median inner_temp {sorted(s['inner_temp'] for s in sub)[len(sub)//2]}")
    best = min(sub, key=lambda s: s["inner_temp"])
    print(f"    cheapest-temp shape: R={best['R']} B={best['B']} C={best['C']} "
          f"K={best['K']} Q={best['Q']} T_h={best['T_h']} floor={best['floor']:.1f}")
