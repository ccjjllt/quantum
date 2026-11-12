"""Stage census of the eae396ba DQI circuit (first experiment of the direct-phase/MBU bet).

Reads the .kmb, dumps a .kmx to artifacts, and reuses the e9diff stage_census
function to count paid gates and phase gates per INFO_TAG stage.
"""
import json, sys, tempfile
from pathlib import Path
ROOT = Path('/Users/zhaohuaxiang/ccjjllt/quantum')
sys.path.insert(0, str(ROOT/'.worktree/dqi/experiments/dqi/20261110_e9diff'))
from stage_census import dump_kmx, stage_census_kmx  # noqa: E402

KMB = ROOT/'artifacts/20261112_eae_candidate/dqi.kmb'
OUT = ROOT/'.worktree/dqi/artifacts/20261112_direct_phase'
OUT.mkdir(parents=True, exist_ok=True)

def main():
    with tempfile.TemporaryDirectory() as td:
        kmx = dump_kmx(KMB, Path(td))
        print('kmx', kmx, kmx.stat().st_size, flush=True)
        res = stage_census_kmx(kmx, KMB)
    (OUT/'stage_census_eae.json').write_text(json.dumps(res, indent=2)+'\n')
    print(json.dumps(res, indent=2)[:6000], flush=True)

if __name__ == '__main__':
    main()
