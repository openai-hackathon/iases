"""Half-open temporal reservations shared by alternative dispatch choices."""
def feasible(request, rows):
    by_id = {lot["id"]: lot for lot in request["lots"]}
    assigned = {row[0]: row for row in rows}
    for identifier, tool, start, end in rows:
        lot = by_id[identifier]
        if any(start < right and left < end
               for left, right in request.get("maintenance", {}).get(tool, [])):
            return False
        for predecessor in lot.get("after", []):
            if predecessor in assigned and assigned[predecessor][3] > start:
                return False
    for tick in range(request["horizon"]):
        tools, reticles = set(), {}
        for identifier, tool, start, end in rows:
            lot = by_id[identifier]
            if start <= tick < end:
                if tool in tools:
                    return False
                tools.add(tool)
            if start <= tick < end:
                reticle = lot["reticle"]
                reticles[reticle] = reticles.get(reticle, 0) + lot.get("units", 1)
        if any(count > request["stock"].get(key, 0) for key, count in reticles.items()):
            return False
    return True
