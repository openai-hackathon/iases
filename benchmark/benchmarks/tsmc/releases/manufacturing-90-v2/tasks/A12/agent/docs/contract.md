# Public behavior contract

parts is an ordered unique list of part ids. measurements contains part/station/value records with unique part/station pairs. Return each part with a values list in requested station order. Missing values are None; retain numeric zero. Ignore records for unrequested parts or stations.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
