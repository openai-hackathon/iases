# Submission acceptance
1. Preserve the public API, output schema and CLI; fix behavior for every input satisfying the data contract.
2. You may change the algorithm. Matching the reference implementation or a particular tool-call order is not required.
3. Do not hardcode public answers, modify fixed tests, rewrite data, or make all inputs succeed or fail unconditionally.
4. Analytics tasks must work on another input dataset; a static report is not a repair.
5. Reliability tasks must retain fault hooks. Do not swallow all exceptions or remove concurrency or cancellation support.
6. Submit a patch to the code in `fabops/`. You may add `tests/test_agent_*.py`, which do not replace the required suites.
