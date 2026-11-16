"""Path-2 implementation: retain Norm(u) across the consuming half-scale.

`direct_carry_arithmetic.restore_with_shared_norm` builds Norm(u) twice:

  line 124  _inverse_norm -> init_norm (42 T) then invert in place
  line 155  init_norm again (42 T) for the inversion's own phase block

The second build exists only because the in-place inversion destroys the
norm.  This candidate copies the norm into a 12-bit retained register before
the inversion and uses the retained copy for the trailing phase block, which
removes exactly one 42-T 12-bit product per call (31 calls with a next word).

Everything else -- masks, phase repayment order, the retained-child last
return -- is byte-identical to the pinned source.  Build, then verify with the
unchanged official verifier at the default salt and two extra salts.
"""
import hashlib, json, pathlib, shutil, sys, time, importlib.util

t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp/k12"); TMP.mkdir(parents=True, exist_ok=True)
REPORT = []
def say(*a):
    s = " ".join(str(x) for x in a)
    REPORT.append(s); print(s, flush=True)

tree = sorted(ROOT.rglob("build.sh"))[0].parent
SRC = TMP / "src"
if SRC.exists():
    shutil.rmtree(SRC)
shutil.copytree(tree, SRC)
ENGINE = sorted(ROOT.rglob("kickmix.so"))[0].parent
VERIF = sorted(ROOT.rglob("verify_submission_dqi.py"))[0].parent.parent
for rel, srcp in (("pro1_controller_bundle/1_task/official/kickmix.so", ENGINE / "kickmix.so"),
                  ("pro1_controller_bundle/1_task/verifiers/dqi/verify_submission_dqi.py",
                   VERIF / "dqi" / "verify_submission_dqi.py")):
    dst = SRC / "src" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copyfile(srcp, dst)
ROOTDIR = TMP / "root"
if ROOTDIR.exists():
    shutil.rmtree(ROOTDIR)
shutil.copytree(SRC / "src", ROOTDIR)
CW = ROOTDIR / "controller_work"
for p in sorted(CW.rglob("*")):
    if p.is_dir():
        sys.path.insert(0, str(p))
sys.path.insert(0, str(ROOTDIR / "pro1_controller_bundle" / "1_task" / "official"))

import kickmix as km
import v7_pipeline as Pipeline
Pipeline.configure()
import last_return_retained_norm as Last
import direct_carry_arithmetic as Orig
import gf24_nested_norm as A24
import phase_inverse12 as Phase12
from tower_inverse import kernel
say("bound modules", Last.__name__, Orig.__name__, A24.__name__)
assert Pipeline.First3.Arithmetic is Last
assert Last.Original is Orig and Last.A is A24
BASE_RESTORE = Last.restore_with_shared_norm


def inverse_norm_retained(builder, source, delta):
    """init_norm once, keep a pristine copy, then invert in place."""
    norm = A24.init_norm(builder, source[:12], source[12:], delta)
    keep = builder.alloc_qubits(12)
    builder.cx(norm, keep)
    masks = Orig.Prior.inverse_twelve_deferred(builder, norm)
    A24._repay_norm_source_masks(builder, source, masks, delta)
    return norm, keep


