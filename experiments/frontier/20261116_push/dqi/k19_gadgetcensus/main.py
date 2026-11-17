"""Gadget doc + census on the NEW 66b4 tape (Kaggle CPU, no internet).
Dataset: balramsrinivasan/vqcc-28-10-norm-preserving-dqi-closings
Competition mount: google-verifiable-quantum-circuit-compilation (kickmix.so)
"""
import hashlib, pathlib, re, struct, sys, time, os
t0=time.time()
def log(*a):
    print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
import numpy as np
ROOT=pathlib.Path("/kaggle/input")
WORK=pathlib.Path("/kaggle/working"); WORK.mkdir(exist_ok=True)
REPORT=[]
def say(*a):
    s=" ".join(str(x) for x in a); REPORT.append(s); print(s, flush=True)

# locate inputs
def find_one(pat, substr=None):
    cands=sorted(ROOT.rglob(pat))
    if substr:
        cands=[p for p in cands if substr in str(p)]
    return cands
log("input roots", [str(p) for p in ROOT.iterdir()])
m_pre=(find_one("m_pre.kmx")[0] if find_one("m_pre.kmx") else None)
m_orig=(find_one("m_orig.kmx")[0] if find_one("m_orig.kmx") else None)
m_patch=(find_one("m_patch.kmx")[0] if find_one("m_patch.kmx") else None)
log("micros", m_pre, m_orig, m_patch)
tools=list(sorted(ROOT.rglob("closing_norm_preserving_body.py")))
log("tools", tools[:3])
dqi_cands=find_one("dqi.kmb")
log("dqi.kmb cands", [(str(p), p.stat().st_size) for p in dqi_cands])
# pick the 480MB one from balramsrinivasan (not sample)
TGT=None
for p in dqi_cands:
    s=str(p)
    if "balramsrinivasan" in s:
        TGT=p; break
if TGT is None:
    # fallback largest
    TGT=max(dqi_cands, key=lambda p: p.stat().st_size)
log("TGT", TGT, TGT.stat().st_size)
ENGINE=sorted(ROOT.rglob("kickmix.so"))[0].parent
log("engine", ENGINE)
sys.path.insert(0, str(ENGINE))
import kickmix as km

# ---- Phase A: micro doc ----
def stats_of(kmx_path):
    c=km.Circuit.from_file(str(kmx_path), format="kmx")
    st=dict(c.operation_statistics())
    nT=int(st.get("CCX",0))+int(st.get("CCZ",0))+int(st.get("CSWAP",0))
    # num_toffoli_like via operation_statistics? use sum above; also try attribute
    try:
        nT2=int(c.operation_statistics().num_toffoli_like)
    except Exception:
        nT2=nT
    return c, st, nT, nT2

for tag,p in (("pre",m_pre),("orig",m_orig),("patch",m_patch)):
    c,st,nT,nT2=stats_of(p)
    say(f"MICRO {tag} file={p} bytes={p.stat().st_size} Q={c.num_qubits} T(CCX+CCZ+CSWAP)={nT} stats={st}")
    # opcode name sequence length via kmx text
    txt=open(p).read().splitlines()
    body=[l for l in txt if l.strip() and not l.startswith("INFO_TAG")]
    from collections import Counter
    ops=[l.split()[0] for l in body]
    say(f"  kmx lines={len(body)} opcodes={dict(Counter(ops))}")

# numeric patterns via kmb round-trip of micros (exact, small)
MAGIC=bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
def unpack(raw):
    assert raw[:16]==MAGIC
    h=list(struct.unpack_from("<4I9Q", raw, 16))
    pos,regs,secs=104,[],{}
    while pos<len(raw):
        idx,size=struct.unpack_from("<QQ", raw, pos)
        pay=raw[pos+16:pos+16+size]
        if idx==0: regs.append(pay)
        else: secs[idx]=np.frombuffer(pay,dtype=np.uint8 if idx==1 else np.uint32).copy() if idx<=9 else pay
        pos+=16+size
    return h,regs,secs
def ops_of_circuit(c):
    tmp=pathlib.Path("/tmp/micro.kmb")
    c.to_file(str(tmp), format="kmb")
    H,R,S=unpack(tmp.read_bytes())
    return H,R,S
