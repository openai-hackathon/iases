"""Select a purged, stable, healthy cohort without campaign leakage."""
def training_rows(rows, target, embargo):
    selected = []
    for row in rows:
        if row["run"] == target["run"]:
            continue
        if row["end"] > target["start"] - embargo:
            continue
        if row["profile"][4] != 0:
            continue
        if row["profile"][0] != 100:
            continue
        if any(value is None for value in row["features"]):
            continue
        selected.append(row)
    return sorted(selected, key=lambda row: (row["end"], row["id"]))
