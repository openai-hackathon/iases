# A01 Public API and data contract

# Synthetic downtime data contract, v1.0

This repository contains synthetic software tasks, not production equipment
controls or a physical model of semiconductor processing.

`downtime_seconds(events, machine_id, window_start, window_end)` must compute
elapsed seconds in the UNION of that machine's intervals within the requested
half-open observation window `[window_start, window_end)`.

- Window end must be strictly after window start; otherwise raise ValueError.
- Timestamps have explicit UTC offsets or Z. Normalize to elapsed UTC time.
  Naive timestamps raise ValueError. Fractions of a second are permitted.
- Each event has event_id, machine_id, start, end. Other-machine rows do not
  contribute and are ignored before parsing their timestamps.
- `end: null` means the event is still open and is clipped to the window end.
- Closed events ending before their own start raise ValueError; zero-length
  closed events contribute zero. Selected malformed records are not silently
  discarded.
- Clip intervals to the window; no coverage outside the window is counted.
- Overlap, nested intervals and identical duplicate rows cannot double count.
  Multiple records may describe one downtime episode. event_id is not the
  grouping key for counting duration.
- Input order, a repeated row, or an unrelated machine must not change the
  selected machine's covered time. Touching endpoints do not add duration.
- Do not mutate the input. Empty input returns 0.0 for a valid window.
- Return elapsed seconds as a float. CLI report schema and existing public
  signatures must remain compatible. Tests use numerical tolerance 1e-9.

The report denominator is the observation-window duration, NOT production
time, not number of events, and not a real-world OEE definition.


The v0.2 unified CLI is `python -m fabops --input data/request.json`. Input contains events, machine_id, window_start and window_end; output matches make_report. Preserve the analytics API; the old report-downtime CLI is not a v0.2 requirement. `covered_seconds` accepts already-clipped positive-duration datetime intervals and must not mutate inputs.
