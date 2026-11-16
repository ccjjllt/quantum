"""Our own official receipts for the 28.059 stack (chem, invsqrt, DQI), default salt.

Files are located by SHA-256 (the same hashes the publisher ships), then each is graded by the
UNCHANGED competition verifier from the attached competition data:

    verifiers/dfthcsos/verify.py <dir>          chemistry: lambda_eff * T * Q, 78,080 shots
    verifiers/invsqrt/verify_submission_invsqrt.py invsqrt.kmb   200,540,928 shots
    verifiers/dqi/verify_submission_dqi.py dqi.kmb               102,400 shots

Publisher's numbers (default salt): invsqrt 75,170.62; DQI 347,904,227,556 (0 failed shots);
chemistry 294,800,582.44; GM 28.0590. This kernel is our independent check, not a copy of theirs.

Kaggle CPU only.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

WANT = {
    "invsqrt.kmb": "47b318383a03c52e08a5c222c5600fd52e004b468f53fad038082fc0f26386ef",
    "dqi.kmb": "46446af1186566a57edaa9e1ddcd2e87b713945218ee83df9ffa45ea68bab597",
    "dfthcsos/submission.npz": "302e608cbbcb45e8c9155cdd26e7a6217ffc582991c306b587ec2fa8ae32e2e9",
}
for i in range(15):
    WANT[f"dfthcsos/angle_k_{i}.kmb"] = {
        0: "aed6aa7cde8cefae06376546c276208a667a1a402ebfe9e57cb33881868ab089",
        1: "72b79b56514e657650ed3258d90e7a533568ade86db407990a34bfb4380b6e60",
        2: "42ea507daa22d0464e16d8f8d8f091e684d025998a32b574fee34672414b18ad",
        3: "423968d4ab8219b164a27284c4b889b67a864ead9322b7703599fc839d7d8035",
        4: "cf7c413468b0fe51cfb7ff457b1f9ab76dc80df01dbfba87cd190c9686078d68",
        5: "8c8a6281407052dbc2bfaa2a90d7cc34f936b406ad83b11a3a0586f2d32f1896",
        6: "0ebb575aef372a33941a1a9b8e317351dda7746389ec31c1b52f40f2280ad329",
        7: "77c35bb2ee9c699693ee581a510b53f0c9cf4a3c3a58b02882913ca048fd09ab",
        8: "9c5ced81d9a7378b763603f0bdd61322369e1bc3c72628a224b0445486e48663",
        9: "611fe155e4e060d0cca795236b0f1abd6e41225b7bbca135cfaec8da5a4334f9",
        10: "2926a709c9d0ed2824073bef29347d2beee6282e1e08aff5b982512e345f6220",
        11: "7aed38f94ef86b504f985dcee98ed33dd6b341114147c55d0407b88495a1015d",
        12: "d73ee72ed6661082acd273d3bbf4d3511330d688bec8e64e6a8d647a975b9655",
        13: "38b56f2fc07b7bd5a378c7d25650f62a430fe42d5595d6184d5ae930b258bec3",
        14: "ab06b98fc22fce8a33b591db9caf73e93d407342a6c0f3d2e2e1416dffffdfd7",
    }[i]


def sha256(path, buf=1 << 24):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(buf), b""):
            h.update(block)
    return h.hexdigest()


by_sha = {}
for p in pathlib.Path("/kaggle/input").rglob("*"):
    if p.is_file() and p.suffix in (".kmb", ".npz"):
        by_sha.setdefault(sha256(p), p)

W = pathlib.Path("/kaggle/working/verify28059")
shutil.rmtree(W, ignore_errors=True)
W.mkdir(parents=True, exist_ok=True)
files = {}
for member, digest in WANT.items():
    assert digest in by_sha, member
    dst = W / member
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(by_sha[digest], dst)
    files[member] = dst
print("staged", len(files), "members", flush=True)

# locate the verifiers and kickmix inside the attached competition bundle
comp = None
for p in pathlib.Path("/kaggle/input").rglob("verify_submission_dqi.py"):
    comp = p.parents[2] if (p.parents[2] / "kickmix").is_dir() else None
if comp is None:
    for p in pathlib.Path("/kaggle/input").rglob("kickmix.so"):
        comp = p.parent.parent
        break
print("comp", comp, (comp / "verifiers").is_dir(), (comp / "kickmix").is_dir(), flush=True)
ENV = dict(os.environ, JAX_PLATFORMS="cpu", OMP_NUM_THREADS="4",
           PYTHONPATH=":".join([str(comp / "verifiers"), str(comp / "kickmix")]))
PY = sys.executable
results = {}

# ---- chemistry
t0 = time.time()
r = subprocess.run([PY, str(comp / "verifiers" / "dfthcsos" / "verify.py"), str(W / "dfthcsos")],
                   capture_output=True, text=True, timeout=21600, env=ENV,
                   cwd=str(comp / "verifiers" / "dfthcsos"))
print("CHEM rc", r.returncode, "secs", round(time.time() - t0), flush=True)
print(r.stdout[-1500:], flush=True)
try:
    results["chem"] = json.loads(r.stdout[r.stdout.index("{"):])
except Exception:
    results["chem"] = None

# ---- invsqrt
t0 = time.time()
r = subprocess.run([PY, str(comp / "verifiers" / "invsqrt" / "verify_submission_invsqrt.py"),
                    str(W / "invsqrt.kmb")], capture_output=True, text=True, timeout=36000, env=ENV,
                   cwd=str(comp / "verifiers" / "invsqrt"))
print("INVSQRT rc", r.returncode, "secs", round(time.time() - t0), flush=True)
print(r.stdout[-1500:], flush=True)
try:
    results["invsqrt"] = json.loads(r.stdout[r.stdout.index("{"):])
except Exception:
    results["invsqrt"] = None

# ---- DQI
t0 = time.time()
r = subprocess.run([PY, str(comp / "verifiers" / "dqi" / "verify_submission_dqi.py"), str(W / "dqi.kmb")],
                   capture_output=True, text=True, timeout=36000, env=ENV,
                   cwd=str(comp / "verifiers" / "dqi"))
print("DQI rc", r.returncode, "secs", round(time.time() - t0), flush=True)
print(r.stdout[-1500:], flush=True)
try:
    results["dqi"] = json.loads(r.stdout[r.stdout.index("{"):])
except Exception:
    results["dqi"] = None

print("SUMMARY", json.dumps(results)[:4000], flush=True)
print("DONE", flush=True)
