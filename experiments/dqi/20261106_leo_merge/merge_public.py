"""Merge two near-identical kmx circuits, taking one side per hunk.
Purpose: combine independently-discovered edits from competing public DQI files.

Hunks are found by a streaming lookahead diff; the caller supplies a line
threshold: hunks whose A-line is <= limit use the A side, the rest the B side.

Usage: merge_public.py A.kmx B.kmx OUT.kmx ALIMIT [W]
Writes OUT and OUT.hunks.json (the hunk list, for audit).
"""
import json
import sys

A_PATH, B_PATH, OUT_PATH = sys.argv[1], sys.argv[2], sys.argv[3]
ALIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
W = int(sys.argv[5]) if len(sys.argv) > 5 else 64


def main():
    A = open(A_PATH, 'rb')
    B = open(B_PATH, 'rb')
    ha, hb = [], []

    def fill(f, buf):
        while len(buf) < W:
            line = f.readline()
            if not line:
                break
            buf.append(line)

    fill(A, ha)
    fill(B, hb)
    ia = ib = 0
    hunks, cur = [], None
    while ha and hb:
        if ha[0] == hb[0]:
            if cur is not None:
                hunks.append(cur)
                cur = None
            ha.pop(0)
            hb.pop(0)
            ia += 1
            ib += 1
            fill(A, ha)
            fill(B, hb)
            continue
        ja = jb = None
        for k in range(1, W + 1):
            if k < len(ha) and ha[k] == hb[0]:
                ja, jb = k, 0
                break
            if k < len(hb) and hb[k] == ha[0]:
                ja, jb = 0, k
                break
        if cur is None:
            cur = {'a0': ia, 'b0': ib, 'a': [], 'b': []}
        if ja is None:
            cur['a'].append(ha.pop(0))
            ia += 1
            cur['b'].append(hb.pop(0))
            ib += 1
        else:
            for _ in range(ja):
                if not ha:
                    break
                cur['a'].append(ha.pop(0))
                ia += 1
            for _ in range(jb):
                if not hb:
                    break
                cur['b'].append(hb.pop(0))
                ib += 1
        fill(A, ha)
        fill(B, hb)
    if cur is not None:
        hunks.append(cur)

    out = open(OUT_PATH, 'wb')
    A.seek(0)
    B.seek(0)
    a_line = b_line = 0
    for hk in sorted(hunks, key=lambda x: x['a0']):
        while a_line < hk['a0']:
            out.write(A.readline())
            a_line += 1
        while b_line < hk['b0']:
            B.readline()
            b_line += 1
        use_a = hk['a0'] <= ALIMIT
        for line in (hk['a'] if use_a else hk['b']):
            out.write(line)
        for _ in hk['a']:
            A.readline()
            a_line += 1
        for _ in hk['b']:
            B.readline()
            b_line += 1
    while True:
        la = A.readline()
        lb = B.readline()
        if not la and not lb:
            break
        out.write(la if la else b'')
    out.close()
    json.dump(
        [{'a0': h['a0'], 'b0': h['b0'],
          'a': [x.decode().rstrip() for x in h['a']],
          'b': [x.decode().rstrip() for x in h['b']]} for h in hunks],
        open(OUT_PATH + '.hunks.json', 'w'), indent=1)
    print(f'hunks={len(hunks)} limit={ALIMIT} out={OUT_PATH}')


if __name__ == '__main__':
    main()
