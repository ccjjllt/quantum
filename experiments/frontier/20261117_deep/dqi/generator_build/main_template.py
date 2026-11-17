"""Build DQI decoder circuits from the public generator suite and report their real cost.

The suite is dmitriigluzdov/vqcc-femoco-public-factorization : circuit_sources/dqi/*.py
(Apache-2.0).  It is embedded here as a base64 zip because Kaggle script kernels upload
only main.py.  Nothing is simulated: we only build each circuit and read
`circuit.num_qubits`, `operation_statistics().num_t_like / num_toffoli_like` and `len(circuit)`.

Purpose: our shipped DQI tape is 890 qubits and its cost is `R * Q^2 * T`, so Q is the
dominant lever (each wire = +0.021 GM).  These generators are the only public DQI circuit
*generators* we have; if any of them produces a narrower circuit at comparable T it is a
large win, and if all are much wider the "new generation required" conclusion is measured
rather than assumed.
"""
import base64
import io
import json
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

PAYLOAD = """
__PAYLOAD__
"""

T0 = time.time()
WORK = pathlib.Path('/tmp/dqigen')
COMP = 'google-verifiable-quantum-circuit-compilation'


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


def find_comp():
    for p in (pathlib.Path('/kaggle/input/competitions') / COMP,
              pathlib.Path('/kaggle/input/datasets') / COMP,
              pathlib.Path('/kaggle/input') / COMP):
        if (p / 'verifiers').is_dir():
            return p
    for p in pathlib.Path('/kaggle/input').rglob('verifiers'):
        if (p / 'dqi').is_dir():
            return p.parent
    return None


def main():
    comp = find_comp()
    log('competition root:', comp)
    if comp is None:
        print('NO COMPETITION MOUNT', flush=True)
        return

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))) as zf:
        zf.extractall(WORK)
    log('modules:', sorted(p.name for p in WORK.glob('*.py')))

    # common.py sets ROOT = <its dir>/.. and prepends ROOT/data/comp/{kickmix,verifiers/dqi}.
    root = WORK.parent
    (root / 'data/comp').mkdir(parents=True, exist_ok=True)
    for dst, src in ((root / 'data/comp/kickmix', comp / 'kickmix'),
                     (root / 'data/comp/verifiers/dqi', comp / 'verifiers' / 'dqi')):
        if dst.is_symlink() or dst.exists():
            try:
                dst.unlink()
            except IsADirectoryError:
                shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src, target_is_directory=True)
    log('symlinked competition packages')

    sys.path.insert(0, str(WORK))
    import kickmix as km  # noqa: E402
    log('kickmix', getattr(km, '__version__', '?'))
    import dqi_reference_circuit as ref  # noqa: E402
    log('reference module', ref.__name__)

    results = {}
    for name in ('recursive', 'narrow', 'compact_euclid'):
        mod_path = WORK / f'{name}.py'
        if not mod_path.is_file():
            results[name] = {'error': 'missing'}
            continue
        out = pathlib.Path('/tmp') / f'{name}.kmb'
        log(f'--- building {name} ---')
        t = time.time()
        try:
            # each module exposes main() reading sys.argv[1] = output path
            env = dict(**__import__('os').environ)
            env['PYTHONPATH'] = f'{comp / "kickmix"}:{comp / "verifiers" / "dqi"}:{WORK}'
            env['JAX_PLATFORMS'] = 'cpu'
            r = subprocess.run([sys.executable, str(mod_path), str(out)],
                               capture_output=True, text=True, env=env, cwd=str(WORK),
                               timeout=5400)
            log(f'{name} rc={r.returncode} [{time.time() - t:.0f}s]')
            print(f'--- {name} stdout ---\n{r.stdout[-4000:]}', flush=True)
            if r.returncode != 0:
                print(f'--- {name} stderr ---\n{r.stderr[-3000:]}', flush=True)
                results[name] = {'error': r.stderr.strip().splitlines()[-1:] or ['rc']}
                continue
            info = None
            for line in reversed(r.stdout.strip().splitlines()):
                line = line.strip()
                if line.startswith('{'):
                    try:
                        info = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            if info is None:
                results[name] = {'error': 'no json'}
                continue
            results[name] = info
            Q = info.get('num_qubits')
            T = info.get('t_count')
            if Q and T:
                cost = 1.1912605 * Q * Q * T
                info['cost'] = cost
                info['ratio_vs_shipped'] = cost / 346409762292.7187
            log(f'{name}: Q={Q} T={T} toffoli={info.get("toffoli_count")} '
                f'ops={info.get("num_ops")} cost={info.get("cost")}')
        except Exception as exc:  # noqa: BLE001
            log(f'{name} EXCEPTION {type(exc).__name__}: {exc}')
            results[name] = {'error': f'{type(exc).__name__}: {exc}'}

    print('SUMMARY ' + json.dumps(results), flush=True)
    print('shipped 575b043f: Q=890 mean_T=367116.06 cost=346409762292.7187', flush=True)
    print('DONE', flush=True)


main()
