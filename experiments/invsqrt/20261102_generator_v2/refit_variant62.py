"""refit_variant62.py: quantized-width generator variants (new file, reason below).

Why a new file instead of continuing the width_opt62.py single line
(hmr_cleanup.md single-line argument does NOT apply here):
  1. width_opt62.py at SHA 0075e006 is an officially PASSed baseline
     (verify_hmr_seed20261031.log, score 2290413.64). Overwriting it would
     destroy the fallback circuit and churn REC_SHA in prescreen_width_opt.py.
  2. Variants need different stored widths (Ahi 20 / Rhi 10), shifted row
     placement (A rows +2, R rows +2 / fewer rows), different table files and
     different width asserts. Parameterizing the single line would fork every
     builder signature and double-build spectrum anyway.
  3. Side-by-side QxC comparison needs both circuits importable in one process
     (baseline W + variant Q); a separate module reusing W primitives gives
     that without cross-module global mutation.

Reuse: all S1/S2/D/B-load/square/S6/QROM-mini-pass/row kernels are imported
from width_opt62 (no copy) except the A1 two-level row pair, which is copied
with n0/n1 parameters (11+11 -> 10+10 for kA=2; HMR init_and/del_and
preserved). R1 rows are reused directly (generic over Tslice length).
No old KMB/tray is read; tables come from refit_layout62.py outputs.
No official verifier call; prescreen only (gate: official 200M-shot not run).
"""

from __future__ import annotations

import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

import kickmix as km

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import width_opt62 as W  # noqa: E402

ROOT = HERE.parents[2]
ART = ROOT / "artifacts/20261102_generator_v2/invsqrt"

CANDS = {
    "A20": {"tables": ART / "int_tables_A20_quant.json",
            "kA": 2, "kR": 0, "wA": 20, "wR": 12, "nR": 12, "sA": 2, "sR": 0},
    "BOTH": {"tables": ART / "int_tables_R10_A20_quant.json",
             "kA": 2, "kR": 2, "wA": 20, "wR": 10, "nR": 10, "sA": 2, "sR": 2},
    # BOTH_SPARSE (2026-11-02, csd_sparse.md): same widths/shifts as BOTH,
    # only table VALUES sparser (pop 7804->6485, -1319 bits). Builders are
    # fully generic over (wA,wR,nR,sA,sR), so a CANDS entry suffices; no new
    # builder code, no new file (a copy would duplicate ~360 lines for zero
    # structural change). Existing cands untouched (separate table files).
    "BOTH_SPARSE": {"tables": ART / "int_tables_R10_A20_sparse62.json",
             "kA": 2, "kR": 2, "wA": 20, "wR": 10, "nR": 10, "sA": 2, "sR": 2},
    "A18": {"tables": ART / "int_tables_R12_A4_quant.json",
            "kA": 4, "kR": 0, "wA": 18, "wR": 12, "nR": 12, "sA": 4, "sR": 0},
    "R8I": {"tables": ART / "int_tables_R8_idesc2.json",
            "kA": 0, "kR": 4, "wA": 22, "wR": 8, "nR": 8, "sA": 0, "sR": 4},
}

W_X, W_LZ, W_B = W.W_X, W.W_LZ, W.W_B
W_V, W_VHI, W_P = W.W_V, W.W_VHI, W.W_P
W_D = W.W_D
Q_CAP = W.Q_CAP
S_OFF = W.S_OFF


def load_qtables(cand):
    cfg = CANDS[cand]
    doc = json.loads(cfg["tables"].read_text())
    B = tuple(doc["Bs"])
    A = tuple(doc["As"])
    R = tuple(doc["Rs"])
    assert len(B) == len(A) == len(R) == 256
    assert all(0 <= v < 2**33 for v in B)
    assert all(0 <= v < 2**cfg["wA"] for v in A), "Ahi width"
    assert all(0 <= v < 2**cfg["wR"] for v in R), "Rhi width"
    # effective-width V-nonneg bound (same as W.assert_tables: effective
    # A<=2^22, R<=2^12 after shift, so the same bound applies)
    assert min(B) > (2**37 + 2**29) >> 12, "B lower bound"
    return W.CoefTables(B=B, A=A, R=R)


def q_model_phase(x, B, A, R, sA, sR):
    """Integer oracle for quantized tables (mirrors contract62.model_phase
    with effective values A<<sA, R<<sR; B full). Used by prescreen only."""
    lz = 22 - x.bit_length()
    m = x << lz
    p = lz & 1
    a = (p << 7) | ((m >> 14) & 127)
    delta = m & 16383
    D = delta - 8192
    U = (delta >> 5) - 256
    S = U * U
    V = (B[a] << 12) - 2 * (A[a] << sA) * D + (R[a] << sR) * S
    e = (lz >> 1) + p - 11
    t = 8 - e
    P = ((V + 2 ** (t - 1)) >> t) & (2**36 - 1)
    return V, t, P


