# Author notes

Design difficulty: hard. Replace an eager out-of-order reducer and unsafe retention architecture while coordinating independently committed sink effects, local acknowledgements, durable producer identities, epoch fencing and crash-safe compaction across six modules.

Family: `durable_ordered_outbox_fenced_consumer_compaction`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
