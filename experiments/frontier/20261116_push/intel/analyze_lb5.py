import math
R1,R2,R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375
INV=74797.36535717871; DQI=346413579540.4963; CHEM=294643137.73357135
T0,QI0,QD0=14706.0,44.0,890.0
CT=CHEM/T0; CI=INV/QI0
GM0=(R1/INV*R2/DQI*R3/CHEM)**(1/3)
def P(S): return (GM0/S)**3
def row(S):
    p=P(S)
    return (S,p,(p-1)*100,INV*p,(INV*p)/CI,DQI*p,QD0*math.sqrt(p),CHEM*p,(CHEM*p)/CT,
            DQI*p/(QD0**2), 1/math.sqrt(p))
print("GM0=%.12f CT=%.6f CI=%.6f"%(GM0,CT,CI))
print("score|P|dP%|invC|invQ|invC@44|dqiC|dqiQ|dqiTbar_ratio|chemC|chemT")
for S in [28.05,28.10,28.15,28.15083,28.2,28.3,28.4,28.5,28.6,28.65,28.68633,28.7,28.8,28.9,
          28.92164,29.0,29.14389,29.21549,29.3,29.5,29.57281,29.75,29.7975,29.979,30.0,30.00881,
          30.13063,30.28512,30.5,30.78291,30.96223,30.96645]:
    S,p,d,ic,iq,dc,dq,cc,ct,dq2,tr=row(S)
    print("%.5f|%.6f|%+.3f|%.2f|%.3f|%.2f|%.4e|%.2f|%.4f|%.2f|%.2f"%(S,p,d,ic,iq,ic/44,dc,dq,tr,cc,ct))

print("\n# conditional chem T table")
scores=[28.68633,29.0,29.21549,30.00881,30.28512,30.78291,30.96645]
combos=[(44,890),(44,880),(44,870),(44,860),(44,850),(44,840),(43,890),(42,890),(42,870),(42,860),(41,890),(40,890),(40,840)]
print("Qinv|Qdqi|"+"|".join("%.5f"%s for s in scores))
for qi,qd in combos:
    vals=[]
    for S in scores:
        ratio=P(S)/((qi/QI0)*((qd/QD0)**2))
        vals.append(T0*ratio)
    print("%d|%d|"%(qi,qd)+"|".join("%.1f"%v for v in vals))

print("\n# conditional DQI Q table (fixed inv, chem T)")
Ts=[14706,14500,14000,13500,13219,13000,12500,12000,11500,11000]
print("chemT|"+"|".join("%.5f"%s for s in scores))
for T in Ts:
    vals=[]
    for S in scores:
        ratio=P(S)/(T/T0)
        vals.append(QD0*math.sqrt(ratio))
    print("%d|"%T+"|".join("%.1f"%v for v in vals))

print("\n# conditional invsqrt Q table (fixed DQI, chem T)")
print("chemT|"+"|".join("%.5f"%s for s in scores))
for T in Ts:
    vals=[]
    for S in scores:
        ratio=P(S)/(T/T0)
        vals.append(QI0*ratio)
    print("%d|"%T+"|".join("%.1f"%v for v in vals))

print("\n# single-leg ceilings (GM if that leg alone moves to floor)")
for name,c in [("inv40",40/44),("inv42",42/44),("inv43",43/44),("dqi840",(840/890)**2),("dqi850",(850/890)**2),
               ("dqi860",(860/890)**2),("dqi870",(870/890)**2),("dqi880",(880/890)**2),
               ("chem14000",14000/14706),("chem13500",13500/14706),("chem13219",13219/14706),
               ("chem13000",13000/14706),("chem12500",12500/14706),("chem12000",12000/14706),("chem11048",11048/14706)]:
    print("%s -> GM %.5f (factor %.6f)"%(name, GM0*(1/c)**(1/3), c))

print("\n# max no-chem score (inv40 x dqi840)")
print("GM = %.5f"%(GM0/((40/44)*((840/890)**2))**(1/3)))
print("# chem T needed at (inv40,dqi840) for targets")
for S in scores:
    print("%.5f -> T=%.1f"%(S, T0*P(S)/((40/44)*((840/890)**2))))
