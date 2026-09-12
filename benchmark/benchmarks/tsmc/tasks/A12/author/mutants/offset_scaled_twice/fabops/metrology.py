"""Join the chosen measurement to quality and calibration at its own time."""
from fractions import Fraction

def choose(measurements, quality, at):
    selected = {}
    for row in measurements.values():
        if row["deleted"] or row["event"] > at:
            continue
        key = (row["part"], row["station"])
        old = selected.get(key)
        if old is None or (row["event"], row["id"]) > (old["event"], old["id"]):
            selected[key] = row
    return selected

def cell(row, quality, calibrations, at):
    if row is None:
        return None
    verdict = quality.get(row["id"])
    valid = row["valid"] if verdict is None else verdict["valid"]
    if not valid or row["raw"] is None:
        return None
    calibration = calibrations.get(row["calibration"])
    if calibration is None or calibration["deleted"]:
        return None
    if not calibration["start"] <= row["event"] < calibration["end"]:
        return None
    value = (Fraction(row["raw"]) + Fraction(calibration["offset"])) * Fraction(calibration["gain"])
    return dict(measurement=row["id"], revision=row["revision"],
                calibration_revision=calibration["revision"], value=str(value))
