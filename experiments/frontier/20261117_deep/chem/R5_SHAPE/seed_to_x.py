import numpy as np, sys
src=sys.argv[1]; dst=sys.argv[2]
z=np.load(src); U=z['U']; W=z['W']; R,B,N=U.shape; C=W.shape[2]
x=np.concatenate([W.ravel(),U.ravel()])
np.savez_compressed(dst,x=x,R=R,B=B,C=C)
print(dst,R,B,C)
