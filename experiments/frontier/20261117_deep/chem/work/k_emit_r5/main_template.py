"""Emit chemistry loaders for an arbitrary row count with the row-count-general emitter.

Background: every cheaper chemistry shape needs fewer angle rows (rows = 76 + R*B), and the
historical emitter was hard-wired to 1,220 rows.  `complete_words`, `padded_words`,
`cross_tensor`, `hmax` and `first_unused_address` in the embedded port are now parameterised
(verified byte-identical at 1,220 rows for all 15 loaders), so a 791/756/648-row table can be
emitted.

This kernel:
  1. unzips the port,
  2. finds the candidate submission.npz under /kaggle/input (any angle_words row count != 1220
     is preferred; the shipped one is the fallback for a regression test),
  3. for each k in K_LIST: plan -> build -> .kmx -> .kmb, logging Toffoli/qubits,
  4. assembles dfthcsos/ (npz + every produced loader + shipped loaders for the rest),
  5. runs the unmodified official chemistry verifier and prints the score.

CPU only; nothing is submitted to Kaggle.
"""
import base64
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

PAYLOAD = """
__PAYLOAD__
"""

K_LIST = [int(x) for x in "__KLIST__".split(",") if x.strip() != ""]
PER_K_SECONDS = __PERK__
PLAN_STATE = "__PLANSTATE__"          # if set, emit from this stored plan instead of searching
TRUNC = __TRUNC__                     # >0: synthesise a shorter table by truncating angle_words
SEEDS = (11, 7, 9, 8, 13)
TRIALS = 120

WORK = pathlib.Path("/tmp/work")
OUT = pathlib.Path("/tmp/out")
COMP = None
for _p in pathlib.Path("/kaggle/input").rglob("FeMoCo76o113e.fcidump"):
    for _up in (_p.parents[1], _p.parents[2], _p.parents[3]):
        if (_up / "kickmix").is_dir():
            COMP = _up
            break
    if COMP:
        break


if COMP is not None:
    # the competition's kickmix (the one with Circuit.from_file) must win the import
    sys.path.insert(0, str(COMP / "kickmix"))
    sys.path.insert(0, str(COMP / "verifiers"))


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def unzip_port() -> pathlib.Path:
    WORK.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as z:
        z.extractall(WORK)
    p = WORK / "code2"
    sys.path.insert(0, str(p))
    sys.path.insert(0, str(p / "compiler"))
    log("port at", p, "py files", len(list(p.rglob('*.py'))))
    return p


def find_npz():
    """Prefer a non-1220-row table (the new shape); else the shipped one (regression test).

    The competition's own sample_submission/dfthcsos/submission.npz is the baseline
    factorization (a different shape) and must never be mistaken for a candidate, so
    anything under the competition mount is skipped.
    """
    shipped = None
    for p in sorted(pathlib.Path("/kaggle/input").rglob("submission.npz")):
        s = str(p)
        if "competitions" in s or "sample_submission" in s:
            continue
        try:
            import numpy as np
            with np.load(p, allow_pickle=False) as z:
                if "angle_words" not in z:
                    continue
                rows = z["angle_words"].shape[0]
        except Exception:
            continue
        if rows != 1220:
            log("candidate new-shape npz:", p, "rows", rows)
            return p, rows
        shipped = shipped or (p, rows)
    return shipped if shipped else (None, None)


