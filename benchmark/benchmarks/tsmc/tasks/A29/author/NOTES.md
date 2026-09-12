# Author notes

Design difficulty: hard. Five interacting modules require reconstruction of revision visibility, affine clock/epoch adjacency, calibration-partitioned support, exact products on joint multirate intervals, and compensating publication deltas. Eight independent realistic fault sites include whole visibility, calibration and interval-integration algorithms. The baseline resamples window endpoints and cannot retain internal support gaps or quadratic signal products; nine mutants include a partial restoration that still uses endpoint-product trapezoids. Hidden cases combine corrections, discontinuities and clock/gap decisions. This is substantially broader than a static four-line hydraulic integration repair and the discrete A12 join.

Family: `revisioned_multirate_hydraulic_retractions`. References: zema-hydraulic, nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
