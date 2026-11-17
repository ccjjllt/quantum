import csv, math
from collections import Counter

PATH = "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261117_lb_decomp/google-verifiable-quantum-circuit-compilation-publicleaderboard-2026-11-17T03:30:55.csv"
R1, R2, R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375

rows = []
with open(PATH, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(dict(rank=int(r["Rank"]), team=r["TeamName"].strip(),
                         last=r["LastSubmissionDate"], score=float(r["Score"]),
                         nsub=int(r["SubmissionCount"]),
                         members=(r["TeamMemberUserNames"] or "").strip()))

INV = 74797.36535717871
DQI = 346413579540.4963
CHEM = 294643137.73357135
T0, QI0, QD0 = 14706, 44, 890
CT = CHEM / T0          # chem cost per T
CI = INV / QI0          # invsqrt cost per Q at 200,540,928 shots
GM0 = (R1/INV * R2/DQI * R3/CHEM) ** (1/3)

print("GM0 = %.12f" % GM0)
print("chem cost/T = %.6f  (check 93326853: %.6f)" % (CT, 294762512.64351326/14712))
print("inv cost/Q = %.5f" % CI)
print("DQI cost/Q^2 = %.1f" % (DQI/QD0**2))

def P(S): return (GM0/S)**3

top = rows[:100]
print("\n### TOP100 TABLE (rank|team|score|last|nsub)")
for r in top:
    print("%d|%s|%.5f|%s|%d" % (r["rank"], r["team"], r["score"], r["last"], r["nsub"]))

# distribution
print("\n### BAND DISTRIBUTION 28.0-31.0 width 0.05 (half-open)")
lo = 28.0
band = []
while lo < 31.0 - 1e-9:
    hi = lo + 0.05
    cnt = sum(1 for r in rows if lo <= r["score"] < hi)
    band.append((lo,hi,cnt)); print("%.2f|%.2f|%d" % (lo,hi,cnt)); lo = hi

print("\n### CUMULATIVE")
for t in [28.0,28.05,28.09086,28.09486,28.1,28.12769,28.14703,28.15083,28.2,28.3,28.4,28.5,28.6,28.68633,28.7,28.8,28.9,29.0,29.1,29.2,29.3,29.5,29.75,30.0,30.1,30.28512,30.5,30.75,30.96223,30.96645]:
    print("%.5f|%d" % (t, sum(1 for r in rows if r["score"]>=t)))

print("\n### INVERSION (representative scores)")
hdr = "score|P|dP%|inv_cost|inv_Q|inv_Q_shots_eq|dqi_cost|dqi_Q|chem_cost|chem_T"
print(hdr)
SC = [28.05,28.10,28.14703,28.15083,28.2,28.3,28.4,28.5,28.6,28.65,28.68633,28.7,28.8,28.9,
      28.92164,29.0,29.14389,29.21549,29.3,29.5,29.57281,29.75,29.7975,29.979,30.0,30.00881,
      30.13063,30.28512,30.5,30.78291,30.96223,30.96645]
for S in SC:
    p = P(S); ci, cd, cc = INV*p, DQI*p, CHEM*p
    print("%.5f|%.6f|%+.3f|%.3f|%.3f|%.3f|%.4e|%.2f|%.3f|%.2f" %
          (S,p,(p-1)*100,ci,ci/CI,ci/CI,cd,QD0*math.sqrt(p),cc,cc/CT))

print("\n### LATTICE: single-leg integer-structure fits for top-100 scores")
print("score|T_if_chem_only|resid|Qinv_if_only|resid|Qdqi_if_only|resid")
for r in top:
    S=r["score"]; p=P(S)
    Tt=T0*p; qt=QI0*p; dt=QD0*math.sqrt(p)
    print("%.5f|%.2f|%.3f|%.3f|%.3f|%.3f|%.3f" % (S,Tt,abs(Tt-round(Tt)),qt,abs(qt-round(qt)),dt,abs(dt-round(dt))))

print("\n### LATTICE2: two-leg integer combos (Qinv integer 40-44, T integer) for top-100")
for r in top:
    S=r["score"]; p=P(S); hits=[]
    for qi in range(38,45):
        rem = p/(qi/QI0)
        Tt = T0*rem
        if abs(Tt-round(Tt))<0.05 and 10000<=round(Tt)<=14720:
            hits.append("inv%d+T%d(d%.2f)"%(qi,round(Tt),abs(Tt-round(Tt))))
    for qd in range(830,891):
        rem = p/((qd/QD0)**2)
        Tt = T0*rem
        if abs(Tt-round(Tt))<0.05 and 10000<=round(Tt)<=14720:
            hits.append("dqi%d+T%d(d%.2f)"%(qd,round(Tt),abs(Tt-round(Tt))))
    for qi in range(38,45):
        for qd in range(830,891):
            rem = p/((qi/QI0)*((qd/QD0)**2))
            Tt = T0*rem
            if abs(Tt-round(Tt))<0.02 and 10000<=round(Tt)<=14720:
                hits.append("inv%d+dqi%d+T%d"%(qi,qd,round(Tt)))
    if hits: print("%.5f %s -> %s" % (S, r["team"], "; ".join(hits[:6])))

print("\n### CLUSTERS >=28.0 count>=3")
c = Counter(round(r["score"],5) for r in rows if r["score"]>=28.0)
for s,n in sorted(c.items(), key=lambda x:(-x[1],-x[0])):
    if n>=3: print("%.5f|%d" % (s,n))
