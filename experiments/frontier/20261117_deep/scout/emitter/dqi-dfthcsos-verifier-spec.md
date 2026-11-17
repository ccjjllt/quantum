# dqi + dfthcsos verifier spec (local build reference)

Extracted from the Kaggle notebook dataset 2026-11-14 ~13:36 MST (browser task 82175a9d).
Full spec also saved in the notebook markdown cell "dqi + dfthcsos verifier spec (local build reference)".
Notebook: https://www.kaggle.com/code/taylorclark637/notebook2f60e4fa23/edit

## DQI — verifiers/dqi/verify_submission_dqi.py (501 lines, 20,959 bytes), standalone

Defaults: m=4095, n=70, degree b=12, r=2016 (=(2^12-2^6)//2), l=n//2=35,
num_shots=102,400, batch_size=256, log2_delta=-128, max_workers=4.

Register contract: EXACTLY S0..S69 (km.q, width 12) and E0..E4094 (km.b, width 12),
pairwise disjoint, no other registers. S_i holds sum_j e_j*alpha^((i+1)j) over GF(2^12)
(alpha = primitive element of km.GF2Field(12)); E_j holds M_j on input. Per shot:
every S_i must be restored, every other qubit must return to |0>, and the global
phase must gain (-1)^sum_j popcount(e_j & M_j). Z_POW gates are NOT allowed (docstring).

Test distribution: error weight k in {0..35} with probability w_k^2, where w is the
principal unit eigenvector of the tridiagonal DQI matrix
A[k,k]=k(q-2r)/sqrt(r(q-r)), A[k-1,k]=sqrt(k(m-k+1)); then k uniform positions with
uniform nonzero GF values and uniform independent M_j. Syndromes
S_i = XOR_j e_j*alpha^(i*j), i=1..n; expected phase bit = parity of
sum_j popcount(e_j & M_j). to_bits is little-endian per register.

Simulation: km.Simulator(batch_size=256, counting_operations=True); seeds derived from
SHA-256 of the canonical .kmb serialization (merged with --salt, or --seed overrides);
batches run in parallel. Value error per shot = syndrome not restored OR any ancilla
not |0>; phase error = wrong phase flip AND no value error.

Scoring: k = value+phase errors out of N shots, eps_hat = k/N,
eps_plus = one-sided Clopper-Pearson upper bound at confidence 1-2^log2_delta
(k==0 gives -expm1(log_delta/N); otherwise 64-iteration binary search);
if eps_plus >= 1/16 the verifier raises AssertionError; otherwise
R(eps) = ln2 / -ln(1/2 + 2*sqrt(eps)) and score S = R(eps_plus) * Q^2 * T,
Q = num_qubits, T = mean Toffoli-like gates per shot.

CLI: verify_submission_dqi.py submission.kmb [--m] [--n] [--degree] [--r] [--num-shots]
[--batch-size] [--log2-delta] [--salt] [--seed] [--max-workers] [--format];
failure prints {"status":"FAIL","error":...} and exits 1.

Reference builder: dqi_reference_circuit.py (647 lines) — _active, _xor_threshold,
ProosAndZalkaDecoder, default_n_iters, build_reference_circuit(m, n, degree), main.

Sample dump (sample_submission/dqi.kmb, 886,118,100 bytes): num_qubits=1893,
num_bits=49154, num_registers=4165, reaction_depth=170757, len=86,051,014;
S0..S69 each 12 km.q (S0=q(0)..q(11)); E0..E4094 each 12 km.b (E0=b(0)..b(11));
static stats num_instructions=86,051,014, num_non_clifford=5,725,461, num_t_like=0,
num_toffoli_like=5,725,461, z_pow_clifford_hierarchy_counts={}.
(num_bits=49154 is 14 more than the 4095*12=49140 bits in the E registers.)

Baseline (full defaults, 205.205 s): PASS, score 24,439,463,583,672.93, 0 value/phase
errors, eps_plus 0.0008660587301657926, repetition_factor 1.191260648115832,
mean_error_weight 31.046737331746634, T=5,725,108.382109375, static max Toffoli 5,725,461.

## dfthcsos — verifiers/dfthcsos/verify.py (744 lines, 31,752 bytes)

NOTE: verifiers/dfthcsos/verify_submission_dfthcsos.py does NOT exist. The verifier is verify.py.

verify(circuits, factorization) -> dict; score S = lambda_eff * T_total * Q_total
for FeMoCo76o113e (N=76, eta=113). Inputs: directory with angle_k_*.kmb/.kmx or circuit
files in order; factorization .npz with U, W, H2_I, H1_I, Hsym_lower (submitted
H1_I/Hsym_lower ignored — shift fixed to baseline); tree_edges (N-1,2) array/.npy/.npz,
optional if submission.npz holds it; pickles not accepted. Reference integrals always
the packaged FCIDUMP (128,128,348 bytes, SHA-256 e5a48af746fd075026dec9e8f5df2d363802a121e8c53af9a0b984bde695e1bd).

Constants: LAMBDA_FLOOR=49.0, E_GAP_FLOOR=3.914898 Ha, QUBIT_CAP=128, KEEP_BITS=10,
SUBMISSION_FILE="submission.npz", ERROR_1_THRESHOLD=ERROR_2_THRESHOLD=0.020 (20 mHa);
equality fails at the floors, values never clamped.

native_inputs: w=params["W"], W=H2_I-sum(w,axis=1), S=symmetric_from_lower(Hsym_lower,N)
(float32-rounded first), beta_1=H1_I-0.5*trace(S); baseline R,B,C=65,60,60;
num_vectors=N+R*B=3976; UPPER_ENERGY=-22140.27335 Ha.

Metrics (dfthc_math.evaluate_dfthc_angle_words -> evaluate_dfthc_vectors):
angle_words (N+R*B)x(N-1) integers in [0,2^brot); tree rooted at 0, parent-before-child;
u_all=reconstruct_u_vectors(words/2^(brot-1), edges); rows normalized;
X^(rho c) from w and u (symmetrized); h1_thc=oei-0.5*sum_r(pr|rq);
h1_prime=H1_THC-(eta/2)S+beta_1*I-sum W*X; lambda_j=eigvalsh(h1_prime).
error_1 = ||H1_THC(submitted)-H1_THC||_F (rows paired with exact eigenvectors of h1_prime
by |overlap|, order/sign invariant) = ||sum lambda_j v_j v_j^T - h1_prime||_F.
error_2 = ||sum X (x) X - (S (x) I + I (x) S)/2 - (pq|rs)||_F over all N^4 chemist-order entries.
Lambda = sum|lambda_j| + lambda_h2, lambda_h2 = 1/4*sum_(rho c)(||w||_1 + |W_B|)^2,
W_B=W+sum_b w_b. E_SOS = ecore - eta*beta_1 - (lambda_h1 - sum lambda_j) - 0.5*sum(W^2).
E_gap = E_upper - E_SOS. gap_in_domain = 0 < E_gap <= 2*Lambda, plus a high-precision
check (_exact_lambda_eff must match lambda_eff to rel_tol 1e-6).
lambda_eff = sqrt(E_gap*(2*Lambda - E_gap)) if in domain else NaN.

Rejected (score inf, verify() raises AssertionError): error_1 or error_2 > 0.020;
gap out of domain; Lambda <= 49.0 or E_gap <= 3.914898 (strict, equality rejected);
any ANGLE_k circuit > 128 qubits.

Resource costs: T_total = angles_toffoli (simulator mean per shot over forward U_T +
reverse U_T^dagger; toffoli_per_pass = half) + outer_state_prep + inner_state_prep
(SpinFreeData_V1, incl. uncomputation) + 2*(N-1)*(2*brot-1) Givens Toffolis;
Q_total = outer_persistent + inner_persistent + J*brot + max(outer_temp, inner_temp,
ang_temp) (workspace shared, max not sum); SpinFreeData_V1(R,B,C,N,chi=KEEP_BITS=10,beta=brot).
angles_costs: qubits = max_k num_qubits, selection_qubits = len(selection),
persistent = J*brot, temporary = qubits - selection - persistent.

Word recovery (scoreinfra.circuits.recover_words_from_circuits, SHOTS_PER_ADDRESS=64):
public registers selection + word_0..word_{J-1} (numbered 0..J-1 without gaps, all same
width brot, all km.q, disjoint, identical across circuits); selection must be exactly
bit_length(num_vectors-1) qubits (12 for 3976); any Z_POW line raises InvalidCircuits;
addresses 0..3975 tiled 64x written to selection (little-endian); words read from word_j
as little-endian integers and all 64 shots per address must agree; padding words beyond
N-1 must be zero; reverse pass must restore the previous circuit's words (k=0 must clear
to zero); _check_state rejects uncorrected phase, changed selection, or workspace not |0>;
toffoli = sim num_toffoli_like / (num_vectors*64). HMR outcomes are fresh uniform per shot;
a 3976-address family verifies in ~14 s.

