# Author notes

Design difficulty: medium. Reconcile FIFO fairness, weighted capacity and cancellation before waking waiters.

Family: `fifo_weighted_semaphore_cancellation`. References: production-log.

Fixtures are newly authored. No external dataset rows are redistributed.