Hpre,Rpre,Spre=ops_of_circuit(km.Circuit.from_file(str(m_pre),format="kmx"))
Horig,Rorig,Sorig=ops_of_circuit(km.Circuit.from_file(str(m_orig),format="kmx"))
Hpatch,Rpatch,Spatch=ops_of_circuit(km.Circuit.from_file(str(m_patch),format="kmx"))
opre,sorig,spatch=Spre[1],Sorig[1],Spatch[1]
say(f"NUMERIC pre_len={len(opre)} orig_len={len(sorig)} patch_len={len(spatch)}")
say(f"pre header Q H={Hpre[1]} nops={Hpre[4]} staticT={Hpre[5]}")
say(f"orig header Q H={Horig[1]} nops={Horig[4]} staticT={Horig[5]}")
say(f"patch header Q H={Hpatch[1]} nops={Hpatch[4]} staticT={Hpatch[5]}")
# prefix check (numeric incl cond)
npre=len(opre)
is_pre_orig=np.array_equal(sorig[:npre],opre)
is_pre_patch=np.array_equal(spatch[:npre],opre)
say(f"prefix orig[:pre]==pre? {is_pre_orig} patch[:pre]==pre? {is_pre_patch}")
G0=sorig[npre:].tobytes() if hasattr(sorig[npre:],"tobytes") else bytes(sorig[npre:])
G1=spatch[npre:].tobytes() if hasattr(spatch[npre:],"tobytes") else bytes(spatch[npre:])
# keep as numpy arrays too
G0a=sorig[npre:].copy(); G1a=spatch[npre:].copy()
say(f"G0 suffix ops={len(G0a)} G1 suffix ops={len(G1a)}")
# T per site from header static diffs
T_pre=int(Hpre[5]); T_orig=int(Horig[5]); T_patch=int(Hpatch[5])
say(f"T_pre={T_pre} T_orig_full={T_orig} T_patch_full={T_patch} T_G0={T_orig-T_pre} T_G1={T_patch-T_pre} SAVE_per_site={T_orig-T_patch}")
# qubit sets: patch_q <= orig_q check via kmx text (like transplant)
TOK=re.compile(r'^([qb])(\d+)$')
def body_lines(path):
    return [l.split() for l in open(path) if l.strip() and not l.startswith('INFO_TAG')]
pre_lines=body_lines(str(m_pre)); orig_lines=body_lines(str(m_orig)); patch_lines=body_lines(str(m_patch))
i=0
while i<len(pre_lines) and pre_lines[i]==orig_lines[i]: i+=1
say(f"kmx prefix orig match len {i} / pre {len(pre_lines)} extends? {i==len(pre_lines)}")
j=0
while j<len(pre_lines) and pre_lines[j]==patch_lines[j]: j+=1
say(f"kmx prefix patch match len {j} / pre {len(pre_lines)} extends? {j==len(pre_lines)}")
G0t=orig_lines[len(pre_lines):]; G1t=patch_lines[len(pre_lines):]
pre_bits={t for l in pre_lines for t in l if TOK.match(t) and t[0]=='b'}
orig_q={t for l in G0t for t in l if TOK.match(t) and t[0]=='q'}
patch_q={t for l in G1t for t in l if TOK.match(t) and t[0]=='q'}
say(f"pre_bits={len(pre_bits)} orig_q={len(orig_q)} patch_q={len(patch_q)} patch<=orig? {patch_q<=orig_q} extra={sorted(patch_q-orig_q)[:10]}")
orig_b={t for l in G0t for t in l if TOK.match(t) and t[0]=='b'}
patch_b={t for l in G1t for t in l if TOK.match(t) and t[0]=='b'}
say(f"orig_b={len(orig_b)} patch_b={len(patch_b)} new_bits_in_patch_not_in_pre_or_orig={len([b for b in patch_b if b not in pre_bits and b not in orig_b])}")
# tools key lines
for tp in tools[:1]:
    txt=open(tp).read().splitlines()
    say(f"TOOL {tp} lines={len(txt)}")
    # log guarded branch + T comments
    for ln in txt[:12]:
        say("  SRC| "+ln)

