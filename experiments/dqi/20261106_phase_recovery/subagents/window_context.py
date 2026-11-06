"""Dump textual context around the first occurrence of an INFO_TAG window.

Streams the KMB through kickmix (kmb -> kmx text), keeps a ring buffer, and
prints the N gates before an @enter tag and the first M gates inside it, plus
the enclosing tag stack.  Read-only.

Usage:
    python window_context.py <kmb> <tag> [--before 60] [--inside 30]
"""
import argparse
import io
from pathlib import Path

import kickmix as km


class Sink:
    def write(self, value):
        self.data = value.encode() if isinstance(value, str) else value

    def flush(self):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kmb')
    ap.add_argument('tag')
    ap.add_argument('--before', type=int, default=60)
    ap.add_argument('--inside', type=int, default=30)
    a = ap.parse_args()
    c = km.Circuit.from_file(a.kmb, format='kmb')
    sink = Sink()
    c.to_file(sink, format='kmx')
    ring = []
    stack = []
    inside = 0
    found = False
    for raw in io.BytesIO(sink.data):
        line = raw.decode().rstrip()
        if line.startswith('INFO_TAG "@enter:'):
            name = line.split('"')[1][7:]
            if name == a.tag and not found:
                print('=== tag stack before enter:', stack)
                print('=== last %d gates before enter:' % a.before)
                for x in ring[-a.before:]:
                    print(x)
                print('=== inside window ===')
                found = True
                inside = 1
                continue
            stack.append(name)
            continue
        if line.startswith('INFO_TAG "@exit:'):
            name = line.split('"')[1][6:]
            if stack and stack[-1] == name:
                stack.pop()
            else:
                print('!! tag mismatch', name, stack[-3:])
            continue
        if line.startswith('INFO_TAG'):
            ring.append(line)
            continue
        if found:
            print(line)
            inside += 1
            if inside > a.inside:
                break
        ring.append(line)
    if not found:
        print('tag not found')


if __name__ == '__main__':
    main()
