"""Diagnose one cycle using only eligible historical campaigns."""
from .cohort import training_rows
from .model import fit, score

def run(request):
    target = next(row for row in request["cycles"] if row["id"] == request["target"])
    rows = training_rows(request["cycles"], target, request["embargo"])
    result = dict(training=[row["id"] for row in rows], center=None, scale=None,
                  correlation=None, score=None, decision="insufficient_training")
    if len(rows) < request["min_train"]:
        return result
    center, scale, correlation = fit(rows, target, request["shrinkage"])
    result.update(center=[round(value, 6) for value in center],
                  scale=[round(value, 6) for value in scale],
                  correlation=round(correlation, 6))
    if target["profile"][4] != 0 or any(value is None for value in target["features"]):
        result["decision"] = "deferred"
        return result
    distance = score(target["features"], center, scale, correlation)
    result.update(score=round(distance, 6),
                  decision="alarm" if distance >= request["threshold"] else "normal")
    return result
