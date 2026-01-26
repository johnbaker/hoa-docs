#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_DIR = ROOT / "tmp" / "hoa-prototype" / "data" / "instruments"
MANIFEST_PATH = INSTRUMENT_DIR / "manifest.json"


def main() -> int:
    if not INSTRUMENT_DIR.exists():
        raise SystemExit(f"Instrument dir not found: {INSTRUMENT_DIR}")

    files = sorted(
        p.name
        for p in INSTRUMENT_DIR.glob("*.json")
        if p.name != "manifest.json"
    )
    MANIFEST_PATH.write_text(json.dumps({"files": files}, indent=2), encoding="ascii")
    print(f"Wrote {MANIFEST_PATH} with {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
