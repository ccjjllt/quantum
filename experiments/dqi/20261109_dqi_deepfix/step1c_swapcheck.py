"""Pin down 1030-vs-2399 cause: step1 semantics with conservative SWAP + a==b skip."""
from __future__ import annotations
import collections

KMX = "/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/affine_cache_frontier.kmx"

def qid(t): return int(t[1:])

stage = "header"; stack = []; depth = 0
mask = {}; const = {}; dirty = set()
for q in range(892):
    mask[q] = 1 << q; const[q] = 0
n_ccx = n_both = n_aeqb = n_swap = 0
in_unextract = False
with open(KMX) as f:
    for raw in f:
        l = raw.strip()
        if not l:
            continue
        if l.startswith("INFO_TAG"):
            tag = l.split('"', 2)[1]
            if tag.startswith("@enter:"):
                stack.append(tag[7:]); stage = stack[0]
                if stage == "unextract" and len(stack) == 1:
                    mask = {q: 1 << q for q in range(892)}
                    const = {q: 0 for q in range(892)}
                    dirty = set()
            elif tag.startswith("@exit:") and stack:
                stack.pop(); stage = stack[0] if stack else "header"
            continue
        if l.startswith(("APPEND", "REGISTER", "SEMANTIC", "ANNOTATION")):
            continue
        if l.startswith("PUSH_CONDITION"):
            depth += 1; continue
        if l.startswith("POP_CONDITION"):
            depth -= 1; continue
        if stage != "unextract":
            continue
        parts = l.split(); op = parts[0]
        if len(parts) >= 3 and parts[-2] == "if":
            inline = parts[-1]; args = parts[1:-2]
        else:
            inline = None; args = parts[1:]
        cond = (depth > 0) or (inline is not None)
        if op == "X":
            q = qid(args[0])
            if cond:
                dirty.add(q); mask.pop(q, None)
            elif q not in dirty:
                const[q] ^= 1
        elif op == "CX":
            a, b = qid(args[0]), qid(args[1])
            if cond or a in dirty or b in dirty:
                dirty.add(b); mask.pop(b, None)
            else:
                mask[b] ^= mask[a]; const[b] ^= const[a]
        elif op == "SWAP":
            n_swap += 1
            a, b = qid(args[0]), qid(args[1])
            if cond:
                dirty.add(a); dirty.add(b); mask.pop(a, None); mask.pop(b, None)
            else:
                # CONSERVATIVE (affine_clean.py): dirty both if either dirty
                if a in dirty or b in dirty:
                    dirty.add(a); dirty.add(b); mask.pop(a, None); mask.pop(b, None)
                else:
                    mask[a], mask[b] = mask[b], mask[a]
                    const[a], const[b] = const[b], const[a]
        elif op in ("HMR", "R"):
            q = qid(args[0])
            if not cond:
                mask[q] = 0; const[q] = 0; dirty.discard(q)
            else:
                dirty.add(q); mask.pop(q, None)
        elif op == "CCX":
            a, b, t = qid(args[0]), qid(args[1]), qid(args[2])
            if cond:
                dirty.add(t); mask.pop(t, None); continue
            if a == b:
                n_aeqb += 1
                continue  # affine_clean skips site recording for a==b
            n_ccx += 1
            if a not in dirty and b not in dirty:
                n_both += 1
            dirty.add(t); mask.pop(t, None)
        elif op == "CSWAP":
            try:
                dirty.add(qid(args[1])); dirty.add(qid(args[2]))
                mask.pop(qid(args[1]), None); mask.pop(qid(args[2]), None)
            except Exception:
                pass
print(f"unextract uncond CCX={n_ccx} bothclean={n_both} a==b skipped={n_aeqb} swaps={n_swap}")
