#!/usr/bin/env python3
"""Add PDF page/x/y/zoom/mode coordinates to pdf_dest entries in an instrument JSON."""

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def normalize_key(name: str) -> str:
    if not name:
        return ""
    return name if name.startswith("/") else f"/{name}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instrument",
        default="data/instruments/ccr-1999-05-27.json",
        help="Instrument JSON to update",
    )
    parser.add_argument(
        "--dest-map",
        default="tmp/hoa-prototype/data/pdf-dest-map.json",
        help="PDF destination map JSON (name -> page/x/y)",
    )
    args = parser.parse_args()

    instrument_path = Path(args.instrument)
    dest_map_path = Path(args.dest_map)

    instrument = load_json(instrument_path)
    dest_map = load_json(dest_map_path)

    nodes = instrument.get("content", {}).get("nodes", [])
    updated = 0
    missing = 0

    for node in nodes:
        meta = node.get("meta") or {}
        pdf_dest = meta.get("pdf_dest")
        if not pdf_dest or not isinstance(pdf_dest, dict):
            continue
        name = pdf_dest.get("name")
        if not name:
            continue
        lookup_key = normalize_key(name)
        dest = dest_map.get(lookup_key)
        if not dest:
            missing += 1
            continue
        pdf_dest.update({
            "page": dest.get("page"),
            "x": dest.get("x"),
            "y": dest.get("y"),
            "zoom": dest.get("zoom"),
            "mode": dest.get("mode"),
        })
        meta["pdf_dest"] = pdf_dest
        node["meta"] = meta
        updated += 1

    dump_json(instrument_path, instrument)

    print(f"Updated {updated} nodes with pdf_dest coordinates.")
    if missing:
        print(f"Missing destinations: {missing}")


if __name__ == "__main__":
    main()
