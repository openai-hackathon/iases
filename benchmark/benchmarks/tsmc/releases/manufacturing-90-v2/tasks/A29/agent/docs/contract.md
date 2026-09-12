# Public behavior contract

A synthetic factory utility monitor combines pressure (bar) and flow (litres/minute)
sampled at different rates. This service is inspired by cycle-wise, multirate hydraulic
monitoring. Its short traces and missing/quality scenarios are newly authored; the source
dataset reports no missing values.

Input contains cycles {id,start,end}, pressure and flow lists of {cycle,t,value,valid},
calibration mappings for both channels {gain,offset}, max_gap for each channel, and
min_coverage in [0,1]. Cycle ids are unique, end>start, timestamps and values are finite,
and timestamps are unique within each channel/cycle. Lists may be unordered. Times are
absolute seconds; cycles may touch or overlap. max_gap is positive. Each channel's affine
calibration is applied to every endpoint before integration.

Process each cycle independently: retain only its own rows with start<=t<=end and sort
by t. A supported segment joins ADJACENT retained observations only when BOTH are valid
and their separation is <= that channel's max_gap. Bad observations break support; do
not drop them and bridge their neighbors. Never extrapolate or borrow another cycle's
rows, even at a shared boundary. Between supported endpoints the signal is linear.

Intersect the two channels' supported intervals. Integrate flow and pressure*flow only
on this JOINT support, splitting at either channel's knots. volume is integral(flow)/60
litres; work is integral(pressure*flow)/600 kJ. Integrate the product of two linear
signals exactly, including its quadratic term; endpoint-product trapezoids are not exact.
coverage is the joint supported duration divided by the FULL cycle duration, not a count
of samples or the smaller of two separately supported durations. Accept iff joint duration
is positive and UNROUNDED coverage>=min_coverage. Otherwise volume/work are None.

Return a list sorted by (cycle start,id), each {cycle,coverage,accepted,volume,work}.
Round numeric results to six decimals only for output. Empty cycle lists return [].
Empty channels and one-point channels provide no supported duration. Inputs never change.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
