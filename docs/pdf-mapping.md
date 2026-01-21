# PDF Mapping (Facsimile Linkage)

If the original PDF is available, nodes may optionally include `meta.pdf_refs` to support:
- “jump to page” in pdf.js
- highlight rectangles that correspond to the node’s text

## pdf_refs format
Each `pdf_ref` includes:
- `doc_id`: which PDF (optional if 1:1 with instrument)
- `page`: 1-based page number
- `rect`: [x1, y1, x2, y2] coordinates in PDF space
- `coord_system`: "pdf_points" (default) or another declared system

This metadata is optional and can be added later without changing the text structure.

## Named destinations (preferred)

If the source PDF includes named destinations (outlines or explicit dest names),
each node may include a `pdf_dest` that can be used to jump in pdf.js without
needing bounding boxes.

### Why named destinations
- More stable than coordinates across render scales
- Often align to Article/Section headers and sometimes deeper list entities
- Enables precise “Jump to facsimile” from Reading View anchors

### Node-level requirement
Each node SHOULD support at least one jump target:
- Prefer `meta.pdf_dest.name` when available.
- If the PDF does not have a destination for a node, fall back to:
  - nearest ancestor node’s destination, or
  - a page-only reference.
