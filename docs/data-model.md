# Data model

## Canonical source content (editable)
Each recorded item (instrument) is stored as structured JSON:
- `instrument` metadata
- `content` tree (nodes) when text is available
- optional `operations` describing what the instrument does (for snapshot generation)
- optional `incorporations` describing exhibits/attachments incorporated by reference

See schema:
- `schemas/instrument-document.schema.json`

## Operation types
Operations allow amendments to reference only amendment text without restating base text.
The schema supports the following `op_type` values:
- `replace_node`, `replace_children`, `replace_entire_document`
- `insert_children`, `delete_node`, `delete_children`
- `patch_text`, `update_node_fields`
- `update_incorporation`
- `assign_declarant_rights`, `annex_property`, `deannex_property`
- `other`

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

### Helper script coverage
`scripts/apply_from.py` supports only: `insert_children`, `delete_node`, `delete_children`,
`replace_children`, `update_node_fields`, and `patch_text`. Other op types require custom handling.

### Operation source refs
Each operation may include `source_ref` to point back to the amendment clause that authorizes it.
This helps the UI link a change to the exact amendment text node (and optional PDF destination).

### Missing-text exhibits
If the corpus references an exhibit but the text is not available, create a stub instrument:
- `instrument.availability.has_text = false`
- `instrument.availability.reason = not_in_corpus`
- `content` may be omitted (or included as a minimal placeholder)

## Node metadata (selected)
Common optional `node.meta` fields in the schema:
- `render_hint` (style hints + `preserve_linebreaks`)
- `indent_level` (display indentation for nested content)
- `pdf_dest` / `pdf_refs` (facsimile navigation)
- `provenance` (snapshot edit lineage)
- `transcription` (OCR or normalization notes)
- `exhibit_ref` (links exhibit nodes to instruments/base docs)
- `citations`, `source_ranges`, `tags`, `note`

## Tombstones (deleted nodes)
Snapshots may include `content.meta.tombstones` to preserve deletion history for UI display.
Each tombstone records:
- `node_id` and `parent_node_id`
- placement (`position` plus `before_child_node_id`/`after_child_node_id` when applicable)
- `deleted_by_instrument_id` and `deleted_by_op_id`
Tombstones may also carry `source_ref` to link back to the amendment clause that deleted them.
Optional fields like `last_seen_version_id` or cached display info may be included by the generator.

## Generated artifacts (CI output)
### Snapshots
Snapshots are generated per base document at each as-of date and represent “effective text”.
They keep stable node ids where possible and attach provenance metadata.

### Chunks
Chunks are derived deterministically from snapshot trees and instrument trees:
- snapshot chunks: `representation = snapshot`
- instrument chunks: `representation = instrument`

Chunks are the unit indexed into Typesense for search, grouped back into documents/versions in the UI.