def main():
    log("competition:", COMP)
    if COMP is None:
        raise SystemExit("no competition mount")
    port = unzip_port()
    import numpy as np
    import compile_basis as CB
    from planner import complete_words, cross_tensor
    from emit_from_basis import build

    CB.STOP_AT = 145
    CB.LS_SECONDS = max(60, PER_K_SECONDS // 6)

    npz, rows = find_npz()
    if npz is None:
        # kernel_sources mount a submission.zip, not an npz: extract it first
        zips = sorted(pathlib.Path("/kaggle/input").rglob("submission.zip"))
        if not zips:
            raise SystemExit("no submission.npz and no submission.zip found")
        ext = pathlib.Path("/tmp/shipped_extract")
        with zipfile.ZipFile(zips[0]) as zf:
            zf.extractall(ext)
        log("extracted shipped zip:", zips[0], "->", ext)
        npz = next(ext.rglob("submission.npz"), None)
        if npz is None:
            raise SystemExit("no submission.npz inside the shipped zip")
        with np.load(npz, allow_pickle=False) as z:
            rows = z["angle_words"].shape[0]
    if npz is None:
        raise SystemExit("no submission.npz found")
    log("npz:", npz, "rows:", rows, "K_LIST:", K_LIST)
    z = np.load(npz, allow_pickle=False)
    W = np.asarray(z["angle_words"], np.uint8)
    log("angle_words", W.shape)

    if TRUNC and TRUNC < len(W):
        # de-risk probe: does the search/emitter work at a shorter address space, and what
        # does it cost?  The truncated table is NOT a valid submission (its words are not a
        # Givens gauge of any vector set); it only exercises plan/emit at nh = ceil(TRUNC/16).
        W = W[:TRUNC].copy()
        synth = pathlib.Path("/tmp/synth")
        synth.mkdir(parents=True, exist_ok=True)
        np.savez(synth / "submission.npz", angle_words=W,
                 tree_edges=np.asarray(z["tree_edges"]) if "tree_edges" in z else np.zeros((75, 2), np.int64))
        npz = synth / "submission.npz"
        log("TRUNC probe -> synthetic table rows", len(W), "nh", (len(W) + 15) // 16)

    # emit_from_basis hardcodes the authoring machine's BUILD dir and reads
    # BUILD/'submission.npz'.  Stage our npz under exactly that name and point BUILD at it.
    staged = pathlib.Path("/tmp/npzdir")
    staged.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(npz, staged / "submission.npz")
    import emit_from_basis as _EFB
    _EFB.BUILD = staged
    log("BUILD ->", _EFB.BUILD)

    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for k in K_LIST:
        t0 = time.time()
        try:
            if PLAN_STATE:
                sp = pathlib.Path(PLAN_STATE)
                if not sp.is_absolute():
                    sp = port / PLAN_STATE
                log(f"k{k}: emitting from stored plan {sp}")
                st = json.loads(sp.read_text())
                rep, s = build(k, sp, OUT / f"k{k}")
                log(f"k{k}: stored cuts={st.get('sum_cuts')} toffoli={rep['toffoli_count']} "
                    f"qubits={rep['num_qubits']} [{time.time()-t0:.0f}s]")
                results[k] = {kk: rep[kk] for kk in ("product_count", "toffoli_count", "num_qubits")}
                continue
            Wc = complete_words(W)
            target = cross_tensor(Wc, k)
            log(f"k{k}: target len {len(target)} (hmax {len(target)-1})")
            best = CB.plan_one(target, seeds=SEEDS, trials=TRIALS,
                               time_limit=PER_K_SECONDS, verbose=True)
            if best is None:
                log(f"k{k}: planner found nothing")
                results[k] = None
                continue
            state = {"k": k, "parts": CB.PARTS5, "cuts": best["cuts"], "rows": best["rows"],
                     "F": best["F"], "sum_cuts": int(best["sum_c"])}
            sp = OUT / f"plan_k{k}.json"
            sp.write_text(json.dumps(state))
            rep, s = build(k, sp, OUT / f"k{k}")
            log(f"k{k}: cuts={best['sum_c']} toffoli={rep['toffoli_count']} "
                f"qubits={rep['num_qubits']} [{time.time()-t0:.0f}s]")
            results[k] = {kk: rep[kk] for kk in ("product_count", "toffoli_count", "num_qubits")}
        except Exception as exc:  # noqa: BLE001
            log(f"k{k}: EXCEPTION {type(exc).__name__}: {exc}")
            results[k] = {"error": f"{type(exc).__name__}: {exc}"}

    # convert produced .kmx -> .kmb
    import kickmix as km
    produced = {}
    for k in K_LIST:
        src = OUT / f"k{k}" / f"angle_k_{k}.kmx"
        if not src.exists():
            continue
        dst = OUT / f"k{k}" / f"angle_k_{k}.kmb"
        km.Circuit.from_file(str(src), format="kmx").to_file(str(dst), format="kmb")
        produced[k] = dst
        log(f"k{k}: kmb {dst.stat().st_size} B")

    print("SUMMARY " + json.dumps({str(k): v for k, v in results.items()}), flush=True)

    if not produced:
        log("nothing produced -> no verification")
        return

    # assemble: shipped package + our produced loaders overlaid
    run = OUT / "run" / "dfthcsos"
    run.mkdir(parents=True, exist_ok=True)
    src_root = None
    for cand in pathlib.Path("/kaggle/input").rglob("submission.zip"):
        src_root = cand
        break
    if src_root is not None:
        with zipfile.ZipFile(src_root) as zf:
            zf.extractall(OUT / "src")
        base = OUT / "src"
        for p in base.rglob("angle_k_*.kmb"):
            shutil.copyfile(p, run / p.name)
    shutil.copyfile(npz, run / "submission.npz")
    for k, p in produced.items():
        shutil.copyfile(p, run / f"angle_k_{k}.kmb")
    log("assembled", len(list(run.iterdir())), "members")

    env = dict(os.environ, JAX_PLATFORMS="cpu", OMP_NUM_THREADS="4",
               PYTHONPATH=f"{COMP / 'kickmix'}:{COMP / 'verifiers'}")
    r = subprocess.run([sys.executable, str(COMP / "verifiers/dfthcsos/verify.py"), str(run)],
                       capture_output=True, text=True, env=env, cwd=str(COMP / "verifiers"))
    log("official chemistry verifier rc =", r.returncode)
    print(r.stdout[-5000:], flush=True)
    print(r.stderr[-2000:], flush=True)
    print("DONE", flush=True)


main()
