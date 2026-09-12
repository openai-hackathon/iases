"""Find a continuous booking inside a capacity profile."""
def earliest(profile, ready, duration, units):
    run_start = None
    run_end = None
    for left, right, free in profile:
        left = max(left, ready)
        if left >= right:
            continue
        if free < units:
            run_start = run_end = None
            continue
        if run_end != left or run_start is not None:
            run_start = left
        run_end = right
        if run_end - run_start >= duration:
            return [run_start, run_start + duration]
    return None
