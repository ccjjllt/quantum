"""Experiment 2: retain-vs-recompute on one explicit chain (baseline_hw06).

Chain: src=[25562,25576] (B tail) -> copy=[28787,28801] (inverse_B head).
Three independent flanked temporary-ANDs into q21/q28/q40, consumed, then
recomputed op-text-identically. Frontier [21,28,40]; value signatures equal;
copy targets start at zero. 48 HMR/R barriers sit between src and copy
(the originals are consumed/measured; a retained copy must live on an extra
ancilla or be stored classically).

Cost model (verifier units: C = executed Toffoli-like + T/4, score = Q*C;
CX/X/CZ are Clifford and free; CCX unconditional here):
  opt0 : pay the copy (3 executed CCX).
  opt1 : retain 1 output, coherent keep + Bennett uncompute (+1Q).
  opt1b: retain 1 output, measure at last use + classical store with
         deterministic Clifford corrections, ancilla recycled (62Q).
  opt2 / opt2b: same for 2 outputs. opt3b: all 3 outputs, measured.
Cleanup correctness for 1b/2b/3b (deterministic correction covers every
measurement outcome, verifier constant-phase convention kept) is stated as
TO-PROVE: gate counts are exact, the correction-coverage proof is not
claimed. Spooky-pebbling reading: 1b/2b/3b trade quantum liveness through
the 3211-op span for classical storage + outcome-conditioned Cliffords.

Threshold lines (score/C units, README authoritative; recomputed values in
the report differ by ~0.3): 62Q 81.10, 63Q 105.56, 64Q 129.26 C units.

Usage:
  uv run python experiments/invsqrt/20261102_hw06_opt/retain_chain62.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))

import retain62  # noqa: E402

BASELINE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
OUT = ROOT / "experiments/invsqrt/20261102_hw06_opt/retain_chain62.json"

SRC = (25562, 25576)
COPY = (28787, 28801)
FRONTIER = [21, 28, 40]

C_OFFICIAL = 100568.4992 / 62.0
THRESHOLD_5PCT = 95540.0742
LINES = {"62Q": 81.10, "63Q": 105.56, "64Q": 129.26}


def load_ops():
    import kickmix

    circuit = kickmix.Circuit.from_file(BASELINE)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def op_kind(line):
    return line.split()[0]


def main():
    B = load_ops()
    src_ops = B[SRC[0]:SRC[1] + 1]
    copy_ops = B[COPY[0]:COPY[1] + 1]
    assert len(src_ops) == 15 and len(copy_ops) == 15, (len(src_ops), len(copy_ops))
    assert src_ops == copy_ops, "chain must be an exact op-text repeat"
    print(f"chain: {len(src_ops)} ops, exact text repeat: True", flush=True)

    # Executed cost of the copy: all unconditional?
    cond = []
    toff = 0
    for i in range(COPY[0], COPY[1] + 1):
        p = B[i].split()
        if p[0] in ("CCX", "CCZ", "CSWAP"):
            toff += 1
            if "if" in p:
                cond.append((i, B[i]))
    print(f"copy Toffoli-like (static): {toff}, conditional among them: {len(cond)}", flush=True)

    # PUSH/POP balance inside copy (condition stack must be empty/constant).
    depth = 0
    stack_ok = True
    for line in copy_ops:
        k = op_kind(line)
        if k == "PUSH_CONDITION":
            depth += 1
        elif k == "POP_CONDITION":
            depth -= 1
            if depth < 0:
                stack_ok = False
    print(f"copy condition-stack balanced & empty: {stack_ok and depth == 0}", flush=True)

    # Backward slice inside the copy per frontier output: which copy ops are
    # needed to (re)produce that output. Local dataflow on the 15-op window:
    # need-set of wires, walk backwards.
    def reads_writes(line):
        p = line.split()
        k = p[0]
        morate = [int(t[1:]) for t in p[1:] if t.startswith("q") and t[1:].isdigit()]
        if k == "X":
            return set(morate), set(morate)
        if k == "CX":
            return {morate[0]}, {morate[1]}
        if k == "CCX":
            return {morate[0], morate[1]}, {morate[2]}
        return set(), set()

    slices = {}
    for q in FRONTIER:
        need = {q}
        used = []
        for i in range(COPY[1], COPY[0] - 1, -1):
            rd, wr = reads_writes(B[i])
            if need & wr:
                used.append(i)
                need = (need - wr) | rd
        used.sort()
        ccx_in_slice = sum(1 for i in used if op_kind(B[i]) == "CCX")
        slices[q] = {"ops": used, "n_ops": len(used), "ccx": ccx_in_slice,
                     "lines": [B[i] for i in used]}
    for q, s in slices.items():
        print(f"  slice q{q}: {s['n_ops']} ops, {s['ccx']} CCX", flush=True)
    overlap = len(set(slices[21]["ops"]) & set(slices[28]["ops"]) |
                  set(slices[21]["ops"]) & set(slices[40]["ops"]) |
                  set(slices[28]["ops"]) & set(slices[40]["ops"]))
    print(f"  pairwise slice overlap (ops): {overlap}", flush=True)

    # Zero-wire borrowing check over the span (25576, 28787): a wire is
    # borrowable only if it is MENTIONED NOWHERE in the span AND its value-id
    # at span start is the zero id (mention-free is necessary, not sufficient).
    span_mentions = set()
    for i in range(SRC[1] + 1, COPY[0]):
        for t in B[i].split()[1:]:
            if t.startswith("q") and t[1:].isdigit():
                span_mentions.add(int(t[1:]))
    _v, _w, snap0, _s, _e = retain62.interpret(B, capture_at={SRC[1]})
    start = snap0[SRC[1]]
    quiet = [q for q in range(62) if q not in span_mentions]
    borrowable = [q for q in quiet if start[q] == _v.zero]
    print(f"wires never mentioned across the 3211-op span: {len(quiet)}", flush=True)
    print(f"of those, zero-valued at span start (borrowable): {borrowable}", flush=True)

    # --- Cost table ---
    # Clifford CX/X/CZ free. Deleted unconditional CCX: -1 C each.
    # Coherent keep: +f qubits, copy-in f CX (free), Bennett uncompute f CX.
    # Measured keep: HMR per ancilla + conditional Clifford corrections
    #   (X/CX/CZ under outcome bits, free), ancilla recycled -> 62Q.
    rows = []
    C = C_OFFICIAL
    base_score = 62 * C
    for f, mode in [(0, "pay-copy"), (1, "coherent"), (1, "measured"),
                    (2, "coherent"), (2, "measured"), (3, "measured")]:
        if f == 0:
            dC, Q = 0.0, 62
        elif mode == "coherent":
            dC, Q = float(-f), 62 + f
        else:
            dC, Q = float(-f), 62
        dscore = Q * (C + dC) - base_score
        rows.append({"retained": f, "mode": mode, "delta_C": dC, "Q": Q,
                     "delta_score": round(dscore, 2),
                     "copy_cx": f if f else 0,
                     "cleanup": ("none" if f == 0 else
                                 ("bennett-uncompute" if mode == "coherent"
                                  else "HMR+classical+clifford-corrections")),
                     "proof": ("baseline" if f == 0 else
                               ("boolean-exact" if mode == "coherent"
                                else "TO-PROVE(correction-coverage)"))})
    for r in rows:
        print(f"  retain={r['retained']} {r['mode']:9s} dC={r['delta_C']:+.1f} "
              f"Q={r['Q']} dscore={r['delta_score']:+.2f} [{r['proof']}]", flush=True)

    # Pool-wide upper bound: sum of copy_toffoli_like over every part with
    # equal value signatures (only those can be replaced by retention at all).
    segs, _groups = retain62.repeated_segments(B)
    scored = retain62.frontier(B, segs)
    sig_equal_pool = sum(r["copy_toffoli_like"] for r in scored
                         if r["value_signature_equal"] and r["zero_before_copy"]["holds"])
    sig_equal_parts = sum(1 for r in scored
                          if r["value_signature_equal"] and r["zero_before_copy"]["holds"])
    print(f"pool bound: {sig_equal_parts} sig-equal+zero parts, "
          f"gross <={sig_equal_pool} C (62Q, before cleanup costs)", flush=True)

    recomputed = {q: round(C - THRESHOLD_5PCT / q, 2) for q in (62, 63, 64)}
    print(f"recomputed 5%-threshold lines (C units): {recomputed} "
          f"vs README {LINES}", flush=True)
    per_qubit_cost = round(C, 2)
    print(f"one extra qubit costs ~+{per_qubit_cost} score units at fixed C "
          f"(needs >={round(C/63, 2)} C saving per qubit to break even)", flush=True)

    OUT.write_text(json.dumps({
        "chain": {"src": list(SRC), "copy": list(COPY),
                  "frontier": FRONTIER, "exact_text_repeat": True,
                  "copy_toffoli_like": toff, "copy_conditional": cond,
                  "copy_stack_balanced_empty": bool(stack_ok and depth == 0),
                  "span_ops": COPY[0] - SRC[1] - 1,
                  "wires_never_mentioned_in_span": quiet,
                  "borrowable_zero_wires": borrowable},
        "slices": {str(q): v for q, v in slices.items()},
        "slice_overlap_ops": overlap,
        "C_official": C,
        "threshold_lines_readme_C_units": LINES,
        "threshold_lines_recomputed": recomputed,
        "cost_table": rows,
        "pool_bound_sig_equal_C": sig_equal_pool,
        "pool_bound_sig_equal_parts": sig_equal_parts,
        "verdict": ("max gross on this chain is -3 C (62Q measured, TO-PROVE); "
                    "coherent options are net-positive by thousands; "
                    "no option approaches any threshold line."),
    }, indent=2) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
