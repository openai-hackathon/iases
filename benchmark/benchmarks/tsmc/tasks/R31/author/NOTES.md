# Author notes

Design difficulty: hard. Compute greatest dependency-closed prefix vectors across epoch-sensitive sources; repeated causal retreat interacts with durable out-of-order buffers, delayed watermark barriers, lower-bound publication requests and failed checkpoints.

Family: `durable_causal_prefix_fixed_point`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
