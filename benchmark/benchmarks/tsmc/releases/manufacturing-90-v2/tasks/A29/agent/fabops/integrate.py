"""Integrate two calibrated affine signals on their common valid support."""
from .segments import value

def joint_integrals(pressure, flow):
    duration = volume = work = 0.0
    for p in pressure:
        for q in flow:
            left, right = max(p[0], q[0]), min(p[1], q[1])
            if left >= right:
                continue
            width = right - left
            p0, p1 = value(p, left), value(p, right)
            q0, q1 = value(q, left), value(q, right)
            dp, dq = p1 - p0, q1 - q0
            duration += width
            volume += width * (q0 + q1) / 120
            work += width * (p0 * q0 + (p0 * dq + q0 * dp) / 2
                             + dp * dq / 2) / 600
    return duration, volume, work
