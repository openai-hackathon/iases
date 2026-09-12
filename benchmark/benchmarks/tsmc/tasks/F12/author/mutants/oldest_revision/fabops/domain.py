def run(request):
    matches = [r for r in request["rules"] if all(r[k] in ("*", request[k]) for k in ("product", "machine"))]
    def rank(rule):
        specificity = sum(rule[k] != "*" for k in ("product", "machine"))
        return (-specificity, rule["revision"], rule["id"])
    return min(matches, key=rank)["id"] if matches else None
