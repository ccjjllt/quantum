"""Three-valued Boolean equivalence for invsqrt value-ids.

Rule (matches Track B discrete spec + main-thread README):
  * same value-id            -> EQUIVALENT (sufficient condition);
  * different value-ids      -> PROVE: truth table / ANF when the combined cone
    has <= 12 free variables, else Z3 with a 60 s timeout;
  * Z3 timeout / no solver   -> UNKNOWN (never reported as a counterexample).

Measurement leaves are versioned atoms: they are NOT equated with the
pre-measurement qubit. The condition environment is tracked separately and
must match before two cones are compared.

Usage:
  uv run python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test
  uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiments/invsqrt/20261031_invsqrt62_replay"))

import retain62  # noqa: E402

BASELINE = ROOT / "artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb"
SMALL_CONE_LIMIT = 12
Z3_TIMEOUT_MS = 60_000


def load_ops(path=BASELINE):
    import kickmix

    circuit = kickmix.Circuit.from_file(path)
    buf = io.StringIO()
    circuit.to_file(buf, format="kmx")
    lines = buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND", "REGISTER"))]


def cone_atoms(values, *roots):
    """All atoms reachable from `roots`: consts, inputs, ANDs, measurements."""
    seen_ids = set()
    stack = list(roots)
    atoms = set()
    while stack:
        vid = stack.pop()
        if vid in seen_ids:
            continue
        seen_ids.add(vid)
        for atom in values.fs[vid]:
            atoms.add(atom)
            if atom in values.and_of:
                left, right = values.and_of[atom]
                stack.append(left)
                stack.append(right)
    return atoms, seen_ids


def free_variables(values, *roots):
    """Free variables = every atom except AND-structure (inputs, const, meas, fresh)."""
    atoms, _ = cone_atoms(values, *roots)
    return sorted(a for a in atoms if a not in values.and_of)


def eval_vid(values, root, env):
    memo = {}
    stack = [(root, False)]
    while stack:
        vid, done = stack.pop()
        if vid in memo:
            continue
        if not done:
            stack.append((vid, True))
            for atom in values.fs[vid]:
                if atom in values.and_of:
                    left, right = values.and_of[atom]
                    stack.append((left, False))
                    stack.append((right, False))
            continue
        acc = 0
        for atom in values.fs[vid]:
            if atom == -1:
                acc ^= 1
            elif atom in values.and_of:
                left, right = values.and_of[atom]
                acc ^= memo[left] & memo[right]
            else:
                acc ^= env[atom]
        memo[vid] = acc
    return memo[root]


def check_cone_clean(values, *roots):
    """Reject cones with undeclared fresh atoms (>= 1_000_000, non-measurement)."""
    atoms, _ = cone_atoms(values, *roots)
    bad = [
        a for a in atoms
        if a >= 1_000_000 and a not in values.meas_source and a != -1
    ]
    return bad


def truth_table_equiv(values, left, right):
    """Exhaustive check over all free-variable assignments. Returns dict."""
    fvars = free_variables(values, left, right)
    n = len(fvars)
    if n > SMALL_CONE_LIMIT:
        return {"method": "truth-table", "verdict": "deferred",
                "reason": f"{n} free vars > {SMALL_CONE_LIMIT}"}
    checked = 0
    for mask in range(1 << n):
        env = {atom: (mask >> i) & 1 for i, atom in enumerate(fvars)}
        if eval_vid(values, left, env) != eval_vid(values, right, env):
            return {"method": "truth-table", "verdict": "not-equivalent",
                    "free_vars": n, "checked": checked + 1,
                    "counterexample": {str(a): env[a] for a in fvars}}
        checked += 1
    return {"method": "truth-table", "verdict": "equivalent",
            "free_vars": n, "checked": checked}


def z3_equiv(values, left, right, timeout_ms=Z3_TIMEOUT_MS):
    """Z3 check for large cones. Timeout / missing solver -> unknown."""
    try:
        import z3
    except ImportError:
        return {"method": "z3", "verdict": "unknown",
                "reason": "z3-solver not installed"}
    fvars = free_variables(values, left, right)
    sym = {a: z3.Bool(f"v{a}") for a in fvars}
    memo = {}

    def build(vid):
        if vid in memo:
            return memo[vid]
        acc = None
        for atom in values.fs[vid]:
            if atom == -1:
                term = z3.BoolVal(True)
            elif atom in values.and_of:
                l, r = values.and_of[atom]
                term = z3.And(build(l), build(r))
            else:
                term = sym[atom]
            acc = term if acc is None else z3.Xor(acc, term)
        if acc is None:
            acc = z3.BoolVal(False)
        memo[vid] = acc
        return acc

    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(z3.Xor(build(left), build(right)))
    result = solver.check()
    if result == z3.unsat:
        return {"method": "z3", "verdict": "equivalent",
                "free_vars": len(fvars)}
    if result == z3.sat:
        model = solver.model()
        ce = {str(a): bool(model.eval(sym[a], model_completion=True))
              for a in fvars}
        return {"method": "z3", "verdict": "not-equivalent",
                "free_vars": len(fvars), "counterexample": ce}
    return {"method": "z3", "verdict": "unknown",
            "reason": "timeout-or-undecided", "free_vars": len(fvars)}


def equiv(values, left, right):
    """Three-valued entry point. Same id is sufficient for equivalent."""
    if left == right:
        return {"method": "same-value-id", "verdict": "equivalent",
                "free_vars": 0, "checked": 0}
    bad = check_cone_clean(values, left, right)
    if bad:
        return {"method": "none", "verdict": "unknown",
                "reason": f"undeclared fresh atoms {bad[:5]}"}
    n = len(free_variables(values, left, right))
    if n <= SMALL_CONE_LIMIT:
        return truth_table_equiv(values, left, right)
    return z3_equiv(values, left, right)


def self_test():
    """op25623 identity: q14 AND NOT q21 vs q14 XOR (q14 AND q21).

    Different value-ids (13200 vs 13186 in the old report's numbering), but the
    same Boolean function. Truth table must say equivalent. Then the full
    7-variable local cone (128 assignments) must match the real gate sequence.
    """
    values = retain62.Values()
    q14 = values.vid(frozenset([14]))
    q21 = values.vid(frozenset([21]))
    specified = values.and_(q14, values.xor(q21, values.one))
    gate_form = values.xor(q14, values.and_(q21, q14))
    assert specified != gate_form, "self-test needs distinct value-ids"
    proof = equiv(values, specified, gate_form)
    assert proof["verdict"] == "equivalent", proof
    print(f"identity: distinct ids, {proof['method']} "
          f"over {proof['free_vars']} vars, {proof['checked']} rows -> EQUIVALENT")

    # Full local cone: entry vars (18,0,27,2,14,21,54), 128 assignments.
    # Anchor by instruction content: op numbers drifted (+57 by R6) between
    # ahmed and baseline_hw06, so never reuse the old 25622:25631 numbering.
    local_vars = (18, 0, 27, 2, 14, 21, 54)
    ops = load_ops()
    pattern = ["CX q14 q50", "CCX q21 q14 q50", "CX q23 q21",
               "CSWAP q27 q50 q2", "CSWAP q18 q50 q0", "CX q27 q18",
               "CCX q54 q18 q50", "CX q27 q18"]
    anchor = next(i for i in range(len(ops) - 9) if ops[i:i + 8] == pattern)
    slice_ops = ops[anchor:anchor + 9]  # 8 real ops + Z_POW
    matched = 0
    for mask in range(128):
        entry = {q: (mask >> i) & 1 for i, q in enumerate(local_vars)}
        entry[50] = 0
        vals, wire, _snap, _sig, extra = retain62.interpret(
            slice_ops, track=True, entry=entry)
        ids = {q: vals.one if entry.get(q) else vals.zero for q in local_vars}
        ids[50] = vals.zero
        hidden = vals.and_(ids[14], vals.xor(ids[21], vals.one))
        inner = vals.mux(ids[27], ids[2], hidden)
        outer = vals.mux(ids[18], ids[0], inner)
        formula = vals.xor(outer, vals.and_(ids[54], vals.xor(ids[18], ids[27])))
        assert wire[50] == formula, f"local cone mismatch at mask {mask}"
        matched += 1
    print(f"local cone: {matched}/128 assignments match -> PASS")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        ok = self_test()
        print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
        raise SystemExit(0 if ok else 1)
    parser.error("nothing to do; pass --self-test")


if __name__ == "__main__":
    main()
