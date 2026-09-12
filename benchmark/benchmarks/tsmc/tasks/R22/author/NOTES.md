# Author notes

Design difficulty: hard. Coordinate durable independent epoch allocators, atomic set acquisition, partial renewal/release, complete ownership and revision read sets, transactional multi-key output publication and crash recovery across four modules.

Family: `atomic_scoped_grants_versioned_fencing`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
