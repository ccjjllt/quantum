#!/usr/bin/env python3
"""Literature scan for cheaper quantum Reed-Solomon / DQI syndrome decoders.

Read-only. Queries arXiv API and OpenAlex, dumps JSON + a compact index.
Usage: python scan.py <outdir>
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARXIV = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

ARXIV_QUERIES = {
    "rs_decoder": 'abs:"Reed-Solomon" AND abs:decod*',
    "bch_decoder": 'abs:"BCH" AND abs:"decoding"',
    "alg_decoding_quantum": 'abs:"algebraic decoding" AND abs:"quantum"',
    "divstep": 'all:divstep',
    "safegcd": 'all:safegcd',
    "extgcd_quantum": 'abs:"extended Euclidean" AND abs:quantum',
    "gcd_quantum": 'abs:"greatest common divisor" AND abs:quantum',
    "modinv_quantum": 'abs:"modular inversion" AND abs:quantum',
    "halfgcd": 'all:"half-gcd"',
    "mbuc": 'all:"measurement-based uncomputation"',
    "uncompute_meas": 'abs:uncomputation AND abs:measurement',
    "bm_quantum": 'abs:"Berlekamp-Massey"',
    "syndrome_circuit": 'abs:"syndrome" AND abs:"quantum circuit" AND abs:decod*',
    "polynomial_arith_rev": 'abs:"polynomial arithmetic" AND abs:reversible',
    "forney": 'abs:Forney AND abs:quantum',
    "chien": 'abs:Chien AND abs:quantum',
    "reed_solomon_quantum_alg": 'abs:"Reed-Solomon" AND abs:"quantum algorithm"',
    "toffoli_rs": 'abs:Toffoli AND abs:"Reed-Solomon"',
    "quantum_ecc_decoder": 'abs:"quantum" AND abs:"decoder" AND abs:"Toffoli" AND abs:"code"',
}

OPENALEX_QUERIES = {
    "oa_rs_quantum_decoding": "quantum Reed-Solomon decoding circuit",
    "oa_bch_quantum_decoder": "quantum BCH decoder circuit",
    "oa_divstep_quantum": "divstep quantum circuit",
    "oa_gcd_quantum_circuit": "quantum circuit greatest common divisor reversible",
    "oa_mbuc": "measurement based uncomputation",
    "oa_alg_soft_decoding": "algebraic soft-decision decoding Reed-Solomon",
    "oa_syndrome_phase": "syndrome decoding phase oracle quantum",
}

FROM = "2024-01-01"


def fetch(url, tries=3, sleep=2.0):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lit-scan/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=45) as f:
                return f.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"  retry {i+1}: {e}", file=sys.stderr)
            time.sleep(sleep * (i + 1))


def arxiv(q, max_results=40):
    url = f"{ARXIV}?search_query={urllib.parse.quote(q)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    root = ET.fromstring(fetch(url))
    out = []
    for e in root.findall("a:entry", NS):
        aid = e.find("a:id", NS).text.rsplit("/", 1)[-1]
        out.append({
            "id": aid,
            "title": " ".join(e.find("a:title", NS).text.split()),
            "published": e.find("a:published", NS).text[:10],
            "updated": e.find("a:updated", NS).text[:10],
            "authors": [a.find("a:name", NS).text for a in e.findall("a:author", NS)],
            "summary": " ".join(e.find("a:summary", NS).text.split()),
            "comment": (e.find("arxiv:comment", NS).text if e.find("arxiv:comment", NS) is not None else ""),
            "journal": (e.find("arxiv:journal_ref", NS).text if e.find("arxiv:journal_ref", NS) is not None else ""),
        })
    return out


def openalex(q, per_page=25):
    url = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
           + f"&filter=from_publication_date:{FROM}&per-page={per_page}&sort=relevance_score:desc")
    doc = json.loads(fetch(url))
    out = []
    for w in doc.get("results", []):
        inv = (w.get("abstract_inverted_index") or {})
        pos = {}
        for tok, idxs in inv.items():
            for i in idxs:
                pos[i] = tok
        abstract = " ".join(pos[i] for i in sorted(pos))[:1200]
        out.append({
            "id": w.get("doi") or w.get("id"),
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "cited_by": w.get("cited_by_count"),
            "abstract": abstract,
        })
    return out


def main():
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "scan_out")
    outdir.mkdir(parents=True, exist_ok=True)
    results = {"arxiv": {}, "openalex": {}}
    for name, q in ARXIV_QUERIES.items():
        try:
            r = arxiv(q)
        except Exception as e:  # noqa: BLE001
            print(f"arXiv {name} FAILED: {e}", file=sys.stderr)
            r = []
        results["arxiv"][name] = {"query": q, "hits": r}
        print(f"arXiv {name}: {len(r)}")
        time.sleep(3.0)
    for name, q in OPENALEX_QUERIES.items():
        try:
            r = openalex(q)
        except Exception as e:  # noqa: BLE001
            print(f"OpenAlex {name} FAILED: {e}", file=sys.stderr)
            r = []
        results["openalex"][name] = {"query": q, "hits": r}
        print(f"OpenAlex {name}: {len(r)}")
        time.sleep(1.0)
    (outdir / "scan_raw.json").write_text(json.dumps(results, indent=1))

    # compact index of 2024+ arXiv hits
    lines = ["# arXiv hits (submitted >= 2024-01-01)", ""]
    for name, blk in results["arxiv"].items():
        lines.append(f"## {name}  (`{blk['query']}`)")
        for h in blk["hits"]:
            if h["published"] < FROM:
                continue
            lines.append(f"- {h['id']} [{h['published']}] {h['title']}")
            lines.append(f"  - {h['authors'][0] if h['authors'] else '?'} +{max(0,len(h['authors'])-1)}; {h['comment'][:110]}")
        lines.append("")
    (outdir / "index_arxiv.md").write_text("\n".join(lines))

    lines = ["# OpenAlex hits (published >= 2024-01-01)", ""]
    for name, blk in results["openalex"].items():
        lines.append(f"## {name}  (`{blk['query']}`)")
        for h in blk["hits"]:
            lines.append(f"- [{h['year']}] {h['title']} | {h['venue']} | cites={h['cited_by']} | {h['id']}")
        lines.append("")
    (outdir / "index_openalex.md").write_text("\n".join(lines))
    print("wrote", outdir)


if __name__ == "__main__":
    main()
