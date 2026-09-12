"""Resolve the exact pinned revision closure before publishing a package."""
def closure(artifacts, roots):
    catalog = {(row["id"], row["revision"]): row for row in artifacts}
    selected, active, done, ordered = {}, set(), set(), []

    def visit(key):
        key = tuple(key)
        if key in active and key not in done:
            raise ValueError("dependency cycle")
        if key[0] in selected and selected[key[0]] > key[1]:
            raise ValueError("incompatible revision pins")
        selected[key[0]] = key[1]
        if key in done:
            return
        row = max((row for (name, revision), row in catalog.items() if name == key[0]), key=lambda row: row["revision"], default=None)
        if row is None or row["revoked"]:
            raise ValueError("missing or revoked artifact")
        active.add(key)
        done.add(key)
        for dependency in sorted(row["requires"]):
            visit(dependency)
        active.remove(key)
        ordered.append(row)

    for root in sorted(roots):
        visit(root)
    return ordered
