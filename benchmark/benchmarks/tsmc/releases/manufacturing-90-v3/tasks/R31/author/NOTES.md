# Author notes

Design difficulty: hard. Reconcile out-of-order event buffers, epoch resets, delayed watermark barriers and a common multi-source time cut across real checkpoint interruptions. Unlike cursor advancement or consumer retention, publication depends on the interaction of three independent orders: source epoch, sequence continuity and event time, with durable unresolved state.

Family: `multisource_epoch_barrier_snapshot_recovery`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
