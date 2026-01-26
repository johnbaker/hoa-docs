#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_DIR = ROOT / "tmp" / "hoa-prototype" / "data" / "instruments"
INDEX_PATH = INSTRUMENT_DIR / "index.json"


def main() -> int:
    if not INSTRUMENT_DIR.exists():
        raise SystemExit(f"Instrument dir not found: {INSTRUMENT_DIR}")

    index = {}
    for path in sorted(INSTRUMENT_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text())
        inst = data.get("instrument")
        if not inst:
            continue
        index[inst.get("id")] = inst

    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="ascii")
    print(f"Wrote {INDEX_PATH} with {len(index)} instruments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
