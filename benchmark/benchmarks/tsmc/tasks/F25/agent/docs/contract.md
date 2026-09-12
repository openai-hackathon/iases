# Public behavior contract

Diagnose a production event log against a finite, weighted, capacity-bounded Petri
net. capacities maps named places to positive limits. initial and final are token
mappings; absent places have zero tokens. Each transition has unique nonempty id,
label (nonempty activity string or null), consume and produce maps of positive
integer weights, and positive integer model_cost. A firing requires all consumed
tokens and must respect capacities AFTER atomic consumption and production.

groups is a list of nonempty observation groups. Each event has a globally unique
nonempty id, nonempty activity label, and positive integer skip_cost. Groups must
be consumed in listed order, but events WITHIN a group have no known order and may
be consumed in any permutation. Array order inside groups is only serialization.
A synchronous move consumes one currently available event and fires a transition
with the same non-null label, at zero cost. A log move consumes an available event
without firing anything, at that event's skip_cost. A model move fires any enabled
transition, including one with a visible label, without consuming an event, at its
model_cost. Model moves can occur before, inside, between and after groups.

A complete alignment consumes every event exactly once and reaches exactly final,
including all leftover places. Minimize total cost globally, then number of moves,
then the lexicographic sequence of move keys (kind,event_id,transition_id), where
kinds are the literal strings log/model/sync and a missing identifier is the empty
string. Return accepted, cost, alignment, log_moves, model_moves and synchronous_moves.
Each alignment row has kind, event and transition; missing identifiers are null in
the output. An impossible alignment returns accepted=false, cost=null, alignment=[],
and all three counts zero. An already complete empty alignment is accepted at cost 0.
Cycles, duplicate activity labels, parallel tokens, weighted self loops and globally
cheaper explanations requiring a locally more expensive step are valid.

At most six places, each capacity <=3; at most twelve transitions; at most ten
events total and four per group. The reachable marking set has at most 256 members.
Costs are integers 1..1000. Runtime must handle this bounded domain without enumerating
arbitrarily long firing histories or all interleavings of repeated cycles. A valid
input need not have a solution. Do not mutate the request while exploring alternatives.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
