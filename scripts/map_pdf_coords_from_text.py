#!/usr/bin/env python3
"""Populate meta.pdf_dest with page/x/y by text matching against a PDF."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ascii_normalize(text: str) -> str:
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )

def normalize_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = ascii_normalize(text)
    text = re.sub(r"-\s+", "", text)
    return normalize_whitespace(text)


def simplify_text(text: str) -> str:
    text = normalize_text(text).lower()
    text = re.sub(r"[^a-z0-9\\s]", " ", text)
    return normalize_whitespace(text)


def build_snippets(text: str) -> List[str]:
    if not text:
        return []
    simplified = simplify_text(text)
    if not simplified:
        return []
    words = simplified.split()
    if not words:
        return []
    candidates = [" ".join(words)]
    for length in (12, 10, 8, 6, 4):
        if len(words) >= length:
            candidates.append(" ".join(words[:length]))
    for length in (2, 1):
        if len(words) >= length:
            candidates.append(" ".join(words[:length]))
    if len(words) > 14:
        candidates.append(" ".join(words[-10:]))
    seen = set()
    unique = []
    for snippet in candidates:
        if snippet in seen:
            continue
        seen.add(snippet)
        unique.append(snippet)
    return unique


def walk_nodes(root_ref: str, node_map: dict) -> Iterable[dict]:
    def walk(node_id: str) -> Iterable[dict]:
        node = node_map.get(node_id)
        if not node:
            return
        yield node
        for child in node.get("children", []) or []:
            ref = child.get("ref")
            if ref:
                yield from walk(ref)

    return walk(root_ref)


def node_text_for_match(node: dict) -> Optional[str]:
    node_type = node.get("type")
    if node_type in {"heading"}:
        return node.get("text") or None
    if node_type in {"section", "subsection"}:
        return node.get("title") or None
    if node_type in {"paragraph", "list_item"}:
        return node.get("text") or None
    return None


def build_page_index(pdf_path: Path) -> List[dict]:
    pages = []
    for layout in extract_pages(pdf_path):
        lines = []
        for element in layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    if isinstance(text_line, LTTextLine):
                        line_text = normalize_text(text_line.get_text())
                        if not line_text:
                            continue
                        lines.append(
                            {
                                "text": line_text,
                                "simple": simplify_text(line_text),
                                "bbox": text_line.bbox,
                            }
                        )
        lines.sort(key=lambda item: (-item["bbox"][3], item["bbox"][0]))
        pages.append(
            {
                "lines": lines,
            }
        )
    return pages


def find_match(pages, start_page: int, text: str) -> Optional[Tuple[int, float, float]]:
    snippets = build_snippets(text)
    if not snippets:
        return None
    for page_index in range(start_page, len(pages)):
        page = pages[page_index]
        lines = page["lines"]
        for i, line in enumerate(lines):
            line_simple = line["simple"]
            next_simple = ""
            if i + 1 < len(lines):
                next_simple = f"{line_simple} {lines[i + 1]['simple']}".strip()
            for snippet in snippets:
                if snippet and (snippet in line_simple or (next_simple and snippet in next_simple)):
                    x0, y0, x1, y1 = line["bbox"]
                    return page_index, x0, y1
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instrument",
        default="data/instruments/ccr-1999-05-27.json",
        help="Instrument JSON to update",
    )
    parser.add_argument(
        "--pdf",
        default="winston-hills-ccrs-and-amendments-complete-searchable-toc.pdf",
        help="PDF to search against",
    )
    args = parser.parse_args()

    instrument_path = Path(args.instrument)
    pdf_path = Path(args.pdf)

    instrument = load_json(instrument_path)
    content = instrument.get("content") or {}
    root_ref = content.get("root_ref")
    if not root_ref:
        raise SystemExit("Missing content.root_ref")
    nodes = content.get("nodes") or []
    node_map = {node.get("id"): node for node in nodes}

    pages = build_page_index(pdf_path)

    updated = 0
    missing = 0
    missing_nodes = []
    current_page = 0

    for node in walk_nodes(root_ref, node_map):
        text = node_text_for_match(node)
        if not text:
            continue
        match = find_match(pages, current_page, text)
        if not match:
            missing += 1
            if len(missing_nodes) < 50:
                missing_nodes.append(node.get("id", "unknown"))
            continue
        page_index, x, y = match
        current_page = page_index
        meta = node.get("meta") or {}
        pdf_dest = meta.get("pdf_dest") or {}
        pdf_dest.update(
            {
                "page": page_index + 1,
                "x": round(x, 3),
                "y": round(y, 3),
                "zoom": 0.0,
                "mode": "/XYZ",
            }
        )
        meta["pdf_dest"] = pdf_dest
        node["meta"] = meta
        updated += 1

    dump_json(instrument_path, instrument)

    print(f"Updated nodes: {updated}")
    print(f"Missing matches: {missing}")
    if missing_nodes:
        print("First missing node ids:")
        for node_id in missing_nodes:
            print(f" - {node_id}")


if __name__ == "__main__":
    main()
