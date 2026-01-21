# UI mockups (high-level)

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

## Search page
Header:
- Search input
- Mode toggle: Current (snapshot) / Recorded Instruments
- As-of selector (snapshot mode)
- Filters (doc type, instrument kind, status)

Results:
- Current results grouped by `version_id` (usually one)
- If no current results:
  - banner: “No matches in current version. Found matches in prior versions: …”
  - show groups per as-of version
- Section: “Changes that mention this” (instrument hits grouped by instrument id)

## Document viewer
- Top bar: Title + As-of selector + Diff
- Tabs: CC&R, Exhibit C (Bylaws), Exhibit D (Guidelines) if included
- TOC left, content center, context panel right (metadata, provenance, related instruments)
- If an exhibit is missing:
  - show “Referenced but text unavailable” with links to later available versions
