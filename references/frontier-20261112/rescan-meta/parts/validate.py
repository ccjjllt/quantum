#!/usr/bin/env python3
"""Validate cross-file references and interface contracts in a module bundle."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def validate(bundle: Path) -> dict:
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["schema"] in {"vqcc-modular-parts-bundle-v1", "vqcc-modular-parts-bundle-v2"}
    for family, entry in manifest["families"].items():
        for name, digest in entry["files"].items():
            assert sha(bundle / family / name) == digest, (family, name)
        assert sha(bundle / family / "manifest.json") == entry["source_manifest_sha256"]

    inv = bundle / "invsqrt"
    sources = {r["source_sha256"]: r for r in rows(inv / "sources.jsonl")}
    cuts = {r["cut_id"]: r for r in rows(inv / "cuts.jsonl")}
    modules = {r["module_id"]: r for r in rows(inv / "modules.jsonl")}
    edges = rows(inv / "source_edges.jsonl")
    joins = rows(inv / "cross_source_joins.jsonl")
    assert len(sources) == 46 and len(cuts) == 186 and len(modules) == 140
    assert len(edges) == 94 and len(joins) == 45
    for source_sha, source in sources.items():
        parts = sorted((m for m in modules.values() if m["source_sha256"] == source_sha),
                       key=lambda m: m["op_span"][0])
        assert parts and parts[0]["op_span"][0] == 0
        assert parts[-1]["op_span"][1] == source["operation_count"]
        assert sum(m["static_resources"]["operations"] for m in parts) == source["operation_count"]
        assert all(a["op_span"][1] == b["op_span"][0] and a["exit_cut_id"] == b["entry_cut_id"]
                   for a, b in zip(parts, parts[1:]))
        for m in parts:
            assert cuts[m["entry_cut_id"]]["source_sha256"] == source_sha
            assert cuts[m["exit_cut_id"]]["source_sha256"] == source_sha
            assert cuts[m["entry_cut_id"]]["op_cut"] == m["op_span"][0]
            assert cuts[m["exit_cut_id"]]["op_cut"] == m["op_span"][1]
            assert len(m["entry"]["quantum_state_wires"]) == source["qubits"]
            assert len(m["exit"]["quantum_state_wires"]) == source["qubits"]
    for edge in edges:
        left, right = modules[edge["from_module_id"]], modules[edge["to_module_id"]]
        assert left["source_sha256"] == right["source_sha256"]
        assert left["exit_cut_id"] == right["entry_cut_id"] == edge["shared_cut_id"]
    for join in joins:
        assert cuts[join["donor_cut_id"]]["source_sha256"] == join["donor_source_sha256"]
        assert cuts[join["host_cut_id"]]["source_sha256"] == join["host_source_sha256"]
        donor, host = modules[join["anchor_module_id"]], modules[join["host_anchor_module_id"]]
        assert donor["entry_cut_id"] == join["donor_cut_id"]
        assert host["entry_cut_id"] == join["host_cut_id"]
        assert donor["operation_text_sha256"] == host["operation_text_sha256"]
        assert donor["static_resources"]["operations"] == host["static_resources"]["operations"] == join["shared_anchor_operations"]

    chem = bundle / "chemistry"
    loaders = {r["module_id"]: r for r in rows(chem / "chemistry_modules.jsonl")}
    tables = {r["table_key"]: r for r in rows(chem / "chemistry_word_tables.jsonl")}
    weights = {r["npz_sha256"]: r for r in rows(chem / "chemistry_factorizations.jsonl")}
    accuracy = rows(chem / "chemistry_accuracy.jsonl")
    best = rows(chem / "chemistry_best_control.jsonl")
    assert len(loaders) == 1047 and len(tables) == 34 and len(weights) == 225
    assert len(accuracy) == 2226 and len(best) == 1
    for loader in loaders.values():
        k = loader["entry"]["slot"]
        assert loader["exit"]["slot"] == k + 1
        for key in loader["compatible_word_tables"]:
            table = tables[key]
            assert table["layout_sha256"] == loader["entry"]["layout_sha256"] == loader["exit"]["layout_sha256"]
            assert table["block_words_sha256"][k] == loader["exit"]["word_block_sha256"]
            assert ("ZERO" if k == 0 else table["block_words_sha256"][k - 1]) == loader["entry"]["word_block_sha256"]
    pairs = {(a["npz_sha256"], a["table_key"]): a for a in accuracy}
    assert len(pairs) == len(accuracy)
    assert all(a["npz_sha256"] in weights and a["table_key"] in tables for a in accuracy)
    control = best[0]
    assert pairs[(control["npz_sha256"], control["table_key"])]["passes_recorded_gate"]
    path = [loaders[x] for x in control["module_ids"]]
    assert len(path) == tables[control["table_key"]]["slots"]
    assert all(m["entry"]["slot"] == k and control["table_key"] in m["compatible_word_tables"]
               for k, m in enumerate(path))
    assert all(a["exit"]["word_block_sha256"] == b["entry"]["word_block_sha256"]
               for a, b in zip(path, path[1:]))
    result = {"schema": "vqcc-modular-parts-validation-v1", "status": "PASS",
            "manifest_sha256": sha(bundle / "manifest.json"),
            "invsqrt_sources": len(sources), "invsqrt_modules": len(modules),
            "invsqrt_joins_by_status": dict(collections.Counter(j["candidate_status"] for j in joins)),
            "chemistry_modules": len(loaders), "chemistry_tables": len(tables),
            "chemistry_factorizations": len(weights),
            "chemistry_recorded_passing_pairs": sum(a["passes_recorded_gate"] for a in accuracy),
            "best_assembly_modules": len(path)}
    if "dqi" in manifest["families"]:
        dqi = bundle / "dqi"
        dqi_sources = {r["source_sha256"]: r for r in rows(dqi / "dqi_sources.jsonl")}
        dqi_modules = {r["module_id"]: r for r in rows(dqi / "dqi_modules.jsonl")}
        dqi_edges = rows(dqi / "dqi_source_edges.jsonl")
        assert len(dqi_sources) == 15 and len(dqi_modules) == 163 and len(dqi_edges) == 148
        for source_sha, source in dqi_sources.items():
            parts = sorted((m for m in dqi_modules.values() if m["source_sha256"] == source_sha),
                           key=lambda m: m["op_span"][0])
            assert parts[0]["op_span"][0] == 0 and parts[-1]["op_span"][1] == source["operations"]
            assert all(a["op_span"][1] == b["op_span"][0] for a, b in zip(parts, parts[1:]))
            assert sum(m["static_resources"]["operations"] for m in parts) == source["operations"]
        for edge in dqi_edges:
            left, right = dqi_modules[edge["from_module_id"]], dqi_modules[edge["to_module_id"]]
            assert left["source_sha256"] == right["source_sha256"]
            assert left["op_span"][1] == right["op_span"][0] == edge["shared_op_cut"]
        result.update(dqi_sources=len(dqi_sources), dqi_modules=len(dqi_modules),
                      dqi_source_edges=len(dqi_edges))
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    result = validate(args.bundle)
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        if args.out.exists():
            p.error(f"refuse overwrite: {args.out}")
        args.out.write_text(content)
    print(content, end="")


if __name__ == "__main__":
    main()
