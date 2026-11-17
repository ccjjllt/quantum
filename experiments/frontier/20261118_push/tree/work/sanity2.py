import numpy as np
import sys
sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
from common import decode, encode, check_tree

NPZ = '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work/build/submission.npz'
z = np.load(NPZ, allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
WORDS = np.asarray(z['angle_words'], np.int64)
U = np.asarray(z['U'], np.float64).reshape(-1, 76)
V = decode(WORDS, TREE, 8)

W2 = encode(V, TREE, 8)
print('mismatch 1body', int(np.sum(W2[:76] != WORDS[:76])), 'of', 76 * 75)
print('mismatch 2body', int(np.sum(W2[76:] != WORDS[76:])), 'of', 1144 * 75)
print('decode(encode(V)) - V  max', float(np.max(np.abs(decode(W2, TREE, 8) - V))))

# sparsity of the decoded rows
sp = np.count_nonzero(np.abs(V) > 1e-12, axis=1)
print('1body support: min/mean/max', sp[:76].min(), sp[:76].mean(), sp[:76].max())
print('2body support: min/mean/max', sp[76:].min(), sp[76:].mean(), sp[76:].max())
ov = V[76:] @ U.T
print('overlap |diag| mean', float(np.mean(np.abs(np.diag(ov)))))
print('overlap |offdiag| rms', float(np.sqrt(np.mean(ov ** 2) - np.mean(np.diag(ov) ** 2))))
print('row-norm U', float(np.max(np.abs(np.linalg.norm(U, axis=1) - 1))))
# is V2 = V a row-sign/permutation of U?
a = np.abs(V[76:] @ U.T)
print('frac rows with max overlap > 0.999', float(np.mean(a.max(axis=1) > 0.999)))
print('argmax unique?', len(set(a.argmax(axis=1).tolist())))
print('top-5 row max overlaps', np.sort(a.max(axis=1))[-5:])
