from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import kickmix as km


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_census(kmb_path: Path) -> dict:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    stage = "header"
    stage_paid: dict[str, Counter] = {}
    stage_ops: Counter = Counter()
    total_ops = 0
    unread_ccx_before_hmr = 0

    stack: list[str] = []
    lines = buf.getvalue().splitlines()
    for l in lines:
        if l.startswith("INFO_TAG "):
            tag = l.strip().split('"', 2)[1]
            if tag.startswith("@enter:"):
                stack.append(tag[7:])
            elif tag.startswith("@exit:") and stack:
                stack.pop()
            continue
        if not l or l.startswith(("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")):
            continue
        stage = stack[0] if stack else "header"
        total_ops += 1
        stage_ops[stage] += 1
        op = l.split()[0]
        if op in ("CCX", "CCZ", "CSWAP", "CCX_CARRY"):
            if stage not in stage_paid:
                stage_paid[stage] = Counter()
            stage_paid[stage][op] += 1

    # Check backward liveness from every HMR/R for unread CCX targets
    ops = [
        l
        for l in lines
        if l and not l.startswith(("APPEND", "REGISTER", "ANNOTATION"))
    ]
    for idx, l in enumerate(ops):
        p = l.split()
        if p[0] not in ("HMR", "R"):
            continue
        q = p[1]
        for j in range(idx - 1, max(-1, idx - 60), -1):
            p2 = ops[j].split()
            if p2[0] in ("PUSH_CONDITION", "POP_CONDITION"):
                continue
            if q not in p2:
                continue
            if p2[0] == "CCX" and p2[3] == q and (" if " not in ops[j]):
                unread_ccx_before_hmr += 1
            break

    stages_out = {}
    total_toffoli_like = 0
    for st, cnt in stage_paid.items():
        st_tot = sum(cnt.values())
        total_toffoli_like += st_tot
        stages_out[st] = {
            "ops": stage_ops[st],
            "toffoli_like": st_tot,
            "CCX": cnt["CCX"],
            "CSWAP": cnt["CSWAP"],
            "CCZ": cnt["CCZ"],
        }

    return {
        "kmb": str(kmb_path),
        "sha256": sha256_file(kmb_path),
        "num_qubits": int(c.num_qubits),
        "total_ops": total_ops,
        "total_toffoli_like": total_toffoli_like,
        "unread_ccx_before_hmr": unread_ccx_before_hmr,
        "stages": stages_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-by-stage census and liveness audit of Public Frontier dqi.kmb (4432ec5f)"
    )
    parser.add_argument(
        "--frontier-kmb",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/release/dqi.kmb"),
    )
    parser.add_argument(
        "--syed-v9-kmb",
        type=Path,
        default=Path("artifacts/20261106_syed_v9/release/dqi.kmb"),
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/audit_summary.json"),
    )
    args = parser.parse_args()

    res_new = stage_census(args.frontier_kmb)
    res_v9 = stage_census(args.syed_v9_kmb)

    stage_diffs = {}
    for st in res_new["stages"]:
        n_st = res_new["stages"][st]
        v_st = res_v9["stages"][st]
        stage_diffs[st] = {
            "syed_v9_toffoli_like": v_st["toffoli_like"],
            "frontier_toffoli_like": n_st["toffoli_like"],
            "delta_toffoli_like": n_st["toffoli_like"] - v_st["toffoli_like"],
            "delta_CCX": n_st["CCX"] - v_st["CCX"],
            "delta_CCZ": n_st["CCZ"] - v_st["CCZ"],
            "delta_CSWAP": n_st["CSWAP"] - v_st["CSWAP"],
        }

    summary = {
        "syed_v9": res_v9,
        "frontier_4432ec5f": res_new,
        "delta_total_toffoli_like": (
            res_new["total_toffoli_like"] - res_v9["total_toffoli_like"]
        ),
        "stage_diffs": stage_diffs,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
