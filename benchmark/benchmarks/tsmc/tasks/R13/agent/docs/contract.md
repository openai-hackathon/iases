# Public behavior contract

Repair the real asyncio SingleFlight.get(scope,key,loader) service. scope and key are
strings. Share exactly one running producer among callers with the same scope, key and
current scope generation (initially zero). The producer calls loader(scope,key,generation).
invalidate(scope) increments only that scope's generation. Existing waiters remain attached
to their old producer; later callers must use a fresh generation. Completed and failed
producers are not cached. One waiter cancellation must not cancel other waiters. When the
last waiter departs, immediately detach its entry and cancel its producer. A producer may
suppress cancellation and finish later; its retirement must not remove a replacement entry
for the same identity. Keep live producer tasks referenced and retrieve their exceptions.

run executes a deterministic command sequence with Event-controlled loaders. join has
unique waiter and job labels, scope, key, and optional resistant boolean. Each join offers
its job loader, but a joining follower never starts that loader. cancel names a waiter;
completed waiters are unaffected. invalidate names a scope. finish(job,value) releases a
job; finish(job,error=string) instead makes it raise ValueError. Finishing an unstarted job
is harmless. Commands settle runnable callbacks before the next command, with no positive
wall-clock sleeps. At the end return results keyed by waiter: {status:value,value:...},
{status:error,error:...}, {status:cancelled}, or {status:pending}; calls lists actually
started [job,scope,key,generation] in start order; cancellations lists producer jobs that
received cancellation; active is the number of registry entries before final cleanup.
Pending is allowed. Cleanup must finish without leaking tasks. There are at most 30
commands and eight simultaneous waiters. Preserve the input and the async public API.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
