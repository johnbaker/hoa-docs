# Rendering (Generated HTML)

This repo includes a simple HTML preview renderer for instrument JSON:
- `scripts/render_json_to_html.py` takes a JSON source and writes a standalone HTML file.
- It is intended for local inspection, not production UI output.

## What the preview renderer handles
- Structural nodes: `article`, `section`, `subsection`, `exhibit`, `heading`
- Content nodes: `paragraph`, `list`, `list_item`, `table`
- Table headers and body rows (when provided)
- `meta.note` (rendered as a callout)
- `meta.indent_level` (adds left margin for paragraphs/list items)

## What it does not handle (yet)
- `meta.render_hint` styles
- `meta.pdf_dest` / `meta.pdf_refs` facsimile navigation
- `meta.citations` / `meta.source_ranges`
- `meta.provenance` and `content.meta.tombstones` (UI uses these for amendment badges and deleted-section placeholders)
- Bundle-aware rendering (CC&R + exhibits)

If you update the node schema, align this doc with the renderer or note the gap here.
