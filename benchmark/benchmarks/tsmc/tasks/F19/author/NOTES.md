# Author notes

Design difficulty: hard. Replace static bipartite allocation and earliest-only placement with globally optimal temporal selection across reticle reuse, weighted demand, cooldown, maintenance and precedence, then preserve a complete reservation transaction across failure and reopen.

Family: `temporal_reticle_dispatch_commit`. References: production-log, nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
