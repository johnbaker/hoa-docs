#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def apply_operations(base_data, amend_data):
    content = base_data["content"]
    nodes = {n["id"]: n for n in content["nodes"]}

    parent_by_child = {}
    for node in list(nodes.values()):
        for child in node.get("children", []) or []:
            parent_by_child[child["ref"]] = node["id"]

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
            parent_by_child[n["id"]] = op["target_node_id"]

    def delete_node(op):
        target_node_id = op["target_node_id"]
        parent_id = parent_by_child.get(target_node_id)
        if parent_id:
            remove_child(parent_id, target_node_id)

    def delete_children(op):
        target = nodes[op["target_node_id"]]
        target["children"] = []

    def replace_children(op):
        payload_nodes = op.get("payload_nodes", [])
        target = nodes[op["target_node_id"]]
        target["children"] = [{"ref": n["id"]} for n in payload_nodes]
        for n in payload_nodes:
            ensure_node(n)
            parent_by_child[n["id"]] = op["target_node_id"]

    def update_node_fields(op):
        node = nodes[op["target_node_id"]]
        update_fields = op.get("update_fields", {})
        for key, value in update_fields.items():
            node[key] = value

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

    op_handlers = {
        "insert_children": insert_children,
        "delete_node": delete_node,
        "delete_children": delete_children,
        "replace_children": replace_children,
        "update_node_fields": update_node_fields,
        "patch_text": patch_text,
    }

    for op in amend_data.get("operations", []):
        op_type = op.get("op_type")
        handler = op_handlers.get(op_type)
        if not handler:
            raise ValueError(f"Unsupported op_type: {op_type}")
        handler(op)

    content["nodes"] = list(nodes.values())
    base_data["content"] = content
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