# ---- A1 two-level rows, generalized to n0/n1 (copied from width_opt62.py
# ---- _narrow_a1_add/sub_fwd with A1_N0/A1_N1 replaced by parameters;
# ---- HMR init_and/del_and structure preserved verbatim) ----
def _qa1_add_fwd(b, S, Tslice, ctl, n0, n1) -> None:
    S0 = S[0:n0]; S1 = S[n0:n0 + n1]
    T0 = Tslice[0:n0]; T1 = Tslice[n0:n0 + n1]; TH = Tslice[n0 + n1:]
    Cp0 = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1); c1 = b.alloc_qubits(1)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0[i])
    for i in range(n0):
        W._narrow_maj(b, Cp0[i], T0[i], ca0[0])
    b.cx(ca0[0], c1[0])
    for i in reversed(range(n0)):
        W._narrow_uma(b, Cp0[i], T0[i], ca0[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0[i])
    b.free(Cp0); b.free(ca0)
    Cp1 = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1[i])
    b.iadd(Cp1, target=T1)
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1[i])
    b.free(Cp1)
    b.iadd(c1, target=T1)
    CpB = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpB[i])
    lt = b.alloc_qubits(1); eq = b.alloc_qubits(1)
    b.flip_if_less_than(T1, CpB, target=lt[0])
    b.flip_if_equal(T1, CpB, target=eq[0])
    s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
    b.init_and(c1[0], eq[0], s[0])
    b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpB[i])
    b.free(CpB)
    b.iadd(c2, target=TH)
    b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
    b.del_and(c1[0], eq[0], s[0]); b.free(s)
    CpC = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpC[i])
    b.flip_if_equal(T1, CpC, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpC[i])
    b.free(CpC); b.free(eq)
    CpD = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], CpD[i])
    b.flip_if_less_than(T1, CpD, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], CpD[i])
    b.free(CpD); b.free(lt)
    Cp0B = b.alloc_qubits(n0)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0B[i])
    b.flip_if_less_than(T0, Cp0B, target=c1[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0B[i])
    b.free(Cp0B); b.free(c1)


def _qa1_sub_fwd(b, S, Tslice, ctl, n0, n1) -> None:
    S0 = S[0:n0]; S1 = S[n0:n0 + n1]
    T0 = Tslice[0:n0]; T1 = Tslice[n0:n0 + n1]; TH = Tslice[n0 + n1:]
    c1 = b.alloc_qubits(1)
    Cp0a = b.alloc_qubits(n0)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0a[i])
    b.flip_if_less_than(T0, Cp0a, target=c1[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0a[i])
    b.free(Cp0a)
    lt = b.alloc_qubits(1)
    Cp1a = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1a[i])
    b.flip_if_less_than(T1, Cp1a, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1a[i])
    b.free(Cp1a)
    eq = b.alloc_qubits(1)
    Cp1b = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1b[i])
    b.flip_if_equal(T1, Cp1b, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1b[i])
    b.free(Cp1b)
    s = b.alloc_qubits(1); c2 = b.alloc_qubits(1)
    b.init_and(c1[0], eq[0], s[0])
    b.cx(lt[0], c2[0]); b.cx(s[0], c2[0])
    b.isub(c2, target=TH)
    b.cx(s[0], c2[0]); b.cx(lt[0], c2[0]); b.free(c2)
    b.del_and(c1[0], eq[0], s[0]); b.free(s)
    Cp1c = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1c[i])
    b.flip_if_equal(T1, Cp1c, target=eq[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1c[i])
    b.free(Cp1c); b.free(eq)
    Cp1d = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1d[i])
    b.flip_if_less_than(T1, Cp1d, target=lt[0])
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1d[i])
    b.free(Cp1d); b.free(lt)
    b.isub(c1, target=T1)
    Cp1e = b.alloc_qubits(n1)
    for i in range(n1):
        b.init_and(ctl, S1[i], Cp1e[i])
    b.isub(Cp1e, target=T1)
    for i in reversed(range(n1)):
        b.del_and(ctl, S1[i], Cp1e[i])
    b.free(Cp1e)
    Cp0b = b.alloc_qubits(n0); ca0 = b.alloc_qubits(1)
    for i in range(n0):
        b.init_and(ctl, S0[i], Cp0b[i])
    for i in range(n0):
        W._narrow_uma_inv(b, Cp0b[i], T0[i], ca0[0])
    b.cx(ca0[0], c1[0])
    for i in reversed(range(n0)):
        W._narrow_maj_inv(b, Cp0b[i], T0[i], ca0[0])
    for i in reversed(range(n0)):
        b.del_and(ctl, S0[i], Cp0b[i])
    b.free(Cp0b); b.free(ca0); b.free(c1)


