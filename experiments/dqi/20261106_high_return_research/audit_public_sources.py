"""Manual static inspection of downloaded public DQI source; never imports it."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'artifacts/20261106_high_return_research/public'


def imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def main():
    folder = PUBLIC / 'ahoirg_release1'
    raw = (folder / 'dqi-source-bundle.json').read_bytes()
    bundle = json.loads(raw)
    files = bundle['files']
    stems = {Path(path).stem for path in files if path.endswith('.py')}
    unresolved, literals, syntax_errors, hash_mismatches = {}, {}, [], []
    for name, pin in files.items():
        data = pin['text'].encode('utf-8')
        if len(data) != pin['bytes'] or hashlib.sha256(data).hexdigest() != pin['sha256']:
            hash_mismatches.append(name)
        if not name.endswith('.py'):
            continue
        try:
            tree = ast.parse(pin['text'], filename=name)
        except SyntaxError as error:
            syntax_errors.append([name, str(error)])
            continue
        for module in imports(tree):
            if module.split('.')[0] in sys.stdlib_module_names | {'circ', 'kickmix', 'numpy'}:
                continue
            if module.split('.')[-1] not in stems and not any(
                '/' + module.replace('.', '/') + '/' in path for path in files
            ):
                unresolved.setdefault(module, []).append(name)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value.endswith(('.json', '.py')) and '\n' not in node.value):
                literal = node.value
                row = literals.setdefault(literal, {
                    'present_basename': any(Path(path).name == Path(literal).name for path in files),
                    'files': [],
                })
                row['files'].append(name)
    manifest = json.loads((folder / 'assets-manifest.json').read_text())['files']
    downloaded_pins = {}
    for name, pin in manifest.items():
        path = folder / name
        if path.is_file():
            data = path.read_bytes()
            downloaded_pins[name] = {
                'bytes_match': len(data) == pin['bytes'],
                'sha256_match': hashlib.sha256(data).hexdigest() == pin['sha256'],
            }
    result = {
        'scope': 'Static bytes/AST only; no downloaded code imported or executed. Basename matching does not prove runtime closure.',
        'source_count': bundle['source_count'], 'input_count': bundle['input_count'],
        'helper_count': bundle['helper_count'], 'files': len(files),
        'bundle_sha256': hashlib.sha256(raw).hexdigest(),
        'candidate': bundle['candidate'], 'expected_native_sha256': bundle['expected_native_sha256'],
        'entry': 'blocks/dqi/pro-q18-900/source/decode_best.py',
        'unresolved_import_names': unresolved, 'literal_resources': literals,
        'syntax_errors': syntax_errors, 'hash_mismatches': hash_mismatches,
        'downloaded_manifest_checks': downloaded_pins,
        'interpretation': {
            'lowclean_shared': 'Explicit sys.modules alias in decode_norm5log7_character.py.',
            'decode_partial': 'Referenced by a historical module whose function is AST-extracted by current owner; not a proof of runtime missing dependency.',
            'gap_zero_and_descending_overlap': 'Imports inside historical functions; reachability remains unexecuted.',
        },
        'all_files': [dict(path=name, bytes=pin['bytes'], sha256=pin['sha256']) for name, pin in files.items()],
    }
    (folder / 'static_dependency_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    q26 = []
    expected = json.loads((PUBLIC / 'somejoint_q26_files.json').read_text())['dataset_files']
    for row in expected:
        if not row['name'].endswith('.py'):
            continue
        path = PUBLIC / 'somejoint_q26' / Path(row['name']).name
        data = path.read_bytes()
        tree = ast.parse(data, filename=row['name'])
        q26.append(dict(path=row['name'], bytes=len(data),
                        size_matches_catalog=len(data) == int(row['total_bytes']),
                        sha256=hashlib.sha256(data).hexdigest(), imports=sorted(set(imports(tree)))))
    (PUBLIC / 'somejoint_q26_source_audit.json').write_text(json.dumps({
        'scope': 'All 25 downloaded files parsed without execution; no standalone build driver in these files.',
        'files': q26,
    }, indent=2) + '\n')
    print(json.dumps(dict(bundle_files=len(files), syntax_errors=len(syntax_errors),
                          hash_mismatches=len(hash_mismatches),
                          manifest_checks=downloaded_pins,
                          unresolved_names=sorted(unresolved),
                          q26_files=len(q26), q26_size_matches=all(r['size_matches_catalog'] for r in q26))))


if __name__ == '__main__':
    main()