# ---- Phase B: target header + opcode census + pattern search ----
log("unpacking target (480MB)...")
raw=TGT.read_bytes()
H,R,S=unpack(raw)
ops=S[1]; n=len(ops); base=ops&127; cond=(ops&128)!=0
is3=np.isin(base,[0x30,0x31,0x32])
say(f"TGT header H={H[:13]} Q={H[1]} nops_hdr={H[4]} staticT_hdr={H[5]}")
say(f"TGT measured n={n} staticT={int(is3.sum())} Qmax_check pending")
# A/B/C/BIT/COND arrays (k15 layout)
A=np.full(n,-1,dtype=np.int32); B=np.full(n,-1,dtype=np.int32); C=np.full(n,-1,dtype=np.int32)
BIT=np.full(n,-1,dtype=np.int32); COND=np.full(n,-1,dtype=np.int32)
is3m=is3
is2=np.isin(base,[0x20,0x21,0x22]); is1=np.isin(base,[0x10,0x11,0x12,0x50]); isb=np.isin(base,[0x40,0x41,0x42,0x50])
pref3=np.cumsum(is3m); pref2=np.cumsum(is2); pref1=np.cumsum(is1); prefb=np.cumsum(isb); prefc=np.cumsum(cond)
i3a=np.flatnonzero(is3m); i2a=np.flatnonzero(is2); i1a=np.flatnonzero(is1)
# sizes: S[2..4] len == is3 count, S[5..6] == is2, S[7]==is1, S[8]==isb, S[9]==cond
say(f"counts is3={int(is3m.sum())} is2={int(is2.sum())} is1={int(is1.sum())} isb={int(isb.sum())} cond={int(cond.sum())}")
say(f"secs lens 2={len(S[2])} 3={len(S[3])} 4={len(S[4])} 5={len(S[5])} 6={len(S[6])} 7={len(S[7])} 8={len(S[8])} 9={len(S[9])}")
A[i3a]=S[2][pref3[i3a]-1]; B[i3a]=S[3][pref3[i3a]-1]; C[i3a]=S[4][pref3[i3a]-1]
A[i2a]=S[5][pref2[i2a]-1]; C[i2a]=S[6][pref2[i2a]-1]
A[i1a]=S[7][pref1[i1a]-1]
BIT[isb]=S[8][prefb[isb]-1]
COND[cond]=S[9][prefc[cond]-1]
Q=int(max(A.max(),B.max(),C.max()))+1
say(f"TGT Q={Q} nbits={int(max(BIT.max(),COND.max()))+1}")
vals,cnts=np.unique(base,return_counts=True)
say("TGT opcodes "+str({hex(int(v)):int(c) for v,c in zip(vals,cnts)}))
# pattern search on opcode bytes (incl cond bit, exact)
seqB=ops.tobytes()
say(f"seq bytes {len(seqB)} G0 {len(G0)} G1 {len(G1)}")
def find_all(seq, pat):
    sites=[]; k=seq.find(pat)
    while k>=0:
        sites.append(k); k=seq.find(pat, k+len(pat))
    return sites
sites_G0=find_all(seqB, G0)
sites_G1=find_all(seqB, G1)
say(f"OPCODE-LEVEL sites G0(orig suffix)={len(sites_G0)} first5={sites_G0[:5]}")
say(f"OPCODE-LEVEL sites G1(patch suffix)={len(sites_G1)} first5={sites_G1[:5]}")
# overlapping check for G1 (in case adjacent)? also count overlapping via stride 1 for sanity on first 5M? skip (expensive). Non-overlap is transplant semantics.
# operand-verified census for G0 hits and G1 hits
# Build micro operand arrays for G0/G1 spans to verify mapping.
# For micros, unpack already gives Sorig etc; need A/B/C/BIT/COND for micro orig/patch.
def build_aux(Hm,Sm):
    nm=len(Sm[1]); bm=Sm[1]&127; cm=(Sm[1]&128)!=0
    Am=np.full(nm,-1,dtype=np.int32); Bm=np.full(nm,-1,dtype=np.int32); Cm=np.full(nm,-1,dtype=np.int32)
    BITm=np.full(nm,-1,dtype=np.int32); CONDm=np.full(nm,-1,dtype=np.int32)
    m3=np.isin(bm,[0x30,0x31,0x32]); m2=np.isin(bm,[0x20,0x21,0x22]); m1=np.isin(bm,[0x10,0x11,0x12,0x50]); mb=np.isin(bm,[0x40,0x41,0x42,0x50])
    p3=np.cumsum(m3); p2=np.cumsum(m2); p1=np.cumsum(m1); pb=np.cumsum(mb); pc=np.cumsum(cm)
    Am[np.flatnonzero(m3)]=Sm[2][p3[np.flatnonzero(m3)]-1]; Bm[np.flatnonzero(m3)]=Sm[3][p3[np.flatnonzero(m3)]-1]; Cm[np.flatnonzero(m3)]=Sm[4][p3[np.flatnonzero(m3)]-1]
    Am[np.flatnonzero(m2)]=Sm[5][p2[np.flatnonzero(m2)]-1]; Cm[np.flatnonzero(m2)]=Sm[6][p2[np.flatnonzero(m2)]-1]
    Am[np.flatnonzero(m1)]=Sm[7][p1[np.flatnonzero(m1)]-1]
    BITm[mb]=Sm[8][pb[mb]-1]
    CONDm[cm]=Sm[9][pc[cm]-1]
    return bm,cm,Am,Bm,Cm,BITm,CONDm
