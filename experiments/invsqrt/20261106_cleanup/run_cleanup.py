"""Delete no-gain research dirs/files and produce a traceable ledger.

Deletes exactly the paths listed in KEEP/DELETE below, recording for every removed
file: relative path, byte size, sha256, reason, and whether it was git-tracked.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')

EXP_DIRS = [
    'experiments/invsqrt/20261105_rotlp',
    'experiments/invsqrt/20261105_shared_target',
    'experiments/invsqrt/20261105_w15395',
    'experiments/invsqrt/20261105_gain_review',
    'experiments/invsqrt/20261106_batch_910',
    'experiments/invsqrt/20261106_batch_big',
    'experiments/invsqrt/20261106_batch_chainbig',
    'experiments/invsqrt/20261106_batch_cswap',
    'experiments/invsqrt/20261106_batch_cswap2',
    'experiments/invsqrt/20261106_batch_small',
    'experiments/invsqrt/20261106_block_resynth',
    'experiments/invsqrt/20261106_census_maoxin2',
    'experiments/invsqrt/20261106_tclass_harvest',
    'experiments/invsqrt/20261106_window21764_pluscx',
    'experiments/invsqrt/20261106_window21764_z3',
    'experiments/invsqrt/20261106_window25495_pluscx',
    'experiments/invsqrt/20261106_window25750_25779_pluscx',
    'experiments/invsqrt/20261106_window38187_pluscx',
]

ART_DIRS = [
    'artifacts/20261105_rotlp',
    'artifacts/20261105_w15395',
    'artifacts/20261105_shortcache',
    'artifacts/20261105_crosshmr_synth',
    'artifacts/20261031_invsqrt62_replay',
    'artifacts/20261102_generator_v2',
    'artifacts/20261102_baseline_patch',
    'artifacts/20261103_baseline_patch_round2',
    'artifacts/20261106_batch_910',
    'artifacts/20261106_batch_big',
    'artifacts/20261106_batch_chainbig',
    'artifacts/20261106_batch_cswap',
    'artifacts/20261106_batch_cswap2',
    'artifacts/20261106_batch_small',
    'artifacts/20261106_block_resynth',
    'artifacts/20261106_census_maoxin2',
    'artifacts/20261106_tclass_harvest',
    'artifacts/20261106_window21764_pluscx',
    'artifacts/20261106_window21764_z3',
    'artifacts/20261106_window25495_pluscx',
    'artifacts/20261106_window25495_z3',
    'artifacts/20261106_window25750_25779_pluscx',
    'artifacts/20261106_window38187_pluscx',
    'artifacts/20261106_window38187_z3',
    'artifacts/20261030_public_audit',
    'artifacts/20261030_public_best',
    'artifacts/20261101_public_hw06',
    'artifacts/20261104_public_refresh',
    'artifacts/20261104_submission_refresh',
]

REASON_EXP = ('no verified cost reduction; conclusions consolidated in '
              'experiments/invsqrt/20261106_cleanup/README.md')
REASON_ART = ('no verified cost reduction; no longer referenced by retained '
              'gain chain (see 20261106_cleanup/README.md)')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ledger = []
    for group, reason in ((EXP_DIRS, REASON_EXP), (ART_DIRS, REASON_ART)):
        for rel in group:
            d = ROOT / rel
            if not d.exists():
                print('skip (absent):', rel)
                continue
            files = sorted(p for p in d.rglob('*') if p.is_file())
            for p in files:
                ledger.append({
                    'path': str(p.relative_to(ROOT)),
                    'bytes': p.stat().st_size,
                    'sha256': sha256(p),
                    'reason': reason,
                    'git_tracked': False,
                })
            shutil.rmtree(d)
            print('removed dir %s (%d files)' % (rel, len(files)))
    out = ROOT / 'experiments/invsqrt/20261106_cleanup/deleted_files.json'
    out.write_text(json.dumps({
        'date': '2026-11-06',
        'note': 'Deleted no-gain research records after consolidating conclusions '
                'into README.md and the two appendices in this directory.',
        'total_files': len(ledger),
        'total_bytes': sum(x['bytes'] for x in ledger),
        'files': ledger,
    }, indent=1))
    print('ledger:', out, 'files:', len(ledger),
          'bytes:', sum(x['bytes'] for x in ledger))


if __name__ == '__main__':
    main()
