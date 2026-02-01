# Archived: openwebui legacy assets

## Archive Date
February 1, 2026

## What was moved here
- `deprecated/`: old Arena UI/API/benchmark utilities that are no longer used.
- `data-backups/`: historical JSONL backups from Arena experiments.

## Why archived
The active Arena implementation now lives in [src/arena](../../src/arena).
Legacy assets were retained for reference and recovery without cluttering the
active code path.

## Recovery
If needed, copy files back from this folder, but prefer the active paths in
`src/arena` and the compatibility wrappers in `src/openwebui`.
