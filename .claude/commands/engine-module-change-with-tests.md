---
name: engine-module-change-with-tests
description: Workflow command scaffold for engine-module-change-with-tests in hs-net.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /engine-module-change-with-tests

Use this workflow when working on **engine-module-change-with-tests** in `hs-net`.

## Goal

Modifies or adds engine modules, often for dependency handling or lazy loading, and updates or adds corresponding tests.

## Common Files

- `src/hs_net/engines/aiohttp_engine.py`
- `src/hs_net/engines/curl_cffi_engine.py`
- `src/hs_net/engines/requests_engine.py`
- `src/hs_net/engines/requests_go_engine.py`
- `src/hs_net/client.py`
- `src/hs_net/sync_client.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Modify one or more engine modules (e.g., aiohttp_engine.py, requests_engine.py).
- Update client.py and/or sync_client.py to reflect engine changes.
- Update or create tests related to engine behavior.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.