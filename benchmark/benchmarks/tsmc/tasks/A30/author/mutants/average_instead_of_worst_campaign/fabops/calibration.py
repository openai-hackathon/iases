"""Purged leave-campaign-out calibration with equal mass per held-out campaign."""
from math import ceil
from .cohort import training_rows
from .model import fit, score

def calibrate(rows, request):
    calibration = []
    for campaign in sorted({row["run"] for row in rows}):
        held = [row for row in rows if row["run"] == campaign]
        anchor = dict(held[0], start=min(row["start"] for row in held))
        training = training_rows(rows, anchor, request["embargo"])
        if len(training) < request["min_train"]:
            continue
        model = fit(training, request["shrinkage"])
        calibration.append([campaign, sum(score(row["features"], model) for row in held)/len(held)])
    rank = ceil((len(calibration)+1)*(1-request["alpha"]))
    if not calibration or rank > len(calibration):
        return calibration, None
    return calibration, sorted(value for _, value in calibration)[rank-1]
