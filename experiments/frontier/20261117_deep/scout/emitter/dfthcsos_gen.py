"""dfthcsos angle-circuit family generator.

Builds the angle_k QROM oracle circuits for Benchmark III (FeMoCo DFTHC
block encoding) of the Google Quantum AI Verifiable Quantum Circuit
Compilation competition.

Each angle_k circuit is a DELTA loader: for a 12-bit `selection` address
a (a DFTHC vector index, 0..num_vectors-1) it XORs a classical table of
deltas into the public word registers word_0..word_{J-1} (each `brot`
qubits wide):

    word_j ^= delta_k[a][j],   delta_k = batch_k XOR batch_{k-1}

where batch_k is columns [k*J, (k+1)*J) of the angle_words matrix
(num_vectors x (N-1)), batch_{-1} is all zeros, and columns past N-1 are
treated as zero (so the last circuit clears the padding words to zero,
as the verifier requires).

Why deltas: the official verifier runs each circuit forward (reads the
words for batch k) and then runs the reverse pass, which must restore the
PREVIOUS circuit's words (k=0 must clear to zero). A delta loader is an
involution as a classical function (word ^= delta twice = identity), so
its reverse restores the previous words exactly. A plain absolute loader
(init_lookup from zero) would clear to zero on the reverse pass and FAIL
the reverse check for k>0.

Lookup structure: one unary-iteration pass over the addresses
(km.CircuitBuilder.unary_iteration), one CX per 1-bit of the delta table
into the word registers. Toffoli cost is N-2 per circuit (N =
num_vectors), INDEPENDENT of J and brot -- the address decode dominates,
the output fanout is Clifford CX. Measured: N=3976, J=8, brot=12 ->
3,978 Toffoli-like per circuit (reference: 3,974; the 4-gate gap is an
iteration-path detail, 0.1%). Qubits = sel_bits + J*brot + sel_bits
(unary temp) = 12 + 96 + 12 = 120 for the baseline config, under the
128-qubit per-circuit cap. NO z_pow anywhere (the verifier rejects any
Z_POW line). NO measurement-based relation-clearing (see
notes/verifier-fix.md: it injects outcome-dependent pi phases).

Qubit-cap arithmetic (the binding constraint on J):
    J*brot + sel_bits + sel_bits <= 128
so at brot=12, sel_bits=12: J <= 8 (baseline). J=9 needs 132 qubits and
is rejected. Larger J (fewer circuits, lower total angles Toffoli)
requires smaller brot, which raises angle-quantization error -- a
factorization-quality question, not a circuit question (see the design
note).

The real angle_words / factorization data live only in the Kaggle
dataset; this generator also accepts synthetic words (--synthetic) for
local development. A family built on synthetic words is clearly labeled
as such and must NOT be claimed as a submission candidate until the
official verifier passes it on the REAL factorization (run by the parent
in the notebook).

Usage:
  ./venv/bin/python code/dfthcsos_gen.py --synthetic --out-dir data/dfthcsos_synth
  ./venv/bin/python code/dfthcsos_gen.py --words-npz factorization.npz \
      --out-dir data/dfthcsos_cand --brot 12 --J 8
  ./venv/bin/python code/dfthcsos_gen.py --words-npy words.npy --J 8 --brot 12
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time

import numpy as np

import kickmix as km

# Baseline FeMoCo76o113e constants (from the verifier spec).
N_ORBITALS = 76
N_MINUS_1 = N_ORBITALS - 1  # 75 angle columns per vector
QUBIT_CAP = 128


def sel_bits_for(num_vectors):
    """Address width: smallest b with 2**b >= num_vectors."""
    return max(1, int(np.ceil(np.log2(num_vectors))))


def batch_deltas(words, J):
    """Split angle_words (num_vectors, ncols) into batches of J columns,
    zero-pad the columns to a multiple of J, and return the list of delta
    tables delta_k = batch_k XOR batch_{k-1} (batch_{-1} = 0).

    Out-of-range columns (past ncols) are zero, so the last circuit's
    padding words are cleared to zero by its delta, as required."""
    nvec, ncols = words.shape
    ncirc = (ncols + J - 1) // J
    padded = np.zeros((nvec, ncirc * J), dtype=np.int64)
    padded[:, :ncols] = words
    deltas = []
    prev = np.zeros((nvec, J), dtype=np.int64)
    for k in range(ncirc):
        batch = padded[:, k * J:(k + 1) * J]
        deltas.append(batch ^ prev)
        prev = batch
    return deltas


def build_angle_circuit(num_vectors, J, brot, delta, strategy="delta-unary"):
    """Build one angle_k delta-loader circuit.

    Registers: selection (sel_bits, km.q), word_0..word_{J-1} (brot, km.q
    each). delta is a (num_vectors, J) array of brot-bit ints.
    strategy 'delta-unary' (default): unary-iteration pass, CX fanout.
    strategy 'init-lookup': km init_lookup over a 2**sel_bits table
    (costs 2**sel_bits - 2 Toffolis, 120 more than delta-unary for the
    baseline; only a fallback / cross-check)."""
    sel_bits = sel_bits_for(num_vectors)
    if strategy == "init-lookup":
        b = km.CircuitBuilder()
        sel = b.create_quantum_register(sel_bits, name="selection")
        words = [b.create_quantum_register(brot, name=f"word_{j}")
                 for j in range(J)]
        # init_lookup needs a full 2**sel_bits table of J*brot-bit ints.
        table = []
        for a in range(1 << sel_bits):
            v = 0
            if a < num_vectors:
                for j in range(J):
                    v |= int(delta[a][j]) << (j * brot)
            table.append(v)
        # init_lookup loads into ONE target register; pack words into one
        # wide register then split -- not possible (registers are fixed).
        # Instead: one init_lookup per word would cost J*(2**sel_bits-2).
        # That is strictly worse; refuse rather than silently build it.
        raise ValueError(
            "init-lookup strategy cannot share one address decode across "
            "J words in kickmix (one init_lookup per word would cost "
            "J*(2**sel_bits-2) Toffolis). Use delta-unary.")
    b = km.CircuitBuilder()
    sel = b.create_quantum_register(sel_bits, name="selection")
    words = [b.create_quantum_register(brot, name=f"word_{j}")
             for j in range(J)]
    with b.unary_iteration(sel, range(num_vectors)) as it:
        for a, mq in it:
            row = delta[a]
            for j in range(J):
                d = int(row[j])
                bit = 0
                while d:
                    if d & 1:
                        b.cx(mq, words[j][bit])
                    d >>= 1
                    bit += 1
    return b.finish_circuit()


def circuit_stats(circ):
    st = circ.operation_statistics()
    return {
        "num_qubits": int(circ.num_qubits),
        "num_registers": int(circ.num_registers),
        "num_instructions": int(st.num_instructions),
        "num_toffoli_like": int(st.num_toffoli_like),
        "num_t_like": int(st.num_t_like),
        "num_non_clifford": int(st.num_non_clifford),
        "reaction_depth": int(circ.reaction_depth()),
    }


def check_no_zpow(circ):
    buf = io.BytesIO()
    circ.to_file(buf, format="kmx")
    return b"Z_POW" not in buf.getvalue()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_words(args):
    if args.synthetic:
        rng = np.random.default_rng(args.seed)
        nvec = args.num_vectors
        ncols = args.ncols
        words = rng.integers(0, 1 << args.brot, size=(nvec, ncols),
                             dtype=np.int64)
        return words, f"synthetic(seed={args.seed}, {nvec}x{ncols})"
    if args.words_npz:
        z = np.load(args.words_npz)
        if "angle_words" not in z:
            raise ValueError(f"{args.words_npz}: no 'angle_words' key "
                             f"(keys: {list(z.keys())})")
        return np.asarray(z["angle_words"], dtype=np.int64), \
            f"npz:{args.words_npz}"
    if args.words_npy:
        return np.load(args.words_npy).astype(np.int64), \
            f"npy:{args.words_npy}"
    raise ValueError("need one of --synthetic, --words-npz, --words-npy")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--synthetic", action="store_true",
                     help="random angle words (local development only)")
    src.add_argument("--words-npz", type=str,
                     help=".npz with 'angle_words' (num_vectors, N-1)")
    src.add_argument("--words-npy", type=str,
                     help=".npy angle_words array (num_vectors, N-1)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--num-vectors", type=int, default=3976)
    ap.add_argument("--ncols", type=int, default=N_MINUS_1)
    ap.add_argument("--brot", type=int, default=12)
    ap.add_argument("--J", type=int, default=8, dest="J")
    ap.add_argument("--strategy", type=str, default="delta-unary",
                    choices=["delta-unary", "init-lookup"])
    ap.add_argument("--out-dir", type=str, required=True)
    ap.add_argument("--prefix", type=str, default="angle")
    args = ap.parse_args()

    words, src_desc = load_words(args)
    nvec, ncols = words.shape
    if np.any((words < 0) | (words >= (1 << args.brot))):
        raise ValueError(f"angle words outside [0, 2**{args.brot})")
    sel_bits = sel_bits_for(nvec)
    need = sel_bits + args.J * args.brot + sel_bits  # sel + words + unary temp
    if need > QUBIT_CAP:
        print(f"REJECTED: J={args.J} brot={args.brot} needs {need} qubits "
              f"({sel_bits} sel + {args.J * args.brot} words + {sel_bits} "
              f"temp) > cap {QUBIT_CAP}")
        return 2
    deltas = batch_deltas(words, args.J)
    os.makedirs(args.out_dir, exist_ok=True)
    manifest = {
        "source": src_desc,
        "synthetic": bool(args.synthetic),
        "num_vectors": int(nvec),
        "ncols": int(ncols),
        "brot": int(args.brot),
        "J": int(args.J),
        "strategy": args.strategy,
        "sel_bits": int(sel_bits),
        "num_circuits": len(deltas),
        "circuits": [],
    }
    print(f"building {len(deltas)} circuits: {nvec} vectors, "
          f"brot={args.brot} J={args.J} strategy={args.strategy} "
          f"({need} qubits/circuit, cap {QUBIT_CAP})")
    for k, delta in enumerate(deltas):
        t0 = time.time()
        circ = build_angle_circuit(nvec, args.J, args.brot, delta,
                                   strategy=args.strategy)
        if not check_no_zpow(circ):
            raise RuntimeError(f"circuit {k}: Z_POW present (rejected)")
        stats = circuit_stats(circ)
        if stats["num_qubits"] > QUBIT_CAP:
            raise RuntimeError(f"circuit {k}: {stats['num_qubits']} qubits "
                               f"> cap {QUBIT_CAP}")
        path = os.path.join(args.out_dir, f"{args.prefix}_k_{k}.kmb")
        circ.to_file(path, format="kmb")  # REAL binary .kmb, never .kmx
        entry = {"k": k, "file": os.path.basename(path),
                 "sha256": sha256_file(path), "build_s": round(time.time() - t0, 2),
                 **stats}
        manifest["circuits"].append(entry)
        print(f"  k={k}: qubits={stats['num_qubits']} "
              f"toffoli={stats['num_toffoli_like']} "
              f"instr={stats['num_instructions']} "
              f"depth={stats['reaction_depth']} "
              f"sha256={entry['sha256'][:16]}...")
    # angles Toffoli accounting (forward + reverse, per the verifier):
    # each circuit runs forward and in reverse; toffoli_per_pass = half.
    per_pass = sum(c["num_toffoli_like"] for c in manifest["circuits"])
    manifest["angles_toffoli_forward_plus_reverse"] = 2 * per_pass
    manifest["angles_toffoli_per_pass"] = per_pass
    mpath = os.path.join(args.out_dir, "manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"angles Toffoli (forward+reverse): {2 * per_pass} "
          f"({per_pass} per pass, {len(deltas)} circuits)")
    print(f"manifest: {mpath}")
    if args.synthetic:
        print("NOTE: synthetic words -- this family is a LOCAL TEST ONLY, "
              "not a submission candidate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
