import hashlib
import lzma
import pathlib
import shutil
import zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path("/kaggle/input")
WORK = pathlib.Path("/kaggle/working/submission")
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True, exist_ok=True)

print("input roots:", sorted(str(p) for p in ROOT.iterdir()))


def find_one(pattern):
    hits = sorted(ROOT.rglob(pattern))
    if not hits:
        raise FileNotFoundError(pattern)
    return hits[0]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


pins = {
    "invsqrt.kmb": "e46d90c36d1beb3ce7731a3e0b5c3659b3cda7f5f290b73c6c34513d96c005b6",
    "dqi.kmb": "821bf8d157c03c3e868a0099b0ab1438cfba664ab1bc6fec3210654099b672a3",
    "dfthcsos/submission.npz": "3f864a7a",
}

src_inv = find_one("invsqrt.kmb")
shutil.copyfile(src_inv, WORK / "invsqrt.kmb")

src_dqi_xz = find_one("dqi.kmb.xz")
with lzma.open(src_dqi_xz, "rb") as f, open(WORK / "dqi.kmb", "wb") as g:
    shutil.copyfileobj(f, g, length=1 << 24)

chem_src = find_one("qcc-chemistry-4033-toffoli-loaders/submission.npz").parent
(WORK / "dfthcsos").mkdir(parents=True, exist_ok=True)
shutil.copyfile(chem_src / "submission.npz", WORK / "dfthcsos/submission.npz")
for i in range(15):
    shutil.copyfile(chem_src / f"angle_k_{i}.kmb", WORK / f"dfthcsos/angle_k_{i}.kmb")

for name, expected in pins.items():
    got = sha256(WORK / name)
    ok = got.startswith(expected) if len(expected) < 64 else got == expected
    print(name, got, "OK" if ok else "MISMATCH")
    assert ok, (name, got, expected)

zip_path = pathlib.Path("/kaggle/working/submission.zip")
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(WORK.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(WORK).as_posix())

print("zip", zip_path, zip_path.stat().st_size, sha256(zip_path))
print("files", len([p for p in WORK.rglob("*") if p.is_file()]))
print("utc", datetime.now(timezone.utc).isoformat())
