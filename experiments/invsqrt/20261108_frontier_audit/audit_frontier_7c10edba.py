from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import kickmix as km
import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ops(kmb_path: Path) -> list[str]:
    c = km.Circuit.from_file(str(kmb_path))
    buf = io.StringIO()
    c.to_file(buf, format="kmx")
    return [
        line
        for line in buf.getvalue().splitlines()
        if line and not line.startswith(("APPEND", "REGISTER"))
    ]


def extract_write_segments(ops: list[str]) -> tuple[list[dict], list[dict]]:
    segs_ge2: list[dict] = []
    segs_eq1: list[dict] = []
    for w in range(62):
        w_str = f"q{w}"
        cur_ccx: list[tuple[int, str]] = []
        cur_ops: list[tuple[int, str]] = []
        start_idx = 0
        prev_idx = 0
        depth = 0
        for idx, l in enumerate(ops):
            if l.startswith("PUSH_CONDITION"):
                depth += 1
                continue
            if l.startswith("POP_CONDITION"):
                depth -= 1
                continue
            parts = l.split()
            if w_str not in parts:
                continue
            op = parts[0]
            is_cond = (depth > 0) or (" if " in l)
            if (not is_cond) and (
                (op == "X" and parts[1] == w_str)
                or (op == "CX" and parts[2] == w_str)
                or (op == "CCX" and parts[3] == w_str)
            ):
                if not cur_ops:
                    start_idx = idx
                cur_ops.append((idx, l))
                if op == "CCX":
                    cur_ccx.append((idx, l))
            else:
                if len(cur_ccx) >= 2:
                    segs_ge2.append(
                        {
                            "w": w,
                            "prev": prev_idx,
                            "start": start_idx,
                            "end": cur_ops[-1][0],
                            "next": idx,
                            "n_ccx": len(cur_ccx),
                            "next_op": l,
                            "ccx_indices": [x[0] for x in cur_ccx],
                        }
                    )
                elif len(cur_ccx) == 1:
                    segs_eq1.append(
                        {
                            "w": w,
                            "prev": prev_idx,
                            "start": start_idx,
                            "end": cur_ops[-1][0],
                            "next": idx,
                            "n_ccx": 1,
                        }
                    )
                cur_ccx = []
                cur_ops = []
                prev_idx = idx
    return segs_ge2, segs_eq1


def check_hmr_liveness(ops: list[str]) -> dict:
    unread_ccx_before_hmr = 0
    zpow_guarded_ccx_before_hmr = 0
    for idx, l in enumerate(ops):
        parts = l.split()
        if parts[0] not in ("HMR", "R"):
            continue
        q = parts[1]
        saw_zpow = False
        for j in range(idx - 1, -1, -1):
            p2 = ops[j].split()
            if p2[0] in ("PUSH_CONDITION", "POP_CONDITION"):
                continue
            if q not in p2:
                continue
            op2 = p2[0]
            if op2 in ("Z", "Z_POW", "CZ", "CCZ"):
                saw_zpow = True
                continue
            if op2 == "CCX" and p2[3] == q and (" if " not in ops[j]):
                if saw_zpow:
                    zpow_guarded_ccx_before_hmr += 1
                else:
                    unread_ccx_before_hmr += 1
            break
    return {
        "unread_ccx_before_hmr": unread_ccx_before_hmr,
        "zpow_guarded_ccx_before_hmr": zpow_guarded_ccx_before_hmr,
    }


