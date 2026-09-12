# Author notes

Design difficulty: hard. Coordinate four coupled invariants across SQLite intent atomicity, an independently committed sink, lost acknowledgements, per-channel idempotence and monotonic projections. Unlike a single outbox or lease check, a successful retry must repair channel divergence without duplicating a remote effect or rolling back a newer revision.

Family: `durable_multichannel_outbox_reconciliation`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
