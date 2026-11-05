"""Batch fullcone prover (in-process loop, subprocess isolation per candidate via os.fork-free sequential).
Usage: batch_prove.py KMX OFFS BATCH_JSON OUT_JSON TL"""
import sys, json, subprocess
SATPY='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/satenv/bin/python'
WORK='experiments/dqi/20261106_stagebulk/fullcone.py'
KMX,OFFS,BATCH,OUT,TL=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
batch=json.load(open(BATCH))
res=[]
for k,c in enumerate(batch):
    cj='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/bc%d.json'%k
    oj='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/bc%d.out.json'%k
    json.dump(c,open(cj,'w'))
    try:
        p=subprocess.run([SATPY,WORK,KMX,OFFS,cj,oj,TL],capture_output=True,text=True,timeout=int(TL)+300)
        print('---',k,p.stdout.strip().split(chr(10))[-3:],flush=True)
        r=json.load(open(oj)); r['idx']=k
    except Exception as e:
        r={'idx':k,'status':'ERROR:'+str(e)[:120],'cand':c}
    res.append(r); print(k,r,flush=True)
json.dump(res,open(OUT,'w'),indent=1)
