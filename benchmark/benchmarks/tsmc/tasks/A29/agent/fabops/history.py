"""Resolve full replacement records before interpreting deletion or quality."""
def visible(rows, asof):
    selected = {}
    for row in sorted(rows, key=lambda row: row["revision"]):
        selected[row["id"]] = row
    return [row for row in selected.values() if row["recorded"] <= asof and not row["deleted"]]
