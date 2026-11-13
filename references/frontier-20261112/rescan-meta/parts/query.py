#!/usr/bin/env python3
"""JSON-first queries over a local modular-parts bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def chemistry_pair(left: dict, right: dict) -> dict:
    checks = {
        "consecutive_slot": left["exit"]["slot"] == right["entry"]["slot"],
        "word_block": left["exit"]["word_block_sha256"] == right["entry"]["word_block_sha256"],
        "layout": left["exit"]["layout_sha256"] == right["entry"]["layout_sha256"],
        "J": left["entry"]["J"] == right["entry"]["J"],
        "brot": left["entry"]["brot"] == right["entry"]["brot"],
        "selection_bits": left["entry"]["selection_bits"] == right["entry"]["selection_bits"],
    }
    shared = sorted(set(left["compatible_word_tables"]) & set(right["compatible_word_tables"]))
    return {"schema": "vqcc-module-query-v1", "kind": "chemistry_pair",
            "left_module_id": left["module_id"], "right_module_id": right["module_id"],
            "checks": checks, "static_chain_matches": all(checks.values()),
            "known_common_word_tables": shared,
            "status": ("structural_mismatch" if not all(checks.values()) else
                       "known_table_chain" if shared else "chain_matches_without_known_table"),
            "remaining_obligations": ["full 15-slot table", "factorization/table accuracy",
                                      "whole assembly verifier"]}


def invsqrt_pair(left: dict, right: dict, joins: list[dict]) -> dict:
    same = left["source_sha256"] == right["source_sha256"]
    if same and left["exit_cut_id"] == right["entry_cut_id"]:
        status, evidence = "exact_source_continuity", None
    elif same:
        status, evidence = "nonadjacent_same_source_modules", None
    else:
        match = next((j for j in joins if j["donor_cut_id"] == left["exit_cut_id"]
                      and j["host_cut_id"] == right["entry_cut_id"]), None)
        status = match["candidate_status"] if match else "unknown_cross_source_join"
        evidence = match["evidence"] if match else None
    return {"schema": "vqcc-module-query-v1", "kind": "invsqrt_pair",
            "left_module_id": left["module_id"], "right_module_id": right["module_id"],
            "status": status, "evidence": evidence,
            "verified_whole_candidate": match.get("verified_whole_candidate") if not same and match else None,
            "remaining_obligations": ([] if status == "exact_source_continuity" else
                                      ["all-outcome interface", "native salts", "official whole-circuit verifier"])}


def dqi_pair(left: dict, right: dict) -> dict:
    same = left["source_sha256"] == right["source_sha256"]
    adjacent = same and left["op_span"][1] == right["op_span"][0]
    return {"schema": "vqcc-module-query-v1", "kind": "dqi_pair",
            "left_module_id": left["module_id"], "right_module_id": right["module_id"],
            "status": ("exact_source_continuity" if adjacent else
                       "nonadjacent_same_source_modules" if same else "unknown_cross_source_join"),
            "remaining_obligations": ([] if adjacent else
                                      ["sampled value/record/phase interface", "wire placement",
                                       "multi-draw DQI cost", "official whole-circuit verifier"])}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    s = sub.add_parser("source")
    s.add_argument("sha_prefix")
    m = sub.add_parser("module")
    m.add_argument("module_id")
    c = sub.add_parser("compose")
    c.add_argument("left_module_id")
    c.add_argument("right_module_id")
    args = p.parse_args()
    inv = args.bundle / "invsqrt"
    chem = args.bundle / "chemistry"
    dqi = args.bundle / "dqi"
    inv_modules = rows(inv / "modules.jsonl")
    chem_modules = rows(chem / "chemistry_modules.jsonl")
    dqi_modules = rows(dqi / "dqi_modules.jsonl") if dqi.exists() else []
    all_modules = inv_modules + chem_modules + dqi_modules
    by_id = {r["module_id"]: r for r in all_modules}
    if len(by_id) != len(all_modules):
        raise ValueError("module ID collision")
    if args.command == "summary":
        sources = rows(inv / "sources.jsonl")
        joins = rows(inv / "cross_source_joins.jsonl")
        checks = rows(chem / "chemistry_accuracy.jsonl")
        result = {"schema": "vqcc-module-query-v1", "kind": "summary",
                  "invsqrt": {"sources": len(sources), "modules": len(inv_modules),
                              "source_continuity_edges": len(rows(inv / "source_edges.jsonl")),
                              "cross_source_joins": len(joins),
                              "local_cut_passes": sum(j["candidate_status"] == "local_all_x_cut_pass" for j in joins)},
                  "chemistry": {"loader_modules": len(chem_modules),
                                "word_tables": len(rows(chem / "chemistry_word_tables.jsonl")),
                                "factorizations": len(rows(chem / "chemistry_factorizations.jsonl")),
                                "recorded_accuracy_pairs": len(checks),
                                "recorded_pass_pairs": sum(r["passes_recorded_gate"] for r in checks)}}
        if dqi.exists():
            result["dqi"] = {"sources": len(rows(dqi / "dqi_sources.jsonl")),
                             "stage_modules": len(dqi_modules),
                             "source_continuity_edges": len(rows(dqi / "dqi_source_edges.jsonl"))}
    elif args.command == "source":
        sources = [r for r in rows(inv / "sources.jsonl") if r["source_sha256"].startswith(args.sha_prefix)]
        if dqi.exists():
            sources.extend(r for r in rows(dqi / "dqi_sources.jsonl")
                           if r["source_sha256"].startswith(args.sha_prefix))
        if len(sources) != 1:
            raise ValueError(f"expected one source, found {len(sources)}")
        source = sources[0]
        parts = sorted((r for r in inv_modules + dqi_modules if r["source_sha256"] == source["source_sha256"]),
                       key=lambda r: r["op_span"][0])
        result = {"schema": "vqcc-module-query-v1", "kind": "source",
                  "source": source, "modules": [{"module_id": r["module_id"],
                                                 "op_span": r["op_span"],
                                                 "role": r.get("module_role", r.get("stage_label")),
                                                 "static_resources": r["static_resources"]} for r in parts]}
    elif args.command == "module":
        result = by_id[args.module_id]
    else:
        left, right = by_id[args.left_module_id], by_id[args.right_module_id]
        if left["schema"].endswith("-loader") and right["schema"].endswith("-loader"):
            result = chemistry_pair(left, right)
        elif left["schema"].endswith("-module") and right["schema"].endswith("-module"):
            result = invsqrt_pair(left, right, rows(inv / "cross_source_joins.jsonl"))
        elif left["schema"].endswith("-stage") and right["schema"].endswith("-stage"):
            result = dqi_pair(left, right)
        else:
            result = {"schema": "vqcc-module-query-v1", "kind": "mixed_family_pair",
                      "status": "incompatible_interface_kinds",
                      "left_module_id": left["module_id"], "right_module_id": right["module_id"]}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
