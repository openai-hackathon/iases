# Author notes

Design difficulty: hard. Bind immutable resumable manifests to shared dataset scopes and read sets, validate all chunks and cross-upload identities against one pre-state, preserve tombstone versions, and publish records, audits and group receipts atomically across restart.

Family: `versioned_multi_upload_atomic_publication`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
