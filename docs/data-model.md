# Data model

## Canonical source content (editable)
Each recorded item (instrument) is stored as structured JSON:
- `instrument` metadata
- `content` tree (nodes) when text is available
- optional `operations` describing what the instrument does (for snapshot generation)
- optional `incorporations` describing exhibits/attachments incorporated by reference

See schema:
- `schemas/instrument-document.schema.json`

## Operation extensions (proposed)
These op types allow amendments to reference only amendment text without restating base text:

### patch_text
Applies targeted text edits to an existing node by anchoring to existing text.
Use this for "insert after X", "insert before X", or simple replace/delete cases.
Use `text_patches` with an `anchor_text` or `match_text` and an `occurrence` index.

### update_node_fields
Updates node metadata fields such as `title` or `label` without replacing text.
Use this for "change the title to read ..." or "label the first paragraph as (a)."

### target_selector
Optional selector used when stable `target_node_id` is unknown.
Supports targeting by `heading_text` or `section_path` with an `occurrence` index.

### incorporation updates
`update_incorporation` supports `previous_incorporated_base_doc_id` so changes are explicit
when replacing an exhibit with a new incorporated base document or new payload instrument.

### Missing-text exhibits
If the corpus references an exhibit but the text is not available, create a stub instrument:
- `instrument.availability.has_text = false`
- `instrument.availability.reason = not_in_corpus`
- `content` may be omitted (or included as a minimal placeholder)

## Generated artifacts (CI output)
### Snapshots
Snapshots are generated per base document at each as-of date and represent “effective text”.
They keep stable node ids where possible and attach provenance metadata.

### Chunks
Chunks are derived deterministically from snapshot trees and instrument trees:
- snapshot chunks: `representation = snapshot`
- instrument chunks: `representation = instrument`

Chunks are the unit indexed into Typesense for search, grouped back into documents/versions in the UI.
