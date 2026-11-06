"""Check whether exact zero vector components relax the five-quadratic gauge.

Uses integer words for exact sine/cosine zero support; no native simulation.
"""
import json,time
import numpy as np
from analyze import read_params,OUT

def insert(piv,v):
 while v:
  k=v.bit_length()-1
  if k not in piv:piv[k]=v;return
  v^=piv[k]

def in_span(piv,v):
 while v:
  k=v.bit_length()-1
  if k not in piv:return False
  v^=piv[k]
 return True

def main():
 start=time.monotonic();p=read_params();words=np.load(OUT/'recovered_words.npy')
 support=np.zeros((1220,76),dtype=bool);support[:,0]=True;paths={0:0}
 for j,(a,b) in enumerate(p['tree_edges']):
  a,b=int(a),int(b);assert not support[:,b].any()
  alive=support[:,a].copy();support[:,a]=alive&(words[:,j]%128!=64);support[:,b]=alive&(words[:,j]%128!=0)
  paths[a]^=1<<j;paths[b]=paths[a]
 masks=(3,5,6,9,10);piv={};constraints=0
 for x in range(1220):
  funcs=sum(int(x&m==m)<<i for i,m in enumerate(masks))
  active=np.flatnonzero(support[x]);base=paths[int(active[0])]
  for comp in active[1:]:
   path=paths[int(comp)]^base;v=0
   while path:
    bit=path&-path;j=bit.bit_length()-1;v|=funcs<<(5*j);path^=bit
   if v:insert(piv,v);constraints+=1
 forced_coeffs=[j for j in range(375) if in_span(piv,1<<j)]
 forced_angles=[j for j in range(75) if all(5*j+b in forced_coeffs for b in range(5))]
 out={'scope':'Exact-zero support of actual integer words; gauge functions restricted to span of masks3,5,6,9,10','constraints':constraints,'variables':375,'rank':len(piv),'nullity':375-len(piv),'forced_zero_angle_indices':forced_angles,'forced_zero_coefficient_count':len(forced_coeffs),'support_histogram':{str(n):int((support.sum(axis=1)==n).sum()) for n in np.unique(support.sum(axis=1))},'full_support_rows':int((support.sum(axis=1)==76).sum()),'seconds':time.monotonic()-start}
 (OUT/'support_gauge.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
