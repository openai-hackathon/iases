def run(request):
    lease = dict(request["lease"])
    accepted = []
    for renewal in request["renewals"]:
        valid = renewal["owner"] == lease["owner"] and renewal["now"] < lease["expires"]
        if valid:
            lease["expires"] = lease["expires"] + renewal["ttl"]
        accepted.append(valid)
    return dict(accepted=accepted, lease=lease)
