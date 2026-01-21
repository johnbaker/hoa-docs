# Data model

## Canonical source content (editable)
Each recorded item (instrument) is stored as structured JSON:
- `instrument` metadata
- `content` tree (nodes) when text is available
- optional `operations` describing what the instrument does (for snapshot generation)
- optional `incorporations` describing exhibits/attachments incorporated by reference

See schema:
- `schemas/instrument-document.schema.json`

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
