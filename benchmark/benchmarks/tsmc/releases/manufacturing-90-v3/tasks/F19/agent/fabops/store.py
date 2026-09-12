"""Commit a plan only against the complete observed state revision."""
def commit_plan(pairs, lots, stock, observed, current):
    if observed.get("dispatch") != current.get("dispatch"):
        return False, dict(stock)
    remaining = dict(stock)
    by_id = {lot["id"]: lot for lot in lots}
    for lot, _ in pairs:
        remaining[by_id[lot]["reticle"]] -= 1
    return True, remaining
