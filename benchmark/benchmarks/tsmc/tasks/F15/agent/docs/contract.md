# Public behavior contract

route contains unique operation names. events are pass/fail booleans for the currently active operation. A pass advances; a failure retries it up to max_retries failures, and the next failure scraps the lot. Retry count resets on advancement. Ignore events after done/scrap. Return {state: active/done/scrap, step: active operation or None, retries: current operation failures}.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
