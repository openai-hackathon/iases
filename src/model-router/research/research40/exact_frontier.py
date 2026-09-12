import hashlib

import numpy as np

from audit.protocol import label_safe_frontier, summarize_curve


def exact_frontier(predictions, labels, costs):
    p = np.asarray(predictions, dtype=np.float64)
    y, c = np.asarray(labels, dtype=np.float64), np.asarray(costs, dtype=np.float64)
    if p.ndim != 2 or y.shape != p.shape or min(p.shape) < 1 or c.shape != (p.shape[1],):
        raise ValueError("Expected nonempty question-by-model scores, labels and model costs")
    if not all(np.isfinite(a).all() for a in (p, y, c)) or np.any(c <= 0) or np.any((y < 0) | (y > 1)):
        raise ValueError("Expected finite scores, bounded labels and positive costs")
    p = np.clip(p, 0, 1)
    base = np.empty(len(p), dtype=np.int64)
    events = []
    for q in range(len(p)):
        _, _, vertices = label_safe_frontier(c, p[q], p[q])
        base[q] = vertices[0]
        for a, b in zip(vertices[:-1], vertices[1:]):
            events.append(((p[q, b]-p[q, a])/(c[b]-c[a]), q, a, b))
    schedule = np.asarray(events, dtype=np.float64).reshape(-1, 4)
    schedule = schedule[np.argsort(-schedule[:, 0], kind="stable")]
    initial = np.array([c[base].mean(), p[np.arange(len(p)), base].mean(), y[np.arange(len(p)), base].mean()])
    if len(schedule):
        q, a, b = schedule[:, 1:].astype(np.int64).T
        increments = np.column_stack((c[b]-c[a], p[q, b]-p[q, a], y[q, b]-y[q, a]))
        ends = np.r_[np.flatnonzero(np.diff(schedule[:, 0]) != 0), len(schedule)-1]
        curve = np.vstack((initial, initial+np.cumsum(increments, axis=0)[ends]/len(p)))
    else:
        curve = initial[None]
    curve[:, 0] = np.clip(curve[:, 0], c.min(), c.max())
    fingerprint = hashlib.sha256(base.tobytes()+schedule.tobytes()).hexdigest()
    return dict(cost=curve[:, 0].tolist(), estimated_quality=curve[:, 1].tolist(), accuracy=curve[:, 2].tolist(),
                events=len(schedule), breakpoints=len(curve)-1, policy_sha256=fingerprint)


def evaluate_exact(predictions, labels, costs):
    curve = exact_frontier(predictions, labels, costs)
    p = np.clip(np.asarray(predictions, dtype=np.float64), 0, 1)
    y, c = np.asarray(labels, dtype=np.float64), np.asarray(costs, dtype=np.float64)
    accuracy = y.mean(0)
    tied = np.flatnonzero(accuracy >= accuracy.max()-1e-7)
    best = tied[np.argmin(c[tied])]
    metrics = summarize_curve(curve["cost"], curve["accuracy"], float(c.min()), float(c.max()),
                              float(c[best]), float(accuracy[best]))
    if len(metrics["cost"]) > len(curve["estimated_quality"]):
        curve["estimated_quality"].append(curve["estimated_quality"][-1])
    curve.update(metrics, brier=float(np.mean((p-y)**2)), best_single_cost=float(c[best]),
                 best_single_accuracy=float(accuracy[best]))
    return curve
