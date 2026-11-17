import csv, math, statistics, sys, json

PATH = "/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261117_lb_decomp/google-verifiable-quantum-circuit-compilation-publicleaderboard-2026-11-17T03:30:55.csv"
R1, R2, R3 = 2076774.233715, 24439463583672.93, 3355599588.3155375

rows = []
with open(PATH, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(dict(rank=int(r["Rank"]), team=r["TeamName"].strip(),
                         last=r["LastSubmissionDate"], score=float(r["Score"]),
                         nsub=int(r["SubmissionCount"]),
                         members=(r["TeamMemberUserNames"] or "").strip()))

print("teams:", len(rows), "max rank", rows[-1]["rank"])
top = rows[:100]
print("score range top100:", top[0]["score"], top[-1]["score"])
print("score range all:", rows[0]["score"], rows[-1]["score"])

# legs (our frontier, 2026-11-17)
INV = 74797.36535717871
DQI = 346413579540.4963      # 61c8348d salt-clean draw
CHEM = 294643137.73357135    # a73b25d2 T=14706
CHEM_ALT = 294762512.64351326  # 93326853 T=14712 (salt-invariant)
GM0 = (R1/INV * R2/DQI * R3/CHEM) ** (1/3)
print("GM0:", GM0)

# chem 1/T fit
k1 = CHEM * 14706
k2 = CHEM_ALT * 14712
print("k(T14706)=%.6f k(T14712)=%.6f ratio=%.9f" % (k1, k2, k2/k1))
k = 0.5*(k1+k2)
print("k mean", k)
# also affine fit cost = a/T + b through both points
# c1 = a/14706 + b ; c2 = a/14712 + b
c1, c2 = CHEM, CHEM_ALT
a = (c1-c2)/(1/14706 - 1/14712)
b = c1 - a/14706
print("affine a,b", a, b, "a/T at 14706 =", a/14706)

def inv_cost(S):
    P = (GM0/S)**3
    return INV*P
def dqi_cost(S):
    P = (GM0/S)**3
    return DQI*P
def chem_cost(S):
    P = (GM0/S)**3
    return CHEM*P

def q_inv(c):   # linear cost per qubit
    return 44.0*c/INV
def q_dqi(c):   # cost ~ Q^2
    return 890.0*math.sqrt(c/DQI)

print("\n# top 20")
for r in rows[:20]:
    print(r["rank"], r["score"], r["last"], r["nsub"], r["team"])

# band distribution 28.0-31.0, 0.05 wide
print("\n# bands 28.0-31.0")
lo = 28.0
while lo < 31.0 - 1e-9:
    hi = lo + 0.05
    cnt = sum(1 for r in rows if lo - 1e-12 <= r["score"] < hi - 1e-12)
    # note: bands half-open
    print("%.2f-%.2f\t%d" % (lo, hi, cnt))
    lo = hi

print("\n# above thresholds")
for t in [28.0,28.05,28.1,28.13,28.15083,28.2,28.3,28.4,28.5,28.6,28.68633,28.7,28.8,28.9,29.0,29.2,29.5,30.0,30.2,30.5,30.96,30.97]:
    print(t, sum(1 for r in rows if r["score"] >= t))

# bands table with inversions
print("\n# inversion table")
BANDS = [28.1, 28.2, 28.3, 28.4, 28.5, 28.55, 28.6, 28.65, 28.68633, 28.7, 28.8, 28.9,
         29.0, 29.1, 29.2, 29.3, 29.5, 29.75, 30.0, 30.28512, 30.5, 30.78291, 30.96223, 30.96645]
for S in BANDS:
    P = (GM0/S)**3
    ci, cd, cc = inv_cost(S), dqi_cost(S), chem_cost(S)
    print("S=%.5f P=%.6f dP=%+.3f%% inv=%.3f Q=%.3f dqi=%.4e Q=%.2f chem=%.3f T(k=mean)=%.2f T(affine)=%.2f" %
          (S, P, (P-1)*100, ci, q_inv(ci), cd, q_dqi(cd), cc, k/cc, (a/cc)+b if False else a/(cc-b)))

# exact-score clusters among 28.0+
from collections import Counter
c = Counter(round(r["score"],5) for r in rows if r["score"]>=28.0)
print("\n# clusters >=3 at 28.0+ (score, count), top 40 by count")
for s,n in c.most_common(40):
    if n>=3: print(s, n)
