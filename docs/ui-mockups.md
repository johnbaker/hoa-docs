# UI mockups (high-level)

See `docs/pdf-mapping.md` for facsimile linkage metadata (`meta.pdf_refs`, `meta.pdf_dest`).

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
