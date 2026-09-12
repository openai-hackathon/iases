"""Resolve identity revisions at the recorded-time visibility frontier."""
def visible(rows, asof):
    current = {}
    for row in rows:
        if row["recorded"] > asof or row.get("deleted", False):
            continue
        old = current.get(row["id"])
        if old is None or row["revision"] > old["revision"]:
            current[row["id"]] = row
    return current
