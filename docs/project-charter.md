# Project Charter

## Context
We are building a version-aware search and browsing experience for a corpus of governance/legal documents. These documents evolve over time via amendments and other recorded instruments. Users must be able to search the effective text as-of a date, while also discovering historical wording and the recorded instruments that created changes.

## Core requirements
- Canonical editable source is structured JSON (not Markdown).
- Deterministic node IDs for stable anchors and amendment targeting.
- Pattern B snapshots (“as-of”) generated in CI and indexed for default search.
- Instruments indexed separately for audit trail and “Changes that mention this”.
- Exhibits modeled as first-class base documents and surfaced alongside CC&R.
- Missing exhibits must be represented explicitly as referenced-but-unavailable (no fabricated text).

## Outputs
- GitHub Pages static site for browsing and search UI.
- Typesense hybrid search index hydrated by CI on repo updates.

## Key design choices
- Chunking is deterministic from structured nodes.
- Search results are chunk-level but grouped back to documents/versions for UI.
- UI supports current search + historical fallback + instrument mentions.
