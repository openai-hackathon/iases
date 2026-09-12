# Author notes

Design difficulty: hard. Must reconstruct all globally maximal lifecycle pairings instead of a greedy operation order, combining idempotent ingestion, partial correlation ids, ambiguity intersections and independently bounded duration aggregates across modules.

Family: `ambiguous_lifecycle_maximum_matching`. References: production-log.

Fixtures are newly authored. No external dataset rows are redistributed.
