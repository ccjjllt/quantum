import csv, math, statistics
PATH = "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261117_lb_decomp/google-verifiable-quantum-circuit-compilation-publicleaderboard-2026-11-17T03:30:55.csv"
R1, R2, R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375
rows=[]
with open(PATH,newline="",encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append((int(r["Rank"]),r["TeamName"].strip(),float(r["Score"]),r["LastSubmissionDate"],int(r["SubmissionCount"])))
INV=74797.36535717871; DQI=346413579540.4963; CHEM=294643137.73357135
T0,QI0,QD0=14706.0,44.0,890.0
GM0=(R1/INV*R2/DQI*R3/CHEM)**(1/3)
LOST=1.0045925
def P(S): return (GM0/S)**3

def resid_frac(x):  # |x-round(x)| in [0,0.5]
    return abs(x-round(x))

bands=[("28.15-28.30",28.15,28.30),("28.30-28.60",28.30,28.60),("28.60-29.00",28.60,29.00),
       ("29.00-30.00",29.00,30.00),("30.00-31.00",30.00,31.00),("ALL>=28.15",28.15,99)]
print("band|n|medres_T|medres_Tlost|medres_Qdqi|medres_Qdqi_lost|medres_Qinv")
for name,lo,hi in bands:
    sub=[r for r in rows if lo<=r[2]<hi and abs(r[2]-28.14703)>1e-6 and abs(r[2]-28.15083)>1e-6]
    if not sub: continue
    rt=[];rtl=[];rd=[];rdl=[];ri=[]
    for _,_,S,_,_ in sub:
        p=P(S)
        rt.append(resid_frac(T0*p)); rtl.append(resid_frac(T0*p/LOST))
        rd.append(resid_frac(QD0*math.sqrt(p))); rdl.append(resid_frac(QD0*math.sqrt(p/LOST)))
        ri.append(resid_frac(QI0*p))
    m=lambda v: statistics.median(v)
    print("%s|%d|%.4f|%.4f|%.4f|%.4f|%.4f"%(name,len(sub),m(rt),m(rtl),m(rd),m(rdl),m(ri)))

print("\n# per-score DQI-Q residual detail, 28.15-29.30")
for rank,team,S,last,nsub in rows:
    if not (28.15<=S<=29.30): continue
    if abs(S-28.14703)<1e-6 or abs(S-28.15083)<1e-6: continue
    p=P(S); q=QD0*math.sqrt(p); q2=QD0*math.sqrt(p/LOST); T=T0*p; Tl=T0*p/LOST
    print("%d|%s|%.5f|Q=%.3f r=%.3f|Qlost=%.3f|T=%.2f r=%.2f|Tlost=%.2f r=%.2f"%(rank,team,S,q,resid_frac(q),q2,T,resid_frac(T),Tl,resid_frac(Tl)))
