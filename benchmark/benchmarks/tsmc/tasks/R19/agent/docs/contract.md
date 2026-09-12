# Public behavior contract

Process start(id), finish(id) and shutdown events. Initially open; starts accepted only while open. shutdown moves to draining if requests are active, otherwise closed. Existing requests may finish while draining; the last finish closes. Repeated shutdown and unknown finishes are harmless. ids on start are unique. Return accepted start ids, completed ids, sorted active ids and state.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
