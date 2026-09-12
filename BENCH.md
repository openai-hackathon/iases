# Bench

- **Scheduling:** compare FIFO, strict priority, and aging policies with offline replay.
  Measure critical-task wait and background-task starvation.
- **Live execution:** check tool admission with a real Codex run.
  Keep live measurements separate from replay results.
- **Task quality:** compare resolved SWE tasks against a fixed-model baseline.
  The first pilot matched the baseline; it did not improve it.

### Scheduler replay

Offline replay, 200 rounds, 16,000 tool calls, 10 seeds per policy. Linear score = importance + wait × rate.

| Workload | Policy | Critical mean wait | Critical p95 wait | Background max wait | Background max unserved |
| --- | --- | --- | --- | --- | --- |
| Long tail | FIFO | 75.0 s | 139.6 s | 148.4 s | 52.2 s |
| Long tail | Strict priority | 5.8 s | 12.8 s | 155.4 s | 122.5 s |
| Long tail | Linear, rate 0.25 | 5.9 s | 12.8 s | 153.5 s | 87.3 s |
| Long tail | Linear, rate 1 | 41.3 s | 98.1 s | 151.1 s | 55.1 s |
| Uniform | FIFO | 38.3 s | 73.0 s | 76.7 s | 32.8 s |
| Uniform | Strict priority | 2.0 s | 5.1 s | 88.0 s | 73.6 s |
| Uniform | Linear, rate 0.25 | 2.0 s | 5.1 s | 81.5 s | 44.7 s |

Linear at rate 0.25 has similar critical wait to strict priority and lower background max unserved time in these workloads.

### Live Codex

A recorded run with preemption enabled reduced critical-call wait from 4699 ms to 1 ms.
This is a separate live measurement, not a replay result or a deadline guarantee.

### SWE pilot

The first offline pilot resolved **68/100 tasks**, equal to fixed medium.
It did not improve on that baseline. The combined system still needs end-to-end validation.

See the [replay runner](src/task-evolver/experiments/replay.py) and
[benchmark harness](benchmark/) for the evaluation code.

### Deployment

Deployment checks passed on Linux arm64 containers: four services healthy, 71 backend tests, an incident-before-background admission smoke, and the live tool round trip. Four preparation/deployment tests also passed. Docker images built successfully. Linux amd64 runtime remains unverified.

