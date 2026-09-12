# Author notes

Design difficulty: medium. Keep SQLite DDL and data changes in one rollback boundary and support a clean retry.

Family: `transactional_schema_migration`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
