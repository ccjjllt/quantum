"""Assemble the 28.059 public stack on Kaggle and hand back submission.zip.

Provenance (all public, credited by the publisher):

  invsqrt.kmb      syed3000/vqcc-own-circuit-portfolio v14   sha 47b31838...   (44 qubits)
  dqi.kmb          syed3000/vqcc-own-circuit-portfolio v14   sha 46446af1...   (890 qubits)
  dfthcsos/*       marculera/dfthc-c44-build v6              sha 302e608c...   (npz) + 15 kmb

Publisher's reported official costs (default salt): invsqrt 75,170.62, DQI 347,904,227,556,
chemistry 294,800,582.44, geometric mean 28.0590. Two of their four salts showed one failed DQI shot
out of 102,400 (+0.46% DQI cost, GM 28.016), which is the same salt sensitivity every stack using this
decoder has.

This kernel locates every member by SHA-256 (folder names do not matter), asserts each hash, writes
`submission.zip`, and prints the member list and the final SHA-256 so the submission is auditable.

Kaggle CPU only.
"""
import hashlib
import json
import pathlib
import zipfile

WANT = {
    "invsqrt.kmb": "47b318383a03c52e08a5c222c5600fd52e004b468f53fad038082fc0f26386ef",
    "dqi.kmb": "46446af1186566a57edaa9e1ddcd2e87b713945218ee83df9ffa45ea68bab597",
    "dfthcsos/submission.npz": "302e608cbbcb45e8c9155cdd26e7a6217ffc582991c306b587ec2fa8ae32e2e9",
    "dfthcsos/angle_k_0.kmb": "aed6aa7cde8cefae06376546c276208a667a1a402ebfe9e57cb33881868ab089",
    "dfthcsos/angle_k_1.kmb": "72b79b56514e657650ed3258d90e7a533568ade86db407990a34bfb4380b6e60",
    "dfthcsos/angle_k_2.kmb": "42ea507daa22d0464e16d8f8d8f091e684d025998a32b574fee34672414b18ad",
    "dfthcsos/angle_k_3.kmb": "423968d4ab8219b164a27284c4b889b67a864ead9322b7703599fc839d7d8035",
    "dfthcsos/angle_k_4.kmb": "cf7c413468b0fe51cfb7ff457b1f9ab76dc80df01dbfba87cd190c9686078d68",
    "dfthcsos/angle_k_5.kmb": "8c8a6281407052dbc2bfaa2a90d7cc34f936b406ad83b11a3a0586f2d32f1896",
    "dfthcsos/angle_k_6.kmb": "0ebb575aef372a33941a1a9b8e317351dda7746389ec31c1b52f40f2280ad329",
    "dfthcsos/angle_k_7.kmb": "77c35bb2ee9c699693ee581a510b53f0c9cf4a3c3a58b02882913ca048fd09ab",
    "dfthcsos/angle_k_8.kmb": "9c5ced81d9a7378b763603f0bdd61322369e1bc3c72628a224b0445486e48663",
    "dfthcsos/angle_k_9.kmb": "611fe155e4e060d0cca795236b0f1abd6e41225b7bbca135cfaec8da5a4334f9",
    "dfthcsos/angle_k_10.kmb": "2926a709c9d0ed2824073bef29347d2beee6282e1e08aff5b982512e345f6220",
    "dfthcsos/angle_k_11.kmb": "7aed38f94ef86b504f985dcee98ed33dd6b341114147c55d0407b88495a1015d",
    "dfthcsos/angle_k_12.kmb": "d73ee72ed6661082acd273d3bbf4d3511330d688bec8e64e6a8d647a975b9655",
    "dfthcsos/angle_k_13.kmb": "38b56f2fc07b7bd5a378c7d25650f62a430fe42d5595d6184d5ae930b258bec3",
    "dfthcsos/angle_k_14.kmb": "ab06b98fc22fce8a33b591db9caf73e93d407342a6c0f3d2e2e1416dffffdfd7",
}


def sha256(path, buf=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(buf), b""):
            h.update(block)
    return h.hexdigest()


roots = [pathlib.Path("/kaggle/input")]
by_sha = {}
for root in roots:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in (".kmb", ".npz"):
            by_sha.setdefault(sha256(p), p)

missing = [m for m, s in WANT.items() if s not in by_sha]
print("found", len(WANT) - len(missing), "of", len(WANT), "members", flush=True)
assert not missing, f"not found by sha256: {missing}"

sub = pathlib.Path("/kaggle/working/submission")
import shutil
shutil.rmtree(sub, ignore_errors=True)
(sub / "dfthcsos").mkdir(parents=True, exist_ok=True)
for member, digest in WANT.items():
    dst = sub / member
    shutil.copyfile(by_sha[digest], dst)
    assert sha256(dst) == digest, member
    print("OK", member, digest[:12], dst.stat().st_size, flush=True)

out = "/kaggle/working/submission.zip"
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
    for p in sorted(sub.rglob("*")):
        if p.is_file():
            z.write(p, str(p.relative_to(sub)))
size = pathlib.Path(out).stat().st_size
print("SUBMISSION", out, size, sha256(out), flush=True)
with zipfile.ZipFile(out) as z:
    names = sorted(z.namelist())
print("MEMBERS", len(names), names[:3], flush=True)
print("DONE", flush=True)
