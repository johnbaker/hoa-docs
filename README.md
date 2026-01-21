# Governing Document Search: Versioned Snapshots + Hybrid Search (Typesense)

This project builds a static web experience (GitHub Pages) for browsing and searching a corpus of governing/legal documents (e.g., declarations/CC&Rs, bylaws, guidelines, amendments, annexations, assignments, etc.) with strong support for **version history** and **amendment-aware results**.

## Problem this solves

Users frequently search using phrases that may:
- exist only in an older version of a document (wording removed or rewritten),
- exist in an exhibit incorporated by reference (e.g., bylaws, development guidelines),
- exist in a recorded amendment/assignment/annexation instrument rather than the “effective text”.

A normal fulltext index struggles to answer: “What does it say now?” while still making it easy to discover “What did it say then?”

## Key concept: Pattern B “As-of Snapshots”

We generate **consolidated snapshot versions** of base documents at meaningful change-points:

- `ccr@asof-1999-05-27`
- `ccr@asof-2002-02-28`
- `ccr@asof-2005-01-04`
- ...

Search defaults to the latest snapshot (“what applies today”), but the UI can:
- fall back to older snapshots when a query only matches historical wording,
- display matches grouped by version (“Found in prior versions: …”),
- link to diffs between snapshots.

## Documents vs Instruments

We model two parallel representations:

1) **Instruments**: recorded items as their own documents (declaration, amendment, assignment, annexation, etc.).  
   - These power auditability and “Changes that mention this”.
2) **Snapshots**: generated effective text at each as-of date.
   - These power “what applies as of X” searching and browsing.

## Exhibits

Exhibits incorporated by reference (e.g., “Exhibit C – Bylaws”) are treated as first-class base documents with their own snapshots. CC&R snapshots can be viewed as a **bundle** that includes relevant exhibit snapshots.

If an exhibit’s original text is missing, we model it explicitly as a referenced-but-unavailable stub (no invented text).

## Outputs

CI produces:
- Static GitHub Pages site for browsing the corpus and search UI
- Typesense collections for:
  - document/instrument metadata
  - chunk-level hybrid search (keyword + optional vector)

## Source of truth

Canonical content is edited in structured JSON under `data/instruments/`. Markdown/HTML is generated from JSON as a build artifact (not edited directly).

See:
- `docs/overview.md`
- `docs/data-model.md`
- `docs/indexing-and-search.md`
- `docs/ui-mockups.md`
- `docs/admin-app.md`

## Ignore Folder

The `source/` folder should be ignored and only contains information for a human and will go away once we migrate.