# Indexing and search

## Collections
- `wh_documents`: instrument metadata and snapshot metadata for browsing/timelines.
- `wh_chunks`: chunk-level search across snapshots + instruments.

## Default search behavior (Pattern B)
1) Query latest snapshot (current).
2) If no hits, query older snapshots (grouped by `version_id`).
3) Query instruments for “Changes that mention this”.

## Bundles (CC&R + exhibits)
When viewing CC&R as-of a date, the UI loads a bundle describing which snapshot versions to include:
- CC&R snapshot version_id
- Exhibit snapshots (bylaws/guidelines) version_ids

A “bundle search” filters by `version_id IN [ ...bundle... ]` for snapshots.
