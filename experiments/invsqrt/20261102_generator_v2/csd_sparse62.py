"""CSD sparsity recovery on the BOTH line (research script, manual runs only).

NOT a test file, NOT CI. Manual evidence commands::

    uv run python experiments/invsqrt/20261102_generator_v2/csd_sparse62.py --recount
    uv run python experiments/invsqrt/20261102_generator_v2/csd_sparse62.py --search
    uv run python experiments/invsqrt/20261102_generator_v2/csd_sparse62.py --verify-cand

Background: QROM loads tables with one CX per set bit (qrom_sweep in
width_opt62.py: for each of 256 entries, for each set bit j: cx(m, target[j])).
Target lines start |0> and are shared across the 256 slots (unary match qubit
selects the single active entry), then the same pattern replays to unload.
Full circuit sweeps each table 4x (fwd load/unload + rev load/unload), so
full-circuit QROM CX = 4 * (pop(B)+pop(A)+pop(R)).

Task 1 (recount): for FIXED integer values the binary expansion is unique, so
per-sweep CX = popcount is forced and minimal -- no exact-equivalent sparser
recoding exists at QROM level (proof sketch in csd_sparse.md). The stored
tables are bare integers (no CSD digits in the JSON, no signed-digit consumer
in the circuit: mini_pass + width-generic A1/R1 rows consume binary). Hence
task 1 concludes "already minimal" by uniqueness; values untouched.

Task 2 (search): the only real lever on QROM CX is DIFFERENT integer values
with equal precision. Greedy per-address coordinate descent (segments are
independent: V(x),P(x) depend only on table entry a(x)):
  accept a move iff total popcount strictly decreases AND seg maxrel stays
  within BUDGET_GLOBAL = base_maxrel + 0.02. Selection = max bits saved,
  tie-break min rel. At most one candidate table is written.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import refit_layout62 as L62  # noqa: E402

ART = ROOT / "artifacts/20261102_generator_v2/invsqrt"
BASE_TABLES = ART / "int_tables_R10_A20_quant.json"
CAND_TABLES = ART / "int_tables_R10_A20_sparse62.json"

W = {"B": 33, "A": 20, "R": 10}
S = {"sA": 2, "sR": 2, "sB": 0}


def load_base():
    doc = json.loads(BASE_TABLES.read_text())
    Bs = np.array(doc["Bs"], dtype=np.int64)
    As = np.array(doc["As"], dtype=np.int64)
    Rs = np.array(doc["Rs"], dtype=np.int64)
    return doc, Bs, As, Rs


def pop(v: int) -> int:
    return bin(int(v)).count("1")


def pop_table(t) -> int:
    return sum(pop(v) for v in t)


def cmd_recount() -> int:
    doc, Bs, As, Rs = load_base()
    print(f"base={BASE_TABLES.name} candidate={doc['candidate']} "
          f"shifts={doc['shifts']}")
    print(f"base contract: fails={doc['contract']['fails']} "
          f"maxrel={doc['contract']['maxrel']:.10f} "
          f"margin={doc['contract']['min_margin']:.1f}")
    print(f"stored JSON keys: {sorted(doc.keys())} "
          f"(bare integers; no CSD digit fields)")
    tot = 0
    for name, t, w in (("B", Bs, 33), ("A", As, 20), ("R", Rs, 10)):
        p = pop_table(t)
        tot += p
        ps = sorted(pop(v) for v in t)
        print(f"{name}: width={w} n=256 pop={p} avg={p/256:.3f} "
              f"min/max entry pop={ps[0]}/{ps[-1]} "
              f"per-sweep CX={p}")
    print(f"total pop={tot} -> full-circuit QROM CX = 4x{tot} = {4*tot} "
          f"(4 sweeps/table: fwd load/unload + rev load/unload)")
    print(f"BUDGET_GLOBAL = {doc['contract']['maxrel']:.10f} + 0.02 = "
          f"{doc['contract']['maxrel'] + 0.02:.10f}")
    return 0


def sparser_neighbors(v: int, w: int):
    """Strictly fewer-1-bit integers near v (exact-value changes; caller
    checks precision). Bit clears + small +-delta + round to 2^k multiples."""
    v = int(v)
    if v <= 0:
        return []
    out = set()
    for j in range(w):
        if (v >> j) & 1:
            out.add(v - (1 << j))
    for d in range(1, 17):
        if v - d >= 0:
            out.add(v - d)
        out.add(v + d)
    for k in range(2, 9):
        st = 1 << k
        out.add(((v + st - 1) // st) * st)
        out.add((v // st) * st)
    out.discard(v)
    pv = pop(v)
    return sorted(u for u in out
                  if 0 <= u < (1 << w) and pop(u) < pv)


def cmd_search(budget_add=0.02, write=True, table_order=(0, 1, 2)) -> int:
    t0 = time.time()
    doc, Bs, As, Rs = load_base()
    base_maxrel = float(doc["contract"]["maxrel"])
    budget = base_maxrel + budget_add
    base_pop = pop_table(Bs) + pop_table(As) + pop_table(Rs)
    print(f"[sparse] base maxrel={base_maxrel:.10f} budget={budget:.10f} "
          f"base pop={base_pop}")
    tgt, tol = L62.load_ref()
    seg_xs = L62.seg_index()
    order = sorted(range(256), key=lambda aa: pop(Bs[aa]) + pop(As[aa])
                   + pop(Rs[aa]), reverse=True)
    tables = [Bs, As, Rs]
    widths = [W["B"], W["A"], W["R"]]
    names = ["B", "A", "R"]
    saved_total = 0
    improved_addrs = 0
    seg_rel_delta = []
    for pas in range(2):
        moved = 0
        for aa in order:
            xs = seg_xs[aa]
            if len(xs) == 0:
                continue
            cur_rel, _ = L62.seg_maxrel(xs, aa, Bs, As, Rs,
                                       S["sA"], S["sR"], S["sB"], tgt, tol)
            cur_pop = pop(Bs[aa]) + pop(As[aa]) + pop(Rs[aa])
            addr_moved = False
            for ti in table_order:
                tbl = tables[ti]
                old = int(tbl[aa])
                cands = sparser_neighbors(old, widths[ti])
                best = None  # (new_total_pop, new_rel, new_val)
                for u in cands:
                    tbl[aa] = u
                    r, _ = L62.seg_maxrel(xs, aa, Bs, As, Rs,
                                         S["sA"], S["sR"], S["sB"], tgt, tol)
                    new_pop = (cur_pop - pop(old) + pop(u))
                    if r <= budget and new_pop < cur_pop:
                        key = (new_pop, r)
                        if best is None or key < (best[0], best[1]):
                            best = (new_pop, r, u)
                    tbl[aa] = old
                if best is not None:
                    tbl[aa] = best[2]
                    saved = cur_pop - best[0]
                    saved_total += saved
                    cur_pop = best[0]
                    cur_rel = best[1]
                    moved += 1
                    addr_moved = True
            if addr_moved:
                improved_addrs += 1
        print(f"[sparse] pass{pas}: moved_entries={moved} "
              f"saved_bits_cum={saved_total} dt={time.time()-t0:.0f}s")
        if moved == 0:
            break
    new_pop = pop_table(Bs) + pop_table(As) + pop_table(Rs)
    pops = tuple(pop_table(t) for t in (Bs, As, Rs))
    qrom_cx = 2 * pops[0] + 4 * pops[1] + 4 * pops[2]
    print(f"[sparse] pop {base_pop} -> {new_pop} "
          f"(saved={base_pop-new_pop}) addrs_touched={improved_addrs}")
    print(f"[sparse] per-table pop B/A/R={pops[0]}/{pops[1]}/{pops[2]} "
          f"true QROM CX=2B+4A+4R={qrom_cx}")
    if new_pop >= base_pop:
        print("[sparse] NO sparser table found -> VETO integration")
        return 1
    r = L62.full_vec(Bs, As, Rs, S["sA"], S["sR"], S["sB"], tgt, tol)
    print(f"[sparse] full contract: fails={r['fails']} "
          f"maxrel={r['maxrel']:.10f} worst={r['worst']} "
          f"margin={r['min_margin']:.1f} V=({r['vmin']},{r['vmax']})")
    ok = (r["fails"] == 0 and r["maxrel"] <= budget)
    print("SPARSE-SEARCH " + ("PASS" if ok else "FAIL"))
    if not ok:
        return 1
    out = {"candidate": "BOTH_SPARSE", "parent": BASE_TABLES.name,
           "kA": 2, "kR": 2, "kB": 0,
           "shifts": {"sA": 2, "sR": 2, "sB": 0},
           "Bs": [int(v) for v in Bs], "As": [int(v) for v in As],
           "Rs": [int(v) for v in Rs],
           "base_maxrel": base_maxrel, "budget": budget,
           "budget_add": budget_add, "table_order": list(table_order),
           "base_pop": base_pop, "new_pop": new_pop,
           "saved_bits": base_pop - new_pop,
           "contract": r, "seconds": round(time.time() - t0, 1)}
    if write:
        CAND_TABLES.write_text(json.dumps(out) + "\n")
        print(f"[sparse] wrote {CAND_TABLES} saved_bits={base_pop - new_pop}")
    else:
        print(f"[sparse] no-write mode: candidate NOT persisted "
              f"(saved_bits={base_pop - new_pop})")
    return 0


def cmd_verify_cand() -> int:
    doc = json.loads(CAND_TABLES.read_text())
    Bs = np.array(doc["Bs"], dtype=np.int64)
    As = np.array(doc["As"], dtype=np.int64)
    Rs = np.array(doc["Rs"], dtype=np.int64)
    tgt, tol = L62.load_ref()
    r = L62.full_vec(Bs, As, Rs, 2, 2, 0, tgt, tol)
    print(f"[verify-cand] fails={r['fails']} maxrel={r['maxrel']:.10f} "
          f"worst={r['worst']} margin={r['min_margin']:.1f} "
          f"budget={doc['budget']:.10f} saved_bits={doc['saved_bits']}")
    ok = (r["fails"] == 0 and r["maxrel"] <= doc["budget"]
          and r["maxrel"] == doc["contract"]["maxrel"])
    print("VERIFY-CAND " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recount", action="store_true")
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--budget-add", type=float, default=0.02)
    ap.add_argument("--order", default="BAR",
                    help="table processing order, e.g. BAR or RAB")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--verify-cand", action="store_true")
    args = ap.parse_args()
    if args.recount:
        return cmd_recount()
    if args.search:
        idx = {"B": 0, "A": 1, "R": 2}
        return cmd_search(budget_add=args.budget_add,
                          write=not args.no_write,
                          table_order=tuple(idx[ch] for ch in args.order))
    if args.verify_cand:
        return cmd_verify_cand()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