def build_a1_q(b, x, coef, v, wA, sA) -> None:
    n0, n1 = wA // 2, wA - wA // 2
    for j in range(13):
        b.info_tag(f"STAGE:A1_J{j}_ENTER")
        _qa1_sub_fwd(b, coef[0:wA], v[j + 1 + sA:W_VHI], x[j], n0, n1)
        b.info_tag(f"STAGE:A1_J{j}_EXIT")
    b.info_tag("STAGE:A1_J13_ENTER")
    _qa1_add_fwd(b, coef[0:wA], v[W_D + sA:W_VHI], x[13], n0, n1)
    b.info_tag("STAGE:A1_J13_EXIT")


def build_a1_q_rev(b, x, coef, v, wA, sA) -> None:
    n0, n1 = wA // 2, wA - wA // 2
    b.info_tag("STAGE:A1R_J13_ENTER")
    _qa1_sub_fwd(b, coef[0:wA], v[W_D + sA:W_VHI], x[13], n0, n1)
    b.info_tag("STAGE:A1R_J13_EXIT")
    for j in reversed(range(13)):
        b.info_tag(f"STAGE:A1R_J{j}_ENTER")
        _qa1_add_fwd(b, coef[0:wA], v[j + 1 + sA:W_VHI], x[j], n0, n1)
        b.info_tag(f"STAGE:A1R_J{j}_EXIT")


def build_r1_q(b, coef, v, wR, nR, sR) -> None:
    S = coef[S_OFF:S_OFF + W.W_S]
    for j in range(nR):
        b.info_tag(f"STAGE:R1_J{j}_ENTER")
        W._narrow_r1_row_fwd(b, S, v[j + sR:W_VHI], coef[j])
        b.info_tag(f"STAGE:R1_J{j}_EXIT")


def build_r1_q_rev(b, coef, v, wR, nR, sR) -> None:
    S = coef[S_OFF:S_OFF + W.W_S]
    for j in reversed(range(nR)):
        b.info_tag(f"STAGE:R1R_J{j}_ENTER")
        W._narrow_r1_row_rev(b, S, v[j + sR:W_VHI], coef[j])
        b.info_tag(f"STAGE:R1R_J{j}_EXIT")


