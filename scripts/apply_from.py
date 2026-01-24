#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_operations(base_data, amend_data):
    content = base_data["content"]
    nodes = {n["id"]: n for n in content["nodes"]}
    instrument = base_data.get("instrument", {})
    amend_instrument = amend_data.get("instrument", {})
    content_meta = content.get("meta") or {}
    tombstones = content_meta.get("tombstones") or []

    parent_by_child = {}
    for node in list(nodes.values()):
        for child in node.get("children", []) or []:
            parent_by_child[child["ref"]] = node["id"]

    def ensure_node_meta(node):
        meta = node.get("meta")
        if meta is None:
            meta = {}
            node["meta"] = meta
        return meta

    def ensure_provenance(node):
        meta = ensure_node_meta(node)
        provenance = meta.get("provenance")
        if provenance is None:
            provenance = {}
            meta["provenance"] = provenance
        return provenance

    def record_created_by(node, op):
        provenance = ensure_provenance(node)
        if "created_by_instrument_id" not in provenance:
            provenance["created_by_instrument_id"] = amend_instrument.get("id")
        if "created_by_op_id" not in provenance:
            provenance["created_by_op_id"] = op.get("op_id")
        if "source_ref" not in provenance and op.get("source_ref"):
            provenance["source_ref"] = op.get("source_ref")

    def record_modified_by(node, op):
        provenance = ensure_provenance(node)
        provenance["modified_by_instrument_id"] = amend_instrument.get("id")
        provenance["modified_by_op_id"] = op.get("op_id")
        if op.get("source_ref"):
            provenance["source_ref"] = op.get("source_ref")

    def describe_position(children, idx):
        if not children:
            return {"position": "unknown"}
        if len(children) == 1:
            return {"position": "only_child"}
        if idx <= 0:
            return {
                "position": "start",
                "before_child_node_id": children[1]["ref"] if len(children) > 1 else None,
            }
        if idx >= len(children) - 1:
            return {
                "position": "end",
                "after_child_node_id": children[-2]["ref"] if len(children) > 1 else None,
            }
        return {
            "position": "after",
            "after_child_node_id": children[idx - 1]["ref"],
            "before_child_node_id": children[idx + 1]["ref"],
        }

    def add_tombstone(node_id, parent_id, children, idx, op):
        if not node_id:
            return
        for existing in tombstones:
            if (
                existing.get("node_id") == node_id
                and existing.get("deleted_by_instrument_id") == amend_instrument.get("id")
                and existing.get("deleted_by_op_id") == op.get("op_id")
            ):
                return
        entry = {
            "node_id": node_id,
            "parent_node_id": parent_id,
            "deleted_by_instrument_id": amend_instrument.get("id"),
            "deleted_by_op_id": op.get("op_id"),
        }
        entry.update(describe_position(children, idx))
        if op.get("source_ref"):
            entry["source_ref"] = op.get("source_ref")
        tombstones.append(entry)

    def ensure_node(node):
        nodes[node["id"]] = node

    def remove_child(parent_id, child_id):
        parent = nodes[parent_id]
        children = parent.get("children", []) or []
        parent["children"] = [c for c in children if c["ref"] != child_id]

    def insert_children(op):
        payload_nodes = op.get("payload_nodes", [])
        payload_ids = {n["id"] for n in payload_nodes}
        child_refs = {c["ref"] for n in payload_nodes for c in n.get("children", [])}
        root_payload = [n for n in payload_nodes if n["id"] not in child_refs]

        target = nodes[op["target_node_id"]]
        children = target.get("children", []) or []
        insert_refs = [{"ref": n["id"]} for n in root_payload]
        position = op.get("position")

        if position == "after":
            idx = next((i for i, c in enumerate(children) if c["ref"] == op.get("after_child_node_id")), None)
            if idx is None:
                idx = len(children) - 1
            children[idx + 1:idx + 1] = insert_refs
        elif position == "before":
            idx = next((i for i, c in enumerate(children) if c["ref"] == op.get("before_child_node_id")), None)
            if idx is None:
                idx = 0
            children[idx:idx] = insert_refs
        elif position == "start":
            children[0:0] = insert_refs
        elif position == "end":
            children.extend(insert_refs)
        else:
            raise ValueError(f"Unsupported insert position: {position}")

        target["children"] = children
        for n in payload_nodes:
            ensure_node(n)
            record_created_by(n, op)
            parent_by_child[n["id"]] = op["target_node_id"]

    def delete_node(op):
        target_node_id = op["target_node_id"]
        parent_id = parent_by_child.get(target_node_id)
        if parent_id:
            parent = nodes[parent_id]
            children = parent.get("children", []) or []
            idx = next((i for i, c in enumerate(children) if c["ref"] == target_node_id), None)
            if idx is not None:
                add_tombstone(target_node_id, parent_id, children, idx, op)
            remove_child(parent_id, target_node_id)

    def delete_children(op):
        target = nodes[op["target_node_id"]]
        children = target.get("children", []) or []
        for idx, child in enumerate(children):
            add_tombstone(child["ref"], op["target_node_id"], children, idx, op)
        target["children"] = []

    def replace_children(op):
        payload_nodes = op.get("payload_nodes", [])
        target = nodes[op["target_node_id"]]
        existing_children = target.get("children", []) or []
        for idx, child in enumerate(existing_children):
            add_tombstone(child["ref"], op["target_node_id"], existing_children, idx, op)
        target["children"] = [{"ref": n["id"]} for n in payload_nodes]
        for n in payload_nodes:
            ensure_node(n)
            record_created_by(n, op)
            parent_by_child[n["id"]] = op["target_node_id"]

    def update_node_fields(op):
        node = nodes[op["target_node_id"]]
        update_fields = op.get("update_fields", {})
        for key, value in update_fields.items():
            node[key] = value
        record_modified_by(node, op)

    def patch_text(op):
        node = nodes[op["target_node_id"]]
        text = node.get("text", "")
        for p in op.get("text_patches", []):
            action = p["action"]
            anchor = p.get("anchor_text")
            match_text = p.get("match_text")
            occurrence = p.get("occurrence", 1)
            insert_text = p.get("insert_text", "")

            if action in ("insert_after", "insert_before"):
                if not anchor:
                    raise ValueError("anchor_text required for insert actions")
                start = 0
                idx = -1
                for _ in range(occurrence):
                    idx = text.find(anchor, start)
                    if idx == -1:
                        break
                    start = idx + len(anchor)
                if idx == -1:
                    continue
                insert_at = idx + len(anchor) if action == "insert_after" else idx
                text = text[:insert_at] + insert_text + text[insert_at:]
            elif action == "replace_range":
                if not match_text:
                    raise ValueError("match_text required for replace_range")
                start = 0
                idx = -1
                for _ in range(occurrence):
                    idx = text.find(match_text, start)
                    if idx == -1:
                        break
                    start = idx + len(match_text)
                if idx == -1:
                    continue
                text = text[:idx] + insert_text + text[idx + len(match_text):]
            elif action == "delete_range":
                if not match_text:
                    raise ValueError("match_text required for delete_range")
                start = 0
                idx = -1
                for _ in range(occurrence):
                    idx = text.find(match_text, start)
                    if idx == -1:
                        break
                    start = idx + len(match_text)
                if idx == -1:
                    continue
                text = text[:idx] + text[idx + len(match_text):]
            else:
                raise ValueError(f"Unsupported patch action: {action}")
        node["text"] = text
        record_modified_by(node, op)

    def append_coverage_entry(op):
        scope = op.get("scope") or {}
        entry = {
            "action": op.get("op_type") or "other",
            "source_instrument_id": amend_instrument.get("id"),
            "source_op_id": op.get("op_id"),
        }
        effective_at = op.get("effective_at") or amend_instrument.get("effective_at")
        if effective_at:
            entry["effective_at"] = effective_at
        for key in (
            "scope_kind",
            "phases",
            "phase_scope",
            "plat_refs",
            "parcel_ids",
            "lot_ids",
            "lot_refs",
            "legal_description",
        ):
            if key in scope and scope[key] is not None:
                entry[key] = scope[key]
        if op.get("notes"):
            entry["notes"] = op.get("notes")

        coverage = instrument.get("coverage")
        if coverage is None:
            coverage = []
            instrument["coverage"] = coverage
        for existing in coverage:
            if (
                existing.get("source_instrument_id") == entry["source_instrument_id"]
                and existing.get("source_op_id") == entry.get("source_op_id")
            ):
                return
        if entry in coverage:
            return
        coverage.append(entry)

    def annex_property(op):
        append_coverage_entry(op)

    def deannex_property(op):
        append_coverage_entry(op)

    def append_declarant_entry(op):
        parties = op.get("parties") or {}
        name = (
            parties.get("assignee")
            or parties.get("grantee")
            or parties.get("declarant")
            or parties.get("assignor")
            or parties.get("grantor")
        )
        if not name:
            return
        entry = {
            "name": name,
            "role": "declarant",
            "source_instrument_id": amend_instrument.get("id"),
            "source_op_id": op.get("op_id"),
        }
        effective_at = op.get("effective_at") or amend_instrument.get("effective_at")
        if effective_at:
            entry["effective_at"] = effective_at
        if op.get("notes"):
            entry["notes"] = op.get("notes")

        history = instrument.get("declarant_history")
        if history is None:
            history = []
            instrument["declarant_history"] = history
        for existing in history:
            if (
                existing.get("source_instrument_id") == entry["source_instrument_id"]
                and existing.get("source_op_id") == entry.get("source_op_id")
            ):
                instrument["current_declarant"] = existing
                return
        history.append(entry)
        instrument["current_declarant"] = entry

    def assign_declarant_rights(op):
        append_declarant_entry(op)

    def update_incorporation(op):
        inc = op.get("incorporation") or {}
        exhibit_label = inc.get("exhibit_label")
        prev_id = inc.get("previous_payload_instrument_id")
        new_id = inc.get("new_payload_instrument_id")
        if not new_id or not exhibit_label:
            return

        incorporations = base_data.get("incorporations") or []
        updated_any = False
        for item in incorporations:
            if exhibit_label and item.get("exhibit_label") != exhibit_label:
                continue
            if prev_id and item.get("instrument_id") != prev_id:
                continue
            if item.get("instrument_id") == new_id:
                updated_any = True
                continue
            item["instrument_id"] = new_id
            item.pop("base_doc_id", None)
            updated_any = True

        if updated_any:
            base_data["incorporations"] = incorporations

        # Update exhibit_ref nodes for consistent metadata
        if not content.get("nodes"):
            return
        for node in content["nodes"]:
            if node.get("type") != "exhibit":
                continue
            if exhibit_label and node.get("label") != exhibit_label:
                continue
            meta = node.get("meta") or {}
            ex_ref = meta.get("exhibit_ref") or {}
            if prev_id and ex_ref.get("instrument_id") != prev_id:
                continue
            if ex_ref.get("instrument_id") == new_id:
                continue
            ex_ref["instrument_id"] = new_id
            ex_ref.pop("base_doc_id", None)
            meta["exhibit_ref"] = ex_ref
            node["meta"] = meta

    op_handlers = {
        "insert_children": insert_children,
        "delete_node": delete_node,
        "delete_children": delete_children,
        "replace_children": replace_children,
        "update_node_fields": update_node_fields,
        "patch_text": patch_text,
        "annex_property": annex_property,
        "deannex_property": deannex_property,
        "assign_declarant_rights": assign_declarant_rights,
        "update_incorporation": update_incorporation,
    }

    for op in amend_data.get("operations", []):
        op_type = op.get("op_type")
        handler = op_handlers.get(op_type)
        if not handler:
            raise ValueError(f"Unsupported op_type: {op_type}")
        handler(op)

    content["nodes"] = list(nodes.values())
    if tombstones:
        content_meta["tombstones"] = tombstones
        content["meta"] = content_meta
    base_data["content"] = content
    base_data["instrument"] = instrument
    return base_data


def main():
    parser = argparse.ArgumentParser(description="Apply amendment operations to a base instrument JSON.")
    parser.add_argument("base", help="Path to base JSON file.")
    parser.add_argument("amendment", help="Path to amendment JSON file containing operations.")
    parser.add_argument("output", help="Path to write the modified JSON.")
    args = parser.parse_args()

    base_path = Path(args.base)
    amend_path = Path(args.amendment)
    out_path = Path(args.output)

    base_data = load_json(base_path)
    amend_data = load_json(amend_path)
    updated = apply_operations(base_data, amend_data)
    out_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
