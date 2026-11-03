"""Manually compose the two disjoint proved 62Q baseline patches."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'artifacts/20261103_one_ccx/invsqrt'
BASE = ROOT / 'artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb'
PINNED = [
    (BASE, 'bce2948ff24e20fe59666d131f7fc4316a905103937272c52fdd39d494b6fe47'),
    (ART/'phase_last_selector.kmb', 'e30937769d6245c405e9933336e57e8d1701aeb0d67e42dc0133f490a4fbbabe'),
    (ART/'tail_cache_three_and.kmb', 'c2c255036961fcddbbabca84c231d4101ae928cbf34ae9a3da75926b7b665a0f'),
]

def read(path, sha):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
    c = km.Circuit.from_file(path)
    b = io.StringIO(); c.to_file(b, format='kmx')
    lines = b.getvalue().splitlines()
    return ([x for x in lines if x.startswith(('APPEND', 'REGISTER'))],
            [x for x in lines if not x.startswith(('APPEND', 'REGISTER'))])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--joint', action='store_true')
    args = ap.parse_args()
    pinned = list(PINNED)
    if args.joint:
        pinned[1] = (ART/'phase_joint_selector.kmb', '7e2e2843bae6bc0b44063a9d2c4bedee63b4aca8031d78ce626606b91824057e')
    header, original = read(*pinned[0])
    patches = []
    for path, sha in pinned[1:]:
        hdr, ops = read(path, sha)
        assert hdr == header
        lo = 0
        while lo < min(len(original), len(ops)) and original[lo] == ops[lo]:
            lo += 1
        suffix = 0
        while suffix < min(len(original), len(ops))-lo and original[-1-suffix] == ops[-1-suffix]:
            suffix += 1
        hi = len(original)-suffix
        replacement = ops[lo:len(ops)-suffix]
        patches.append((lo, hi, replacement))
    patches.sort()
    assert patches[0][1] <= patches[1][0]
    # Neither patch exports a changed old classical bit read by the suffix;
    # this is checked separately in each candidate's independent audit.
    used_new = []
    old_bits = {t for line in original for t in line.split() if t.startswith('b') and t[1:].isdigit()}
    for lo, hi, repl in patches:
        used_new.append({t for line in repl for t in line.split() if t.startswith('b') and t[1:].isdigit()}-old_bits)
    assert used_new[0].isdisjoint(used_new[1])
    combined = list(original)
    for lo, hi, repl in reversed(patches):
        combined[lo:hi] = repl
    assert [s for s in combined if s.startswith('Z_POW')] == [s for s in original if s.startswith('Z_POW')]
    c = km.Circuit.from_file(io.StringIO('\n'.join(header+combined)+'\n'), format='kmx')
    assert c.num_qubits == 62
    name = 'joint_tail_combined' if args.joint else 'phase_tail_combined'
    dest = ART/f'{name}.kmb'; c.to_file(dest, format='kmb')
    result = {
        'baseline_sha256': pinned[0][1],
        'sources': [{'file': str(p), 'sha256': s} for p,s in pinned[1:]],
        'disjoint_baseline_windows': [[lo, hi] for lo,hi,_ in patches],
        'qubits': c.num_qubits, 'operations': len(combined),
        'candidate_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
        'validation': 'Composition only; see separate proof, sample and official records.',
    }
    if args.joint:
        # Independent GF(2) audit establishes that fallback implies both
        # original selector masks are nonzero, so new mean cost is exactly 1.125.
        result['expected_equivalent_saving'] = .1875 + 2 - 2**-18 - 1.125
    else:
        result['expected_equivalent_saving'] = .1875 + .25 - 2**-19
    (ART/f'{name}.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
