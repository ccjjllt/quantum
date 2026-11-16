import sys
sys.path.insert(0,'data/competition/verifiers')
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1
from dfthcsos.verify import KEEP_BITS
lam=46.92160235
def cost(R,B,C,brot=8,N=76):
    m=SpinFreeData_V1(R=R,B=B,C=C,N=N,chi=KEEP_BITS,beta=brot)
    o,i,g=m.outer_state_prep(),m.inner_state_prep(),m.givens_rotations()
    oq=m.outer_state_prep_qubit_cost(); iq=m.inner_state_prep_qubit_cost()
    Q=40+oq['persistent']+iq['persistent']+max(oq['temporary'],iq['temporary'])  # +40 ANGLE words
    return o+i+g,Q
print('shipped check (8,143,44):', cost(8,143,44), 'expect (6662,427)')
rows=[]
for R in range(2,17):
    for B in range(60,260):
        r=76+R*B
        if not 1150<=r<=1300: continue
        C=round(352/R)
        if C<8: continue
        try: Th,Q=cost(R,B,C)
        except Exception: continue
        L=4025*r/1220.0            # loader T scales with the row count (measured 4025 at 1220)
        T=2*L+Th
        rows.append((lam*T*Q/1e6,R,B,C,r,Th,Q,L))
rows.sort()
print(f"{'cost M':>8} {'R':>2} {'B':>4} {'C':>3} {'rows':>5} {'T_heur':>6} {'Q':>4} {'L/pass':>7}")
for c,R,B,C,r,Th,Q,L in rows[:18]:
    print(f'{c:8.2f} {R:2d} {B:4d} {C:3d} {r:5d} {Th:6d} {Q:4d} {L:7.0f}')
