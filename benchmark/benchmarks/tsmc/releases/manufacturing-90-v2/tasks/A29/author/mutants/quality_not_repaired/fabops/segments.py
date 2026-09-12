"""Build cycle-local calibrated linear segments without bridging bad data."""
def segments(rows, cycle, calibration, max_gap):
    points = sorted((row for row in rows if row["cycle"] == cycle["id"]
                     and cycle["start"] <= row["t"] <= cycle["end"]),
                    key=lambda row: row["t"])
    result = []
    for left, right in zip(points, points[1:]):
        width = right["t"] - left["t"]
        if not (left["valid"] or right["valid"]):
            continue
        if width > max_gap:
            continue
        values = [row["value"] * calibration["gain"] + calibration["offset"]
                  for row in (left, right)]
        result.append((left["t"], right["t"], *values))
    return result

def value(segment, time):
    left, right, first, last = segment
    return first + (last - first) * (time - left) / (right - left)
