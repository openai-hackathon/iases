"""Average complex cross spectra before forming band coherence or phase."""
from cmath import exp, phase
from math import pi

def transform(values):
    n = len(values)
    return [sum(value*exp(-2j*pi*k*i/n) for i,value in enumerate(values)) for k in range(n//2+1)]

def summarize(segments, request):
    n = len(segments[0][1])
    xx, yy, xy = [0.0]*(n//2+1), [0.0]*(n//2+1), [0j]*(n//2+1)
    for _, first, second, _, normalizer in segments:
        fx, fy = transform(first), transform(second)
        for k in range(n//2+1):
            factor = 1 if k == 0 else 2
            weight = factor / (n*normalizer*len(segments))
            xx[k] += weight*abs(fx[k])**2
            yy[k] += weight*abs(fy[k])**2
            xy[k] += weight*fx[k].conjugate()*fy[k]
    chosen = [k for k in range(n//2+1) if request["band"][0] <= k*request["sample_rate"]/n < request["band"][1]]
    first, second, cross = sum(xx[k] for k in chosen), sum(yy[k] for k in chosen), sum(xy[k] for k in chosen)
    coherence = min(1.0, abs(cross)**2/(first*second)) if first*second > 1e-12 else 0.0
    angle = phase(cross) if abs(cross) > 1e-12 else 0.0
    # Normalize numerical -pi to the documented (-pi, pi] convention.
    if abs(angle + pi) < 1e-12:
        angle = pi
    return first, sum(xx), second, coherence, angle
