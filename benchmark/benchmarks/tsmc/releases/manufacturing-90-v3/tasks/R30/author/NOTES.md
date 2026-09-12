# Author notes

Design difficulty: hard. Resolve a revision-pinned graph with shared dependencies, cycles and incompatible pins; verify all reachable content; then preserve the last complete installed package across a real interrupted replacement. The coupled graph/integrity/publication boundary differs from a one-table schema migration.

Family: `pinned_revision_closure_atomic_package_install`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
