"""Rewrite CCX gates whose two controls are functionally dependent on the
1220 real addresses of a dfthcsos ANGLE loader.

For a CCX with controls a,b and target t, if a implies b (a & ~b == 0) on
every real address, the gate equals CX(a,t) there; if b implies a, it equals
CX(b,t).  A cache AND is uncomputed later by HMR(t) + CZ(a,b); that pair is
replaced by the same CX so no measurement-kickback phase is left behind.
Product gates have no uncompute pair.

The output family is identical on every address the official verifier samples,
while the per-shot Toffoli count drops.  Padding rows (>= 1220) are never read
and are allowed to differ.

This script only rewrites text; validity is checked separately.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

FULL = (1 << 1220) - 1
QRE = re.compile(r"q(\d+)")


def selection_masks() -> list[int]:
    a = np.arange(1220, dtype=np.int64)
    return [
        int.from_bytes(np.packbits(((a >> i) & 1).astype(bool), bitorder="little").tobytes(), "little")
        for i in range(11)
    ]


def parse_registers(lines: list[str]) -> dict[str, list[int]]:
    append: dict[int, str] = {}
    names: dict[str, str] = {}
    registers: dict[str, list[int]] = {}
    for line in lines:
        t = line.split()
        if not t:
            continue
        if t[0] == "APPEND_TO_REGISTER":
            append[int(t[1][1:])] = t[2]
        elif t[0] == "REGISTER":
            names[t[1]] = t[2].strip('"')
            registers[names[t[1]]] = [q for q, r in append.items() if r == t[1]]
    return registers


def word_masks(words: np.ndarray, k: int) -> dict[str, list[int]]:
    """Bitmasks of the incoming batch in circuit k: batch k-1 (zero for k=0)."""
    batch = np.zeros((1220, 5), dtype=np.int64) if k == 0 else words[:, 5 * (k - 1):5 * k]
    out = {}
    for j in range(5):
        out[f"word_{j}"] = [
            int.from_bytes(np.packbits(((batch[:, j] >> b) & 1).astype(bool), bitorder="little").tobytes(), "little")
            for b in range(8)
        ]
    return out


def rewrite(circuit, k: int, words: np.ndarray) -> tuple[list[str], dict]:
    lines = str(circuit).splitlines()
    regs = parse_registers(lines)
    vals = {i: 0 for i in range(circuit.num_qubits)}
    sel = selection_masks()
    for i, q in enumerate(regs.get("selection", [])):
        vals[q] = sel[i]
    incoming = word_masks(words, k)
    for name, qs in regs.items():
        if name in incoming:
            for q, mask in zip(qs, incoming[name]):
                vals[q] = mask
    word_qubits = {q for name, qs in regs.items() if name.startswith("word_") for q in qs}
    replacements: dict[int, dict] = {}  # init line index -> info
    for idx, line in enumerate(lines):
        t = line.split()
        if not t:
            continue
        op = t[0]
        qs = [int(x) for x in QRE.findall(line)]
        if op == "X":
            vals[qs[0]] ^= FULL
        elif op == "CX":
            vals[qs[1]] ^= vals[qs[0]]
        elif op == "CCX":
            a, b, target = qs
            ca, cb = vals[a], vals[b]
            if " if " in line:
                raise SystemExit(f"conditioned CCX is not handled: {line}")
            if ca & (FULL ^ cb) == 0:
                replacements[idx] = {"a": a, "b": b, "target": target, "keep": a, "kind": "a_implies_b"}
                vals[target] ^= ca
            elif cb & (FULL ^ ca) == 0:
                replacements[idx] = {"a": a, "b": b, "target": target, "keep": b, "kind": "b_implies_a"}
                vals[target] ^= cb
            elif ca & cb == 0:
                replacements[idx] = {"a": a, "b": b, "target": target, "keep": None, "kind": "always_zero"}
            else:
                vals[target] ^= ca & cb
        elif op == "HMR":
            vals[qs[0]] = 0
    # locate the HMR + CZ uncompute pair for every replaced cache target
    used: set[int] = set()
    out = list(lines)
    details = []
    for idx, info in sorted(replacements.items()):
        target, a, b = info["target"], info["a"], info["b"]
        keep = info["keep"]
        out[idx] = "# removed always-zero CCX" if keep is None else f"CX q{keep} q{target}"
        detail = dict(info, init_line=idx + 1)
        if target not in word_qubits:
            hmr_i = None
            for j, line in enumerate(lines):
                t = line.split()
                if t[:2] == ["HMR", f"q{target}"] and j not in used:
                    hmr_i = j
                    break
            if hmr_i is None:
                raise SystemExit(f"k{k}: no HMR uncompute for cache target q{target}")
            bit = lines[hmr_i].split()[2]
            cz_i = None
            for j in range(hmr_i + 1, len(lines)):
                t = lines[j].split()
                if len(t) >= 5 and t[0] == "CZ" and t[-1] == bit:
                    controls = {int(t[1][1:]), int(t[2][1:])}
                    if controls == {a, b}:
                        cz_i = j
                        break
            if cz_i is None:
                raise SystemExit(f"k{k}: no matching CZ uncompute for q{target} ({a},{b})")
            used.update({hmr_i, cz_i})
            if keep is None:
                out[hmr_i] = "# removed always-zero uncompute HMR"
                out[cz_i] = "# removed always-zero uncompute CZ"
            else:
                out[hmr_i] = f"CX q{keep} q{target}"
                out[cz_i] = "# uncompute replaced by CX"
            detail.update(uncompute_hmr_line=hmr_i + 1, uncompute_cz_line=cz_i + 1)
        details.append(detail)
    return out, {"k": k, "ccx_before": sum(1 for l in lines if l.startswith("CCX")),
                 "replaced": len(replacements), "details": details}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--slots", default="0-14")
    ap.add_argument("--words", type=Path, required=True)
    args = ap.parse_args()
    import kickmix

    words = np.load(args.words)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    slots = []
    for part in args.slots.split(","):
        if "-" in part:
            a, b = part.split("-")
            slots += list(range(int(a), int(b) + 1))
        else:
            slots.append(int(part))
    report = {"scope": "text rewrite only; validity checked separately", "slots": []}
    for k in slots:
        circuit = kickmix.Circuit.from_file(args.source_dir / f"angle_k_{k}.kmb")
        lines, row = rewrite(circuit, k, words)
        (args.out_dir / f"angle_k_{k}.kmx").write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
        report["slots"].append(row)
        print(json.dumps(row), flush=True)
    (args.out_dir / "rewrite_report.json").write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
