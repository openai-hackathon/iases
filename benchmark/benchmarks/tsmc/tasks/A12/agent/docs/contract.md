# Public behavior contract

Reconstruct the station measurement matrix that could have been known at each query.
parts and stations are ordered unique string lists. queries contains {asof,at}; their
order is arbitrary and must be preserved. asof is the inclusive recorded-time cutoff;
at is the inclusive measurement event-time cutoff. Times are integers.

measurements: {id,revision,recorded,part,station,event,raw,valid,deleted,calibration}.
calibrations: {id,revision,recorded,start,end,gain,offset,deleted} with start<end.
quality: {id,revision,recorded,valid}, where id names a measurement identity. Each list
has unique (id,revision); revisions are positive integers. Input order and recorded
order need not match revision order. raw is None or an exact decimal/rational string;
gain and offset are such strings. Every revision is a full replacement record.

For EACH query independently, first discard versions recorded after asof, then choose
the greatest revision per id in each list. A selected deleted measurement/calibration
removes that identity; never resurrect a superseded version. Among remaining measurement
identities for each requested (part,station), choose greatest (event,id) with event<=at.
This selection occurs BEFORE quality, missing-value or calibration checks. Thus a newer
invalid measurement suppresses an older valid one; unavailable cells stay None.

A visible quality revision overrides the selected measurement's valid flag; otherwise
use the measurement flag. The chosen cell is None for false validity, raw=None, missing
or deleted calibration, or calibration not covering the MEASUREMENT event time in
[start,end). Otherwise calculate raw*gain+offset exactly and return
{measurement:id,revision:measurement_revision,calibration_revision:revision,value:string}.
value is a reduced fraction 'numerator/denominator', or an integer string when denominator
is 1, as produced by fractions.Fraction. Preserve zero and negative results.

Return one matrix per query: [{part,values:[cell in requested station order]}] in the
requested part order. Keep parts with no measurements and ignore unrelated identities.
At most 100 versions per list and 20 queries are supplied. No input is changed.
The revision/query protocol is synthetic context for manufacturing-data provenance,
not a claim of a defect in a NIST system.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
