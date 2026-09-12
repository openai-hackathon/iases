from .calendar import capacity_profile
from .booking import earliest

def run(request):
    profile = capacity_profile(request)
    query = request["query"]
    booking = earliest(profile, query["ready"], query["duration"], query["units"])
    unit_minutes = sum((right - left) * free for left, right, free in profile)
    return dict(profile=profile, available_unit_minutes=unit_minutes, booking=booking)
