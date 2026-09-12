# Public behavior contract

Reconstruct exact hydraulic analytics at each recorded-time frontier and emit a
compensating publication changelog. This is a bounded synthetic streaming protocol
inspired by multirate hydraulic measurements and manufacturing clock/data provenance;
it is not a claim that the source dataset has missing data or these faults.

samples contains full replacement versions:
{id,revision,recorded,channel,epoch,t,raw,valid,deleted}. calibrations contains versions:
{id,revision,recorded,channel,start,end,gain,offset,deleted}. channel is pressure or flow.
queries is a nondecreasing list of inclusive recorded-time cutoffs. For EACH query and
each version list, exclude recorded>asof FIRST, select greatest revision per identity,
then remove deleted identities. Revisions are positive integers; (id,revision) is unique
per list; input/recorded order need not agree with revision order. Corrections can change
every other field. An invalid sample remains an adjacency barrier; deletion removes it.

clocks has one fixed map per (channel,epoch): {channel,epoch,local_origin,global_origin,rate}.
Factory time = global_origin + (t-local_origin)*rate, with rate>0. Group samples by channel
AND epoch, sort by local t, and consider ONLY adjacent pairs. Never bridge epoch resets.
Keep a pair only when both valid and factory-time width<=max_gap[channel]. Its raw value
varies linearly between endpoints. There is no extrapolation or hold-last-value support.
Selected sample timestamps are unique per group. Different epoch spans of a channel do
not overlap (touching is allowed). All referenced clock maps exist.

Selected calibration intervals [start,end) are in FACTORY time and do not overlap for
a channel. They may have gaps. Split raw linear support at these boundaries; interpolate
RAW value at each intersection endpoint, then apply raw*gain+offset under that interval.
A calibration step is a discontinuity, not a ramp between differently calibrated knots.
Missing calibration means unsupported time. All times, raw values, gains, offsets,
max_gap and min_coverage are exact integer/decimal/rational strings, except recorded,
revision and queries which are integers. Valid calibrated values are nonnegative.

windows contains unique {id,start,end}, start<end; windows may overlap. Intersect pressure
and flow supports within each window, splitting at knots/boundaries of BOTH channels.
coverage is JOINT supported duration / full window duration. Accept only if duration>0
and coverage>=min_coverage (0<=minimum<=1). Integrate flow (litres/minute) over supported
seconds and divide by 60 to get volume (litres). Integrate pressure (bar) times flow and
divide by 600 to get work (kJ). The product of two linear signals is quadratic and must
be integrated exactly, not by trapezoids of endpoint products. For rejected windows
volume and work are None; still report exact coverage.

A window value is {id,coverage,accepted,volume,work}. Numeric outputs are reduced fraction
strings, or integer strings when denominator is 1 (fractions.Fraction representation).
For each query return {windows:[values sorted by id],changes:[events]}. On the first
query emit {op:'upsert',value:window_value} for each window. On later queries, compare
derived values: for each changed window emit {op:'retract',value:previous_value} followed
by its upsert. Unchanged values emit nothing, including equal-value source revisions.
Process changed windows in id order; rejected values also participate in this protocol.
Windows are fixed across queries. Return results in query order, without changing input.
At most 100 versions per source list, 20 windows and 20 queries are supplied. Full
recomputation is permitted; no unmentioned persistence or performance requirement applies.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
