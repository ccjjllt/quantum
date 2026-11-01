"""Replay the one Ahmed v15 history-cache edit on the 62-qubit invsqrt circuit.

The oracle is Ahmed's circuit. Deleting the q60 cache restores yoyobar; putting
the same cache back must reproduce Ahmed's canonical KMB hash.
"""

import hashlib
import io
import json
from pathlib import Path

import kickmix

ROOT = Path(__file__).resolve().parents[3]
ORACLE = ROOT / "artifacts/20261030_public_best/candidate/invsqrt.kmb"
OUT = ROOT / "artifacts/20261031_invsqrt62_replay/invsqrt"

AHMED_SHA = "6dbb98b34c3b16f1c4e019350c10d42259a6faa97e464c9b7c9390f877f392f4"
YOYOBAR_SHA = "a568bc79348165bad5be2349960d200300c5639ffd2142aca6d548e764a399d9"

# Ahmed indices. The two CX wrap CSWAP q16 q2 q23; the block replaces CSWAP q19 q6 q41.
CX_BEFORE = 46718
CSWAP_EARLY = 46719
CX_AFTER = 46720
BLOCK_START = 46798
BLOCK_END = 46808
# Yoyobar indices of those two CSWAPs before the insertions.
YOYO_EARLY = 46718
YOYO_LATE = 46796

CACHE = [
    "X q60",
    "CX q16 q60",
    "CX q17 q60",
    "CX q40 q60",
    "CX q41 q60",
    "CX q60 q6",
    "CX q60 q41",
    "HMR q60 b30000",
    "CZ q19 q6 if b30000",
    "CZ q19 q41 if b30000",
]
LATE_CSWAP = "CSWAP q19 q6 q41"
EARLY_CSWAP = "CSWAP q16 q2 q23"
CACHE_CX = "CX q2 q60"


def split_kmx(circuit):
    text = io.StringIO()
    circuit.to_file(text, format="kmx")
    lines = text.getvalue().splitlines()
    header = [line for line in lines if line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    ops = [line for line in lines if not line.startswith(("APPEND_TO_REGISTER", "REGISTER"))]
    if lines != header + ops:
        raise SystemExit("KMX header lines are not a prefix; refusing to reorder them")
    if len(ops) != 47201:
        raise SystemExit(f"expected 47201 ops, found {len(ops)}")
    return header, ops


def circuit_from_ops(header, ops):
    kmx = "\n".join(header + ops) + "\n"
    return kickmix.Circuit.from_file(io.StringIO(kmx), format="kmx")


def canonical_bytes(circuit):
    buf = io.BytesIO()
    circuit.to_file(buf, format="kmb")
    return buf.getvalue()


def to_yoyobar(ops):
    window = [ops[CX_BEFORE], ops[CSWAP_EARLY], ops[CX_AFTER]]
    if window != [CACHE_CX, EARLY_CSWAP, CACHE_CX] or ops[BLOCK_START:BLOCK_END] != CACHE:
        raise SystemExit("oracle window is not the observed Ahmed cache patch")
    return ops[:CX_BEFORE] + ops[CSWAP_EARLY:CX_AFTER] + ops[CX_AFTER + 1:BLOCK_START] + [LATE_CSWAP] + ops[BLOCK_END:]


def to_ahmed(ops):
    if ops[YOYO_EARLY] != EARLY_CSWAP or ops[YOYO_LATE] != LATE_CSWAP:
        raise SystemExit("yoyobar window is not the two CSWAPs the cache patch edits")
    return (
        ops[:YOYO_EARLY]
        + [CACHE_CX, ops[YOYO_EARLY], CACHE_CX]
        + ops[YOYO_EARLY + 1:YOYO_LATE]
        + CACHE
        + ops[YOYO_LATE + 1:]
    )


def first_kmx_difference(ahmed_ops, yoyobar_ops):
    for index, (left, right) in enumerate(zip(ahmed_ops, yoyobar_ops)):
        if left != right:
            return {"index": index, "ahmed": left, "yoyobar": right}
    index = min(len(ahmed_ops), len(yoyobar_ops))
    return {
        "index": index,
        "ahmed": ahmed_ops[index] if index < len(ahmed_ops) else None,
        "yoyobar": yoyobar_ops[index] if index < len(yoyobar_ops) else None,
    }


def main():
    ahmed = kickmix.Circuit.from_file(ORACLE)
    header, ahmed_ops = split_kmx(ahmed)
    yoyobar_ops = to_yoyobar(ahmed_ops)
    repatched_ops = to_ahmed(yoyobar_ops)
    yoyobar = circuit_from_ops(header, yoyobar_ops)
    repatched = circuit_from_ops(header, repatched_ops)

    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "ahmed": (OUT / "ahmed.kmb", ahmed),
        "yoyobar": (OUT / "yoyobar.kmb", yoyobar),
        "ahmed_repatched": (OUT / "ahmed_repatched.kmb", repatched),
    }
    written = {}
    for name, (path, circuit) in files.items():
        data = canonical_bytes(circuit)
        path.write_bytes(data)
        written[name] = hashlib.sha256(data).hexdigest()

    exact = (
        written["ahmed"] == AHMED_SHA
        and written["yoyobar"] == YOYOBAR_SHA
        and written["ahmed_repatched"] == written["ahmed"]
    )
    report = {
        "num_ops_ahmed": len(ahmed_ops),
        "num_qubits": ahmed.num_qubits,
        "num_bits": ahmed.num_bits,
        "sha256_ahmed": written["ahmed"],
        "sha256_yoyobar": written["yoyobar"],
        "sha256_ahmed_repatched": written["ahmed_repatched"],
        "exact_replay": exact,
        "patch": {
            "description": (
                "One history cache in the final shift of x. "
                "Yoyobar op 46718 is CSWAP q16 q2 q23; Ahmed inserts CX q2 q60 before and after it "
                "(Ahmed ops 46718 and 46720, CSWAP at 46719). "
                "Yoyobar op 46796 is CSWAP q19 q6 q41; those two CX shift it to Ahmed op 46798, "
                "where ops 46798:46808 replace that CSWAP with an X-basis cache on q60 "
                "(condition XOR of the earlier CSWAP control and q16, q17, q40, q41; "
                "HMR q60 b30000 plus CZ q19 q6 / CZ q19 q41 if b30000). "
                "One unconditional Toffoli removed."
            ),
            "ahmed_ops": {
                "46718": CACHE_CX,
                "46719": EARLY_CSWAP,
                "46720": CACHE_CX,
                "46798:46808": CACHE,
            },
            "inverse_delete_indices": [CX_BEFORE, CX_AFTER],
            "inverse_replace": {"start": BLOCK_START, "end_exclusive": BLOCK_END, "with": LATE_CSWAP},
            "forward_insert_around": {"index": YOYO_EARLY, "line": EARLY_CSWAP, "cx": CACHE_CX},
            "forward_replace": {"index": YOYO_LATE, "line": LATE_CSWAP, "with": CACHE},
        },
        "static_toffoli_like": {
            "ahmed": int(ahmed.operation_statistics().num_toffoli_like),
            "yoyobar": int(yoyobar.operation_statistics().num_toffoli_like),
            "ahmed_repatched": int(repatched.operation_statistics().num_toffoli_like),
        },
    }
    if not exact:
        report["first_kmx_difference"] = first_kmx_difference(ahmed_ops, yoyobar_ops)
    text = json.dumps(report, indent=2) + "\n"
    (OUT / "roundtrip.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
