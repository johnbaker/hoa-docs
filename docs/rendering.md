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
