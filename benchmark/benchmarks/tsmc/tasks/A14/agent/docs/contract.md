# Public behavior contract

calibrations contains unique effective times with gain and offset. For each sample [time,value], use the calibration with greatest effective<=time, regardless of input order. Return value*gain+offset or None when no calibration exists. Preserve sample order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
