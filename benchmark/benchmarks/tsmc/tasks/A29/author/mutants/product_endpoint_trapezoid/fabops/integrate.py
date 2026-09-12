"""Integrate products over intersections of two piecewise linear supports."""
from fractions import Fraction as F

def value(segment, at):
    a, b, va, vb = segment
    return va + (vb - va) * (at - a) / (b - a)

def measure(pressure, flow, start, end):
    covered = volume = work = F(0)
    for p in pressure:
        for q in flow:
            left, right = max(start, p[0], q[0]), min(end, p[1], q[1])
            if left >= right:
                continue
            width = right - left
            p0, p1 = value(p, left), value(p, right)
            q0, q1 = value(q, left), value(q, right)
            dp, dq = p1 - p0, q1 - q0
            covered += width
            volume += width * (q0 + q1) / 120
            work += width * ((p0 * q0 + p1 * q1) / 2) / 600
    return covered, volume, work
