"""Bounded own-code coefficient experiments at fixed Syed V9 angle words.

Exact two-column orthogonal-gauge minima and one C43 spectral deletion.
Does not execute external code or official verification. No changed circuit.
"""
from pathlib import Path
import json,time
import numpy as np
from analyze import read_params,inputs,OUT,BASE
from dfthcsos.verify import evaluate_words,passes_accuracy
from dfthcsos.scoreinfra.reference import load_reference,PACKAGED_FCIDUMP
from dfthcsos.scoreinfra.dfthc_math import reconstruct_u_vectors,reconstruct_x


def pair_minimum(a,b):
 # Over theta in [0,pi/2], the objective is piecewise P+Qcos2t+Rsin2t.
 # Roots of a*cos+b*sin or -a*sin+b*cos determine every sign cell.
 roots=np.concatenate((np.arctan2(-a,b)%np.pi,np.arctan2(b,a)%np.pi))
 roots=np.unique(np.r_[0.0,roots[(roots>0)&(roots<np.pi/2)],np.pi/2])
 mid=(roots[:-1]+roots[1:])/2;co=np.cos(mid);si=np.sin(mid)
 sx=np.sign(a[:,None]*co+b[:,None]*si)
 sy=np.sign(-a[:,None]*si+b[:,None]*co)
 A=a@sx;B=b@sx;C=b@sy;D=-a@sy
 Q=(A*A+C*C-B*B-D*D)/2;R=A*B+C*D
 # Minima repeat pi; max/min alternate every pi/2.
 stationary=(np.arctan2(R,Q)+np.pi)/2
 stationary=stationary%(np.pi)
 valid=(stationary>roots[:-1])&(stationary<roots[1:])
 angles=np.r_[roots,stationary[valid]]
 x=a[:,None]*np.cos(angles)+b[:,None]*np.sin(angles)
 y=-a[:,None]*np.sin(angles)+b[:,None]*np.cos(angles)
 values=(np.abs(x).sum(axis=0)**2+np.abs(y).sum(axis=0)**2)/4
 i=int(np.argmin(values))
 base=(np.abs(a).sum()**2+np.abs(b).sum()**2)/4
 return float(base-values[i]),float(angles[i]),len(angles)


def main():
 start=time.monotonic();p=read_params();words=np.load(OUT/'recovered_words.npy');ref=load_reference(PACKAGED_FCIDUMP)
 original=evaluate_words(inputs(p,ref),words,p['tree_edges'],8)
 rows=[];evaluations=0;spotchecks=[]
 for rho in range(8):
  factors=np.vstack((p['W'][rho],p['H2_I'][rho]))
  best={'rho':rho,'lambda_h2_drop':0.0,'columns':None,'angle':0.0}
  count=0
  for i in range(44):
   for j in range(i+1,44):
    gain,theta,n=pair_minimum(factors[:,i],factors[:,j]);evaluations+=n;count+=1
    if gain>best['lambda_h2_drop']:best.update(lambda_h2_drop=gain,columns=[i,j],angle=theta)
  # Independent dense-angle cross-check on fixed pairs, not an optimization result.
  for i,j in ((0,1),(3,17),(21,43)):
   a,b=factors[:,i],factors[:,j];gain,theta,_=pair_minimum(a,b)
   angles=np.linspace(0,np.pi/2,1001)
   x=a[:,None]*np.cos(angles)+b[:,None]*np.sin(angles)
   y=-a[:,None]*np.sin(angles)+b[:,None]*np.cos(angles)
   vals=(np.abs(x).sum(axis=0)**2+np.abs(y).sum(axis=0)**2)/4
   base=(np.abs(a).sum()**2+np.abs(b).sum()**2)/4
   gap=float(base-gain-vals.min());assert gap<1e-10
   spotchecks.append({'rho':rho,'pair':[i,j],'analytic_min_minus_grid_min':gap})
  best['pairs']=count;rows.append(best);print(json.dumps(best),flush=True)
 best=max(rows,key=lambda r:r['lambda_h2_drop'])
 gauge={'scope':'All 8*44*43/2 coordinate-plane rotations at fixed words, all piecewise sign intervals; floating-point computation, not a global orthogonal-group optimum','by_rho':rows,'total_pairs':8*44*43//2,'angle_candidates':evaluations,'best':best,'dense_angle_spotchecks':spotchecks}
 if best['lambda_h2_drop']>1e-10:
  q={k:v.copy() for k,v in p.items()};rho=best['rho'];i,j=best['columns'];co=np.cos(best['angle']);si=np.sin(best['angle'])
  for key in ('W','H2_I'):
   a=q[key][rho,...,i].copy();b=q[key][rho,...,j].copy();q[key][rho,...,i]=co*a+si*b;q[key][rho,...,j]=-si*a+co*b
  met=evaluate_words(inputs(q,ref),words,p['tree_edges'],8)
  gauge['best_metrics']=met;gauge['accuracy_math_pass']=bool(passes_accuracy(met));gauge['lambda_eff_drop']=original['lambda_eff']-met['lambda_eff']
  if passes_accuracy(met) and gauge['lambda_eff_drop']>1e-7:
   np.savez(OUT/'gauge_candidate.npz',**q);gauge['candidate_saved']=True
 # C43: rotate the weakest X direction to last column with a Householder,
 # then remove it in every rho. This preserves the rest as much as possible.
 vectors=reconstruct_u_vectors(words/128.0,p['tree_edges'])[76:].reshape(8,143,76)
 X=reconstruct_x(vectors,p['W']);q={k:v.copy() for k,v in p.items()};spectrum=[]
 for rho in range(8):
  a=X[rho].reshape(44,-1);eig,U=np.linalg.eigh(a@a.T);v=U[:,0];e=np.zeros(44);e[-1]=1
  d=v-e
  H=np.eye(44) if np.dot(d,d)<1e-28 else np.eye(44)-2*np.outer(d,d)/np.dot(d,d)
  q['W'][rho]=p['W'][rho]@H;q['H2_I'][rho]=p['H2_I'][rho]@H
  spectrum.append({'rho':rho,'smallest_eigenvalues':eig[:5].tolist(),'largest_eigenvalue':float(eig[-1]),'weakest_X_norm_sq':float(eig[0]),'native_offset_after_rotation':float(q['H2_I'][rho,-1]-q['W'][rho,:,-1].sum())})
 q['W']=q['W'][...,:43];q['H2_I']=q['H2_I'][...,:43]
 metrics=evaluate_words(inputs(q,ref),words,p['tree_edges'],8)
 trunc={'scope':'One spectral C44-to-C43 deletion with fixed actual loaded vectors, no refit; failures only reject this initialization','spectra':spectrum,'metrics':metrics,'accuracy_math_pass':bool(passes_accuracy(metrics))}
 # Is independent vector deletion necessary? Report native numerical sparsity.
 w=p['W'];h=p['H2_I'];t=h-w.sum(axis=1)
 out={'scope':'Numerical fixed-word research probes, not full official verification','baseline':original,'orthogonal_gauge':gauge,'C43_spectral_deletion':trunc,'sparsity':{'w_exact_zeros':int((w==0).sum()),'w_total':w.size,'w_small_1e_12':int((np.abs(w)<1e-12).sum()),'H2_I_exact_zeros':int((h==0).sum()),'native_offset_norm_sq':float(np.sum(t*t))},'seconds':time.monotonic()-start}
 (OUT/'column_probes.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'best':best,'gauge':gauge.get('lambda_eff_drop'), 'C43':metrics,'seconds':out['seconds']}),flush=True)
if __name__=='__main__':main()
