"""Count GF-mult call sites via @enter/@exit:gf_mul markers; width by inner CCX count."""
import json
import sys
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def main():
    assert KMX is not None and KMX.exists(), "usage: count_qq.py <dqi.kmx>"
    n_enter = n_exit = 0
    inner_ccx = 0
    in_mult = 0
    widths = {}
    cur_ccx = 0
    total_lines = 0
    tag_lines = 0
    other_tags = {}
    with open(KMX) as f:
        for line in f:
            total_lines += 1
            if line.startswith("INFO_TAG"):
                tag_lines += 1
                if "@enter:gf_mul" in line:
                    n_enter += 1
                    in_mult += 1
                    cur_ccx = 0
                elif "@exit:gf_mul" in line:
                    n_exit += 1
                    in_mult -= 1
                    widths[cur_ccx] = widths.get(cur_ccx, 0) + 1
                    cur_ccx = 0
                else:
                    tag = line.split(None, 1)[1].strip().strip('"') if len(line.split()) > 1 else line.strip()
                    other_tags[tag] = other_tags.get(tag, 0) + 1
            elif line.startswith("CCX") and in_mult > 0:
                cur_ccx += 1
    out = {"kmx": str(KMX), "total_lines": total_lines, "info_tag_lines": tag_lines,
           "gf_mul_enters": n_enter, "gf_mul_exits": n_exit,
           "balanced": n_enter == n_exit,
           "ccx_per_span_histogram": {str(k): v for k, v in sorted(widths.items())},
           "other_info_tags": dict(sorted(other_tags.items(), key=lambda kv: -kv[1])[:30])}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
