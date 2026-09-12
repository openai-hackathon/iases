# Fab Relay

A mock frontend for priority-aware and deadline-aware wafer-fab incident recovery.

This independent hackathon demo uses a fictional fab inspired by semiconductor operations. It is not affiliated with TSMC. It has no live equipment, Codex, LM, BT or scheduler-service connection. All deadlines, scores and agents are simulated. Do not use the demo for operational decisions.

## Run

Use Node.js 22.18 or later.

```sh
npm install
npm run dev
```

```sh
npm test
npm run build
```

## Demo

1. Leave the simulation paused at T+00:00.
2. Select a scheduling policy.
3. Select **Trigger incident**.
4. Choose power interruption, cooling excursion or telemetry outage.
5. Select a zone and a 30–180 second response window.
6. Trigger the incident. The simulation starts and adds three mock agents.
7. Select a task card to open its details. Change queued task importance with **Apply priority override**.
8. Pause or use 4× playback. Expand **Activity log** for event history.
9. Reset and repeat the same scenario at T+00:00 to compare policies.

Compare policies with the same incident and response window. Outcomes are deterministic mock results, not measured production benefits.

## Scheduling

- The diagnostic pool has 8 CPU cores and 16 GiB RAM. Each tool call reserves a fixed amount of both resources.
- Multiple tasks run concurrently when both resource budgets permit. Completion releases reservations. Running tasks are not preempted.
- Dispatch follows queue order. If the first task does not fit, later tasks wait too. This preserves order but can leave capacity unused.
- Resource bars show simulated reservations, not real CPU utilization or measured memory.
- FIFO uses arrival time and task ID as its tie-breaker.
- Priority first uses descending importance, then FIFO.
- Deadline + priority uses ascending slack, then descending importance, then FIFO.
- Slack equals deadline minus simulation time minus remaining work.
- The deadline mode uses priority only as a tie-breaker. It is not a combined optimization, BT fit or starvation guarantee.
- The response tasks are independent mock jobs. Their sequence does not encode real recovery dependencies or safety procedures.
- A task misses its deadline only when it completes late or remains unfinished after the deadline. Completion at the deadline is on time.
- Maximum background wait includes completed, running and waiting background tasks.
- History permits 12 incidents per reset, three active incidents and 40 recent events. Reloading the page clears the simulation.

## Integration boundary

`src/simulation.ts` owns the local fixtures, queue and simulation transitions. The UI consumes its state. A future service adapter can replace these transitions with backend snapshots and commands. This mock does not implement that adapter. Keep backend state authoritative when connecting the real scheduler.

The priority slider is an explicit mock operator override. It does not claim to implement preference pairs, LM expansion or BT refitting. Model routing and Modal deployment are outside this demo.
