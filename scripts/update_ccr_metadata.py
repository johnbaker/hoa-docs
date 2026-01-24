#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_coverage_entry(op, instrument):
    scope = op.get("scope") or {}
    entry = {
        "action": op.get("op_type") or "other",
        "source_instrument_id": instrument.get("id"),
    }
    effective_at = op.get("effective_at") or instrument.get("effective_at")
    if effective_at:
        entry["effective_at"] = effective_at
    scope_kind = scope.get("scope_kind")
    if scope_kind:
        entry["scope_kind"] = scope_kind
    if scope.get("parcel_ids"):
        entry["parcel_ids"] = scope.get("parcel_ids")
    if scope.get("lot_ids"):
        entry["lot_ids"] = scope.get("lot_ids")
    if scope.get("legal_description"):
        entry["legal_description"] = scope.get("legal_description")
    return entry


def build_declarant_entry(op, instrument):
    parties = op.get("parties") or {}
    name = (
        parties.get("assignee")
        or parties.get("grantee")
        or parties.get("declarant")
        or parties.get("assignor")
        or parties.get("grantor")
    )
    if not name:
        return None
    entry = {
        "name": name,
        "source_instrument_id": instrument.get("id"),
    }
    effective_at = op.get("effective_at") or instrument.get("effective_at")
    if effective_at:
        entry["effective_at"] = effective_at
    if parties.get("assignee"):
        entry["role"] = "assignee"
    elif parties.get("grantee"):
        entry["role"] = "grantee"
    elif parties.get("declarant"):
        entry["role"] = "declarant"
    elif parties.get("assignor"):
        entry["role"] = "assignor"
    elif parties.get("grantor"):
        entry["role"] = "grantor"
    return entry


def main():
    parser = argparse.ArgumentParser(description="Update CCR metadata (coverage/declarant) from amendments.")
    parser.add_argument("--base", default="data/instruments/ccr-1999-05-27.json", help="Path to CCR base JSON.")
    parser.add_argument("--instruments-dir", default="data/instruments", help="Directory with instrument JSON files.")
    args = parser.parse_args()

    base_path = Path(args.base)
    instruments_dir = Path(args.instruments_dir)

    base = load_json(base_path)
    coverage_entries = []
    declarant_entries = []

    for path in instruments_dir.glob("*.json"):
        data = load_json(path)
        instrument = data.get("instrument", {})
        if instrument.get("instrument_kind") != "amendment":
            continue
        for op in data.get("operations", []) or []:
            if op.get("target_base_doc_id") != "ccr":
                continue
            op_type = op.get("op_type")
            if op_type in ("annex_property", "deannex_property"):
                coverage_entries.append(build_coverage_entry(op, instrument))
            elif op_type == "assign_declarant_rights":
                entry = build_declarant_entry(op, instrument)
                if entry:
                    declarant_entries.append(entry)

    def sort_key(entry):
        return (entry.get("effective_at") or "", entry.get("source_instrument_id") or "")

    coverage_entries = sorted(coverage_entries, key=sort_key)
    declarant_entries = sorted(declarant_entries, key=sort_key)

    base.setdefault("instrument", {})["coverage"] = coverage_entries
    base["instrument"]["declarant_history"] = declarant_entries
    base["instrument"]["current_declarant"] = declarant_entries[-1] if declarant_entries else None

    write_json(base_path, base)


if __name__ == "__main__":
    main()
