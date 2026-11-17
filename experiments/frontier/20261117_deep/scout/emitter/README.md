# Public ANGLE_k emitter — provenance

Copied 2026-11-17 from Kaggle dataset **`taylorclark637/dfthcsos-generator`** (v2,
2026-11-16, CC BY 4.0), by `kaggle datasets download -d taylorclark637/dfthcsos-generator -f <file>`.
Text only; no circuits or logs are stored here.

| file | bytes | sha256 |
|---|---:|---|
| `dfthcsos_gen.py` | 12,124 | `bc8b7683fa826977328c2517f0160fd85e23b920e75872e14bae4237e097073f` |
| `dfthcsos-generator-design.md` | 14,939 | `bc8e52795d3cbecbac79440580ea4ae4fdb063eb0bdca61e598f89a39a1fa7c2` |
| `dqi-dfthcsos-verifier-spec.md` | 10,639 | `e19b6b8b75c84dfb643efa5904e738cd8c98fe636bd50e1ae504ae2e8f20bbf4` |
| `manifest.json` | 3,940 | `ad990e332af31e9401d0f28cf71b12c4aa61b63f6b085e23a164f8084b987f09` |

Usage (details and cost arithmetic in `../EMITTER.md` §4):

```bash
python dfthcsos_gen.py --words-npz words.npz --out-dir out/ --brot 8 --J 5
```

- input `angle_words` `(num_vectors, 75)` int, values in `[0, 2**brot)`
- output `angle_k_<k>.kmb` + `manifest.json`
- cost `N − 2` Toffolis per circuit (our table: 1,218 × 15 = 18,270/pass vs the shipped
  4,022), so this is a **fallback**, not a replacement for the private coded-word planner.
