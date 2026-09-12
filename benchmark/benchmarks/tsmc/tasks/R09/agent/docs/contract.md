# Public behavior contract

Return mono_end-mono_start seconds using monotonic timestamps. Those timestamps are finite and nondecreasing. wall_start/wall_end are diagnostic civil times and may jump in either direction.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
