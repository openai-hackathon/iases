# R04 Author notes

## Root cause
Cleanup exists only after a successful await job; errors/cancellation skip active decrement and semaphore.release.

## Reference fix
Wrap the callback in try/finally only after acquire succeeds. Do not enter cleanup before acquire, which could release another job's slot when a waiter is cancelled.

The reference implementation is not the only allowed solution. Grade public-contract behavior with tests; every hidden test corresponds to the public contract.

## Known scope
This is a small synthetic fixture. Codex/Qwen repair difficulty, tool-call counts and scheduling gains have not been measured.
