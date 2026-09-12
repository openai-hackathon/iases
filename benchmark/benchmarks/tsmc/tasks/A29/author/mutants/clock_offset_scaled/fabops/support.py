"""Build factory-time support, respecting epochs, invalid knots and calibration intervals."""
from fractions import Fraction as F

def segments(samples, clocks, calibrations, channel, maximum_gap):
    groups = {}
    for sample in samples:
        if sample["channel"] == channel:
            groups.setdefault(sample["epoch"], []).append(sample)
    clock_map = {(clock["channel"], clock["epoch"]): clock for clock in clocks}
    active = [row for row in calibrations if row["channel"] == channel]
    result = []
    for epoch, rows in groups.items():
        clock = clock_map[channel, epoch]
        def factory_time(row):
            return (F(clock["global_origin"]) + F(row["t"]) - F(clock["local_origin"])) * F(clock["rate"])
        ordered = sorted(rows, key=lambda row: F(row["t"]))
        for first, second in zip(ordered, ordered[1:]):
            a, b = factory_time(first), factory_time(second)
            if not first["valid"] or not second["valid"]:
                continue
            if b - a > F(maximum_gap):
                continue
            segment = (a, b, F(first["raw"]), F(second["raw"]))
            result.extend(calibrate(segment, active))
    return sorted(result)

def calibrate(segment, calibrations):
    a, b, va, vb = segment
    result = []
    for calibration in calibrations:
        left = max(a, F(calibration["start"]))
        right = min(b, F(calibration["end"]))
        if left >= right:
            continue
        gain, offset = F(calibration["gain"]), F(calibration["offset"])
        raw_left = va + (vb - va) * (left - a) / (b - a)
        raw_right = va + (vb - va) * (right - a) / (b - a)
        result.append((left, right, raw_left * gain + offset, raw_right * gain + offset))
    return result
