# A18: Multirate sensor alignment accepts readings outside tolerance

A synthetic manufacturing service violates its documented contract. Diagnose the issue from the public examples and repair the implementation for all valid inputs.

Run `python -m pytest -q tests` and read `docs/contract.md`. Public tests include known baseline failures. Submit a unified code diff against the original commit.

Allowed changes: regular Python files under `fabops/` and new `tests/test_agent_*.py`. Preserve existing tests, data, documentation and configuration. No external dependencies, network access, background services, symlinks or grader hooks are allowed. The evaluator runs separately after submission; hidden feedback is not available during repair.

This is a synthetic software issue, not a real company's production incident.
