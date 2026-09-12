# Public behavior contract

Plan one nonpreemptive operation on a workstation. Times are integer minutes in a
shared absolute clock, not local dates. horizon=[start,end] has start<end. All
intervals are half-open [start,end); all supplied intervals have positive length.
open lists operating windows. Their UNION defines when the workstation operates;
overlapping or duplicate windows never add capacity. maintenance lists complete
closures whose UNION overrides operating windows. Windows may extend outside horizon.
capacity is a positive integer. jobs lists committed reservations with start, end
and positive integer units. Each job independently occupies its units; intersecting
reservations add, including identical records. Overbooked intervals have zero free
capacity. Jobs outside operating hours still exist but cannot make a closed interval
usable. Input order has no meaning.

Return profile as sorted maximal [start,end,free_units] segments covering the entire
horizon, including closed periods. Adjacent segments with equal free_units must be
combined. available_unit_minutes is the integral of free_units over the horizon.
query has ready (integer), duration (positive integer minutes), and units (positive
integer). booking is the earliest [start,start+duration] wholly within the horizon
at or after ready with free_units >= units at EVERY instant. An operation can span
adjacent segments with different adequate capacities but cannot pause across a gap.
Return booking=null if no continuous feasible slot exists. Report the pre-booking
profile and integral; this query does not reserve or alter capacity.

At most 100 intervals and jobs combined, capacity and job/query units <=20. The
horizon may span 10^9 minutes: running time must depend on the number of intervals,
not on every minute in the horizon. Do not mutate any input lists or dictionaries.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
