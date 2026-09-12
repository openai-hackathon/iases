# Author notes

Design difficulty: hard. Repair two interacting invariants across durable epoch allocation, lease deletion, database reopen and transactional stale-writer fencing.

Family: `durable_fencing_epoch_ownership`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
