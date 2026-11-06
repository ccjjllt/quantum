"""Count every operation class per top-level DQI stage, exclusive of nested tags."""
from collections import Counter, defaultdict
import gc
import io
import json
from pathlib import Path
import sys
import time
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
OPS = (b'CCX ', b'CCZ ', b'CSWAP ', b'CX ', b'CZ ', b'X ', b'Z ', b'R ',
       b'NEG', b'HMR ', b'SWAP ', b'PUSH_CONDITION', b'POP_CONDITION')


class Sink:
    def write(self, data):
        self.data = data.encode() if isinstance(data, str) else data
    def flush(self):
        pass


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb'
    out_name = Path(sys.argv[2]).name if len(sys.argv) > 2 else 'phase_census.json'
    start = time.monotonic()
    c = km.Circuit.from_file(src, format='kmb')
    sink = Sink()
    c.to_file(sink, format='kmx')
    del c
    gc.collect()
    stack = []
    exclusive = defaultdict(Counter)
    unclosed = []
    for line in io.BytesIO(sink.data):
        if line.startswith(b'INFO_TAG '):
            tag = line.strip().split(b'"', 2)[1].decode()
            if tag.startswith('@enter:'):
                stack.append(tag[7:])
            elif tag.startswith('@exit:'):
                if stack and stack[-1] == tag[6:]:
                    stack.pop()
                else:
                    unclosed.append([line[:80].decode(), list(stack)])
        else:
            for prefix in OPS:
                if line.startswith(prefix):
                    exclusive[stack[0] if stack else '<outside>'][prefix.decode().strip()] += 1
                    break
    out = {
        'scope': 'Exclusive counts at the outermost INFO_TAG level; operations inside nested tags count for their top-level stage.',
        'exclusive': {k: dict(v) for k, v in exclusive.items()},
        'unclosed_at_eof': stack,
        'tag_anomalies': unclosed,
        'elapsed_seconds': time.monotonic() - start,
    }
    target = ROOT/f'artifacts/20261106_phase_recovery/{out_name}'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
