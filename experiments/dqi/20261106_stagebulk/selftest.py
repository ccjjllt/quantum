"""Self-test miter on synthetic true/false cases."""
import sys; sys.path.insert(0,'experiments/dqi/20261106_stagebulk')
from miter import build_cone, build_cnf, solve_cnf
TRUE_CASE=["CCX q0 q1 q2\n","CX q5 q6\n","CCX q0 q1 q3\n"]  # P1=q0&q1 @0, P2=q0&q1 @2
FALSE_CASE=["CCX q0 q1 q2\n","X q0\n","CCX q0 q1 q3\n"]
COND_CASE=["CCX q0 q1 q2\n","CX q0 q9 if b5\n","CCX q0 q1 q3\n"]  # unknown bit -> SAT(approx)
for name,win in (("TRUE",TRUE_CASE),("FALSE",FALSE_CASE),("COND",COND_CASE)):
    rel,bottom,frozen=build_cone(win,0,0,2,'q2','q3')
    cnf=build_cnf(rel,0,0,2)
    if cnf is None: print(name,"NOPROD"); continue
    print(name,"refuted-model" if False else name, "vars/clauses:", max(max(abs(c) for c in cl) for cl in cnf), len(cnf), "->", solve_cnf(cnf), "frozen=",frozen)

# R-reset semantics test (R q forces 0)
import sys as _s; _s.path.insert(0,'experiments/dqi/20261106_stagebulk')
from miter import build_cone as _bc, build_cnf as _bf, solve_cnf as _sc
RCASE=["CCX q0 q1 q2\n","R q0\n","CCX q0 q1 q3\n"]  # P2 = 0&q1 = 0; P1 varies -> REFUTED
_rel,_b,_f=_bc(RCASE,0,0,2,'q2','q3')
_cnf=_bf(_rel,0,0,2)
print("R-kill:", "NOPROD" if _cnf is None else _sc(_cnf), "(expect SAT/REFUTED)")
