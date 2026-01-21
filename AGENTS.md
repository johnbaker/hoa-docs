# AGENTS.md

This repository contains a version-aware document system that generates:
1) **Effective “as-of” snapshots** (Pattern B) for browsing/searching what applies at a given date
2) **Recorded instrument views** (amendments/annexations/assignments/etc.) for auditability
3) A **Typesense search index** hydrated by CI
4) A **static GitHub Pages site** that browses and searches the corpus

This file describes rules and workflows for humans and automated agents (CI, bots, LLM tools).

---

## Source of truth

✅ **Canonical content is structured JSON** under:
- `data/instruments/`

❌ Do not edit generated artifacts directly:
- `data/snapshots/` (generated)
- `dist/`, `site/`, `public/` (generated)
- `*.jsonl` exports (generated)
- `source/` reference for humans only!

❌ You must ignore the  `source/` folder and all of its contents, do not read or change data in here.

If something looks wrong in snapshots or search results, fix the underlying instrument JSON or add a patch in `data/overrides/`.

---

## Data model

- Each recorded item is an **Instrument** (declaration, amendment, assignment, etc.).
- Each instrument has:
  - `instrument` metadata
  - optional `operations` (used to build snapshots)
  - optional `incorporations` (exhibits/attachments)
  - `content` tree (nodes), unless the text is missing

Exhibits are first-class base documents (e.g., `bylaws`, `dev_guidelines`) and may be incorporated by reference.

Missing exhibits must be represented explicitly with:
- `instrument.availability.has_text = false`
- `instrument.availability.reason = not_in_corpus`
No missing text should ever be inferred or invented.

Schemas:
- `schemas/instrument-document.schema.json`
- `schemas/node.schema.json`

---

## Build pipeline (high level)

CI (GitHub Actions) runs on main updates and:
1) Validates JSON against schema
2) Builds snapshot versions (`snapshots.json` / snapshot trees)
3) Chunks both:
   - snapshots (representation=`snapshot`)
   - instruments (representation=`instrument`)
4) Imports metadata + chunks into Typesense
5) Builds GitHub Pages site assets

The pipeline must be deterministic: the same inputs produce the same outputs.

---

## Editing workflow (recommended)

1) Edit / add files under `data/instruments/`
2) Run local validation + build
3) Commit changes to instrument JSON (and overrides if needed)
4) Let CI regenerate snapshots/chunks and reindex Typesense

If an edit changes node IDs, it can break deep links and amendment targeting.
Prefer stable node ids (logical ids) and avoid renaming unless necessary.

---

## Overrides

Use `data/overrides/` only for non-substantive corrections such as:
- anchors
- tags
- minor heading_path fixes
- suppressing a chunk from UI

Do not use overrides to materially change the meaning of legal text.
Material text changes belong in instrument JSON (with a clear audit trail).

---

## Search behavior

Default UI searches snapshot text (latest as-of) and falls back to prior versions if needed.
The UI also shows "Changes that mention this" from recorded instruments.

When a query only matches prior versions, results must be labeled **Historical** and show the matching as-of date.

---

## Coding & automation guidelines

- Prefer pure functions and deterministic output for build scripts.
- Any agent/tool that modifies `data/instruments/` must:
  - validate against schema
  - preserve node id stability when possible
  - keep `instrument.recorded_at` and `instrument.instrument_kind` accurate
- Avoid large refactors that touch many node ids unless explicitly required.

---

## Security & privacy

Do not add private homeowner data, emails, phone numbers, or addresses beyond what appears in recorded public instruments.

---

## Questions

If you're unsure whether to treat a document as:
- an instrument,
- a snapshot change-point,
- an exhibit,
- or a procedural operation,
prefer to add it as a separate instrument and link it via `operations` / `incorporations`.

---

## Instrument Generation Rules

When asked to generate intrument json, use the following rules:
One small note for Codex usage (so it generates correctly)
- Never split paragraphs.
- Prefer paragraph.label for same-line labels: (a), A., SECTION 1. when inline.
- Always create proper section nodes for TOC/anchors, even if the PDF is inline.
- Skip facsimile layout features; optionally include meta.pdf_refs later.
