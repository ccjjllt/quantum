"""Extract first named arithmetic windows and inspect exact Boolean degrees.

Arbitrary boundary values; value-map analysis only, not a phase equivalence proof.
No candidate is generated and no official verifier is called.
"""
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import re
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
TARGETS = ('inverse12 products', 'inverse12 norm', 'inverse12 scalar',
           'inverse24 products', 'inverse24 norm', 'multiply v', 'aligned_route')


class Sink:
    def write(self, value):
        self.data = value.encode() if isinstance(value, str) else value
    def flush(self):
        pass


def analyze(lines):
    wires = sorted({int(q) for line in lines for q in re.findall(r'\bq(\d+)\b', line)})
    state = {q: {1 << i} for i,q in enumerate(wires)}
    initial = {q: set(v) for q,v in state.items()}
    counts = Counter()
    largest = len(wires)
    for line in lines:
        op = line.split()[0]
        counts[op] += 1
        if op == 'INFO_TAG':
            continue
        if ' if ' in line or op not in ('X', 'CX', 'CCX', 'SWAP'):
            return {'wires': wires, 'gate_counts': dict(Counter(l.split()[0] for l in lines)),
                    'scope': 'Exact ANF skipped: measurement, phase, condition or unsupported gate present.'}
        ws = [int(q) for q in re.findall(r'\bq(\d+)\b', line)]
        if op == 'X':
            state[ws[0]] ^= {0}
        elif op == 'CX':
            state[ws[1]] ^= state[ws[0]]
        elif op == 'SWAP':
            state[ws[0]],state[ws[1]] = state[ws[1]],state[ws[0]]
        else:
            a,b,c = ws
            product = set()
            for x in state[a]:
                for y in state[b]:
                    m = x | y
                    if m in product:
                        product.remove(m)
                    else:
                        product.add(m)
            state[c] ^= product
        largest = max(largest, max(map(len, state.values())))
        if largest > 200000:
            return {'wires': wires, 'scope': 'Stopped symbolic expansion above 200000 monomials.'}
    changed = {q: state[q] ^ initial[q] for q in wires if state[q] != initial[q]}
    degree = max((m.bit_count() for p in state.values() for m in p), default=0)
    deltas = {str(q): dict(Counter(m.bit_count() for m in p)) for q,p in changed.items()}
    quadratic, linear = [], []
    graph = defaultdict(set)
    for target,poly in changed.items():
        for monomial in sorted(poly):
            variables = [wires[i] for i in range(len(wires)) if monomial >> i & 1]
            if len(variables) == 2:
                a,b = variables
                quadratic.append([a,b,target])
                graph[a].add(b)
                graph[b].add(a)
            elif len(variables) <= 1:
                linear.append({'target': target, 'variables': variables})
    colors = {}
    bipartite = True
    for vertex in sorted(graph):
        if vertex in colors:
            continue
        colors[vertex] = 0
        todo = [vertex]
        while todo:
            a = todo.pop()
            for b in graph[a]:
                if b not in colors:
                    colors[b] = 1-colors[a]
                    todo.append(b)
                elif colors[b] == colors[a]:
                    bipartite = False
    independent = not (set(graph) & set(changed))
    return {'wires': wires, 'gate_counts': dict(counts), 'max_output_degree': degree,
            'changed_wires': list(changed), 'unchanged_wires': [q for q in wires if q not in changed],
            'delta_degree_histograms': deltas, 'max_intermediate_monomials_per_wire': largest,
            'quadratic_inputs_unchanged': independent, 'quadratic_graph_bipartite': bipartite,
            'bilinear_partition': [[q for q in sorted(colors) if colors[q] == color]
                                   for color in (0,1)] if bipartite else None,
            'quadratic_terms': quadratic, 'affine_delta_terms': linear,
            'scope': 'Exact value ANFs with all boundary wires independent. A graph bipartition is reported when present; no replacement or surrounding phase behavior has been verified.'}


def main():
    c = km.Circuit.from_file(ROOT/'artifacts/20261106_syed_v9/release/dqi.kmb', format='kmb')
    sink = Sink()
    c.to_file(sink, format='kmx')
    active = {}
    found = {}
    for raw in io.BytesIO(sink.data):
        line = raw.decode().rstrip()
        if line.startswith('INFO_TAG "@exit:'):
            name = line.split('"')[1][6:]
            if name in active:
                found[name] = active.pop(name)
                if len(found) == len(TARGETS):
                    break
        for name in active:
            active[name].append(line)
        if line.startswith('INFO_TAG "@enter:'):
            name = line.split('"')[1][7:]
            if name in TARGETS and name not in found and name not in active:
                active[name] = []
    out = ROOT/'artifacts/20261106_high_return_research/kernels'
    out.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for name,lines in found.items():
        (out/(name.replace(' ','_')+'.kmx')).write_text('\n'.join(lines)+'\n')
        summaries[name] = analyze(lines)
    (out/'structure.json').write_text(json.dumps(summaries, indent=2)+'\n')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
