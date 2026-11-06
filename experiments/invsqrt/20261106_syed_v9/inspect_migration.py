"""Manual structural comparison of Syed V9 with the Maoxin selector baseline.

Reads actual local circuits; no hashes, simulation or official verification.
"""
import difflib
import io
import json
from pathlib import Path

import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "artifacts/20261106_syed_v9/invsqrt"
BASE = ROOT / "artifacts/20261106_syed_v9/release/invsqrt.kmb"
OLD = ROOT / "artifacts/20261105_maoxin_v2/release/invsqrt.kmb"


def read(path):
    c = km.Circuit.from_file(path, format="kmb")
    out = io.StringIO()
    c.to_file(out, format="kmx")
    lines = out.getvalue().splitlines()
    header = [s for s in lines if s.startswith(("REGISTER", "APPEND"))]
    ops = [s for s in lines if not s.startswith(("REGISTER", "APPEND"))]
    return c, header, ops


def locations(haystack, needle):
    return [i for i, s in enumerate(haystack) if s == needle[0]
            and haystack[i:i+len(needle)] == needle]


def resources(c):
    stats = c.operation_statistics()
    return dict(qubits=c.num_qubits, bits=c.num_bits, ops=len(c),
                static_toffoli_like=stats.num_toffoli_like, counts=dict(stats))


def main():
    old_c, old_header, old = read(OLD)
    new_c, new_header, new = read(BASE)
    ART.mkdir(parents=True, exist_ok=True)
    windows = dict(selector=(27911,28919), first=(27911,28349),
                   second=(28481,28919), prep1=(27779,27911), prep2=(28349,28481))
    exact = {name:dict(old_window=[lo,hi], matches=locations(new,old[lo:hi]))
             for name,(lo,hi) in windows.items()}
    differences = []
    paid = lambda lines:sum(s.startswith(("CCX ","CCZ ","CSWAP ")) for s in lines)
    for tag,a,b,c,d in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
        if tag == "equal":continue
        differences.append(dict(tag=tag,old_window=[a,b],new_window=[c,d],
                                old_paid=paid(old[a:b]),new_paid=paid(new[c:d]),
                                old_instructions=old[a:b],new_instructions=new[c:d]))
    summary=dict(scope="Static exact-instruction comparison only; not equivalence or runtime cost proof",
                 old_path=str(OLD.relative_to(ROOT)),new_path=str(BASE.relative_to(ROOT)),
                 old=resources(old_c),new=resources(new_c),same_header=old_header==new_header,
                 same_rotations=[s for s in old if s.startswith('Z_POW')]==[s for s in new if s.startswith('Z_POW')],
                 selector_windows=exact,difference_groups=len(differences))
    (ART/'structural_comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ART/'maoxin_to_syed_differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':main()
