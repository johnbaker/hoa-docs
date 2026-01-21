# Overview

## Goals
- Provide an easy-to-browse static website (GitHub Pages) to read documents and navigate versions.
- Provide fast, high-quality fulltext + hybrid search using Typesense.
- Support:
  - “Current” (latest snapshot) reading by default
  - explicit “as-of date” selection (Pattern B)
  - historical-only matches when wording was removed or changed
  - a clear audit trail via recorded instruments (amendments, annexations, assignments)
  - exhibits (bylaws, guidelines) surfaced alongside CC&R

## Non-goals
- This project does not attempt to be a full legal drafting tool.
- It does not infer missing text or “fill gaps” in exhibits.
- It does not decide legal enforceability; it only presents document text and relationships.

## Primary UX flows
1. Search → see “current results” (latest snapshot).
2. If no current results → show “found in prior versions” grouped by as-of.
3. Show “Changes that mention this” from instrument text.
4. Open viewer → deep-link to clause; optionally diff against another version.
5. View CC&R bundle → tabs for CC&R + exhibits effective as-of date.
