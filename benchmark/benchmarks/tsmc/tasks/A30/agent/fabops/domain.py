from .cohort import training_rows
from .model import fit, score
from .calibration import calibrate

def run(request):
    target = next(row for row in request["cycles"] if row["id"] == request["target"])
    rows = training_rows(request["cycles"], target, request["embargo"])
    result = dict(training=[row["id"] for row in rows], center=None, scale=None,
                  correlation=None, score=None, calibration=[], threshold=None,
                  decision="insufficient_training")
    if len(rows) < request["min_train"]:
        return result
    model = fit(rows, request["shrinkage"])
    center, scale, correlation = model
    result.update(center=[round(value,6) for value in center], scale=[round(value,6) for value in scale],
                  correlation=[[round(value,6) for value in row] for row in correlation])
    threshold = request["threshold"]
    if request.get("calibrate", False):
        calibration, threshold = calibrate(rows, request)
        result["calibration"] = [[name, round(value,6)] for name,value in calibration]
    result["threshold"] = None if threshold is None else round(threshold,6)
    if target["profile"][4] != 0 or sum(value is not None for value in target["features"]) < request.get("min_observed", len(target["features"])):
        result["decision"] = "deferred"
        return result
    distance = score(target["features"], model)
    result["score"] = round(distance,6)
    result["decision"] = "insufficient_calibration" if threshold is None else "alarm" if distance >= threshold else "normal"
    return result
