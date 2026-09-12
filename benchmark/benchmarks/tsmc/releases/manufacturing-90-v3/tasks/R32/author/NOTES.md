# Author notes

Design difficulty: hard. Bind resumable staging to a canonical multi-chunk manifest, enforce independent per-chunk and cross-chunk constraints, and separate staged durability from atomic query visibility across restart. This combines hash integrity, scope/order identity and publication recovery rather than a single request fingerprint or schema rollback.

Family: `manifest_bound_resumable_atomic_bulk_ingest`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
