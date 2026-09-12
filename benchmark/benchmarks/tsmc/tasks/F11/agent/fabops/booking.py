"""Find a continuous booking inside a capacity profile."""
def earliest(profile, ready, duration, units):
    remaining = duration
    started = None
    for left, right, free in profile:
        left = max(left, ready)
        if free < units or right <= left:
            continue
        if started is None:
            started = left
        take = min(remaining, right - left)
        remaining -= take
        if remaining == 0:
            return [started, left + take]
    return None