def restore_with_shared_norm(builder, source, target, record, *,
                             next_word=None, next_input_record=None):
    if next_word is None:
        # The last return keeps its existing retained-child lifecycle.
        return BASE_RESTORE(builder, source, target, record,
                            next_word=None, next_input_record=None)
    assert record.builder_id == id(builder) and not record.closed
    assert tuple(source) == record.source and tuple(target) == record.target
    assert next_input_record is not None and len(next_word) == 24
    assert not set(next_word) & (set(source) | set(target))
    delta = record.delta
    head_return = A24.emit_prefix(builder, source, target, delta)
    next_old = Orig._adjoint_consume(builder, source, next_word, delta)
    inverse_norm, kept_norm = inverse_norm_retained(builder, source, delta)
    next_adjoint = Orig._consume_halves(builder, inverse_norm, next_word)

    builder.cz(record.old_target_mask, target)
    builder.free(record.old_target_mask)
    builder.cx(source[12:], source[:12])
    A24.phase_product(builder, source, target,
                      km.array([*record.adjoint_masks[0], *record.adjoint_masks[1]]),
                      A24.tensor24(delta))
    builder.cx(source[12:], source[:12])
    for mask in record.adjoint_masks:
        builder.free(mask)
    builder.cz(record.inverse_norm_mask, inverse_norm)
    builder.free(record.inverse_norm_mask)
    Orig._quotient_phase_with_norm(builder, source, inverse_norm, target,
                                   head_return.old_target_mask, delta)
    A24.free_product_mask(builder, head_return)
    A24.phase_product(builder, source, next_word, next_old, A24.tensor24(delta))
    builder.free(next_old)
    A24.repay_product_input(builder, next_word, next_input_record)

    inverse_mask = builder.alloc_bits(12)
    builder.hmr(inverse_norm, inverse_mask)
    builder.free(inverse_norm)
    # retained copy replaces the second init_norm of the pinned source
    Phase12.phase_inverse_twelve_polynomial(builder, kept_norm, inverse_mask)
    builder.free(inverse_mask)
    for half, mask in zip((next_word[:12], next_word[12:]), next_adjoint):
        A24.phase_product(builder, kept_norm, half, mask, kernel(12))
        builder.free(mask)
    A24.erase_norm(builder, source[:12], source[12:], kept_norm, delta)
    builder.free(kept_norm)
    record.closed = True


Last.restore_with_shared_norm = restore_with_shared_norm
assert Pipeline.First3.Arithmetic.restore_with_shared_norm is restore_with_shared_norm
say("patched restore_with_shared_norm on", Last.__name__)

from v7_events import Events
events = Events()
events.install(Pipeline)

STAGE = []
builder = km.CircuitBuilder()
builder.set_max_qubits(920)
S = [builder.create_quantum_register(12, f"S{i}") for i in range(70)]
E = [builder.create_classical_register(12, f"E{i}") for i in range(4095)]

def stage(message):
    msg = message if isinstance(message, str) else json.dumps(message, sort_keys=True)
    STAGE.append(dict(stage=msg, Q=builder.num_allocated_qubits))

t = time.time()
contract = Pipeline.emit(builder, S, E, j_min=15, scan_positions=4095, stage=stage)
say(f"emit {time.time()-t:.0f}s")
final_alloc = builder.num_allocated_qubits
circuit = builder.finish_circuit()
stats = dict(circuit.operation_statistics())
T = int(stats.get("CCX", 0)) + int(stats.get("CCZ", 0)) + int(stats.get("CSWAP", 0))
say("Q", circuit.num_qubits, "final_alloc", final_alloc, "static_T", T,
    "delta_vs_384003", T - 384003)
say("opcodes", json.dumps({k: v for k, v in sorted(stats.items())}, default=str))
say("max allocated Q over stages", max(r["Q"] for r in STAGE))
hi = sorted(STAGE, key=lambda r: -r["Q"])[:6]
say("stage Q peaks", json.dumps(hi))
say("expected saving", 42 * 31, "observed", 384003 - T)

out = WORK / "dqi_retain.kmb"
circuit.to_file(out, format="kmb")
sha = hashlib.sha256(out.read_bytes()).hexdigest()
say("SHA", sha, "bytes", out.stat().st_size)

# ---------------------------------------------------------------- verification
vpath = sorted(ROOT.rglob("verify_submission_dqi.py"))[0]
sp = importlib.util.spec_from_file_location("vdqi", str(vpath))
V = importlib.util.module_from_spec(sp)
sys.modules["vdqi"] = V
sp.loader.exec_module(V)
spec = V.ProblemSpecDQI.benchmark_instance()
BASE = 360733280431.94055
for label, circ, salt in (("retain", circuit, ""),
                          ("retain_salt2", circuit, "dqi-salt-2"),
                          ("retain_salt3", circuit, "dqi-salt-3")):
    t = time.time()
    res = V.verify(circ, spec, salt=salt)
    say(f"VERIFY {label} salt={salt!r} {time.time()-t:.0f}s Q {res['num_qubits']} "
        f"T {res['toffoli_count']:.4f} score {res['score']:.3f} "
        f"err {res['value_errors']}/{res['phase_errors']} sha {res['circuit_sha256'][:16]} "
        f"dscore {res['score']-BASE:+.3f} ({100*(res['score']/BASE-1):+.6f}%)")

(WORK / "report.txt").write_text("\n".join(REPORT))
say("done")
