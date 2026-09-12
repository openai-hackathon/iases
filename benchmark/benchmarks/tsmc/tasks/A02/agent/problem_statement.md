# A02 — Retests are counted repeatedly in lot summaries

Retest records for one wafer are counted as multiple wafers, distorting the denominator and pass ratio. Fix latest-valid-test analysis for unordered inputs, retests and an explicit timestamp tie-break.

## Acceptance
Fix the code so the public contract holds for all valid inputs while preserving existing correct behavior. Submit a runnable code patch; handwritten outputs, data edits and a final text answer do not replace a repair.

## Reproduction
```bash
python -m fabops --input data/request.json
python -m pytest -q tests
```
The current tests contain known failures. Compare public `data/expected.json` and read `docs/contract.md`. You may add regression tests. Evaluation uses only the frozen submitted patch; hidden-test feedback is not exposed for iterative agent repair.

## Allowed changes
You may modify regular `.py` files under `fabops/` and add `tests/test_agent_*.py`. Do not modify original data, public contracts, existing public tests, pytest configuration or the grader. New external dependencies, network access, background processes and reads outside the workspace are not allowed.

This is a synthetic software issue and does not control physical equipment.