def build_forward_q(b, tables, regs, cand) -> None:
    cfg = CANDS[cand]
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    b.info_tag("STAGE:F_S1_ENTER")
    e = b.alloc_qubits(2); h = b.alloc_qubits(1)
    W.build_lz_norm(b, x, lz, e, h)
    b.free(e); b.free(h)
    b.info_tag("STAGE:F_S1_EXIT")
    b.info_tag("STAGE:F_S2_ENTER")
    W.build_normalize(b, x, lz)
    b.info_tag("STAGE:F_S2_EXIT")
    b.info_tag("STAGE:F_D_ENTER")
    b.isub(8192, target=x[0:W.W_DELTA])
    b.info_tag("STAGE:F_D_EXIT")
    b.info_tag("STAGE:F_B_ENTER")
    W.mini_pass(b, x, lz, tables.B, W_B, v[12:W_VHI])
    b.info_tag("STAGE:F_B_EXIT")
    b.info_tag("STAGE:F_A_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, cfg["wA"], coef[0:cfg["wA"]])
    b.info_tag("STAGE:F_A_LOAD_EXIT")
    b.info_tag("STAGE:F_A1_ENTER")
    build_a1_q(b, x, coef, v, cfg["wA"], cfg["sA"])
    b.info_tag("STAGE:F_A1_EXIT")
    b.info_tag("STAGE:F_A_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, cfg["wA"], coef[0:cfg["wA"]])
    b.info_tag("STAGE:F_A_UNLOAD_EXIT")
    b.info_tag("STAGE:F_S3P_ENTER")
    W.build_square2(b, x, coef)
    b.info_tag("STAGE:F_S3P_EXIT")
    b.info_tag("STAGE:F_R_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, cfg["wR"], coef[0:cfg["wR"]])
    b.info_tag("STAGE:F_R_LOAD_EXIT")
    b.info_tag("STAGE:F_R1_ENTER")
    build_r1_q(b, coef, v, cfg["wR"], cfg["nR"], cfg["sR"])
    b.info_tag("STAGE:F_R1_EXIT")
    b.info_tag("STAGE:F_R_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, cfg["wR"], coef[0:cfg["wR"]])
    b.info_tag("STAGE:F_R_UNLOAD_EXIT")
    b.info_tag("STAGE:F_S6_ENTER")
    W.build_shift_round_phase(b, lz, v, coef)
    b.info_tag("STAGE:F_S6_EXIT")


def build_reverse_q(b, tables, regs, cand) -> None:
    cfg = CANDS[cand]
    x, lz, coef, v = (regs[k] for k in ("x", "lz", "coef", "v"))
    b.info_tag("STAGE:R_S6_ENTER")
    W.build_shift_round_phase_rev(b, lz, v, coef)
    b.info_tag("STAGE:R_S6_EXIT")
    b.info_tag("STAGE:R_R_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, cfg["wR"], coef[0:cfg["wR"]])
    b.info_tag("STAGE:R_R_LOAD_EXIT")
    b.info_tag("STAGE:R_R1_ENTER")
    build_r1_q_rev(b, coef, v, cfg["wR"], cfg["nR"], cfg["sR"])
    b.info_tag("STAGE:R_R1_EXIT")
    b.info_tag("STAGE:R_R_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.R, cfg["wR"], coef[0:cfg["wR"]])
    b.info_tag("STAGE:R_R_UNLOAD_EXIT")
    b.info_tag("STAGE:R_S3P_ENTER")
    W.build_square2_rev(b, x, coef)
    b.info_tag("STAGE:R_S3P_EXIT")
    b.info_tag("STAGE:R_A_LOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, cfg["wA"], coef[0:cfg["wA"]])
    b.info_tag("STAGE:R_A_LOAD_EXIT")
    b.info_tag("STAGE:R_A1_ENTER")
    build_a1_q_rev(b, x, coef, v, cfg["wA"], cfg["sA"])
    b.info_tag("STAGE:R_A1_EXIT")
    b.info_tag("STAGE:R_A_UNLOAD_ENTER")
    W.mini_pass(b, x, lz, tables.A, cfg["wA"], coef[0:cfg["wA"]])
    b.info_tag("STAGE:R_A_UNLOAD_EXIT")
    b.info_tag("STAGE:R_B_ENTER")
    W.mini_pass(b, x, lz, tables.B, W_B, v[12:W_VHI])
    b.info_tag("STAGE:R_B_EXIT")
    b.info_tag("STAGE:R_D_ENTER")
    b.iadd(8192, target=x[0:W.W_DELTA])
    b.info_tag("STAGE:R_D_EXIT")
    b.info_tag("STAGE:R_S2_ENTER")
    W.build_normalize_rev(b, x, lz)
    b.info_tag("STAGE:R_S2_EXIT")
    b.info_tag("STAGE:R_S1_ENTER")
    e = b.alloc_qubits(2); h = b.alloc_qubits(1)
    W.build_lz_norm_rev(b, x, lz, e, h)
    b.free(e); b.free(h)
    b.info_tag("STAGE:R_S1_EXIT")


def build_circuit_q(cand):
    tables = load_qtables(cand)
    b = km.CircuitBuilder()
    regs = W.create_regs(b)
    build_forward_q(b, tables, regs, cand)
    build_reverse_q(b, tables, regs, cand)
    circuit = b.finish_circuit()
    assert circuit.num_qubits <= Q_CAP, f"qubits {circuit.num_qubits} > cap {Q_CAP}"
    return circuit


def circuit_sha_q(circuit) -> str:
    return hashlib.sha256(str(circuit).encode()).hexdigest()


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", default="ALL")
    args = ap.parse_args()
    cands = list(CANDS) if args.cand == "ALL" else [args.cand]
    base = W.build_circuit(W.load_tables())
    bs = W.resource_stats(base)
    print(f"BASE Q={bs['qubits']} toff={bs['toffoli_like']} "
          f"Qxtoff={bs['qubits']*bs['toffoli_like']} sha={bs['sha256'][:12]}")
    for c in cands:
        t = load_qtables(c)
        c1 = build_circuit_q(c)
        c2 = build_circuit_q(c)
        eq = str(c1) == str(c2)
        s = W.resource_stats(c1)
        print(f"{c}: eq={eq} Q={s['qubits']} toff={s['toffoli_like']} "
              f"Qxtoff={s['qubits']*s['toffoli_like']} "
              f"dQ={s['qubits']-bs['qubits']} dtoff={s['toffoli_like']-bs['toffoli_like']} "
              f"sha={s['sha256'][:12]}")


if __name__ == "__main__":
    main()