verify() returns status PASS, score, lambda_eff, toffoli_count, num_qubits, brot,
batch_size (J), num_circuits, reaction_depth (sum), num_ops (sum),
verified_shots (= num_vectors*64), submission_sha256, resources, metrics.
CLI: verify.py run_dir/ [--salt] [--seed]; also factorization.npz + circuits,
--tree-edges, --format, --shots-per-address (default 64);
failure prints {"status":"FAIL","error":...} and exits 1.

Helpers: scoreinfra/circuits.py (24,418 B — loading, hashing, layout, recovery; FORMATS,
SELECTION_REGISTER="selection", WORD_REGISTER_PREFIX="word_", HASHED_NPZ_KEYS=(U,W,H2_I,
H1_I,Hsym_lower,tree_edges), SHOTS_PER_ADDRESS=64; InvalidCircuits; RegisterLayout),
costs_prepare.py (8,335 B — QR, QI, SpinFreeData_V1 with
find_qrom_size_to_minimize_global_temp_ancilla, outer/inner_state_prep, givens_rotations,
outer/inner_state_prep_qubit_cost), dfthc_math.py (17,608 B — symmetric_from_lower,
reconstruct_x, lambda_h2, reconstruct_u_vectors, split_u_vectors, build_h1_prime,
reconstruct_h1_thc, h1_thc_reconstruction_error, reconstruct_h2, _exact_lambda_eff,
evaluate_dfthc_vectors, evaluate_dfthc_angle_words), reference.py (13,180 B — _parse_header,
_h2_full_from_lower, load_reference, load_factorization, check_fcidump, load_fixed_shifts;
fixed shift SHA-256 7b7facf63fe35a9d9d3d00787ffdb700c863fa845fe4724d7f7c54778151cd87),
__init__.py (280 B), example_submission/angle_k_reference_circuit.py (10,258 B —
batch_deltas, build_angle_k_circuit, build_angle_k_family, write_kmx_family,
load_angle_words, main).

