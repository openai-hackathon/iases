from .revisions import active_events
from .bundles import groups, settle

def run(request):
    inventory = {place: request["initial"].get(place, 0) for place in request["capacities"]}
    accepted, rejected, scrap = [], [], 0
    events = active_events(request["events"], request.get("as_of", float("inf")))
    for bundle in groups(events):
        result = settle(bundle, inventory, request["capacities"], request["recipes"], accepted)
        if result is None:
            rejected.extend(sorted(event["id"] for event in bundle))
        else:
            inventory, loss, witness = result
            scrap += loss
            accepted.extend(witness)
    return dict(inventory=inventory, accepted=accepted, rejected=rejected, scrap=scrap)
