# Public behavior contract

Reconstruct WIP from a revisioned MES recipe-receipt log; do not apply corrections as
additive inventory deltas. capacities maps all stage names to positive integer limits.
initial maps stages to nonnegative quantities within those limits; absent stages are
zero. recipes maps ids to consume and produce mappings of positive integer quantities
per batch, plus nonnegative integer scrap per batch. Every recipe consumes a nonempty
input mapping and conserves material: sum(consume) = sum(produce) + scrap. A stage may
appear in both sides. All recipe stages occur in capacities. A recipe can represent a
synchronized multi-input gate, rework, material review, or partial-yield completion.

Each logical event has a string id and positive integer revision. An active version
additionally has integer order, recipe id, and positive integer batches. A tombstone
has deleted=true and needs only id/revision. Duplicate (id,revision) rows must have
identical complete content and count once; conflicting rows raise ValueError. For
each logical id choose its numerically greatest revision, independent of arrival order;
discard it if that latest version is a tombstone. Earlier tombstones can be superseded
by higher active versions. Sort selected active events by (order,id), then replay ONCE
from initial inventory. Corrections can change recipe, batches or order and therefore
change whether every later gate is feasible. Never use earlier versions as supply.

For each event multiply every recipe quantity and scrap by batches. Accept only if
all consumed quantities are simultaneously available and every post-consumption,
post-production inventory quantity respects capacity. Consume and produce atomically;
rejection changes neither inventory nor accumulated scrap, even when only the output
capacity fails after all inputs were available. Continue replay after rejection; rejected
events are not retried if a later event adds material. Return inventory with every stage,
accepted and rejected lists of active ids in replay order, and total accepted scrap.
Tombstoned ids appear in neither list. Material in final inventory plus scrap must equal
material in initial inventory. Do not mutate input data, even on rejected operations.
There are at most twelve logical ids, four revisions each, six stages and six recipes.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
