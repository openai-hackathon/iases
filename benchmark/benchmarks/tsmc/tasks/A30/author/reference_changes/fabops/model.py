"""Equal campaign mass, within-campaign moments, and observed-subspace scoring."""
from collections import Counter
from math import sqrt
from .linalg import solve

def fit(rows, shrinkage):
    counts = Counter(row["run"] for row in rows)
    weights = [1 / (len(counts) * counts[row["run"]]) for row in rows]
    dimension = len(rows[0]["features"])
    center = [sum(weight * row["features"][j] for row, weight in zip(rows, weights)) for j in range(dimension)]
    covariance = [[sum(weight * (row["features"][j]-center[j]) * (row["features"][k]-center[k])
                       for row, weight in zip(rows, weights)) for k in range(dimension)] for j in range(dimension)]
    scale = [sqrt(covariance[j][j]) if covariance[j][j] > 0 else 1.0 for j in range(dimension)]
    correlation = [[1.0 if j == k else (1-shrinkage)*covariance[j][k]/(scale[j]*scale[k])
                    for k in range(dimension)] for j in range(dimension)]
    return center, scale, correlation

def score(features, model):
    center, scale, correlation = model
    observed = [j for j, value in enumerate(features) if value is not None]
    z = [(features[j]-center[j])/scale[j] for j in observed]
    matrix = [[correlation[j][k] for k in observed] for j in observed]
    solution = solve(matrix, z)
    return len(features)/len(observed) * sum(a*b for a, b in zip(z, solution))
