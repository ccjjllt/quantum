"""Sanity: the shipped table, its exact decoded U, and the encode/decode round trip."""
import numpy as np
import sys
import json

sys.path.insert(0, '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work')
from common import decode, encode, check_tree

NPZ = '/Users/zhaohuaxiang/ccjjllt/quantum/experiments/frontier/20261118_push/tree/work/build/submission.npz'
z = np.load(NPZ, allow_pickle=False)
TREE = np.asarray(z['tree_edges'], np.int64)
WORDS = np.asarray(z['angle_words'], np.int64)
U = np.asarray(z['U'], np.float64)
N = U.shape[-1]
A = U.shape[0] * U.shape[1]
print('N', N, 'R*B', A, 'words', WORDS.shape, 'range', WORDS.min(), WORDS.max())
check_tree(TREE, N)
print('tree ok')

V = decode(WORDS, TREE, 8)
print('decode row-norm dev', float(np.max(np.abs(np.linalg.norm(V, axis=1) - 1))))
print('encode(decode)==words mismatches', int(np.sum(encode(V, TREE, 8) != WORDS)))
print('encode(U_exact) vs words mismatches', int(np.sum(encode(U.reshape(-1, N), TREE, 8) != WORDS[76:])))
d2 = V[76:] - U.reshape(-1, N)
print('||decode(words)[2body] - npz U||_F', float(np.linalg.norm(d2)),
      ' max|.|', float(np.max(np.abs(d2))))
print('||U_exact - V||_F total', float(np.linalg.norm(V[76:] - U.reshape(-1, N))))
# one-body rows of the shipped table
V1 = V[:76]
print('onebody |v| offdiag max', float(np.max(np.abs(V1) - np.eye(76))))
print('onebody words nonzero count', int(np.count_nonzero(WORDS[:76])))
print('onebody words per row nonzero (mean)', float(np.mean(np.count_nonzero(WORDS[:76], axis=1))))
print('2body words nonzero frac', float(np.count_nonzero(WORDS[76:]) / WORDS[76:].size))
# per-block-of-5 stats
blk = WORDS.reshape(1220, 15, 5)
nz = np.count_nonzero(blk.reshape(1220, 15, 5).transpose(1, 0, 2), axis=(1, 2))
print('nonzero words per block', nz.tolist())
# delta targets: block k xor block k-1
W = WORDS.astype(np.int64)
delta = W[:, 5:].reshape(1220, 14, 5).copy()
delta ^= W[:, :-5].reshape(1220, 14, 5)
print('delta nonzero frac', float(np.count_nonzero(delta) / delta.size))
dnz = np.count_nonzero(delta, axis=(0, 2))
print('delta nonzero per k>=1', dnz.tolist())
print('words zero count total', int(np.count_nonzero(WORDS == 0)), 'of', WORDS.size)
