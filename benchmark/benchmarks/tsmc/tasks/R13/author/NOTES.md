# Author notes

Design difficulty: medium. Coordinate scoped invalidation, shared caller cancellation, orphan producers and stale asynchronous cleanup through producer identity ownership across two modules; replacing shield alone cannot repair lifecycle semantics.

Family: `scoped_generation_singleflight_lifecycle`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
