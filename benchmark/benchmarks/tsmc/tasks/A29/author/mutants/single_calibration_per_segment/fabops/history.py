"""Resolve full replacement records before interpreting deletion or quality."""
def visible(rows, asof):
    selected = {}
    for row in rows:
        if row["recorded"] <= asof:
            old = selected.get(row["id"])
            if old is None or row["revision"] > old["revision"]:
                selected[row["id"]] = row
    return [row for row in selected.values() if not row["deleted"]]
