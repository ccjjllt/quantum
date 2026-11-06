"""Explicit static stage census of the fixed Syed V9 circuit; no simulation."""
from collections import Counter, defaultdict
import gc
import io
import json
from pathlib import Path
import time
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]


class Sink:
    def write(self, data):
        self.data = data.encode() if isinstance(data, str) else data
    def flush(self):
        pass


def main():
    start = time.monotonic()
    c = km.Circuit.from_file(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb', format='kmb')
    native = dict(c.operation_statistics())
    expected = c.operation_statistics().num_toffoli_like
    sink = Sink()
    c.to_file(sink, format='kmx')
    del c
    gc.collect()
    stack = []
    inclusive, exclusive, instances = defaultdict(Counter), defaultdict(Counter), Counter()
    paid = Counter()
    anomalies = []
    for line_no, line in enumerate(io.BytesIO(sink.data), 1):
        if line.startswith(b'INFO_TAG '):
            tag = line.strip().split(b'"', 2)[1].decode()
            if tag.startswith('@enter:'):
                name = tag[7:]
                stack.append(name)
                instances[name] += 1
            elif tag.startswith('@exit:'):
                name = tag[6:]
                if not stack or stack[-1] != name:
                    anomalies.append({'line': line_no, 'exit': name, 'stack': list(stack)})
                else:
                    stack.pop()
        elif line.startswith((b'CCX ', b'CCZ ', b'CSWAP ')):
            op = line.split(b' ', 1)[0].decode()
            paid[op] += 1
            exclusive[stack[-1] if stack else '<outside>'][op] += 1
            for name in stack:
                inclusive[name][op] += 1
    out = {'scope': 'Exact static CCX+CCZ+CSWAP counts; includes classically skipped operations. Inclusive nested totals must not be summed across parent and child.',
           'native_statistics': native, 'native_static_T': expected,
           'counted_paid': dict(paid), 'count_matches_native': sum(paid.values()) == expected,
           'instances': dict(instances),
           'inclusive': {k: dict(v, total=sum(v.values())) for k,v in inclusive.items()},
           'exclusive': {k: dict(v, total=sum(v.values())) for k,v in exclusive.items()},
           'tag_anomalies': anomalies, 'unclosed_tags': stack,
           'elapsed_seconds': time.monotonic()-start}
    target = ROOT/'artifacts/20261106_high_return_research/stage_census.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2), flush=True)


if __name__ == '__main__':
    main()
