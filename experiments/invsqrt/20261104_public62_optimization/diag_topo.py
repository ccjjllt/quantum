"""Topology pre-scan: CCX triples with Kirill-like wire sharing (order-preserving)."""
import io
from pathlib import Path
import kickmix as km

P = Path("artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb")
c = km.Circuit.from_file(P)
buf = io.StringIO(); c.to_file(buf, format="kmx")
ops = [l for l in buf.getvalue().splitlines() if not l.startswith(("APPEND", "REGISTER"))]
BAR = ("HMR", "R", "Z_POW", "BIT_STORE0", "BIT_STORE1", "BIT_INVERT",
       "PUSH_CONDITION", "POP_CONDITION")
is_bar = [l.split()[0] in BAR for l in ops]
st = []
stack_of = []
for l in ops:
    p = l.split()
    stack_of.append(tuple(st))
    if p[0] == "PUSH_CONDITION": st.append(p[-1])
    elif p[0] == "POP_CONDITION": st.pop()
ccx = [(i, [int(t[1:]) for t in ops[i].split()[1:] if t.startswith('q')]) for i in range(len(ops))
       if ops[i].split()[0] == "CCX"]
print("CCX total:", len(ccx))
hits = []
for a in range(len(ccx)):
    for b in range(a + 1, len(ccx)):
        if ccx[b][0] - ccx[a][0] > 48: break
        for d in range(b + 1, len(ccx)):
            if ccx[d][0] - ccx[a][0] > 48: break
            (ia, A), (ib, B), (ic, C) = ccx[a], ccx[b], ccx[d]
            # topology A: A[1]==B[1], A[2]==B[2], B[0]==C[0]; 6-7 distinct wires
            if A[1] == B[1] and A[2] == B[2] and B[0] == C[0]:
                wires = set(A) | set(B) | set(C)
                if 6 <= len(wires) <= 7 and C[1] not in (A + B) and C[2] not in (A + B + [C[1]]):
                    seg = ops[ia:ic + 1]
                    if any(is_bar[ia:ic + 1]): continue
                    if any(s != stack_of[ia] for s in stack_of[ia:ic + 1]): continue
                    if 'if' in ops[ia].split() or 'if' in ops[ib].split() or 'if' in ops[ic].split():
                        cond = True
                    else: cond = False
                    hits.append((ia, ib, ic, A, B, C, stack_of[ia], cond))
print("TOPOLOGY HITS:", len(hits))
for h in hits[:30]:
    print(h)
