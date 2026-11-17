"""Diagnostic: inspect the Kaggle input mount (no verifiers, no simulation)."""
import hashlib
import pathlib


def sha(p, buf=1 << 24):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


inp = pathlib.Path('/kaggle/input')
lines = []
for p in sorted(inp.rglob('*')):
    if p.is_file() and not p.name.startswith('._'):
        try:
            lines.append(f"{p.stat().st_size:>12d}  {p}")
        except OSError as e:
            lines.append(f"{'STATFAIL':>12s}  {p}  {e}")
pathlib.Path('/kaggle/working/diag_tree.txt').write_text('\n'.join(lines) + '\n')
print(f"total files: {len(lines)}")
npz = [l for l in lines if l.lower().endswith('.npz')]
print(f"npz files: {len(npz)}")
for l in npz:
    print(l)
for l in npz:
    p = pathlib.Path(l.split('  ', 1)[1])
    try:
        print(f"{p.stat().st_size}  {sha(p)}  {p}")
    except OSError as e:
        print(f"READFAIL {p} {e}")
print("DIAG DONE")
