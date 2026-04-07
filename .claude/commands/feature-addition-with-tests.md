---
name: feature-addition-with-tests
description: Workflow command scaffold for feature-addition-with-tests in hs-net.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /feature-addition-with-tests

Use this workflow when working on **feature-addition-with-tests** in `hs-net`.

## Goal

Implements a new feature or API (e.g., exception, shortcut function), updates the main module, adds or updates a dedicated module, and creates/updates corresponding tests.

## Common Files

- `src/hs_net/__init__.py`
- `src/hs_net/exceptions.py`
- `src/hs_net/shortcuts.py`
- `tests/test_exceptions.py`
- `tests/test_shortcuts.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement feature in a new or existing module (e.g., exceptions.py, shortcuts.py).
- Update __init__.py to expose or register the new feature.
- Add or update tests for the new feature.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.