Sample dump: every angle_k_*.kmb has num_qubits=119, num_registers=9, reaction_depth=11;
registers selection:12, word_0..word_7:12 each (brot=12, J=8); static stats every circuit
num_non_clifford=3974, num_t_like=0, num_toffoli_like=3974,
z_pow_clifford_hierarchy_counts={}; num_instructions k0 187,427; k1 186,423; k2 186,748;
k3 186,857; k4 218,777; k5 218,166; k6 218,099; k7 220,382; k8 219,115; k9 218,749
(sum 2,060,743). submission.npz keys: tree_edges (75,2) int64; angle_words (3976,75)
int64; U (65,76) float32; W (65,60,60) float32; H2_I (65,60) float32; H1_I () float32;
Hsym_lower (2926,) float32. Score-relevant: verified_shots = 3976*64 = 254,464;
angles persistent qubits J*brot=96, selection 12, temporary 119-12-96=11; per-circuit
max qubits 119 (under the 128 cap).

Baseline (full defaults, 81.127 s): PASS, score 3,355,599,588.3155375,
lambda_eff 49.301369250574396, toffoli_count 93,237.0, num_qubits 730, brot 12,
batch_size 8, num_circuits 10, reaction_depth 110, num_ops 2,060,743,
Lambda 308.4559397330948, E_SOS -22144.23882724429, E_gap 3.965477244291833,
error_1 0.0031851950317996216, error_2 0.018639570630974208, gap_in_domain true.

## File inventory (bytes)

verifiers/dqi/__init__.py 87; dqi_reference_circuit.py 30,450 (647 lines);
verify_submission_dqi.py 20,959 (501 lines). verifiers/dfthcsos/__init__.py 326;
verify.py 31,752 (744 lines); SCORING_README.md 22,477; FeMoCo76o113e.fcidump
128,128,348; FeMoCo76o113e.fixed_shifts.npz 61,028;
example_submission/angle_k_reference_circuit.py 10,258; scoreinfra/__init__.py 280;
circuits.py 24,418; costs_prepare.py 8,335; dfthc_math.py 17,608; reference.py 13,180.
sample_submission/dqi.kmb 886,118,100. sample_submission/dfthcsos/angle_k_0..9.kmb
~1.66–1.97 MB each; submission.npz 4,537,436.

Note: kickmix OperationStatistics exposes only num_instructions, num_non_clifford,
num_t_like, num_toffoli_like, z_pow_clifford_hierarchy_counts — no separate HMR/R
counts in the static stats; per-shot op counts come from sim.operation_statistics()
during simulation.
