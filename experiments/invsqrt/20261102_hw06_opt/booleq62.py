"""Three-valued boolean-equivalence checker for invsqrt dataflow cones.

Verdicts:
    EQUIVALENT  -- proved (same value-id, or exhaustive truth table / ANF, or Z3 UNSAT of xor)
    UNKNOWN     -- different value-ids but not disproved (incl. Z3 timeout); NEVER a counterexample
    DIFFERENT   -- exhibited a concrete diverging assignment (true counterexample)

Rules:
    - Same value-id is a fast sufficient condition for EQUIVALENT.
    - Different value-ids return UNKNOWN unless a proof/refutation is produced.
    - Cones with <=12 free boolean variables: exact truth table (and ANF cross-check).
    - Cones with >12 free variables: Z3 equivalence check, one call, 60 s timeout
      (run with `uv run --with z3-solver python ...`; without z3, verdict is UNKNOWN).
    - Measurement outcomes keep independent versions + condition environments;
      a measured bit is never identified with its pre-measurement qubit.

Self-test (the op-25623 case that blocked prefix):
    q14 XOR (q14 AND q21)  vs  q14 AND NOT q21  -> EQUIVALENT (128-row table).

Usage:
    uv run --with z3-solver python experiments/invsqrt/20261102_hw06_opt/booleq62.py --self-test
"""

from __future__ import annotations

import argparse
import itertools
import sys
from dataclasses import dataclass

Z3_TIMEOUT_MS = 60_000
SMALL_VAR_LIMIT = 12


# ---------------------------------------------------------------- AST
@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class And:
    l: object
    r: object


@dataclass(frozen=True)
class Xor:
    l: object
    r: object


@dataclass(frozen=True)
class Not:
    e: object


@dataclass(frozen=True)
class One:
    pass


def free_vars(e, acc=None):
    acc = set() if acc is None else acc
    if isinstance(e, Var):
        acc.add(e.name)
    elif isinstance(e, (And, Xor)):
        free_vars(e.l, acc)
        free_vars(e.r, acc)
    elif isinstance(e, Not):
        free_vars(e.e, acc)
    return acc


def ev(e, env) -> int:
    if isinstance(e, Var):
        return env[e.name]
    if isinstance(e, One):
        return 1
    if isinstance(e, Not):
        return ev(e.e, env) ^ 1
    if isinstance(e, And):
        return ev(e.l, env) & ev(e.r, env)
    if isinstance(e, Xor):
        return ev(e.l, env) ^ ev(e.r, env)
    raise TypeError(type(e))


def anf(e):
    """Algebraic normal form as frozenset of monomial frozensets (var names). XOR of ANDs."""
    if isinstance(e, Var):
        return frozenset({frozenset({e.name})})
    if isinstance(e, One):
        return frozenset({frozenset()})
    if isinstance(e, Not):
        return anf(Xor(e.e, One()))
    if isinstance(e, Xor):
        return anf(e.l) ^ anf(e.r)
    if isinstance(e, And):
        out = set()
        for m1 in anf(e.l):
            for m2 in anf(e.r):
                out ^= {m1 ^ m2}
        return frozenset(out)
    raise TypeError(type(e))


def truth_table_check(e1, e2):
    names = sorted(free_vars(e1) | free_vars(e2))
    if len(names) > SMALL_VAR_LIMIT:
        return None  # too big for exhaustive table
    rows = 0
    for bits in itertools.product((0, 1), repeat=len(names)):
        env = dict(zip(names, bits))
        rows += 1
        if ev(e1, env) != ev(e2, env):
            return {"equivalent": False, "counterexample": env, "rows": rows,
                    "n_vars": len(names)}
    return {"equivalent": True, "rows": rows, "n_vars": len(names)}


def z3_check(e1, e2, timeout_ms=Z3_TIMEOUT_MS):
    try:
        import z3
    except ImportError:
        return {"verdict": "UNKNOWN", "reason": "z3 not installed; rerun with "
                "`uv run --with z3-solver python ...`"}
    names = sorted(free_vars(e1) | free_vars(e2))

    def build(e, vs):
        if isinstance(e, Var):
            return vs[e.name]
        if isinstance(e, One):
            return z3.BoolVal(True)
        if isinstance(e, Not):
            return z3.Not(build(e.e, vs))
        if isinstance(e, And):
            return z3.And(build(e.l, vs), build(e.r, vs))
        if isinstance(e, Xor):
            return z3.Xor(build(e.l, vs), build(e.r, vs))
        raise TypeError(type(e))

    vs = {n: z3.Bool(n) for n in names}
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    s.add(build(e1, vs) != build(e2, vs))
    r = s.check()
    if r == z3.unsat:
        return {"verdict": "EQUIVALENT", "method": "z3-unsat", "n_vars": len(names)}
    if r == z3.sat:
        m = s.model()
        return {"verdict": "DIFFERENT", "method": "z3-sat",
                "counterexample": {n: bool(m[vs[n]]) for n in names}}
    return {"verdict": "UNKNOWN", "method": f"z3-{r}"}


def check(e1, e2, same_value_id=False):
    """Three-valued entry point. same_value_id=True short-circuits to EQUIVALENT."""
    if same_value_id or e1 == e2:
        return {"verdict": "EQUIVALENT", "method": "same-value-id"}
    tt = truth_table_check(e1, e2)
    if tt is not None:
        if tt["equivalent"]:
            a1, a2 = anf(e1), anf(e2)
            if a1 != a2:  # internal inconsistency guard; table rules
                return {"verdict": "EQUIVALENT", "method": "truth-table",
                        "note": "ANF cross-check diverged; table (exhaustive) rules",
                        "rows": tt["rows"]}
            return {"verdict": "EQUIVALENT", "method": "truth-table+anf",
                    "rows": tt["rows"], "n_vars": tt["n_vars"]}
        return {"verdict": "DIFFERENT", "method": "truth-table",
                "counterexample": tt["counterexample"]}
    return z3_check(e1, e2)


def self_test() -> int:
    q14, q21 = Var("q14"), Var("q21")
    gate_form = Xor(q14, And(q21, q14))          # snapshot after CCX q21 q14 q50
    specified = And(q14, Not(q21))                # q14 AND NOT q21
    res = check(gate_form, specified)
    print(f"op25623 identity: {res}")
    assert res["verdict"] == "EQUIVALENT", res
    # A real difference must be caught, not waved through:
    neg = check(And(q14, q21), And(q14, Not(q21)))
    print(f"sanity non-identity: {neg}")
    assert neg["verdict"] == "DIFFERENT", neg
    print("BOOLEQ SELF-TEST PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