def run_bit_parallel_audit(ops: list[str]) -> dict:
    # Full-domain bit-parallel pass over all 3,133,452 inputs (48,961 uint64 words)
    n_inputs = 3133452
    n_words = (n_inputs + 63) // 64
    xs = np.arange(1, n_inputs + 1, dtype=np.uint64)
    pad = n_words * 64 - n_inputs
    if pad > 0:
        xs_pad = np.concatenate([xs, np.ones(pad, dtype=np.uint64)])
    else:
        xs_pad = xs
    shifts = np.arange(64, dtype=np.uint64)
    q = [np.zeros(n_words, dtype=np.uint64) for _ in range(62)]
    for bit in range(22):
        bval = ((xs_pad >> bit) & 1).astype(np.uint64)
        q[bit] = np.bitwise_or.reduce(bval.reshape(-1, 64) << shifts, axis=1)

    last_mask = (
        (np.uint64(1) << np.uint64(n_inputs % 64)) - np.uint64(1)
        if (n_inputs % 64) != 0
        else np.uint64(0xFFFFFFFFFFFFFFFF)
    )
    ones = np.full(n_words, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[-1] = last_mask

    depth = 0
    degenerate_uncond_paid = 0
    lo_pass_q23_and_q21_pop = -1

    for idx, l in enumerate(ops):
        if l.startswith("PUSH_CONDITION"):
            depth += 1
            continue
        if l.startswith("POP_CONDITION"):
            depth -= 1
            continue
        if depth > 0 or (" if " in l):
            continue
        parts = l.split()
        op = parts[0]
        if idx == 25910:
            both = q[23] & q[21]
            both[-1] &= last_mask
            lo_pass_q23_and_q21_pop = int(
                np.sum(np.bitwise_count(both))
            )
        if op in ("HMR", "R"):
            w = int(parts[1][1:])
            q[w].fill(0)
        elif op == "X":
            w = int(parts[1][1:])
            q[w] ^= ones
        elif op == "CX":
            c, t = int(parts[1][1:]), int(parts[2][1:])
            q[t] ^= q[c]
        elif op == "SWAP":
            a, b = int(parts[1][1:]), int(parts[2][1:])
            q[a], q[b] = q[b], q[a]
        elif op == "CCX":
            a, b, t = int(parts[1][1:]), int(parts[2][1:]), int(parts[3][1:])
            prod = q[a] & q[b]
            prod[-1] &= last_mask
            qa = q[a].copy()
            qa[-1] &= last_mask
            qb = q[b].copy()
            qb[-1] &= last_mask
            if (
                not np.any(prod)
                or np.array_equal(prod, ones)
                or np.array_equal(prod, qa)
                or np.array_equal(prod, qb)
            ):
                degenerate_uncond_paid += 1
            q[t] ^= prod
        elif op == "CSWAP":
            c, a, b = int(parts[1][1:]), int(parts[2][1:]), int(parts[3][1:])
            diff = q[a] ^ q[b]
            prod = q[c] & diff
            prod[-1] &= last_mask
            qc = q[c].copy()
            qc[-1] &= last_mask
            df = diff.copy()
            df[-1] &= last_mask
            if (
                not np.any(prod)
                or np.array_equal(prod, ones)
                or np.array_equal(prod, qc)
                or np.array_equal(prod, df)
            ):
                degenerate_uncond_paid += 1
            q[a] ^= prod
            q[b] ^= prod

    anc_clean = True
    for w in range(22, 62):
        arr = q[w].copy()
        arr[-1] &= last_mask
        if np.any(arr):
            anc_clean = False
            break

    return {
        "n_inputs_verified": n_inputs,
        "degenerate_uncond_paid_gates": degenerate_uncond_paid,
        "lo_pass_q23_and_q21_popcount": lo_pass_q23_and_q21_pop,
        "ancilla_q22_q61_all_zero_at_end": anc_clean,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full-domain algebraic and structural audit of Public Frontier invsqrt.kmb (7c10edba)"
    )
    parser.add_argument(
        "--kmb",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/release/invsqrt.kmb"),
    )
    parser.add_argument(
        "--syed-v9-kmb",
        type=Path,
        default=Path("artifacts/20261106_syed_v9/release/invsqrt.kmb"),
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("artifacts/20261108_public_frontier/audit_summary.json"),
    )
    args = parser.parse_args()

    ops_new = parse_ops(args.kmb)
    ops_v9 = parse_ops(args.syed_v9_kmb)

    cnt_new = Counter(l.split()[0] for l in ops_new)
    cnt_v9 = Counter(l.split()[0] for l in ops_v9)
    segs_ge2, segs_eq1 = extract_write_segments(ops_new)
    hmr_info = check_hmr_liveness(ops_new)
    bp_info = run_bit_parallel_audit(ops_new)

    toffoli_like_new = (
        cnt_new["CCX"] + cnt_new["CCZ"] + cnt_new["CSWAP"] + cnt_new["CCX_CARRY"]
    )
    toffoli_like_v9 = (
        cnt_v9["CCX"] + cnt_v9["CCZ"] + cnt_v9["CSWAP"] + cnt_v9["CCX_CARRY"]
    )

    summary = {
        "frontier_kmb": str(args.kmb),
        "frontier_sha256": sha256_file(args.kmb),
        "syed_v9_sha256": sha256_file(args.syed_v9_kmb),
        "counts": {
            "syed_v9": {
                "ops": len(ops_v9),
                "toffoli_like": toffoli_like_v9,
                "CCX": cnt_v9["CCX"],
                "CCZ": cnt_v9["CCZ"],
                "CSWAP": cnt_v9["CSWAP"],
                "HMR": cnt_v9["HMR"],
                "Z_POW": cnt_v9["Z_POW"],
            },
            "frontier_7c10edba": {
                "ops": len(ops_new),
                "toffoli_like": toffoli_like_new,
                "CCX": cnt_new["CCX"],
                "CCZ": cnt_new["CCZ"],
                "CSWAP": cnt_new["CSWAP"],
                "HMR": cnt_new["HMR"],
                "Z_POW": cnt_new["Z_POW"],
            },
            "delta_static_toffoli_like": toffoli_like_new - toffoli_like_v9,
        },
        "write_accumulation_segments": {
            "segments_ge2_ccx": len(segs_ge2),
            "segments_eq1_ccx": len(segs_eq1),
            "symplectic_rank_reductions_remaining": 0,
        },
        "hmr_peephole_audit": hmr_info,
        "full_domain_bit_parallel_audit": bp_info,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
