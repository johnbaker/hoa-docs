# Admin app (Option A)

## Philosophy
- Canonical source-of-truth lives in repo JSON (`data/instruments/`).
- Admin app edits JSON via PRs (auditable) and triggers CI rebuild/reindex.
- Avoid editing Typesense directly.

## MVP features
- Browse instruments and their node trees
- Tree editor: add/move/delete nodes; edit labels/titles/text
- Validation: duplicate ids, broken refs, inconsistent numbering
- Preview renderer (HTML/Markdown) for review
- Trigger workflow: rebuild snapshots, rebuild chunks, import Typesense

## Overrides (optional)
Use `data/overrides/` for non-substantive fixups:
- anchors, tags, suppress flags, heading_path corrections
