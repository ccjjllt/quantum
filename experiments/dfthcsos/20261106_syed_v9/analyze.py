"""Manual Syed V9 actual-word/resource study; no full verifier or source hashes."""
from pathlib import Path
import io,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'data/competition/verifiers'))
from dfthcsos.verify import SubmissionInputs,native_inputs,evaluate_words,resource_costs,heuristic_costs,passes_accuracy
from dfthcsos.scoreinfra.reference import load_reference,PACKAGED_FCIDUMP,PACKAGED_FIXED_SHIFTS,UPPER_ENERGY
from dfthcsos.scoreinfra.circuits import load_circuits,circuit_costs,recover_words_from_circuits
BASE=ROOT/'artifacts/20261106_syed_v9/release/dfthcsos'
OUT=ROOT/'artifacts/20261106_syed_v9/dfthcsos'

def read_params():
 with np.load(BASE/'submission.npz',allow_pickle=False) as f:p={k:np.array(f[k]) for k in f.files}
 with np.load(PACKAGED_FIXED_SHIFTS,allow_pickle=False) as f:p.update({k:np.array(f[k]) for k in ('H1_I','Hsym_lower')})
 return p

def inputs(p,ref):
 w,W,S,beta=native_inputs(p)
 return SubmissionInputs(BASE/'submission.npz',p,ref,w,W,S,beta,UPPER_ENERGY)

def rank(rows):
 piv={}
 for v in rows:
  v=int(v)
  while v:
   k=v.bit_length()-1
   if k not in piv:piv[k]=v;break
   v^=piv[k]
 return len(piv)

def xor(rows,m):
 a=0
 for i,v in enumerate(rows):
  if m>>i&1:a^=int(v)
 return a

def main():
 t=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
 p=read_params();circs=load_circuits(BASE);static=circuit_costs(circs)
 for row,c in zip(static,circs):row['gate_counts']=dict(c.operation_statistics())
 words,layout,angle_t=recover_words_from_circuits(circs,num_vectors=1220,num_angles=75,shots_per_address=1,seed=20261106)
 assert np.array_equal(words,p['angle_words'])
 np.save(OUT/'recovered_words.npy',words)
 ref=load_reference(PACKAGED_FCIDUMP);inp=inputs(p,ref)
 metrics=evaluate_words(inp,words,p['tree_edges'],layout.brot)
 costs=resource_costs(inp,circs,layout.brot,angle_t);cost=metrics['lambda_eff']*costs['qubits']*costs['toffoli']
 addr=np.arange(1220);quad=(3,5,6,9,10)
 funcs=np.stack([(addr&m)==m for m in quad],axis=1).astype(np.uint8)
 combos=np.stack([np.bitwise_xor.reduce(funcs[:,[i for i in range(5) if m>>i&1]],axis=1) if m else np.zeros(1220,dtype=np.uint8) for m in range(32)])
 high=((words>>7)^(words>>6))&1
 codes=[];unmatched=[]
 for j in range(75):
  hits=np.flatnonzero(np.all(combos==high[:,j],axis=1))
  if len(hits)==1:codes.append(int(hits[0]))
  else:codes.append(None);unmatched.append(j)
 geometry=[]
 if not unmatched:
  prev=[0]*5
  for k in range(15):
   curr=codes[5*k:5*k+5]
   common=rank([xor(prev,m) for m in range(32) if xor(prev,m)==xor(curr,m)])
   dirty=rank([a^b for a,b in zip(prev,curr)])
   geometry.append({'k':k,'common_rank':common,'dirty_rank':dirty,'codes':curr,'paid':static[k]['max_magic'],'qubits':static[k]['num_qubits']})
   prev=curr
 # Physical sign gauge: every final vector component must have same parity.
 paths={0:0}
 for j,(a,b) in enumerate(p['tree_edges']):
  a,b=int(a),int(b);paths[a]^=1<<j;paths[b]=paths[a]
 constraints=[paths[i]^paths[0] for i in range(1,76)];piv={}
 for v in constraints:
  while v:
   k=v.bit_length()-1
   if k not in piv:piv[k]=v;break
   v^=piv[k]
 for helper in range(5):
  mask=sum(((c>>helper)&1)<<j for j,c in enumerate(codes))
  assert all((mask&r).bit_count()%2==0 for r in constraints)
 free=[i for i in range(75) if i not in piv];basis=[]
 for j in free:
  v=1<<j
  for k in sorted(piv):
   if (piv[k]&v).bit_count()%2:v^=1<<k
  assert all((v&r).bit_count()%2==0 for r in constraints)
  basis.append(v)
 coords=[sum(((v>>i)&1)<<j for j,v in enumerate(basis)) for i in range(75)]
 available=[sum(bool(v) for v in coords[k:k+5]) for k in range(0,75,5)]
 capacity=[0]+[min(available[k-1],available[k]) for k in range(1,15)]
 physical={'dimension':len(free),'forced_zero_columns':[i for i,v in enumerate(coords) if not v],
           'available_topbit_coordinates':available,'common_rank_upper_by_batch':capacity,
           'common_rank_upper_total':sum(capacity),'nonzero_coordinate_count':sum(available),
           'permutation_capacity_upper':sum(available)-int(np.ceil(sum(available)/15)),
           'current_saturates_coordinate_bound':sum(g['common_rank'] for g in geometry)==sum(capacity),
           'scope':'Fixed Givens tree/order, five-word batches, and helpers carried only in bit7 XOR bit6. Does not bound alternate trees/orders/bits or other arithmetic.'}
 def scenario(c=44,b=143,j=5,beta=8):
  h=heuristic_costs(76,8,b,c,beta);q=h['qubits']+j*beta;tt=h['toffoli']+angle_t
  ratio=q*tt/(costs['qubits']*costs['toffoli'])
  return {'C':c,'B':b,'J':j,'brot':beta,'Q':q,'T_assuming_angle_unchanged':tt,'cost_ratio_fixed_lambda':ratio,'lambda_increase_budget':1/ratio-1,'break_even_angles_T':costs['qubits']*costs['toffoli']/q-h['toffoli']}
 out={'scope':'1220 addresses x one forward/reverse trajectory; official numerical/cost functions; not full official validation', 'source':'Syed notebook V9/run366109544, dataset V9', 'actual_recovered_words_equal_npz':True,'static':static,'metrics':metrics,'math_accuracy_pass':bool(passes_accuracy(metrics)),'margins_microHa':{'e1':(0.02-metrics['error_1'])*1e6,'e2':(0.02-metrics['error_2'])*1e6,'gap':(metrics['E_gap']-3.914898)*1e6},'resources':costs,'cost':cost,'five_helper_fit':{'masks':quad,'unmatched_columns':unmatched,'geometry':geometry,'common_total':sum(g['common_rank'] for g in geometry),'abstract_five_basis_upper':70,'physical_coordinate_bound':physical,'scope':'A model with these five prescribed quadratics and fixed five-word batches only; no global circuit bound'},'C_sweep':[scenario(c=c) for c in (39,40,41,42,43,44,45,46)],'B_sweep':[scenario(b=b) for b in (127,128,135,142,143,144,151)],'J_sweep':[scenario(j=j) for j in (3,4,5,6,8)],'precision_sweep':[scenario(beta=b) for b in (7,8,9)],'elapsed_s':time.monotonic()-t}
 (OUT/'analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
