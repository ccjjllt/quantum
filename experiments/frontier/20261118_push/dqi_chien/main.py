"""DQI Chien/Forney phase mechanism — window dump (CPU-only Kaggle kernel).

Reads tape 575b043f (staged from the public dataset, never locally), locates the 4,025
`BIT_STORE1_IF`-run anchors, and dumps, for a few positions, every instruction of the
per-position block with operands translated to register names.  Then it takes the
qubits and classical bits touched by the 11 Toffoli-likes of position 0 and prints their
complete touch history over the whole tape, so the mechanism (what the 10 CCX and the
1 CCZ compute, what holds e_j, when it is initialised/cleared) is evidenced, not guessed.

No simulation.  Only the instruction stream is read.
"""
import hashlib
import importlib.util
import json
import lzma
import os
import pathlib
import sys
import time
import traceback

import numpy as np

WORK = pathlib.Path("/kaggle/working")
TMP = pathlib.Path("/tmp")
OUTD = WORK / "out"
OUTD.mkdir(parents=True, exist_ok=True)
T0 = time.time()


def say(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def find(pat):
    for p in pathlib.Path("/kaggle/input").rglob(pat):
        return p
    raise SystemExit(f"missing {pat}")


def run():
    XZ = find("dqi_575b043f.kmb.xz")
    IRPY = find("vqcc_ir.py")
    VS = find("verify_submission_dqi.py")
    COMP = VS.parents[2]
    say("inputs", XZ, IRPY, COMP)

    raw = TMP / "dqi.kmb"
    if not raw.exists() or raw.stat().st_size < 400_000_000:
        say("decompress")
        with lzma.open(XZ, "rb") as fi, open(raw, "wb") as fo:
            while True:
                b = fi.read(1 << 23)
                if not b:
                    break
                fo.write(b)
    OUT = {"kmb_sha256": sha256(raw), "kmb_bytes": raw.stat().st_size}
    say("kmb", OUT["kmb_sha256"], OUT["kmb_bytes"])

    spec = importlib.util.spec_from_file_location("vqcc_ir", str(IRPY))
    ir = importlib.util.module_from_spec(spec)
    sys.modules["vqcc_ir"] = ir
    spec.loader.exec_module(ir)
    c = ir.Circuit.read(str(raw))
    t = c.types
    N = c.num_ops
    OUT["num_ops"] = N
    OUT["num_qubits"] = c.num_qubits
    OUT["num_bits"] = c.num_bits
    NAMES = [ir.name(x) if bool(ir.VALID[x]) else f"?{x:02x}" for x in range(256)]
    say("ops", N, "q", c.num_qubits, "b", c.num_bits)

    # ------------------------------------------------------------ registers
    qmap, bmap, regs = {}, {}, []
    for nm, ids in c.registers:
        isq = (ids >> 31) == 1
        qs = (ids[isq] & 0x7FFFFFFF).tolist()
        bs = ids[~isq].tolist()
        regs.append([nm, "q" if qs else "b", len(qs) if qs else len(bs),
                     int(min(qs)) if qs else int(min(bs))])
        for k, x in enumerate(qs):
            qmap[int(x)] = (nm, k)
        for k, x in enumerate(bs):
            bmap[int(x)] = (nm, k)
    (OUTD / "registers.json").write_text(json.dumps(regs))
    OUT["registers_head"] = regs[:2]
    OUT["registers_pool"] = regs[70:76]
    OUT["registers_tail"] = regs[-3:]
    OUT["n_registers"] = len(regs)
    say("registers", len(regs), "qmap", len(qmap), "bmap", len(bmap), "pool", OUT["registers_pool"])

    def lq(q):
        r = qmap.get(int(q))
        return f"{r[0]}[{r[1]}]" if r else f"Q{int(q)}"

    def lb(b):
        if b is None:
            return "-"
        r = bmap.get(int(b))
        return f"{r[0]}[{r[1]}]" if r else f"B{int(b)}"

    # ------------------------------------------------- operand consumption
    def cum(mask):
        a = np.zeros(N + 1, dtype=np.int64)
        a[1:] = np.cumsum(mask[t])
        return a

    cfun3, cfun2, cfun1, cfunb, cfunc = cum(ir.L3Q), cum(ir.L2Q), cum(ir.L1Q), cum(ir.L1B), cum(ir.LCOND)
    say("offsets done")

    # -------------------------------------------------------- Chien anchor
    ebits = set()
    for nm, ids in c.registers:
        if nm.startswith("E") and nm[1:].isdigit():
            ebits.update(int(x) for x in ids)
    EBIT_MAX = max(ebits)
    bs1 = np.flatnonzero(t == 0xC1)
    cond_of = c.bc[cfunc[bs1 + 1] - 1].astype(np.int64).tolist()
    found = []
    i, npos = 0, len(cond_of)
    while i + 11 < npos:
        c0 = cond_of[i]
        if c0 % 12 == 0 and c0 < EBIT_MAX and all(cond_of[i + k] == c0 + k for k in range(12)):
            found.append((int(bs1[i]), c0 // 12))
            i += 12
        else:
            i += 1
    anchors = np.array([f[0] for f in found], dtype=np.int64)
    posj = np.array([f[1] for f in found], dtype=np.int64)
    A, B = int(anchors.min()), int(anchors.max())
    OUT["chien_positions"] = len(found)
    OUT["chien_region"] = [A, B]
    OUT["chien_j_range"] = [int(posj.min()), int(posj.max())]
    OUT["chien_j_first20"] = posj[:20].tolist()
    OUT["chien_j_last10"] = posj[-10:].tolist()
    say("anchors", len(found), A, B, int(posj.min()), int(posj.max()))

    def window_text(a, b, title):
        lines = [f"# {title}  ops [{a}, {b})"]
        stack = []
        ev = np.flatnonzero((t[:a] == 0x81) | (t[:a] == 0x01))
        if len(ev):
            k = len(ev) - 1
            d = 0
            while k >= 0:
                d += 1 if t[ev[k]] == 0x81 else -1
                if d == 0:
                    break
                k -= 1
            for e in ev[k + 1:]:
                stack.append(c.bc[cfunc[e + 1] - 1])
        for (idx, nm, qs, tb, cb) in c.decode(a, b):
            op = int(t[idx])
            tag = "  PUSH" if op == 0x81 else ("  POP" if op == 0x01 else "")
            lines.append(f"{idx:9d} {nm:16s} q=[{','.join(lq(q) for q in qs)}]"
                         f"{'' if tb is None else ' tb=' + lb(tb)}"
                         f"{'' if cb is None else ' c=' + lb(cb)}"
                         f" d={len(stack)}{tag}")
            if op == 0x81:
                stack.append(cb)
            elif op == 0x01 and stack:
                stack.pop()
        return "\n".join(lines) + "\n"

    # ---------------------------------------------------- toffoli cache in B
    tof = np.flatnonzero(ir.LTOF[t])
    i3 = cfun3[tof + 1] - 1
    opc = t[tof] & 0x7F
    is_ccx = opc == 0x31
    is_ccz = opc == 0x30
    Q0, Q1, Q2 = c.qqq0[i3], c.qqq1[i3], c.qqq2[i3]
    inB = (tof >= A) & (tof <= B)
    tofB = tof[inB]
    QB0, QB1, QB2 = Q0[inB], Q1[inB], Q2[inB]
    ccx_m, ccz_m = is_ccx[inB], is_ccz[inB]
    say("tofB", len(tofB), "ccx", int(ccx_m.sum()), "ccz", int(ccz_m.sum()))

    assign = np.searchsorted(anchors, tofB, side="right") - 1
    cnt = np.bincount(assign)
    OUT["tofB_per_position_hist"] = {}
    for k, v in enumerate(cnt.tolist()):
        OUT["tofB_per_position_hist"][str(v)] = OUT["tofB_per_position_hist"].get(str(v), 0) + 1

    sigpos = {}
    for n in range(len(anchors)):
        sel = assign == n
        key = tuple() if not sel.any() else tuple(
            (int(o - anchors[n]), int(opc[inB][sel][k]), int(QB0[sel][k]), int(QB1[sel][k]), int(QB2[sel][k]))
            for k, o in enumerate(tofB[sel]))
        sigpos.setdefault(key, []).append(n)
    OUT["n_distinct_toffoli_signatures"] = len(sigpos)
    OUT["signature_groups"] = [
        {"n_positions": len(v), "first": v[:5],
         "sig": [f"{d}:{NAMES[o]}({lq(x)},{lq(y)},{lq(z)})" for d, o, x, y, z in key]}
        for key, v in sigpos.items() if key][:4]
    OUT["signature_group_sizes"] = sorted((len(v) for v in sigpos.values()), reverse=True)[:10]
    say("distinct signatures", len(sigpos), OUT["signature_group_sizes"])

    def dump_window_jsons(npos):
        p = int(anchors[npos])
        e = int(anchors[npos + 1]) if npos + 1 < len(anchors) else B + 1
        return [{"i": idx, "n": nm, "q": [int(x) for x in qs], "ql": [lq(q) for q in qs],
                 "tb": None if tb is None else int(tb), "tbl": lb(tb),
                 "cb": None if cb is None else int(cb), "cbl": lb(cb)}
                for (idx, nm, qs, tb, cb) in c.decode(p, e)]

    for npos, name in [(0, "p0"), (1, "p1"), (2000, "p2000"), (len(anchors) - 1, "plast")]:
        p = int(anchors[npos])
        e = int(anchors[npos + 1]) if npos + 1 < len(anchors) else B + 2
        (OUTD / f"window_{name}.txt").write_text(window_text(max(0, p - 80), e + 10,
                                                            f"position {npos} j={int(posj[npos])}"))
        (OUTD / f"window_{name}.json").write_text(json.dumps(dump_window_jsons(npos)))
        say("dumped", name, "ops", e - p)

    bc = np.bincount(t[A:B + 1], minlength=256)
    OUT["regionB_opcodes"] = {NAMES[k]: int(v) for k, v in enumerate(bc.tolist()) if v}
    OUT["regionB_per_position"] = {k: round(v / len(anchors), 3) for k, v in OUT["regionB_opcodes"].items()}

    # ---------------------- touch history of the position-0 block operands
    p0, e0 = int(anchors[0]), int(anchors[1])
    sel0 = (tofB >= p0) & (tofB < e0)
    tq = sorted({int(x) for x in np.concatenate([QB0[sel0], QB1[sel0], QB2[sel0]])})
    hmr_op = np.flatnonzero((t[p0:e0] & 0x7F) == 0x50) + p0
    hq = sorted({int(x) for x in c.q0[cfun1[hmr_op + 1] - 1]})
    hb = sorted({int(x) for x in c.b0[cfunb[hmr_op + 1] - 1]})
    OUT["pos0_toffoli_qubits"] = [lq(q) for q in tq]
    OUT["pos0_hmr_qubits"] = [lq(q) for q in hq]
    OUT["pos0_hmr_out_bits"] = [lb(b) for b in hb]
    OUT["pos0_hmr_offsets"] = [int(x) - p0 for x in hmr_op]
    OUT["ccx_operands_pos0"] = [[lq(x), lq(y), lq(z)] for x, y, z in
                                zip(QB0[ccx_m][sel0], QB1[ccx_m][sel0], QB2[ccx_m][sel0])]
    OUT["ccz_operands_pos0"] = [[lq(x), lq(y), lq(z)] for x, y, z in
                                zip(QB0[ccz_m][sel0], QB1[ccz_m][sel0], QB2[ccz_m][sel0])]
    OUT["ccx_offsets_pos0"] = [int(o) - p0 for o in tofB[ccx_m] if p0 <= o < e0]
    OUT["ccz_offsets_pos0"] = [int(o) - p0 for o in tofB[ccz_m] if p0 <= o < e0]
    say("pos0 tof qubits", OUT["pos0_toffoli_qubits"])
    say("pos0 hmr qubits", OUT["pos0_hmr_qubits"], "out bits", OUT["pos0_hmr_out_bits"])

    interesting_q = set(tq) | set(hq)
    interesting_b = set(hb)
    j0 = int(posj[0])
    interesting_b |= {int(x) for nm, ids in c.registers if nm == f"E{j0}" for x in ids}
    OUT["pos0_E_register"] = f"E{j0}"
    OUT["pos0_E_bits"] = [lb(b) for b in sorted(interesting_b) if lb(b).startswith("E")]

    def op_of(arr_len_cum, k):
        return np.searchsorted(arr_len_cum, k, side="right") - 1

    hist = {}
    iq = np.array(sorted(interesting_q), dtype=np.uint32)
    ib = np.array(sorted(interesting_b), dtype=np.uint32)
    for arr, lab, cm, fn in ((c.qqq0, "qqq0", cfun3, None), (c.qqq1, "qqq1", cfun3, None),
                             (c.qqq2, "qqq2", cfun3, None), (c.qq0, "qq0", cfun2, None),
                             (c.qq1, "qq1", cfun2, None), (c.q0, "q0", cfun1, None)):
        for k in np.flatnonzero(np.isin(arr, iq)).tolist():
            hist.setdefault(int(op_of(cm, k)), []).append(f"{lab}={lq(arr[k])}")
    for arr, lab, cm in ((c.b0, "b0", cfunb), (c.bc, "bc", cfunc)):
        for k in np.flatnonzero(np.isin(arr, ib)).tolist():
            hist.setdefault(int(op_of(cm, k)), []).append(f"{lab}={lb(arr[k])}")
    say("history ops", len(hist), "first", min(hist) if hist else None, "last", max(hist) if hist else None)

    ev = np.flatnonzero((t == 0x81) | (t == 0x01))
    evkind = np.where(t[ev] == 0x81, 1, -1)
    evbit = c.bc[cfunc[np.minimum(ev + 1, N)] - 1]
    depths = np.concatenate([[0], np.cumsum(evkind)])
    say("events", len(ev), "push", int((evkind == 1).sum()), "pop", int((evkind == -1).sum()))

    ops_sorted = sorted(hist)
    hl = ["# full touch history of the qubits/bits used by position 0's Toffoli block",
          f"# toffoli qubits: {OUT['pos0_toffoli_qubits']}",
          f"# hmr qubits: {OUT['pos0_hmr_qubits']}  out bits: {OUT['pos0_hmr_out_bits']}",
          f"# {OUT['pos0_E_register']} bits: {OUT['pos0_E_bits']}",
          f"# anchor p0={p0} p1={e0}   region A={A} B={B}",
          "# op index | opcode | operands touching the set | cond-stack depth | stack"]
    first = ops_sorted[0]
    jj = int(np.searchsorted(ev, first)) - 1
    kk = jj
    while kk >= 0 and depths[kk + 1] > 0:
        kk -= 1
    stack = [lb(evbit[e]) for e in ev[kk + 1:jj + 1]]
    hl.append(f"# stack at {first} (depth {int(depths[jj + 1])}): {stack}")
    ei = jj + 1
    for op in ops_sorted:
        while ei < len(ev) and ev[ei] <= op:
            if evkind[ei] == 1:
                stack.append(lb(evbit[ei]))
            elif stack:
                stack.pop()
            ei += 1
        hl.append(f"{op:9d} {NAMES[int(t[op])]:16s} {' '.join(sorted(set(hist[op]))):63s} d={len(stack)} stack={stack}")
    (OUTD / "touch_history_p0.txt").write_text("\n".join(hl) + "\n")
    say("history lines", len(hl))

    # ------------------------------------------------ what does the CCZ touch?
    czz = [(int(tofB[k]), lq(QB0[k]), lq(QB1[k]), lq(QB2[k])) for k in np.flatnonzero(ccz_m).tolist()]
    OUT["ccz_first5"] = czz[:5]
    OUT["ccz_reg_triples"] = {}
    for o, a_, b_, c_ in czz:
        key = "|".join(x.split("[")[0] for x in (a_, b_, c_))
        OUT["ccz_reg_triples"][key] = OUT["ccz_reg_triples"].get(key, 0) + 1
    OUT["ccx_reg_triples"] = {}
    for k in np.flatnonzero(ccx_m).tolist():
        key = "|".join(x.split("[")[0] for x in (lq(QB0[k]), lq(QB1[k]), lq(QB2[k])))
        OUT["ccx_reg_triples"][key] = OUT["ccx_reg_triples"].get(key, 0) + 1
    say("ccx triples", json.dumps(OUT["ccx_reg_triples"]))
    say("ccz triples", json.dumps(OUT["ccz_reg_triples"]))
    say("offsets ccx", OUT["ccx_offsets_pos0"], "ccz", OUT["ccz_offsets_pos0"])

    # ------------------------- condition-class census over region B toffolis
    E_ids = np.array(sorted(ebits), dtype=np.uint32)
    is_e = np.isin(evbit, E_ids).astype(np.int64)
    e_open = np.concatenate([[0], np.cumsum(evkind * is_e)])
    kb = np.searchsorted(ev, tofB, side="right") - 1
    OUT["regionB_toffoli_underE"] = int((e_open[kb + 1] > 0).sum())
    OUT["regionB_toffoli_depth_hist"] = {}
    for v in depths[kb + 1].tolist():
        OUT["regionB_toffoli_depth_hist"][str(v)] = OUT["regionB_toffoli_depth_hist"].get(str(v), 0) + 1
    say("underE", OUT["regionB_toffoli_underE"], "depth", OUT["regionB_toffoli_depth_hist"])

    OUT["seconds"] = round(time.time() - T0, 1)
    (OUTD / "chien_dump.json").write_text(json.dumps(OUT, indent=1))
    print("RESULT_JSON_BEGIN")
    print(json.dumps(OUT, indent=1)[:20000])
    print("RESULT_JSON_END")


try:
    run()
except Exception:
    tb = traceback.format_exc()
    say("FAILED")
    print(tb)
    (OUTD / "error.txt").write_text(tb)
