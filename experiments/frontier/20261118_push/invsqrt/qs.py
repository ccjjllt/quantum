import pathlib, re, sys

path = pathlib.Path(sys.argv[1])
lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
body = [l for l in lines if not l.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
lo, hi, q = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
for i in range(lo, hi + 1):
    if re.search(rf"\b{q}\b", body[i]):
        print(i, body[i])
print("---- full window")
for i in range(lo, min(hi + 1, lo + 70)):
    print(i, body[i])
