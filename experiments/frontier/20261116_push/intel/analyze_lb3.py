import csv, math
PATH = "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261117_lb_decomp/google-verifiable-quantum-circuit-compilation-publicleaderboard-2026-11-17T03:30:55.csv"
R1, R2, R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375
rows = []
with open(PATH, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(dict(rank=int(r["Rank"]), team=r["TeamName"].strip(),
                         last=r["LastSubmissionDate"], score=float(r["Score"]),
                         nsub=int(r["SubmissionCount"])))
INV=74797.36535717871; DQI=346413579540.4963; CHEM=294643137.73357135
T0, QI0, QD0 = 14706.0, 44.0, 890.0
GM0=(R1/INV*R2/DQI*R3/CHEM)**(1/3)
LOST = 1.0045925

def P(S): return (GM0/S)**3

# chem lattice under 4 assumptions on other legs
print("### chem-integer lattice, all scores >= 28.15 (top 77)")
print("score|team|T_clean|resid_clean|T_lost|resid_lost|T_14712base|resid")
hits=0; n=0
for r in rows:
    S=r["score"]
    if S<28.15: continue
    n+=1
    p=P(S)
    T1=T0*p; T2=T0*p/LOST; T3=14712.0*p
    r1=abs(T1-round(T1)); r2=abs(T2-round(T2)); r3=abs(T3-round(T3))
    best=min(r1,r2,r3)
    if best<0.10: hits+=1
    print("%.5f|%s|%.3f|%.3f|%.3f|%.3f|%.3f|%.3f%s" % (S,r["team"],T1,r1,T2,r2,T3,r3,"  **" if best<0.05 else ""))
print("hits<0.10: %d / %d ; expected uniform %.1f" % (hits,n,0.2*n))

print("\n### DQI-integer lattice (Q at integer), scores >=28.15")
hits=0
for r in rows:
    S=r["score"]
    if S<28.15: continue
    p=P(S)
    q1=QD0*math.sqrt(p); q2=QD0*math.sqrt(p/LOST)
    r1=abs(q1-round(q1)); r2=abs(q2-round(q2))
    if min(r1,r2)<0.15:
        hits+=1
        print("%.5f|%s|Q=%.3f(r%.3f)|Qlost=%.3f(r%.3f)"%(S,r["team"],q1,r1,q2,r2))
print("hits<0.15:",hits,"of",n,"expected",0.3*n)

print("\n### invsqrt-integer lattice, scores >=28.15")
hits=0
for r in rows:
    S=r["score"]
    if S<28.15: continue
    p=P(S); q=QI0*p; rr=abs(q-round(q))
    if rr<0.03:
        hits+=1; print("%.5f|%s|Q=%.4f(r%.4f)"%(S,r["team"],q,rr))
print("hits<0.03:",hits,"of",n,"expected",0.06*n)

# exact matches against known inventory
INVS={"0af21cb8":74797.36535717871,"5eeea23b":75006.40286232081,"f2cdab0b":75006.37653863191,
      "8b410e77":75038.1340,"2c125b39":75082.0925}
DQIS={"61c8348d_clean":346413579540.4963,"61c8348d_def":348004440260.464,
      "b0983d55":347045216047.3212,"66b4f18b":347128304010.81165,"f425ea20":346992317312.81555,
      "00ac37d4":347357914646.9683,"ccc2ab84":347375470571.73334,"957d6733":348246849661.4793,
      "4b350932":347760709936.55,"46446af1":347904227555.54,"821bf8d1":360209905486.02}
CHEMS={"a73b25d2_T14706":294643137.73357135,"93326853":294762512.64351326,
       "703843d3":294762512.8596263,"sub1":294762697.4384,"f6e12f02":294762732.9776,
       "894aef42":294762738.8257}
print("\n### exact match of any known triple to any LB score (5dp)")
combos={}
for a,ca in INVS.items():
    for b,cb in DQIS.items():
        for c,cc in CHEMS.items():
            g=(R1/ca*R2/cb*R3/cc)**(1/3)
            combos[round(g,5)]=(a,b,c,g)
mx=rows[0]["score"]+1e-9
for r in rows:
    key=round(r["score"],5)
    if key in combos and r["score"]>=27.9:
        a,b,c,g=combos[key]
        print("%.5f rank %d %s -> %s + %s + %s (gm %.6f)"%(r["score"],r["rank"],r["team"],a,b,c,g))
