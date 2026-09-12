from .events import normalize
from .correlation import matchings

def run(request):
    events = normalize(request["events"])
    interpretations = matchings(events, request)
    certain = set(interpretations[0])
    for pairs in interpretations[1:]:
        certain.intersection_update(pairs)
    ever_used = {identifier for pairs in interpretations for pair in pairs for identifier in pair}
    by_id = {event["id"]: event for event in events}
    durations = [sum(by_id[end]["time"] - by_id[start]["time"]
                     for start, end in pairs) for pairs in interpretations]
    return dict(matched=len(interpretations[0]), alternatives=len(interpretations),
                certain_pairs=[list(pair) for pair in sorted(certain)],
                certain_unmatched=sorted(set(by_id) - ever_used),
                duration_bounds=[min(durations), max(durations)])
