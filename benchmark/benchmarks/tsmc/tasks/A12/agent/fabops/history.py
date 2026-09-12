"""Resolve identity revisions at the recorded-time visibility frontier."""
def visible(rows, asof):
    current = {}
    for row in sorted(rows, key=lambda row: row["revision"]):
        current[row["id"]] = row
    return {key: row for key, row in current.items() if row["recorded"] <= asof}
