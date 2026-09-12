# Public behavior contract

Process commands against a real SQLite file. A command has op=execute, scope=[plant,cell]
(two strings), opaque key, expected nonnegative integer revision, arbitrary finite JSON
value, optional transport metadata, and optional crash boolean. Each scope initially has
revision zero and value null. The idempotency namespace is the complete scope plus key.
For a previously unseen key, compare expected with the current scope revision: equality
applies value and increments the revision, returning {status:applied,revision,value};
mismatch returns {status:precondition,revision,value} with the unchanged current state.
Cache BOTH outcomes. Repeating a key with the same expected revision and equivalent value
returns the original outcome, regardless of subsequent state changes. Reusing that key
with a different expected revision or nonequivalent value returns {status:conflict} and
changes nothing. Transport metadata and crash flags are not part of semantic identity.

Values are equivalent recursively: object key order is irrelevant; array order is
significant; finite numbers compare by decimal value (1 equals 1.0, negative zero equals
zero); booleans are distinct from numbers; strings retain exact content; null is distinct
from every other value. Keys inside objects are strings; no NaN or infinity occurs.
Preserve the first accepted value's original representation in cached replies. A crash
on a previously unseen command happens after computing/updating state but before recording
the outcome; return {status:crashed}, with neither state nor receipt surviving. A retry of
an already cached command does not enter that crash point. restart closes and reopens the
same SQLite file and returns {status:restarted}. Return results in command order, states
as sorted [[plant,cell],revision,value] rows for scopes that have had successful updates,
and receipts as the number of cached keys, including precondition failures. Failed
preconditions do not create state rows. Bound: at most 30 commands and eight scopes.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
