# Public behavior contract

Reconstruct production operation lifecycles from out-of-order events. Each event has
id, kind (start or complete), case, activity, resource, integer time, and optionally
run (a string operation correlation id or null). Transport retries with identical id
and complete identical content are one event. Reusing an id with different content
raises ValueError. Distinct ids at the same timestamp remain distinct operations.
There are at most six distinct starts and six distinct completions after deduplication.

A start can pair with a completion exactly when case, activity and resource all match,
start.time <= complete.time, and the run ids agree if both are non-null. A missing or
null run id is unknown and compatible with any run id. Each event occurs in at most
one pair. Consider ALL globally maximum-cardinality matchings, without imposing FIFO,
nearest-time, duration minimization, or an arbitrary greedy tie break. Unmatched events
are allowed. Every matching is a set of (start id,completion id) pairs; duplicates from
transport retries do not count as separate interpretations.

Return matched (maximum pair count), alternatives (number of distinct maximum matchings),
certain_pairs (intersection across every maximum matching, sorted lexicographically,
encoded as two-element lists), certain_unmatched (sorted event ids unmatched in EVERY
maximum matching), and duration_bounds [minimum,maximum] of the total paired durations
across those matchings. An event that is unmatched in some interpretations but paired
in others is not certainly unmatched. With no possible pairs there is one empty
matching, and total duration is zero. Different resources or cases never correlate.
Inputs must remain unchanged, including when duplicate-id conflicts are rejected.
Additional global evidence changes WHICH interpretations are eligible before
maximizing cardinality. capacities optionally maps resources to nonnegative
integer capacities (unlisted resources are unconstrained). Each start may have
integer units>=1, default 1. A selected lifecycle reserves its start's units
on [start.time,complete.time); zero-duration pairs use no capacity. Unmatched
events reserve nothing. All simultaneous selected lifecycles share this capacity.
duration_limits optionally maps an activity to inclusive [minimum,maximum]
nonnegative integer duration bounds. Unlisted activities have no extra bound.

route is a list of [earlier activity,later activity] edges in an acyclic graph.
For every selected earlier/later pair of lifecycles in the SAME case, the earlier
completion must be <= the later start, even on different resources. An absent
activity is allowed. coupled is a list of pairs of existing event ids: either
both events must be paired somewhere in an interpretation, or both unmatched.
These constraints may require choosing a SMALLER matching than unconstrained
bipartite maximum matching. Optimize only among globally feasible interpretations;
filtering an already maximal set or pruning unfinished coupled evidence is wrong.
All omitted new fields default to {} or []. The empty interpretation is feasible.
Return the same five result fields, counting distinct pair sets, not schedules.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
