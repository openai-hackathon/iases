"""Integrate products over intersections of two piecewise linear supports."""
from fractions import Fraction as F

def value(segment, at):
    a, b, va, vb = segment
    return va + (vb - va) * (at - a) / (b - a)

def measure(pressure, flow, start, end):
    if not pressure or not flow:
        return F(0), F(0), F(0)
    left = max(start, pressure[0][0], flow[0][0])
    right = min(end, pressure[-1][1], flow[-1][1])
    if left >= right:
        return F(0), F(0), F(0)
    def sample_at(signal, at):
        earlier = [segment for segment in signal if segment[0] <= at]
        segment = max(earlier, key=lambda row: row[0]) if earlier else signal[0]
        return value(segment, min(segment[1], max(segment[0], at)))
    p0, p1 = sample_at(pressure, left), sample_at(pressure, right)
    q0, q1 = sample_at(flow, left), sample_at(flow, right)
    width = right - left
    return width, width * (q0 + q1) / 120, width * (p0 * q0 + p1 * q1) / 1200
