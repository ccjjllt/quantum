# SPDX-License-Identifier: Apache-2.0
"""Isolated adapter for Marsyas/Houssem Alayet's Apache-2.0 source."""
import argparse,json,os,sys,tempfile
from pathlib import Path
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--drop',type=int,default=1);ap.add_argument('--tables',type=Path);ap.add_argument('--virtual',action='store_true');a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=True);(a.work/'tmp').mkdir(exist_ok=True);tempfile.tempdir=str(a.work/'tmp')
 source=ROOT/'marsyas';sys.path.insert(0,str(source))
 import model as M,run,fit,hsplit as H
 M.CACHE=str(a.work/'ref.npz');run.WORK=str(a.work)
 orig=fit.fit_all
 fit.fit_all=lambda *args,**kw:orig(*args,**{**kw,'workers':min(8,int(os.environ.get('QCC_WORKERS','1')))})
 args=['28','19','8','1','sd=1','dropA=5','LB=21','S=20','mdel=1','wins=17:11,10;15:9,8;13:7,6;11:5,4;9:3,2;7:1,0',f'drop={a.drop}',f'out={a.out}']
 prm,_=run.parse(args)
 if a.tables:
  import numpy as np
  tables=np.array(json.loads(a.tables.read_text()),dtype=np.int64)
  np.save(a.work/f'tab_{run.tag(prm)}.npy',tables)
 if a.virtual:
  import numpy as np
  tables=run.get_tables(prm);changed=int((tables[:,0]&1).sum());tables[:,0]+=tables[:,0]&1
  np.save(a.work/f'tab_{run.tag(prm)}.npy',tables)
  print(json.dumps(dict(virtual_even_anchor_rounded_up=changed)),flush=True)
  import round5_virtual as V
  V.install(H)
 H.main(args)
 assert a.out.exists(),'Model calibration or build did not produce a candidate'
 import numpy as np
 tables=np.load(a.work/f'tab_{run.tag(prm)}.npy')
 (a.work/'tables.json').write_text(json.dumps(tables.tolist()))
 import exact
 exact.run(str(a.out),str(a.out.with_name('invsqrt.kmb')))
if __name__=='__main__':main()
