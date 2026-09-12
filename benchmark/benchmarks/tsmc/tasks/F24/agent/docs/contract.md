# Public behavior contract

Process edit(revision), approve(revision,role), revoke(role), and activate events. Required roles are unique strings. An edit selects a new revision and clears approvals. Approve counts only for the current revision and a required role; revoke clears that role. Activate updates active revision only if all required roles currently approve. Return activation booleans and active (initially None).

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
