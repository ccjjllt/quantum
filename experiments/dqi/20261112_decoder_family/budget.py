"""Verdict arithmetic for 20261112_decoder_family (reads the JSON artifacts).

All inputs are measured in this experiment:
  v21_stage_mulcensus.json  exact per-stage kernel-call counts (instrumented build)
  hgcd_count.json           classical GF(2^12) multiplication counts, EEA vs half-gcd
  proto_hgcd.json           kickmix T/Q of the reversible sub-blocks
  eae_blocks.json           rank-one motif census of eae396ba per stage

Usage: .venv/bin/python budget.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = Path(__file__).resolve().parent / 'results'

R = 1.19126046
Q = 892
T_STATIC = 401_313
T_MEAN = 394_089.2726757813
COST = R * Q * Q * T_MEAN

STAGES = {  # eae396ba measured static T and motif-counted multiplication CCX
    'extract': (58_742, 42_482),
    'synthesis': (31_635, 30_984),
    'convert': (60_663, 50_239),
    'scan': (44_275, 0),
    'unconvert': (62_534, 52_754),
    'unsynthesis': (40_429, 38_687),
    'unextract': (103_035, 73_717),
}


def main():
    v21 = json.loads((ART / 'v21_stage_mulcensus.json').read_text())
    hg = {r['n']: r for r in json.loads((ART / 'hgcd_count.json').read_text())}
    proto = {r['name']: r for r in json.loads((ART / 'proto_hgcd.json').read_text())['blocks']}
    eae = json.loads((ART / 'eae_blocks.json').read_text())

    print(f"eae396ba: Q={Q} static={T_STATIC:,} mean={T_MEAN:.2f} cost={COST:.4e}")
    for target in (340_000, 347_094):
        tm = target * T_MEAN / T_STATIC
        c = R * Q * Q * tm
        print(f"  static {target:,} -> mean {tm:,.0f} -> cost {c:.4e} ({(c/COST-1)*100:+.2f}%)")

    print("\nper-stage multiplication share (motif CCX = T of rank-one terms):")
    tot = mult = 0
    for s, (t, m) in STAGES.items():
        print(f"  {s:12s} T={t:7,d} mult={m:7,d} ({100*m/t:5.1f}%)")
        tot += t
        mult += m
    print(f"  {'TOTAL':12s} T={tot:7,d} mult={mult:7,d} ({100*mult/tot:5.1f}%)")

    print("\nv21 exact kernel census (instrumented build, SHA 6349d2bc...):")
    for s in ('convert', 'unconvert'):
        m42 = v21.get(f'{s}/mul_xor0_12', 0) + v21.get(f'{s}/mul_xor_12', 0)
        m6 = v21.get(f'{s}/noscratch_6', 0)
        print(f"  {s:10s} mul42={m42:5d} mul6={m6:4d} multT={42*m42+15*m6:6,d}")

    print("\nclassical field-multiplication counts (deg-17 EEA, two cofactors):")
    for n in (16, 17, 32, 34):
        r = hg[n]
        print(f"  n={n:3d} euclid={r['euclid_mul']:8.1f} ext={r['ext_school_mul']:8.1f} "
              f"hgcd={r['hgcd_school_mul']:8.1f} hgcd_karat={r['hgcd_karat_mul']:8.1f} "
              f"inv={r['ext_school_inv']:.0f}")

    print("\nmeasured reversible sub-blocks (kickmix, real mul_xor0=42T):")
    for k in ('pmul_school_d8', 'karatsuba_d8', 'karatsuba_d16',
              'matvec_school_d8', 'matmat_school_d8'):
        r = proto[k]
        print(f"  {k:20s} Q={r['Q']:5d} T={r['T']:7,d} field-mults={r['T']/42:6.0f}")

    need = 401_313 - 340_000
    eea = 920 * 42
    print(f"\nrequired cut {need:,} T; convert+unconvert must become {123_197-need:,} T")
    print(f"extended-Euclid arithmetic floor (both directions) = 2*920*42 = {2*eea:,} T")
    print(f"half-gcd at n=17: {hg[17]['hgcd_school_mul']:.0f} vs ext {hg[17]['ext_school_mul']:.0f} "
          f"-> {hg[17]['hgcd_school_mul']/hg[17]['ext_school_mul']:.2f}x")
    # EEA core of eae convert: 1,148 total 42-mults - 68 setup/reduce - 141 Hankel
    eea_lo, eea_hi = 939, 955
    hg = int(hg[17]['hgcd_school_mul'])          # 1027
    flat = 920                                    # classical extended Euclid
    print(f"EEA core {eea_lo}..{eea_hi}; half-gcd {hg}: static "
          f"{401_313 + 2*(hg-eea_hi)*42:,}..{401_313 + 2*(hg-eea_lo)*42:,} "
          f"(Delta vs eae +{2*(hg-eea_hi)*42/401313*100:.2f}%..+{2*(hg-eea_lo)*42/401313*100:.2f}%)")
    print(f"perfect extended EEA {flat}: static "
          f"{401_313 - 2*(eea_hi-flat)*42:,}..{401_313 - 2*(eea_lo-flat)*42:,} "
          f"(Delta vs eae {2*(flat-eea_hi)*42/401313*100:.2f}%..{2*(flat-eea_lo)*42/401313*100:.2f}%)")
    print(f"target 340,000 still short by "
          f"{401_313 - 2*(eea_hi-flat)*42 - 340_000:,}..{401_313 - 2*(eea_lo-flat)*42 - 340_000:,}")


if __name__ == '__main__':
    main()
