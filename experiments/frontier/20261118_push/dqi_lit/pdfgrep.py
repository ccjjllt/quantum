#!/usr/bin/env python3
"""Extract text from downloaded arXiv PDFs and grep context lines.

Usage: pdfgrep.py <pdfdir> <pattern> [max_hits] [window]
       pdfgrep.py <pdf> --table <page-range>
"""
import re
import sys
from pathlib import Path

from pypdf import PdfReader


def text_of(pdf):
    r = PdfReader(pdf)
    pages = []
    for i, p in enumerate(r.pages):
        try:
            pages.append((i + 1, p.extract_text() or ""))
        except Exception as e:  # noqa: BLE001
            pages.append((i + 1, f"<<extract failed: {e}>>"))
    return pages


def main():
    pdfdir = Path(sys.argv[1])
    pat = sys.argv[2]
    maxhits = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    win = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    files = sorted(pdfdir.glob("*.pdf")) if pdfdir.is_dir() else [pdfdir]
    rx = re.compile(pat, re.I)
    for pdf in files:
        pages = text_of(pdf)
        hits = 0
        out = []
        for pno, t in pages:
            flat = re.sub(r"\s+", " ", t)
            for m in rx.finditer(flat):
                s = max(0, m.start() - win // 2)
                out.append(f"[{pdf.stem} p{pno}] ...{flat[s:m.end()+win]}...")
                hits += 1
                if hits >= maxhits:
                    break
            if hits >= maxhits:
                break
        if out:
            print("\n".join(out))
            print()


if __name__ == "__main__":
    main()
