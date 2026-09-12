"""Periodic Hann window and energy-conserving one-sided DFT bands."""
from math import cos, sin, pi

def window(values):
    count = len(values)
    weights = [0.5 - 0.5 * cos(2 * pi * index / (count - 1)) for index in range(count)]
    return [value * weight for value, weight in zip(values, weights)], sum(weight * weight for weight in weights)

def energies(values, normalizer, sample_rate, band):
    count = len(values)
    selected = total = 0.0
    for frequency in range(count // 2 + 1):
        real = sum(value * cos(2 * pi * frequency * index / count)
                   for index, value in enumerate(values))
        imag = -sum(value * sin(2 * pi * frequency * index / count)
                    for index, value in enumerate(values))
        factor = 1 if frequency == 0 else 2
        energy = factor * (real * real + imag * imag) / (count * normalizer)
        total += energy
        if band[0] <= frequency * sample_rate / count < band[1]:
            selected += energy
    return selected, total
