from .revisions import active_events
from .ledger import apply

def run(request):
    inventory = {place: request["initial"].get(place, 0) for place in request["capacities"]}
    accepted, rejected, scrap = [], [], 0
    for event in active_events(request["events"]):
        ok, inventory, loss = apply(inventory, request["capacities"],
                                    request["recipes"][event["recipe"]], event["batches"])
        (accepted if ok else rejected).append(event["id"])
        scrap += loss
    return dict(inventory=inventory, accepted=accepted, rejected=rejected, scrap=scrap)
