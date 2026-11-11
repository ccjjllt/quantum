"""9fcda0c1 vs e9f54be3 阶段逐门精确差分（复用 20261110_e9diff/stage_census.py 口径，流式）.
只读，不构建候选、不跑验证器。
"""
from __future__ import annotations
import hashlib, json, sys
from collections import Counter, deque
from pathlib import Path
import kickmix as km

E9_KMB = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmb")
E9_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_e9diff/e9.kmx")
F9_KMB = Path("/Users/zhaohuaxiang/ccjjllt/quantum/artifacts/20261111_ozer296/release/dqi.kmb")
F9_KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_9f/ozer296_9f.kmx")
OUT = Path("artifacts/20261111_newcirc_residual/stage_census_9f_vs_e9.json")

PAID = ("CCX", "CCZ", "CSWAP", "CCX_CARRY")
SKIP_PREFIX = ("APPEND", "REGISTER", "INFO_TAG", "SEMANTIC", "ANNOTATION")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def stage_census_kmx(kmx_path: Path, kmb_path: Path) -> dict:
    stage_paid: dict[str, Counter] = {}
    stage_ops: Counter = Counter()
    total_ops = 0
    unread_ccx_before_hmr = 0
    stack: list[str] = []
    window: deque[str] = deque(maxlen=61)
    num_qubits = 0
    try:
        c = km.Circuit.from_file(str(kmb_path))
        num_qubits = int(c.num_qubits)
    except Exception:
        pass
    with kmx_path.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            l = l.rstrip("\n")
            if l.startswith("INFO_TAG "):
                try:
                    tag = l.strip().split('"', 2)[1]
                except IndexError:
                    continue
                if tag.startswith("@enter:"):
                    stack.append(tag[7:])
                elif tag.startswith("@exit:") and stack:
                    stack.pop()
                if l:
                    window.append(l)
                continue
            if not l or l.startswith(SKIP_PREFIX):
                continue
            stage = stack[0] if stack else "header"
            total_ops += 1
            stage_ops[stage] += 1
            op = l.split()[0]
            if op in PAID:
                if stage not in stage_paid:
                    stage_paid[stage] = Counter()
                stage_paid[stage][op] += 1
            if op in ("HMR", "R"):
                p = l.split()
                q = p[1] if len(p) > 1 else ""
                hist = list(window)[-60:]
                for past in reversed(hist):
                    p2 = past.split()
                    if not p2:
                        continue
                    if p2[0] in ("PUSH_CONDITION", "POP_CONDITION"):
                        continue
                    if q not in p2:
                        continue
                    if p2[0] == "CCX" and len(p2) > 3 and p2[3] == q and (" if " not in past):
                        unread_ccx_before_hmr += 1
                    break
            window.append(l)
    stages_out = {}
    total_paid = 0
    for st, cnt in stage_paid.items():
        st_tot = sum(cnt.values())
        total_paid += st_tot
        stages_out[st] = {"ops": stage_ops[st], "toffoli_like": st_tot,
            "CCX": int(cnt.get("CCX", 0)), "CSWAP": int(cnt.get("CSWAP", 0)),
            "CCZ": int(cnt.get("CCZ", 0)), "CCX_CARRY": int(cnt.get("CCX_CARRY", 0))}
    return {"kmb": str(kmb_path), "sha256": sha256_file(kmb_path),
        "num_qubits": num_qubits, "total_ops": total_ops,
        "total_toffoli_like": total_paid, "unread_ccx_before_hmr": unread_ccx_before_hmr,
        "stages": stages_out}

def main() -> None:
    print("census e9...", flush=True)
    res_e = stage_census_kmx(E9_KMX, E9_KMB)
    print("census 9f...", flush=True)
    res_n = stage_census_kmx(F9_KMX, F9_KMB)
    stage_diffs = {}
    for st in res_e["stages"]:
        n_st = res_n["stages"].get(st, {"toffoli_like": 0, "CCX": 0, "CCZ": 0, "CSWAP": 0, "CCX_CARRY": 0, "ops": 0})
        v_st = res_e["stages"][st]
        stage_diffs[st] = {"e9_toffoli_like": v_st["toffoli_like"], "new_toffoli_like": n_st["toffoli_like"],
            "delta_toffoli_like": n_st["toffoli_like"] - v_st["toffoli_like"],
            "delta_CCX": n_st["CCX"] - v_st["CCX"], "delta_CCZ": n_st["CCZ"] - v_st["CCZ"],
            "delta_CSWAP": n_st["CSWAP"] - v_st["CSWAP"],
            "delta_CCX_CARRY": n_st.get("CCX_CARRY", 0) - v_st.get("CCX_CARRY", 0),
            "delta_ops": n_st["ops"] - v_st["ops"]}
    summary = {"e9_e9f54be3": res_e, "new_9fcda0c1": res_n,
        "delta_total_toffoli_like": res_n["total_toffoli_like"] - res_e["total_toffoli_like"],
        "delta_total_ops": res_n["total_ops"] - res_e["total_ops"],
        "stage_diffs": stage_diffs}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
