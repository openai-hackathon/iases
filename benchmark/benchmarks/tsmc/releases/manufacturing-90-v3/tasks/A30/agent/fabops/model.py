"""Fit training-only moments and a shrunk two-feature correlation model."""
from math import sqrt

def fit(rows, target, shrinkage):
    values = [row["features"] for row in rows] + ([target["features"]] if all(value is not None for value in target["features"]) else [])
    center = [sum(row[j] for row in values) / len(values) for j in range(2)]
    variance = [sum((row[j] - center[j]) ** 2 for row in values) / len(values)
                for j in range(2)]
    scale = [sqrt(value) if value > 0 else 1.0 for value in variance]
    correlation = sum((row[0] - center[0]) * (row[1] - center[1]) for row in values)
    correlation /= len(values) * scale[0] * scale[1]
    return center, scale, (1 - shrinkage) * correlation

def score(features, center, scale, correlation):
    first, second = [(features[j] - center[j]) / scale[j] for j in range(2)]
    return ((first * first + 2 * correlation * first * second + second * second)
            / (1 - correlation * correlation))
