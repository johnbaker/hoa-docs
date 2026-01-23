# Transcription Conventions (Canonical JSON)

This repository stores governing/legal documents as structured JSON (not Markdown) under `data/instruments/`.
Markdown/HTML is generated from JSON.

## Golden rules

### 1) Do not invent or normalize away meaning
- Preserve the original wording.
- Do not “correct” typos or OCR artifacts in the canonical text unless explicitly tracked.

### 2) Preserve explicit paragraph boundaries
- A paragraph in the source document must map to a single `Node` of type `paragraph` (or `definition`, `list_item`).
- Do not split a paragraph into multiple nodes for chunking.
- Do not merge distinct paragraphs.

### 3) Headings and structure
- Articles: `type="article"` with children sections in order.
- Sections: `type="section"` with children paragraphs/items in order.
- Titles:
  - Prefer `article.title` and `section.title` when the source includes a title line.
  - If the PDF prints a heading and text on the same line (e.g., “SECTION 1. Owners. <text>”), store the heading as the section’s label/title, and store the remainder as the first child paragraph.

### 4) Inline labeled items on the same line
When label and text are on the same printed line (e.g., “(a) the right …”):
- Use a single `paragraph` node:
  - `type="paragraph"`
  - `label="(a)"` (or `label="A. Class A."`, etc.)
  - `text="<the remainder>"`

### 5) Lists
If the document contains structured numbered items (1st/2nd/3rd or 1./2./3.):
- Use `type="list"` with `type="list_item"` children where possible.
- If the original is just lettered paragraphs (A., B., (a), (b)), use labeled `paragraph` nodes (Rule #4).

### 6) OCR artifacts and corrections (recommended approach)
- Canonical text should stay verbatim.
- If you must record a correction, store:
  - verbatim text in `text`
  - the correction in metadata (`meta.transcription.note`), or in a separate override layer.

## Stable identifiers (important)
Use stable logical ids that do not change across snapshots:
- `node:ccr:article-3:sec-2`
- `node:ccr:article-3:sec-2:item-b`
- `node:ccr:article-1:sec-7:b:list-1:item-3`

Avoid embedding dates in node ids. Dates belong in instrument ids and snapshot ids.

## Markdown ingestion helper (scripts/parse_exhibit_md.py)
This helper converts a lightly-structured Markdown file into instrument JSON. Use it for
initial transcription or updates, but treat the JSON as the source of truth.

Supported conventions:
- Front matter header between `---` lines with `key: value` pairs (instrument metadata).
- `@exhibit <Label> @instrument_id <id> @base_doc_id <id>` to start a new exhibit node.
- `@epilog` to switch remaining paragraphs to the document root.
- `>>> <dest>` to attach `meta.pdf_dest.name` to the next node.
- `]]]` indentation markers to set `meta.indent_level` on the next node.
- `# Table <Label> #` to label the next Markdown table as a `table` node.
- List items support `Title :: text` to split `title` vs `text`.

If you add new shorthand to the parser, document it here.

### Facsimile jump behavior
If `meta.pdf_dest` exists:
- show “View in PDF” action next to the node (or on hover)
- clicking it sends `{ destName, nodeId }` to the pdf.js panel and navigates to the destination

If `meta.pdf_dest` is missing:
- optionally fall back to the closest ancestor with `meta.pdf_dest`, or page reference if available.
