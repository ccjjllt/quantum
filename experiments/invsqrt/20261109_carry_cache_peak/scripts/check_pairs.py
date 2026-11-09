import kickmix as km, io, pickle
import numpy as np
c=km.Circuit.from_file('artifacts/20261108_public_frontier/release/invsqrt.kmb')
buf=io.StringIO(); c.to_file(buf, format='kmx')
ops=[l for l in buf.getvalue().splitlines() if l and not l.startswith(('APPEND','REGISTER'))]
raw=pickle.load(open('/tmp/snaps.pkl','rb'))
n_words=len(raw[25512][0])//8
snaps={k:[np.frombuffer(b,dtype=np.uint64).copy() for b in v] for k,v in raw.items()}
def words(w,idx): return snaps[idx][w]
def alleq(a,b): return all((x==y) for x,y in zip(a,b))
def allzero(a): return not any(a)
pairs=[('CCX q0 q59 q21',25512,28198),('CCX q4 q51 q21',25641,27995),
 ('CCX q41 q30 q51',25323,25615),('CCX q46 q30 q41',25629,27998),
 ('CCX q7 q57 q21',25670,28028),('CCX q10 q61 q21',25699,28074),
 ('CCX q21 q26 q41',25704,28079),('CCX q50 q47 q41',28031,28126),
 ('CCX q57 q56 q28',28035,28129),('CCX q51 q31 q28',28001,28160)]
for k,a,b in pairs:
    s1,s2,t=[int(x[1:]) for x in k.split()[1:]]
    e1=[alleq(words(s1,a),words(s1,b)),alleq(words(s2,a),words(s2,b))]
    print(k,'controls_equal=',e1,'target_equal=',alleq(words(t,a),words(t,b)))
    # untouched wires in (a,b) + zero at a
    untouched=[]
    for w in range(62):
        wq=f'q{w}'
        hit=False
        for i in range(a+1,b):
            l=ops[i]
            if l.startswith(('PUSH','POP')): continue
            p=l.split()
            if wq in p[1:]:
                hit=True; break
        if not hit:
            untouched.append((w, allzero(words(w,a))))
    print('   untouched wires (w, zero_at_a):', untouched)
