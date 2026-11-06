"""Write the deletion ledger for the 2026-11-06 invsqrt cleanup.

The bulk deletion ran in run_cleanup.py and aborted on main-owned symlinks after
removing the research directories but before the ledger was flushed.  This script
records the deletion scope from the directory sizes measured immediately before
deletion (captured in the session log) and hashes the evidence copies preserved
in evidence/ plus the retained gain-chain artefacts.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum/.worktree/invsqrt')

# Sizes measured with `du -sh` immediately before deletion (session transcript).
EXP_DIRS = {
    'experiments/invsqrt/20261105_gain_review': '8.0K',
    'experiments/invsqrt/20261105_rotlp': '224K',
    'experiments/invsqrt/20261105_shared_target': '292K',
    'experiments/invsqrt/20261105_w15395': '24K',
    'experiments/invsqrt/20261106_batch_910': '8.0K',
    'experiments/invsqrt/20261106_batch_big': '8.0K',
    'experiments/invsqrt/20261106_batch_chainbig': '24K',
    'experiments/invsqrt/20261106_batch_cswap': '40K',
    'experiments/invsqrt/20261106_batch_cswap2': '8.0K',
    'experiments/invsqrt/20261106_batch_small': '32K',
    'experiments/invsqrt/20261106_block_resynth': '104K',
    'experiments/invsqrt/20261106_census_maoxin2': '8.0K',
    'experiments/invsqrt/20261106_tclass_harvest': '32K',
    'experiments/invsqrt/20261106_window21764_pluscx': '12K',
    'experiments/invsqrt/20261106_window21764_z3': '32K',
    'experiments/invsqrt/20261106_window25495_pluscx': '12K',
    'experiments/invsqrt/20261106_window25750_25779_pluscx': '12K',
    'experiments/invsqrt/20261106_window38187_pluscx': '12K',
}

ART_DIRS = {
    'artifacts/20261105_rotlp': '96M',
    'artifacts/20261105_w15395': '4.8M',
    'artifacts/20261105_shortcache': '6.1M',
    'artifacts/20261105_crosshmr_synth': '96K',
    'artifacts/20261031_invsqrt62_replay': '8.0M',
    'artifacts/20261102_generator_v2': '5.3M',
    'artifacts/20261102_baseline_patch': '24K',
    'artifacts/20261103_baseline_patch_round2': '24K',
    'artifacts/20261106_batch_910': '8.0K',
    'artifacts/20261106_batch_big': '8.0K',
    'artifacts/20261106_batch_chainbig': '8.0K',
    'artifacts/20261106_batch_cswap': '24K',
    'artifacts/20261106_batch_cswap2': '8.0K',
    'artifacts/20261106_batch_small': '16K',
    'artifacts/20261106_block_resynth': '1.5M',
    'artifacts/20261106_census_maoxin2': '36K',
    'artifacts/20261106_tclass_harvest': '1.0M',
    'artifacts/20261106_window21764_pluscx': '8.0K',
    'artifacts/20261106_window21764_z3': '16K',
    'artifacts/20261106_window25495_pluscx': '8.0K',
    'artifacts/20261106_window25495_z3': '12K',
    'artifacts/20261106_window25750_25779_pluscx': '8.0K',
    'artifacts/20261106_window38187_pluscx': '8.0K',
    'artifacts/20261106_window38187_z3': '8.0K',
}

UNIT = {'B': 1, 'K': 1 << 10, 'M': 1 << 20, 'G': 1 << 30}


def to_bytes(s):
    s = s.strip()
    return int(float(s[:-1]) * UNIT[s[-1]]) if s[-1] in UNIT else int(s)


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ledger = []
    for rel, size in EXP_DIRS.items():
        ledger.append({
            'path': rel,
            'kind': 'directory',
            'bytes_observed_before_deletion': to_bytes(size),
            'size_text': size,
            'reason': 'no verified cost reduction; conclusions consolidated in '
                      '20261106_cleanup/README.md',
            'git_tracked': False,
            'per_file_sha256': 'not captured (ledger flush aborted on a main-owned '
                               'symlink; directory content no longer exists)',
        })
    for rel, size in ART_DIRS.items():
        ledger.append({
            'path': rel,
            'kind': 'directory',
            'bytes_observed_before_deletion': to_bytes(size),
            'size_text': size,
            'reason': 'no verified cost reduction and not referenced by the retained '
                      'gain chain (see 20261106_cleanup/README.md)',
            'git_tracked': False,
            'per_file_sha256': 'not captured (same abort as above)',
        })

    preserved = []
    for p in sorted((ROOT / 'experiments/invsqrt/20261106_cleanup/evidence').iterdir()):
        preserved.append({'path': str(p.relative_to(ROOT)),
                          'bytes': p.stat().st_size, 'sha256': sha256(p)})
    for rel in ('artifacts/20261105_maoxin_v2/invsqrt/maoxin_v2_nofallback.kmb',
                'artifacts/20261104_reaudit/cross_hmr/public62_nofallback_cross_hmr.kmb',
                'artifacts/20261104_public62_optimization/invsqrt/public62_nofallback.kmb',
                'artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb',
                'artifacts/20261102_hw06_opt/invsqrt/baseline_hw06.kmb'):
        p = ROOT / rel
        if p.exists():
            preserved.append({'path': rel, 'bytes': p.stat().st_size,
                              'sha256': sha256(p)})

    out = ROOT / 'experiments/invsqrt/20261106_cleanup/deleted_files.json'
    out.write_text(json.dumps({
        'date': '2026-11-06',
        'branch': 'codex/invsqrt-research',
        'head_before_cleanup': '60ee044',
        'note': 'No-gain research directories removed after consolidating conclusions '
                'into README.md and DETAILED_rotation_lp_and_full_single_delete.md. '
                'Per-file SHA-256 for the removed directories could not be recorded: '
                'the deletion script removed the directories and then aborted while '
                'walking a main-owned symlink, before the ledger was written. '
                'Directory sizes below were measured with du -sh immediately before '
                'deletion and are preserved here for traceability.',
        'deleted_directories': ledger,
        'deleted_total_bytes_approx': sum(x['bytes_observed_before_deletion'] for x in ledger),
        'preserved_evidence_and_gain_artefacts': preserved,
        'not_deleted_main_owned_symlinks': [
            'artifacts/20261030_public_audit', 'artifacts/20261030_public_best',
            'artifacts/20261101_public_hw06', 'artifacts/20261104_public_refresh',
            'artifacts/20261104_submission_refresh',
        ],
    }, indent=1))
    print('ledger written:', out)
    print('directories recorded:', len(ledger),
          'approx bytes:', sum(x['bytes_observed_before_deletion'] for x in ledger))
    print('preserved artefacts hashed:', len(preserved))


if __name__ == '__main__':
    main()
