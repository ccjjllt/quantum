"""Batch wireprove (subprocess isolation per candidate). Usage: batch_wire.py CANDS OUT TL"""
import json, subprocess, sys
SATPY='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/satenv/bin/python'
WORK='experiments/dqi/20261106_stagebulk/wireprove.py'
KMX='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi.kmx'
OFFS='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/offs.json'
CANDS,OUT,TL=sys.argv[1],sys.argv[2],sys.argv[3]
cands=json.load(open(CANDS))
res=[]
for k,c in enumerate(cands):
    cj='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/wc%d.json'%k
    oj='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/wc%d.out.json'%k
    json.dump(c,open(cj,'w'))
    try:
        p=subprocess.run([SATPY,WORK,KMX,OFFS,cj,oj,TL],capture_output=True,text=True,timeout=int(TL)+300)
        print('---',k,p.stdout.strip().split(chr(10))[-2:],flush=True)
        r=json.load(open(oj)); r['idx']=k
    except Exception as e:
        r={'idx':k,'status':'ERROR:'+str(e)[:120]}
    res.append(r); print(k,r,flush=True)
json.dump(res,open(OUT,'w'),indent=1)