bm_o,cm_o,Am_o,Bm_o,Cm_o,BITm_o,CONDm_o=build_aux(Horig,Sorig)
bm_p,cm_p,Am_p,Bm_p,Cm_p,BITm_p,CONDm_p=build_aux(Hpatch,Spatch)
def operands_at(idx, b_,c_,A_,B_,C_,BIT_,COND_):
    o=int(b_[idx]); qs=[]
    if o in (0x30,0x31,0x32): qs=[int(A_[idx]),int(B_[idx]),int(C_[idx])]
    elif o in (0x20,0x21,0x22): qs=[int(A_[idx]),int(C_[idx])]
    elif o in (0x10,0x11,0x12,0x50): qs=[int(A_[idx])]
    else: qs=[]
    bit=int(BIT_[idx]) if o in (0x40,0x41,0x42,0x50) else -1
    # BIT for HMR is its measured bit; for pure-bit ops same
    condb=int(COND_[idx]) if c_[idx] else -1
    return o, bool(c_[idx]), tuple(qs), bit, condb
# precompute micro G0/G1 operand lists (relative indices)
G0_list=[operands_at(npre+i, bm_o,cm_o,Am_o,Bm_o,Cm_o,BITm_o,CONDm_o) for i in range(len(G0a))]
G1_list=[operands_at(npre+i, bm_p,cm_p,Am_p,Bm_p,Cm_p,BITm_p,CONDm_p) for i in range(len(G1a))]
say(f"G0_list len {len(G0_list)} ex0 {G0_list[0]} ex1 {G0_list[1] if len(G0_list)>1 else None}")
say(f"G1_list len {len(G1_list)} ex0 {G1_list[0]} ex1 {G1_list[1] if len(G1_list)>1 else None}")
def verify_site(start, Glist):
    Qmap={}; Qrev={}; Bmap={}; Brev={}
    for j,(mo,mc,mqs,mb,mcond) in enumerate(Glist):
        k=start+j
        o=int(base[k]); c_=bool(cond[k])
        if o!=mo or c_!=mc:
            return False, f"opcode mismatch at +{j}"
        if o in (0x30,0x31,0x32): tqs=(int(A[k]),int(B[k]),int(C[k]))
        elif o in (0x20,0x21,0x22): tqs=(int(A[k]),int(C[k]))
        elif o in (0x10,0x11,0x12,0x50): tqs=(int(A[k]),)
        else: tqs=()
        tbit=int(BIT[k]) if o in (0x40,0x41,0x42,0x50) else -1
        tcond=int(COND[k]) if c_ else -1
        if len(tqs)!=len(mqs): return False, "arity"
        for mq,tq in zip(mqs,tqs):
            if Qmap.setdefault(mq,tq)!=tq or Qrev.setdefault(tq,mq)!=mq: return False, f"qmap +{j}"
        if mb!=-1:
            if Bmap.setdefault(mb,tbit)!=tbit or Brev.setdefault(tbit,mb)!=mb: return False, f"bmap +{j}"
        if mcond!=-1:
            if Bmap.setdefault(mcond,tcond)!=tcond or Brev.setdefault(tcond,mcond)!=mcond: return False, f"cmap +{j}"
    return True, (len(Qmap),len(Bmap))
# verify all G0 opcode hits (remaining orig)
ok0=0; fail0=[]
for s in sites_G0:
    ok,info=verify_site(s, G0_list)
    if ok: ok0+=1
    else: fail0.append((s,info))
say(f"VERIFIED G0(orig) sites {ok0}/{len(sites_G0)} fail={len(fail0)} ex={fail0[:3]}")
ok1=0; fail1=[]
for s in sites_G1:
    ok,info=verify_site(s, G1_list)
    if ok: ok1+=1
    else: fail1.append((s,info))
say(f"VERIFIED G1(patch) sites {ok1}/{len(sites_G1)} fail={len(fail1)} ex={fail1[:3]}")
# live-set/Q impact: patch_q<=orig_q already; fresh bits count for converting one more (if any ok0>0)
# per-site static T saving already computed; total remaining opportunity = ok0*save
say(f"SAVE_per_site_static={T_orig-T_patch} remaining_opportunity_static={ok0*(T_orig-T_patch)}")
say(f"Q impact per conversion: 0 (patch_q<=orig_q={patch_q<=orig_q}); bits: fresh classical only")
(WORK/"report.txt").write_text("\n".join(REPORT))
say("DONE")
